#!/usr/bin/env python3
"""
USRP B210 稳定收发与干扰检测系统
- 采样率 1 MHz（可调）
- 双线程解耦，避免溢出
- 实时功率显示，功率门限检测
- 适用于天线对天线真实环境测试
"""

import numpy as np
import uhd
import time
import threading
import queue
from datetime import datetime

# ==================== 参数配置 ====================
SAMPLE_RATE = 1e6          # 1 MHz 采样率（可降低至 500e3 进一步减轻压力）
TX_FREQ = 1e9               # 1 GHz 中心频率
RX_FREQ = 1e9
TX_GAIN = 25                # 发送增益（天线使用时 20-30 均可）
RX_GAIN = 40                # 接收增益（可提高至 45 增强接收）
CARRIER_FREQ = 250e3        # 发送端载波频率（需 < SAMPLE_RATE/2）
NOISE_FLOOR_DB = -70        # 环境底噪估计值（根据实际修改，可通过启动时测量获得）
POWER_THRESHOLD_DB = -65    # 功率门限：高于此值才进行干扰检测
SPECTRAL_ENTROPY_THRESH = 0.95  # 宽带噪声谱熵阈值

# ==================== 视频发送模块 ====================
class VideoTransmitter:
    def __init__(self, serial="serial=7MFTKFU"):
        self.serial = serial
        self.tx_freq = TX_FREQ
        self.sample_rate = SAMPLE_RATE
        self.tx_gain = TX_GAIN
        self.carrier_freq = CARRIER_FREQ
        
        self.usrp = uhd.usrp.MultiUSRP(self.serial)
        self.setup_usrp()
        
        self.is_transmitting = False
        self.transmit_thread = None
        
        print(f"[发送] 频率 {self.tx_freq/1e6} MHz | 采样率 {self.sample_rate/1e6} MHz | 增益 {self.tx_gain} dB | 载波 {self.carrier_freq/1e3} kHz")

    def setup_usrp(self):
        self.usrp.set_tx_rate(self.sample_rate, 0)
        self.usrp.set_tx_freq(uhd.libpyuhd.types.tune_request(self.tx_freq), 0)
        self.usrp.set_tx_gain(self.tx_gain, 0)
        self.usrp.set_tx_antenna("TX/RX", 0)
        self.tx_stream = self.usrp.get_tx_stream(uhd.usrp.StreamArgs("fc32", "sc16"))

    def generate_frame(self, frame_num):
        """生成模拟视频帧（QPSK调制）"""
        frame_samples = int(self.sample_rate * 0.033)  # 33ms一帧，约30fps
        t = np.arange(frame_samples) / self.sample_rate
        
        # QPSK符号生成（符号率 = 200 ksps）
        symbol_rate = 200e3
        samples_per_symbol = int(self.sample_rate / symbol_rate)
        num_symbols = frame_samples // samples_per_symbol
        symbols = np.random.choice([1+1j, 1-1j, -1+1j, -1-1j], num_symbols) * 0.7
        symbols_upsampled = np.repeat(symbols, samples_per_symbol)
        
        # 长度对齐
        if len(symbols_upsampled) > frame_samples:
            symbols_upsampled = symbols_upsampled[:frame_samples]
        else:
            symbols_upsampled = np.pad(symbols_upsampled, (0, frame_samples - len(symbols_upsampled)), 'constant')
        
        # 调制到载波
        signal = symbols_upsampled * np.exp(1j * 2 * np.pi * self.carrier_freq * t)
        
        # 添加同步头（可选）
        sync = np.array([1, -1, 1, -1, 1, -1, 1, -1], dtype=np.complex64)
        sync = np.tile(sync, 32)
        full_signal = np.concatenate([sync, signal])
        return full_signal.astype(np.complex64)

    def transmit_loop(self):
        frame_count = 0
        while self.is_transmitting:
            signal = self.generate_frame(frame_count)
            buffer = signal.reshape(1, -1)
            metadata = uhd.types.TXMetadata()
            metadata.start_of_burst = True
            metadata.end_of_burst = True
            self.tx_stream.send(buffer, metadata)
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"[发送] 已发送 {frame_count} 帧")

    def start(self):
        if not self.is_transmitting:
            self.is_transmitting = True
            self.transmit_thread = threading.Thread(target=self.transmit_loop, daemon=True)
            self.transmit_thread.start()
            print("[发送] 启动")

    def stop(self):
        self.is_transmitting = False
        if self.transmit_thread:
            self.transmit_thread.join(timeout=1)
        print("[发送] 停止")

# ==================== 信号接收模块 ====================
class SignalReceiver:
    def __init__(self, serial="serial=7MFTKFU"):
        self.serial = serial
        self.rx_freq = RX_FREQ
        self.sample_rate = SAMPLE_RATE
        self.rx_gain = RX_GAIN
        
        self.usrp = uhd.usrp.MultiUSRP(self.serial)
        self.setup_usrp()
        
        self.data_queue = queue.Queue(maxsize=100)  # 缓冲队列
        self.is_receiving = False
        self.receive_thread = None
        self.overflow_count = 0
        
        print(f"[接收] 频率 {self.rx_freq/1e6} MHz | 采样率 {self.sample_rate/1e6} MHz | 增益 {self.rx_gain} dB")

    def setup_usrp(self):
        self.usrp.set_rx_rate(self.sample_rate, 0)
        self.usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(self.rx_freq), 0)
        self.usrp.set_rx_gain(self.rx_gain, 0)
        self.usrp.set_rx_antenna("RX2", 0)
        # 增大缓冲区
       # self.usrp.set_rx_buffer(50e6)  # 50 MB
        stream_args = uhd.usrp.StreamArgs("fc32", "sc16")
        stream_args.args = "recv_frame_size=4096,num_recv_frames=512"
        self.rx_stream = self.usrp.get_rx_stream(stream_args)

    def receive_loop(self):
        # 启动连续接收
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        stream_cmd.stream_now = True
        self.rx_stream.issue_stream_cmd(stream_cmd)
        
        buffer = np.zeros((1, 4096), dtype=np.complex64)
        metadata = uhd.types.RXMetadata()
        while self.is_receiving:
            try:
                samples = self.rx_stream.recv(buffer, metadata)
                if metadata.error_code == uhd.types.RXMetadataErrorCode.overflow:
                    self.overflow_count += 1
                    if self.overflow_count % 10 == 0:
                        print(f"[接收] 溢出次数: {self.overflow_count}")
                elif metadata.error_code != uhd.types.RXMetadataErrorCode.none:
                    print(f"[接收] 错误: {metadata.error_code}")
                
                if samples > 0:
                    data = buffer[0][:samples].copy()
                    # 放入队列，若队列满则丢弃旧数据（防止阻塞）
                    try:
                        self.data_queue.put(data, block=False)
                    except queue.Full:
                        # 队列满，丢弃最旧的数据
                        try:
                            self.data_queue.get_nowait()
                            self.data_queue.put(data, block=False)
                        except:
                            pass
            except Exception as e:
                print(f"[接收] 异常: {e}")
                time.sleep(0.1)

    def start(self):
        if not self.is_receiving:
            self.is_receiving = True
            self.receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
            self.receive_thread.start()
            print("[接收] 启动")

    def stop(self):
        self.is_receiving = False
        if self.receive_thread:
            self.receive_thread.join(timeout=2)
        # 停止流
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        self.rx_stream.issue_stream_cmd(stream_cmd)
        print("[接收] 停止")

# ==================== 干扰检测模块（增强版）====================
class InterferenceDetector:
    def __init__(self):
        self.detection_history = []
        self.interference_types = [
            "无干扰", "单音干扰", "多音干扰", "扫频干扰", "脉冲干扰", "宽带噪声"
        ]
        self.stats = {
            "total_samples": 0,
            "interference_count": 0,
            "last_detection": None
        }
        self.background_power_db = NOISE_FLOOR_DB  # 背景噪声估计

    def estimate_noise_floor(self, data):
        """实时估计噪声基底（取最低10%的功率平均值）"""
        power = np.abs(data)**2
        sorted_power = np.sort(power)
        noise_samples = sorted_power[:len(sorted_power)//10]
        noise_power_db = 10 * np.log10(np.mean(noise_samples) + 1e-12)
        return noise_power_db

    def extract_features(self, signal_data):
        if len(signal_data) < 1024:
            return None
        magnitude = np.abs(signal_data)
        features = np.zeros(10, dtype=np.float32)
        features[0] = np.mean(magnitude)
        features[1] = np.std(magnitude)
        features[2] = np.max(magnitude)
        features[3] = features[2] / (features[0] + 1e-10)

        # 频谱特征
        spectrum = np.fft.fft(signal_data[:1024])
        spectrum_power = np.abs(spectrum)**2
        features[4] = np.mean(spectrum_power)
        features[5] = np.std(spectrum_power)
        features[6] = np.max(spectrum_power)

        # 谱熵
        norm_power = spectrum_power / (np.sum(spectrum_power) + 1e-10)
        entropy = -np.sum(norm_power * np.log(norm_power + 1e-10))
        features[7] = entropy / np.log(len(spectrum_power))

        # 谱质心
        indices = np.arange(len(spectrum_power))
        centroid = np.sum(indices * spectrum_power) / (np.sum(spectrum_power) + 1e-10)
        features[8] = centroid / len(spectrum_power)

        # 谱扩展
        spread = np.sqrt(np.sum((indices - centroid)**2 * spectrum_power) / (np.sum(spectrum_power) + 1e-10))
        features[9] = spread / len(spectrum_power)

        return features

    def detect(self, signal_data):
        """返回 (干扰类型, 置信度)"""
        if len(signal_data) < 1024:
            return "无干扰", 0.0

        # 计算当前功率
        power_db = 10 * np.log10(np.mean(np.abs(signal_data)**2) + 1e-12)
        
        # 功率门限：如果功率低于背景噪声+3dB，认为是无信号或仅噪声
        if power_db < self.background_power_db + 3:
            return "无干扰", 0.0

        features = self.extract_features(signal_data)
        if features is None:
            return "无干扰", 0.0

        self.stats["total_samples"] += len(signal_data)

        # 规则检测（带更严格的阈值）
        if features[3] > 15:  # 高峰均比 -> 脉冲
            intf_type = "脉冲干扰"
            confidence = min(features[3] / 30, 1.0)
        elif features[6] / features[4] > 100:  # 峰值远大于均值 -> 单音
            intf_type = "单音干扰"
            confidence = min(features[6] / features[4] / 200, 1.0)
        elif features[7] > SPECTRAL_ENTROPY_THRESH:  # 高谱熵 -> 宽带噪声
            intf_type = "宽带噪声"
            confidence = features[7]
        elif 0.3 < features[8] < 0.7:  # 中等谱质心 -> 扫频
            intf_type = "扫频干扰"
            confidence = 0.7
        else:
            intf_type = "无干扰"
            confidence = 0.0

        if intf_type != "无干扰":
            self.stats["interference_count"] += 1
            self.stats["last_detection"] = datetime.now().strftime("%H:%M:%S")
            self.detection_history.append({
                "timestamp": datetime.now().isoformat(),
                "type": intf_type,
                "confidence": confidence,
                "power_db": power_db,
                "features": features.tolist()
            })
        return intf_type, confidence

# ==================== 主系统 ====================
class StableSystem:
    def __init__(self):
        print("="*70)
        print("USRP B210 稳定收发与干扰检测系统")
        print("="*70)
        self.transmitter = VideoTransmitter()
        self.receiver = SignalReceiver()
        self.detector = InterferenceDetector()
        self.is_running = False
        self.process_thread = None
        self.log_queue = queue.Queue()  # 用于UI输出（这里简单打印）

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def process_loop(self):
        """从接收队列取数据并分析"""
        buffer = []  # 累积数据
        last_power_time = 0
        while self.is_running:
            try:
                # 从队列取数据（等待最多0.5秒）
                data = self.receiver.data_queue.get(timeout=0.5)
                buffer.extend(data)
                
                # 每0.5秒分析一次
                now = time.time()
                if len(buffer) >= int(SAMPLE_RATE * 0.5):  # 累积0.5秒数据
                    # 取最新的0.5秒数据
                    segment = np.array(buffer[-int(SAMPLE_RATE*0.5):])
                    
                    # 更新背景噪声估计（取最低10%功率）
                    self.detector.background_power_db = self.detector.estimate_noise_floor(segment)
                    
                    # 检测干扰
                    intf_type, conf = self.detector.detect(segment)
                    
                    # 计算功率（用于显示）
                    power_db = 10 * np.log10(np.mean(np.abs(segment)**2) + 1e-12)
                    
                    # 每5秒打印一次状态
                    if now - last_power_time >= 5:
                        self.log(f"功率 {power_db:.1f} dB | 噪声基底 {self.detector.background_power_db:.1f} dB | 检测: {intf_type} ({conf:.2f})")
                        last_power_time = now
                    
                    # 如果检测到干扰且置信度高，额外打印
                    if intf_type != "无干扰" and conf > 0.7:
                        self.log(f"检测到干扰: {intf_type} (置信度 {conf:.2f})")
                    
                    # 清空buffer，但保留最后0.1秒数据用于连续分析
                    buffer = buffer[-int(SAMPLE_RATE*0.1):]
            except queue.Empty:
                continue
            except Exception as e:
                self.log(f"处理错误: {e}")

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.transmitter.start()
            self.receiver.start()
            self.process_thread = threading.Thread(target=self.process_loop, daemon=True)
            self.process_thread.start()
            self.log("系统已启动")

    def stop(self):
        self.is_running = False
        self.transmitter.stop()
        self.receiver.stop()
        if self.process_thread:
            self.process_thread.join(timeout=2)
        self.log("系统已停止")

# ==================== 主程序 ====================
if __name__ == "__main__":
    import sys
    try:
        system = StableSystem()
        system.start()
        print("\n系统运行中，按 Ctrl+C 停止...\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n用户中断")
        system.stop()
        sys.exit(0)
