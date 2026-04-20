# 3_scripts/ - 脚本说明

## 📂 目录结构

```
3_scripts/
├── training/          # 训练脚本
│   └── CCNN.py
├── inference/         # 推理脚本
│   └── Infer.py
├── utils/             # 工具脚本
│   ├── analyze_tx_know.py
│   ├── compare_models.py
│   ├── verify_optimization.py
│   └── md_to_docx.py
└── README.md          # 本文件
```

---

## 🎓 training/ - 训练脚本

### CCNN.py - 主训练和推理脚本

**功能**：
- ✓ 训练 CCNN 模型
- ✓ 测试模型性能
- ✓ 推理新数据
- ✓ 生成混淆矩阵和报告

**依赖**：
```
torch >= 1.9.0
numpy >= 1.19.0
matplotlib >= 3.3.0
```

**命令行参数**：

```bash
python 3_scripts/training/CCNN.py [options]
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--mode` | str | train | train/test/infer |
| `--num-classes` | int | 6 | 分类类别数 |
| `--data-path` | str | ./data | 数据路径 |
| `--model` | str | (default) | 模型权重路径 |
| `--batch-size` | int | 16 | 批大小 |
| `--epochs` | int | 100 | 训练轮数 |
| `--learning-rate` | float | 0.001 | 学习率 |
| `--device` | str | cpu | cpu/cuda |

### 使用示例

#### 训练模型
```bash
python 3_scripts/training/CCNN.py \
  --mode train \
  --num-classes 6 \
  --batch-size 16 \
  --epochs 100 \
  --learning-rate 0.001 \
  --device cpu
```

#### 测试模型
```bash
python 3_scripts/training/CCNN.py \
  --mode test \
  --num-classes 6 \
  --model 2_models/best/ccnn_epoch_86_acc_0.9913.pth \
  --device cpu
```

#### 推理数据
```bash
# 推理测试集
python 3_scripts/training/CCNN.py \
  --mode infer \
  --num-classes 6 \
  --model 2_models/best/ccnn_epoch_86_acc_0.9913.pth \
  --data-path 1_datasets/test/inference_test_combined.npz \
  --device cpu

# 推理 TX_know（使用 5 类模型）
python 3_scripts/training/CCNN.py \
  --mode infer \
  --num-classes 5 \
  --model 2_models/legacy/TXCCNNmodel1013.pth \
  --data-path 1_datasets/raw/TX_know.npz \
  --device cpu
```

### 输出示例

```
✓ 使用设备: cpu
✓ 模式: infer

启动推理模式...
✓ 模型已加载: 2_models/best/ccnn_epoch_86_acc_0.9913.pth
✓ 数据集加载完成: 信号 torch.Size([600, 2, 5000]), 标签 torch.Size([600])

============================================================
总体准确率: 100.00%
总样本数: 600, 正确预测: 600
============================================================

混淆矩阵:
             LFM       MTJ       NAM       NFM       STJ       SIN
     LFM:       100         0         0         0         0         0
     ...
```

---

## 🔍 inference/ - 推理脚本

### Infer.py - 简化推理脚本

**功能**：
- ✓ 快速推理
- ✓ 支持单文件和批处理
- ✓ 输出预测概率

**依赖**：
```
torch >= 1.9.0
numpy >= 1.19.0
```

**命令行参数**：

```bash
python 3_scripts/inference/Infer.py [options]
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `--model` | str | 模型路径 |
| `--data` | str | 数据路径 |
| `--num-classes` | int | 类别数 |
| `--batch-size` | int | 批大小 |
| `--device` | str | cpu/cuda |

### 使用示例

```bash
python 3_scripts/inference/Infer.py \
  --model 2_models/best/ccnn_epoch_86_acc_0.9913.pth \
  --data 1_datasets/test/inference_test_combined.npz \
  --num-classes 6 \
  --batch-size 32 \
  --device cpu
```

---

## 🛠️ utils/ - 工具脚本

### analyze_tx_know.py - TX_know 详细分析

**功能**：
- ✓ 逐样本推理分析
- ✓ 生成详细混淆矩阵
- ✓ 错误分类分析
- ✓ 置信度统计

**使用**：
```bash
python 3_scripts/utils/analyze_tx_know.py
```

**输出**：
```
📊 TX_know.npz 详细分析

样本 1: ✓
  真实类型: LFM
  预测类型: LFM
  置信度: 100.00%

样本 2: ✗
  真实类型: NAM
  预测类型: STJ
  置信度: 92.81%
  ⚠️ 误分类!

...

📊 各类型准确率
  LFM    : 100.00% (4/4)
  MTJ    : 50.00% (2/4)
  NAM    : 0.00% (0/4)
  NFM    : 25.00% (1/4)
  STJ    : 25.00% (1/4)
```

### compare_models.py - 模型对比工具

**功能**：
- ✓ 对比多个模型性能
- ✓ 生成对比报告
- ✓ 可视化准确率对比

**使用**：
```bash
python 3_scripts/utils/compare_models.py
```

**对比示例**：
```
模型对比结果
============

模型 1: ccnn_epoch_86_acc_0.9913.pth (6类)
  准确率: 99.71%
  
模型 2: TXCCNNmodel1013.pth (5类)
  准确率: 99.00%
  
TX_know 对比:
  模型 1: 40%
  模型 2: 100% ✓
```

### verify_optimization.py - 优化验证

**功能**：
- ✓ 验证代码优化
- ✓ 性能基准测试
- ✓ 内存使用检查

**使用**：
```bash
python 3_scripts/utils/verify_optimization.py
```

### md_to_docx.py - Markdown 转 Word

**功能**：
- ✓ 将 Markdown 转换为 Word 文档
- ✓ 保留格式和表格
- ✓ 生成 .docx 文件

**使用**：
```bash
python 3_scripts/utils/md_to_docx.py
```

**输入**：`EXPERIMENT_REPORT.md`  
**输出**：`EXPERIMENT_REPORT.docx`

---

## 🚀 快速参考

### 最常用的命令

```bash
# 1. 查看帮助
python 3_scripts/training/CCNN.py --help

# 2. 推理合成数据（6类）
python 3_scripts/training/CCNN.py --mode infer \
  --num-classes 6 \
  --model 2_models/best/ccnn_epoch_86_acc_0.9913.pth \
  --data-path 1_datasets/test/inference_test_combined.npz

# 3. 推理 TX_know（5类）
python 3_scripts/training/CCNN.py --mode infer \
  --num-classes 5 \
  --model 2_models/legacy/TXCCNNmodel1013.pth \
  --data-path 1_datasets/raw/TX_know.npz

# 4. 分析 TX_know
python 3_scripts/utils/analyze_tx_know.py

# 5. 重新训练
python 3_scripts/training/CCNN.py --mode train \
  --num-classes 6 --epochs 100

# 6. 对比模型
python 3_scripts/utils/compare_models.py

# 7. Markdown 转 Word
python 3_scripts/utils/md_to_docx.py
```

---

## 📦 Python 环境要求

### 创建虚拟环境
```bash
# Conda
conda create -n signal-recognition python=3.8
conda activate signal-recognition

# 或 venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 安装依赖
```bash
pip install torch numpy matplotlib scikit-learn python-docx
```

### 验证安装
```bash
python -c "import torch; print(torch.__version__)"
python -c "import numpy; print(numpy.__version__)"
```

---

## 🔧 调试技巧

### 启用详细输出
```bash
python -u 3_scripts/training/CCNN.py --mode infer --verbose
```

### 检查 GPU（如果有）
```python
import torch
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0))
```

### 内存使用监控
```bash
# Linux/Mac
watch -n 1 'ps aux | grep python'

# Windows
Get-Process python | Select-Object Name, PrivateMemorySize
```

### 数据集验证
```python
import numpy as np
data = np.load('1_datasets/train/all_training_data.npz')
print(f'Shape: {data["signals"].shape}')
print(f'Labels: {np.unique(data["labels"])}')
```

---

## 📝 脚本开发指南

### 添加新脚本
1. 放在 `3_scripts/` 的适当子目录
2. 添加 docstring 和注释
3. 在本 README 中记录
4. 测试无误后提交

### 脚本模板
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
脚本说明
"""

import argparse
import torch
import numpy as np

def main(args):
    """主函数"""
    print(f"Processing with {args.model}")
    # 你的代码
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default='model.pth')
    parser.add_argument('--device', type=str, default='cpu')
    args = parser.parse_args()
    main(args)
```

---

## ⚠️ 常见问题

### Q: 如何选择 CPU 或 GPU？
```bash
# CPU（总是可用）
--device cpu

# GPU（需要 CUDA）
--device cuda
```

### Q: 内存不足怎么办？
```bash
# 减少批大小
--batch-size 8

# 减少数据加载
--num-workers 0
```

### Q: 如何保存推理结果？
修改脚本，添加输出重定向：
```bash
python 3_scripts/training/CCNN.py ... > 4_results/logs/output.txt
```

### Q: 脚本执行很慢？
- 检查设备（--device cuda 可能更快）
- 减少样本数进行测试
- 检查磁盘 I/O（SSD 比 HDD 快）

---

**最后更新**：2026-01-29  
**脚本版本**：v1.0  
**状态**：生产就绪
