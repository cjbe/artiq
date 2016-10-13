#ifndef __TDC_H
#define __TDC_H

void tdc_reset(void);

void tdc_debug_init(void);
void tdc_debug_next(void);
void tdc_debug_finish(void);

int tdc_ringosc_freq(void);
int tdc_read_hist(int addr);

#endif /* __TDC_H */
