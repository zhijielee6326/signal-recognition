# 信号干扰检测与自适应视频传输系统 - 验收说明

## 系统概述

本系统实现了完整的**信号干扰检测识别 + 自适应视频传输**闭环：

```
TX: 视频 -> JPEG -> FEC -> QPSK调制 -> 发送
RX: 接收 -> QPSK解调 -> FEC解码 -> JPEG解码 -> 显示
干扰监测: CCNN(7类)实时检测 -> 自适应调整传输参数
```

## 快速启动

```bash
# 进入项目目录
cd ~/桌面/毕设/gnuradio

# 激活虚拟环境（run_demo.sh会自动处理）

# 仿真模式（无需USRP硬件）
./run_demo.sh sim

# USRP实机模式（需要B210连接）
./run_demo.sh full
```

## 运行时操作

### 仿真模式 (sim)
启动后按键盘控制干扰注入：
- **1**: 注入扫频干扰(LFM)
- **2**: 注入多音干扰(MTJ)
- **3**: 注入窄带AM(NAM)
- **4**: 注入窄带FM(NFM)
- **5**: 注入单音干扰(STJ)
- **6**: 注入正弦波干扰(SIN)
- **0**: 清除干扰
- **+/-**: 调整JSR（干信比）
- **q/Esc**: 退出

### 系统响应
当检测到干扰时，系统自动调整：
| 干扰类型 | 传输策略 |
|---------|---------|
| 无干扰   | 高质量: Q=85, FEC=1x, FPS=25 |
| 窄带AM   | 降质保传: Q=55, FEC=2x, FPS=15 |
| 窄带FM   | 降质保传: Q=55, FEC=2x, FPS=15 |
| LFM/MTJ  | 低质冗余: Q=35, FEC=2x, FPS=8 |
| 单音STJ  | 最低质保: Q=15, FEC=3x, FPS=5 |

## CCNN 干扰识别模型

### 7类识别（含"无干扰"）
- 0: 扫频干扰(LFM)
- 1: 多音干扰(MTJ)
- 2: 窄带AM(NAM)
- 3: 窄带FM(NFM)
- 4: 单音干扰(STJ)
- 5: 正弦波(SIN)
- 6: 无干扰

### JSR-准确率测试结果
模型文件: `CCNN/2_models/wide_jsr/ccnn_epoch_26_acc_0.9991.pth`

| JSR(dB) | LFM | MTJ | NAM | NFM | STJ | SIN | CLEAN | Overall |
|---------|-----|-----|-----|-----|-----|-----|-------|---------|
| -6      | 66% | 90% | 26% | 71% | 55% | 49% | 100%  | 65.3%   |
| -4      | 100%| 97% | 87% | 99% | 89% |100% | 100%  | 96.0%   |
| -2      | 100%| 98% | 99% |100% | 99% |100% | 100%  | 99.4%   |
| 0       | 100%| 99% |100% |100% |100% |100% | 100%  | 99.9%   |
| >=2     | 100%|100% |100% |100% |100% |100% | 100%  | 100%    |

**关键指标：**
- JSR >= 0dB: 准确率 99.9%
- JSR >= -2dB: 准确率 99.4%
- 无干扰信号: **0%误报率**（60/60 正确识别为"无干扰"）

### JSR-准确率曲线
参见: `gnuradio/jsr_sweep_results.png`

## JSR Sweep 测试

```bash
cd ~/桌面/毕设/gnuradio
/home/zhijielee/桌面/毕设/venv/bin/python3 jsr_sweep_test.py \
  --model /home/zhijielee/桌面/CCNN/2_models/wide_jsr/ccnn_epoch_26_acc_0.9991.pth \
  --num-classes 7 --device cpu
```

输出:
- 控制台: 准确率表格
- `jsr_sweep_results.json`: JSON详细数据
- `jsr_sweep_results.png`: JSR-准确率曲线图

## 项目文件结构

```
毕设/
├── gnuradio/
│   ├── video_transmission_system.py  # 主系统（TX/RX/干扰检测/自适应）
│   ├── cnn_interference_detector.py  # CCNN推理封装
│   ├── usrp_model_test_v4.py        # Python信号生成器（6类干扰+PSK）
│   ├── generate_training_data.py    # 训练数据生成脚本
│   ├── jsr_sweep_test.py            # JSR Sweep测试+画图
│   ├── run_demo.sh                  # 一键启动脚本
│   └── jsr_sweep_results.png        # JSR-准确率曲线
│
└── CCNN/
    ├── 1_datasets/train_wide_jsr/
    │   ├── train_split.npz           # 训练集 (10640样本, 7类)
    │   ├── test_split.npz            # 测试集 (2660样本)
    │   └── sweep_test/               # JSR Sweep测试数据
    ├── 2_models/wide_jsr/
    │   └── ccnn_epoch_26_acc_0.9991.pth  # 最佳模型
    └── 3_scripts/training/CCNN.py    # 模型定义+训练代码
```

## 核心改进（相比旧版本）

1. **训练数据覆盖低JSR**: JSR范围从 {6,8,10,12,14}dB 扩展到 {-2,0,2,4,6,8,10,12,14,16}dB
2. **7类模型**: 新增"无干扰"类，解决误报问题
3. **数据一致性**: 训练数据/SimChannel/推理端全部使用同一套Python生成器
4. **CCNN直接检测**: 移除PSD门控，CCNN直接输出干扰类型（含无干扰）
5. **SimulatedChannel**: 从MATLAB数据改为Python生成器，与训练数据一致

## 验证命令

```bash
# 1. JSR Sweep测试
cd ~/桌面/毕设/gnuradio
/home/zhijielee/桌面/毕设/venv/bin/python3 jsr_sweep_test.py \
  --model ~/桌面/CCNN/2_models/wide_jsr/ccnn_epoch_26_acc_0.9991.pth \
  --num-classes 7

# 2. 仿真模式集成测试
./run_demo.sh sim
# 启动后按 1-6 注入干扰，观察系统自动调整
# 按 0 清除干扰，观察系统恢复

# 3. USRP模式（需B210）
./run_demo.sh full
```

## 训练命令（已执行完毕，供参考）

```bash
# 1. 生成训练数据
/home/zhijielee/桌面/毕设/venv/bin/python3 generate_training_data.py

# 2. 训练模型
/home/zhijielee/桌面/毕设/venv/bin/python3 -u ~/桌面/CCNN/3_scripts/training/CCNN.py \
  --mode train \
  --data-path ~/桌面/CCNN/1_datasets/train_wide_jsr/train_split.npz \
  --num-classes 7 --epochs 120 --batch-size 64 --device cpu
```

训练日志: `~/桌面/CCNN/3_scripts/training/train_wide_jsr.log`
