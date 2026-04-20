# USRP自发自收干扰检测验证指南

## 概述

使用单台USRP B210进行自发自收（loopback）测试，验证CCNN算法的干扰信号检测能力。

## 硬件连接

### 方式1: 物理回环（推荐）
使用50Ω同轴电缆连接USRP的TX/RX端口和RX2端口：
```
USRP B210
├── TX/RX (发送端) ──[同轴线+衰减器]──┐
└── RX2 (接收端) ────────────────────┘
```

**重要**: 建议在连接线上加30dB衰减器，避免接收端过载！

### 方式2: 软件回环
直接使用代码配置，无需物理连接（部分型号支持）。

## 环境准备

### 1. 激活虚拟环境
```bash
cd ~/毕设
source venv/bin/activate
```

### 2. 检查USRP连接
```bash
uhd_find_devices
# 应该看到你的USRP设备信息
```

### 3. 确认模型文件存在
```bash
ls -lh CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth
```

## 使用方法

### 快速测试（所有干扰类型）
```bash
cd ~/毕设/gnuradio
python3 usrp_loopback_test.py \
    --serial "serial=7MFTKFU" \
    --model ../CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth \
    --tests 10
```

### 测试特定干扰类型
```bash
# 测试单音干扰
python3 usrp_loopback_test.py --type tone --tests 20

# 测试扫频干扰
python3 usrp_loopback_test.py --type chirp --tests 20

# 测试脉冲干扰
python3 usrp_loopback_test.py --type pulse --tests 20

# 测试宽带噪声
python3 usrp_loopback_test.py --type noise --tests 20

# 测试无干扰（基线）
python3 usrp_loopback_test.py --type none --tests 20
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--serial` | USRP设备序列号 | serial=7MFTKFU |
| `--model` | CCNN模型路径 | ../CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth |
| `--classes` | 干扰类别数量 | 6 |
| `--tests` | 每种干扰的测试次数 | 10 |
| `--type` | 测试类型 (all/none/tone/chirp/pulse/noise) | all |

## 输出示例

```
======================================================================
USRP自发自收干扰检测验证系统
======================================================================
✓ USRP初始化完成
  频率: 2.45 GHz
  采样率: 2.0 MHz
  TX增益: 20 dB | RX增益: 35 dB

测试 [tone] 干扰...
  [1/10] ✓ 期望: 单音干扰 | 检测: 单音干扰 (置信度: 0.95)
  [2/10] ✓ 期望: 单音干扰 | 检测: 单音干扰 (置信度: 0.93)
  ...

======================================================================
测试结果总结
======================================================================

TONE:
  测试次数: 10
  正确次数: 9
  准确率: 90.0%

总体准确率: 88.5% (44/50)
======================================================================
```

## 故障排查

### 问题1: "No UHD Devices Found"
```bash
# 检查用户组
groups | grep usrp

# 如果没有usrp组，添加并重新登录
sudo usermod -a -G usrp $USER
sudo udevadm control --reload-rules && sudo udevadm trigger
# 然后重新登录或重启
```

### 问题2: 接收不到数据
- 检查物理连接是否正确
- 确认衰减器功率合适（建议30dB）
- 尝试调整RX增益：`--rx-gain 40`

### 问题3: 模型加载失败
```bash
# 检查模型文件
ls -lh ../CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth

# 检查PyTorch安装
python3 -c "import torch; print(torch.__version__)"
```

### 问题4: 检测准确率低
- 检查信号功率是否合适
- 调整TX/RX增益
- 确认物理连接质量
- 检查环境干扰

## 其他测试脚本

### 1. 使用现有的complete_system.py
```bash
python3 complete_system.py
# 按Ctrl+C停止
```

### 2. 使用signal_receiver.py进行自发自收
```bash
# 发送单音并检测
python3 signal_receiver.py \
    --serial "serial=7MFTKFU" \
    --tx-type tone \
    --tx-freq 2.45e9 \
    --tx-gain 20 \
    --tone-freq 500e3 \
    --model ../CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth \
    --save ../CCNN/1_datasets/raw/loopback_test.npz

# 发送视频信号并检测
python3 signal_receiver.py \
    --serial "serial=7MFTKFU" \
    --tx-type video \
    --tx-gain 20 \
    --model ../CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth
```

## 实验建议

1. **基线测试**: 先测试无干扰情况，确认系统正常
2. **单一干扰**: 逐个测试每种干扰类型
3. **混合干扰**: 修改代码添加多种干扰组合
4. **参数调优**: 调整增益、频率等参数观察影响
5. **数据保存**: 保存测试数据用于离线分析

## 下一步

- 调整信号参数（频率、功率、调制方式）
- 测试不同SNR条件下的检测性能
- 收集真实环境数据进行验证
- 生成实验报告和性能曲线

## 联系与支持

如有问题，请检查：
1. USRP硬件连接
2. 虚拟环境激活
3. 模型文件路径
4. 系统日志输出
