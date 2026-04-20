import os

# 解决 OpenMP 库冲突问题
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

import numpy as np
import scipy.io as sio
import torch
from torch.utils.data import Dataset, DataLoader


# 数据转换函数（将.mat文件转换为.npz格式）
def convert_mat_to_npz(mat_folder, output_path):
    """将MATLAB生成的.mat文件转换为.npz格式

    参数:
        mat_folder: 包含.mat文件的文件夹路径
        output_path: 输出的.npz文件路径
    """
    # 干扰类型到标签的映射 (支持5类和6类)
    type_mapping = {
        "LFM": 0,
        "MTJ": 1,
        "NAM": 2,
        "NFM": 3,
        "STJ": 4,
        "SIN": 5
    }

    # 按信号类型分组保存数据
    signal_groups = {signal_type: {"data": [], "label": []} for signal_type in type_mapping.keys()}
    total_files = 0
    processed_files = 0

    # 遍历所有.mat文件
    for filename in sorted(os.listdir(mat_folder)):
        if filename.endswith('.mat'):
            total_files += 1
            # 解析文件名获取干扰类型（文件名格式: BPSK_LFM_6_1.mat）
            parts = filename.split('_')
            if len(parts) < 2:
                continue

            # 获取干扰类型（第二个部分）
            intf_type = parts[1]
            if intf_type not in type_mapping:
                continue  # 跳过未映射的类型

            label = type_mapping[intf_type]

            try:
                # 加载.mat文件
                file_path = os.path.join(mat_folder, filename)
                mat_data = sio.loadmat(file_path)
                complex_data = mat_data['data'].flatten()  # 获取复数信号数据

                # 分离实部和虚部，并转换为(2, 5000)形状
                real_part = np.real(complex_data).reshape(1, -1)
                imag_part = np.imag(complex_data).reshape(1, -1)
                formatted_data = np.vstack([real_part, imag_part]).astype(np.float32)

                signal_groups[intf_type]["data"].append(formatted_data)
                signal_groups[intf_type]["label"].append(label)
                processed_files += 1

                if processed_files % 100 == 0:
                    print(f"已处理 {processed_files}/{total_files} 文件...")
            except Exception as e:
                print(f"警告: 处理文件 {filename} 失败: {e}")
                continue

    # 对每个信号类型单独保存（便于检查）和汇总保存
    print(f"\n✓ 共处理 {processed_files} 个文件\n")
    
    for signal_type, group_data in signal_groups.items():
        if len(group_data["data"]) > 0:
            data_array = np.stack(group_data["data"], axis=0)
            label_array = np.array(group_data["label"], dtype=np.int32)
            
            # 保存单个类型的数据
            type_output_path = output_path.replace('.npz', f'_{signal_type}.npz')
            np.savez(type_output_path, data=data_array, label=label_array)
            print(f"✓ {signal_type}: {len(label_array)} 个样本 -> {type_output_path}")
        else:
            print(f"✗ {signal_type}: 没有找到数据")

    # 汇总保存所有数据到一个文件
    all_data = []
    all_labels = []
    for signal_type in sorted(type_mapping.keys()):
        group_data = signal_groups[signal_type]
        if len(group_data["data"]) > 0:
            all_data.extend(group_data["data"])
            all_labels.extend(group_data["label"])

    if all_data:
        data_array = np.stack(all_data, axis=0)
        label_array = np.array(all_labels, dtype=np.int32)
        np.savez(output_path, data=data_array, label=label_array)
        print(f"\n✓ 总计: {len(label_array)} 个样本汇总保存到 {output_path}")
        print(f"  数据形状: {data_array.shape}")


if __name__ == '__main__':
    mat_folder = "C:\\Users\\m1889\\Desktop\\project\\干扰信号识别\\信号识别\\signal\\matlab_data_generate\\data"
    # 输出到训练目录（包含所有信号类型的综合数据）
    output_npz = "C:\\Users\\m1889\\Desktop\\project\\干扰信号识别\\信号识别\\signal\\CCNN\\data\\all_training_data.npz"
    
    print("开始批量转换 MATLAB 数据文件...")
    print(f"源文件夹: {mat_folder}")
    print(f"输出目录: {output_npz}")
    print()
    
    convert_mat_to_npz(mat_folder, output_npz)
    
    print("\n" + "="*70)
    print("✓ 数据转换完成！")
    print("="*70)


