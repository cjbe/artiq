#!/usr/bin/env python3.5

import argparse
import sys
import os

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer
from migen.genlib.cdc import MultiReg
from migen.build.generic_platform import *
from migen.build.xilinx.vivado import XilinxVivadoToolchain
from migen.build.xilinx.ise import XilinxISEToolchain
from migen.fhdl.specials import Keep

from misoc.interconnect.csr import *
from misoc.interconnect import wishbone
from misoc.cores import gpio
from misoc.integration.soc_core import mem_decoder
from misoc.targets.kc705 import MiniSoC, soc_kc705_args, soc_kc705_argdict
from misoc.integration.builder import builder_args, builder_argdict

from artiq.gateware.soc import AMPSoC, build_artiq_soc
from artiq.gateware import rtio, nist_qc1, nist_clock, nist_qc2, oxford
from artiq.gateware.tdc import TDC
from artiq.gateware.rtio.phy import ttl_simple, ttl_serdes_7series, dds, spi, tdc
from artiq import __version__ as artiq_version
from artiq import __artiq_dir__ as artiq_dir


class _RTIOCRG(Module, AutoCSR):
    def __init__(self, platform, rtio_internal_clk):
        self._clock_sel = CSRStorage()
        self._pll_reset = CSRStorage(reset=1)
        self._pll_locked = CSRStatus()
        self.clock_domains.cd_rtio = ClockDomain()
        self.clock_domains.cd_rtiox4 = ClockDomain(reset_less=True)

        # 250 MHz external clock input
        ext_clock = platform.request("ext_clk")
        platform.add_period_constraint(ext_clock.p, 4.0)
        
        # Generate 125 MHz clock from external clock
        rtio_external_clk = Signal()
        pll_out = Signal()
        ext_ref_deskew = Signal()
        ext_ref_deskew_buf = Signal()
        self.specials += [
            Instance("PLLE2_ADV",
                     p_STARTUP_WAIT="FALSE",
                     p_REF_JITTER1=0.01,
                     p_CLKIN1_PERIOD=4.0,
                     i_CLKIN1=ext_clock.p,

                     # VCO @ 1GHz
                     p_CLKFBOUT_MULT=4, p_DIVCLK_DIVIDE=1,
                     i_CLKFBIN=ext_ref_deskew_buf,
                     i_RST=self._pll_reset.storage,

                     o_CLKFBOUT=ext_ref_deskew,

                     p_CLKOUT0_DIVIDE=8, p_CLKOUT0_PHASE=0.0,
                     o_CLKOUT0=pll_out),
            Instance("BUFG", i_I=pll_out, o_O=rtio_external_clk),
            Instance("BUFG", i_I=ext_ref_deskew, o_O=ext_ref_deskew_buf),
        ]

        pll_locked = Signal()
        rtio_clk = Signal()
        rtiox4_clk = Signal()
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
                     o_CLKOUT0=rtiox4_clk),
            Instance("BUFG", i_I=rtio_clk, o_O=self.cd_rtio.clk),
            Instance("BUFG", i_I=rtiox4_clk, o_O=self.cd_rtiox4.clk),

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



class _Oxford_Ions(MiniSoC, AMPSoC):
    csr_map = {
        # mapped on Wishbone instead
        "timer_kernel": None,
        "rtio": None,
        "i2c": None,
        "tdc": None,

        "rtio_crg": 13,
        "kernel_cpu": 14,
        "rtio_moninj": 15,
        "rtio_analyzer": 16,
    }
    csr_map.update(MiniSoC.csr_map)
    mem_map = {
        "timer_kernel":  0x10000000, # (shadow @0x90000000)
        "rtio":          0x20000000, # (shadow @0xa0000000)
        "i2c":           0x30000000, # (shadow @0xb0000000)
        "tdc":           0x60000000,
        "mailbox":       0x70000000  # (shadow @0xf0000000)
    }
    mem_map.update(MiniSoC.mem_map)

    def __init__(self, cpu_type="or1k", **kwargs):
        MiniSoC.__init__(self,
                         cpu_type=cpu_type,
                         sdram_controller_type="minicon",
                         l2_size=128*1024,
                         with_timer=False,
                         ident=artiq_version,
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

        self.platform.add_extension(_sma33_io)

        i2c = self.platform.request("i2c")
        self.submodules.i2c = gpio.GPIOTristate([i2c.scl, i2c.sda])
        self.register_kernel_cpu_csrdevice("i2c")
        self.config["I2C_BUS_COUNT"] = 1

    def add_rtio(self, rtio_channels):
        self.submodules.rtio_crg = _RTIOCRG(self.platform, self.crg.cd_sys.clk)
        self.submodules.rtio = rtio.RTIO(rtio_channels)
        self.register_kernel_cpu_csrdevice("rtio")
        self.config["RTIO_FINE_TS_WIDTH"] = self.rtio.fine_ts_width
        self.submodules.rtio_moninj = rtio.MonInj(rtio_channels)

        self.specials += [
            Keep(self.rtio.cd_rsys.clk),
            Keep(self.rtio_crg.cd_rtio.clk),
            Keep(self.ethphy.crg.cd_eth_rx.clk),
            Keep(self.ethphy.crg.cd_eth_tx.clk),
        ]

        self.platform.add_period_constraint(self.rtio.cd_rsys.clk, 8.)
        self.platform.add_period_constraint(self.rtio_crg.cd_rtio.clk, 8.)
        self.platform.add_period_constraint(self.ethphy.crg.cd_eth_rx.clk, 8.)
        self.platform.add_period_constraint(self.ethphy.crg.cd_eth_tx.clk, 8.)
        self.platform.add_false_path_constraints(
            self.rtio.cd_rsys.clk,
            self.rtio_crg.cd_rtio.clk,
            self.ethphy.crg.cd_eth_rx.clk,
            self.ethphy.crg.cd_eth_tx.clk)

        self.submodules.rtio_analyzer = rtio.Analyzer(self.rtio,
            self.get_native_sdram_if())



# TDC parameters
tdc_n_carry4 = 340
tdc_n_ch = 2

# The input and output 8-channel buffer boards scramble and invert the channels.
# This list maps the logical index to the physical index
descrambleList = [ 3, 2, 1, 0, 7, 6, 5, 4 ];

class TransparentOverride(Module):
    """Connects outputs to internal logic when input low, otherwise connects them to an external input, connected to the old LCU"""
    def __init__(self, pad, logicOutput, externalInput, inputOverride):
        self.comb += If(inputOverride,
            pad.eq(externalInput)
        ).Else(
            pad.eq(logicOutput)
        )


class OxfordOverride(_Oxford_Ions):
    def __init__(self, cpu_type="or1k", **kwargs):
        _Oxford_Ions.__init__(self, cpu_type, **kwargs)
        
        platform = self.platform
        platform.add_extension(oxford.fmc_adapter_io)

        rtio_channels = []

        led = platform.request("ledFrontPanel", 0) 
        self.comb += led.eq(1) # Front panel LED0 hard wired on
        
        # The 6 'override inputs'
        overrideInputs = [ platform.request("in", descrambleList[i]) for i in range(2,8) ]

        inputOverride = Signal()

        for bank in ['a','b','c','d','e','f','g']:
            for i in range(8):
                if bank=='g' and i<6:
                    pad = platform.request(bank, descrambleList[i])
                    internalOutput = Signal()
                    phy = ttl_simple.Output(internalOutput, invert=True)
                    overrideMod = TransparentOverride( pad, internalOutput, overrideInputs[i], inputOverride )
                    self.submodules += overrideMod
                elif bank=='g' and i==7:
                    pad = platform.request(bank, descrambleList[i])
                    phy = ttl_simple.Output(pad, invert=True)
                    self.comb += inputOverride.eq(~pad)
                else:
                    phy = ttl_serdes_7series.Output_8X(platform.request(bank, descrambleList[i]), invert=True )
                self.submodules += phy
                rtio_channels.append(rtio.Channel.from_phy(phy))
            
        for i in range(2):
            phy = ttl_serdes_7series.Inout_8X(platform.request("in", descrambleList[i]), invert=True)
            self.submodules += phy
            rtio_channels.append(rtio.Channel.from_phy(phy, ififo_depth=512))
        for i in range(6):
            phy = ttl_simple.Inout( overrideInputs[i], invert=True)
            self.submodules += phy
            rtio_channels.append(rtio.Channel.from_phy(phy))
            
        
        phy = ttl_simple.Output(platform.request("ledFrontPanel", 1)) # No invert for the LEDs
        self.submodules += phy
        rtio_channels.append(rtio.Channel.from_phy(phy))

        # TDC
        tdc_inputs = Signal(tdc_n_ch)
        self.submodules.tdc = TDC(inputs=tdc_inputs, n_channels=tdc_n_ch, carry4_count=tdc_n_carry4)
        self.register_kernel_cpu_csrdevice("tdc")
        for i in range(tdc_n_ch):
            in_pair = self.platform.request("tdc_in", i)
            self.specials += Instance("IBUFDS", p_DIFF_TERM="True", i_I=in_pair.p, i_IB=in_pair.n, o_O=tdc_inputs[i])
            phy = tdc.Channel(self.tdc, i)
            self.submodules += phy
            rtio_channels.append(rtio.Channel.from_phy(phy))

        # AD9910 DDS SPI hacks
        dds_sigs = ["dds_iorst", "dds_ioupdate", "dds_p0", "dds_p1", "dds_p2"]
        for sig in dds_sigs:
            phy = ttl_simple.Output(platform.request(sig, 0))
            self.submodules += phy
            rtio_channels.append(rtio.Channel.from_phy(phy))

        self.config["RTIO_REGULAR_TTL_COUNT"] = len(rtio_channels)

        phy = spi.SPIMaster(self.platform.request("dds_spi", 0))
        self.submodules += phy
        self.config["RTIO_FIRST_SPI_CHANNEL"] = len(rtio_channels)
        rtio_channels.append(rtio.Channel.from_phy(
                phy, ofifo_depth=128, ififo_depth=128))

        self.config["RTIO_FIRST_DDS_CHANNEL"] = len(rtio_channels)
        self.config["RTIO_DDS_COUNT"] = 0
        self.config["DDS_CHANNELS_PER_BUS"] = 0
        self.config["DDS_AD9914"] = True

        self.config["RTIO_LOG_CHANNEL"] = len(rtio_channels)
        rtio_channels.append(rtio.LogChannel())

        self.add_rtio(rtio_channels)

        self.config["DDS_RTIO_CLK_RATIO"] = 24





def main():
    parser = argparse.ArgumentParser(
        description="ARTIQ core device builder / KC705 "
                    "+ Oxford hardware adapters")
    builder_args(parser)
    soc_kc705_args(parser)
    parser.add_argument("-H", "--hw-adapter", default="oxford_override",
                        help="hardware adapter type: "
                             " oxford_override "
                             "(default: %(default)s)")
    args = parser.parse_args()

    hw_adapter = args.hw_adapter.lower()
    if hw_adapter != "oxford_override":
        raise SystemExit("Invalid hardware adapter string (-H/--hw-adapter)")

    soc = OxfordOverride(**soc_kc705_argdict(args))
    soc.platform.add_source_dir(os.path.join(artiq_dir, "gateware", "tdc_core"))

    # Do not error out from combinatorial loops (from the TDC ring oscs)
    soc.platform.toolchain.pre_synthesis_commands.extend([
                "set_property SEVERITY {{Warning}} [get_drc_checks LUTLP-1]",
            ])

    # Constrain carry chain placement and timing
    for ch in range(tdc_n_ch):
        soc.platform.toolchain.post_synthesis_commands.extend([
            "set_false_path -through [get_nets {{{{tdc/cmp_channelbank/g_multi.cmp_channelbank/g_channels[{ch}].cmp_channel/cmp_delayline/signal_i}}}}]".format(ch=ch),
            "set_property LOC SLICE_X{x}Y0 [get_cells \
                {{{{tdc/cmp_channelbank/g_multi.cmp_channelbank/g_channels[{ch}].cmp_channel/cmp_delayline/g_carry4[0].g_firstcarry4.cmp_CARRY4}}}}]".format(x=ch*2,ch=ch),
            ])
        for i in range(tdc_n_carry4*4):
            soc.platform.toolchain.post_synthesis_commands.append(
                "set_property LOC SLICE_X{x}Y{y} [get_cells \
                {{{{tdc/cmp_channelbank/g_multi.cmp_channelbank/g_channels[{ch}].cmp_channel/cmp_delayline/g_fd[{ff}].cmp_FDR_1}}}}]"
                .format(x=ch*2,y=i//4, ch=ch, ff=i))

    # Save out routed design
    soc.platform.toolchain.bitstream_commands.extend([
                "write_checkpoint -force top_route.dcp"
            ])

    build_artiq_soc(soc, builder_argdict(args))

if __name__ == "__main__":
    main()

