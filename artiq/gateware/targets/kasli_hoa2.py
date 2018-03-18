#!/usr/bin/env python3

import argparse

from migen import *
from migen.build.generic_platform import *
from migen.genlib.io import DifferentialOutput

from misoc.targets.kasli import soc_kasli_args, soc_kasli_argdict
from misoc.integration.builder import builder_args, builder_argdict

from artiq.gateware import rtio
from artiq.gateware.rtio.phy import ttl_simple, ttl_serdes_7series, spi2
from artiq.build_soc import build_artiq_soc
from artiq import __version__ as artiq_version

from artiq.gateware.targets.kasli import (_MasterBase, _SatelliteBase, _dio,
    _urukul)


def add_dio(cls, eem):
    cls.platform.add_extension(_dio(eem))
    rtio_channels = []
    for port in range(8):
        pads = cls.platform.request(eem, port)
        phy = ttl_serdes_7series.InOut_8X(pads.p, pads.n)
        cls.submodules += phy
        rtio_channels.append(rtio.Channel.from_phy(phy))
    return rtio_channels


def add_urukul(cls, eem, eem_aux):
    cls.platform.add_extension(_urukul(eem, eem_aux))
    rtio_channels = []

    phy = spi2.SPIMaster(cls.platform.request(eem+"_spi_p"),
            cls.platform.request(eem+"_spi_n"))
    cls.submodules += phy
    rtio_channels.append(rtio.Channel.from_phy(phy, ififo_depth=4))

    pads = cls.platform.request(eem+"_dds_reset")
    s = Signal()
    cls.specials += DifferentialOutput(s, pads.p, pads.n)
    phy = ttl_simple.ClockGen(s)
    cls.submodules += phy
    rtio_channels.append(rtio.Channel.from_phy(phy))

    for signal in "io_update sw0 sw1 sw2 sw3".split():
        pads = cls.platform.request(eem+"_{}".format(signal))
        phy = ttl_serdes_7series.Output_8X(pads.p, pads.n)
        cls.submodules += phy
        rtio_channels.append(rtio.Channel.from_phy(phy))

    return rtio_channels


class Master(_MasterBase):
    def __init__(self, *args, **kwargs):
        _MasterBase.__init__(self, *args, **kwargs)

        platform = self.platform

        # EEM clock fan-out from Si5324, not MMCX
        try:
            self.comb += platform.request("clk_sel").eq(1)
        except ConstraintError:
            pass

        rtio_channels = []

        rtio_channels += add_dio(self, "eem0")
        rtio_channels += add_dio(self, "eem1")
        rtio_channels += add_urukul(self, "eem3", "eem2")

        self.config["HAS_RTIO_LOG"] = None
        self.config["RTIO_LOG_CHANNEL"] = len(rtio_channels)
        rtio_channels.append(rtio.LogChannel())

        self.add_rtio(rtio_channels)


class Satellite(_SatelliteBase):
    def __init__(self, *args, **kwargs):
        _SatelliteBase.__init__(self, *args, **kwargs)

        platform = self.platform

        # EEM clock fan-out from Si5324, not MMCX
        try:
            self.comb += platform.request("clk_sel").eq(1)
        except ConstraintError:
            pass

        rtio_channels = []

        rtio_channels += add_urukul(self, "eem1", "eem0")
        rtio_channels += add_urukul(self, "eem3", "eem2")

        self.add_rtio(rtio_channels)


def main():
    parser = argparse.ArgumentParser(
        description="ARTIQ device binary builder for the Kasli HOA2 setup")
    builder_args(parser)
    soc_kasli_args(parser)
    parser.set_defaults(output_dir="artiq_kasli")
    parser.add_argument("-V", "--variant", default="master",
                        help="variant: master/satellite ")
    args = parser.parse_args()

    variant = args.variant.lower()
    if variant == "master":
        cls = Master
    elif variant == "satellite":
        cls = Satellite
    else:
        raise SystemExit("Invalid variant (-V/--variant)")

    soc = cls(**soc_kasli_argdict(args))
    build_artiq_soc(soc, builder_argdict(args))


if __name__ == "__main__":
    main()
