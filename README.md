<p align="center">
  <h1 align="center">面向信号干扰检测与识别的视频传输系统</h1>
  <p align="center">
    <strong>Interference-Aware Adaptive Video Transmission System</strong>
  </p>
  <p align="center">
    <em>基于 CCNN 的 7 类干扰信号识别 &amp; 自适应 QPSK 视频传输</em>
  </p>
</p>

---

## 项目概述

本项目设计并实现了一套完整的**干扰感知自适应视频传输系统**。系统能够实时检测并识别通信信道中的干扰信号类型，并据此动态调整传输参数，在恶劣电磁环境下最大化视频传输质量。

### 核心亮点

- **CCNN 干扰识别模型**：基于 CNN + SE 注意力 + 残差网络 + 多头因果注意力机制，7 类干扰分类准确率达 **99.91%**
- **硬件在环验证**：基于 USRP B210 软件无线电平台完成端到端实机测试
- **自适应传输策略**：根据干扰类型和强度动态调整 JPEG 质量、FEC 冗余度和帧率
- **实时可视化面板**：matplotlib 4 面板实时展示频谱、CCNN 概率、时域波形、JSR 曲线
- **完整系统闭环**：视频采集 -> JPEG 编码 -> FEC -> QPSK 调制 -> 信道传输 -> 解调解码 -> 视频显示

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
│      └──► CCNN 7类直接识别 ──► 自适应控制 ────────┘  │
│                    (反馈调整TX参数)                    │
└──────────────────────────────────────────────────┘
```

---

## 目录结构

```
毕设/
├── CCNN/                              # 干扰识别模型
│   ├── 1_datasets/                    # 数据集
│   │   ├── train/                     # 旧6类训练集 (39 npz, 397M)
│   │   ├── train_wide_jsr/            # 7类宽JSR训练集 (3 npz, 828M)
│   │   ├── test/                      # 测试集 (7 npz)
│   │   ├── samples/                   # 演示样本 (6 npz)
│   │   └── raw/                       # 原始数据
│   ├── 2_models/                      # 模型文件
│   │   ├── wide_jsr/                  # 7类模型 (43 checkpoints, best: epoch_26 99.91%)
│   │   ├── best/                      # 旧6类最佳模型 (99.13%)
│   │   ├── archive/                   # ONNX / .om 部署格式
│   │   └── legacy/                    # 早期实验模型
│   ├── 3_scripts/
│   │   └── training/
│   │       └── CCNN.py                # 模型定义 + 训练代码
│   ├── 4_results/                     # 训练日志与结果图
│   ├── 5_docs/                        # 技术文档
│   ├── 6_archive/                     # 历史归档
│   └── matlab_data_generate/          # MATLAB 数据生成脚本 (旧版, 保留对比)
│       ├── TX_*.m                     # 6类干扰信号生成 (MATLAB)
│       ├── PSK_MOD.m                  # PSK 调制
│       ├── study.m                    # 批量生成主脚本
│       └── data/                      # 3600个 .mat 文件
│
├── gnuradio/                          # 视频传输系统 (核心)
│   ├── video_transmission_system.py   # 主系统 (1500+ 行)
│   ├── cnn_interference_detector.py   # CCNN 干扰检测器封装
│   ├── run_system_with_viz.py         # 实时可视化运行脚本
│   ├── run_demo.sh                    # 一键启动脚本
│   ├── usrp_model_test_v4.py          # Python 信号生成器 (替代 MATLAB)
│   ├── generate_training_data.py      # 批量生成训练数据
│   ├── jsr_sweep_test.py              # JSR 精度扫描测试
│   ├── jsr_sweep_results.json         # JSR sweep 结果数据
│   ├── jsr_sweep_results.png          # JSR sweep 结果图
│   ├── usrp_chain_demo.py             # USRP 链路演示
│   ├── usrp_gnuradio_antenna_demo.py  # 天线测试演示
│   ├── experiment_jammer_results.json # 干扰注入实验数据
│   ├── fig_*.png                      # 实验结果图
│   └── README_*.md                    # 各模块说明文档
│
├── USRP/                              # USRP 硬件测试
│   ├── usrp_model_test.py             # 实机 JSR 扫描脚本
│   ├── plot_usrp_jsr.py               # JSR 曲线绘图
│   ├── usrp_jsr_results.json          # 实测结果数据
│   └── usrp_jsr_accuracy.pdf          # JSR 精度报告
│
├── venv/                              # Python 虚拟环境
│                                      # (torch, numpy, uhd, cv2, scipy, matplotlib)
│
├── 参考文献/                           # 论文参考文献
├── 进展/                              # 项目进展报告与论文草稿
├── MATLAB_vs_Python.md                # MATLAB vs Python 对比文档
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
│   CNN      │  Conv1d x 3 + BN + ReLU + AvgPool + Dropout
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
│ Classifier │  AvgPool -> FC(192->16) -> FC(16->7)
│  (7类)     │
└───────────┘
```

### 识别的 7 类信号

| 编号 | 类别 | 英文 | 特征描述 |
|:----:|:-----|:-----|:---------|
| 0 | 扫频干扰 | LFM (Linear Frequency Modulation) | 线性调频，频率随时间线性扫过宽带 |
| 1 | 多音干扰 | MTJ (Multi-Tone Jamming) | 多个等间隔单频信号叠加 |
| 2 | 窄带调幅 | NAM (Narrowband AM) | 窄带调幅噪声 |
| 3 | 窄带调频 | NFM (Narrowband FM) | 窄带调频噪声 |
| 4 | 单音干扰 | STJ (Single-Tone Jamming) | 单一频率的连续波干扰 |
| 5 | 正弦波 | SIN (Sine Wave) | 纯正弦信号 |
| 6 | 无干扰 | Clean | 正常 QPSK 信号 (防误报) |

### 训练结果

- **最佳模型**：`CCNN/2_models/wide_jsr/ccnn_epoch_26_acc_0.9991.pth`
- **测试准确率**：**99.91%**（Epoch 26, 7类含"无干扰"）
- **输入规格**：IQ 双通道，长度 5000（复数信号实部+虚部）
- **参数量**：96,921
- **JSR 范围**：-2 ~ 16 dB（-2dB 时仍达 99.4%）
- **误报率**：0%（60/60 正常信号正确识别为"无干扰"）

---

## 自适应视频传输系统

### 信号处理链路

| 模块 | 技术方案 | 参数 |
|:-----|:---------|:-----|
| 调制方式 | QPSK | 根升余弦脉冲成形，滚降系数 0.35 |
| 采样率 | 2 MHz | USRP B210 硬件采样 |
| 中心频率 | 2.45 GHz | ISM 频段 |
| 符号率 | 500 ksym/s | 4倍上采样 |
| 视频编码 | JPEG | 质量 20~85 自适应 |
| 前向纠错 | XOR 冗余编码 | 1~3 倍冗余 |
| 协议 | 自定义帧结构 | CRC-16 校验，480 字节最大载荷 |

### 干扰检测流程（CCNN 直接 7 类识别）

```
接收信号
    │
    ▼
┌──────────────────────┐
│   CCNN 7类直接识别     │  ──► 无干扰 ──► 正常传输
│ (6类干扰 + "无干扰"类)  │  ──► 干扰类型 ──► 自适应控制
│  输出: 类型 + 7类概率   │
└──────────┬───────────┘
           │
           ▼
    自适应控制器
    (JPEG质量 / FEC冗余 / 帧率)
```

### 自适应传输策略

| 干扰程度 | 触发条件 | JPEG质量 | FEC冗余 | 帧率 |
|:--------:|:---------|:--------:|:-------:|:----:|
| 无干扰 | 正常信号 | 70 | 1x | 25 fps |
| 轻度干扰 | NAM / NFM / SIN | 50 | 2x | 15 fps |
| 中度干扰 | LFM / MTJ | 30 | 2x | 8 fps |
| 严重干扰 | STJ | 20 | 3x | 5 fps |

> 采用滞后计数器（干扰连续 5 次确认切换，无干扰连续 8 次恢复）防止策略抖动。

---

## 实验结果

### JSR 扫描测试 (仿真)

| JSR (dB) | 总体准确率 | LFM | MTJ | NAM | NFM | STJ | SIN | Clean |
|:--------:|:---------:|:---:|:---:|:---:|:---:|:---:|:---:|:-----:|
| -6 | 65.3% | 66 | 90 | 26 | 71 | 55 | 49 | 100 |
| -4 | 96.0% | 100 | 97 | 87 | 99 | 89 | 100 | 100 |
| -2 | 99.4% | 100 | 98 | 99 | 100 | 99 | 100 | 100 |
| 0+ | **99.9%** | 100 | 99-100 | 100 | 100 | 100 | 100 | 100 |

### USRP 硬件在环测试

- **测试平台**：USRP B210 (serial: 7MFTKFU)
- **中心频率**：2.45 GHz | 采样率：2 MHz
- **结果**：干扰注入后检测有效，自适应策略正确切换，干扰清除后快速恢复

---

## 快速开始

### 环境要求

- Python 3.12+
- PyTorch 2.10+ (CPU)
- numpy, opencv-python, scipy, matplotlib
- UHD (仅 USRP 模式需要)

### 安装

```bash
git clone git@github.com:zhijielee6326/interference-aware-video-transmission.git
cd interference-aware-video-transmission

python3 -m venv venv
source venv/bin/activate
pip install torch numpy opencv-python-headless scipy matplotlib
```

### 仿真模式运行

```bash
cd gnuradio

# 方式1: 实时可视化面板 (推荐)
../venv/bin/python3 run_system_with_viz.py

# 方式2: cv2 面板 (手动按键注入干扰)
./run_demo.sh sim

# 方式3: 无GUI自动运行
./run_demo.sh sim --no-gui
```

### 实时可视化面板

运行 `run_system_with_viz.py` 会弹出 2x2 matplotlib 面板：

```
┌──────────────────────┬──────────────────────┐
│ 1. Real-time PSD     │ 2. CCNN 7-class      │
│    频谱图实时更新      │    概率柱状图          │
├──────────────────────┼──────────────────────┤
│ 3. Time-domain IQ    │ 4. JSR vs Accuracy   │
│    时域波形 I/Q       │    精度曲线(静态)      │
└──────────────────────┴──────────────────────┘
```

内置自动演示：每 5 秒自动切换一种干扰类型。

### USRP 实机模式

```bash
cd gnuradio
./run_demo.sh full             # 需要 USRP B210 连接
```

### CCNN 离线测试

```bash
cd gnuradio
../venv/bin/python3 cnn_interference_detector.py \
    --model ../CCNN/2_models/wide_jsr/ccnn_epoch_26_acc_0.9991.pth \
    --ccnn ../CCNN/3_scripts/training/CCNN.py --classes 7
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
| 数据生成 | MATLAB (旧版) / Python usrp_model_test_v4.py (当前) |

---

## 项目信息

- **作者**：李智杰
- **类型**：本科毕业设计
- **硬件平台**：USRP B210
- **开发环境**：Ubuntu, Python 3.12
- **GitHub**：https://github.com/zhijielee6326/interference-aware-video-transmission

---

## License

This project is for academic and educational purposes.
