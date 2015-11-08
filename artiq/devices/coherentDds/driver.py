import logging
import serial
import math


logger = logging.getLogger(__name__)


class CoherentDds:
    ser = None;
    lsbAmp = 1.0 / 16383 # 0x3fff is maximum amplitude
    lsbPhase = 360.0 / 65536 # Degrees per LSB.
  
    def __init__(self, addr, clockFreq):
        # addr : serial port name
        # clockFreq : clock frequency in Hz
        
        self.ser = serial.Serial(addr, baudrate=115200)
        self.lsbFreq = clockFreq / (2**32);
        self.clockFreq = clockFreq

        
        # Write a trivial pulse shape to /disable/ pulse shaping (the VGA is always at max)
        self.setPulseShape(0, [1]);
    
    def send(self, data):
        self.ser.write(data.encode())
    
    def identity(self):
        """Returns a string representing the firmware name and version"""
        self.send('idn?\n')
        return self.ser.readline().decode().strip()
        
    
    def resetPhase(self):    
        self.send('resetPhase\n');
    
    def setProfile(self, channel, profile, freq, phase=0.0, amp=1.0):
        """Sets a DDS profile frequency (Hz), phase (degrees), and amplitude (full-scale).
        phase defaults to 0 and amplitude defaults to 1"""
        if amp < 0 or amp > 1:
            raise ValueError("DDS amplitude must be between 0 and 1")
        if freq < 0 or freq > 450e6: # This should be dependant on the clock frequency
            raise ValueError("DDS frequency must be between 0 and 450 MHz")
        
        ampWord = int(round( amp * 0x3fff ))
        phaseWord = int(round( (phase % 360) / 360.0 * 0xffff ))
        freqWord = int(round( freq / self.lsbFreq ))
        self.setProfileWords(channel, profile, freqWord, phaseWord, ampWord)
    
    def setProfileWords(self, channel, profile, freq, phase, amp): # Freq, phase, amp are all in units of lsb
        if channel < 0 or channel > 3 or not isinstance(channel, int):
            raise ValueError("DDS channel should be an integer between 0 and 3")
        if profile < 0 or profile > 7 or not isinstance(profile, int):
            raise ValueError("DDS profile should be an integer between 0 and 7")
        if amp > 0x3fff or amp < 0 or not isinstance(amp, int):
            raise ValueError("DDS amplitude word should be an integer between 0 and 0x3fff")
        if phase > 0xffff or phase < 0 or not isinstance(phase, int):
            raise ValueError("DDS phase word should be an integer between 0 and 0xffff")
        if freq < 0 or freq > 0xffffffff or not isinstance(freq, int):
            raise ValueError("DDS frequency word should be an integer between 0 and 0xffffffff")
        
        self.send('setProfile {} {} {} {} {}\n'.format( channel, profile, freq, phase, amp) );

    def reset(self):
        self.send('reset\n');
        time.sleep(50e-3);

    def setPulseShape(self, shapeChannel, shapeVec):
        if shapeChannel < 0 or shapeChannel > 3 or not isinstance(shapeChannel, int):
            raise ValueError("DDS pulse shape channel should be an integer between 0 and 3")
        if len(shapeVec) < 1 or len(shapeVec) > 2048:
            raise ValueError("DDS pulse shape array length should be between 1 and 2048")
        
        quantisedShapeVec = []
        for el in shapeVec:
            quantisedEl = round(el*0x3fff)
            if quantisedEl < 0 or quantisedEl > 0x3fff:
                raise ValueError("DDS pulse shape points should all be between 0.0 and 1.0")
            quantisedShapeVec.append(quantisedEl)
        
        self.send('setPulseShape {}\n'.format(shapeChannel))
        for i in range(len(quantisedShapeVec)):
            self.send('%d' % quantisedShapeVec[i]);
            if i != len(quantisedShapeVec)-1:
                self.send(',');
        self.send('\n');

    #def setSensiblePulseShape(self, duration):
    #    """Sets a sensible looking pulse shape with total duration 'duration' seconds. The duration must be between 0 and 10us"""
    #    if duration > 10e-6 or duration < 0:
    #        raise ValueError("DDS pulse shape duration must be between 0 and 10us")
    #    

    def ping(self):
        return True




class CoherentDdsSim:
    def __init__(self):
        pass

    def identity(self):
        return "coherentdds simulation"
            
    def resetPhase(self):  
        logger.warning("Resetting phase")
        pass
    
    def setProfile(self, channel, profile, freq, phase=0.0, amp=1.0):
        logger.warning("Setting ch:p {}:{} to freq={}, phase={}, amp={}".format(channel,profile,freq,phase,amp))
        pass
    
    def setProfileWords(self, channel, profile, freq, phase, amp): # Freq, phase, amp are all in units of lsb
        pass

    def reset(self):
        pass

    def setPulseShape(self, shapeChannel, shapeVec):
        pass
    
    def ping(self):
        return True