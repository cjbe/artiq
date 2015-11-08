#!/usr/bin/env python3.5

import argparse
import sys

from artiq.devices.dosDac.driver import DosDac, DosDacSim
from artiq.protocols.pc_rpc import simple_server_loop
from artiq.tools import verbosity_args, simple_network_args, init_logger


def get_argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--device", default=None,
                        help="serial device. See documentation for how to "
                             "specify a USB Serial Number.")
    parser.add_argument("--simulation", action="store_true",
                        help="Put the driver in simulation mode, even if "
                             "--device is used.")
    
    simple_network_args(parser, 4001)
    verbosity_args(parser)
    return parser


def main():
    args = get_argparser().parse_args()
    init_logger(args)

    if not args.simulation and args.device is None:
        print("You need to specify either --simulation or -d/--device "
              "argument. Use --help for more information.")
        sys.exit(1)

    if args.simulation:
        dev = DosDacSim()
    else:
        dev = DosDac(addr=args.device)
        
    simple_server_loop({"dosDac": dev}, args.bind, args.port)

if __name__ == "__main__":
    main()
