from migen.build.generic_platform import *

fmc_adapter_io = [
    # LPC : JF
    ("a", 0, Pins("LPC:LA01_CC_P"), IOStandard("LVTTL")),
    ("a", 1, Pins("LPC:LA00_CC_N"), IOStandard("LVTTL")),
    ("a", 2, Pins("LPC:LA01_CC_N"), IOStandard("LVTTL")),
    ("a", 3, Pins("LPC:LA03_P"), IOStandard("LVTTL")),
    ("a", 4, Pins("LPC:LA00_CC_P"), IOStandard("LVTTL")),
    ("a", 5, Pins("LPC:LA02_P"), IOStandard("LVTTL")),
    ("a", 6, Pins("LPC:LA02_N"), IOStandard("LVTTL")),
    ("a", 7, Pins("LPC:LA03_N"), IOStandard("LVTTL")),

    # LPC : JG
    ("b", 0, Pins("LPC:LA04_P"), IOStandard("LVTTL")),
    ("b", 1, Pins("LPC:LA04_N"), IOStandard("LVTTL")),
    ("b", 2, Pins("LPC:LA06_N"), IOStandard("LVTTL")),
    ("b", 3, Pins("LPC:LA07_P"), IOStandard("LVTTL")),
    ("b", 4, Pins("LPC:LA06_P"), IOStandard("LVTTL")),
    ("b", 5, Pins("LPC:LA05_P"), IOStandard("LVTTL")),
    ("b", 6, Pins("LPC:LA05_N"), IOStandard("LVTTL")),
    ("b", 7, Pins("LPC:LA07_N"), IOStandard("LVTTL")),

    # LPC : JH
    ("c", 0, Pins("LPC:LA09_P"), IOStandard("LVTTL")),
    ("c", 1, Pins("LPC:LA09_N"), IOStandard("LVTTL")),
    ("c", 2, Pins("LPC:LA10_N"), IOStandard("LVTTL")),
    ("c", 3, Pins("LPC:LA16_P"), IOStandard("LVTTL")),
    ("c", 4, Pins("LPC:LA10_P"), IOStandard("LVTTL")),
    ("c", 5, Pins("LPC:LA11_P"), IOStandard("LVTTL")),
    ("c", 6, Pins("LPC:LA11_N"), IOStandard("LVTTL")),
    ("c", 7, Pins("LPC:LA16_N"), IOStandard("LVTTL")),
    
    # LPC : JI
    ("d", 0, Pins("LPC:LA29_N"), IOStandard("LVTTL")),
    ("d", 1, Pins("LPC:LA29_P"), IOStandard("LVTTL")),
    ("d", 2, Pins("LPC:LA25_N"), IOStandard("LVTTL")),
    ("d", 3, Pins("LPC:LA25_P"), IOStandard("LVTTL")),
    ("d", 4, Pins("LPC:LA28_N"), IOStandard("LVTTL")),
    ("d", 5, Pins("LPC:LA28_P"), IOStandard("LVTTL")),
    ("d", 6, Pins("LPC:LA24_N"), IOStandard("LVTTL")),
    ("d", 7, Pins("LPC:LA24_P"), IOStandard("LVTTL")),

    # LPC : JK
    ("e", 0, Pins("LPC:LA33_N"), IOStandard("LVTTL")),
    ("e", 1, Pins("LPC:LA33_P"), IOStandard("LVTTL")),
    ("e", 2, Pins("LPC:LA30_P"), IOStandard("LVTTL")),
    ("e", 3, Pins("LPC:LA31_P"), IOStandard("LVTTL")),
    ("e", 4, Pins("LPC:LA32_N"), IOStandard("LVTTL")),
    ("e", 5, Pins("LPC:LA32_P"), IOStandard("LVTTL")),
    ("e", 6, Pins("LPC:LA30_N"), IOStandard("LVTTL")),
    ("e", 7, Pins("LPC:LA31_N"), IOStandard("LVTTL")),
    
    
    # HPC : JF
    ("f", 0, Pins("HPC:LA01_CC_P"), IOStandard("LVTTL")),
    ("f", 1, Pins("HPC:LA00_CC_N"), IOStandard("LVTTL")),
    ("f", 2, Pins("HPC:LA01_CC_N"), IOStandard("LVTTL")),
    ("f", 3, Pins("HPC:LA03_P"), IOStandard("LVTTL")),
    ("f", 4, Pins("HPC:LA00_CC_P"), IOStandard("LVTTL")),
    ("f", 5, Pins("HPC:LA02_P"), IOStandard("LVTTL")),
    ("f", 6, Pins("HPC:LA02_N"), IOStandard("LVTTL")),
    ("f", 7, Pins("HPC:LA03_N"), IOStandard("LVTTL")),
    
    # HPC : JG
    ("g", 0, Pins("HPC:LA04_P"), IOStandard("LVTTL")),
    ("g", 1, Pins("HPC:LA04_N"), IOStandard("LVTTL")),
    ("g", 2, Pins("HPC:LA06_N"), IOStandard("LVTTL")),
    ("g", 3, Pins("HPC:LA07_P"), IOStandard("LVTTL")),
    ("g", 4, Pins("HPC:LA06_P"), IOStandard("LVTTL")),
    ("g", 5, Pins("HPC:LA05_P"), IOStandard("LVTTL")),
    ("g", 6, Pins("HPC:LA05_N"), IOStandard("LVTTL")),
    ("g", 7, Pins("HPC:LA07_N"), IOStandard("LVTTL")),
    
    # HPC : JH
    ("in", 0, Pins("HPC:LA09_P"), IOStandard("LVTTL")),
    ("in", 1, Pins("HPC:LA09_N"), IOStandard("LVTTL")),
    ("in", 2, Pins("HPC:LA10_N"), IOStandard("LVTTL")),
    ("in", 3, Pins("HPC:LA16_P"), IOStandard("LVTTL")),
    ("in", 4, Pins("HPC:LA10_P"), IOStandard("LVTTL")),
    ("in", 5, Pins("HPC:LA11_P"), IOStandard("LVTTL")),
    ("in", 6, Pins("HPC:LA11_N"), IOStandard("LVTTL")),
    ("in", 7, Pins("HPC:LA16_N"), IOStandard("LVTTL")),

    # HPC : JI
    ("h", 0, Pins("HPC:LA29_N"), IOStandard("LVTTL")),
    ("h", 1, Pins("HPC:LA29_P"), IOStandard("LVTTL")),
    ("h", 2, Pins("HPC:LA25_N"), IOStandard("LVTTL")),
    ("h", 3, Pins("HPC:LA25_P"), IOStandard("LVTTL")),
    ("h", 4, Pins("HPC:LA28_N"), IOStandard("LVTTL")),
    ("h", 5, Pins("HPC:LA28_P"), IOStandard("LVTTL")),
    ("h", 6, Pins("HPC:LA24_N"), IOStandard("LVTTL")),
    ("h", 7, Pins("HPC:LA24_P"), IOStandard("LVTTL")),

    
    # HPC : JK
    ("dds_iorst", 0, Pins("HPC:LA31_P"), IOStandard("LVTTL")), # HPC : JK3
    ("dds_ioupdate", 0, Pins("HPC:LA32_N"), IOStandard("LVTTL")), # HPC : JK4
    ("dds_p0", 0, Pins("HPC:LA32_P"), IOStandard("LVTTL")), # HPC : JK5
    ("dds_p1", 0, Pins("HPC:LA30_N"), IOStandard("LVTTL")), # HPC : JK6
    ("dds_p2", 0, Pins("HPC:LA31_N"), IOStandard("LVTTL")), # HPC : JK7

    ("dds_spi", 0,  Subsignal("clk", Pins("HPC:LA33_N")), # HPC : JK0
                Subsignal("mosi", Pins("HPC:LA33_P")), # HPC : JK1
                Subsignal("miso", Pins("HPC:LA30_P")), # HPC : JK2
                IOStandard("LVTTL")),


    # LEDs on FMC LPC
    ("ledFrontPanel", 0, Pins("LPC:LA17_CC_N"), IOStandard("LVTTL")),
    ("ledFrontPanel", 1, Pins("LPC:LA17_CC_P"), IOStandard("LVTTL")),

    # Clock input/output on FMC LPC
    ("ext_clk0_p", 0, Pins("LPC:CLK0_M2C_P"), IOStandard("LVDS_25")),
    ("ext_clk0_n", 0, Pins("LPC:CLK0_M2C_N"), IOStandard("LVDS_25")),

    # LVDS2B on LPC
    ("tdc_in", 0,
        Subsignal("p", Pins("AJ26"), IOStandard("LVDS_25")),
        Subsignal("n", Pins("AK26"), IOStandard("LVDS_25"))
    ),

    # LVDS1B on LPC
    ("tdc_in", 1,
        Subsignal("p", Pins("AJ28"), IOStandard("LVDS_25")),
        Subsignal("n", Pins("AJ29"), IOStandard("LVDS_25"))
    ),
]