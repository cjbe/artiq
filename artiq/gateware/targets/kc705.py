#!/usr/bin/env python3

import argparse
import sys

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

        # 10 MHz when using 125MHz input
        self.clock_domains.cd_ext_clkout = ClockDomain(reset_less=True)
        ext_clkout = platform.request("user_sma_gpio_p_33")
        self.sync.ext_clkout += ext_clkout.eq(~ext_clkout)


        rtio_external_clk = Signal()
        user_sma_clock = platform.request("user_sma_clock")
        platform.add_period_constraint(user_sma_clock.p, 8.0)
        self.specials += Instance("IBUFDS",
                                  i_I=user_sma_clock.p, i_IB=user_sma_clock.n,
                                  o_O=rtio_external_clk)

        pll_locked = Signal()
        rtio_clk = Signal()
        rtiox4_clk = Signal()
        ext_clkout_clk = Signal()
        self.specials += [
            Instance("PLLE2_ADV",
                     p_STARTUP_WAIT="FALSE", o_LOCKED=pll_locked,

                     p_REF_JITTER1=0.01,
                     p_CLKIN1_PERIOD=8.0, p_CLKIN2_PERIOD=8.0,
                     i_CLKIN1=rtio_internal_clk, i_CLKIN2=rtio_external_clk,
                     # Warning: CLKINSEL=0 means CLKIN2 is selected
                     i_CLKINSEL=~self._clock_sel.storage,

                     # VCO @ 1GHz when using 125MHz input
                     p_CLKFBOUT_MULT=8, p_DIVCLK_DIVIDE=1,
                     i_CLKFBIN=self.cd_rtio.clk,
                     i_RST=self._pll_reset.storage,

                     o_CLKFBOUT=rtio_clk,

                     p_CLKOUT0_DIVIDE=2, p_CLKOUT0_PHASE=0.0,
                     o_CLKOUT0=rtiox4_clk,

                     p_CLKOUT1_DIVIDE=50, p_CLKOUT1_PHASE=0.0,
                     o_CLKOUT1=ext_clkout_clk),
            Instance("BUFG", i_I=rtio_clk, o_O=self.cd_rtio.clk),
            Instance("BUFG", i_I=rtiox4_clk, o_O=self.cd_rtiox4.clk),
            Instance("BUFG", i_I=ext_clkout_clk, o_O=self.cd_ext_clkout.clk),

            AsyncResetSynchronizer(self.cd_rtio, ~pll_locked),
            MultiReg(pll_locked, self._pll_locked.status)
        ]


# The default user SMA voltage on KC705 is 2.5V, and the Migen platform
# follows this default. But since the SMAs are on the same bank as the DDS,
# which is set to 3.3V by reprogramming the KC705 power ICs, we need to
# redefine them here.
_sma33_io = [
    ("user_sma_gpio_p_33", 0, Pins("Y23"), IOStandard("LVCMOS33")),
    ("user_sma_gpio_n_33", 0, Pins("Y24"), IOStandard("LVCMOS33")),
]


_ams101_dac = [
    ("ams101_dac", 0,
        Subsignal("ldac", Pins("XADC:GPIO0")),
        Subsignal("clk", Pins("XADC:GPIO1")),
        Subsignal("mosi", Pins("XADC:GPIO2")),
        Subsignal("cs_n", Pins("XADC:GPIO3")),
        IOStandard("LVTTL")
     )
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

        self.platform.add_extension(_sma33_io)
        self.platform.add_extension(_ams101_dac)

        i2c = self.platform.request("i2c")
        self.submodules.i2c = gpio.GPIOTristate([i2c.scl, i2c.sda])
        self.csr_devices.append("i2c")
        self.config["I2C_BUS_COUNT"] = 1

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

class Oxford(_NIST_Ions):
    def __init__(self, cpu_type="or1k", **kwargs):
        _NIST_Ions.__init__(self, cpu_type, **kwargs)
        
        platform = self.platform
        platform.add_extension(oxford.fmc_adapter_io)

        rtio_channels = []

        led = platform.request("ledFrontPanel", 0) 
        self.comb += led.eq(1) # Front panel LED0 hard wired on
        
        for bank in ['a','b','c','d','e','f','g']:
            for i in range(8):
                phy = ttl_serdes_7series.Output_8X(platform.request(
                    bank, 
                    descrambleList[i]),
                    invert=True)
                    
                self.submodules += phy
                rtio_channels.append(rtio.Channel.from_phy(phy))
            
        for i in range(8):
            phy = ttl_serdes_7series.Inout_8X(
                platform.request("in", descrambleList[i]),
                invert=True)
            self.submodules += phy
            rtio_channels.append(rtio.Channel.from_phy(phy, ififo_depth=512))
            
        # No invert for the LEDs
        phy = ttl_simple.Output(platform.request("ledFrontPanel", 1))
        self.submodules += phy
        rtio_channels.append(rtio.Channel.from_phy(phy))

        self.config["RTIO_LOG_CHANNEL"] = len(rtio_channels)
        rtio_channels.append(rtio.LogChannel())

        self.add_rtio(rtio_channels)


class OxfordSingleFmc(_NIST_Ions):
    def __init__(self, cpu_type="or1k", **kwargs):
        _NIST_Ions.__init__(self, cpu_type, **kwargs)
        
        platform = self.platform
        platform.add_extension(oxford.fmc_adapter_io)

        rtio_channels = []

        for bank in ['a','b','c','d','e']:
            for i in range(8):
                phy = ttl_serdes_7series.Inout_8X(platform.request(
                    bank, 
                    descrambleList[i]),
                    invert=True)
                    
                self.submodules += phy
                rtio_channels.append(rtio.Channel.from_phy(phy))

        for i in range(2):
            # No invert for the LEDs
            phy = ttl_simple.Output(platform.request("ledFrontPanel", i))
            self.submodules += phy
            rtio_channels.append(rtio.Channel.from_phy(phy))

        self.config["RTIO_LOG_CHANNEL"] = len(rtio_channels)
        rtio_channels.append(rtio.LogChannel())

        self.add_rtio(rtio_channels)


class TransparentOverride(Module):
    """Connects outputs to internal logic when input low, otherwise connects 
    them to an external input, connected to the old control system"""
    def __init__(self, pad, logicOutput, externalInput, inputOverride):
        self.comb += If(inputOverride,
            pad.eq(externalInput)
        ).Else(
            pad.eq(logicOutput)
        )


class OxfordLab2(_NIST_Ions):
    """Hardware adapter for Lab 2.
    Banks a,b,c,d all Serdes outputs
    Banks e and f TTL outputs (no serdes), potentially overridden by inputs, 
        apart from f[6:7], which are normal serdes outputs 
    Banks g, 'in' all inputs, all TTL inputs (no serdes) apart from in[6] and in[7]
    Override functionality:
    When 'external override' is enabled:
    * inputs g[0:7] connected to outputs e[0:7]
    * inputs in[0:5] connected to outputs f[0:5]
    when 'external override' is disabled:
    * all outputs controlled by Artiq"""
    def __init__(self, cpu_type="or1k", **kwargs):
        _NIST_Ions.__init__(self, cpu_type, **kwargs)
        
        platform = self.platform
        platform.add_extension(oxford.fmc_adapter_io)

        rtio_channels = []

        led = platform.request("ledFrontPanel", 0) 
        self.comb += led.eq(1) # Front panel LED0 hard wired on
        
        # The 8+6 'override inputs'
        overrideInputs = []
        overrideInputs.extend(
            [platform.request("g", descrambleList[i]) for i in range(8) ])
        overrideInputs.extend(
            [platform.request("in", descrambleList[i]) for i in range(6) ])

        inputOverride = Signal()

        for bank in ['a','b','c','d']:
            for i in range(8):
                phy = ttl_serdes_7series.Output_8X(
                    platform.request(bank, descrambleList[i]),
                    invert=True)
                self.submodules += phy
                rtio_channels.append(rtio.Channel.from_phy(phy))
            
        for bank in ['e', 'f']:
            for i in range(8):
                ind = 8+i if bank=='f' else i
                pad = platform.request(bank, descrambleList[i])
                internalOutput = Signal()
                if bank=='f' and i>=6:
                    phy = ttl_serdes_7series.Output_8X(
                        internalOutput,
                        invert=True)
                else:
                    phy = ttl_simple.Output(internalOutput, invert=True)
                    overrideMod = TransparentOverride(
                        pad,
                        internalOutput,
                        overrideInputs[ind],
                        inputOverride)
                    self.submodules += overrideMod
                self.submodules += phy
                rtio_channels.append(rtio.Channel.from_phy(phy))

        for bank in ['g', 'in']:
            for i in range(8):
                ind = 8+i if bank=='in' else i
                if bank=='in' and i>=6:
                    phy = ttl_serdes_7series.Inout_8X(
                            platform.request("in", descrambleList[i]), 
                            invert=True)
                else:
                    phy = ttl_simple.Inout( overrideInputs[ind], invert=True)
                self.submodules += phy
                rtio_channels.append(rtio.Channel.from_phy(phy, ififo_depth=512))

        # No invert for the LEDs
        phy = ttl_simple.Output(platform.request("ledFrontPanel", 1))
        self.submodules += phy
        rtio_channels.append(rtio.Channel.from_phy(phy))

        # External override enable signal
        phy = ttl_simple.Output(inputOverride)
        self.submodules += phy
        rtio_channels.append(rtio.Channel.from_phy(phy))

        self.config["HAS_RTIO_LOG"] = None
        self.config["RTIO_LOG_CHANNEL"] = len(rtio_channels)
        rtio_channels.append(rtio.LogChannel())

        self.add_rtio(rtio_channels)



def main():
    parser = argparse.ArgumentParser(
        description="ARTIQ core device builder / KC705 "
                    "+ Oxford hardware adapters")
    builder_args(parser)
    soc_kc705_args(parser)
    parser.add_argument("-H", "--hw-adapter", default="oxford_lab2",
                        help="hardware adapter type: "
                             "oxford / oxford_lab2 / oxford_singlefmc"
                             "(default: %(default)s)")
    args = parser.parse_args()

    hw_adapter = args.hw_adapter.lower()
    if hw_adapter == "oxford":
        cls = Oxford
    elif hw_adapter == "oxford_lab2":
        cls = OxfordLab2
    elif hw_adapter == "oxford_singlefmc":
        cls = OxfordSingleFmc
    else:
        raise SystemExit("Invalid hardware adapter string (-H/--hw-adapter)")

    soc = cls(**soc_kc705_argdict(args))
    build_artiq_soc(soc, builder_argdict(args))


if __name__ == "__main__":
    main()

