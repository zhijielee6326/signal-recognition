#!/usr/bin/env python3
"""
生成宽JSR范围的CCNN训练数据（7类：6类干扰 + 无干扰）
使用 usrp_model_test_v4.py 的 Python 生成器，确保训练/SimChannel/推理端一致。
"""

import os
import sys
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from usrp_model_test_v4 import GEN_MAP, make_combined, gen_psk, FS, RS, N, T

# 6类干扰 label 0-5，+ 无干扰 label 6
JAMMER_TYPES = ['lfm', 'mtj', 'nam', 'nfm', 'stj', 'sin']
MODULATIONS = ['BPSK', 'QPSK', '8PSK']
NUM_CLASSES = 7  # 6类干扰 + 1类无干扰

# 输出目录
OUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', 'CCNN', '1_datasets', 'train_wide_jsr'
)

# JSR分布（dB -> 每类样本数）
JSR_SAMPLES = {
    -2: 150,
     0: 250,
     2: 250,
     4: 250,
     6: 200,
     8: 200,
    10: 200,
    12: 150,
    14: 150,
    16: 100,
}

# 无干扰样本数（与干扰总样本数相当，保证类别平衡）
CLEAN_SAMPLES = sum(JSR_SAMPLES.values())  # 1900

# sweep测试覆盖的JSR范围
SWEEP_JSR_VALUES = [-6, -4, -2, 0, 2, 4, 6, 8, 10, 12, 14, 16]
SWEEP_SAMPLES = 100


def generate_main_training_data():
    """生成主训练+测试数据（7类，80/20随机切分）"""
    all_data = []
    all_labels = []

    total_intf = sum(JSR_SAMPLES.values()) * len(JAMMER_TYPES)
    total = total_intf + CLEAN_SAMPLES
    print(f"将生成 {total} 个样本 (6类干扰 x {sum(JSR_SAMPLES.values())} + {CLEAN_SAMPLES}无干扰)")
    print(f"JSR分布: {dict(JSR_SAMPLES)}")

    count = 0
    # 6类干扰数据
    for jsr_db, n_per_type in JSR_SAMPLES.items():
        for type_idx, jtype in enumerate(JAMMER_TYPES):
            for _ in range(n_per_type):
                sig = make_combined(jtype, jsr_db=jsr_db)
                iq = np.vstack([sig.real[np.newaxis, :], sig.imag[np.newaxis, :]]).astype(np.float32)
                all_data.append(iq)
                all_labels.append(type_idx)
                count += 1
                if count % 500 == 0:
                    print(f"  已生成 {count}/{total} ...")

    # 无干扰数据（纯PSK载波，随机调制方式）
    print(f"  生成无干扰样本 {CLEAN_SAMPLES}...")
    for _ in range(CLEAN_SAMPLES):
        mod = np.random.choice(MODULATIONS)
        sig = gen_psk(mod)
        iq = np.vstack([sig.real[np.newaxis, :], sig.imag[np.newaxis, :]]).astype(np.float32)
        all_data.append(iq)
        all_labels.append(6)  # label=6: 无干扰
        count += 1
        if count % 500 == 0:
            print(f"  已生成 {count}/{total} ...")

    data_arr = np.stack(all_data)
    label_arr = np.array(all_labels, dtype=np.int32)

    print(f"总数据: {data_arr.shape}, 标签: {label_arr.shape}")
    unique, counts = np.unique(label_arr, return_counts=True)
    names = JAMMER_TYPES + ['clean']
    for u, c in zip(unique, counts):
        print(f"  label {u} ({names[u]}): {c}")

    # 随机80/20切分
    indices = np.random.permutation(len(data_arr))
    split = int(0.8 * len(data_arr))
    train_idx, test_idx = indices[:split], indices[split:]

    train_data, train_label = data_arr[train_idx], label_arr[train_idx]
    test_data, test_label = data_arr[test_idx], label_arr[test_idx]

    train_path = os.path.join(OUT_DIR, 'train_split.npz')
    test_path = os.path.join(OUT_DIR, 'test_split.npz')

    np.savez(train_path, data=train_data, label=train_label)
    np.savez(test_path, data=test_data, label=test_label)

    print(f"\n训练集: {train_data.shape} -> {train_path}")
    print(f"测试集: {test_data.shape} -> {test_path}")


def generate_sweep_test_data():
    """生成每个JSR值的独立测试文件"""
    sweep_dir = os.path.join(OUT_DIR, 'sweep_test')
    os.makedirs(sweep_dir, exist_ok=True)

    for jsr_db in SWEEP_JSR_VALUES:
        all_data = []
        all_labels = []

        # 6类干扰
        for type_idx, jtype in enumerate(JAMMER_TYPES):
            for _ in range(SWEEP_SAMPLES):
                sig = make_combined(jtype, jsr_db=jsr_db)
                iq = np.vstack([sig.real[np.newaxis, :], sig.imag[np.newaxis, :]]).astype(np.float32)
                all_data.append(iq)
                all_labels.append(type_idx)

        # 无干扰
        for _ in range(SWEEP_SAMPLES):
            mod = np.random.choice(MODULATIONS)
            sig = gen_psk(mod)
            iq = np.vstack([sig.real[np.newaxis, :], sig.imag[np.newaxis, :]]).astype(np.float32)
            all_data.append(iq)
            all_labels.append(6)

        data_arr = np.stack(all_data)
        label_arr = np.array(all_labels, dtype=np.int32)

        fname = f'sweep_jsr_{jsr_db:+04d}dB.npz'
        path = os.path.join(sweep_dir, fname)
        np.savez(path, data=data_arr, label=label_arr)
        print(f"  JSR={jsr_db:+3d}dB: {data_arr.shape} -> {fname}")

    print(f"\nJSR sweep测试数据已保存到 {sweep_dir}/")


if __name__ == '__main__':
    np.random.seed(42)
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=" * 60)
    print("步骤1: 生成主训练/测试数据 (7类)")
    print("=" * 60)
    generate_main_training_data()

    print("\n" + "=" * 60)
    print("步骤2: 生成JSR sweep测试数据")
    print("=" * 60)
    generate_sweep_test_data()

    print("\n全部完成！")
