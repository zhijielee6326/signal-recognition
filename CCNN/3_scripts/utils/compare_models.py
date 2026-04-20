"""
模型对比测试脚本
比较两个模型在同一测试集上的性能
支持不同类别数的模型对比
"""

import os
import sys
import io

# 设置标准输出为UTF-8编码（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import torch
import numpy as np
from torch import nn
from torch.utils.data import Dataset, DataLoader
import time
from datetime import datetime

# 导入CCNN模型和数据集
from CCNN import CCNN, SignalDataset

class ModelComparator:
    """模型对比器"""
    
    def __init__(self, model_configs, device='cpu'):
        """
        初始化对比器
        Args:
            model_configs: 模型配置列表 [(名称, 路径, 类别数, 类别名单), ...]
            device: 运行设备
        """
        self.models = {}
        self.model_configs = {}
        self.device = device
        
        # 加载所有模型
        for name, path, num_classes, class_names in model_configs:
            print(f"📦 加载模型: {name}")
            if not os.path.exists(path):
                print(f"  ❌ 文件不存在: {path}")
                continue
            
            try:
                model = CCNN(num_classes=num_classes)
                model.load_state_dict(torch.load(path, map_location=device))
                model = model.to(device)
                model.eval()
                self.models[name] = model
                self.model_configs[name] = {
                    'num_classes': num_classes,
                    'class_names': class_names,
                    'path': path
                }
                print(f"  ✓ 加载成功 ({os.path.getsize(path) / 1024:.1f} KB, {num_classes}类)")
            except Exception as e:
                print(f"  ❌ 加载失败: {e}")
    
    def test_on_file(self, npz_file, model_name, batch_size=32):
        """
        在单个文件上测试某个模型
        Args:
            npz_file: npz文件路径
            model_name: 模型名称
            batch_size: 批处理大小
        
        Returns:
            字典 {准确率, 混淆矩阵, 预测}
        """
        if model_name not in self.models:
            return None
        
        model = self.models[model_name]
        config = self.model_configs[model_name]
        num_classes = config['num_classes']
        class_names = config['class_names']
        
        dataset = SignalDataset(npz_file, augment=False)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
        
        correct = 0
        total = 0
        preds_all = []
        labels_all = []
        confusion_matrix = np.zeros((num_classes, num_classes))
        
        with torch.no_grad():
            for signals, labels in loader:
                signals = signals.to(self.device)
                labels = labels.to(self.device)
                
                # 对于5类模型，只取前5类的数据
                if num_classes == 5 and labels.max() >= 5:
                    continue
                
                outputs = model(signals)
                _, preds = torch.max(outputs, 1)
                
                # 统计
                correct += (preds == labels).sum().item()
                total += labels.size(0)
                
                preds_all.extend(preds.cpu().numpy())
                labels_all.extend(labels.cpu().numpy())
                
                # 生成混淆矩阵
                for p, t in zip(preds.cpu().numpy(), labels.cpu().numpy()):
                    confusion_matrix[p, int(t)] += 1
        
        if total == 0:
            return None
        
        accuracy = correct / total * 100
        
        # 计算每类准确率
        class_accuracies = {}
        for i in range(num_classes):
            if confusion_matrix[:, i].sum() > 0:
                class_acc = confusion_matrix[i, i] / confusion_matrix[:, i].sum() * 100
                class_accuracies[class_names[i]] = class_acc
        
        return {
            'accuracy': accuracy,
            'correct': correct,
            'total': total,
            'confusion_matrix': confusion_matrix,
            'class_accuracies': class_accuracies,
            'preds': np.array(preds_all),
            'labels': np.array(labels_all)
        }
    
    def compare_results(self, test_folder, batch_size=32):
        """
        在所有测试文件上对比模型
        Args:
            test_folder: 包含npz文件的测试文件夹
            batch_size: 批处理大小
        """
        if not os.path.exists(test_folder):
            print(f"❌ 测试文件夹不存在: {test_folder}")
            return
        
        npz_files = sorted([
            os.path.join(test_folder, f) 
            for f in os.listdir(test_folder) 
            if f.endswith('.npz')
        ])
        
        if not npz_files:
            print(f"❌ 未找到npz文件: {test_folder}")
            return
        
        print(f"\n{'='*90}")
        print(f"🧪 模型对比测试")
        print(f"{'='*90}")
        print(f"测试文件夹: {test_folder}")
        print(f"测试文件数: {len(npz_files)}")
        print(f"模型数量: {len(self.models)}")
        print(f"{'='*90}\n")
        
        overall_results = {name: {'total_correct': 0, 'total_samples': 0} for name in self.models.keys()}
        file_results = []
        
        for i, npz_file in enumerate(npz_files):
            filename = os.path.basename(npz_file)
            print(f"[{i+1}/{len(npz_files)}] 处理文件: {filename}")
            print("-" * 90)
            
            results = {}
            for model_name in self.models.keys():
                result = self.test_on_file(npz_file, model_name, batch_size)
                if result:
                    results[model_name] = result
            
            # 打印对比结果
            print(f"{'模型名':<30} {'准确率':<12} {'正确数':<10} {'总数':<10}")
            print("-" * 60)
            
            for model_name in sorted(self.models.keys()):
                if model_name in results:
                    res = results[model_name]
                    acc = res['accuracy']
                    correct = res['correct']
                    total = res['total']
                    
                    print(f"{model_name:<30} {acc:>6.2f}% {correct:>8}/{total:<8}")
                    
                    # 更新总体统计
                    overall_results[model_name]['total_correct'] += correct
                    overall_results[model_name]['total_samples'] += total
            
            # 显示类别准确率（第一个模型）
            first_model = list(sorted(self.models.keys()))[0]
            if first_model in results:
                print(f"\n  {first_model} 的类别准确率:")
                for class_name, class_acc in results[first_model]['class_accuracies'].items():
                    print(f"    {class_name:<15} {class_acc:>6.2f}%")
            
            file_results.append((filename, results))
            print()
        
        # 打印总体对比
        print(f"\n{'='*90}")
        print(f"📊 总体对比结果")
        print(f"{'='*90}")
        print(f"{'模型名':<30} {'总准确率':<12} {'正确数':<15} {'总数':<10}")
        print("-" * 70)
        
        for model_name in sorted(self.models.keys()):
            total_correct = overall_results[model_name]['total_correct']
            total_samples = overall_results[model_name]['total_samples']
            overall_acc = (total_correct / total_samples * 100) if total_samples > 0 else 0
            
            print(f"{model_name:<30} {overall_acc:>6.2f}% {total_correct:>13}/{total_samples:<8}")
        
        print(f"{'='*90}\n")
        
        # 模型对比分析
        print(f"📈 模型性能分析:")
        print("-" * 90)
        
        model_names = sorted(self.models.keys())
        accs = [(name, overall_results[name]['total_correct'] / overall_results[name]['total_samples'] * 100) 
                for name in model_names if overall_results[name]['total_samples'] > 0]
        accs_sorted = sorted(accs, key=lambda x: x[1], reverse=True)
        
        for rank, (name, acc) in enumerate(accs_sorted, 1):
            print(f"{rank}. {name:<28} {acc:>6.2f}%")
        
        if len(accs_sorted) > 1:
            diff = accs_sorted[0][1] - accs_sorted[-1][1]
            print(f"\n最优模型与最差模型的差异: {diff:.2f}%")
            
            if diff < 0.5:
                print("✓ 两个模型性能基本相同")
            elif diff < 2:
                print("⚠ 两个模型性能有差异，但均可接受")
            else:
                print("❌ 两个模型性能差异较大，建议使用最优模型")
        
        # 版本对比信息
        print(f"\n📝 模型版本信息:")
        print("-" * 90)
        for name in sorted(self.models.keys()):
            config = self.model_configs[name]
            print(f"{name:<30} 类别数: {config['num_classes']} | 类别: {', '.join(config['class_names'])}")
        
        print(f"\n{'='*90}\n")
        
        return overall_results, file_results


def main():
    # 配置
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 模型配置: (名称, 路径, 类别数, 类别名单)
    model_configs = [
        ('ccnn_epoch_86 (6类最优)', 
         os.path.join(script_dir, '..', '..', '2_models', 'best', 'ccnn_epoch_86_acc_0.9913.pth'),
         6, 
         ['LFM', 'MTJ', 'NAM', 'NFM', 'STJ', 'SIN']),
        
        ('TXCCNNmodel1013 (5类旧版)',
         os.path.join(script_dir, '..', '..', '2_models', 'legacy', 'TXCCNNmodel1013.pth'),
         5,
         ['LFM', 'MTJ', 'NAM', 'NFM', 'STJ']),
    ]
    
    test_folder = os.path.join(script_dir, '..', '..', '1_datasets', 'test')
    batch_size = 32
    device = 'cpu'
    
    # 创建对比器
    comparator = ModelComparator(model_configs, device=device)
    
    if len(comparator.models) < 1:
        print("❌ 没有成功加载任何模型")
        return
    
    # 执行对比
    start_time = time.time()
    overall_results, file_results = comparator.compare_results(test_folder, batch_size)
    elapsed = time.time() - start_time
    
    print(f"⏱️  总耗时: {elapsed:.1f}秒\n")


if __name__ == '__main__':
    main()
