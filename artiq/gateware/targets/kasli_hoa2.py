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

from artiq.gateware.targets.kasli import (_MasterBase, _SatelliteBase)
from artiq.gateware import eem


class Master(_MasterBase):
    def __init__(self, *args, **kwargs):
        _MasterBase.__init__(self, *args, rtio_clk_freq=125e6, **kwargs)

        platform = self.platform

        # EEM clock fan-out from Si5324, not MMCX
        try:
            self.comb += platform.request("clk_sel").eq(1)
        except ConstraintError:
            pass

        self.rtio_channels = []

        eem.DIO.add_std(self, 0,
            ttl_serdes_7series.InOut_8X, ttl_serdes_7series.InOut_8X)
        eem.DIO.add_std(self, 1,
            ttl_serdes_7series.InOut_8X, ttl_serdes_7series.InOut_8X)
        eem.Urukul.add_std(self, 3, 2, ttl_serdes_7series.Output_8X)
        eem.Zotino.add_std(self, 4, ttl_serdes_7series.Output_8X)

        self.config["HAS_RTIO_LOG"] = None
        self.config["RTIO_LOG_CHANNEL"] = len(self.rtio_channels)
        self.rtio_channels.append(rtio.LogChannel())

        self.add_rtio(self.rtio_channels)


class Satellite(_SatelliteBase):
    def __init__(self, *args, **kwargs):
        _SatelliteBase.__init__(self, *args, rtio_clk_freq=125e6, **kwargs)

        platform = self.platform

        # EEM clock fan-out from Si5324, not MMCX
        try:
            self.comb += platform.request("clk_sel").eq(1)
        except ConstraintError:
            pass

        self.rtio_channels = []

        eem.SUServo.add_std(
            self, eems_sampler=(5, 4),
            eems_urukul0=(1, 0), eems_urukul1=(3, 2),
            t_rtt=15+4)

        eem.DIO.add_std(self, 7,
            ttl_serdes_7series.InOut_8X, ttl_serdes_7series.InOut_8X)

        self.add_rtio(self.rtio_channels)


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
