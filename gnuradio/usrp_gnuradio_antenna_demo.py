#!/usr/bin/env python3
import argparse
import signal
import sys

from PyQt5 import Qt
from gnuradio import analog
from gnuradio import blocks
from gnuradio import gr
from gnuradio import qtgui
from gnuradio import uhd
from gnuradio.fft import window


class UsrpAntennaDemo(gr.top_block, Qt.QWidget):
    def __init__(self, serial, sample_rate, center_freq, tone_freq, tx_gain, rx_gain, amplitude):
        gr.top_block.__init__(self, "USRP B210 GNU Radio Antenna Demo", catch_exceptions=True)
        Qt.QWidget.__init__(self)

        self.setWindowTitle("USRP B210 GNU Radio 天线耦合演示")
        self.resize(1200, 800)
        self.layout = Qt.QVBoxLayout(self)

        self.sample_rate = sample_rate
        self.center_freq = center_freq
        self.tone_freq = tone_freq
        self.tx_gain = tx_gain
        self.rx_gain = rx_gain
        self.amplitude = amplitude
        self.serial = serial

        self.info = Qt.QLabel(
            f"设备: {self.serial} | fc={self.center_freq/1e6:.3f} MHz | fs={self.sample_rate/1e6:.3f} MHz | "
            f"tone={self.tone_freq/1e3:.1f} kHz | TX gain={self.tx_gain:.1f} dB | RX gain={self.rx_gain:.1f} dB"
        )
        self.layout.addWidget(self.info)

        self.note = Qt.QLabel(
            "硬件连接：TX/RX 与 RX2 使用天线近距离空口耦合；建议间距 10~50 cm，并从较低增益开始。"
        )
        self.layout.addWidget(self.note)

        self.src = analog.sig_source_c(self.sample_rate, analog.GR_COS_WAVE, self.tone_freq, self.amplitude, 0.0)
        self.tx_scale = blocks.multiply_const_cc(0.8)

        self.usrp_sink = uhd.usrp_sink(
            self.serial,
            uhd.stream_args(cpu_format="fc32", otw_format="sc16", channels=[0]),
        )
        self.usrp_sink.set_samp_rate(self.sample_rate)
        self.usrp_sink.set_center_freq(self.center_freq, 0)
        self.usrp_sink.set_gain(self.tx_gain, 0)
        self.usrp_sink.set_antenna("TX/RX", 0)

        self.usrp_source = uhd.usrp_source(
            self.serial,
            uhd.stream_args(cpu_format="fc32", otw_format="sc16", channels=[0]),
        )
        self.usrp_source.set_samp_rate(self.sample_rate)
        self.usrp_source.set_center_freq(self.center_freq, 0)
        self.usrp_source.set_gain(self.rx_gain, 0)
        self.usrp_source.set_antenna("RX2", 0)

        self.freq_sink = qtgui.freq_sink_c(
            2048,
            window.WIN_HAMMING,
            0,
            self.sample_rate,
            "接收频谱",
            1,
            None,
        )
        self.freq_sink.set_update_time(0.1)
        self.freq_sink.set_y_axis(-140, 10)
        self.freq_sink.set_fft_average(0.2)
        self.freq_sink.enable_autoscale(False)
        self.freq_sink.enable_grid(True)
        self.freq_sink.set_line_label(0, "RX")
        self.layout.addWidget(self.freq_sink.qwidget())

        self.time_sink = qtgui.time_sink_c(
            2048,
            self.sample_rate,
            "接收时域",
            1,
            None,
        )
        self.time_sink.set_update_time(0.1)
        self.time_sink.enable_grid(True)
        self.time_sink.set_line_label(0, "RX")
        self.layout.addWidget(self.time_sink.qwidget())

        self.connect((self.src, 0), (self.tx_scale, 0))
        self.connect((self.tx_scale, 0), (self.usrp_sink, 0))
        self.connect((self.usrp_source, 0), (self.freq_sink, 0))
        self.connect((self.usrp_source, 0), (self.time_sink, 0))


def parse_args():
    parser = argparse.ArgumentParser(description="USRP B210 GNU Radio 天线耦合演示")
    parser.add_argument("--serial", default="serial=7MFTKFU", help="USRP 设备地址")
    parser.add_argument("--sample-rate", type=float, default=1e6, help="采样率，默认 1e6")
    parser.add_argument("--center-freq", type=float, default=1e9, help="中心频率，默认 1e9")
    parser.add_argument("--tone-freq", type=float, default=100e3, help="单音频率，默认 100e3")
    parser.add_argument("--tx-gain", type=float, default=15.0, help="TX 增益，天线耦合建议从 10~15 dB 开始")
    parser.add_argument("--rx-gain", type=float, default=25.0, help="RX 增益，天线耦合建议从 20~30 dB 开始")
    parser.add_argument("--amplitude", type=float, default=0.4, help="发送幅度，默认 0.4")
    return parser.parse_args()


def main():
    args = parse_args()

    qapp = Qt.QApplication(sys.argv)
    tb = UsrpAntennaDemo(
        serial=args.serial,
        sample_rate=args.sample_rate,
        center_freq=args.center_freq,
        tone_freq=args.tone_freq,
        tx_gain=args.tx_gain,
        rx_gain=args.rx_gain,
        amplitude=args.amplitude,
    )

    tb.start()
    tb.show()

    def handle_signal(sig=None, frame=None):
        tb.stop()
        tb.wait()
        qapp.quit()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    qapp.aboutToQuit.connect(handle_signal)
    qapp.exec_()


if __name__ == "__main__":
    main()
