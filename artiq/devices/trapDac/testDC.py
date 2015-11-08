from driver import * 
import time


dev = OldlabDCInterface('/dev/arduino_64935343233351B07032')

time.sleep(1)

#dev.setAllDacChannels(ch0=10,ch1=20,ch2=30,ch3=40,ch4=50)

for i in range(5):
    dev.setDacChannel(i,i)