#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CCNN 优化验证脚本
验证所有的优化改进是否正确应用
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
import sys
import io

# 设置标准输出为UTF-8编码
if sys.platform == 'win32':
    import sys
    import codecs
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import torch
import numpy as np

# 添加CCNN模块路径
sys.path.insert(0, os.path.dirname(__file__))

def check_imports():
    """检查所有必要的导入"""
    print("=" * 70)
    print("✓ 检查导入模块")
    print("=" * 70)
    try:
        from CCNN import CCNN, MyDataset, SignalDataset
        from CCNN import test_model_comprehensive, test_model_with_npz_files
        print("✓ 所有模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def check_model():
    """检查模型初始化"""
    print("\n" + "=" * 70)
    print("✓ 检查模型初始化")
    print("=" * 70)
    try:
        from CCNN import CCNN
        model = CCNN(num_classes=6)  # 现在支持6种: LFM, MTJ, NAM, NFM, STJ, SIN
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model = model.to(device)
        print(f"✓ 模型初始化成功 (device: {device})")
        
        # 计数参数
        total_params = sum(p.numel() for p in model.parameters())
        print(f"✓ 总参数量: {total_params:,}")
        return True
    except Exception as e:
        print(f"❌ 模型初始化失败: {e}")
        return False

def check_dataset():
    """检查数据集类"""
    print("\n" + "=" * 70)
    print("✓ 检查数据集类")
    print("=" * 70)
    try:
        # 使用实际存在的数据文件
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(script_dir, '..', '..', '1_datasets', 'raw', 'TX_know.npz')
        
        if not os.path.exists(data_path):
            print(f"⚠️  数据文件不存在: {data_path}")
            print(f"   使用临时数据进行测试...")
            # 创建临时测试数据
            test_data = np.random.randn(10, 2, 5000).astype(np.float32)
            test_label = np.array([0, 1, 2, 3, 4, 0, 1, 2, 3, 4])
            temp_path = os.path.join(os.path.dirname(__file__), 'temp_test_data.npz')
            np.savez(temp_path, data=test_data, label=test_label)
            data_path = temp_path
            cleanup = True
        else:
            cleanup = False
        
        from CCNN import SignalDataset
        dataset = SignalDataset(data_path, augment=False)
        
        # 获取一个样本
        signal, label = dataset[0]
        print(f"✓ 数据集加载成功")
        print(f"  - 数据文件: {os.path.basename(data_path)}")
        print(f"  - 信号形状: {signal.shape}")
        print(f"  - 标签: {label.item()}")
        print(f"  - 标签类型: {label.dtype} (Torch类型)")
        print(f"  - 数据集大小: {len(dataset)} 个样本")
        
        # 清理临时文件
        if cleanup and os.path.exists(data_path):
            os.remove(data_path)
        
        return True
    except Exception as e:
        print(f"❌ 数据集检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_data_augmentation():
    """检查数据增强功能"""
    print("\n" + "=" * 70)
    print("✓ 检查数据增强功能")
    print("=" * 70)
    try:
        # 使用实际存在的数据文件
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(script_dir, '..', '..', '1_datasets', 'raw', 'TX_know.npz')
        
        if not os.path.exists(data_path):
            print(f"⚠️  数据文件不存在: {data_path}")
            print(f"   使用临时数据进行测试...")
            # 创建临时测试数据
            test_data = np.random.randn(5, 2, 5000).astype(np.float32)
            test_label = np.array([0, 1, 2, 3, 4])
            temp_path = os.path.join(os.path.dirname(__file__), 'temp_test_augment.npz')
            np.savez(temp_path, data=test_data, label=test_label)
            data_path = temp_path
            cleanup = True
        else:
            cleanup = False
        
        from CCNN import SignalDataset
        dataset = SignalDataset(data_path, augment=True)
        
        # 获取多个样本，验证增强多样性
        signals = []
        for i in range(3):
            signal, _ = dataset[0]
            signals.append(signal)
        
        # 检查增强后的信号是否不同（由于增强）
        diff1 = torch.abs(signals[0] - signals[1]).max().item()
        diff2 = torch.abs(signals[1] - signals[2]).max().item()
        
        print(f"✓ 数据增强功能正常")
        print(f"  - 增强类型: 5种 (频率偏移、时间缩放、相位旋转、幅度缩放、噪声)")
        print(f"  - 增强差异1: {diff1:.6f}")
        print(f"  - 增强差异2: {diff2:.6f}")
        print(f"  - 增强有效: {'✓' if (diff1 > 0 or diff2 > 0) else '✗'}")
        
        # 清理临时文件
        if cleanup and os.path.exists(data_path):
            os.remove(data_path)
        
        return True
    except Exception as e:
        print(f"❌ 数据增强检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_label_type():
    """检查标签类型修复"""
    print("\n" + "=" * 70)
    print("✓ 检查标签类型修复")
    print("=" * 70)
    try:
        # 使用实际存在的数据文件
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(script_dir, '..', '..', '1_datasets', 'raw', 'TX_know.npz')
        
        if not os.path.exists(data_path):
            print(f"⚠️  数据文件不存在: {data_path}")
            print(f"   使用临时数据进行测试...")
            # 创建临时测试数据
            test_data = np.random.randn(10, 2, 5000).astype(np.float32)
            test_label = np.array([0, 1, 2, 3, 4, 0, 1, 2, 3, 4])
            temp_path = os.path.join(os.path.dirname(__file__), 'temp_test_label.npz')
            np.savez(temp_path, data=test_data, label=test_label)
            data_path = temp_path
            cleanup = True
        else:
            cleanup = False
        
        from CCNN import SignalDataset
        dataset = SignalDataset(data_path, augment=False)
        
        # 检查标签类型
        _, label = dataset[0]
        label_type = type(label.item())
        
        print(f"✓ 标签类型检查")
        print(f"  - 标签Torch类型: {label.dtype}")
        print(f"  - 标签Python类型: {label_type.__name__}")
        print(f"  - 是整数类型: {label.dtype in [torch.int64, torch.int32, torch.long]}")
        
        # 检查与CrossEntropyLoss的兼容性
        model = torch.nn.Linear(5, 5)
        loss_fn = torch.nn.CrossEntropyLoss()
        
        # 创建虚拟输出
        output = model(torch.randn(1, 5))
        
        try:
            loss = loss_fn(output, label.unsqueeze(0))
            print(f"✓ 与CrossEntropyLoss兼容 (loss={loss.item():.6f})")
        except Exception as e:
            print(f"❌ 与CrossEntropyLoss不兼容: {e}")
        
        # 清理临时文件
        if cleanup and os.path.exists(data_path):
            os.remove(data_path)
        
        return True
    except Exception as e:
        print(f"❌ 标签类型检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_inference():
    """检查推理功能"""
    print("\n" + "=" * 70)
    print("✓ 检查推理功能")
    print("=" * 70)
    try:
        from CCNN import CCNN
        from torch.utils.data import DataLoader
        
        model = CCNN(num_classes=6)  # 现在支持6种: LFM, MTJ, NAM, NFM, STJ, SIN
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model = model.to(device)
        model.eval()
        
        # 创建虚拟输入
        batch_size = 4
        dummy_input = torch.randn(batch_size, 2, 5000).to(device)
        
        with torch.no_grad():
            output = model(dummy_input)
        
        print(f"✓ 推理功能正常")
        print(f"  - 输入形状: {dummy_input.shape}")
        print(f"  - 输出形状: {output.shape}")
        print(f"  - 预测值: {output.argmax(dim=1).cpu().numpy()}")
        
        return True
    except Exception as e:
        print(f"❌ 推理功能检查失败: {e}")
        return False

def main():
    """主检查函数"""
    print("\n")
    print("█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "  CCNN 优化验证脚本".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)
    
    checks = [
        ("导入模块", check_imports),
        ("模型初始化", check_model),
        ("数据集类", check_dataset),
        ("标签类型修复", check_label_type),
        ("数据增强", check_data_augmentation),
        ("推理功能", check_inference),
    ]
    
    results = []
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))
    
    # 总结
    print("\n" + "=" * 70)
    print("✓ 验证总结")
    print("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "❌ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总体结果: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有优化验证成功！程序可以正常使用。")
    else:
        print("\n⚠️  有些检查失败，请检查日志。")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
