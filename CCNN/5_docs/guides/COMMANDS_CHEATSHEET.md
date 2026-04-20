# 🚀 CCNN 命令速查表

快速参考 - 复制粘贴即用

---

## ⚡ 最常用命令

### 📊 推理 (默认 - 最常用)

```bash
# 推理单个文件夹
python CCNN.py --mode infer --data-path ./data1/

# 使用GPU加速
python CCNN.py --mode infer --device cuda

# 指定模型和数据路径
python CCNN.py --mode infer \
  --model-path ./model/TXCCNNmodel1013.pth \
  --data-path ./data1/ \
  --batch-size 64
```

### 🧪 测试性能

```bash
# 完整的性能评估
python CCNN.py --mode test --data-path ./data/

# 指定模型
python CCNN.py --mode test \
  --model-path ./model/TXCCNNmodel1013.pth \
  --data-path ./data/
```

### 🎓 训练模型

```bash
# 从头开始训练
python CCNN.py --mode train

# 使用GPU训练 (推荐)
python CCNN.py --mode train --device cuda

# 指定批大小
python CCNN.py --mode train --batch-size 32 --device cuda
```

---

## 🎯 按场景分类

### 场景1: 快速推理测试
```bash
python CCNN.py --mode infer --device cuda --batch-size 64
```

### 场景2: 验证优化
```bash
python verify_optimization.py
```

### 场景3: 完整的模型评估
```bash
python CCNN.py --mode test \
  --model-path ./model/TXCCNNmodel1013.pth \
  --data-path ./data/
```

### 场景4: 改进训练 (数据增强)
```bash
# 编辑 CCNN.py，找到:
# dataset = SignalDataset(npz_path, augment=False)
# 改为:
# dataset = SignalDataset(npz_path, augment=True)

python CCNN.py --mode train --batch-size 32 --device cuda
```

### 场景5: CPU推理 (无GPU)
```bash
python CCNN.py --mode infer --device cpu --batch-size 16
```

---

## 📋 参数对照表

### 基础参数

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--mode` | 运行模式 | infer | train/test/infer |
| `--device` | 设备 | 自动 | cuda/cpu |
| `--batch-size` | 批大小 | 32 | 16/32/64 |
| `--model-path` | 模型路径 | - | ./model/ccnn.pth |
| `--data-path` | 数据路径 | - | ./data/ |

### 设备选择

```bash
# 自动选择 (推荐)
python CCNN.py --mode infer
# → 有GPU用GPU，否则用CPU

# 强制GPU
python CCNN.py --mode infer --device cuda

# 强制CPU
python CCNN.py --mode infer --device cpu
```

### 批大小选择

```bash
# 小批量 (内存少)
--batch-size 16

# 标准 (默认)
--batch-size 32

# 大批量 (内存足)
--batch-size 64

# 超大批量 (高吞吐)
--batch-size 128
```

---

## 🔧 高级用法

### 多参数组合

```bash
# GPU + 大批量 + 自定义路径
python CCNN.py --mode infer \
  --device cuda \
  --batch-size 128 \
  --model-path C:/models/best_model.pth \
  --data-path C:/data/test_signals/

# CPU + 小批量 + 内存优化
python CCNN.py --mode infer \
  --device cpu \
  --batch-size 8
```

### 训练参数调优

```bash
# 基础训练
python CCNN.py --mode train

# 快速训练 (小批量)
python CCNN.py --mode train --batch-size 8 --device cuda

# 优化训练 (大批量)
python CCNN.py --mode train --batch-size 64 --device cuda
```

### 性能诊断

```bash
# 验证所有优化
python verify_optimization.py

# 输出:
# ✓ 导入模块
# ✓ 模型初始化
# ✓ 数据集类
# ✓ 标签类型修复
# ✓ 数据增强
# ✓ 推理功能
```

---

## 💡 快速提示

### 💾 保存推理结果

```bash
# 创建脚本 save_results.py
python CCNN.py --mode infer --data-path ./data1/ > results.txt

# 查看结果
type results.txt  # Windows
cat results.txt   # Linux/Mac
```

### 📊 监控推理进度

```bash
# 实时监控
python CCNN.py --mode infer --batch-size 1  # 逐个处理
```

### ⚡ 加速推理

```bash
# 最快模式: GPU + 大批量
python CCNN.py --mode infer --device cuda --batch-size 256
```

### 🛠️ 调试模式

```bash
# 小数据测试
python CCNN.py --mode infer --batch-size 4
```

---

## 🎓 学习指南

### 第1步: 验证环境
```bash
python verify_optimization.py
# 预期: 6/6 通过 ✓
```

### 第2步: 快速推理
```bash
python CCNN.py --mode infer --device cuda
# 预期: 100% 准确率
```

### 第3步: 性能评估
```bash
python CCNN.py --mode test \
  --model-path ./model/TXCCNNmodel1013.pth \
  --data-path ./data/
# 预期: 详细的混淆矩阵
```

### 第4步: 改进训练
```bash
python CCNN.py --mode train --device cuda
# 预期: 训练曲线输出
```

---

## 🐛 故障排除

### 错误: ModuleNotFoundError: torch

```bash
# 使用指定的Python环境
C:/Users/m1889/anaconda3/envs/tf2-cpu/python.exe CCNN.py --mode infer
```

### 错误: CUDA out of memory

```bash
# 减少批大小
python CCNN.py --mode infer --batch-size 8

# 或切换到CPU
python CCNN.py --mode infer --device cpu
```

### 错误: 模型文件不存在

```bash
# 检查路径 (使用绝对路径最安全)
python CCNN.py --mode infer \
  --model-path "C:/path/to/model.pth"
```

### 错误: 找不到数据文件

```bash
# 确保路径存在
dir ./data1/   # Windows 查看目录

# 使用绝对路径
python CCNN.py --mode infer --data-path "C:/full/path/to/data/"
```

### 错误: OMP (OpenMP) 警告

```bash
# 设置环境变量 (Windows)
$env:KMP_DUPLICATE_LIB_OK="TRUE"
python CCNN.py --mode infer

# 或一行命令
cmd /c "set KMP_DUPLICATE_LIB_OK=TRUE && python CCNN.py --mode infer"
```

---

## 📞 命令帮助

```bash
# 查看所有可用选项
python CCNN.py --help

# 输出:
# usage: CCNN.py [-h] [--mode {train,test,infer}] 
#                 [--model-path MODEL_PATH]
#                 [--data-path DATA_PATH]
#                 [--batch-size BATCH_SIZE]
#                 [--device {cuda,cpu}]
```

---

## 🎯 最常用组合

### 日常使用 (推荐)
```bash
python CCNN.py --mode infer --device cuda
```

### 验证安装
```bash
python verify_optimization.py
```

### 性能测试
```bash
python CCNN.py --mode test --data-path ./data/
```

### GPU加速推理
```bash
python CCNN.py --mode infer --device cuda --batch-size 128
```

### CPU推理 (兼容性好)
```bash
python CCNN.py --mode infer --device cpu
```

---

## 📊 输出示例

### 推理输出
```
✓ 使用设备: cuda
✓ 模式: infer
✓ 找到 1 个测试文件

处理文件: TX_know.npz
✓ 文件准确率: 100.00% (20/20)
  样本1: 真实=LFM, 预测=LFM ✓
```

### 验证输出
```
✓ 导入模块
✓ 模型初始化
✓ 数据集类
✓ 标签类型修复
✓ 数据增强
✓ 推理功能

总体结果: 6/6 通过
🎉 所有优化验证成功！
```

---

## 🚀 一键启动

### Windows PowerShell
```powershell
$env:KMP_DUPLICATE_LIB_OK="TRUE"; python CCNN.py --mode infer --device cuda
```

### Windows CMD
```cmd
set KMP_DUPLICATE_LIB_OK=TRUE && python CCNN.py --mode infer --device cuda
```

### Linux/Mac
```bash
KMP_DUPLICATE_LIB_OK=TRUE python CCNN.py --mode infer --device cuda
```

---

**快速查询:** 复制上面的命令，修改路径，立即执行！

👉 **推荐命令 (复制即用):**
```bash
python CCNN.py --mode infer --device cuda --batch-size 64
```

