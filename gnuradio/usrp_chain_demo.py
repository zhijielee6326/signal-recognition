#!/usr/bin/env python3
"""
USRP B210 入门全链路 Demo

功能：
1. 单台 USRP 自发自收（loopback）
2. TX 连续发送单音信号
3. RX 连续接收并实时打印链路状态
4. 显示接收功率、峰值频率、峰值幅度

推荐硬件连接：
    USRP TX/RX 与 RX2 使用天线近距离空口耦合
    （建议两副天线相距 10~50 cm，先用较低增益启动）

运行示例：
    python3 usrp_chain_demo.py --serial "serial=7MFTKFU"
"""

import argparse
import threading
import time
import queue

import numpy as np
import uhd


class ToneTransmitter:
    def __init__(self, serial: str, sample_rate: float, center_freq: float, tx_gain: float, tone_freq: float, amplitude: float):
        self.sample_rate = sample_rate
        self.center_freq = center_freq
        self.tx_gain = tx_gain
        self.tone_freq = tone_freq
        self.amplitude = amplitude

        self.usrp = uhd.usrp.MultiUSRP(serial)
        self.usrp.set_tx_rate(self.sample_rate, 0)
        self.usrp.set_tx_freq(uhd.libpyuhd.types.tune_request(self.center_freq), 0)
        self.usrp.set_tx_gain(self.tx_gain, 0)
        self.usrp.set_tx_antenna("TX/RX", 0)

        self.tx_stream = self.usrp.get_tx_stream(uhd.usrp.StreamArgs("fc32", "sc16"))
        self.running = False
        self.thread = None

        n = 4096
        t = np.arange(n) / self.sample_rate
        self.buffer = (self.amplitude * np.exp(1j * 2 * np.pi * self.tone_freq * t)).astype(np.complex64)

    def _run(self):
        metadata = uhd.types.TXMetadata()
        first_packet = True

        while self.running:
            metadata.start_of_burst = first_packet
            metadata.end_of_burst = False
            self.tx_stream.send(self.buffer.reshape(1, -1), metadata)
            first_packet = False

        metadata.start_of_burst = False
        metadata.end_of_burst = True
        self.tx_stream.send(np.zeros((1, 0), dtype=np.complex64), metadata)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print(f"[TX] 已启动 | fc={self.center_freq/1e6:.3f} MHz | fs={self.sample_rate/1e6:.3f} MHz | gain={self.tx_gain:.1f} dB | tone={self.tone_freq/1e3:.1f} kHz")

    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1)
        print("[TX] 已停止")


class ToneReceiver:
    def __init__(self, serial: str, sample_rate: float, center_freq: float, rx_gain: float, fft_size: int):
        self.sample_rate = sample_rate
        self.center_freq = center_freq
        self.rx_gain = rx_gain
        self.fft_size = fft_size

        self.usrp = uhd.usrp.MultiUSRP(serial)
        self.usrp.set_rx_rate(self.sample_rate, 0)
        self.usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(self.center_freq), 0)
        self.usrp.set_rx_gain(self.rx_gain, 0)
        self.usrp.set_rx_antenna("RX2", 0)

        stream_args = uhd.usrp.StreamArgs("fc32", "sc16")
        stream_args.args = "recv_frame_size=4096,num_recv_frames=256"
        self.rx_stream = self.usrp.get_rx_stream(stream_args)

        self.running = False
        self.thread = None
        self.data_queue = queue.Queue(maxsize=50)
        self.overflow_count = 0

    def _run(self):
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        stream_cmd.stream_now = True
        self.rx_stream.issue_stream_cmd(stream_cmd)

        buffer = np.zeros((1, 4096), dtype=np.complex64)
        metadata = uhd.types.RXMetadata()

        while self.running:
            try:
                n = self.rx_stream.recv(buffer, metadata)
                if metadata.error_code == uhd.types.RXMetadataErrorCode.overflow:
                    self.overflow_count += 1
                if n > 0:
                    chunk = buffer[0][:n].copy()
                    try:
                        self.data_queue.put(chunk, block=False)
                    except queue.Full:
                        try:
                            self.data_queue.get_nowait()
                            self.data_queue.put(chunk, block=False)
                        except Exception:
                            pass
            except Exception as exc:
                print(f"[RX] 接收异常: {exc}")
                time.sleep(0.1)

        stop_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        self.rx_stream.issue_stream_cmd(stop_cmd)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print(f"[RX] 已启动 | fc={self.center_freq/1e6:.3f} MHz | fs={self.sample_rate/1e6:.3f} MHz | gain={self.rx_gain:.1f} dB")

    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=2)
        print(f"[RX] 已停止 | overflow={self.overflow_count}")

    def collect_samples(self, min_samples: int, timeout: float = 1.0):
        samples = []
        deadline = time.time() + timeout
        total = 0

        while total < min_samples and time.time() < deadline:
            try:
                chunk = self.data_queue.get(timeout=0.1)
                samples.append(chunk)
                total += len(chunk)
            except queue.Empty:
                pass

        if total < min_samples:
            return None
        return np.concatenate(samples)[:min_samples]

    def analyze(self, samples: np.ndarray):
        power = np.mean(np.abs(samples) ** 2)
        power_db = 10 * np.log10(power + 1e-12)
        peak_amp = np.max(np.abs(samples))

        windowed = samples[:self.fft_size] * np.hanning(self.fft_size)
        spectrum = np.fft.fftshift(np.fft.fft(windowed, n=self.fft_size))
        mag = np.abs(spectrum)
        peak_idx = np.argmax(mag)
        freqs = np.fft.fftshift(np.fft.fftfreq(self.fft_size, d=1.0 / self.sample_rate))
        peak_freq = freqs[peak_idx]

        return {
            "power_db": power_db,
            "peak_amp": float(peak_amp),
            "peak_freq_hz": float(peak_freq),
        }


def parse_args():
    parser = argparse.ArgumentParser(description="USRP B210 入门全链路 demo")
    parser.add_argument("--serial", default="serial=7MFTKFU", help="USRP 设备序列号")
    parser.add_argument("--sample-rate", type=float, default=1e6, help="采样率，默认 1e6")
    parser.add_argument("--center-freq", type=float, default=1e9, help="中心频率，默认 1e9")
    parser.add_argument("--tx-gain", type=float, default=20.0, help="TX 增益，默认 20 dB")
    parser.add_argument("--rx-gain", type=float, default=35.0, help="RX 增益，默认 35 dB")
    parser.add_argument("--tone-freq", type=float, default=100e3, help="单音频率，默认 100e3")
    parser.add_argument("--amplitude", type=float, default=0.5, help="发送幅度，默认 0.5")
    parser.add_argument("--duration", type=float, default=15.0, help="演示时长，默认 15 秒")
    parser.add_argument("--fft-size", type=int, default=2048, help="FFT 点数，默认 2048")
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 72)
    print("USRP B210 入门全链路 Demo")
    print("功能：发送单音 -> 接收单音 -> 实时打印链路状态")
    print("=" * 72)
    print("硬件连接建议：TX/RX 与 RX2 使用天线近距离空口耦合")
    print("建议天线间距 10~50 cm，并从较低 TX/RX 增益开始")
    print()

    tx = ToneTransmitter(
        serial=args.serial,
        sample_rate=args.sample_rate,
        center_freq=args.center_freq,
        tx_gain=args.tx_gain,
        tone_freq=args.tone_freq,
        amplitude=args.amplitude,
    )

    rx = ToneReceiver(
        serial=args.serial,
        sample_rate=args.sample_rate,
        center_freq=args.center_freq,
        rx_gain=args.rx_gain,
        fft_size=args.fft_size,
    )

    try:
        rx.start()
        time.sleep(0.3)
        tx.start()
        time.sleep(0.5)

        start_time = time.time()
        frame_id = 0

        while time.time() - start_time < args.duration:
            data = rx.collect_samples(args.fft_size, timeout=1.0)
            if data is None:
                print(f"[Frame {frame_id:03d}] 未收到足够数据，请检查连线/增益")
                frame_id += 1
                continue

            result = rx.analyze(data)
            print(
                f"[Frame {frame_id:03d}] "
                f"RX功率={result['power_db']:.2f} dB | "
                f"峰值频率={result['peak_freq_hz']/1e3:.1f} kHz | "
                f"峰值幅度={result['peak_amp']:.3f}"
            )
            frame_id += 1
            time.sleep(1.0)

        print()
        print("Demo 完成：说明发射、接收和基础频谱分析链路已经跑通。")

    except KeyboardInterrupt:
        print("\n用户中断，准备退出。")
    finally:
        tx.stop()
        rx.stop()


if __name__ == "__main__":
    main()
