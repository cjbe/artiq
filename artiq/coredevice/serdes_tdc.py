import numpy

from artiq.language.core import *
from artiq.language.types import *
from artiq.coredevice.rtio import (rtio_output,
                                    rtio_input_timestamp,
                                   rtio_input_data_timeout)


class TDC:
    kernel_invariants = {"core", "channel"}

    def __init__(self, dmgr, channel, core_device="core"):
        self.core = dmgr.get(core_device)
        self.channel = channel

        # in RTIO cycles
        self.o_previous_timestamp = numpy.int64(0)
        self.i_previous_timestamp = numpy.int64(0)


    @kernel
    def _set_sensitivity(self, value):
        rtio_output(now_mu(), self.channel, 0, value)
        self.i_previous_timestamp = now_mu()

    @kernel
    def gate_rising_mu(self, duration):
        """Register rising edge events for the specified duration
        (in machine units).

        The time cursor is advanced by the specified duration."""
        self._set_sensitivity(1)
        delay_mu(duration)
        self._set_sensitivity(0)

    @kernel
    def gate_falling_mu(self, duration):
        """Register falling edge events for the specified duration
        (in machine units).

        The time cursor is advanced by the specified duration."""
        self._set_sensitivity(2)
        delay_mu(duration)
        self._set_sensitivity(0)

    @kernel
    def gate_both_mu(self, duration):
        """Register both rising and falling edge events for the specified
        duration (in machine units).

        The time cursor is advanced by the specified duration."""
        self._set_sensitivity(3)
        delay_mu(duration)
        self._set_sensitivity(0)

    @kernel
    def gate_rising(self, duration):
        """Register rising edge events for the specified duration
        (in seconds).

        The time cursor is advanced by the specified duration."""
        self._set_sensitivity(1)
        delay(duration)
        self._set_sensitivity(0)

    @kernel
    def gate_falling(self, duration):
        """Register falling edge events for the specified duration
        (in seconds).

        The time cursor is advanced by the specified duration."""
        self._set_sensitivity(2)
        delay(duration)
        self._set_sensitivity(0)

    @kernel
    def gate_both(self, duration):
        """Register both rising and falling edge events for the specified
        duration (in seconds).

        The time cursor is advanced by the specified duration."""
        self._set_sensitivity(3)
        delay(duration)
        self._set_sensitivity(0)


    @kernel
    def timedelta_mu(self):
        return rtio_input_data_timeout(self.i_previous_timestamp, self.channel)

    @kernel
    def timestamp_mu(self):
        return rtio_input_timestamp(self.i_previous_timestamp, self.channel)



