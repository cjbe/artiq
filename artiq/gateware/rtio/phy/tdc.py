from migen import *

from artiq.gateware.rtio import rtlink


class Channel(Module):
    """RTIO phy for a single TDC channel.
    Output data is a 2-bit sensitivity (with same bit layout as ttl_*.Inout)
    Input data is the TDC fine time-stamp"""
    def __init__(self, tdc, channel=0):
        self.rtlink = rtlink.Interface(
            rtlink.OInterface(2),
            rtlink.IInterface(tdc.fp_count))
        self.probes = []

        # # #

        tdc_ch = tdc.channels[channel]

        sensitivity = Signal(2)

        self.sync.rio += If(self.rtlink.o.stb,
                            sensitivity.eq(self.rtlink.o.data))

        self.comb += [
            self.rtlink.i.stb.eq(
                tdc_ch.stb & 
                ( ((tdc_ch.pol==1) & sensitivity[0]) | ((tdc_ch.pol==0) & sensitivity[1]) )
            ),
            self.rtlink.i.data.eq( tdc_ch.fine )
        ]
