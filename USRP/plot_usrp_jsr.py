#!/usr/bin/env python3
"""
读取 usrp_jsr_results.json，生成实机JSR曲线图
用法：python3 plot_usrp_jsr.py
"""
import json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

with open('usrp_jsr_results.json', 'r') as f:
    data = json.load(f)

jsr_list   = data['jsr']
test_types = data['types']
results    = data['results']

colors  = ['#E63946','#457B9D','#2A9D8F','#E9C46A','#F4A261','#6A0572']
markers = ['o','s','^','D','v','P']
label_map = {
    'lfm': 'LFM (Linear FM Sweep)',
    'mtj': 'MTJ (Multi-Tone)',
    'nam': 'NAM (Noise AM)',
    'nfm': 'NFM (Noise FM)',
    'stj': 'STJ (Single-Tone)',
}

fig, ax = plt.subplots(figsize=(9, 6))

for i, ttype in enumerate(test_types):
    acc = results[ttype]
    ax.plot(jsr_list, acc,
            color=colors[i % len(colors)],
            marker=markers[i % len(markers)],
            linewidth=2.2, markersize=7,
            label=label_map.get(ttype, ttype.upper()))

ax.axhline(90, color='gray', linestyle='--', linewidth=1.2, alpha=0.7)
ax.text(max(jsr_list) + 0.1, 90, '90%', va='center',
        fontsize=9, color='gray')

ax.set_xlabel('Jammer-to-Signal Ratio, JSR (dB)', fontsize=13)
ax.set_ylabel('Recognition Accuracy (%)', fontsize=13)
ax.set_title('CCNN Interference Recognition Accuracy vs JSR\n'
             '(USRP B210 Hardware-in-the-Loop Test)',
             fontsize=13, fontweight='bold')
ax.set_xticks(jsr_list)
ax.set_yticks(range(0, 101, 10))
ax.set_xlim(min(jsr_list) - 1, max(jsr_list) + 1)
ax.set_ylim(-3, 103)
ax.grid(True, linestyle='--', alpha=0.45)
ax.legend(loc='lower right', fontsize=10, framealpha=0.9)

plt.tight_layout()
plt.savefig('usrp_jsr_accuracy.png', dpi=180, bbox_inches='tight')
plt.savefig('usrp_jsr_accuracy.pdf', bbox_inches='tight')
print("已保存 usrp_jsr_accuracy.png / .pdf")
