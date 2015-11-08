import time
from driver import *
#["hwgrep://USB VID:PID=1313:1003 SNR=150706175404",
serDevs = ["hwgrep://USB VID:PID=1313:1003 SNR=150212175407"]

devs = [ PiezoController(ser) for ser in serDevs]

v  = 10.0


for i, dev in enumerate(devs):
    print("Device {}:".format(i))
    #print( dev.get_serial() )
    #print( dev.get_name() )
    #print( dev.get_voltage_limit() )
    #time.sleep(1)
    for ch in ['x', 'y', 'z']:
        #dev.set_channel(ch, v)
        v += 10.0
        print("{} = {}".format(ch, dev.get_channel(ch)))