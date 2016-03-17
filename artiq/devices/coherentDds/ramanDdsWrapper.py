from artiq.language.core import *


class RamanDdsWrapper:
    """Wraps a CoherentDDS class to allow profiles to be set in logical frequencies (detunings from zero field) rather than the physical frequencies that are the input to the Raman AOMs.
    This class is very ugly at the moment as it hardcodes the arrangement of our AOM (inc. the diffraction orders)."""
    def __init__(self, dmgr, device, LO_freq, Rh_freq):
        """LO_freq : blue beat note frequency between master and slave laser"""
        self.core = dmgr.get("core")

        self.dds = dmgr.get(device)

        zeroFieldFrequency = 3225.608e6 # S1/2 F=4 - F=3 splitting at zero field, Hz
        
        # To drive a transition at  zeroFieldFrequency+f we need to drive the
        # Rpara or Rv AOM at: offsetFrequency+driveSign*f
        self.offsetFrequency = (LO_freq+Rh_freq) - zeroFieldFrequency
        self.driveSign = -1
    

    def setProfile(self, channel, profile, freq, phase=0.0, amp=1.0):
        freqDDS = self.offsetFrequency + self.driveSign*freq
        
        if channel == 0:
            # channel 0 is Rpara, which is double passed
            freqDDS /= 2
            phase /= 2
        
        self.dds.setProfile(channel, profile, freqDDS, phase=phase, amp=amp)
