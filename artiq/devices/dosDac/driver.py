import logging
import serial
import time

logger = logging.getLogger(__name__)


class DosDac:
    dacMap = {
        'Btrim': 0,
        'D40Pwr': 5,
        '397/40f': 6,
        '397/43f': 7,
        '866freq': 8,
        '393freq': 9,
        '850freq': 10
    }
    
    def __init__(self, addr):
        self.dev = DosDacInterface(addr)
        
        self.currentValues = [self.getDac(self.dacMap[dacName]) for dacName in self.dacMap]
    
    
    def setDac(self, channel, value):
        if isinstance(channel,int):
            channelNum = channel
        elif channel in self.dacMap:
            channelNum = self.dacMap[channel]
        else:
            raise ValueError("DAC channel must either be a valid channel name or a channel number")
        # Should check for validity of 'value' here
        
        # The following is a hacky 'slow-scan'
        if channelNum != 0: # Exclude Btrim
            currentVal = self.currentValues[self.dacMap[channel]]
            sign = (currentVal-value) / abs(currentVal-value)
            while abs(currentVal-value) > 50:
                currentVal -= sign*50
                self.dev.setDac(channelNum,int(currentVal))
                time.sleep(50e-3)
                
        self.currentValues[self.dacMap[channel]] = int(value)
        self.dev.setDac(channelNum,int(value))
    
    def getDac(self,channel):
        if isinstance(channel,int):
            channelNum = channel
        elif channel in self.dacMap:
            channelNum = self.dacMap[channel]
        else:
            raise ValueError("DAC channel must either be a valid channel name or a channel number")
        return self.dev.getDac(channelNum)

    def ping(self):
        return True



class DosDacSim:
    dacMap = {
        'Btrim': 0,
        'RpHpzt': 1,
        'RpVpzt': 2,
        'RvHpzt': 3,
        'RvVpzt': 4,
        'D40Pwr': 5,
        '397/40f': 6,
        '397/43f': 7,
        '866freq': 8,
        '393freq': 9,
        '850freq': 10
    }
    
    def __init__(self):
        pass
    
    def setDac(self, channel, value):
        pass
    
    def getDac(self,channel):
        return 666

    def ping(self):
        return True




# The direct hardware interface class
class DosDacInterface:
    def __init__(self, addr):
        self.ser = serial.Serial(addr, baudrate=115200)
    
    def setDac(self, channel, value): # Sets a given DAC to a given value in mV
        if channel < 0 or channel > 10 or not isinstance(channel,int):
            raise ValueError("DAC channel must be a number between 0 and 10")
        self.ser.write('S {:02} {}\n'.format(channel,int(value)).encode())
        
    def getDac(self, channel):
        self.ser.flushInput()
        if channel < 0 or channel > 10 or not isinstance(channel,int):
            raise ValueError("DAC channel must be a number between 0 and 10")
        self.ser.write('G {:02}\n'.format(channel).encode())
        return int(self.ser.readline().decode())
    
    