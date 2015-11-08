# Test trapDac
from driver import *

dev = TrapDac('/dev/arduino_64935343233351B07032', '/dev/arduino_6493534353335160C011')


#dev.setTrap('loading')
dev.setTrap('tight')