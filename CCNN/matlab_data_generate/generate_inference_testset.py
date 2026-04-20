"""
推理测试集生成脚本
从MATLAB数据中随机提取测试样本（与训练集无重复）
"""

import os
import sys
import io

# 设置标准输出为UTF-8编码（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

import numpy as np
import scipy.io as sio
import random
from collections import defaultdict


def generate_inference_testset(mat_folder, output_path, samples_per_type=100, seed=42):
    """
    从MATLAB文件中生成推理测试集
    
    参数:
        mat_folder: 包含.mat文件的文件夹路径
        output_path: 输出的.npz文件路径
        samples_per_type: 每种信号类型的样本数
        seed: 随机种子，用于可重复性
    """
    
    random.seed(seed)
    np.random.seed(seed)
    
    # 干扰类型到标签的映射
    type_mapping = {
        "LFM": 0,
        "MTJ": 1,
        "NAM": 2,
        "NFM": 3,
        "STJ": 4,
        "SIN": 5
    }
    
    # 按信号类型分组
    signal_files = defaultdict(list)
    
    print("📂 扫描MATLAB数据文件...")
    print(f"源文件夹: {mat_folder}\n")
    
    # 遍历所有.mat文件，按类型分组
    for filename in sorted(os.listdir(mat_folder)):
        if filename.endswith('.mat'):
            # 解析文件名获取干扰类型
            parts = filename.split('_')
            if len(parts) < 2:
                continue
            
            intf_type = parts[1]
            if intf_type not in type_mapping:
                continue
            
            signal_files[intf_type].append(filename)
    
    # 打印发现的文件统计
    print("📊 发现的信号类型及文件数:\n")
    total_files = 0
    for signal_type in sorted(type_mapping.keys()):
        count = len(signal_files[signal_type])
        total_files += count
        print(f"  {signal_type:<6} : {count:>4} 个文件")
    print(f"\n  总计  : {total_files:>4} 个文件\n")
    
    # 从每种类型中随机选择样本
    test_data = []
    test_labels = []
    selected_summary = {}
    
    print("🔀 随机选择测试样本...\n")
    
    for signal_type in sorted(type_mapping.keys()):
        files = signal_files[signal_type]
        
        if not files:
            print(f"  ⚠️  {signal_type}: 无文件可选")
            continue
        
        # 限制选择数量不超过可用文件数
        num_select = min(samples_per_type, len(files))
        selected_files = random.sample(files, num_select)
        selected_summary[signal_type] = {
            'total': len(files),
            'selected': num_select,
            'percentage': f"{(num_select/len(files)*100):.1f}%"
        }
        
        label = type_mapping[signal_type]
        processed = 0
        
        for filename in selected_files:
            try:
                file_path = os.path.join(mat_folder, filename)
                mat_data = sio.loadmat(file_path)
                complex_data = mat_data['data'].flatten()
                
                # 分离实部和虚部
                real_part = np.real(complex_data).reshape(1, -1)
                imag_part = np.imag(complex_data).reshape(1, -1)
                formatted_data = np.vstack([real_part, imag_part]).astype(np.float32)
                
                test_data.append(formatted_data)
                test_labels.append(label)
                processed += 1
            except Exception as e:
                print(f"    ⚠️  处理文件 {filename} 失败: {e}")
                continue
        
        print(f"  ✓ {signal_type}: 成功处理 {processed}/{num_select} 个样本")
    
    # 保存汇总信息
    print(f"\n📊 选择统计:")
    print("-" * 60)
    print(f"{'信号类型':<10} {'总文件':<10} {'选择':<10} {'比例':<10}")
    print("-" * 60)
    for signal_type in sorted(type_mapping.keys()):
        if signal_type in selected_summary:
            s = selected_summary[signal_type]
            print(f"{signal_type:<10} {s['total']:<10} {s['selected']:<10} {s['percentage']:<10}")
    print("-" * 60)
    
    # 创建混合测试集（打乱顺序）
    if test_data:
        # 打乱数据顺序
        indices = np.random.permutation(len(test_data))
        test_data = [test_data[i] for i in indices]
        test_labels = [test_labels[i] for i in indices]
        
        # 转换为numpy数组
        data_array = np.stack(test_data, axis=0)
        label_array = np.array(test_labels, dtype=np.int32)
        
        # 保存测试集
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        np.savez(output_path, data=data_array, label=label_array)
        
        print(f"\n✅ 推理测试集生成成功!")
        print(f"   文件路径: {output_path}")
        print(f"   样本总数: {len(label_array)}")
        print(f"   数据形状: {data_array.shape}")
        print(f"   标签形状: {label_array.shape}")
        
        # 打印类别分布
        print(f"\n📈 测试集类别分布:")
        print("-" * 40)
        for signal_type in sorted(type_mapping.keys()):
            label = type_mapping[signal_type]
            count = (label_array == label).sum()
            if count > 0:
                percentage = f"{(count/len(label_array)*100):.1f}%"
                print(f"  {signal_type}: {count:>4} 样本 ({percentage})")
        print("-" * 40)
        
        return data_array, label_array
    else:
        print("❌ 没有成功加载任何数据!")
        return None, None


def generate_individual_test_files(mat_folder, output_dir, samples_per_type=50):
    """
    为每种信号类型生成单独的测试文件（便于单类推理测试）
    
    参数:
        mat_folder: 包含.mat文件的文件夹路径
        output_dir: 输出目录
        samples_per_type: 每种类型的样本数
    """
    
    random.seed(42)
    np.random.seed(42)
    
    # 干扰类型到标签的映射
    type_mapping = {
        "LFM": 0,
        "MTJ": 1,
        "NAM": 2,
        "NFM": 3,
        "STJ": 4,
        "SIN": 5
    }
    
    # 按信号类型分组
    signal_files = defaultdict(list)
    
    for filename in sorted(os.listdir(mat_folder)):
        if filename.endswith('.mat'):
            parts = filename.split('_')
            if len(parts) < 2:
                continue
            intf_type = parts[1]
            if intf_type not in type_mapping:
                continue
            signal_files[intf_type].append(filename)
    
    print("📁 生成单类测试文件...\n")
    
    # 为每种类型生成单独的文件
    for signal_type in sorted(type_mapping.keys()):
        files = signal_files[signal_type]
        if not files:
            continue
        
        num_select = min(samples_per_type, len(files))
        selected_files = random.sample(files, num_select)
        
        test_data = []
        test_labels = []
        label = type_mapping[signal_type]
        
        for filename in selected_files:
            try:
                file_path = os.path.join(mat_folder, filename)
                mat_data = sio.loadmat(file_path)
                complex_data = mat_data['data'].flatten()
                
                real_part = np.real(complex_data).reshape(1, -1)
                imag_part = np.imag(complex_data).reshape(1, -1)
                formatted_data = np.vstack([real_part, imag_part]).astype(np.float32)
                
                test_data.append(formatted_data)
                test_labels.append(label)
            except Exception as e:
                continue
        
        if test_data:
            data_array = np.stack(test_data, axis=0)
            label_array = np.array(test_labels, dtype=np.int32)
            
            output_file = os.path.join(output_dir, f"inference_test_{signal_type}.npz")
            os.makedirs(output_dir, exist_ok=True)
            np.savez(output_file, data=data_array, label=label_array)
            
            print(f"  ✓ {signal_type}: {len(label_array)} 样本 -> {os.path.basename(output_file)}")
    
    print()


def main():
    # 配置路径
    mat_folder = r"C:\Users\m1889\Desktop\project\干扰信号识别\信号识别\signal\matlab_data_generate\data"
    output_dir = r"C:\Users\m1889\Desktop\project\干扰信号识别\信号识别\signal\CCNN\inference_test"
    output_combined = os.path.join(output_dir, "inference_test_combined.npz")
    
    print("=" * 70)
    print("🚀 推理测试集生成工具")
    print("=" * 70)
    print()
    
    # 生成混合测试集
    print("【第一步】生成混合推理测试集")
    print("=" * 70)
    generate_inference_testset(
        mat_folder,
        output_combined,
        samples_per_type=100,
        seed=42
    )
    
    print()
    print()
    
    # 生成单类测试文件
    print("【第二步】生成单类推理测试文件")
    print("=" * 70)
    generate_individual_test_files(
        mat_folder,
        output_dir,
        samples_per_type=50
    )
    
    print()
    print("=" * 70)
    print("✅ 所有推理测试集已生成完毕！")
    print("=" * 70)
    print()
    print("📝 生成的文件列表:")
    print(f"  1. {output_combined}")
    print(f"  2. {output_dir}/inference_test_*.npz (各类别)")
    print()
    print("💡 使用推理测试集:")
    print(f"  python CCNN.py --mode infer --data-path {output_dir}")
    print()


if __name__ == '__main__':
    main()
