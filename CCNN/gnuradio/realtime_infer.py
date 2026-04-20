#!/usr/bin/env python3
"""
实时推理脚本：从 USRP 接收 IQ，构造成 (2,5000) 的样本并用训练好的 CCNN 做推理（CPU）
在运行前请在 Ubuntu 中安装 `requirements.txt` 中列出的包，并确保 `uhd` 可用。
用法示例（在 CCNN/gnuradio 目录下运行）:
  python3 realtime_infer.py --model ../2_models/best/ccnn_epoch_86_acc_0.9913.pth --num-classes 6
"""
import os
import sys
import time
import argparse
import numpy as np
import torch
import importlib.util

# 导入本目录下的 SignalReceiver
from signal_receiver import SignalReceiver


def load_ccnn_from_path(path, repo_root, num_classes=6, device='cpu'):
    # 动态加载训练脚本中的模型类定义
    training_py = os.path.join(repo_root, 'CCNN', '3_scripts', 'training', 'CCNN.py')
    spec = importlib.util.spec_from_file_location("ccnn_module", training_py)
    ccnn_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ccnn_mod)

    model = ccnn_mod.CCNN(num_classes=num_classes)
    state = torch.load(path, map_location=device)
    # state might be state_dict or full model
    if isinstance(state, dict) and not any(k.startswith('_') for k in state.keys()):
        try:
            model.load_state_dict(state)
        except Exception:
            # try nested
            model.load_state_dict(state.get('state_dict', state))
    else:
        # attempt to load full model
        try:
            model = state
        except Exception:
            pass

    model = model.to(device)
    model.eval()
    return model


def build_input_from_complex(complex_arr, target_len=5000):
    # complex_arr: 1D complex numpy array
    x = complex_arr
    if x.size < target_len:
        pad = np.zeros(target_len - x.size, dtype=x.dtype)
        x = np.concatenate([x, pad])
    else:
        x = x[-target_len:]

    stacked = np.vstack([np.real(x), np.imag(x)]).astype(np.float32)
    # 功率归一化
    power = np.mean(np.abs(x) ** 2)
    if power > 0:
        stacked = stacked / np.sqrt(power)
    return stacked


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True, help='路径到 .pth 模型文件')
    parser.add_argument('--serial', default=None, help='USRP serial string (可选)')
    parser.add_argument('--num-classes', type=int, default=6)
    parser.add_argument('--interval', type=float, default=1.0, help='推理间隔（秒）')
    parser.add_argument('--device', choices=['cpu','cuda'], default='cpu')
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    print(f"加载模型: {args.model} (device={args.device})")
    model = load_ccnn_from_path(args.model, repo_root, num_classes=args.num_classes, device=args.device)

    # 初始化接收器
    receiver = SignalReceiver(serial=args.serial) if args.serial else SignalReceiver()
    receiver.start_receiving()

    try:
        print("开始实时推理循环，按 Ctrl-C 停止...")
        while True:
            # 等待足够数据
            data = receiver.get_recent_data(5000)
            if len(data) < 1024:
                time.sleep(0.2)
                continue

            complex_np = np.array(data[-5000:])
            sample = build_input_from_complex(complex_np, target_len=5000)

            tensor = torch.from_numpy(sample).unsqueeze(0)  # (1,2,5000)
            with torch.no_grad():
                out = model(tensor)
                probs = torch.softmax(out, dim=1).cpu().numpy().squeeze()
                pred = int(np.argmax(probs))
                conf = float(probs[pred])

            print(f"推理结果: 类别={pred} 置信度={conf:.3f}")
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print('\n已停止')
    finally:
        receiver.stop_receiving()


if __name__ == '__main__':
    main()
