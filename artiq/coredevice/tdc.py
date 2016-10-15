import numpy

from artiq.language.core import *
from artiq.language.types import *
from artiq.coredevice.rtio import rtio_output, rtio_input_timestamp_data


class TdcChannel:
    """TDC channel driver

    Provides functions to resolve the absolute timestamp of incoming rising
    and falling edges to a precision of ~30ps. This driver has a very similar
    interace to the input part of the TTLInOut driver. 

    :param channel: channel number
    """
    kernel_invariants = {"core", "channel"}

    def __init__(self, dmgr, channel, core_device="core"):
        self.core = dmgr.get(core_device)
        self.channel = channel

        # in RTIO cycles
        self.i_previous_timestamp = numpy.int64(0)


    @kernel
    def _set_sensitivity(self, value):
        rtio_output(now_mu(), self.channel, 0, value)
        self.i_previous_timestamp = now_mu()

    @kernel
    def gate_rising_mu(self, duration):
        """Register rising edge events for the specified duration
        (in machine units).

        The time cursor is advanced by the specified duration."""
        self._set_sensitivity(1)
        delay_mu(duration)
        self._set_sensitivity(0)

    @kernel
    def gate_falling_mu(self, duration):
        """Register falling edge events for the specified duration
        (in machine units).

        The time cursor is advanced by the specified duration."""
        self._set_sensitivity(2)
        delay_mu(duration)
        self._set_sensitivity(0)

    @kernel
    def gate_both_mu(self, duration):
        """Register both rising and falling edge events for the specified
        duration (in machine units).

        The time cursor is advanced by the specified duration."""
        self._set_sensitivity(3)
        delay_mu(duration)
        self._set_sensitivity(0)

    @kernel
    def gate_rising(self, duration):
        """Register rising edge events for the specified duration
        (in seconds).

        The time cursor is advanced by the specified duration."""
        self._set_sensitivity(1)
        delay(duration)
        self._set_sensitivity(0)

    @kernel
    def gate_falling(self, duration):
        """Register falling edge events for the specified duration
        (in seconds).

        The time cursor is advanced by the specified duration."""
        self._set_sensitivity(2)
        delay(duration)
        self._set_sensitivity(0)

    @kernel
    def gate_both(self, duration):
        """Register both rising and falling edge events for the specified
        duration (in seconds).

        The time cursor is advanced by the specified duration."""
        self._set_sensitivity(3)
        delay(duration)
        self._set_sensitivity(0)

    @kernel
    def count(self):
        """Poll the TDC input during all the previously programmed gate
        openings, and returns the number of registered events.

        This function does not interact with the time cursor."""
        count = 0
        while rtio_input_timestamp(self.i_previous_timestamp, self.channel) >= 0:
            count += 1
        return count

    @kernel
    def timestamp_mu(self):
        """Returns a tuple of the coarse/fine timestamp of the last event.
        If the read times out, returns -1 for the coarse timestamp. 
        The fine timestamp is in units of 2^-fp_count RTIO coarse clock periods
        (fp_count = 13 currently)."""
        return rtio_input_timestamp_data(self.i_previous_timestamp, self.channel)


class TDC:
    """TDC controller driver

    Provides debug interface to TDC
    """

    def __init__(self, dmgr, core_device="core"):
        self.core = dmgr.get(core_device)

    @kernel
    def reset(self):
        tdc_reset()

    @kernel
    def ring_osc_freq(self):
        return tdc_ringosc_freq()

    @kernel
    def read_hist(self, channel):
        N = 2048
        hist = [0]*N
        tdc_debug_init()
        for _ in range(channel):
            tdc_debug_next()
        for i in range(N):
            hist[i] = tdc_read_hist(i)
        tdc_debug_finish()
        return hist


@syscall(flags={"nowrite"})
def tdc_reset() -> TNone:
    raise NotImplementedError("syscall not simulated")

@syscall(flags={"nowrite"})
def tdc_debug_init() -> TNone:
    raise NotImplementedError("syscall not simulated")

@syscall(flags={"nowrite"})
def tdc_debug_next() -> TNone:
    raise NotImplementedError("syscall not simulated")

@syscall(flags={"nowrite"})
def tdc_debug_finish() -> TNone:
    raise NotImplementedError("syscall not simulated")


@syscall(flags={"nowrite"})
def tdc_ringosc_freq() -> TInt32:
    raise NotImplementedError("syscall not simulated")

@syscall(flags={"nowrite"})
def tdc_read_hist(addr: TInt32) -> TInt32:
    raise NotImplementedError("syscall not simulated")