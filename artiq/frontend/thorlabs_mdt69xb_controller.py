#!/usr/bin/env python3.5

import argparse
import sys

from artiq.devices.thorlabs_mdt69xb.driver import PiezoController
from artiq.protocols.pc_rpc import simple_server_loop
from artiq.tools import verbosity_args, simple_network_args, init_logger


def get_argparser():
    parser = argparse.ArgumentParser(description="ARTIQ controller for the Thorlabs MDT693B or MDT694B 3 (1) channel open-loop piezo controller")
    simple_network_args(parser, 4002)
    parser.add_argument("-d", "--device", default=None,
                        help="serial device. See documentation for how to "
                             "specify a USB Serial Number.")
    parser.add_argument("--simulation", action="store_true",
                        help="Put the driver in simulation mode, even if "
                             "--device is used.")
    verbosity_args(parser)
    return parser


def main():
    args = get_argparser().parse_args()
    init_logger(args)

    if not args.simulation and args.device is None:
        print("You need to specify either --simulation or -d/--device "
              "argument. Use --help for more information.")
        sys.exit(1)

    dev = PiezoController(args.device if not args.simulation else None)
    
    try:
        simple_server_loop({"piezoController": dev}, args.bind, args.port)
    finally:
        dev.close()
        
if __name__ == "__main__":
    main()
