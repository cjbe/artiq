#!/usr/bin/env python3

import argparse

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer
from migen.genlib.cdc import MultiReg
from migen.build.generic_platform import *
from migen.build.xilinx.vivado import XilinxVivadoToolchain
from migen.build.xilinx.ise import XilinxISEToolchain

from misoc.interconnect.csr import *
from misoc.cores import gpio
from misoc.targets.kc705 import MiniSoC, soc_kc705_args, soc_kc705_argdict
from misoc.integration.builder import builder_args, builder_argdict

from artiq.gateware.amp import AMPSoC, build_artiq_soc
from artiq.gateware import rtio, oxford
from artiq.gateware.rtio.phy import (ttl_simple, ttl_serdes_7series,
                                     dds, spi)
from artiq import __version__ as artiq_version


class _RTIOCRG(Module, AutoCSR):
    def __init__(self, platform, rtio_internal_clk):
        self._clock_sel = CSRStorage()
        self._pll_reset = CSRStorage(reset=1)
        self._pll_locked = CSRStatus()
        self.clock_domains.cd_rtio = ClockDomain()
        self.clock_domains.cd_rtiox4 = ClockDomain(reset_less=True)

        pll_locked = Signal()
        rtio_clk = Signal()
        rtiox4_clk = Signal()
        self.specials += [
            Instance("PLLE2_ADV",
                     p_STARTUP_WAIT="FALSE", o_LOCKED=pll_locked,

                     p_REF_JITTER1=0.01,
                     p_CLKIN1_PERIOD=8.0,
                     i_CLKIN1=rtio_internal_clk,
                     # Warning: CLKINSEL=0 means CLKIN2 is selected
                     i_CLKINSEL=1,

                     # VCO @ 1GHz when using 125MHz input
                     p_CLKFBOUT_MULT=8, p_DIVCLK_DIVIDE=1,
                     i_CLKFBIN=self.cd_rtio.clk,
                     i_RST=self._pll_reset.storage,

                     o_CLKFBOUT=rtio_clk,

                     p_CLKOUT0_DIVIDE=2, p_CLKOUT0_PHASE=0.0,
                     o_CLKOUT0=rtiox4_clk),
            Instance("BUFG", i_I=rtio_clk, o_O=self.cd_rtio.clk),
            Instance("BUFG", i_I=rtiox4_clk, o_O=self.cd_rtiox4.clk),

            AsyncResetSynchronizer(self.cd_rtio, ~pll_locked),
            MultiReg(pll_locked, self._pll_locked.status)
        ]




class _NIST_Ions(MiniSoC, AMPSoC):
    mem_map = {
        "cri_con":       0x10000000,
        "rtio":          0x20000000,
        "rtio_dma":      0x30000000,
        "mailbox":       0x70000000
    }
    mem_map.update(MiniSoC.mem_map)

    def __init__(self, cpu_type="or1k", **kwargs):
        MiniSoC.__init__(self,
                         cpu_type=cpu_type,
                         sdram_controller_type="minicon",
                         l2_size=128*1024,
                         ident=artiq_version,
                         ethmac_nrxslots=4,
                         ethmac_ntxslots=4,
                         **kwargs)
        AMPSoC.__init__(self)
        if isinstance(self.platform.toolchain, XilinxVivadoToolchain):
            self.platform.toolchain.bitstream_commands.extend([
                "set_property BITSTREAM.GENERAL.COMPRESS True [current_design]",
            ])
        if isinstance(self.platform.toolchain, XilinxISEToolchain):
            self.platform.toolchain.bitgen_opt += " -g compress"

        self.submodules.leds = gpio.GPIOOut(Cat(
            self.platform.request("user_led", 0),
            self.platform.request("user_led", 1)))
        self.csr_devices.append("leds")

        self.config["HAS_DDS"] = None

    def add_rtio(self, rtio_channels):
        self.submodules.rtio_crg = _RTIOCRG(self.platform, self.crg.cd_sys.clk)
        self.csr_devices.append("rtio_crg")
        self.submodules.rtio_core = rtio.Core(rtio_channels)
        self.csr_devices.append("rtio_core")
        self.submodules.rtio = rtio.KernelInitiator()
        self.submodules.rtio_dma = ClockDomainsRenamer("sys_kernel")(
            rtio.DMA(self.get_native_sdram_if()))
        self.register_kernel_cpu_csrdevice("rtio")
        self.register_kernel_cpu_csrdevice("rtio_dma")
        self.submodules.cri_con = rtio.CRIInterconnectShared(
            [self.rtio.cri, self.rtio_dma.cri],
            [self.rtio_core.cri])
        self.register_kernel_cpu_csrdevice("cri_con")
        self.submodules.rtio_moninj = rtio.MonInj(rtio_channels)
        self.csr_devices.append("rtio_moninj")

        self.rtio_crg.cd_rtio.clk.attr.add("keep")
        self.platform.add_period_constraint(self.rtio_crg.cd_rtio.clk, 8.)
        self.platform.add_false_path_constraints(
            self.crg.cd_sys.clk,
            self.rtio_crg.cd_rtio.clk)

        self.submodules.rtio_analyzer = rtio.Analyzer(self.rtio_core.cri,
                                                      self.get_native_sdram_if())
        self.csr_devices.append("rtio_analyzer")



# The input and output 8-channel buffer boards scramble and invert the channels.
# This list maps the logical index to the physical index
descrambleList = [ 3, 2, 1, 0, 7, 6, 5, 4 ];


class Singlefmc(_NIST_Ions):
    """
    KC705 with VHDCI -> EEM adapter on HPC and LPC FMCs
    """
    def __init__(self, cpu_type="or1k", **kwargs):
        _NIST_Ions.__init__(self, cpu_type, **kwargs)

        platform = self.platform
        platform.add_extension(oxford.fmc_adapter_io)

        rtio_channels = []

        for bank in ['a','b','c','d']:
            for i in range(8):
                phy = ttl_serdes_7series.Output_8X(
                                    platform.request(bank, descrambleList[i]),
                                    invert=True)
                self.submodules += phy
                rtio_channels.append(rtio.Channel.from_phy(
                                                phy,
                                                ofifo_depth=64))

        for i in range(8):
            phy = ttl_serdes_7series.Input_8X(
                                platform.request('e', descrambleList[i]),
                                invert=True)
            self.submodules += phy
            rtio_channels.append(rtio.Channel.from_phy(
                                            phy,
                                            ififo_depth=512))

        self.platform.add_platform_command(
            "set_false_path -from [get_pins *_serdes_oe_reg/C] -to [get_pins ISERDESE2_*/D]"
            )
        self.platform.add_platform_command(
            "set_false_path -from [get_pins OSERDESE2_*/CLK] -to [get_pins ISERDESE2_*/D]"
            )

        self.config["HAS_RTIO_LOG"] = None
        self.config["RTIO_LOG_CHANNEL"] = len(rtio_channels)
        rtio_channels.append(rtio.LogChannel())

        self.add_rtio(rtio_channels)


def main():
    parser = argparse.ArgumentParser(
        description="ARTIQ device binary builder for KC705 system"
                    "with a single Oxford hardware adapter on the LPC"
                    "FMC connector")
    builder_args(parser)
    soc_kc705_args(parser)
    args = parser.parse_args()

    soc = Singlefmc(**soc_kc705_argdict(args))
    build_artiq_soc(soc, builder_argdict(args))


if __name__ == "__main__":
    main()


























