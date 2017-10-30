from migen import *

from artiq.gateware.rtio import rtlink


class Input(Module):
    def __init__(self, phy_sig=None, phy_ref=None):
        self.rtlink = rtlink.Interface(
            rtlink.OInterface(2, 2),
            rtlink.IInterface(1))
        # # #

        sensitivity = Signal(2)

        self.sync.rio += [
            If(self.rtlink.o.stb & self.rtlink.o.address[1],
                sensitivity.eq(self.rtlink.o.data))
        ]

        self.comb += [
            self.rtlink.i.stb.eq(sensitivity[0] | sensitivity[1]),
            self.rtlink.i.data.eq(1)
        ]


class TDC(Module):
    def __init__(self, phy_sig=None, phy_ref=None, n_counter=14):
        """Simple TDC that connects to the ISERDES of two ttl_serdes_generic
        phys. 
        Records (as RTIO input event data) the time difference between rising/falling
        edges on the reference input and the signal input.
        The gating logic similar to the TTL Input logic, with selectable rising/falling/both
        sensitivity.
        All edges on the signal input preceeding the first edge on the reference in a given
        gate window are ignored.

        n_counter: width of time difference in RTIO clock LSB"""
        self.rtlink = rtlink.Interface(
            rtlink.OInterface(2),
            rtlink.IInterface(n_counter, timestamped=False))
        # # #

        sensitivity = Signal(2)
        gate_open = Signal()
        gate_open_d = Signal()

        self.sync.rio += If(self.rtlink.o.stb,
                            sensitivity.eq(self.rtlink.o.data))

        self.comb += gate_open.eq( sensitivity != 0 )
        self.sync.rio += gate_open_d.eq( gate_open)

        stb_sig = Signal()
        stb_ref = Signal()
        self.comb += [
            stb_sig.eq( (sensitivity[0] & phy_sig.stb_rising) |
                        (sensitivity[1] & phy_sig.stb_falling) ),
            stb_ref.eq( (sensitivity[0] & phy_ref.stb_rising) |
                        (sensitivity[1] & phy_ref.stb_falling) ),
        ]

        counter = Signal(n_counter-len(phy_sig.fine_ts))
        ref_fine_ts = Signal(len(phy_sig.fine_ts))
        ref_valid = Signal()
        self.sync.rio += [
            counter.eq(counter+1),
            If(gate_open & ~gate_open_d,
                ref_valid.eq(0)),
            If(stb_ref,
                counter.eq(0),
                ref_valid.eq(1),
                ref_fine_ts.eq(phy_ref.fine_ts)),
        ]

        fine_ts_diff = Signal(len(phy_sig.fine_ts))
        self.comb += [
            self.rtlink.i.stb.eq(stb_sig & ref_valid),
            fine_ts_diff.eq(phy_sig.fine_ts-ref_fine_ts),
            self.rtlink.i.data.eq( Cat(fine_ts_diff, counter) ),
        ]
