from artiq.language.core import *


class UwaveDdsWrapper:
    """Wraps an Arduino DDS class to allow profiles to be set in logical frequencies (detunings from zero field) rather than the physical frequencies that are the input to the mixup chain"""
    def __init__(self, dmgr, device, LOfrequency):
        self.core = dmgr.get("core")

        self.dds = dmgr.get(device)

        zeroFieldFrequency = 3225.608e6 # S1/2 F=4 - F=3 splitting at zero field, Hz
        
        # To get the DDS frequency, subtract off target frequency from this offset frequency
        self.offsetFrequency = LOfrequency - zeroFieldFrequency
    

    def setProfile(self, profile, freq, phase=0.0, amp=1.0):
        freqDDS = self.offsetFrequency - freq
        
        self.dds.setProfile(profile, freqDDS, phase, amp)