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

from artiq.gateware.amp import AMPSoC
from artiq.gateware import rtio, vhdci
from artiq.gateware.rtio.phy import (ttl_simple, ttl_serdes_7series,
                                     dds, spi, serdes_tdc, ad5360_monitor)
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


class _StandaloneBase(MiniSoC, AMPSoC):
    mem_map = {
        "cri_con":       0x10000000,
        "rtio":          0x20000000,
        "rtio_dma":      0x30000000,
        "mailbox":       0x70000000
    }
    mem_map.update(MiniSoC.mem_map)

    def __init__(self, **kwargs):
        MiniSoC.__init__(self,
                         cpu_type="or1k",
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

        self.platform.add_period_constraint(self.rtio_crg.cd_rtio.clk, 8.)
        self.platform.add_false_path_constraints(
            self.crg.cd_sys.clk,
            self.rtio_crg.cd_rtio.clk)

        self.submodules.rtio_analyzer = rtio.Analyzer(self.rtio_core.cri,
                                                      self.get_native_sdram_if())
        self.csr_devices.append("rtio_analyzer")


class spi_wrapper:
    def __init__(self, pad_clk=None, pad_mosi=None, pad_cs_n=None, pad_miso=None):
        self.clk_p = pad_clk.p
        self.clk_n = pad_clk.n
        self.mosi_p = pad_mosi.p
        self.mosi_n = pad_mosi.n
        self.cs_n_p = pad_cs_n.p
        self.cs_n_n = pad_cs_n.n
        if pad_miso:
            self.miso_p = pad_miso.p
            self.miso_n = pad_miso.n


class VHDCI(_StandaloneBase):
    """
    KC705 with VHDCI -> EEM adapter on HPC and LPC FMCs
    """
    def __init__(self, **kwargs):
        _StandaloneBase.__init__(self, cpu_type="or1k", **kwargs)

        platform = self.platform
        platform.add_extension(vhdci.fmc_adapter_io)

        rtio_channels = []
        clock_generators = []


        def add_eem_spi(connector, eem, ind=0):
            stem = connector+"_eem"+str(eem)
            pad_clk = platform.request(stem, ind*4 + 0)
            pad_mosi = platform.request(stem, ind*4 + 1)
            pad_cs_n = platform.request(stem, ind*4 + 2)
            phy = spi.SPIMaster(spi_wrapper(pad_clk, pad_mosi, pad_cs_n),
                                differential=True, invert=True)
            self.submodules += phy
            rtio_channels.append(rtio.Channel.from_phy(
                phy, ofifo_depth=128, ififo_depth=128))

        def add_eem_ttl(connector, eem):
            # All TTL channels are In+Out capable
            phys = []
            for i in range(8):
                pad = platform.request(connector+"_eem"+str(eem), i)
                phy = ttl_serdes_7series.InOut_8X(pad.p, pad.n, invert=True)
                self.submodules += phy
                phys.append(phy)
                rtio_channels.append(rtio.Channel.from_phy(
                    phy, ififo_depth=512))
            return phys

        def add_eem_zotino(connector, eem):
            stem = connector+"_eem"+str(eem)
            pad_clk = platform.request(stem, 0)
            pad_mosi = platform.request(stem, 1)
            pad_miso = platform.request(stem, 2)
            pad_cs_n = platform.request(stem, 3)
            sdac_phy = spi.SPIMaster(spi_wrapper(pad_clk, pad_mosi, pad_cs_n,
                                                                pad_miso),
                                            differential=True, invert=True)
            self.submodules += sdac_phy
            rtio_channels.append(rtio.Channel.from_phy(sdac_phy, ififo_depth=4))

            # LDAC
            pad = platform.request(stem, 5)
            ldac_phy = ttl_serdes_7series.Output_8X(pad.p, pad.n, invert=True)
            self.submodules += ldac_phy
            rtio_channels.append(rtio.Channel.from_phy(ldac_phy))

            # CSN_EXT
            pad = platform.request(stem, 4)
            phy = ttl_serdes_7series.Output_8X(pad.p, pad.n, invert=True)
            self.submodules += phy
            rtio_channels.append(rtio.Channel.from_phy(phy))

            # CLRN
            pad = platform.request(stem, 7)
            phy = ttl_serdes_7series.Output_8X(pad.p, pad.n, invert=True)
            self.submodules += phy
            rtio_channels.append(rtio.Channel.from_phy(phy))

            # dac_monitor = ad5360_monitor.AD5360Monitor(sdac_phy.rtlink, ldac_phy.rtlink)
            # self.submodules += dac_monitor
            # sdac_phy.probes.extend(dac_monitor.probes)

        def add_tdc(phy_sig, phy_ref):
            phy_tdc = serdes_tdc.TDC(phy_sig=phy_sig, phy_ref=phy_ref)
            self.submodules += phy_tdc
            rtio_channels.append(rtio.Channel.from_phy(
                                 phy_tdc, ififo_depth=512))

        add_eem_ttl("lpc", 3)
        input_phys = add_eem_ttl("lpc", 2)
        add_eem_spi("lpc", 1, 0)
        add_eem_spi("lpc", 1, 1)
        add_eem_spi("lpc", 0, 0)
        add_eem_spi("lpc", 0, 1)
        add_eem_zotino("hpc", 0)
        add_tdc(input_phys[4], input_phys[5])
        add_tdc(input_phys[6], input_phys[7])

        phy = ttl_simple.Output(platform.request("user_led", 2))
        self.submodules += phy
        rtio_channels.append(rtio.Channel.from_phy(phy))

        lpc_i2c = self.platform.request("LPC_i2c")
        hpc_i2c = self.platform.request("HPC_i2c")
        self.submodules.i2c = gpio.GPIOTristate([lpc_i2c.scl, lpc_i2c.sda, hpc_i2c.scl, hpc_i2c.sda])
        self.csr_devices.append("i2c")
        self.config["I2C_BUS_COUNT"] = 2

        self.config["HAS_RTIO_LOG"] = None
        self.config["RTIO_LOG_CHANNEL"] = len(rtio_channels)
        rtio_channels.append(rtio.LogChannel())

        self.add_rtio(rtio_channels)


def main():
    parser = argparse.ArgumentParser(
        description="ARTIQ device binary builder for KC705 system"
                    "with VHDCI-EEM adapters on HPC and LPC FMCs")
    builder_args(parser)
    soc_kc705_args(parser)

    parser.add_argument("-V", "--variant", default="vhdci",
                        help="variant: "
                             "vhdci")
    args = parser.parse_args()

    variant = args.variant.lower()
    if variant == "vhdci":
        cls = VHDCI
    else:
        raise SystemExit("Invalid variant (-V/--variant)")

    soc = cls(**soc_kc705_argdict(args))
    build_artiq_soc(soc, builder_argdict(args))


if __name__ == "__main__":
    main()
