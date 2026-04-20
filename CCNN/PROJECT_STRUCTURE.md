# 干扰信号识别项目 - 项目结构说明

## 📂 项目整体结构

```
signal/
├── CCNN/                           # 深度学习模型目录
│   ├── 1_datasets/                # 数据集（3个子目录）
│   │   ├── train/                 # 训练数据集
│   │   ├── test/                  # 测试/验证数据集
│   │   ├── raw/                   # 原始 TX_know 数据
│   │   └── README.md
│   ├── 2_models/                  # 模型文件（3个子目录）
│   │   ├── best/                  # 最佳模型（6类，99.13%准确率）
│   │   ├── legacy/                # 旧版模型（5类，100%准确率）
│   │   ├── archive/               # 存档模型（ONNX等格式）
│   │   └── README.md
│   ├── 3_scripts/                 # Python 脚本（3个子目录）
│   │   ├── training/              # 训练脚本
│   │   ├── inference/             # 推理脚本
│   │   ├── utils/                 # 工具脚本
│   │   └── README.md
│   ├── 4_results/                 # 实验结果（2个子目录）
│   │   ├── logs/                  # 训练日志、推理结果
│   │   ├── plots/                 # 训练曲线、可视化
│   │   └── README.md
│   ├── 5_docs/                    # 文档资料（3个子目录）
│   │   ├── reports/               # 实验报告
│   │   ├── guides/                # 使用指南、快速开始
│   │   ├── checklists/            # 项目检查清单、历史记录
│   │   └── README.md
│   ├── 6_archive/                 # 归档资料（可选）
│   │   ├── matlab/                # MATLAB 原始代码
│   │   └── historical/            # 历史版本
│   └── PROJECT_STRUCTURE.md       # 本文件
│
├── matlab_data_generate/          # MATLAB 数据生成模块
│   ├── *.m                        # MATLAB 脚本
│   ├── data/                      # MATLAB 生成的 .mat 文件
│   └── README.md
│
└── [其他文件]
```

---

## 📊 各目录详细说明

### 1️⃣ 1_datasets/ - 数据集目录

**用途**：存放所有数据集文件（.npz 格式）

#### 1.1 train/ - 训练数据集
| 文件 | 大小 | 说明 |
|------|------|------|
| `all_training_data.npz` | ~1.5 GB | 完整训练集（3600样本，6类） |
| `all_training_data_LFM.npz` | ~250 MB | LFM 类专用（600样本） |
| `all_training_data_MTJ.npz` | ~250 MB | MTJ 类专用（600样本） |
| `all_training_data_NAM.npz` | ~250 MB | NAM 类专用（600样本） |
| `all_training_data_NFM.npz` | ~250 MB | NFM 类专用（600样本） |
| `all_training_data_STJ.npz` | ~250 MB | STJ 类专用（600样本） |
| `all_training_data_SIN.npz` | ~250 MB | SIN 类专用（600样本） |
| 单个原始文件 | ~10 MB each | 原始数据（39个） |

**配置**：
- 训练/验证分割：80/20
- 批大小：16
- 样本维度：(2, 5000)
- 类别数：6

#### 1.2 test/ - 测试/验证数据集
| 文件 | 样本数 | 准确率 |
|------|--------|--------|
| `inference_test_combined.npz` | 600 | 100.00% |
| `inference_test_LFM.npz` | 50 | 100.00% |
| `inference_test_MTJ.npz` | 50 | 98.00% |
| `inference_test_NAM.npz` | 50 | 100.00% |
| `inference_test_NFM.npz` | 50 | 100.00% |
| `inference_test_SIN.npz` | 50 | 100.00% |
| `inference_test_STJ.npz` | 50 | 100.00% |

**特点**：
- 完全独立于训练集（无数据泄露）
- 平衡分布（每类样本数相等）
- 从 3600 个原始 MATLAB 文件中随机抽取 25%

#### 1.3 raw/ - 原始数据
| 文件 | 样本数 | 说明 |
|------|--------|------|
| `TX_know.npz` | 20 | 真实 TX 传输数据 |

**用途**：
- 模型性能验证
- 真实数据兼容性测试
- 问题诊断

---

### 2️⃣ 2_models/ - 模型文件目录

**用途**：存放所有预训练模型和权重

#### 2.1 best/ - 最佳模型
| 文件 | 大小 | 参数 | 准确率 |
|------|------|------|--------|
| `ccnn_epoch_86_acc_0.9913.pth` | 395.8 KB | 49 | 99.13% |

**特性**：
- 类别数：6（LFM, MTJ, NAM, NFM, STJ, SIN）
- 训练轮数：100（第 86 轮最优）
- 验证准确率：99.13%
- 测试准确率：99.71%（独立测试集）
- 框架：PyTorch
- 设备兼容：CPU/CUDA

**推荐使用场景**：
- ✅ 合成信号分类
- ✅ 实验室研究
- ⚠️ 不推荐用于 TX_know 类型数据

#### 2.2 legacy/ - 旧版模型
| 文件 | 大小 | 参数 | 准确率 |
|------|------|------|--------|
| `TXCCNNmodel1013.pth` | 1.2 MB | - | 100%* |

**特性**：
- 类别数：5（LFM, MTJ, NAM, NFM, STJ）**不包含 SIN**
- TX_know 数据上的准确率：**100%**

**推荐使用场景**：
- ✅ TX_know 类型真实数据分类
- ✅ 原生产环境

**对比**：
```
6 类模型 (best) 在 TX_know 上：40% ❌
5 类模型 (legacy) 在 TX_know 上：100% ✅
```

#### 2.3 archive/ - 存档模型
| 文件 | 格式 | 说明 |
|------|------|------|
| `TXCCNNmodel1013.onnx` | ONNX | 开放格式 |
| `TXCCNNmodel1013.om` | OM | Ascend NPU 格式 |

**用途**：
- 跨平台部署
- 边缘计算设备
- 模型转换中间格式

---

### 3️⃣ 3_scripts/ - 脚本目录

**用途**：存放所有 Python 脚本和工具

#### 3.1 training/ - 训练脚本
| 文件 | 用途 | 主要函数 |
|------|------|---------|
| `CCNN.py` | 主训练脚本 | `train()`, `test()`, `infer()` |

**使用方法**：

```bash
# 训练模式
python 3_scripts/training/CCNN.py --mode train \
  --num-classes 6 \
  --batch-size 16 \
  --epochs 100 \
  --learning-rate 0.001 \
  --device cpu

# 测试模式
python 3_scripts/training/CCNN.py --mode test \
  --num-classes 6 \
  --model 2_models/best/ccnn_epoch_86_acc_0.9913.pth \
  --device cpu
```

**参数说明**：
- `--mode`: train/test/infer
- `--num-classes`: 类别数（5 或 6）
- `--batch-size`: 批大小
- `--epochs`: 训练轮数
- `--device`: cpu/cuda
- `--model`: 模型文件路径

#### 3.2 inference/ - 推理脚本
| 文件 | 用途 |
|------|------|
| `Infer.py` | 快速推理脚本 |

**使用方法**：

```bash
python 3_scripts/inference/Infer.py \
  --model 2_models/best/ccnn_epoch_86_acc_0.9913.pth \
  --data 1_datasets/test/inference_test_combined.npz \
  --num-classes 6
```

#### 3.3 utils/ - 工具脚本
| 文件 | 功能 |
|------|------|
| `analyze_tx_know.py` | TX_know 详细分析 |
| `compare_models.py` | 模型对比工具 |
| `verify_optimization.py` | 优化验证 |
| `md_to_docx.py` | Markdown 转 Word |

**使用示例**：

```bash
# 分析 TX_know 数据
python 3_scripts/utils/analyze_tx_know.py

# 对比不同模型
python 3_scripts/utils/compare_models.py

# Markdown 转 Word
python 3_scripts/utils/md_to_docx.py
```

---

### 4️⃣ 4_results/ - 结果输出目录

**用途**：存放所有实验结果和输出

#### 4.1 logs/ - 日志文件
| 文件 | 说明 |
|------|------|
| `inference_full_results.txt` | 完整推理结果 |
| `inference_test.log` | 测试日志 |

#### 4.2 plots/ - 可视化图表
| 文件 | 说明 |
|------|------|
| `training_performance.png` | 训练曲线图 |

---

### 5️⃣ 5_docs/ - 文档目录

**用途**：项目文档、说明和指南

#### 5.1 reports/ - 实验报告
| 文件 | 格式 | 内容 |
|------|------|------|
| `EXPERIMENT_REPORT.md` | Markdown | 完整实验报告 |
| `EXPERIMENT_REPORT.docx` | Word | 同上（Word版本） |

**包含内容**：
- 背景与目标
- 方法论
- 详细结果
- 深度分析
- 结论与建议

#### 5.2 guides/ - 使用指南
| 文件 | 内容 |
|------|------|
| `QUICKSTART.md` | 5 分钟快速开始 |
| `README_USAGE.md` | 详细使用说明 |
| `COMMANDS_CHEATSHEET.md` | 命令速查表 |

#### 5.3 checklists/ - 检查清单
| 文件 | 内容 |
|------|------|
| `SUCCESS_REPORT.md` | 成功指标 |
| `BUGFIX_REPORT.md` | 已修复问题 |
| `OPTIMIZATION_SUMMARY.md` | 优化总结 |
| `FILES_MANIFEST.md` | 文件清单 |

---

### 6️⃣ 6_archive/ - 归档目录（可选）

**用途**：存放旧版本、参考资料

#### 6.1 matlab/ - MATLAB 代码
存放 MATLAB 生成脚本的备份

#### 6.2 historical/ - 历史版本
存放旧版本模型或过期脚本

---

## 🚀 快速开始

### 场景 1：使用现有模型进行推理

```bash
cd CCNN

# 推理 6 类模型
python 3_scripts/inference/Infer.py \
  --model 2_models/best/ccnn_epoch_86_acc_0.9913.pth \
  --data 1_datasets/test/inference_test_combined.npz \
  --num-classes 6

# 推理 5 类模型（TX_know 数据）
python 3_scripts/inference/Infer.py \
  --model 2_models/legacy/TXCCNNmodel1013.pth \
  --data 1_datasets/raw/TX_know.npz \
  --num-classes 5
```

### 场景 2：重新训练模型

```bash
cd CCNN

# 使用训练脚本
python 3_scripts/training/CCNN.py --mode train \
  --num-classes 6 \
  --epochs 100 \
  --batch-size 16 \
  --device cpu
```

### 场景 3：查看完整实验报告

```bash
# 打开 Word 版本
open 5_docs/reports/EXPERIMENT_REPORT.docx

# 或查看 Markdown 版本
cat 5_docs/reports/EXPERIMENT_REPORT.md
```

---

## ⚠️ 重要发现

### SIN 类问题

**现象**：
- 6 类模型在合成数据上表现优异（99.71%）
- 6 类模型在 TX_know 上表现不佳（40%）
- 5 类模型（无 SIN 类）在 TX_know 上完美（100%）

**结论**：
新增的 SIN 类导致其他 5 个类别的学习性能恶化，特别是对 NAM、NFM、STJ 类的分类精度大幅下降。

**建议**：
对于 TX_know 类型的真实数据，继续使用 5 类旧版模型，直至问题根本解决。

---

## 📝 文件管理规范

### 添加新数据集
```
1_datasets/train/     # 新训练数据
1_datasets/test/      # 新测试数据
1_datasets/raw/       # 新的原始数据
```

### 添加新模型
```
2_models/best/        # 新的最佳模型
2_models/legacy/      # 旧版本/参考模型
2_models/archive/     # 转换格式/弃用模型
```

### 添加新脚本
```
3_scripts/training/   # 训练相关
3_scripts/inference/  # 推理相关
3_scripts/utils/      # 工具类
```

### 保存结果
```
4_results/logs/       # 所有日志输出
4_results/plots/      # 图表和可视化
```

---

## 🔗 相关链接

- 📄 **完整实验报告**：[5_docs/reports/EXPERIMENT_REPORT.md](5_docs/reports/EXPERIMENT_REPORT.md)
- 🚀 **快速开始指南**：[5_docs/guides/QUICKSTART.md](5_docs/guides/QUICKSTART.md)
- ⚙️ **命令速查表**：[5_docs/guides/COMMANDS_CHEATSHEET.md](5_docs/guides/COMMANDS_CHEATSHEET.md)
- 📊 **使用说明**：[5_docs/guides/README_USAGE.md](5_docs/guides/README_USAGE.md)

---

## 📞 支持与反馈

- 问题报告：见 [5_docs/checklists/BUGFIX_REPORT.md](5_docs/checklists/BUGFIX_REPORT.md)
- 优化记录：见 [5_docs/checklists/OPTIMIZATION_SUMMARY.md](5_docs/checklists/OPTIMIZATION_SUMMARY.md)
- 更新日志：见 [5_docs/checklists/CHANGES.md](5_docs/checklists/CHANGES.md)

---

**最后更新**：2026-01-29  
**项目版本**：v1.1（整理后）  
**状态**：✅ 生产就绪（需 SIN 类诊断）
