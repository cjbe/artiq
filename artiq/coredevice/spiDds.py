from artiq.language.core import *
from artiq.language.types import *


class AD9910():
    kernel_invariants = {
        "core", "sysclk", "spi", "io_update", "io_rst"
    }

    def __init__(self, dmgr, sysclk, spi_device, io_update_device, io_rst_device=None):
        self.core = dmgr.get("core")
        self.sysclk = sysclk
        self.spi = dmgr.get(spi_device)
        self.io_update = dmgr.get(io_update_device)
        if io_rst_device is not None:
            self.io_rst = dmgr.get(io_rst_device)

    @kernel
    def init(self):
        """Initialises the DDS misc config. Call after reset before any other DDS function"""

        self.spi.set_config_mu(0,5,5)
        self.spi.set_xfer(write_length=8)

        # Sinc Filter on, Sine output, Autoclear phase accum on io update, SDIO input only
        self._write_reg(0, [0,0x41,0x20,0x2])
        # Enable amplitude scaling, SYNC_CLK enabled, matched latency. SYNC_SMP_ERR enabled (active low)
        self._write_reg(1, [0x1, 0x40,0, 0x80])
        # Default values + ref divider bypassed
        self._write_reg(2, [0x1f,0x3f,0xc0,0x00])
        # Set FS output current of DAC to max
        self._write_reg(3, [0,0,0,0xff])

    @kernel
    def _write_reg(self, addr, data):
        """Write AD9910 reg.
        addr is reg address
        data is byte array"""
        self.spi.write(addr<<24)
        delay(8*ns)
        for d in data:
            self.spi.write(d<<24)
            delay(8*ns)

    @kernel
    def _write_ftw(self, freq_lsb=0, phase_lsb=0, amp_lsb=0x3fff, profile=0):
        reg = 0xE+profile
        data = [0]*8
        # First 4 bytes are freq word
        for i in range(4):
            data[4+i] = 0xff & (freq_lsb >> 8*i)
        # Next 2 bytes are phase
        for i in range(2):
            data[3-i] = 0xff & (phase_lsb >> 8*i)
        # Highest 2 are (14 bit) amp
        for i in range(2):
            data[1-i] = 0xff & (amp_lsb >> 8*i)
        self._write_reg(reg, data)

    @kernel
    def set_mu(self, freq_mu, phase_mu, profile=0):
        # TODO: Should adjust the timeline such that IO_UPDATE occurs at now()
        self.io_rst.pulse(16*ns)
        delay(8*ns)
        self.write_ftw(freq_mu, phase_mu, profile=profile)
        delay(16*ns)
        self.dds_ioupdate.pulse(16*ns)

    @kernel
    def set(self, freq, phase, profile=profile):
        freq_mu = self.frequency_to_ftw(freq)
        phase_mu = self.turns_to_pow(phase)
        self.set_mu(freq_mu, phase_mu, profile=profile)

    @portable(flags=["fast-math"])
    def frequency_to_ftw(self, frequency):
        """Returns the frequency tuning word corresponding to the given
        frequency.
        """
        return round(int(2, width=64)**32*frequency/self.sysclk)

    @portable(flags=["fast-math"])
    def turns_to_pow(self, turns):
        """Returns the phase offset word corresponding to the given phase
        in turns."""
        return round(turns*2**self.pow_width)