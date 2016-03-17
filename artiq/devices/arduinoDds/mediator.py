from artiq.language.core import *
from artiq.language.units import *


class ProfileSwitcher:
    def __init__(self, dmgr, device, profile_lines, interProfileDelay=200*ns, finalDelay=200*ns):
        """interProfileDelay is the delay to insert between switching profile lines.
        finalDelay is the delay to add after all profile changes have occured.
        Profile line order is [p0, p1, p2]"""
        self.core = dmgr.get("core")
        self.device = dmgr.get(device)
        
        self.p0 = dmgr.get(profile_lines[0])
        self.p1 = dmgr.get(profile_lines[1])
        self.p2 = dmgr.get(profile_lines[2])
        
        self.interProfileDelay_mu = seconds_to_mu(interProfileDelay, self.core)
        self.finalDelay_mu = seconds_to_mu(finalDelay_mu, self.core)

        
    @kernel
    def setProfile(self, profile):
        if profile < 0 or profile > 7:
            raise InvalidProfile()
        
        if profile & 0x4:
            self.p2.on()
        else:
            self.p2.off()
        delay(self.interProfileDelay_mu*ns)      
      
        if profile & 0x2:
            self.p1.on()
        else:
            self.p1.off()
        delay(self.interProfileDelay_mu*ns)
        
        if profile & 0x1:
            self.p0.on()
        else:
            self.p0.off()
        delay(self.finalDelay_mu)        
        

class InvalidProfile(Exception):
    pass
