from migen import *
from misoc.interconnect.csr import *
from migen.genlib.fifo import *


class TdcCalOsc(Module):
    def __init__(self, cal_clk, ro_length=51):
        cal_clkdiv = Signal(4)

        # Ringosc clock domain is used to clock this x16 divider
        self.clock_domains.ringosc = ClockDomain(reset_less=True)
        self.sync.ringosc += cal_clkdiv.eq( cal_clkdiv+1 )
        self.comb += cal_clk.eq(cal_clkdiv[3])

        calib_osc = Instance("tdc_ringosc",
            p_g_LENGTH=51,
            i_en_i= ~ResetSignal(),
            o_clk_o=self.ringosc.clk
            )
        self.specials += calib_osc



class TDC(Module, AutoCSR):
    """Wrapper for TDC core. 
    Debug / reset exposed via CSR interface
    TDC timestamps exposed via self.channels record array"""
    def __init__(self, inputs, n_channels=2, carry4_count=340, raw_count=11, fp_count=13, exhis_count=4, coarse_count=25, 
                ro_length=51, fcounter_width=13, ftimer_width=14):
        fp_width = coarse_count+fp_count
        self.fp_count = fp_count
        self._ready = CSRStatus()
        self._reset = CSRStorage()
        self._cc_rst = CSRStorage()

        # Debug signals
        self._freeze_req = CSRStorage()
        self._freeze_acq = CSRStatus()
        self._cs_next = CSR()
        self._cs_last = CSRStatus()
        self._calib_sel = CSRStorage()
        self._lut_a = CSRStorage(size=raw_count)
        self._lut_d = CSRStatus(size=fp_count)
        self._his_a = CSRStorage(size=raw_count)
        self._his_d = CSRStatus(size=fp_count+exhis_count)
        self._oc_start = CSRStorage()
        self._oc_ready = CSRStatus()
        self._oc_freq = CSRStatus(size=fcounter_width)
        self._oc_sfreq = CSRStatus(size=fcounter_width)

        # Output signals

        raw = Signal(n_channels*raw_count)
        fp = Signal(n_channels*fp_width)
        polarity = Signal(n_channels)
        detect_stb = Signal(n_channels)

        channel_record = [('raw', raw_count), ('coarse',coarse_count), ('fine',fp_count), ('pol',1), ('stb', 1)]
        self.channels = []
        for i in range(n_channels):
            ch = Record(channel_record)
            fp_ch = Signal(fp_width)
            self.comb += [
                fp_ch.eq( fp[(i*fp_width):((i+1)*fp_width)] ),
                ch.raw.eq( raw[(i*raw_count):((i+1)*raw_count)] ),
                ch.coarse.eq( fp_ch[fp_count:] ),
                ch.fine.eq( fp_ch[:fp_count] ),
                ch.pol.eq(polarity[i]),
                ch.stb.eq(detect_stb[i])
            ]
            self.channels.append(ch)


        # Calibration oscillator input
        self.cal_clk = Signal()
        self.submodules += TdcCalOsc(self.cal_clk, ro_length=ro_length)

        self.specials += Instance("tdc",
            p_g_CHANNEL_COUNT= n_channels,
            p_g_CARRY4_COUNT= carry4_count,
            p_g_RAW_COUNT= raw_count,
            p_g_FP_COUNT= fp_count,
            p_g_EXHIS_COUNT= exhis_count,
            p_g_COARSE_COUNT= coarse_count,
            p_g_RO_LENGTH= ro_length,
            p_g_FCOUNTER_WIDTH= fcounter_width,
            p_g_FTIMER_WIDTH= ftimer_width,

            i_clk_i=ClockSignal(),
            i_reset_i=(self._reset.storage | ResetSignal()),
            o_ready_o=self._ready.status,
            
            # Coarse counter control.
            i_cc_rst_i=self._cc_rst.storage,
            #o_cc_cy_o=,
            
            # Per-channel deskew inputs.
            i_deskew_i=0,
            
            # Per-channel signal inputs.
            i_signal_i=inputs,
            i_calib_i=Replicate(self.cal_clk, n_channels),
            
            # Per-channel detection outputs.
            o_detect_o=detect_stb,
            o_polarity_o=polarity,
            o_raw_o=raw,
            o_fp_o=fp,
            
            # Debug interface.
            i_freeze_req_i=self._freeze_req.storage,
            o_freeze_ack_o=self._freeze_acq.status,
            i_cs_next_i=self._cs_next.re,
            o_cs_last_o=self._cs_last.status,
            i_calib_sel_i=self._calib_sel.storage,
            i_lut_a_i=self._lut_a.storage,
            o_lut_d_o=self._lut_d.status,
            i_his_a_i=self._his_a.storage,
            o_his_d_o=self._his_d.status,
            i_oc_start_i=self._oc_start.storage,
            o_oc_ready_o=self._oc_ready.status,
            o_oc_freq_o=self._oc_freq.status,
            o_oc_sfreq_o=self._oc_sfreq.status
        )
