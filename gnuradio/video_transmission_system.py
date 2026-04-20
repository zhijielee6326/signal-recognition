#!/usr/bin/env python3
"""
面向信号干扰检测与识别的视频传输系统
============================================

完整系统架构:
  TX端: 视频采集 -> JPEG编码 -> FEC编码 -> QPSK调制 -> USRP发送
  RX端: USRP接收 -> QPSK解调 -> FEC解码 -> JPEG解码 -> 视频显示

  干扰监测: 功率谱特征提取 -> 干扰检测 -> CCNN干扰类型识别

  自适应控制: 根据干扰类型和强度动态调整:
    - JPEG编码质量 (20~95)
    - FEC冗余度 (1~3倍冗余)
    - 视频帧率 (10~25 fps)

运行方式:
  # 完整系统演示(单机USRP环回)
  python3 video_transmission_system.py --mode full --source test

  # 仿真模式(无需USRP硬件)
  python3 video_transmission_system.py --mode sim --source test

  # 使用摄像头
  python3 video_transmission_system.py --mode sim --source camera

  # 使用视频文件
  python3 video_transmission_system.py --mode sim --source video.mp4
"""

import os
import sys
import time
import struct
import threading
import queue
import argparse
import traceback
from datetime import datetime
from collections import deque

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPT_DIR, '..', 'CCNN', '3_scripts', 'training'))

import cv2

# ==================== 协议常量 ====================
SYNC_WORD = 0xAA55AA55
HEADER_FMT = '<IHHHH H'       # sync(4) + seq(2) + pkt_idx(2) + pkt_total(2) + payload_len(2) + reserved(2)
HEADER_SIZE = struct.calcsize(HEADER_FMT)  # 14 bytes
MAX_PAYLOAD = 480              # 最大载荷字节(含对齐考虑)
PKT_OVERHEAD = HEADER_SIZE + 2 # header + CRC16
MAX_PKT_SIZE = MAX_PAYLOAD + PKT_OVERHEAD

# ==================== 视频常量 ====================
DEFAULT_WIDTH = 320
DEFAULT_HEIGHT = 240
DEFAULT_FPS = 25
DEFAULT_JPEG_QUALITY = 70

# ==================== 射频常量 ====================
SAMPLE_RATE = 2e6
CENTER_FREQ = 2.45e9
TX_GAIN = 20
RX_GAIN = 40
SYMBOL_RATE = 500e3
SAMPLES_PER_SYMBOL = int(SAMPLE_RATE / SYMBOL_RATE)  # 4
BUFFER_SIZE = 4096

# ==================== QPSK 星座图 ====================
QPSK_CONSTELLATION = np.array([
    1 + 1j,    # 00
    1 - 1j,    # 01
    -1 + 1j,   # 10
    -1 - 1j,   # 11
], dtype=np.complex64) / np.sqrt(2)

# ==================== 自适应传输策略 ====================
INTERFERENCE_PROFILES = {
    'none':     {'quality': 85, 'fec_redundancy': 1, 'fps': 25, 'label': '无干扰 - 高质量传输'},
    'mild':     {'quality': 55, 'fec_redundancy': 2, 'fps': 15, 'label': '轻度干扰 - 降质保传'},
    'moderate': {'quality': 35, 'fec_redundancy': 2, 'fps': 8,  'label': '中度干扰 - 低质冗余'},
    'severe':   {'quality': 15, 'fec_redundancy': 3, 'fps': 5,  'label': '严重干扰 - 最低质保'},
}

# 干扰类型到严重程度的映射
JAMMER_SEVERITY = {
    '无干扰': 'none',
    '扫频干扰(LFM)': 'moderate',
    '多音干扰(MTJ)': 'moderate',
    '窄带AM(NAM)': 'mild',
    '窄带FM(NFM)': 'mild',
    '单音干扰(STJ)': 'severe',
    '正弦波(SIN)': 'mild',
}


# ==================== CRC-16-CCITT ====================
def crc16(data: bytes, init=0xFFFF) -> int:
    """CRC-16-CCITT 校验"""
    crc = init
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


# ==================== 数据包帧/解帧 ====================
class PacketFramer:
    """将数据流分割为带协议头的分组"""

    @staticmethod
    def frame(data: bytes, seq: int) -> list:
        """将一段数据分片并加协议头和CRC"""
        pkts = []
        max_chunk = MAX_PAYLOAD
        total = (len(data) + max_chunk - 1) // max_chunk

        for i in range(total):
            start = i * max_chunk
            end = min(start + max_chunk, len(data))
            payload = data[start:end]
            payload_len = len(payload)

            header = struct.pack(HEADER_FMT, SYNC_WORD, seq, i, total,
                                 payload_len, 0)
            crc = crc16(header + payload)
            pkt = header + payload + struct.pack('<H', crc)
            pkts.append(pkt)

        return pkts

    @staticmethod
    def deframe(pkt_bytes: bytes):
        """解帧，返回 (seq, pkt_idx, pkt_total, payload) 或 None"""
        if len(pkt_bytes) < HEADER_SIZE + 2:
            return None

        header = pkt_bytes[:HEADER_SIZE]
        sync, seq, pkt_idx, pkt_total, payload_len, _ = struct.unpack(
            HEADER_FMT, header)

        if sync != SYNC_WORD:
            return None
        if len(pkt_bytes) < HEADER_SIZE + payload_len + 2:
            return None

        payload = pkt_bytes[HEADER_SIZE:HEADER_SIZE + payload_len]
        crc_received = struct.unpack('<H', pkt_bytes[HEADER_SIZE + payload_len:
                                                      HEADER_SIZE + payload_len + 2])[0]
        crc_calc = crc16(header + payload)
        if crc_received != crc_calc:
            return None

        return seq, pkt_idx, pkt_total, payload


# ==================== FEC编解码 ====================
class FECCodec:
    """前向纠错：XOR冗余编码"""

    def __init__(self, redundancy=1):
        self.redundancy = max(1, min(redundancy, 3))

    def encode(self, pkts: list) -> list:
        """为每N个数据包生成 redundancy-1 个冗余包"""
        if self.redundancy <= 1:
            return pkts

        result = list(pkts)
        n = len(pkts)
        for r in range(self.redundancy - 1):
            max_len = max(len(p) for p in pkts)
            parity = bytearray(max_len)
            for p in pkts:
                padded = p + b'\x00' * (max_len - len(p))
                for j in range(max_len):
                    parity[j] ^= padded[j]
            # 标记为冗余包: pkt_total字段高位设为0xFEC标记
            fec_header = struct.pack('<IHHHH H', SYNC_WORD, 0xFFFE,
                                     r, n, max_len, 0xFEC0 + r)
            fec_crc = crc16(fec_header + bytes(parity))
            fec_pkt = fec_header + bytes(parity) + struct.pack('<H', fec_crc)
            result.append(fec_pkt)
        return result

    def decode(self, pkts: list, lost_indices: list) -> list:
        """尝试用冗余包恢复丢失的数据包"""
        if not lost_indices or self.redundancy <= 1:
            return pkts

        recovered = list(pkts)
        # 简化实现：如有冗余包且数据包丢失，用第一个冗余包恢复
        data_pkts = [p for p in pkts if p is not None]
        fec_pkts = []
        for p in pkts:
            if p is not None:
                info = PacketFramer.deframe(p)
                if info and info[1] == 0xFFFE:  # FEC标记
                    fec_pkts.append(p)

        if fec_pkts and lost_indices:
            for li in lost_indices[:len(fec_pkts)]:
                if li < len(recovered):
                    # 用冗余包XOR所有已知包来恢复
                    max_len = max(len(p) for p in data_pkts if p is not None) if data_pkts else 0
                    recovered_data = bytearray(max_len)
                    known_pkts = [p for i, p in enumerate(pkts)
                                  if p is not None and i != li]
                    for p in known_pkts:
                        padded = p + b'\x00' * (max_len - len(p))
                        for j in range(max_len):
                            recovered_data[j] ^= padded[j]
                    if fec_pkts:
                        padded = fec_pkts[0] + b'\x00' * (max_len - len(fec_pkts[0]))
                        for j in range(max_len):
                            recovered_data[j] ^= padded[j]
                    recovered[li] = bytes(recovered_data)

        return recovered


# ==================== QPSK调制解调 ====================
class QPSKModem:
    """QPSK调制器/解调器(含频偏估计、AGC、同步)"""

    PREAMBLE_LEN = 256  # 加长前导，提高同步鲁棒性

    def __init__(self, samples_per_symbol=SAMPLES_PER_SYMBOL):
        self.sps = samples_per_symbol
        self._design_filter()
        # 预生成前导序列
        self._preamble = np.exp(
            1j * 2 * np.pi * np.arange(self.PREAMBLE_LEN) / 4
        ).astype(np.complex64)
        self._preamble_conj = np.conj(self._preamble[::-1])

    def _design_filter(self):
        """设计根升余弦滤波器"""
        rolloff = 0.35
        span = 6
        ntaps = span * self.sps + 1
        t = np.arange(ntaps) / self.sps - span / 2

        with np.errstate(invalid='ignore', divide='ignore'):
            h = np.sinc(t) * np.cos(np.pi * rolloff * t) / (
                1 - (2 * rolloff * t) ** 2 + 1e-12)
        h[np.isnan(h)] = 0
        h = h / np.sqrt(np.sum(h ** 2))
        self.tx_filter = h
        self.rx_filter = h  # 匹配滤波器

    def modulate(self, data: bytes) -> np.ndarray:
        """将字节流调制为QPSK基带信号"""
        bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
        if len(bits) % 2:
            bits = np.append(bits, 0)
        indices = (bits[0::2] * 2 + bits[1::2]).astype(int)
        symbols = QPSK_CONSTELLATION[indices]

        # 上采样 + 脉冲成形
        upsampled = np.zeros(len(symbols) * self.sps, dtype=np.complex64)
        upsampled[::self.sps] = symbols
        shaped = np.convolve(upsampled, self.tx_filter, mode='same')
        return shaped.astype(np.complex64)

    def demodulate(self, signal: np.ndarray) -> bytes:
        """将QPSK基带信号解调为字节流(含匹配滤波)"""
        if len(signal) < self.sps:
            return b''

        # 匹配滤波
        filtered = np.convolve(signal, self.rx_filter, mode='same')

        # 下采样
        n_symbols = len(filtered) // self.sps
        if n_symbols == 0:
            return b''
        samples = filtered[self.sps // 2::self.sps][:n_symbols]

        # 矢量化硬判决: 找最近的星座点
        # 计算与4个星座点的距离矩阵 (n_symbols, 4)
        dists = np.abs(samples[:, None] - QPSK_CONSTELLATION[None, :])
        decisions = np.argmin(dists, axis=1)

        bits = np.zeros(len(decisions) * 2, dtype=np.uint8)
        bits[0::2] = (decisions >> 1) & 1
        bits[1::2] = decisions & 1

        n_bytes = len(bits) // 8
        if n_bytes == 0:
            return b''
        return np.packbits(bits[:n_bytes * 8]).tobytes()

    def add_preamble(self, signal: np.ndarray) -> np.ndarray:
        """添加前导序列用于同步和频偏估计"""
        # 前导 + 保护间隔 + 数据
        guard = np.zeros(32, dtype=np.complex64)
        return np.concatenate([self._preamble, guard, signal])

    def detect_preamble(self, signal: np.ndarray, threshold=0.5):
        """检测前导序列位置，同时估计频偏"""
        if len(signal) < self.PREAMBLE_LEN:
            return None

        # 互相关检测
        corr = np.abs(np.convolve(signal, self._preamble_conj,
                                   mode='valid'))
        if len(corr) == 0:
            return None

        peak_idx = np.argmax(corr)
        peak_val = corr[peak_idx]
        rms_val = np.sqrt(np.mean(corr ** 2)) + 1e-12

        # 使用 peak/rms 作为检测指标 (比 peak/mean 更鲁棒)
        # 同时要求绝对峰值足够大 (AGC后信号RMS~1, preamble相关峰值应>3)
        ratio = peak_val / rms_val
        if ratio < 8.0 or peak_val < 3.0:
            return None

        data_start = peak_idx + self.PREAMBLE_LEN
        return data_start

    def estimate_cfo(self, signal: np.ndarray) -> float:
        """利用前导序列估计载波频偏(CFO)"""
        if len(signal) < self.PREAMBLE_LEN:
            return 0.0

        # 取前导部分
        preamble_rx = signal[:self.PREAMBLE_LEN]
        # 与已知前导互相关后取相位差
        corr_product = preamble_rx * np.conj(self._preamble)

        # 利用重复结构估计频偏(前导周期=4)
        half = self.PREAMBLE_LEN // 2
        if half < 2:
            return 0.0
        phase_diff = np.sum(
            corr_product[half:] * np.conj(corr_product[:half]))
        cfo = np.angle(phase_diff) * SAMPLE_RATE / (2 * np.pi * half)
        return cfo

    def correct_cfo(self, signal: np.ndarray, cfo: float) -> np.ndarray:
        """校正载波频偏"""
        if abs(cfo) < 1.0:
            return signal
        t = np.arange(len(signal)) / SAMPLE_RATE
        correction = np.exp(-1j * 2 * np.pi * cfo * t).astype(np.complex64)
        return signal * correction

    @staticmethod
    def agc(signal: np.ndarray, target_rms=1.0) -> np.ndarray:
        """自动增益控制"""
        rms = np.sqrt(np.mean(np.abs(signal) ** 2))
        if rms < 1e-10:
            return signal
        return signal * (target_rms / rms)


# ==================== 视频编解码 ====================
class VideoCodec:
    """视频帧JPEG编解码，支持质量自适应"""

    @staticmethod
    def encode(frame: np.ndarray, quality=70) -> bytes:
        """将视频帧编码为JPEG字节流"""
        params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        _, encoded = cv2.imencode('.jpg', frame, params)
        return encoded.tobytes()

    @staticmethod
    def decode(data: bytes, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT) -> np.ndarray:
        """将JPEG字节流解码为视频帧"""
        try:
            frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8),
                                 cv2.IMREAD_COLOR)
            if frame is not None:
                return cv2.resize(frame, (width, height))
        except Exception:
            pass
        # 解码失败返回灰色占位帧
        return np.full((height, width, 3), 128, dtype=np.uint8)


# ==================== 视频源 ====================
class VideoSource:
    """视频源：摄像头/视频文件/测试图案"""

    def __init__(self, source='test', width=DEFAULT_WIDTH,
                 height=DEFAULT_HEIGHT, fps=DEFAULT_FPS):
        self.width = width
        self.height = height
        self.target_fps = fps
        self.frame_interval = 1.0 / fps
        self.source = source
        self.cap = None
        self.frame_count = 0
        self.is_file = False

        if source == 'camera':
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                print(f"[VideoSource] 摄像头已打开")
            else:
                print(f"[VideoSource] 摄像头不可用，切换到测试图案")
                self.source = 'test'
        elif source != 'test':
            if os.path.isfile(source):
                self.cap = cv2.VideoCapture(source)
                self.is_file = True
                print(f"[VideoSource] 视频文件: {source}")
            else:
                print(f"[VideoSource] 文件不存在: {source}, 切换到测试图案")
                self.source = 'test'

    def get_frame(self):
        """获取下一帧"""
        self.frame_count += 1

        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return cv2.resize(frame, (self.width, self.height))
            if self.is_file:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if ret:
                    return cv2.resize(frame, (self.width, self.height))
            self.source = 'test'
            self.cap = None

        # 测试图案: 带时间戳的彩色画面
        return self._generate_test_pattern()

    def _generate_test_pattern(self):
        """生成测试图案"""
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # 渐变背景
        for i in range(self.height):
            ratio = i / self.height
            img[i, :, 0] = int(40 * (1 - ratio))    # B
            img[i, :, 1] = int(60 * ratio)            # G
            img[i, :, 2] = int(120 + 80 * ratio)      # R

        # 移动方块
        t = self.frame_count
        bx = int((self.width * 0.6) * (0.5 + 0.5 * np.sin(t * 0.05)))
        by = int((self.height * 0.6) * (0.5 + 0.5 * np.cos(t * 0.07)))
        bx = max(0, min(bx, self.width - 80))
        by = max(0, min(by, self.height - 60))
        img[by:by+60, bx:bx+80] = [0, 200, 255]

        # 帧计数和时间戳文字
        text1 = f"Frame: {self.frame_count}"
        text2 = f"Time: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}"
        text3 = f"Video Transmission Demo"
        cv2.putText(img, text3, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (255, 255, 255), 1)
        cv2.putText(img, text1, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (255, 255, 200), 1)
        cv2.putText(img, text2, (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (200, 255, 200), 1)

        # 网格线
        for x in range(0, self.width, 40):
            cv2.line(img, (x, 0), (x, self.height), (80, 80, 80), 1)
        for y in range(0, self.height, 40):
            cv2.line(img, (0, y), (self.width, y), (80, 80, 80), 1)

        return img

    def release(self):
        if self.cap:
            self.cap.release()


# ==================== 仿真信道 ====================
class SimulatedChannel:
    """仿真信道：模拟AWGN和干扰注入"""

    def __init__(self, snr_db=20, jsr_db=None, jammer_type=None):
        self.snr_db = snr_db
        self.jsr_db = jsr_db
        self.jammer_type = jammer_type
        self.noise_level = 0.0

    def apply(self, signal: np.ndarray) -> np.ndarray:
        """对信号施加信道效应"""
        result = signal.copy()

        # AWGN噪声
        if self.snr_db is not None:
            sig_power = np.mean(np.abs(result) ** 2)
            noise_power = sig_power / (10 ** (self.snr_db / 10))
            noise = (np.random.randn(len(result)) +
                     1j * np.random.randn(len(result))) * np.sqrt(noise_power / 2)
            result = result + noise.astype(np.complex64)

        # 干扰注入
        if self.jsr_db is not None and self.jammer_type is not None:
            result = self._inject_jammer(result)

        return result

    def _inject_jammer(self, signal: np.ndarray) -> np.ndarray:
        """注入干扰信号"""
        sig_power = np.mean(np.abs(signal) ** 2)
        jammer_power = sig_power * (10 ** (self.jsr_db / 10))
        N = len(signal)
        t = np.arange(N) / SAMPLE_RATE

        if self.jammer_type == 'stj':
            f0 = 100e3 * (np.random.rand() - 0.5)
            jammer = np.sqrt(jammer_power) * np.exp(
                1j * 2 * np.pi * f0 * t)
        elif self.jammer_type == 'mtj':
            jammer = np.zeros(N, dtype=complex)
            for f in [200e3, 400e3, 600e3]:
                jammer += np.exp(1j * 2 * np.pi * f * t)
            jammer = jammer * np.sqrt(jammer_power / np.mean(np.abs(jammer)**2))
        elif self.jammer_type == 'lfm':
            f0 = -200e3
            K = 800e3 / (N / SAMPLE_RATE)
            jammer = np.sqrt(jammer_power) * np.exp(
                1j * (2*np.pi*f0*t + np.pi*K*t**2))
        elif self.jammer_type == 'nfm':
            mod = np.cumsum(np.random.randn(N)) / SAMPLE_RATE * 100e3
            jammer = np.sqrt(jammer_power) * np.exp(
                1j * 2 * np.pi * mod)
        elif self.jammer_type == 'nam':
            mod = np.random.randn(N)
            f0 = 150e3 * (np.random.rand() - 0.5)
            jammer = (1 + 2 * mod) * np.exp(1j * 2 * np.pi * f0 * t)
            jammer = jammer * np.sqrt(jammer_power / np.mean(np.abs(jammer)**2))
        elif self.jammer_type == 'sin':
            f_mod = 50e3 + 50e3 * np.random.rand()
            f0 = 100e3 * (np.random.rand() - 0.5)
            mod = np.cumsum(np.sin(2 * np.pi * f_mod * t)) / SAMPLE_RATE * 100e3
            jammer = np.sqrt(jammer_power) * np.exp(
                1j * (2*np.pi*f0*t + 0.5 * 2*np.pi*mod))
        else:
            return signal

        return (signal + jammer.astype(np.complex64)).astype(np.complex64)


# ==================== 功率谱干扰检测 ====================
class PSDInterferenceDetector:
    """基于功率谱特征的干扰检测(二值判决)"""

    def __init__(self, fft_size=1024):
        self.fft_size = fft_size
        self.noise_floor_history = deque(maxlen=30)

    def _estimate_noise_floor(self, psd_db):
        """估计噪声基底(取最低20%的功率)"""
        sorted_psd = np.sort(psd_db)
        n_noise = max(1, len(sorted_psd) // 5)
        return np.mean(sorted_psd[:n_noise])

    def _extract_features(self, signal_data):
        """提取功率谱多维特征"""
        N = self.fft_size
        if len(signal_data) < N:
            return None

        data = signal_data[:N]
        windowed = data * np.hanning(N)
        spectrum = np.fft.fftshift(np.fft.fft(windowed, n=N))
        psd = np.abs(spectrum) ** 2
        psd_db = 10 * np.log10(psd + 1e-12)

        noise_floor = self._estimate_noise_floor(psd_db)
        self.noise_floor_history.append(noise_floor)
        avg_noise = np.mean(self.noise_floor_history)

        # 特征1: 谱峰值与噪底比
        peak_to_noise = np.max(psd_db) - avg_noise

        # 特征2: 频率重心偏移量
        freqs = np.fft.fftshift(np.fft.fftfreq(N, d=1.0/SAMPLE_RATE))
        centroid = np.sum(freqs * psd) / (np.sum(psd) + 1e-12)

        # 特征3: 归一化谱熵
        norm_psd = psd / (np.sum(psd) + 1e-12)
        entropy = -np.sum(norm_psd * np.log2(norm_psd + 1e-12))
        max_entropy = np.log2(N)
        norm_entropy = entropy / max_entropy

        # 特征4: 带外泄露功率比
        center = N // 2
        bw = N // 4
        in_band = np.sum(psd[center-bw:center+bw])
        total = np.sum(psd)
        out_of_band_ratio = 1 - in_band / (total + 1e-12)

        # 特征5: 谱峰集中度 (top-10功率bin占比)
        sorted_psd = np.sort(psd)[::-1]
        top10_ratio = np.sum(sorted_psd[:10]) / (np.sum(psd) + 1e-12)

        return {
            'peak_to_noise': peak_to_noise,
            'centroid_offset': abs(centroid),
            'norm_entropy': norm_entropy,
            'out_of_band_ratio': out_of_band_ratio,
            'top10_ratio': top10_ratio,
        }

    def detect(self, signal_data) -> tuple:
        """
        检测是否存在干扰
        返回 (has_interference: bool, confidence: float, features: dict)
        """
        features = self._extract_features(signal_data)
        if features is None:
            return False, 0.0, {}

        # 自适应阈值判决
        # 正常QPSK信号: peak_to_noise ~40-45dB, entropy ~0.75
        # 窄带干扰: peak_to_noise >50dB, entropy <0.5 (谱能量集中)
        # 宽带干扰: peak_to_noise >50dB, entropy变化
        has_interference = False
        score = 0.0

        # 判据1: 谱峰噪比异常高 (>50dB = 明显有额外强信号)
        if features['peak_to_noise'] > 50:
            score += 0.5
            has_interference = True

        # 判据2: 谱熵异常低 (能量高度集中 = 窄带干扰主导)
        if features['norm_entropy'] < 0.5:
            score += 0.3
            has_interference = True

        # 判据3: top-10频率bin占比过高 (能量过于集中)
        if features.get('top10_ratio', 0) > 0.15:
            score += 0.2
            has_interference = True

        confidence = min(score, 1.0)
        return has_interference, confidence, features


# ==================== 传输控制器 ====================
class TransmissionController:
    """自适应传输控制器"""

    def __init__(self):
        self.current_profile = INTERFERENCE_PROFILES['none']
        self.current_severity = 'none'
        self.target_quality = self.current_profile['quality']
        self.target_fps = self.current_profile['fps']
        self.target_fec = self.current_profile['fec_redundancy']

        # 平滑过渡参数
        self._smooth_quality = self.target_quality
        self._smooth_fps = self.target_fps
        self._quality_alpha = 0.3  # 平滑系数

        # 状态统计
        self.stats = {
            'frames_sent': 0,
            'frames_received': 0,
            'frames_lost': 0,
            'interference_events': 0,
            'profile_changes': 0,
        }
        self._interference_count = 0
        self._no_interference_count = 0

    def update(self, interference_type: str, confidence: float):
        """根据干扰识别结果更新传输参数"""
        severity = JAMMER_SEVERITY.get(interference_type, 'none')

        # 置信度过滤
        if confidence < 0.3:
            severity = 'none'

        # 滞后计数器，避免频繁切换
        if severity != 'none':
            self._interference_count += 1
            self._no_interference_count = 0
        else:
            self._no_interference_count += 1
            self._interference_count = 0

        # 确认干扰状态(连续5次检测到干扰才切换，8次无干扰才恢复)
        if self._interference_count >= 5:
            new_severity = severity
        elif self._no_interference_count >= 8:
            new_severity = 'none'
        else:
            new_severity = self.current_severity

        if new_severity != self.current_severity:
            self.current_severity = new_severity
            self.current_profile = INTERFERENCE_PROFILES[new_severity]
            self.target_quality = self.current_profile['quality']
            self.target_fps = self.current_profile['fps']
            self.target_fec = self.current_profile['fec_redundancy']
            self.stats['profile_changes'] += 1
            if new_severity != 'none':
                self.stats['interference_events'] += 1

    def get_smoothed_params(self):
        """获取平滑后的传输参数"""
        alpha = self._quality_alpha
        self._smooth_quality = (alpha * self.target_quality +
                                (1 - alpha) * self._smooth_quality)
        self._smooth_fps = (alpha * self.target_fps +
                            (1 - alpha) * self._smooth_fps)
        return {
            'quality': int(self._smooth_quality),
            'fps': max(10, int(self._smooth_fps)),
            'fec_redundancy': self.target_fec,
            'severity': self.current_severity,
            'label': self.current_profile['label'],
        }


# ==================== 主系统 ====================
class VideoTransmissionSystem:
    """视频传输系统主类"""

    def __init__(self, mode='sim', source='test', serial='serial=7MFTKFU',
                 model_path=None, ccnn_path=None, no_gui=False):
        self.mode = mode
        self.serial = serial
        self.no_gui = no_gui
        self.running = False

        # USRP模式使用更低的视频参数以适配信道带宽
        # QPSK@500ksps = 1Mbps = 125KB/s
        # quality=25 -> ~5KB/frame -> ~40ms/frame -> 可支持~25fps
        if mode == 'full':
            self.vid_width = 160
            self.vid_height = 120
            self.base_quality = 30
            self.base_fps = 5
        else:
            self.vid_width = DEFAULT_WIDTH
            self.vid_height = DEFAULT_HEIGHT
            self.base_quality = DEFAULT_JPEG_QUALITY
            self.base_fps = DEFAULT_FPS

        # 子模块
        self.video_source = VideoSource(source, self.vid_width, self.vid_height)
        self.video_codec = VideoCodec()
        self.qpsk = QPSKModem()
        self.psd_detector = PSDInterferenceDetector()
        self.controller = TransmissionController()
        # 覆盖控制器的初始参数
        if mode == 'full':
            self.controller.target_quality = self.base_quality
            self.controller.target_fps = self.base_fps
            self.controller._smooth_quality = self.base_quality
            self.controller._smooth_fps = self.base_fps
        self.fec_codec = FECCodec(redundancy=1)

        # CCNN干扰识别器(可选)
        self.ccnn_detector = None
        self._init_ccnn(model_path, ccnn_path)

        # 仿真信道
        self.sim_channel = SimulatedChannel(snr_db=20)

        # USRP(仅full模式)
        self.usrp_trx = None

        # 数据队列
        self.tx_frame_queue = queue.Queue(maxsize=5)
        self.rx_frame_queue = queue.Queue(maxsize=5)
        self.display_queue = queue.Queue(maxsize=10)

        # 统计信息
        self.frame_seq = 0
        self.last_interference_type = '无干扰'
        self.last_interference_conf = 0.0
        self.last_psd_features = {}
        self.latency_ms = 0.0
        self.last_tx_frame = None

        print(f"\n{'='*65}")
        print(f"  面向信号干扰检测与识别的视频传输系统")
        print(f"  模式: {mode} | 视频源: {source}")
        print(f"  分辨率: {self.vid_width}x{self.vid_height} | 调制: QPSK")
        print(f"  采样率: {SAMPLE_RATE/1e6:.0f}MHz | 中心频率: "
              f"{CENTER_FREQ/1e9:.2f}GHz")
        print(f"  基准质量: Q={self.base_quality} FPS={self.base_fps}")
        if self.ccnn_detector:
            print(f"  CCNN干扰识别: 已加载")
        else:
            print(f"  CCNN干扰识别: 未加载(仅功率谱检测)")
        print(f"{'='*65}\n")

    def _init_ccnn(self, model_path, ccnn_path):
        """初始化CCNN干扰识别模型"""
        if model_path is None:
            model_path = os.path.join(
                SCRIPT_DIR, '..', 'CCNN', '2_models', 'best',
                'ccnn_epoch_86_acc_0.9913.pth')
        if ccnn_path is None:
            ccnn_path = os.path.join(
                SCRIPT_DIR, '..', 'CCNN', '3_scripts', 'training', 'CCNN.py')

        try:
            from cnn_interference_detector import InterferenceDetector
            self.ccnn_detector = InterferenceDetector(
                model_path=model_path, ccnn_py=ccnn_path, num_classes=6)
            print("[CCNN] 模型加载成功")
        except Exception as e:
            print(f"[CCNN] 模型加载失败: {e}")
            print("[CCNN] 将仅使用功率谱特征检测")
            import traceback; traceback.print_exc()

    def _init_usrp(self):
        """初始化USRP硬件"""
        try:
            import uhd as _uhd
            self._uhd = _uhd  # 保存引用供其他方法使用
            self.usrp_trx = {
                'usrp': _uhd.usrp.MultiUSRP(self.serial),
            }
            usrp = self.usrp_trx['usrp']
            # TX配置
            usrp.set_tx_rate(SAMPLE_RATE, 0)
            usrp.set_tx_freq(
                _uhd.libpyuhd.types.tune_request(CENTER_FREQ), 0)
            usrp.set_tx_gain(TX_GAIN, 0)
            usrp.set_tx_antenna("TX/RX", 0)
            self.usrp_trx['tx_stream'] = usrp.get_tx_stream(
                _uhd.usrp.StreamArgs("fc32", "sc16"))

            # RX配置
            usrp.set_rx_rate(SAMPLE_RATE, 0)
            usrp.set_rx_freq(
                _uhd.libpyuhd.types.tune_request(CENTER_FREQ), 0)
            usrp.set_rx_gain(RX_GAIN, 0)
            usrp.set_rx_antenna("RX2", 0)
            sa = _uhd.usrp.StreamArgs("fc32", "sc16")
            sa.args = "recv_frame_size=8192,num_recv_frames=1024"
            self.usrp_trx['rx_stream'] = usrp.get_rx_stream(sa)
            self.usrp_trx['rx_queue'] = queue.Queue(maxsize=200)

            print("[USRP] B210 初始化完成")
        except Exception as e:
            print(f"[USRP] 初始化失败: {e}")
            self.usrp_trx = None

    # ============ TX链路 ============

    def _tx_pipeline(self, frame: np.ndarray, quality: int,
                     fec_redundancy: int) -> np.ndarray:
        """TX完整处理链: 帧 -> JPEG -> 分包 -> FEC -> QPSK -> 基带信号"""
        t0 = time.time()

        # JPEG编码
        jpeg_data = self.video_codec.encode(frame, quality)

        # 分包
        pkts = PacketFramer.frame(jpeg_data, self.frame_seq)
        self.frame_seq = (self.frame_seq + 1) % 65536

        # FEC编码
        self.fec_codec = FECCodec(redundancy=fec_redundancy)
        pkts = self.fec_codec.encode(pkts)

        # 合并所有包为一个字节流
        all_bytes = b''.join(pkts)

        # 添加包分隔标记(用于接收端同步)
        delimiter = struct.pack('<I', 0x55AA55AA)
        frame_bytes = delimiter + struct.pack('<I', len(all_bytes)) + all_bytes

        # QPSK调制
        baseband = self.qpsk.modulate(frame_bytes)

        # 添加前导序列
        baseband = self.qpsk.add_preamble(baseband)

        # 帧间静默间隔(帮助RX分离帧)
        silence = np.zeros(int(SAMPLE_RATE * 0.02), dtype=np.complex64)
        baseband = np.concatenate([baseband, silence])

        self.latency_ms = (time.time() - t0) * 1000
        return baseband

    def _tx_thread(self):
        """TX线程: 持续获取视频帧并处理"""
        params = self.controller.get_smoothed_params()
        last_params_change = 0

        while self.running:
            params = self.controller.get_smoothed_params()
            frame_interval = 1.0 / params['fps']

            # 获取视频帧
            frame = self.video_source.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            self.last_tx_frame = frame.copy()

            # TX处理链
            try:
                baseband = self._tx_pipeline(
                    frame, params['quality'], params['fec_redundancy'])
            except Exception as e:
                print(f"[TX] 编码错误: {e}")
                time.sleep(frame_interval)
                continue

            if self.mode == 'full' and self.usrp_trx:
                # USRP发送
                try:
                    meta = self._uhd.types.TXMetadata()
                    meta.start_of_burst = True
                    meta.end_of_burst = True
                    self.usrp_trx['tx_stream'].send(
                        baseband.reshape(1, -1), meta)
                except Exception as e:
                    print(f"[TX] USRP发送错误: {e}")
                # 等待发送完成: 信号长度/采样率 + 缓冲
                tx_time = len(baseband) / SAMPLE_RATE
                time.sleep(tx_time + 0.05)
            elif self.mode == 'sim':
                # 仿真信道
                rx_signal = self.sim_channel.apply(baseband)
                self.tx_frame_queue.put((frame, rx_signal, params))

            # 帧率控制
            time.sleep(max(0, frame_interval - 0.01))

            self.controller.stats['frames_sent'] += 1

    # ============ RX链路 ============

    def _rx_pipeline(self, signal: np.ndarray) -> tuple:
        """RX完整处理链: 基带信号 -> AGC -> 频偏校正 -> QPSK解调 -> 去包 -> JPEG解码 -> 帧"""
        # AGC归一化
        signal = self.qpsk.agc(signal)

        # 频偏估计与校正
        cfo = self.qpsk.estimate_cfo(signal)
        signal = self.qpsk.correct_cfo(signal, cfo)

        # 尝试检测前导序列，但即使失败也继续解调
        preamble_pos = self.qpsk.detect_preamble(signal)
        if preamble_pos is not None:
            signal = signal[preamble_pos:]

        # QPSK解调
        demod_bytes = self.qpsk.demodulate(signal)
        if len(demod_bytes) < 8:
            return None, "解调数据过短"

        # 寻找帧分隔标记
        delimiter = struct.pack('<I', 0x55AA55AA)
        delim_pos = demod_bytes.find(delimiter)
        if delim_pos < 0:
            return None, "分隔标记未找到"

        # 读取数据长度
        if delim_pos + 8 > len(demod_bytes):
            return None, "数据长度字段不完整"
        data_len = struct.unpack('<I', demod_bytes[delim_pos+4:delim_pos+8])[0]

        # 合理性检查
        if data_len == 0 or data_len > 500000:
            return None, f"数据长度异常({data_len})"

        # 提取有效载荷
        data_start = delim_pos + 8
        data_end = min(data_start + data_len, len(demod_bytes))

        payload = demod_bytes[data_start:data_end]
        if len(payload) < data_len * 0.5:
            return None, f"数据不完整({len(payload)}/{data_len})"

        # 逐包解帧并重组
        offset = 0
        packets = {}
        lost_indices = []
        pkt_idx = 0

        while offset + HEADER_SIZE + 2 <= len(payload):
            result = PacketFramer.deframe(payload[offset:])
            if result is None:
                # 尝试找下一个同步字
                next_sync = payload[offset+2:].find(
                    struct.pack('<I', SYNC_WORD))
                if next_sync >= 0:
                    lost_indices.append(pkt_idx)
                    offset += 2 + next_sync
                    pkt_idx += 1
                    continue
                else:
                    lost_indices.append(pkt_idx)
                    break

            seq, idx, total, pkt_payload = result
            packets[idx] = payload[offset:offset + HEADER_SIZE +
                                   len(pkt_payload) + 2]
            offset += HEADER_SIZE + len(pkt_payload) + 2
            pkt_idx += 1

            if idx == total - 1:
                break

        # FEC解码
        pkt_list = [packets.get(i) for i in range(max(packets.keys()) + 1
                                                    if packets else 0)]
        if lost_indices:
            fec = FECCodec(redundancy=2)
            pkt_list = fec.decode(pkt_list, lost_indices)

        # 按序重组JPEG数据
        jpeg_chunks = []
        for i in range(len(pkt_list)):
            if pkt_list[i] is not None:
                result = PacketFramer.deframe(pkt_list[i])
                if result:
                    _, idx, _, pkt_payload = result
                    jpeg_chunks.append(pkt_payload)

        if not jpeg_chunks:
            return None, "无有效数据包"

        jpeg_data = b''.join(jpeg_chunks)

        # JPEG解码
        frame = self.video_codec.decode(jpeg_data)
        return frame, "OK"

    def _rx_thread(self):
        """RX线程: 接收信号并处理"""
        if self.mode == 'full' and self.usrp_trx:
            self._rx_thread_usrp()
        elif self.mode == 'sim':
            self._rx_thread_sim()

    def _rx_thread_sim(self):
        """仿真模式RX线程"""
        while self.running:
            try:
                tx_frame, rx_signal, params = self.tx_frame_queue.get(
                    timeout=1.0)
            except queue.Empty:
                continue

            # 干扰检测与识别
            self._monitor_interference(rx_signal)

            # RX处理链
            rx_frame, status = self._rx_pipeline(rx_signal)

            if rx_frame is None:
                rx_frame = np.full((DEFAULT_HEIGHT, DEFAULT_WIDTH, 3),
                                   60, dtype=np.uint8)
                cv2.putText(rx_frame, f"Decode Failed: {status}",
                            (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                            (0, 0, 255), 1)

            self.controller.stats['frames_received'] += 1
            self.display_queue.put((tx_frame, rx_frame, params))

    def _rx_thread_usrp(self):
        """USRP模式RX线程"""
        _uhd = self._uhd

        # 启动RX流
        cmd = _uhd.types.StreamCMD(_uhd.types.StreamMode.start_cont)
        cmd.stream_now = True
        self.usrp_trx['rx_stream'].issue_stream_cmd(cmd)

        buf = np.zeros((1, BUFFER_SIZE), dtype=np.complex64)
        meta = _uhd.types.RXMetadata()
        signal_buffer = []

        while self.running:
            try:
                n = self.usrp_trx['rx_stream'].recv(buf, meta)
                if n > 0:
                    chunk = buf[0][:n].copy()
                    signal_buffer.extend(chunk)

                    # 积累足够数据后处理(0.1s块，减少延迟)
                    rx_chunk = int(SAMPLE_RATE * 0.1)
                    if len(signal_buffer) >= rx_chunk:
                        signal_data = np.array(signal_buffer[:rx_chunk],
                                               dtype=np.complex64)
                        signal_buffer = signal_buffer[rx_chunk // 2:]

                        # 干扰监测
                        self._monitor_interference(signal_data)

                        # RX处理链
                        rx_frame, status = self._rx_pipeline(signal_data)
                        params = self.controller.get_smoothed_params()

                        tx_frame = self.last_tx_frame
                        if tx_frame is None:
                            tx_frame = np.zeros((DEFAULT_HEIGHT, DEFAULT_WIDTH, 3),
                                                dtype=np.uint8)

                        if rx_frame is None:
                            rx_frame = np.full(
                                (DEFAULT_HEIGHT, DEFAULT_WIDTH, 3),
                                60, dtype=np.uint8)

                        self.controller.stats['frames_received'] += 1
                        self.display_queue.put((tx_frame, rx_frame, params))

            except Exception as e:
                print(f"[RX] USRP接收错误: {e}")
                time.sleep(0.1)

    # ============ 干扰监测 ============

    def _monitor_interference(self, signal_data):
        """执行干扰检测与识别"""
        if len(signal_data) < 1024:
            return

        # 第1级: 功率谱特征检测(二值判决)
        has_intf, psd_conf, features = self.psd_detector.detect(signal_data)
        self.last_psd_features = features

        if has_intf and psd_conf > 0.3:
            # 第2级: CCNN干扰类型识别
            if self.ccnn_detector:
                try:
                    intf_type, cnn_conf = self.ccnn_detector.detect(signal_data)
                    self.last_interference_type = intf_type
                    self.last_interference_conf = cnn_conf
                    self.controller.update(intf_type, cnn_conf)
                    return
                except Exception as e:
                    pass

            # 无CCNN时仅用功率谱检测
            self.last_interference_type = '窄带AM(NAM)'  # 默认
            self.last_interference_conf = psd_conf
            self.controller.update('窄带AM(NAM)', psd_conf)
        else:
            self.last_interference_type = '无干扰'
            self.last_interference_conf = 1.0 - psd_conf
            self.controller.update('无干扰', 1.0)

    # ============ 显示线程 ============

    def _display_thread(self):
        """显示线程: 实时展示TX/RX视频和系统状态"""
        while self.running:
            try:
                tx_frame, rx_frame, params = self.display_queue.get(
                    timeout=1.0)
            except queue.Empty:
                continue

            if self.no_gui:
                continue

            # 构建显示画面
            display = self._build_display(tx_frame, rx_frame, params)

            cv2.imshow("Video Transmission System", display)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                self.running = False
                break

            # 仿真模式下支持按键注入干扰
            if self.mode == 'sim':
                self._handle_sim_keys(key)

        try:
            cv2.destroyAllWindows()
        except cv2.error:
            pass

    def _build_display(self, tx_frame, rx_frame, params):
        """构建显示画面"""
        h, w = DEFAULT_HEIGHT, DEFAULT_WIDTH

        # 在TX帧上添加标签
        tx_display = tx_frame.copy()
        cv2.putText(tx_display, "TX (Original)", (5, 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        cv2.putText(tx_display, f"Q={params['quality']} FPS={params['fps']}",
                    (5, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        # 在RX帧上添加标签
        rx_display = rx_frame.copy()
        cv2.putText(rx_display, "RX (Received)", (5, 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)

        # 状态信息面板
        panel_h = 130
        panel = np.full((panel_h, w * 2, 3), 30, dtype=np.uint8)

        # 干扰状态
        intf_color = (0, 255, 0) if self.last_interference_type == '无干扰' \
            else (0, 0, 255)
        cv2.putText(panel,
                    f"Interference: {self.last_interference_type} "
                    f"({self.last_interference_conf:.1%})",
                    (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, intf_color, 1)

        # 自适应策略
        profile_color = {
            'none': (0, 255, 0), 'mild': (0, 255, 255),
            'moderate': (0, 165, 255), 'severe': (0, 0, 255)
        }.get(params['severity'], (255, 255, 255))
        cv2.putText(panel, f"Profile: {params['label']}",
                    (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    profile_color, 1)

        # PSD特征
        if self.last_psd_features:
            feat = self.last_psd_features
            cv2.putText(panel,
                        f"PSD: PeakNoise={feat.get('peak_to_noise',0):.1f}dB "
                        f"Entropy={feat.get('norm_entropy',0):.3f}",
                        (10, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                        (200, 200, 200), 1)

        # 统计信息
        stats = self.controller.stats
        cv2.putText(panel,
                    f"TX:{stats['frames_sent']} RX:{stats['frames_received']} "
                    f"FEC:{params['fec_redundancy']}x "
                    f"Latency:{self.latency_ms:.1f}ms",
                    (10, 91), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                    (180, 180, 180), 1)

        # 操作提示
        cv2.putText(panel,
                    "Keys: 1-6=Inject Jammer  0=Clear  Q=Quit",
                    (10, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                    (120, 120, 120), 1)

        # 合并: TX | RX | Panel
        top = np.hstack([tx_display, rx_display])
        display = np.vstack([top, panel])
        return display

    def _handle_sim_keys(self, key):
        """处理仿真模式按键"""
        jammer_map = {
            ord('1'): ('stj', 10, '单音干扰(STJ)'),
            ord('2'): ('mtj', 10, '多音干扰(MTJ)'),
            ord('3'): ('lfm', 10, '扫频干扰(LFM)'),
            ord('4'): ('nam', 10, '窄带AM(NAM)'),
            ord('5'): ('nfm', 10, '窄带FM(NFM)'),
            ord('6'): ('sin', 10, '正弦波(SIN)'),
        }

        if key in jammer_map:
            jtype, jsr, label = jammer_map[key]
            self.sim_channel.jsr_db = jsr
            self.sim_channel.jammer_type = jtype
            print(f"[SIM] 注入干扰: {label} JSR={jsr}dB")
        elif key == ord('0'):
            self.sim_channel.jsr_db = None
            self.sim_channel.jammer_type = None
            print("[SIM] 清除干扰")

    # ============ 系统控制 ============

    def start(self):
        """启动系统"""
        self.running = True

        if self.mode == 'full':
            self._init_usrp()
            if not self.usrp_trx:
                print("[ERROR] USRP初始化失败，切换到仿真模式")
                self.mode = 'sim'

        # 启动各线程
        threads = [
            threading.Thread(target=self._tx_thread, daemon=True,
                             name='TX'),
            threading.Thread(target=self._rx_thread, daemon=True,
                             name='RX'),
            threading.Thread(target=self._display_thread, daemon=True,
                             name='Display'),
        ]
        for t in threads:
            t.start()

        print("[System] 系统已启动\n")

    def stop(self):
        """停止系统"""
        if not self.running:
            return
        self.running = False
        self.video_source.release()
        # 停止USRP RX流
        if self.usrp_trx and self.usrp_trx.get('rx_stream'):
            try:
                _uhd = self._uhd
                cmd = _uhd.types.StreamCMD(_uhd.types.StreamMode.stop_cont)
                self.usrp_trx['rx_stream'].issue_stream_cmd(cmd)
            except Exception:
                pass
        # 等待线程退出
        time.sleep(0.3)
        try:
            cv2.destroyAllWindows()
        except cv2.error:
            pass
        print("[System] 系统已停止")

    def run(self, duration=None):
        """运行系统"""
        self.start()
        try:
            if duration:
                time.sleep(duration)
            else:
                while self.running:
                    time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[Interrupt] 用户中断")
        finally:
            self.stop()

    def print_final_stats(self):
        """打印最终统计"""
        stats = self.controller.stats
        params = self.controller.get_smoothed_params()
        print(f"\n{'='*55}")
        print(f"  运行统计")
        print(f"{'='*55}")
        print(f"  发送帧数: {stats['frames_sent']}")
        print(f"  接收帧数: {stats['frames_received']}")
        print(f"  干扰事件: {stats['interference_events']}")
        print(f"  策略切换: {stats['profile_changes']}次")
        print(f"  最终策略: {params['label']}")
        print(f"{'='*55}")


# ==================== 命令行入口 ====================
def parse_args():
    parser = argparse.ArgumentParser(
        description='面向信号干扰检测与识别的视频传输系统')

    parser.add_argument('--mode', choices=['full', 'sim'], default='sim',
                        help='运行模式: full=USRP实机, sim=仿真')
    parser.add_argument('--source', default='test',
                        help='视频源: test=测试图案, camera=摄像头, '
                             '或视频文件路径')
    parser.add_argument('--serial', default='serial=7MFTKFU',
                        help='USRP序列号(仅full模式)')
    parser.add_argument('--model', default=None,
                        help='CCNN模型路径(.pth)')
    parser.add_argument('--ccnn', default=None,
                        help='CCNN.py路径')
    parser.add_argument('--duration', type=float, default=None,
                        help='运行时长(秒), 不指定则持续运行')
    parser.add_argument('--no-gui', action='store_true',
                        help='禁用GUI(仅后台处理)')

    return parser.parse_args()


def main():
    args = parse_args()

    system = VideoTransmissionSystem(
        mode=args.mode,
        source=args.source,
        serial=args.serial,
        model_path=args.model,
        ccnn_path=args.ccnn,
        no_gui=args.no_gui,
    )

    try:
        system.run(duration=args.duration)
    finally:
        system.print_final_stats()


if __name__ == '__main__':
    main()
