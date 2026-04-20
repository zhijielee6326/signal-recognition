#!/usr/bin/env python3
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

d = np.load('diagnose_result.npz')
freqs   = d['freqs']
spec_tx = 10*np.log10(d['spec_tx']+1e-10)
spec_rx = 10*np.log10(d['spec_rx']+1e-10)

fig, axes = plt.subplots(2, 1, figsize=(10, 7))

axes[0].plot(freqs, spec_tx, color='steelblue', linewidth=1.2)
axes[0].set_title('TX Signal Spectrum (STJ)')
axes[0].set_ylabel('Power (dB)')
axes[0].set_xlabel('Frequency (kHz)')
axes[0].grid(True, alpha=0.4)

axes[1].plot(freqs, spec_rx, color='tomato', linewidth=1.2)
axes[1].set_title('RX Signal Spectrum (after USRP RF chain)')
axes[1].set_ylabel('Power (dB)')
axes[1].set_xlabel('Frequency (kHz)')
axes[1].grid(True, alpha=0.4)

plt.tight_layout()
plt.savefig('diagnose_spectrum.png', dpi=150)
print("已保存 diagnose_spectrum.png")
