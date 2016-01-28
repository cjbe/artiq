# RUN: %python -m artiq.compiler.testbench.signature +diag +delay %s >%t
# RUN: OutputCheck %s --file-to-check=%t

def f():
    r = range(10)
    # CHECK-L: ${LINE:+2}: error: for statement cannot be interleaved because iteration count is indeterminate
    # CHECK-L: ${LINE:+1}: note: this value is not a constant range literal
    for _ in r:
        delay_mu(1)
