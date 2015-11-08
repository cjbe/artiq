from driver import * 
import time


dev = OldlabRFAttenuatorInterface('/dev/arduino_6493534353335160C011')

time.sleep(10)

while True:
    dev.setAtten(10)
    time.sleep(2)
    dev.setAtten(20)
    time.sleep(2)