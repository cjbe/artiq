import logging
import serial
import re

logger = logging.getLogger(__name__)


class PiezoController:
    """Driver for Thorlabs MDT693B 3 channel open-loop piezo controller."""

    channels = ['x', 'y', 'z']

    def __init__(self, serial_addr):
        if serial_addr is None:
            self.simulation = True
        else:
            self.simulation = False
            self.port = serial.Serial(
                serial_addr,
                baudrate=115200,
                rtscts=True,
                timeout=0.1)

        self.vLimit = self.get_voltage_limit()
        logger.info("Device vlimit is {}".format(self.vLimit))

    def close(self):
        """Close the serial port."""
        if not self.simulation:
            self.port.close()

    def _send_command(self, cmd):
        if self.simulation:
            print(cmd)
            return None
        else:
            self.port.write((cmd+'\r').encode())

    def _read_line(self):
        """Read a CR terminated line. Returns '' on timeout"""
        s = ''
        while len(s) == 0 or s[-1] != '\r':
            c = self.port.read().decode()
            if c == '': # Timeout
                break
            s += c
        return s

    def _read_bracketed(self):
        """Reads until a string enclosed in square brackets is found, and returns it."""
        line = self._read_line()
        while line != '':
            match = re.search("\[(.*)\]", line)
            if match:
                return match.group(1)
            line = self._read_line()
        raise IOError("Timeout while reading bracketed string")

    def get_serial(self):
        """Returns the device serial string."""
        self._send_command('id?')
        line = self._read_line()
        while line != '':
            match = re.search("Serial#:(.*)", line)
            if match:
                return match.group(1).strip()
            line = self._read_line()
        # If we get here we got a timeout
        raise IOError("Timeout while reading serial string")

    def get_id(self):
        """Returns the identity paragraph that include the device model, serial number, and firmware version. 
        This function needs to wait for a serial timeout, hence is a little slow"""
        # Due to the crappy Thorlabs protocol (no clear finish marker) we have to wait for a timeout to ensure that we have read everything
        self._send_command('id?')
        s = ''
        line = self._read_line()
        while line != '':
            s += line
            line = self._read_line()
        return s.replace('\r', '\n')

    def set_channel(self, channel, voltage):
        """Set a channel (one of 'x','y','z') to a given voltage."""
        self._check_valid_channel(channel)
        self._check_voltage_in_limit(voltage)
        self._send_command("{}voltage={}".format( channel, voltage))

    def get_channel(self, channel):
        """Returns the current output voltage for a given channel (one of 'x','y','z').
        Note that this may well differ from the set voltage by a few volts due to ADC
        and DAC offsets."""
        self._check_valid_channel(channel)
        self._send_command("{}voltage?".format(channel))
        return float( self._read_bracketed() )

    def get_voltage_limit(self):
        """Returns the output limit setting in Volts (one of 75V, 100V, 150V, set by
        the switch on the device back panel)"""
        str = self._send_command("vlimit?")
        return float( self._read_bracketed() )

    def _check_valid_channel(self, channel):
        """Raises a ValueError if the channel is not valid"""
        if channel not in self.channels:
            raise ValueError("Channel must be one of 'x', 'y', or 'z'")

    def _check_voltage_in_limit(self, voltage):
        """Raises a ValueError if the voltage is not in limit for the current
        controller settings"""
        if voltage > self.vLimit or voltage < 0:
            raise ValueError("Voltage must be between 0 and vlimit={}".format(self.vLimit))

    def ping(self):
        self.get_voltage_limit()
        return True
