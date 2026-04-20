# 视频传输系统使用说明

## 环境要求

- Python 3.12
- 虚拟环境: `~/桌面/毕设/venv/`
- 硬件(可选): USRP B210

### 依赖安装

```bash
~/桌面/毕设/venv/bin/python3 -m pip install numpy scipy torch opencv-python-headless==4.9.0.80
# UHD驱动需通过系统包安装
```

## 运行方式

### 1. 仿真模式(无需USRP)

```bash
cd ~/桌面/毕设/gnuradio
~/桌面/毕设/venv/bin/python3 video_transmission_system.py --mode sim --source test
```

运行时按键:
- `1` - 注入单音干扰(STJ)
- `2` - 注入多音干扰(MTJ)
- `3` - 注入扫频干扰(LFM)
- `4` - 注入窄带AM干扰(NAM)
- `5` - 注入窄带FM干扰(NFM)
- `6` - 注入正弦调频干扰(SIN)
- `0` - 清除干扰
- `Q` - 退出

视频源选项:
- `test` - 自动生成测试图案(默认)
- `camera` - 摄像头
- `video.mp4` - 视频文件路径

### 2. USRP实机模式

```bash
# 确保USRP B210已连接
~/桌面/毕设/venv/bin/python3 video_transmission_system.py --mode full --source test --serial "serial=7MFTKFU"
```

硬件连接: TX/RX端口 与 RX2端口 天线空口耦合(间距10~50cm)

### 3. 无GUI后台模式

```bash
~/桌面/毕设/venv/bin/python3 video_transmission_system.py --mode sim --source test --no-gui --duration 30
```

## 系统架构

```
[TX端]
视频源 -> JPEG编码(可调质量) -> 分包+CRC16 -> FEC冗余编码 -> QPSK调制 -> USRP发送

[RX端]
USRP接收 -> AGC -> 频偏校正 -> QPSK解调 -> 去包+CRC校验 -> FEC解码 -> JPEG解码 -> 显示

[干扰监测]
接收信号 -> PSD特征提取 -> 干扰检测(二值判决) -> CCNN干扰类型识别 -> 自适应策略调整
```

## 自适应传输策略

| 干扰级别 | JPEG质量 | FEC冗余 | 帧率  | 触发条件              |
|---------|---------|--------|------|----------------------|
| 无干扰   | 85      | 1x     | 25fps | 连续8次无干扰检测       |
| 轻度     | 55      | 2x     | 15fps | 连续5次检测到轻度干扰    |
| 中度     | 35      | 2x     | 8fps  | 连续5次检测到中度干扰    |
| 严重     | 15      | 3x     | 5fps  | 连续5次检测到严重干扰    |

## 干扰类型映射

| CCNN识别结果    | 严重程度 |
|---------------|--------|
| 无干扰         | none   |
| 窄带AM(NAM)    | mild   |
| 窄带FM(NFM)    | mild   |
| 正弦波(SIN)    | mild   |
| 多音干扰(MTJ)  | moderate |
| 扫频干扰(LFM)  | moderate |
| 单音干扰(STJ)  | severe |

## 关键参数

| 参数 | 仿真模式 | USRP模式 |
|-----|---------|---------|
| 分辨率 | 320x240 | 160x120 |
| 采样率 | 2MHz | 2MHz |
| 中心频率 | 2.45GHz | 2.45GHz |
| 调制方式 | QPSK | QPSK |
| 符号率 | 500ksps | 500ksps |
| TX增益 | - | 20dB |
| RX增益 | - | 40dB |

## 实验图表

- `fig_adaptive_transmission.png` - 自适应策略时序图
- `fig_psd_comparison.png` - 各干扰类型PSD对比
- `fig_adaptive_comparison.png` - 自适应vs非自适应帧接收率对比
- `experiment_jammer_results.json` - 各干扰类型识别结果数据
