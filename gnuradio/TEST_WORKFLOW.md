# USRP自发自收测试完整流程

## 📋 测试准备清单

### 1. 环境检查
```bash
cd ~/毕设/gnuradio
source ~/毕设/venv/bin/activate
python3 check_environment.py
```

**必须全部通过**：
- ✓ 虚拟环境已激活
- ✓ PyTorch已安装
- ✓ UHD Python绑定可用
- ✓ USRP设备已连接
- ✓ 用户在usrp组中
- ✓ CCNN模型文件存在

### 2. 硬件连接
```
USRP B210
├── TX/RX ──[同轴线 + 30dB衰减器]──┐
└── RX2 ────────────────────────────┘
```

### 3. 软件测试（可选）
先用模拟数据测试检测器：
```bash
python3 test_detector_simple.py
```

## 🚀 开始测试

### 方案A：完整测试（推荐）
测试所有5种干扰类型，每种10次：
```bash
./run_loopback_test.sh all 10
```

预计时间：约5-10分钟

### 方案B：单一干扰测试
```bash
# 测试单音干扰（20次）
./run_loopback_test.sh tone 20

# 测试扫频干扰（20次）
./run_loopback_test.sh chirp 20

# 测试脉冲干扰（20次）
./run_loopback_test.sh pulse 20

# 测试宽带噪声（20次）
./run_loopback_test.sh noise 20

# 测试无干扰基线（20次）
./run_loopback_test.sh none 20
```

### 方案C：自定义参数
```bash
python3 usrp_loopback_test.py \
    --serial "serial=7MFTKFU" \
    --model ../CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth \
    --type all \
    --tests 20 \
    --classes 6
```

## 📊 结果分析

### 预期输出
```
======================================================================
测试结果总结
======================================================================

NONE:
  测试次数: 10
  正确次数: 9
  准确率: 90.0%

TONE:
  测试次数: 10
  正确次数: 9
  准确率: 90.0%

CHIRP:
  测试次数: 10
  正确次数: 8
  准确率: 80.0%

PULSE:
  测试次数: 10
  正确次数: 9
  准确率: 90.0%

NOISE:
  测试次数: 10
  正确次数: 9
  准确率: 90.0%

总体准确率: 88.0% (44/50)
======================================================================
```

### 性能指标
- **优秀**: 总体准确率 > 85%
- **良好**: 总体准确率 70-85%
- **需改进**: 总体准确率 < 70%

## 🔧 故障排查

### 问题1: 找不到USRP设备
```bash
# 检查设备
uhd_find_devices

# 检查权限
groups | grep usrp

# 如果不在usrp组
sudo usermod -a -G usrp $USER
# 重新登录
```

### 问题2: 接收不到数据
- 检查物理连接是否牢固
- 确认使用了30dB衰减器
- 尝试调整增益：
  ```bash
  # 在usrp_loopback_test.py中修改
  TX_GAIN = 15  # 降低发送功率
  RX_GAIN = 40  # 提高接收灵敏度
  ```

### 问题3: 检测准确率低
1. 检查信号质量：
   ```bash
   # 使用signal_receiver.py查看实时信号
   python3 signal_receiver.py --serial "serial=7MFTKFU"
   ```

2. 调整参数：
   - 增加测试次数（--tests 50）
   - 调整采样率
   - 修改干扰信号参数

3. 检查模型：
   ```bash
   # 确认模型文件完整
   ls -lh ../CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth
   ```

### 问题4: 模型加载失败
```bash
# 检查PyTorch
python3 -c "import torch; print(torch.__version__)"

# 检查模型路径
python3 test_detector_simple.py
```

## 📝 实验记录

### 建议记录内容
1. **测试配置**
   - USRP序列号
   - 采样率、中心频率
   - TX/RX增益
   - 衰减器参数

2. **测试结果**
   - 每种干扰的准确率
   - 总体准确率
   - 误检类型分析

3. **环境条件**
   - 测试时间、地点
   - 环境干扰情况
   - 硬件连接方式

4. **问题与改进**
   - 遇到的问题
   - 解决方法
   - 改进建议

## 🎯 下一步工作

### 1. 参数优化
- 调整信号功率
- 优化采样率
- 测试不同频段

### 2. 扩展测试
- 混合干扰测试
- 不同SNR条件
- 长时间稳定性测试

### 3. 真实环境验证
- 使用两台USRP
- 天线对天线测试
- 真实干扰场景

### 4. 数据分析
- 生成混淆矩阵
- 绘制ROC曲线
- 分析误检原因

## 📚 相关文档

- `QUICKSTART.md` - 快速开始指南
- `README_LOOPBACK.md` - 详细使用文档
- `../CCNN/README_SETUP.md` - 环境配置说明
- `../CCNN/PROJECT_STRUCTURE.md` - 项目结构说明

## 💡 提示

1. **首次测试**：建议先运行少量测试（5-10次）验证系统正常
2. **数据保存**：可以修改代码保存测试数据用于离线分析
3. **实时监控**：使用signal_receiver.py可以实时查看信号和检测结果
4. **批量测试**：可以编写脚本进行批量测试和自动分析

## ⚠️ 注意事项

1. **必须使用衰减器**：直接连接可能损坏设备
2. **检查连接**：确保同轴线连接牢固
3. **环境干扰**：尽量在电磁环境干净的地方测试
4. **设备保护**：测试完成后断开连接

---

**准备好了吗？开始测试！**

```bash
cd ~/毕设/gnuradio
source ~/毕设/venv/bin/activate
./run_loopback_test.sh all 10
```
