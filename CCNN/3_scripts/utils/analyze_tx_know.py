"""
TX_know.npz 详细分析脚本
分析模型在真实TX数据上的性能
"""

import os
import sys
import io

# 设置标准输出为UTF-8编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader

# 导入模型
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from CCNN import CCNN, SignalDataset


class TXAnalyzer:
    """TX_know数据分析器"""
    
    def __init__(self, model_path, device='cpu'):
        self.device = device
        self.class_names = ['LFM', 'MTJ', 'NAM', 'NFM', 'STJ', 'SIN']
        self.num_classes = len(self.class_names)
        
        # 加载模型
        print("📦 加载模型...")
        self.model = CCNN(num_classes=self.num_classes)
        self.model.load_state_dict(torch.load(model_path, map_location=device))
        self.model.to(device)
        self.model.eval()
        print(f"✓ 模型加载成功: {os.path.basename(model_path)}\n")
    
    def analyze_tx_know(self, data_path):
        """分析TX_know数据"""
        
        print("=" * 80)
        print("📊 TX_know.npz 详细分析")
        print("=" * 80)
        
        # 加载数据
        print(f"\n📂 加载数据: {data_path}")
        data = np.load(data_path)
        signals = data['data']
        labels = data['label']
        
        print(f"✓ 信号形状: {signals.shape}")
        print(f"✓ 标签形状: {labels.shape}")
        print(f"✓ 样本总数: {len(labels)}")
        
        # 转换为张量
        signals = torch.from_numpy(signals).float()
        labels = torch.from_numpy(labels).long()
        
        # 数据统计
        print("\n📈 样本分布:")
        print("-" * 40)
        for class_idx, class_name in enumerate(self.class_names):
            count = (labels == class_idx).sum().item()
            percentage = f"{(count/len(labels)*100):.1f}%" if len(labels) > 0 else "0%"
            print(f"  {class_name:<8} : {count:>3} 个样本 ({percentage})")
        print("-" * 40)
        
        # 进行推理
        print("\n🔮 进行推理...")
        predictions = []
        confidences = []
        
        with torch.no_grad():
            for i in range(0, len(signals), 4):
                batch_signals = signals[i:i+4].to(self.device)
                outputs = self.model(batch_signals)
                probs = torch.softmax(outputs, dim=1)
                preds = outputs.argmax(dim=1)
                conf = probs.max(dim=1)[0]
                
                predictions.extend(preds.cpu().numpy())
                confidences.extend(conf.cpu().numpy())
        
        predictions = np.array(predictions)
        confidences = np.array(confidences)
        
        # 计算准确率
        accuracy = (predictions == labels.cpu().numpy()).sum() / len(labels)
        
        print(f"✓ 推理完成")
        print(f"✓ 总体准确率: {accuracy*100:.2f}%")
        
        # 详细结果
        print("\n" + "=" * 80)
        print("🔍 推理结果详情")
        print("=" * 80)
        
        for idx in range(len(labels)):
            true_label = labels[idx].item()
            pred_label = predictions[idx]
            confidence = confidences[idx]
            
            true_name = self.class_names[true_label]
            pred_name = self.class_names[pred_label]
            
            status = "✓" if true_label == pred_label else "✗"
            print(f"\n样本 {idx+1:>2}: {status}")
            print(f"  真实类型: {true_name:<8} (标签={true_label})")
            print(f"  预测类型: {pred_name:<8} (标签={pred_label})")
            print(f"  置信度:  {confidence*100:>6.2f}%")
            
            if true_label != pred_label:
                print(f"  ⚠️  误分类!")
        
        # 生成混淆矩阵
        print("\n" + "=" * 80)
        print("📋 混淆矩阵分析")
        print("=" * 80)
        
        confusion = np.zeros((self.num_classes, self.num_classes))
        for true, pred in zip(labels.cpu().numpy(), predictions):
            confusion[pred, true] += 1
        
        # 打印混淆矩阵
        print("\n混淆矩阵 (行=预测, 列=真实):\n")
        print(f"{'':>8}", end='')
        for name in self.class_names:
            print(f"{name:>8}", end='')
        print()
        
        for i, true_name in enumerate(self.class_names):
            print(f"{true_name:>8}", end='')
            for j in range(self.num_classes):
                val = int(confusion[j, i])
                print(f"{val:>8}", end='')
            print()
        
        # 各类准确率
        print("\n" + "=" * 80)
        print("📊 各类型准确率")
        print("=" * 80 + "\n")
        
        for class_idx, class_name in enumerate(self.class_names):
            total = (labels == class_idx).sum().item()
            if total > 0:
                correct = confusion[class_idx, class_idx]
                acc = correct / total * 100
                print(f"  {class_name:<8} : {acc:>6.2f}% ({int(correct)}/{total})")
            else:
                print(f"  {class_name:<8} : 无数据")
        
        # 总结
        print("\n" + "=" * 80)
        print("📝 总结")
        print("=" * 80)
        
        total_correct = (predictions == labels.cpu().numpy()).sum()
        total_samples = len(labels)
        
        print(f"\n总体表现:")
        print(f"  ✓ 正确预测: {total_correct}/{total_samples}")
        print(f"  ✓ 准确率: {accuracy*100:.2f}%")
        print(f"  ✓ 误分类: {total_samples - total_correct}")
        
        # 分析误分类
        wrong_indices = np.where(predictions != labels.cpu().numpy())[0]
        if len(wrong_indices) > 0:
            print(f"\n⚠️  误分类分析 ({len(wrong_indices)} 个错误):")
            for idx in wrong_indices:
                true_name = self.class_names[labels[idx].item()]
                pred_name = self.class_names[predictions[idx]]
                print(f"  • 样本{idx+1}: {true_name} → {pred_name} (置信度: {confidences[idx]*100:.2f}%)")
        
        print("\n" + "=" * 80 + "\n")
        
        return accuracy, confusion


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    model_path = os.path.join(script_dir, '..', '..', '2_models', 'best', 'ccnn_epoch_86_acc_0.9913.pth')
    data_path = os.path.join(script_dir, '..', '..', '1_datasets', 'raw', 'TX_know.npz')
    
    print("\n🚀 TX_know 数据分析工具\n")
    
    # 创建分析器
    analyzer = TXAnalyzer(model_path, device='cpu')
    
    # 分析数据
    accuracy, confusion = analyzer.analyze_tx_know(data_path)


if __name__ == '__main__':
    main()
