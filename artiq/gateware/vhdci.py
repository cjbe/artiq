from migen.build.generic_platform import *

"""
Pinout for passive FMC - VHDCI adapter (https://www.ohwr.org/projects/fmc-vhdci/wiki)

To drive the management I2C the board needs a 3V3 and GND rail added, instead of the
33rd diff. pair.
"""


eem_pins = [
["LA00_CC", "LA08", "LA02", "LA03", "LA04", "LA05", "LA06", "LA07" ],
["LA01_CC", "LA09", "LA10", "LA11", "LA12", "LA13", "LA14", "LA15"],
["LA19", "LA18_CC", "LA26", "LA21", "LA22", "LA23", "LA24", "LA25"],
["LA20", "LA27", "LA28", "LA29", "LA30", "LA31", "LA32", "LA33"],
]


def fmc_io():
    r = []
    io_std = "LVDS_25"
    for connector in "LPC", "HPC":
        for eem_ind, eem_vec in enumerate(eem_pins):
            for pin_ind, pin in enumerate(eem_vec):
                stem = connector + ":" + pin
                r+= [(connector.lower() + "_eem" + str(eem_ind), pin_ind,
                     Subsignal("p", Pins(stem+"_P")),
                     Subsignal("n", Pins(stem+"_N")),
                     IOStandard(io_std), Misc("DIFF_TERM=TRUE")
                    )]
        r += [(connector+"_i2c", 0,
                Subsignal("scl", Pins(connector+":LA16_N")),
                Subsignal("sda", Pins(connector+":LA16_P")),
                IOStandard("LVCMOS25"),
                Misc("PULLUP"))]
    return r

fmc_adapter_io = fmc_io()