#!/usr/bin/env python3
"""
CCNN干扰检测器 - 修复版
修复要点：
  1. 固定输入长度5000（由模型结构决定）
  2. 推理前做功率归一化（与训练MyDataset一致）
  3. 模型加载失败时明确报错，不静默fallback
"""
import numpy as np
import torch
import torch.nn as nn
import importlib.util, os, sys, json
from datetime import datetime

REQUIRED_LENGTH = 5000  # 由CNN步长链严格决定，不能改

class InterferenceDetector:
    def __init__(self, model_path=None, ccnn_py=None, num_classes=6):
        """
        model_path : .pth文件路径
        ccnn_py    : CCNN.py路径（含类定义）
        num_classes: 默认6类
        """
        self.num_classes = num_classes
        if num_classes >= 7:
            self.interference_types = [
                "扫频干扰(LFM)",   # 0
                "多音干扰(MTJ)",   # 1
                "窄带AM(NAM)",     # 2
                "窄带FM(NFM)",     # 3
                "单音干扰(STJ)",   # 4
                "正弦波(SIN)",     # 5
                "无干扰",          # 6
            ]
        else:
            self.interference_types = [
                "扫频干扰(LFM)",   # 0
                "多音干扰(MTJ)",   # 1
                "窄带AM(NAM)",     # 2
                "窄带FM(NFM)",     # 3
                "单音干扰(STJ)",   # 4
                "正弦波(SIN)"      # 5
            ]
        self.use_cnn = False
        self.detection_history = []
        self.last_probs = None  # (num_classes,) softmax probabilities
        self.stats = {"total_samples": 0, "interference_count": 0}

        if model_path and ccnn_py:
            self._load_model(model_path, ccnn_py)
        elif model_path:
            # 自动在同目录往上找CCNN.py
            auto = self._find_ccnn_py(model_path)
            if auto:
                self._load_model(model_path, auto)
            else:
                raise FileNotFoundError(
                    "找不到CCNN.py，请用 ccnn_py= 参数手动指定路径"
                )
        else:
            print("⚠️  未提供模型路径，使用规则检测（仅用于调试）")

    # ------------------------------------------------------------------ #
    def _find_ccnn_py(self, model_path):
        """从model_path向上搜索CCNN.py"""
        base = os.path.dirname(os.path.abspath(model_path))
        for _ in range(6):
            candidate = os.path.join(base, "3_scripts", "training", "CCNN.py")
            if os.path.exists(candidate):
                return candidate
            base = os.path.dirname(base)
        return None

    def _load_model(self, model_path, ccnn_py):
        print(f"正在加载模型...")
        print(f"  模型文件: {model_path}")
        print(f"  定义文件: {ccnn_py}")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        if not os.path.exists(ccnn_py):
            raise FileNotFoundError(f"CCNN.py不存在: {ccnn_py}")

        # 动态加载CCNN类
        spec = importlib.util.spec_from_file_location("ccnn_module", ccnn_py)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # 实例化并加载权重
        model = mod.CCNN(num_classes=self.num_classes)
        ckpt  = torch.load(model_path, map_location="cpu")

        if isinstance(ckpt, dict):
            if "state_dict" in ckpt:
                model.load_state_dict(ckpt["state_dict"])
            else:
                model.load_state_dict(ckpt)          # 直接是OrderedDict
        elif isinstance(ckpt, nn.Module):
            model = ckpt
        else:
            raise ValueError(f"未知的checkpoint格式: {type(ckpt)}")

        model.eval()
        self.model = model
        self.use_cnn = True

        # 验证：跑一次dummy推理确保长度正确
        with torch.no_grad():
            dummy = torch.randn(1, 2, REQUIRED_LENGTH)
            out   = model(dummy)
            assert out.shape == (1, self.num_classes), f"输出shape异常: {out.shape}"

        params = sum(p.numel() for p in model.parameters())
        print(f"✓ 模型加载成功！参数量: {params:,}，期望输入长度: {REQUIRED_LENGTH}")

    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize(sig: np.ndarray) -> np.ndarray:
        """功率归一化，与MyDataset.__getitem__保持一致"""
        power = np.mean(np.abs(sig) ** 2)
        return sig / (np.sqrt(power) + 1e-8)

    def _prepare_input(self, signal_data: np.ndarray) -> np.ndarray:
        """
        把任意长度的IQ信号裁剪/拼接成(2, 5000)并归一化
        """
        sig = np.asarray(signal_data, dtype=np.complex64).flatten()

        if len(sig) >= REQUIRED_LENGTH:
            sig = sig[:REQUIRED_LENGTH]
        else:
            # 数据不足时循环填充（比补零更接近真实信号统计特性）
            repeats = REQUIRED_LENGTH // len(sig) + 1
            sig = np.tile(sig, repeats)[:REQUIRED_LENGTH]

        sig = self._normalize(sig)
        return np.vstack([sig.real, sig.imag])   # (2, 5000)

    # ------------------------------------------------------------------ #
    def detect(self, signal_data, spectrum_data=None):
        """
        返回 (干扰类型str, 置信度float)
        signal_data: 1-D complex64 数组，长度≥1024即可
        """
        self.stats["total_samples"] += len(signal_data)

        if self.use_cnn:
            x = self._prepare_input(signal_data)            # (2, 5000)
            tensor = torch.from_numpy(x[None]).float()      # (1, 2, 5000)

            with torch.no_grad():
                out   = self.model(tensor)
                probs = torch.softmax(out, dim=1)
                conf, pred = torch.max(probs, 1)

            self.last_probs = probs.numpy()[0]  # (num_classes,)
            itype = self.interference_types[pred.item()]
            confidence = conf.item()
        else:
            itype, confidence = self._rule_based(signal_data, spectrum_data)

        if confidence > 0.5:
            self.stats["interference_count"] += 1
            self.detection_history.append({
                "timestamp": datetime.now().isoformat(),
                "type": itype,
                "confidence": confidence
            })

        return itype, confidence

    # ------------------------------------------------------------------ #
    def _rule_based(self, signal_data, spectrum_data=None):
        """无模型时的备用规则检测（仅调试用）"""
        mag = np.abs(signal_data)
        papr = np.max(mag) / (np.mean(mag) + 1e-10)

        spec = np.abs(np.fft.fft(signal_data[:512]))**2 if spectrum_data is None else spectrum_data
        peak_mean_ratio = np.max(spec) / (np.mean(spec) + 1e-10)

        if papr > 15:
            return "脉冲干扰", min(papr/30, 1.0)
        elif peak_mean_ratio > 100:
            return "单音干扰(STJ)", min(peak_mean_ratio/200, 1.0)
        else:
            return "无干扰", 0.0

    # ------------------------------------------------------------------ #
    def print_statistics(self):
        print("\n" + "="*60)
        print(f"总样本数: {self.stats['total_samples']:,}")
        print(f"检测到干扰: {self.stats['interference_count']}次")
        type_counts = {}
        for d in self.detection_history:
            type_counts[d['type']] = type_counts.get(d['type'], 0) + 1
        for k, v in type_counts.items():
            print(f"  {k}: {v}次 ({v/len(self.detection_history)*100:.1f}%)")
        print("="*60)


# ============================================================ #
# 离线验证（不需要USRP，直接运行此文件）
# ============================================================ #
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help=".pth模型路径")
    parser.add_argument("--ccnn",  required=True, help="CCNN.py路径")
    parser.add_argument("--classes", type=int, default=6)
    args = parser.parse_args()

    detector = InterferenceDetector(args.model, args.ccnn, args.classes)

    # 用仿真信号测试6类
    FS = 2e6
    N  = REQUIRED_LENGTH
    t  = np.arange(N) / FS
    labels = ["扫频干扰(LFM)", "多音干扰(MTJ)", "窄带AM(NAM)",
              "窄带FM(NFM)",  "单音干扰(STJ)",  "正弦波(SIN)"]

    def sim(kind):
        base = 0.3*(np.random.randn(N)+1j*np.random.randn(N))
        if kind == 0:   # LFM
            k = (900e3-100e3)/(N/FS)
            return base + 1.5*np.exp(1j*2*np.pi*(100e3*t+0.5*k*t**2))
        elif kind == 1: # MTJ
            return base + sum(1.5*np.exp(1j*2*np.pi*f*t) for f in [300e3,500e3,700e3])
        elif kind == 2: # NAM
            return base + (1+0.8*np.random.randn(N))*np.exp(1j*2*np.pi*300e3*t)
        elif kind == 3: # NFM
            ph = np.cumsum(0.5*np.random.randn(N))/FS*200e3*2*np.pi
            return base + 1.5*np.exp(1j*ph)
        elif kind == 4: # STJ
            return base + 2.0*np.exp(1j*2*np.pi*500e3*t)
        elif kind == 5: # SIN
            return 2.5*np.exp(1j*2*np.pi*400e3*t)

    print("\n===== 离线仿真验证 =====")
    correct = 0
    for i, label in enumerate(labels):
        sig = sim(i).astype(np.complex64)
        pred, conf = detector.detect(sig)
        ok = pred == label
        correct += ok
        print(f"{'✓' if ok else '✗'} [{label}] → 预测: {pred} ({conf:.1%})")

    print(f"\n离线准确率: {correct}/{len(labels)} = {correct/len(labels):.1%}")
