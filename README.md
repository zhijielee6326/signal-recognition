<p align="center">
  <h1 align="center">面向信号干扰检测与识别的视频传输系统</h1>
  <p align="center">
    <strong>Interference-Aware Adaptive Video Transmission System</strong>
  </p>
  <p align="center">
    <em>基于 CCNN 的 6 类干扰信号识别 &amp; 自适应 QPSK 视频传输</em>
  </p>
</p>

---

## 项目概述

本项目设计并实现了一套完整的**干扰感知自适应视频传输系统**。系统能够实时检测并识别通信信道中的干扰信号类型，并据此动态调整传输参数，在恶劣电磁环境下最大化视频传输质量。

### 核心亮点

- **CCNN 干扰识别模型**：基于 CNN + SE 注意力 + 残差网络 + 多头因果注意力机制，6 类干扰分类准确率达 **99.13%**
- **硬件在环验证**：基于 USRP B210 软件无线电平台完成端到端实机测试
- **自适应传输策略**：根据干扰类型和强度动态调整 JPEG 质量、FEC 冗余度和帧率
- **完整系统闭环**：视频采集 → JPEG 编码 → FEC → QPSK 调制 → 信道传输 → 解调解码 → 视频显示

---

## 系统架构

```
┌──────────────────── TX 端 ────────────────────┐
│                                                │
│  视频源 ──► JPEG编码 ──► 分包 ──► FEC编码 ──►  │
│                                        QPSK调制 │
│                                            │    │
└────────────────────────────────────────────┼────┘
                                             │
                                    ┌────────▼────────┐
                                    │    无线信道       │
                                    │  (AWGN + 干扰)   │
                                    └────────┬────────┘
                                             │
┌──────────────────── RX 端 ──────────────────┼────┐
│                                             │    │
│  QPSK解调 ◄── 频偏校正 ◄── AGC ◄── USRP接收     │
│      │                                          │
│      ├──► 分包重组 ──► FEC解码 ──► JPEG解码 ──► 视频显示 │
│      │                                          │
│      └──► 功率谱检测 ──► CCNN识别 ──► 自适应控制 ─┘  │
│                          (反馈调整TX参数)           │
└──────────────────────────────────────────────────┘
```

---

## 目录结构

```
.
├── CCNN/                              # CCNN 干扰识别模型
│   ├── 1_datasets/                    # 数据集
│   │   ├── samples/                   # 各类干扰样本数据 (npz)
│   │   └── README.md                  # 数据集说明
│   ├── 2_models/
│   │   ├── best/                      # 最优模型 (99.13% acc)
│   │   │   └── ccnn_epoch_86_acc_0.9913.pth
│   │   ├── legacy/                    # 早期模型
│   │   └── archive/                   # ONNX / .om 部署格式
│   ├── 3_scripts/
│   │   ├── training/
│   │   │   └── CCNN.py                # 模型定义 + 训练代码
│   │   ├── inference/
│   │   │   └── Infer.py               # 推理代码 (华为昇腾)
│   │   └── utils/                     # 工具脚本
│   ├── 4_results/                     # 训练日志与结果图
│   └── 5_docs/                        # 详细技术文档
│
├── gnuradio/                          # 视频传输系统
│   ├── video_transmission_system.py   # 主系统 (1400+ 行)
│   ├── cnn_interference_detector.py   # CCNN 干扰检测器封装
│   ├── run_demo.sh                    # 一键启动脚本
│   ├── complete_system.py             # 完整系统演示
│   ├── usrp_model_test_v4.py          # USRP 模型测试
│   ├── usrp_chain_demo.py             # USRP 链路演示
│   ├── fig_*.png                      # 实验结果图
│   └── *.json                         # JSR 扫描实验数据
│
├── USRP/                              # USRP 硬件测试
│   ├── usrp_model_test.py             # 实机 JSR 扫描脚本
│   ├── plot_usrp_jsr.py               # JSR 曲线绘图
│   ├── usrp_jsr_results.json          # 实测结果数据
│   └── usrp_jsr_accuracy.pdf          # JSR 精度报告
│
├── 进展/                              # 项目进展报告
└── README.md                          # 本文件
```

---

## CCNN 干扰识别模型

### 网络结构

```
输入 (2, 5000) IQ信号
    │
    ▼
┌───────────┐
│   CNN      │  Conv1d×3 + BN + ReLU + AvgPool + Dropout
│ (128ch)    │  提取局部时域特征
└─────┬─────┘
      ▼
┌───────────┐
│  ResNet    │  残差卷积块 + SE通道注意力 (reduction=16)
│  (32ch)    │  自适应增强重要特征通道
└─────┬─────┘
      ▼
┌───────────┐
│  TCC_mod   │  因果卷积多头注意力 (4头) + LayerNorm + FFN
│  (32ch)    │  捕捉全局时序依赖关系
└─────┬─────┘
      ▼
┌───────────┐
│ Classifier │  AvgPool → FC(192→16) → FC(16→6)
│  (6类)     │
└───────────┘
```

### 识别的 6 类干扰信号

| 编号 | 类别 | 英文 | 特征描述 |
|:----:|:-----|:-----|:---------|
| 0 | 扫频干扰 | LFM (Linear Frequency Modulation) | 线性调频，频率随时间线性扫过宽带 |
| 1 | 多音干扰 | MTJ (Multi-Tone Jamming) | 多个等间隔单频信号叠加 |
| 2 | 窄带调幅 | NAM (Narrowband AM) | 窄带调幅噪声 |
| 3 | 窄带调频 | NFM (Narrowband FM) | 窄带调频噪声 |
| 4 | 单音干扰 | STJ (Single-Tone Jamming) | 单一频率的连续波干扰 |
| 5 | 正弦波 | SIN (Sine Wave) | 纯正弦信号 |

### 训练结果

- **最佳模型**：`CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth`
- **测试准确率**：**99.13%**（Epoch 86）
- **输入规格**：IQ 双通道，长度 5000（复数信号实部+虚部）
- **参数量**：约 30 万

---

## 自适应视频传输系统

### 信号处理链路

| 模块 | 技术方案 | 参数 |
|:-----|:---------|:-----|
| 调制方式 | QPSK | 根升余弦脉冲成形，滚降系数 0.35 |
| 采样率 | 2 MHz | USRP B210 硬件采样 |
| 中心频率 | 2.45 GHz | ISM 频段 |
| 符号率 | 500 ksym/s | 4倍上采样 |
| 视频编码 | JPEG | 质量 15~85 自适应 |
| 前向纠错 | XOR 冗余编码 | 1~3 倍冗余 |
| 协议 | 自定义帧结构 | CRC-16 校验，488 字节最大载荷 |

### 干扰检测流程（两级检测）

```
接收信号
    │
    ▼
┌──────────────────────┐
│ 第1级：功率谱特征检测  │  ──► 无干扰 ──► 正常传输
│ (peak_to_noise,      │
│  谱熵, top-10占比)   │
└──────────┬───────────┘
           │ 检测到异常
           ▼
┌──────────────────────┐
│ 第2级：CCNN 分类识别  │  ──► 输出干扰类型 + 置信度
│ (6类干扰分类)         │
└──────────┬───────────┘
           │
           ▼
    自适应控制器
    (JPEG质量 / FEC冗余 / 帧率)
```

### 自适应传输策略

| 干扰程度 | 触发条件 | JPEG质量 | FEC冗余 | 帧率 |
|:--------:|:---------|:--------:|:-------:|:----:|
| 无干扰 | 正常信号 | 85 | 1x | 25 fps |
| 轻度干扰 | NAM / NFM / SIN | 55 | 2x | 15 fps |
| 中度干扰 | LFM / MTJ | 35 | 2x | 8 fps |
| 严重干扰 | STJ | 15 | 3x | 5 fps |

> 采用滞后计数器（干扰连续 5 次确认切换，无干扰连续 8 次恢复）防止策略抖动。

---

## 实验结果

### USRP 硬件在环测试

使用 USRP B210 进行端到端实机测试，在 1 GHz 中心频率下对不同干信比 (JSR) 下各干扰类型的识别准确率进行了扫描：

- **测试平台**：USRP B210 (serial: 7MFTKFU)
- **中心频率**：1 GHz
- **采样率**：2 MHz
- **JSR 范围**：-10 dB ~ 10 dB

### 关键实验数据

- 仿真模式：TX/RX 完美匹配，自适应传输工作正常
- USRP 实机模式：TX/RX 运行稳定，干扰检测零误报
- CCNN 模型：训练数据集准确率 99.13%，实机识别有效
- 自适应策略：干扰注入后视频质量可控下降，干扰清除后快速恢复

---

## 快速开始

### 环境要求

- Python 3.12+
- PyTorch 2.10+ (CPU)
- numpy, opencv-python, scipy, matplotlib
- UHD (仅 USRP 模式需要)

### 安装

```bash
git clone https://github.com/zhijielee6326/signal-recognition.git
cd signal-recognition

python3 -m venv venv
source venv/bin/activate
pip install torch numpy opencv-python scipy matplotlib
```

### 仿真模式运行

```bash
cd gnuradio
./run_demo.sh sim              # 仿真模式（无需 USRP）
./run_demo.sh sim camera       # 仿真 + 摄像头
./run_demo.sh sim video.mp4    # 仿真 + 视频文件
```

### USRP 实机模式

```bash
cd gnuradio
./run_demo.sh full             # 需要 USRP B210 连接
```

### CCNN 离线测试

```bash
cd gnuradio
python3 cnn_interference_detector.py \
    --model ../CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth \
    --ccnn ../CCNN/3_scripts/training/CCNN.py
```

---

## 技术栈

| 领域 | 技术 |
|:-----|:-----|
| 深度学习 | PyTorch, CNN, SE-Attention, Multi-Head Attention |
| 软件无线电 | UHD / USRP B210, QPSK 调制解调 |
| 信号处理 | FFT 功率谱分析, RRC 脉冲成形, CFO 估计校正 |
| 视频处理 | OpenCV, JPEG 编解码, 自适应质量控制 |
| 信道编码 | XOR 前向纠错, CRC-16 校验 |
| 模型部署 | ONNX, 华为昇腾 .om |

---

## 项目信息

- **作者**：李智杰
- **类型**：本科毕业设计
- **硬件平台**：USRP B210
- **开发环境**：Ubuntu 22.04, Python 3.12

---

## License

This project is for academic and educational purposes.
