#include <system.h>
#include <generated/csr.h>


void tdc_reset(void)
{
    tdc_reset_write(1);
    tdc_reset_write(0);
    while(tdc_ready_read()==0);
}


void tdc_debug_init(void)
{
    tdc_freeze_req_write(1);
    while( 0==tdc_freeze_acq_read() );

    // Pulse 'next' until we see 'last', then pulse one more time so we are definitely at the start
    while( tdc_cs_last_read() == 0 ) tdc_next();
    tdc_next();
}


void tdc_debug_next(void)
{
    tdc_cs_next_write(1);
}


void tdc_debug_finish(void)
{
    tdc_freeze_req_write(0);
}


// Should only be called in debug mode
int tdc_ringosc_freq(void)
{
    tdc_oc_start_write(1);
    tdc_oc_start_write(0);
    while( 0 == tdc_oc_ready_read() );

    return tdc_oc_freq_read();
}


int tdc_read_hist(int addr)
{
    tdc_his_a_write(addr);
    return tdc_his_d_read();
}