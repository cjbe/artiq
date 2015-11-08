import time
import serial
import logging

logger = logging.getLogger(__name__)



def _write_exactly(f, data):
    remaining = len(data)
    pos = 0
    while remaining:
        written = f.write(data[pos:])
        remaining -= written
        pos += written




class ArduinoDds:
    lsbAmp = 1.0 / 16383 # 0x3fff is maximum amplitude
    lsbPhase = 360.0 / 65536 # Degrees per LSB.
  
    def __init__(self, addr, clockFreq):
        # addr : serial port name
        # clockFreq : clock frequency in Hz
        
        self.ser = serial.Serial(addr, baudrate=115200)
        self.lsbFreq = clockFreq / (2**32);
        self.clockFreq = clockFreq
        time.sleep(5)
        logger.info("Connected to ArduinoDDS with ID '{}'".format(self.identity()))
    
    
    def send(self, data):
        self.ser.write(data.encode())

    
    def setProfile(self, profile, freq, phase=0.0, amp=1.0):
        """Sets a DDS profile frequency (Hz), phase (degrees), and amplitude (full-scale).
        phase defaults to 0 and amplitude defaults to 1"""
        if amp < 0 or amp > 1:
            raise ValueError("DDS amplitude must be between 0 and 1")
        if freq < 0 or freq > 450e6: # This should be dependant on the clock frequency
            raise ValueError("DDS frequency must be between 0 and 450 MHz")
        
        ampWord = int(round( amp / self.lsbAmp ))
        phaseWord = int(round( (phase % 360.0) / self.lsbPhase ))
        freqWord = int(round( freq / self.lsbFreq ))
        self.setProfileLSB(profile, freqWord, phaseWord, ampWord)
        
    
    def setProfileLSB(self, profile, freq, phase, amp): # Freq, phase, amp are all in units of lsb
        if profile < 0 or profile > 7 or not isinstance(profile, int):
            raise ValueError("DDS profile should be an integer between 0 and 7")
        if amp > 0x3fff or amp < 0 or not isinstance(amp, int):
            raise ValueError("DDS amplitude word should be an integer between 0 and 0x3fff")
        if phase > 0xffff or phase < 0 or not isinstance(phase, int):
            raise ValueError("DDS phase word should be an integer between 0 and 0xffff")
        if freq < 0 or freq > 0xffffffff or not isinstance(freq, int):
            raise ValueError("DDS frequency word should be an integer between 0 and 0xffffffff")
        
        self.send('PLSB {} {} {} {}\n'.format( profile, amp, phase, freq) );

    def reset(self):
        self.send("reset\n")
        
    def identity(self):
        self.send("*IDN?\n")
        return self.ser.readline().decode().strip()

    def ping(self):
        return True


class ArduinoDdsSim:
    lsbAmp = 1.0 / 16383 # 0x3fff is maximum amplitude
    lsbPhase = 360.0 / 65536 # Degrees per LSB.
    lsbFreq = (2**32) / 1e9
  
    def __init__(self):
        pass
    
    def setProfile(self, profile, freq, phase=0.0, amp=1.0):
        pass
    
    def setProfileLSB(self, profile, freq, phase, amp): # Freq, phase, amp are all in units of lsb
        pass

    def reset(self):
        pass
        
    def identity(self):
        return "ident"

    def ping(self):
        return True