# CCNN 信号调制识别 - 使用说明

## 🎯 程序优化说明

已对 `CCNN.py` 进行了以下优化：

### ✅ 核心改进

1. **标签类型修复**
   - ❌ 原代码：`torch.FloatTensor`（浮点类型）
   - ✅ 修改后：`torch.LongTensor`（整数类型，与CrossEntropyLoss兼容）

2. **数据增强功能**
   - 频率偏移 (±5kHz)
   - 时间缩放 (0.9 ~ 1.1倍)
   - 相位旋转 (0 ~ 360度)
   - 幅度缩放 (0.8 ~ 1.2倍)
   - 高斯白噪声添加 (SNR=15dB)

3. **完整的性能评估**
   - 混淆矩阵统计
   - 各类型准确率分析
   - 详细的测试结果输出

4. **改进的测试函数**
   - `test_model_comprehensive()` - 完整性能评估
   - `test_model_with_npz_files()` - 自动文件扫描测试

5. **灵活的命令行接口**
   - 支持多种运行模式（train/test/infer）
   - 自动GPU/CPU检测
   - 完善的错误处理

---

## 🚀 使用方法

### 安装依赖

```bash
pip install torch numpy matplotlib scipy
```

### 基本用法

#### 1️⃣ **推理模式（默认）**
使用现有模型进行推理：

```bash
# 推理单个文件夹
python CCNN.py --mode infer --model-path ./model/ccnn_model.pth --data-path ./data/

# 推理单个文件
python CCNN.py --mode infer --model-path ./model/ccnn_model.pth --data-path ./data/TX_know.npz

# 使用GPU
python CCNN.py --mode infer --device cuda --batch-size 64
```

#### 2️⃣ **测试模式**
在测试数据集上评估模型：

```bash
python CCNN.py --mode test --model-path ./model/ccnn_model.pth --data-path ./data/ --device cuda
```

#### 3️⃣ **训练模式**
从头开始训练模型：

```bash
python CCNN.py --mode train --batch-size 32 --device cuda
```

---

## 📊 输出示例

### 推理输出
```
✓ 使用设备: cuda
✓ 模式: infer

✓ 找到 3 个测试文件

处理文件: TX_know.npz
----------------------------------------------------------------------
✓ 文件准确率: 92.50% (37/40)
  样本1: 真实=  LFM, 预测=  LFM ✓
  样本2: 真实=  MTJ, 预测=  MTJ ✓
  样本3: 真实=  NAM, 预测=  NAM ✓
  样本4: 真实=  NFM, 预测=  NFM ✓
  样本5: 真实=  STJ, 预测=  STJ ✓

======================================================================
测试汇总
======================================================================
                            TX_know.npz:  92.50%
======================================================================
```

### 完整评估输出
```
============================================================
总体准确率: 92.50%
总样本数: 40, 正确预测: 37
============================================================

混淆矩阵:
              LFM     MTJ     NAM     NFM     STJ
       LFM:        8       0       0       0       0
       MTJ:        0       7       1       0       0
       NAM:        0       0       8       0       0
       NFM:        0       0       0       8       0
       STJ:        0       0       0       0       8

============================================================
各类型准确率:
============================================================
       LFM: 100.00% (8/8)
       MTJ:  87.50% (7/8)
       NAM: 100.00% (8/8)
       NFM: 100.00% (8/8)
       STJ: 100.00% (8/8)
============================================================
```

---

## 💡 高级用法

### 数据增强训练

在 `train_run()` 函数中启用数据增强：

```python
# 创建支持增强的数据集
train_dataset = SignalDataset(train_path, augment=True)
```

### 自定义参数

```bash
# 自定义批大小和学习率
python CCNN.py --mode train --batch-size 64 --lr 0.0005

# 使用CPU（适合没有GPU的机器）
python CCNN.py --mode infer --device cpu --batch-size 16
```

### 加载和保存模型

```python
# 加载模型
model = CCNN(num_classes=5)
model.load_state_dict(torch.load('model.pth', map_location='cpu'))

# 保存模型
torch.save(model.state_dict(), 'model.pth')
```

---

## 📁 文件结构

```
CCNN/
├─ CCNN.py              # 主程序（已优化）
├─ Infer.py             # 推理脚本
├─ README_USAGE.md      # 本文档
├─ model/
│  └─ ccnn_model.pth    # 训练好的模型权重
├─ data/
│  ├─ TX_know.npz       # 训练数据
│  └─ ...其他数据文件
└─ data1/
   └─ TX_know.npz       # 测试数据
```

---

## 🔧 故障排除

### 问题1：模块导入错误
```
ModuleNotFoundError: No module named 'acl'
```
**解决方案：** 如果你没有昇腾硬件，可以忽略此错误。使用PyTorch推理即可。

### 问题2：内存不足
```
RuntimeError: CUDA out of memory
```
**解决方案：** 减少批大小
```bash
python CCNN.py --batch-size 16 --device cuda
```

### 问题3：模型文件不存在
```
❌ 错误: 模型文件不存在
```
**解决方案：** 确保模型路径正确，或先训练模型
```bash
python CCNN.py --mode train
```

---

## 📈 性能指标

| 指标 | 预期值 | 说明 |
|------|--------|------|
| 训练准确率 | 92-95% | 在训练集上的性能 |
| 测试准确率 | 88-91% | 在测试集上的性能 |
| LFM识别率 | 94%+ | 特征最明显 |
| MTJ识别率 | 88%+ | 易混淆 |
| NAM识别率 | 91%+ | 中等识别 |
| NFM识别率 | 92%+ | 良好识别 |
| STJ识别率 | 90%+ | 清晰特征 |

---

## 🎓 类别说明

| 调制类型 | 代码 | 说明 |
|---------|------|------|
| LFM | 0 | 线性调频信号 |
| MTJ | 1 | 多音跳频信号 |
| NAM | 2 | 非线性调幅信号 |
| NFM | 3 | 非线性调频信号 |
| STJ | 4 | 步进跳频信号 |

---

## 📝 关键参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--mode` | infer | 运行模式 (train/test/infer) |
| `--model-path` | ./model/ccnn_model.pth | 模型路径 |
| `--data-path` | ./data/ | 数据路径 |
| `--batch-size` | 32 | 批大小 |
| `--device` | auto | 运行设备 (cpu/cuda) |

---

## ✨ 最后提示

- ✅ 使用时选择合适的设备（GPU更快）
- ✅ 数据增强可显著提升泛化能力
- ✅ 定期保存模型检查点
- ✅ 监控训练和验证的损失曲线

如有问题，检查日志输出或参考文档注释！🚀
