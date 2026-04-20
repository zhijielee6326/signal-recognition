# 1_datasets/ - 数据集目录说明

## 📂 目录结构

```
1_datasets/
├── train/              # 训练数据集（3.5+ GB）
├── test/               # 测试/验证数据集（~2 GB）
├── raw/                # 原始 TX 数据（极小）
└── README.md           # 本文件
```

---

## 📊 训练数据集（train/）

### 完整训练集
- **文件名**：`all_training_data.npz`
- **大小**：~1.5 GB
- **样本数**：3600
- **类别**：6（LFM, MTJ, NAM, NFM, STJ, SIN）
- **类别分布**：均衡（每类 600 样本）
- **样本维度**：(3600, 2, 5000)
- **用途**：主模型训练

### 单类训练集
按类别分开，便于特定类别的实验：

| 文件 | 样本数 | 大小 |
|------|--------|------|
| `all_training_data_LFM.npz` | 600 | ~250 MB |
| `all_training_data_MTJ.npz` | 600 | ~250 MB |
| `all_training_data_NAM.npz` | 600 | ~250 MB |
| `all_training_data_NFM.npz` | 600 | ~250 MB |
| `all_training_data_STJ.npz` | 600 | ~250 MB |
| `all_training_data_SIN.npz` | 600 | ~250 MB |

**用途**：
- 单类别微调
- 特定类别性能分析
- 特征可视化

### 原始数据文件（39个）
- **文件名格式**：`[ID]_[TYPE]_[PARAM]_[NUM].npz`
- **大小**：~10 MB each
- **总计**：~390 MB
- **样本数**：100 per file

**示例**：
- `14_8PSK_LFM_10_20.npz`
- `7807_QPSK_NFM_6_14.npz`
- `8503_QPSK_STJ_10_100.npz`

---

## 🧪 测试数据集（test/）

### 混合测试集
- **文件名**：`inference_test_combined.npz`
- **样本数**：600（均衡，每类 100）
- **准确率**：100.00% ✓
- **用途**：综合性能评估

### 单类测试集
独立抽取的测试样本（与训练集无重叠）：

| 文件 | 类型 | 样本数 | 准确率 |
|------|------|--------|--------|
| `inference_test_LFM.npz` | LFM | 50 | 100% |
| `inference_test_MTJ.npz` | MTJ | 50 | 98% |
| `inference_test_NAM.npz` | NAM | 50 | 100% |
| `inference_test_NFM.npz` | NFM | 50 | 100% |
| `inference_test_SIN.npz` | SIN | 50 | 100% |
| `inference_test_STJ.npz` | STJ | 50 | 100% |

**特点**：
- 完全独立于训练集（无数据泄露）
- 从 3600 个原始 MATLAB 文件中随机抽取 25%
- 平衡分布（每类样本数相等）

---

## 🔍 原始数据（raw/）

### TX_know 数据
- **文件名**：`TX_know.npz`
- **样本数**：20（真实 TX 传输数据）
- **类别分布**：LFM(4), MTJ(4), NAM(4), NFM(4), STJ(4), SIN(0)
- **大小**：极小（~1 MB）

**用途**：
- 模型真实数据兼容性测试
- 性能验证（真实数据 vs 合成数据）
- 问题诊断

**重要发现**：
- 6 类模型：40% 准确率 ❌
- 5 类模型：100% 准确率 ✓

---

## 📈 数据统计

### 类别分布
```
LFM  ████████████████ 600 samples (16.67%)
MTJ  ████████████████ 600 samples (16.67%)
NAM  ████████████████ 600 samples (16.67%)
NFM  ████████████████ 600 samples (16.67%)
STJ  ████████████████ 600 samples (16.67%)
SIN  ████████████████ 600 samples (16.67%)
```

### 数据分割
```
总样本数：3600
├─ 训练集：2880 (80%)
└─ 验证集：720 (20%)

独立测试集：1200 (25% 新样本)
原始TX数据：20 (真实数据)
```

### 数据转换链
```
MATLAB .mat 文件 (3600个)
         ↓
    特征提取 (IQ分量)
         ↓
    标准化 (2×5000维)
         ↓
    分类标签 (6类)
         ↓
    NPZ 格式转换
         ↓
   训练/测试集分割
         ↓
    存储到本目录
```

---

## 💾 加载数据示例

### Python - NumPy
```python
import numpy as np

# 加载完整训练集
data = np.load('1_datasets/train/all_training_data.npz')
signals = data['signals']      # (3600, 2, 5000)
labels = data['labels']        # (3600,)

# 加载单类数据
lfm_data = np.load('1_datasets/train/all_training_data_LFM.npz')
lfm_signals = lfm_data['signals']  # (600, 2, 5000)
```

### Python - PyTorch
```python
import torch
import numpy as np

# 加载并转换为 PyTorch 张量
data = np.load('1_datasets/train/all_training_data.npz')
signals = torch.from_numpy(data['signals']).float()
labels = torch.from_numpy(data['labels']).long()

# 创建数据加载器
from torch.utils.data import TensorDataset, DataLoader
dataset = TensorDataset(signals, labels)
loader = DataLoader(dataset, batch_size=16, shuffle=True)
```

---

## 🔧 数据管理

### 添加新数据集
```bash
# 1. 生成新的 .npz 文件
python generate_data.py

# 2. 放入相应目录
mv new_training_data.npz train/
mv new_test_data.npz test/

# 3. 更新本 README
```

### 数据验证
```bash
python -c "
import numpy as np
data = np.load('1_datasets/train/all_training_data.npz')
print(f'Signals shape: {data[\"signals\"].shape}')
print(f'Labels shape: {data[\"labels\"].shape}')
print(f'Unique labels: {np.unique(data[\"labels\"])}')
"
```

### 清理过期数据
```bash
# 备份旧数据
mkdir backup
mv train/*_old.npz backup/

# 删除临时文件
rm test/*_temp.npz
```

---

## 📋 数据集检查清单

- [ ] 训练集完整（3600 样本）
- [ ] 类别均衡（每类 600）
- [ ] 验证集独立（20% 无重叠）
- [ ] 测试集独立（1200 新样本）
- [ ] TX_know 数据可访问
- [ ] 所有文件可读（NPZ 格式正确）
- [ ] 空间充足（需 5+ GB 可用）

---

## ⚡ 性能参考

| 操作 | 时间 | 内存 |
|------|------|------|
| 加载完整训练集 | ~2s | ~3.5 GB |
| 加载单类数据 | ~0.5s | ~600 MB |
| 加载测试集 | ~1s | ~2 GB |
| 批处理（BS=16） | ~0.1s | ~1 GB |

---

**最后更新**：2026-01-29  
**数据版本**：v1.0  
**总数据量**：~5.5 GB
