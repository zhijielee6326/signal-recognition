#!/usr/bin/env python3
"""
JSR Sweep 测试 + 画图
测试 CCNN 在不同 JSR 下对 6 类干扰的识别准确率，输出表格 + JSR-准确率曲线。
"""

import os
import sys
import json
import argparse
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

# 导入CCNN模型定义
ccnn_script = os.path.join(SCRIPT_DIR, '..', 'CCNN', '3_scripts', 'training', 'CCNN.py')
import importlib.util
spec = importlib.util.spec_from_file_location("ccnn_module", ccnn_script)
ccnn_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccnn_mod)
CCNN = ccnn_mod.CCNN

from usrp_model_test_v4 import GEN_MAP, gen_psk, FS, RS, N, T

JAMMER_TYPES = ['lfm', 'mtj', 'nam', 'nfm', 'stj', 'sin']
TYPE_NAMES = ['LFM', 'MTJ', 'NAM', 'NFM', 'STJ', 'SIN', 'CLEAN']
SWEEP_JSR = [-6, -4, -2, 0, 2, 4, 6, 8, 10, 12, 14, 16]
SAMPLES_PER_TYPE = 100


def generate_test_data(jsr_db, n_per_type=100):
    """为指定JSR生成测试数据"""
    all_data = []
    all_labels = []
    for type_idx, jtype in enumerate(JAMMER_TYPES):
        for _ in range(n_per_type):
            from usrp_model_test_v4 import make_combined
            sig = make_combined(jtype, jsr_db=jsr_db)
            iq = np.vstack([sig.real[np.newaxis, :], sig.imag[np.newaxis, :]]).astype(np.float32)
            all_data.append(iq)
            all_labels.append(type_idx)

    data = np.stack(all_data)
    labels = np.array(all_labels, dtype=np.int32)
    return data, labels


def test_at_jsr(model, jsr_db, n_per_type=100, device='cpu'):
    """在指定JSR下测试模型准确率（含clean信号）"""
    data, labels = generate_test_data(jsr_db, n_per_type)

    # 添加clean信号测试（label=6）
    for _ in range(n_per_type):
        mod = np.random.choice(['BPSK', 'QPSK', '8PSK'])
        sig = gen_psk(mod)
        iq = np.vstack([sig.real[np.newaxis, :], sig.imag[np.newaxis, :]]).astype(np.float32)
        data = np.concatenate([data, iq[np.newaxis]], axis=0)
        labels = np.append(labels, 6)

    # 功率归一化（与训练时一致）
    complex_sig = data[:, 0, :] + 1j * data[:, 1, :]
    power = np.mean(np.abs(complex_sig) ** 2, axis=1, keepdims=True)
    data_norm = data / np.sqrt(power[:, np.newaxis, :] + 1e-8)

    # 批量推理
    tensor_data = torch.from_numpy(data_norm).float()
    dataset = torch.utils.data.TensorDataset(tensor_data, torch.from_numpy(labels).long())
    loader = DataLoader(dataset, batch_size=64, shuffle=False)

    model.eval()
    all_preds = []
    all_labels = []
    with torch.no_grad():
        for batch_data, batch_labels in loader:
            batch_data = batch_data.to(device)
            out = model(batch_data)
            preds = out.argmax(dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_labels.extend(batch_labels.numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    # 各类准确率
    type_accs = {}
    for i, name in enumerate(TYPE_NAMES):
        mask = all_labels == i
        if mask.sum() > 0:
            type_accs[name] = (all_preds[mask] == i).mean() * 100
        else:
            type_accs[name] = 0.0

    # 总体准确率
    overall = (all_preds == all_labels).mean() * 100

    return overall, type_accs


def plot_jsr_curve(results, save_path):
    """画JSR-准确率曲线（论文核心图）"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans']
    matplotlib.rcParams['font.family'] = 'sans-serif'
    matplotlib.rcParams['axes.unicode_minus'] = False

    jsr_values = [r['jsr_db'] for r in results]

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
    markers = ['o', 's', '^', 'D', 'v', 'p', 'h']

    fig, ax = plt.subplots(figsize=(10, 6))

    for i, name in enumerate(TYPE_NAMES):
        accs = [r['type_accs'][name] for r in results]
        ax.plot(jsr_values, accs, color=colors[i], marker=markers[i],
                linewidth=2, markersize=6, label=name)

    # 总体准确率（黑色粗线）
    overall = [r['overall'] for r in results]
    ax.plot(jsr_values, overall, color='black', marker='*', linewidth=2.5,
            markersize=10, label='Overall')

    ax.set_xlabel('JSR (dB)', fontsize=13)
    ax.set_ylabel('Accuracy (%)', fontsize=13)
    ax.set_title('CCNN Interference Recognition vs JSR', fontsize=14)
    ax.set_xticks(jsr_values)
    ax.set_yticks(range(0, 101, 10))
    ax.set_ylim(-5, 105)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right', fontsize=11)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    print(f"JSR sweep 曲线已保存: {save_path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='JSR Sweep 测试')
    parser.add_argument('--model', type=str, required=True, help='模型 .pth 文件路径')
    parser.add_argument('--num-classes', type=int, default=7, help='类别数')
    parser.add_argument('--output', type=str,
                        default=os.path.join(SCRIPT_DIR, 'jsr_sweep_results.json'),
                        help='结果JSON输出路径')
    parser.add_argument('--device', type=str, default='cpu')
    args = parser.parse_args()

    print(f"加载模型: {args.model}")
    model = CCNN(num_classes=args.num_classes)
    model.load_state_dict(torch.load(args.model, map_location=args.device))
    model = model.to(args.device)
    model.eval()
    print("模型加载成功")

    results = []

    # 打印表头
    header = f"{'JSR(dB)':>8} | " + " | ".join(f"{n:>6}" for n in TYPE_NAMES) + f" | {'Overall':>8}"
    print(f"\n{'='*len(header)}")
    print(header)
    print(f"{'='*len(header)}")

    for jsr_db in SWEEP_JSR:
        overall, type_accs = test_at_jsr(model, jsr_db, SAMPLES_PER_TYPE, args.device)

        row = f"{jsr_db:>+8} | " + " | ".join(f"{type_accs[n]:>5.1f}%" for n in TYPE_NAMES) + f" | {overall:>7.1f}%"
        print(row)

        results.append({
            'jsr_db': jsr_db,
            'overall': round(overall, 2),
            'type_accs': {k: round(v, 2) for k, v in type_accs.items()}
        })

    print(f"{'='*len(header)}\n")

    # 保存JSON
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"结果已保存: {args.output}")

    # 画图
    plot_path = args.output.replace('.json', '.png')
    plot_jsr_curve(results, plot_path)


if __name__ == '__main__':
    main()
