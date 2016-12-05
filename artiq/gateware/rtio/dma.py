from migen import *
from migen.genlib.record import Record, layout_len
from migen.genlib.fsm import FSM
from misoc.interconnect.csr import *
from misoc.interconnect import stream, wishbone

from artiq.gateware.rtio import cri


class WishboneReader(Module):
    def __init__(self, bus=None):
        if bus is None:
            bus = wishbone.Interface
        self.bus = bus

        aw = len(bus.adr)
        dw = len(bus.dat_w)        
        self.sink = stream.Endpoint([("address", aw)])
        self.source = stream.Endpoint([("data", dw)])

        # # #

        bus_stb = Signal()
        data_reg_loaded = Signal()

        self.comb += [
            bus_stb.eq(self.sink.stb & (~data_reg_loaded | self.source.ack)),
            bus.cyc.eq(bus_stb),
            bus.stb.eq(bus_stb),
            bus.adr.eq(self.sink.address),
            self.sink.ack.eq(bus.ack),
            self.source.stb.eq(data_reg_loaded),
        ]
        self.sync += [
            If(self.source.ack, data_reg_loaded.eq(0)),
            If(bus.ack,
                data_reg_loaded.eq(1),
                self.source.data.eq(bus.dat_r),
                self.source.eop.eq(self.sink.eop)
            )
        ]


class DMAReader(Module, AutoCSR):
    def __init__(self, membus, enable):
        aw = len(membus.adr)
        data_alignment = log2_int(len(membus.dat_w)//8)

        self.submodules.wb_reader = WishboneReader(membus)
        self.source = self.wb_reader.source

        # All numbers in bytes
        self.base_address = CSRStorage(aw + data_alignment,
                                       alignment_bits=data_alignment)

        # # #

        enable_r = Signal()
        address = self.wb_reader.sink
        self.sync += [
            enable_r.eq(enable),
            If(enable & ~enable_r,
                address.address.eq(self.base_address.storage),
                address.eop.eq(0),
                address.stb.eq(1),
            ),
            If(address.stb & address.ack,
                If(address.eop,
                    address.stb.eq(0)
                ).Else(
                    address.address.eq(address.address + 1),
                    If(~enable, address.eop.eq(1))
                )
            )
        ]


class RawSlicer(Module):
    def __init__(self, in_size, out_size, granularity):
        g = granularity

        self.sink = stream.Endpoint([("data", in_size*g)])
        self.source = Signal(out_size*g)
        self.source_stb = Signal()
        self.source_consume = Signal(max=out_size+1)
        self.flush = Signal()
        self.flush_done = Signal()

        # # #

        # worst-case buffer space required (when loading):
        #          <data being shifted out>   <new incoming word>
        buf_size =       out_size - 1       +       in_size
        buf = Signal(buf_size*g)
        self.comb += self.source.eq(buf[:out_size*8])

        level = Signal(max=buf_size+1)
        next_level = Signal(max=buf_size+1)
        self.sync += level.eq(next_level)
        self.comb += next_level.eq(level)

        load_buf = Signal()
        shift_buf = Signal()

        self.sync += [
            If(load_buf, Case(level,
                {i: buf[i*g:(i+in_size)*g].eq(self.sink.data)
                 for i in range(out_size)})),
            If(shift_buf, buf.eq(buf >> self.source_consume*g))
        ]

        fsm = FSM(reset_state="FETCH")
        self.submodules += fsm

        fsm.act("FETCH",
            self.sink.ack.eq(1),
            load_buf.eq(1),
            If(self.sink.stb,
                next_level.eq(level + in_size)
            ),
            If(next_level >= out_size, NextState("OUTPUT"))
        )
        fsm.act("OUTPUT",
            self.source_stb.eq(1),
            shift_buf.eq(1),
            next_level.eq(level - self.source_consume),
            If(next_level < out_size, NextState("FETCH")),
            If(self.flush, NextState("FLUSH"))
        )
        fsm.act("FLUSH",
            next_level.eq(0),
            self.sink.ack.eq(1),
            If(self.sink.stb & self.sink.eop,
                self.flush_done.eq(1),
                NextState("FETCH")
            )
        )


# end marker is a record with length=0
record_layout = [
    ("length", 8),  # of whole record (header+data)
    ("channel", 24),
    ("timestamp", 64),
    ("address", 16),
    ("data", 512)  # variable length
]


class RecordConverter(Module):
    def __init__(self, stream_slicer):
        self.source = stream.Endpoint(record_layout)
        self.end_marker_found = Signal()
        self.flush = Signal()

        record_raw = Record(record_layout)
        self.comb += [
            record_raw.raw_bits().eq(stream_slicer.source),
            self.source.channel.eq(record_raw.channel),
            self.source.timestamp.eq(record_raw.timestamp),
            self.source.address.eq(record_raw.address),
            self.source.data.eq(record_raw.data)
        ]

        fsm = FSM(reset_state="FLOWING")
        self.submodules += fsm

        fsm.act("FLOWING",
            If(stream_slicer.source_stb,
                If(record_raw.length == 0,
                    NextState("END_MARKER_FOUND")
                ).Else(
                    self.source.stb.eq(1)
                )
            ),
            If(self.source.ack,
                stream_slicer.source_consume.eq(record_raw.length)
            )
        )
        fsm.act("END_MARKER_FOUND",
            self.end_marker_found.eq(1),
            If(self.flush,
                stream_slicer.flush.eq(1),
                NextState("WAIT_FLUSH")
            )
        )
        fsm.act("WAIT_FLUSH",
            If(stream_slicer.flush_done,
                NextState("SEND_EOP")
            )
        )
        fsm.act("SEND_EOP",
            self.source.eop.eq(1),
            self.source.stb.eq(1),
            If(self.source.ack, NextState("FLOWING"))
        )


class RecordSlicer(Module):
    def __init__(self, in_size):
        self.submodules.raw_slicer = ResetInserter()(RawSlicer(
            in_size//8, layout_len(record_layout)//8, 8))
        self.submodules.record_converter = RecordConverter(self.raw_slicer)

        self.end_marker_found = self.record_converter.end_marker_found
        self.flush = self.record_converter.flush

        self.sink = self.raw_slicer.sink
        self.source = self.record_converter.source


class TimeOffset(Module, AutoCSR):
    def __init__(self):
        self.time_offset = CSRStorage(64)
        self.source = stream.Endpoint(record_layout)
        self.sink = stream.Endpoint(record_layout)

        # # #

        pipe_ce = Signal()
        self.sync += \
            If(pipe_ce,
                self.sink.payload.connect(self.source.payload,
                                          leave_out={"timestamp"}),
                self.source.payload.timestamp.eq(self.sink.payload.timestamp
                                                 + self.time_offset.storage),
                self.source.eop.eq(self.sink.eop),
                self.source.stb.eq(self.sink.stb)
            )
        self.comb += [
            pipe_ce.eq(self.source.ack | ~self.source.stb),
            self.sink.ack.eq(pipe_ce)
        ]


class CRIMaster(Module, AutoCSR):
    def __init__(self):
        self.arb_req = CSRStorage()
        self.arb_gnt = CSRStatus()

        self.error_status = CSRStatus(5)  # same encoding as RTIO status
        self.error_underflow_reset = CSR()
        self.error_sequence_error_reset = CSR()
        self.error_collision_reset = CSR()
        self.error_busy_reset = CSR()

        self.error_channel = CSRStatus(24)
        self.error_timestamp = CSRStatus(64)
        self.error_address = CSRStatus(16)

        self.sink = stream.Endpoint(record_layout)
        self.cri = cri.Interface()
        self.busy = Signal()

        # # #

        self.comb += [
            self.cri.arb_req.eq(self.arb_req.storage),
            self.arb_gnt.status.eq(self.cri.arb_gnt)
        ]

        error_set = Signal(4)
        for i, rcsr in enumerate([self.error_underflow_reset, self.error_sequence_error_reset,
                                  self.error_collision_reset, self.error_busy_reset]):
            # bit 0 is RTIO wait and always 0 here
            bit = i + 1
            self.sync += [
                If(error_set[i],
                    self.error_status.status[bit].eq(1),
                    self.error_channel.status.eq(self.sink.channel),
                    self.error_timestamp.status.eq(self.sink.timestamp),
                    self.error_address.status.eq(self.sink.address)
                ),
                If(rcsr.re, self.error_status.status[bit].eq(0))
            ]

        self.comb += [
            self.cri.chan_sel.eq(self.sink.channel),
            self.cri.o_timestamp.eq(self.sink.timestamp),
            self.cri.o_address.eq(self.sink.address),
            self.cri.o_data.eq(self.sink.data)
        ]

        fsm = FSM(reset_state="IDLE")
        self.submodules += fsm

        fsm.act("IDLE",
            If(self.error_status.status == 0,
                If(self.sink.stb,
                    If(self.sink.eop,
                        # last packet contains dummy data, discard it
                        self.sink.ack.eq(1)
                    ).Else(
                        NextState("WRITE")
                    )
                )
            ).Else(
                # discard all data until errors are acked
                self.sink.ack.eq(1)
            )
        )
        fsm.act("WRITE",
            self.busy.eq(1),
            self.cri.cmd.eq(cri.commands["write"]),
            NextState("CHECK_STATE")
        )
        fsm.act("CHECK_STATE",
            self.busy.eq(1),
            If(~self.cri.o_status,
                self.sink.ack.eq(1),
                NextState("IDLE")
            ),
            If(self.cri.o_status[1], NextState("UNDERFLOW")),
            If(self.cri.o_status[2], NextState("SEQUENCE_ERROR")),
            If(self.cri.o_status[3], NextState("COLLISION")),
            If(self.cri.o_status[4], NextState("BUSY"))
        )
        for n, name in enumerate(["UNDERFLOW", "SEQUENCE_ERROR",
                                  "COLLISION", "BUSY"]):
            fsm.act(name,
                self.busy.eq(1),
                error_set.eq(1 << n),
                self.cri.cmd.eq(cri.commands["o_" + name.lower() + "_reset"]),
                self.sink.ack.eq(1),
                NextState("IDLE")
            )


class DMA(Module):
    def __init__(self, membus):
        self.enable = CSRStorage(write_from_dev=True)

        self.submodules.dma = DMAReader(membus, self.enable.storage)
        self.submodules.slicer = RecordSlicer(len(membus.dat_w))
        self.submodules.time_offset = TimeOffset()
        self.submodules.cri_master = CRIMaster()
        self.cri = self.cri_master.cri

        self.comb += [
            self.dma.source.connect(self.slicer.sink),
            self.slicer.source.connect(self.time_offset.sink),
            self.time_offset.source.connect(self.cri_master.sink)
        ]

        fsm = FSM(reset_state="IDLE")
        self.submodules += fsm

        self.comb += self.enable.dat_w.eq(0)

        fsm.act("IDLE",
            If(self.enable.storage, NextState("FLOWING"))
        )
        fsm.act("FLOWING",
            If(self.slicer.end_marker_found, self.enable.we.eq(1)),
            If(~self.enable.storage,
                self.slicer.flush.eq(1),
                NextState("WAIT_EOP")
            )
        )
        fsm.act("WAIT_EOP",
            If(self.cri_master.sink.stb & self.cri_master.sink.ack & self.cri_master.sink.eop,
                NextState("WAIT_CRI_MASTER")
            )
        )
        fsm.act("WAIT_CRI_MASTER",
            If(~self.cri_master.busy, NextState("IDLE"))
        )

    def get_csrs(self):
        return ([self.enable, self.busy] +
                self.dma.get_csrs() + self.time_offset.get_csrs() +
                self.cri_master.get_csrs())