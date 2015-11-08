from driver import *


dev = CoherentDds('/dev/milldown_1', 1e9)

for i in range(8):
    dev.setProfile(0, i, 200e6)
    dev.setProfile(1, i, 200e6)
dev.setProfile(3, 0, 38.5e6)
dev.resetPhase()



print("ID : {}".format(dev.identity()))

print("All done")