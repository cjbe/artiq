import logging
import serial
import time
import math


logger = logging.getLogger(__name__)


class TrapDac:
    # [dcEcNear, dcEcFar, dopComp, sigComp, vertComp, rfAtten]
    traps = {'loading': [5.0, 5.33, 37.5, 3.0, 158.5, 9.0], 
             'tight': [107.25, 112.25, -60.0, 9.0, 105.0, 4.0] }

    def __init__(self, addrDCInterface, addrRFInterface):
        self.dcIf = OldlabDCInterface(addrDCInterface)
        self.rfIf = OldlabRFAttenuatorInterface(addrRFInterface)
        
    def setTrap(self, trapName):
        """Set the DC and RF amplitudes to a given trap name"""
        if trapName not in self.traps:
            raise ValueError("Given trap name not in trap list")
        
        physDCVector = dcMixer(self.traps[trapName][0:5])
        rfAtten = self.traps[trapName][5]
        
        print("Setting DC...")
        self.dcIf.setAllDacChannels(physDCVector[0], physDCVector[1], physDCVector[2], physDCVector[3], physDCVector[4])
        print("Setting RF...")
        self.rfIf.setAtten(rfAtten)
        print("Done")
        
    def setTrapRaw(self, ecNear, ecFar):
        physDCVector = dcMixer(self.traps['loading'][0:5])
        physDCVector[0] = ecNear
        physDCVector[1] = ecFar
        self.dcIf.setAllDacChannels(physDCVector[0], physDCVector[1], physDCVector[2], physDCVector[3], physDCVector[4])
        
        
    def ping(self):
        return True


class TrapDacSim:
    def __init__(self):
        pass

    def setTrap(self, trapName):
        logger.warning("Going to trap '{}'".format(trapName))
        
    def ping(self):
        return True


def dacChannelMapping(logicalChannel):
    
    return mapping(logicalChannel)

# Maps a 'logical' vector of DC voltages to the 'physical' vector.
def dcMixer(inputVector):
    verticalCompensationVector = [0.000801256321392, -0.134061166991084, -0.017062918467318]
    dopplerCompensationVector = [0.468819184381041, 1.711511132021197, 0.024809294762018]
    sigmaCompensationVector = [-0.477674111263369, -1.743837680160108, 0.079653908484870]
    outputVector = [0]*5

    # Logical - physical mapping
    mapping = [0, 1, 2, 4, 3]

    # The two endcaps
    outputVector[mapping[0]] = inputVector[0]
    outputVector[mapping[1]] = inputVector[1]
    
    outputVector[mapping[2]] = dopplerCompensationVector[0]*inputVector[2] + sigmaCompensationVector[0]*inputVector[3] + verticalCompensationVector[0]*inputVector[4]
    outputVector[mapping[3]] = dopplerCompensationVector[1]*inputVector[2] + sigmaCompensationVector[1]*inputVector[3] + verticalCompensationVector[1]*inputVector[4]
    outputVector[mapping[4]] = dopplerCompensationVector[2]*inputVector[2] + sigmaCompensationVector[2]*inputVector[3] + verticalCompensationVector[2]*inputVector[4]
    print(outputVector)
    return outputVector




class OldlabDCInterface:
    def __init__(self, addr):
        self.ser = serial.Serial(addr, baudrate=115200)
        time.sleep(1)
    
    def setDacChannel(self, channel=0, value=0): # Sets a given DAC channel to a given value in Volts
        assert(channel>=0)
        assert(channel<5)

        self.ser.write('v {} {:3.3f}\n'.format(channel,value).encode())

    def setAllDacChannels(self, ch0=0, ch1=0, ch2=0, ch3=0, ch4=0): # Simultaneously set all DAC channels
        self.ser.write('va {:3.3f} {:3.3f} {:3.3f} {:3.3f} {:3.3f}\n'.format(ch0, ch1, ch2, ch3, ch4).encode())
    

class OldlabRFAttenuatorInterface:
    def __init__(self, addr):
        self.ser = serial.Serial(addr, baudrate=115200)
        #time.sleep(1)
    
    def setAtten(self, value=0):
        atten = math.floor( value*2 + 0.5)/2.0
        atten = min(atten,31.5)
        atten = max(atten,0)
        attenLSB = int(atten/0.5) # Attenutation value in hardware units of 0.5dB
        self.ser.write('atten {}\n'.format(attenLSB).encode())
    
    