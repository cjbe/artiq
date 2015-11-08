#!/usr/bin/env python3.5

import argparse
import sys

from artiq.devices.trapDac.driver import TrapDac, TrapDacSim
from artiq.protocols.pc_rpc import simple_server_loop
from artiq.tools import verbosity_args, simple_network_args, init_logger


def get_argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trapDacDevice", default=None,
                        help="Trap DC Dac serial device")
    parser.add_argument("--trapRFDevice", default=None,
                        help="Trap RF serial device")    
    parser.add_argument("--simulation", action="store_true",
                        help="Put the driver in simulation mode, even if "
                             "--device is used.")
    
    simple_network_args(parser, 4004)
    verbosity_args(parser)
    return parser


def main():
    args = get_argparser().parse_args()
    init_logger(args)

    if not args.simulation and (args.trapDacDevice is None or args.trapRFDevice is None):
        print("You need to specify either --simulation or --trapDacDevice and --trapRFDevice"
              "arguments. Use --help for more information.")
        sys.exit(1)

    if args.simulation:
        dev = TrapDacSim()
    else:
        dev = TrapDac(addrDCInterface=args.trapDacDevice, addrRFInterface=args.trapRFDevice)
        
    simple_server_loop({"trapDac": dev}, args.bind, args.port)


if __name__ == "__main__":
    main()
