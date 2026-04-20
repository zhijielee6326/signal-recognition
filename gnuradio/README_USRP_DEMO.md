# USRP B210 入门 Demo 使用说明

本目录提供两个适合新手上手的 USRP B210 演示：

1. `usrp_chain_demo.py`
   - Python 终端版全链路 demo
   - 功能：发射单音、接收单音、实时打印接收功率和峰值频率

2. `usrp_gnuradio_antenna_demo.py`
   - GNU Radio 图形化 demo
   - 功能：发射单音，并在 GUI 中实时显示接收频谱和时域波形

---

## 一、适用场景

本说明适用于：
- 设备型号：USRP B210
- 系统环境：Ubuntu 20.04 / 22.04 / 24.04
- 耦合方式：天线近距离空口耦合

硬件连接建议：
- TX 端口接发射天线
- RX2 端口接接收天线
- 两副天线相距 `10~50 cm`
- 第一次测试时请从较低增益开始，避免接收过强或前端饱和

---

## 二、所需环境

### 1. 必需环境
- Python 3
- UHD 驱动
- UHD 镜像文件
- USRP B210 已能被系统识别

### 2. Python 版 demo 依赖
- `numpy`
- `uhd`

### 3. GNU Radio 版 demo 依赖
- `gnuradio`
- `PyQt5`
- `UHD for GNU Radio`

---

## 三、先确认驱动正常

先执行：

```bash
uhd_find_devices
```

如果可以看到 B210 设备信息，再继续后面的 demo。

也可以进一步确认：

```bash
uhd_usrp_probe
```

如果还没有安装驱动，可先到补丁目录运行：

```bash
cd "/home/zhijielee/桌面/patch"
sudo ./patch.sh
```

---

## 四、Demo 1：Python 终端版

脚本文件：

```bash
/home/zhijielee/桌面/毕设/gnuradio/usrp_chain_demo.py
```

### 运行方式

```bash
cd "/home/zhijielee/桌面/毕设/gnuradio"
python3 usrp_chain_demo.py --serial "serial=7MFTKFU"
```

### 默认参数
- 中心频率：`1 GHz`
- 采样率：`1 MSps`
- 单音频率：`100 kHz`
- TX 增益：`20 dB`
- RX 增益：`35 dB`

### 天线耦合建议
如果使用天线空口耦合，建议先降低增益，例如：

```bash
python3 usrp_chain_demo.py \
  --serial "serial=7MFTKFU" \
  --tx-gain 10 \
  --rx-gain 20
```

### 运行成功的现象
终端会持续输出类似信息：

```text
[RX] 已启动 | fc=1000.000 MHz | fs=1.000 MHz | gain=20.0 dB
[TX] 已启动 | fc=1000.000 MHz | fs=1.000 MHz | gain=10.0 dB | tone=100.0 kHz
[Frame 000] RX功率=... dB | 峰值频率=100.1 kHz | 峰值幅度=...
```

如果峰值频率稳定在 `100 kHz` 附近，说明链路已经跑通。

---

## 五、Demo 2：GNU Radio 图形化版

脚本文件：

```bash
/home/zhijielee/桌面/毕设/gnuradio/usrp_gnuradio_antenna_demo.py
```

### 运行方式

```bash
cd "/home/zhijielee/桌面/毕设/gnuradio"
python3 usrp_gnuradio_antenna_demo.py --serial "serial=7MFTKFU"
```

### 天线耦合推荐启动参数

```bash
python3 usrp_gnuradio_antenna_demo.py --serial "serial=7MFTKFU" --tx-gain 10 --rx-gain 20
```

### GUI 中应看到的现象
- 频谱窗口中在 `100 kHz` 附近有明显单音峰值
- 时域窗口中可看到稳定接收波形
- 调整 TX/RX 增益后，峰值高度会明显变化

---

## 六、参数说明

两个 demo 共有的常用参数：

- `--serial`
  - USRP 设备地址，例如：`serial=7MFTKFU`
- `--sample-rate`
  - 采样率，默认 `1e6`
- `--center-freq`
  - 中心频率，默认 `1e9`
- `--tone-freq`
  - 单音频率，默认 `100e3`
- `--tx-gain`
  - 发射增益
- `--rx-gain`
  - 接收增益

---

## 七、常见问题

### 1. 能识别设备，但收不到明显峰值
请检查：
- 两副天线是否都接好了
- 是否使用了 TX/RX 和 RX2
- 天线距离是否过远
- TX/RX 增益是否过低
- 中心频率和采样率是否一致

### 2. 峰值太强或波形异常
可能是距离太近或增益过高，建议：
- 先把 `TX gain` 降到 `5~10 dB`
- 把 `RX gain` 降到 `15~20 dB`
- 适当拉开天线距离

### 3. GNU Radio 脚本打不开
说明 GNU Radio 图形环境依赖未装好，可先安装：

```bash
sudo apt update
sudo apt install -y gnuradio python3-pyqt5
```

### 4. Python 报错 `No module named uhd`
说明 Python 环境里缺少 UHD 绑定，需要确认系统中的 UHD Python 模块可用。

可以先测试：

```bash
python3 -c "import uhd; print(uhd.get_version_string())"
```

---

## 八、推荐测试顺序

建议新手按下面顺序测试：

1. 先运行 `uhd_find_devices`
2. 再运行 `usrp_chain_demo.py`
3. 确认终端版能稳定看到 `100 kHz` 单音峰值
4. 最后运行 `usrp_gnuradio_antenna_demo.py` 查看图形频谱

---

## 九、文件说明

本目录和本次演示相关的主要文件：

- `usrp_chain_demo.py`：Python 终端版全链路 demo
- `usrp_gnuradio_antenna_demo.py`：GNU Radio 图形化 demo
- `README_USRP_DEMO.md`：本说明文档

---

## 十、一句话总结

如果你能做到下面两件事，就说明新人入门链路已经跑通：

1. 终端版 demo 能稳定打印 `100 kHz` 附近峰值
2. GNU Radio 图形版能在频谱窗口看到明显单音峰值
