#!/usr/bin/env python3
"""
简化版USRP自发自收测试
用于快速验证单一干扰类型
"""

import numpy as np
import sys
import os
sys.path.append(os.path.dirname(__file__))

from cnn_interference_detector import InterferenceDetector

def test_with_simulated_data():
    """使用模拟数据快速测试检测器"""
    print("="*60)
    print("CCNN检测器快速测试（模拟数据）")
    print("="*60)

    # 加载模型
    model_path = "../CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth"
    print(f"\n加载模型: {model_path}")

    try:
        detector = InterferenceDetector(model_path, num_classes=6)
        print("✓ 模型加载成功")
    except Exception as e:
        print(f"✗ 模型加载失败: {e}")
        return

    # 生成测试信号
    sample_rate = 2e6
    duration = 0.05
    n_samples = int(sample_rate * duration)

    print(f"\n生成测试信号 ({n_samples} 样本)...")

    # 测试1: 干净信号
    print("\n[测试1] 干净QPSK信号")
    clean_signal = np.random.randn(n_samples) + 1j * np.random.randn(n_samples)
    clean_signal *= 0.5
    intf_type, conf = detector.detect(clean_signal)
    print(f"  检测结果: {intf_type} (置信度: {conf:.2f})")

    # 测试2: 单音干扰
    print("\n[测试2] 单音干扰")
    t = np.arange(n_samples) / sample_rate
    tone = 2.0 * np.exp(1j * 2 * np.pi * 500e3 * t)
    tone_signal = clean_signal + tone
    intf_type, conf = detector.detect(tone_signal)
    print(f"  检测结果: {intf_type} (置信度: {conf:.2f})")

    # 测试3: 扫频干扰
    print("\n[测试3] 扫频干扰")
    f0, f1 = 100e3, 900e3
    k = (f1 - f0) / duration
    chirp = 1.5 * np.exp(1j * 2 * np.pi * (f0 * t + 0.5 * k * t**2))
    chirp_signal = clean_signal + chirp
    intf_type, conf = detector.detect(chirp_signal)
    print(f"  检测结果: {intf_type} (置信度: {conf:.2f})")

    # 测试4: 宽带噪声
    print("\n[测试4] 宽带噪声干扰")
    noise = 2.0 * (np.random.randn(n_samples) + 1j * np.random.randn(n_samples))
    noise_signal = clean_signal + noise
    intf_type, conf = detector.detect(noise_signal)
    print(f"  检测结果: {intf_type} (置信度: {conf:.2f})")

    print("\n" + "="*60)
    print("测试完成！")
    print("\n如果检测结果符合预期，可以继续进行USRP硬件测试。")
    print("运行: python3 usrp_loopback_test.py")
    print("="*60)

if __name__ == "__main__":
    test_with_simulated_data()
