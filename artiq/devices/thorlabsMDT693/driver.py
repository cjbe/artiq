import logging
import serial
import time

logger = logging.getLogger(__name__)


class PiezoController:
    """Driver for Thorlabs MDT693B 3 channel open-loop piezo controller."""

    channels = ['x', 'y', 'z']

    def __init__(self, serial_addr):
        if serial_addr is None:
            self.simulation = True
        else:
            self.simulation = False
            self.port = serial.serial_for_url(
                serial_addr,
                baudrate=115200,
                rtscts=True,
                timeout=1.0)

        # Turn off echo mode
        self._send_command("echo=0")

        self.vLimit = self.get_voltage_limit()
        logger.info("Device vlimit is {}".format(self.vLimit))

    def _send_command(self, cmd, response=False):
        if self.simulation:
            print(cmd)
            return None
        else:
            self.port.flushInput()
            self.port.write((cmd+"\n").encode())
            print("Sent {}".format((cmd+"\n").encode()))
            # If the command does not generate a response, the device returns '*' after the command 
            # is executed, else the commands returns a string, terminated in '\r*'
            endStr = "\r*" if response else "*"
            return self._read_response(endStr)
            
            
    def _read_response(self, endStr="\r*"):
        # This devices can return multi-line responses, but always returns
        # '\r*' at the end of the response string
        buf = bytes()
        while True:
            char = self.port.read(1)
            buf += char
            print("b = {}".format(buf))
            if buf.endswith(endStr.encode()):
                break
        print("buf = {}".format(buf))
        return buf.decode()

    def close(self):
        """Close the serial port."""
        if not self.simulation:
            self.port.close()

    def get_serial(self):
        """Returns the device serial string."""
        str = self._send_command("serial?", response=True)
        return str.strip()[0:-2]

    def set_name(self, name):
        """Sets the friendly name of the device."""
        self._send_command("friendly={}".format(name))

    def get_name(self):
        """Returns the friendly name of the device."""
        str = self._send_command("friendly?", response=True)
        return str.strip()[0:-2]

    def set_channel(self, channel, voltage):
        """Set a channel (one of 'x','y','z') to a given voltage."""
        self._check_valid_channel(channel)
        self._check_voltage_in_limit(voltage)
        self._send_command("{}voltage={}".format(channel, voltage))

    def get_channel(self, channel):
        """Returns the current output voltage for a given channel (one of 'x','y','z').
        Note that this may well differ from the set voltage by a few volts due to ADC
        and DAC offsets."""
        self._check_valid_channel(channel)
        str = self._send_command("{}voltage?".format(channel), response=True)
        return float(str.strip()[2:-3])

    def get_voltage_limit(self):
        """Returns the output voltage limit setting (one of 75V, 100V, 150V, set by
        the switch on the device back panel"""
        str = self._send_command("vlimit?", response=True)
        return int(str.strip()[2:-3])

    def _check_voltage_in_limit(self, voltage):
        """Raises a ValueError if the voltage is not in limit for the current
        controller settings"""
        if voltage > self.vLimit or voltage < 0:
            raise ValueError("Voltage must be between 0 and vlimit={}".format(self.vLimit))

    def _check_valid_channel(self, channel):
        """Raises a ValueError if the channel is not valid"""
        if channel not in self.channels:
            raise ValueError("Channel must be one of 'x', 'y', or 'z'")

    def ping(self):
        self.get_serial()
        return True
