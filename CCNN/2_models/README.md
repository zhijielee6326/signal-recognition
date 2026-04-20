# 2_models/ - 模型文件说明

## 📂 目录结构

```
2_models/
├── best/              # 最佳模型（6类，99.13%）
├── legacy/            # 旧版模型（5类，100%）
├── archive/           # 存档模型（格式转换）
└── README.md          # 本文件
```

---

## 🏆 最佳模型（best/）

### 模型文件
- **文件名**：`ccnn_epoch_86_acc_0.9913.pth`
- **大小**：395.8 KB
- **框架**：PyTorch
- **设备**：CPU/CUDA 兼容

### 模型规格
| 参数 | 值 |
|------|-----|
| **类别数** | 6 |
| **类别** | LFM, MTJ, NAM, NFM, STJ, SIN |
| **输入维度** | (2, 5000) |
| **输出维度** | 6 |
| **参数数量** | 49 个张量 |
| **训练轮数** | 100 |
| **最优轮数** | 86 |

### 性能指标
| 指标 | 值 |
|------|-----|
| **验证准确率** | 99.13% |
| **测试准确率** | 99.71% |
| **训练数据准确率** | 99.57% |
| **TX_know 准确率** | 40.00% ⚠️ |

### 模型架构
```
输入 (Batch, 2, 5000)
    ↓
卷积块1: Conv(2→32, k=3) + BatchNorm + ReLU + MaxPool
    ↓
卷积块2: Conv(32→64, k=3) + BatchNorm + ReLU + MaxPool
    ↓
卷积块3: Conv(64→128, k=3) + BatchNorm + ReLU + MaxPool
    ↓
展平
    ↓
全连接: Linear(FC_size → 128) + ReLU + Dropout(0.5)
    ↓
输出: Linear(128 → 6) + Softmax
    ↓
输出 (Batch, 6)
```

### 使用场景 ✅ 推荐
```
✓ 合成信号分类
✓ 实验室模拟数据
✓ LFM、MTJ、NAM、NFM、STJ、SIN 分类
✓ 教学演示
✓ 模型研究
```

### 使用场景 ❌ 不推荐
```
✗ TX_know 真实数据（40% 准确率）
✗ 原生产环境（见 legacy 模型）
✗ 实时关键应用
```

### 调用方法
```bash
# 推理
python 3_scripts/training/CCNN.py --mode infer \
  --model 2_models/best/ccnn_epoch_86_acc_0.9913.pth \
  --num-classes 6 \
  --data-path 1_datasets/test/inference_test_combined.npz

# 测试
python 3_scripts/training/CCNN.py --mode test \
  --model 2_models/best/ccnn_epoch_86_acc_0.9913.pth \
  --num-classes 6 \
  --device cpu
```

---

## 🔙 旧版模型（legacy/）

### 模型文件
- **文件名**：`TXCCNNmodel1013.pth`
- **大小**：1.2 MB
- **框架**：PyTorch
- **训练时间**：较早期版本

### 模型规格
| 参数 | 值 |
|------|-----|
| **类别数** | 5 |
| **类别** | LFM, MTJ, NAM, NFM, STJ |
| **SIN 类** | ❌ 不包含 |
| **输入维度** | (2, 5000) |

### 性能指标
| 测试数据 | 准确率 |
|---------|--------|
| **TX_know** | **100.00%** ✓ |
| **训练数据** | 99%+ |

### 对比分析
```
性能对比：6 类模型 vs 5 类模型

           6类模型    5类模型
测试集    99.71%     -
TX_know    40.00%    100.00% ⭐
LFM        100%      100%
MTJ        100%      100%
NAM        0%        100%  ← 重大差异
NFM        25%       100%  ← 重大差异
STJ        25%       100%  ← 重大差异
SIN        100%      N/A
```

**关键发现**：
- 5 类模型在 TX_know 上完美表现
- 6 类模型因添加 SIN 类而在 TX_know 上失效
- NAM、NFM、STJ 三个类别受影响最大

### 使用场景 ✅ 推荐
```
✓ TX_know 数据分类（100% 准确）
✓ 实时生产环境
✓ 原业务数据
✓ 关键应用系统
```

### 调用方法
```bash
# 推理（TX_know）
python 3_scripts/training/CCNN.py --mode infer \
  --model 2_models/legacy/TXCCNNmodel1013.pth \
  --num-classes 5 \
  --data-path 1_datasets/raw/TX_know.npz

# 测试
python 3_scripts/training/CCNN.py --mode test \
  --model 2_models/legacy/TXCCNNmodel1013.pth \
  --num-classes 5
```

---

## 📦 存档模型（archive/）

### ONNX 格式
- **文件名**：`TXCCNNmodel1013.onnx`
- **大小**：类似 .pth
- **用途**：跨平台推理
- **支持**：TensorFlow, TVM, TensorRT

### OM 格式（Ascend NPU）
- **文件名**：`TXCCNNmodel1013.om`
- **大小**：类似 .pth
- **用途**：华为昇腾 NPU 加速
- **性能**：高吞吐量推理

### 转换使用
```bash
# ONNX 推理
import onnx
import onnxruntime as rt
sess = rt.InferenceSession('2_models/archive/TXCCNNmodel1013.onnx')
result = sess.run(None, {'input': input_data})

# OM 推理（需要昇腾环境）
# 调用相关 Ascend API
```

---

## 🔧 模型管理

### 查看模型信息
```python
import torch

# 加载模型
model = torch.load('2_models/best/ccnn_epoch_86_acc_0.9913.pth')

# 查看结构
print(model)

# 统计参数
total_params = sum(p.numel() for p in model.parameters())
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f'Total: {total_params}, Trainable: {trainable_params}')

# 查看权重
for name, param in model.named_parameters():
    print(f'{name}: {param.shape}')
```

### 模型转换
```bash
# PyTorch 转 ONNX
python -c "
import torch
import onnx

model = torch.load('2_models/best/ccnn_epoch_86_acc_0.9913.pth')
dummy_input = torch.randn(1, 2, 5000)
torch.onnx.export(model, dummy_input, 'model.onnx')
"

# 验证 ONNX
onnx.checker.check_model('model.onnx')
```

### 模型版本管理
```
2_models/
├── best/
│   └── ccnn_epoch_86_acc_0.9913.pth      # v1.0 当前版本
├── legacy/
│   └── TXCCNNmodel1013.pth               # v0.9 参考版本
└── archive/
    ├── ccnn_v0.8_acc_0.9800.pth          # 历史版本
    ├── ccnn_v0.7_acc_0.9650.pth
    └── TXCCNNmodel1013.onnx
```

---

## 📊 性能对比速查表

### 模型选择决策树
```
你的数据来源是什么？
├─ 合成信号（MATLAB）
│  └─ 使用 6 类模型 (best) ✓
├─ TX 真实数据
│  └─ 使用 5 类模型 (legacy) ✓
└─ 未知
   ├─ 尝试 5 类模型（更稳妥）
   └─ 如果需要 SIN，尝试 6 类
```

### 精度汇总
| 模型 | 类别 | 测试准确率 | TX_know | 建议 |
|------|------|----------|---------|------|
| best | 6 | 99.71% | 40% | 合成数据 |
| legacy | 5 | ~99% | 100% | 真实数据 |

---

## ⚠️ 已知问题

### 6 类模型 (best)
- ❌ TX_know 上表现差（40%）
- ⚠️ SIN 类导致其他类混淆
- 📋 见 EXPERIMENT_REPORT 了解详情

### 5 类模型 (legacy)
- ✅ TX_know 上表现完美
- ⚠️ 无法识别 SIN 类信号
- ✅ 生产稳定

---

## 📝 模型训练配置

### 最佳模型训练参数
```
优化器：Adam
学习率：0.001
批大小：16
训练轮数：100
验证集比例：20%
最优轮数：86
损失函数：CrossEntropyLoss
设备：CPU
```

### 数据配置
```
训练集：2880 样本
验证集：720 样本
类别：6
类别均衡：是（每类 600）
```

---

## 🚀 部署检查清单

- [ ] 模型文件完整（>100 KB）
- [ ] 正确的类别数（5 或 6）
- [ ] 输入维度正确（2, 5000）
- [ ] PyTorch 已安装
- [ ] 选择正确的模型（根据数据源）
- [ ] 设备兼容（CPU/CUDA）
- [ ] 性能验证通过

---

**最后更新**：2026-01-29  
**模型版本**：best v1.0 / legacy v0.9  
**建议**：根据数据来源选择合适的模型
