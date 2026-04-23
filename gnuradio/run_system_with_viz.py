#!/usr/bin/env python3
"""
Real-time Visualization for Interference-Aware Video Transmission System
========================================================================
Launches VideoTransmissionSystem (sim mode) + matplotlib 2x2 live dashboard:
  1. Real-time Power Spectrum (PSD)
  2. CCNN 7-class Probability Bar Chart
  3. Time-domain IQ Waveform
  4. JSR vs Accuracy curve (static, from sweep data)

Built-in auto-demo: cycles through interference types automatically.

Usage:
  python3 run_system_with_viz.py
  python3 run_system_with_viz.py --duration 30
  python3 run_system_with_viz.py --no-demo       # disable auto-demo
"""

import os
import sys
import json
import time
import argparse
import numpy as np

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from video_transmission_system import VideoTransmissionSystem, SAMPLE_RATE

# ==================== Labels ====================
INTF_SHORT = ["LFM", "MTJ", "NAM", "NFM", "STJ", "SIN", "Clean"]
INTF_FULL = [
    "LFM Sweep",     # 0
    "MTJ Multi-Tone",# 1
    "NAM Narrow AM",  # 2
    "NFM Narrow FM",  # 3
    "STJ Single-Tone",# 4
    "SIN Sine",       # 5
    "Clean (No Jamming)",  # 6
]
BAR_COLORS_DEFAULT = ['#4e79a7'] * 7

# ==================== Auto-demo Sequence ====================
DEMO_SEQUENCE = [
    # (start_s, jammer_type, jsr_db, display_label)
    (0,  None,  None, "Clean"),
    (5,  'lfm', 4,    "LFM Sweep @ JSR=4dB"),
    (10, 'mtj', 0,    "MTJ Multi-Tone @ JSR=0dB"),
    (15, 'stj', 10,   "STJ Single-Tone @ JSR=10dB"),
    (20, 'nam', 2,    "NAM Narrow AM @ JSR=2dB"),
    (25, 'nfm', 6,    "NFM Narrow FM @ JSR=6dB"),
    (30, 'sin', 8,    "SIN Sine @ JSR=8dB"),
    (35, None,  None, "Clean (Recovered)"),
]


def load_jsr_sweep_data():
    path = os.path.join(SCRIPT_DIR, 'jsr_sweep_results.json')
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        return json.load(f)


class SystemVisualizer:

    def __init__(self, duration=45, demo=True):
        self.duration = duration
        self.demo = demo
        self.start_time = None
        self.demo_index = 0
        self.current_demo_label = "Clean"

        print("[Viz] Initializing system...")
        self.system = VideoTransmissionSystem(
            mode='sim', source='test', no_gui=True)
        self.system.start()
        self.start_time = time.time()
        print("[Viz] System started. Building dashboard...")

        self.jsr_data = load_jsr_sweep_data()
        self._init_figure()

    # ----------------------------------------------------------
    def _init_figure(self):
        # Use default DejaVu Sans (clean English, no CJK issues)
        plt.rcParams['axes.unicode_minus'] = False

        self.fig, self.axes = plt.subplots(
            2, 2, figsize=(14, 9),
            gridspec_kw={'hspace': 0.38, 'wspace': 0.28})
        self.fig.subplots_adjust(
            left=0.06, right=0.97, top=0.92, bottom=0.07)
        self.fig.suptitle(
            'Interference-Aware Video Transmission  --  Real-time Dashboard',
            fontsize=13, fontweight='bold')

        self._init_psd()
        self._init_bar()
        self._init_time()
        self._init_jsr()

    # --- Subplot 1: PSD ---
    def _init_psd(self):
        ax = self.axes[0, 0]
        self.ax_psd = ax
        ax.set_title('1) Real-time Power Spectrum', fontsize=11)
        ax.set_xlabel('Frequency (kHz)')
        ax.set_ylabel('Power (dB)')
        ax.set_xlim(-SAMPLE_RATE / 2e3, SAMPLE_RATE / 2e3)
        ax.set_ylim(-40, 60)
        ax.grid(True, alpha=0.3)
        self.line_psd, = ax.plot([], [], color='#1f77b4', linewidth=0.8)
        self.psd_text = ax.text(
            0.02, 0.95, '', transform=ax.transAxes, fontsize=9, va='top',
            bbox=dict(boxstyle='round,pad=0.3', fc='wheat', alpha=0.85))

    # --- Subplot 2: CCNN probability ---
    def _init_bar(self):
        ax = self.axes[0, 1]
        self.ax_bar = ax
        ax.set_title('2) CCNN 7-class Probability', fontsize=11)
        ax.set_ylabel('Probability')
        ax.set_ylim(0, 1.08)
        self.bars = ax.bar(
            range(7), [0]*7,
            color=BAR_COLORS_DEFAULT, edgecolor='#333333', linewidth=0.6,
            tick_label=INTF_SHORT)
        ax.set_xticks(range(7))
        ax.set_xticklabels(INTF_SHORT, rotation=30, ha='right', fontsize=8)
        # probability value on top of each bar
        self.bar_val_texts = []
        for i in range(7):
            t = ax.text(i, 0, '', ha='center', va='bottom', fontsize=7)
            self.bar_val_texts.append(t)
        self.bar_text = ax.text(
            0.02, 0.95, '', transform=ax.transAxes, fontsize=9, va='top',
            bbox=dict(boxstyle='round,pad=0.3', fc='lightyellow', alpha=0.85))

    # --- Subplot 3: Time-domain IQ ---
    def _init_time(self):
        ax = self.axes[1, 0]
        self.ax_time = ax
        ax.set_title('3) Time-domain IQ Waveform', fontsize=11)
        ax.set_xlabel('Sample Index')
        ax.set_ylabel('Amplitude')
        ax.set_xlim(0, 512)
        ax.set_ylim(-2.5, 2.5)
        ax.grid(True, alpha=0.3)
        self.line_i, = ax.plot([], [], color='#1f77b4', lw=0.5,
                               label='I (real)', alpha=0.85)
        self.line_q, = ax.plot([], [], color='#d62728', lw=0.5,
                               label='Q (imag)', alpha=0.85)
        ax.legend(loc='upper right', fontsize=8, framealpha=0.8)

    # --- Subplot 4: JSR-Accuracy ---
    def _init_jsr(self):
        ax = self.axes[1, 1]
        self.ax_jsr = ax
        ax.set_title('4) JSR vs Detection Accuracy', fontsize=11)
        ax.set_xlabel('JSR (dB)')
        ax.set_ylabel('Accuracy (%)')
        ax.set_ylim(50, 105)
        ax.grid(True, alpha=0.3)
        if self.jsr_data:
            jsr_x = [d['jsr_db'] for d in self.jsr_data]
            acc_y = [d['overall'] for d in self.jsr_data]
            ax.plot(jsr_x, acc_y, 'o-', color='#2ca02c',
                    linewidth=1.8, markersize=5, zorder=3)
            ax.fill_between(jsr_x, 90, acc_y, alpha=0.12, color='#2ca02c')
            ax.axhline(y=99, color='gray', ls='--', lw=0.6, alpha=0.5)
            ax.text(jsr_x[-1]+0.3, 90.5, '99%', fontsize=7, color='gray')
        self.jsr_info_text = ax.text(
            0.02, 0.95, '', transform=ax.transAxes, fontsize=9, va='top',
            bbox=dict(boxstyle='round,pad=0.3', fc='#e8f4fd', alpha=0.9))

    # ----------------------------------------------------------
    def _update_frame(self, frame_num):
        s = self.system

        # Auto-demo
        if self.demo and self.start_time:
            self._auto_demo(time.time() - self.start_time)

        # Read shared state (thread-safe, read-only)
        raw_signal  = s.last_raw_signal
        psd_raw     = s.last_psd_raw
        cnn_probs   = s.last_cnn_probs
        intf_type   = s.last_interference_type
        intf_conf   = s.last_interference_conf

        # --- 1) PSD ---
        if psd_raw is not None and len(psd_raw) > 0:
            N = len(psd_raw)
            freqs = np.fft.fftshift(np.fft.fftfreq(N, d=1.0 / SAMPLE_RATE))
            self.line_psd.set_data(freqs / 1e3, psd_raw)
            # Use English label
            intf_en = self._cn_to_en(intf_type)
            self.psd_text.set_text(f'{intf_en}  ({intf_conf:.1%})')

        # --- 2) CCNN probability bars ---
        if cnn_probs is not None:
            pred_idx = int(np.argmax(cnn_probs))
            for i, (bar, p) in enumerate(zip(self.bars, cnn_probs)):
                bar.set_height(p)
                if i == pred_idx:
                    bar.set_color('#e15759' if i < 6 else '#59a14f')
                else:
                    bar.set_color('#4e79a7')
                self.bar_val_texts[i].set_position((i, p + 0.02))
                self.bar_val_texts[i].set_text(f'{p:.2f}' if p > 0.01 else '')
            self.bar_text.set_text(
                f'Predict: {INTF_FULL[pred_idx]}  ({cnn_probs[pred_idx]:.2f})')

        # --- 3) Time-domain ---
        if raw_signal is not None:
            n = min(512, len(raw_signal))
            x = np.arange(n)
            self.line_i.set_data(x, raw_signal[:n].real)
            self.line_q.set_data(x, raw_signal[:n].imag)

        # --- 4) Status info ---
        severity = s.controller.current_severity
        params = s.controller.get_smoothed_params()
        elapsed = time.time() - self.start_time if self.start_time else 0
        self.jsr_info_text.set_text(
            f'Elapsed: {elapsed:.0f}s\n'
            f'Strategy: {severity}\n'
            f'Q={params["quality"]}  FPS={params["fps"]}\n'
            f'Demo: {self.current_demo_label}')

        return (self.line_psd, self.psd_text,
                *self.bars, *self.bar_val_texts, self.bar_text,
                self.line_i, self.line_q,
                self.jsr_info_text)

    @staticmethod
    def _cn_to_en(cn_name):
        """Map Chinese interference name to English short label."""
        mapping = {
            '无干扰': 'Clean',
            '扫频干扰(LFM)': 'LFM Sweep',
            '多音干扰(MTJ)': 'MTJ Multi-Tone',
            '窄带AM(NAM)': 'NAM Narrow AM',
            '窄带FM(NFM)': 'NFM Narrow FM',
            '单音干扰(STJ)': 'STJ Single-Tone',
            '正弦波(SIN)': 'SIN Sine',
        }
        return mapping.get(cn_name, cn_name)

    def _auto_demo(self, elapsed):
        target_idx = 0
        for i, (t_start, _, _, _) in enumerate(DEMO_SEQUENCE):
            if elapsed >= t_start:
                target_idx = i
        if target_idx != self.demo_index:
            self.demo_index = target_idx
            _, jtype, jsr, label = DEMO_SEQUENCE[target_idx]
            self.current_demo_label = label
            self.system.sim_channel.jammer_type = jtype
            self.system.sim_channel.jsr_db = jsr
            print(f"[Demo @ {elapsed:.0f}s] {label}")

    # ----------------------------------------------------------
    def run(self):
        print(f"[Viz] Dashboard started (duration={self.duration}s)")
        print(f"[Viz] Close window or Ctrl+C to exit\n")

        self.anim = FuncAnimation(
            self.fig, self._update_frame,
            interval=500, blit=False, cache_frame_data=False)

        if self.duration > 0:
            timer = self.fig.canvas.new_timer(interval=self.duration * 1000)
            timer.add_callback(self._on_timeout)
            timer.single_shot = True
            timer.start()

        try:
            plt.show()
        except KeyboardInterrupt:
            pass
        finally:
            self._cleanup()

    def _on_timeout(self):
        print(f"\n[Viz] Demo finished ({self.duration}s)")
        plt.close(self.fig)

    def _cleanup(self):
        self.system.stop()
        self.system.print_final_stats()
        if self.system.ccnn_detector:
            self.system.ccnn_detector.print_statistics()
        print("[Viz] Exited.")


def main():
    parser = argparse.ArgumentParser(
        description='Real-time Visualization Dashboard')
    parser.add_argument(
        '--duration', type=int, default=45,
        help='Demo duration in seconds, 0=unlimited (default: 45)')
    parser.add_argument(
        '--no-demo', action='store_true',
        help='Disable auto-demo sequence')
    args = parser.parse_args()

    viz = SystemVisualizer(
        duration=args.duration,
        demo=not args.no_demo)
    viz.run()


if __name__ == '__main__':
    main()
