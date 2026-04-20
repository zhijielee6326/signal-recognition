# USRP自发自收测试 - 快速开始

## 第一步：环境检查

```bash
cd ~/毕设/gnuradio
source ~/毕设/venv/bin/activate
python3 check_environment.py
```

如果所有检查都通过，继续下一步。

## 第二步：硬件连接

**重要**: 使用50Ω同轴电缆 + 30dB衰减器连接：
```
USRP TX/RX ──[同轴线+30dB衰减器]──> USRP RX2
```

## 第三步：运行测试

### 方法1：使用快速脚本（推荐）
```bash
./run_loopback_test.sh all 10
```

### 方法2：直接运行Python脚本
```bash
python3 usrp_loopback_test.py \
    --serial "serial=7MFTKFU" \
    --model ../CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth \
    --tests 10
```

### 方法3：测试单一干扰类型
```bash
# 测试单音干扰
./run_loopback_test.sh tone 20

# 测试扫频干扰
./run_loopback_test.sh chirp 20

# 测试脉冲干扰
./run_loopback_test.sh pulse 20
```

## 预期输出

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

总体准确率: 88.5% (44/50)
```

## 常见问题

**Q: 提示"No UHD Devices Found"**
```bash
sudo usermod -a -G usrp $USER
# 然后重新登录
```

**Q: 接收不到数据**
- 检查物理连接
- 确认使用了衰减器
- 调整增益参数

**Q: 准确率很低**
- 检查信号质量
- 调整TX/RX增益
- 确认模型文件正确

## 文件说明

- `usrp_loopback_test.py` - 主测试脚本
- `run_loopback_test.sh` - 快速启动脚本
- `check_environment.py` - 环境检查工具
- `README_LOOPBACK.md` - 详细使用文档

## 下一步

测试完成后，可以：
1. 调整参数进行更多测试
2. 分析检测结果
3. 生成实验报告
4. 尝试真实环境测试

详细文档请查看 `README_LOOPBACK.md`
