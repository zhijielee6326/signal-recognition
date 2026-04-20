# 模型类别问题说明与解决方案

## 问题发现

测试时发现所有信号都被识别为"多音干扰"，准确率0%。

## 根本原因

**类别定义不匹配！**

### 我们原来以为的类别：
```
0: 无干扰
1: 单音干扰
2: 多音干扰
3: 扫频干扰
4: 脉冲干扰
5: 宽带噪声
```

### 模型实际训练的类别：
```
0: LFM  - Linear Frequency Modulation (线性调频/扫频干扰)
1: MTJ  - Multi-Tone Jamming (多音干扰)
2: NAM  - Narrowband AM (窄带调幅)
3: NFM  - Narrowband FM (窄带调频)
4: STJ  - Single-Tone Jamming (单音干扰)
5: SIN  - Sinusoidal (正弦波)
```

## 解决方案

### 1. 更新了类别定义

修改了 `cnn_interference_detector.py` 中的类别映射：
```python
self.interference_types = [
    "扫频干扰(LFM)",    # 0
    "多音干扰(MTJ)",    # 1
    "窄带AM(NAM)",      # 2
    "窄带FM(NFM)",      # 3
    "单音干扰(STJ)",    # 4
    "正弦波(SIN)"       # 5
]
```

### 2. 创建了新的测试脚本

`usrp_model_test.py` - 专门测试模型支持的干扰类型：
- LFM (扫频干扰)
- STJ (单音干扰)
- MTJ (多音干扰)
- SIN (正弦波)

**注意**: 模型不支持以下类型：
- ❌ 无干扰（模型没有这个类别）
- ❌ 脉冲干扰（模型没有这个类别）
- ❌ 宽带噪声（模型没有这个类别）

## 使用新的测试脚本

### 完整测试（推荐）
```bash
cd ~/毕设/gnuradio
source ~/毕设/venv/bin/activate

python3 usrp_model_test.py \
    --serial "serial=7MFTKFU" \
    --model ../CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth \
    --tests 10
```

### 测试单一类型
```bash
# 测试扫频干扰
python3 usrp_model_test.py --type lfm --tests 20

# 测试单音干扰
python3 usrp_model_test.py --type stj --tests 20

# 测试多音干扰
python3 usrp_model_test.py --type mtj --tests 20

# 测试正弦波
python3 usrp_model_test.py --type sin --tests 20
```

## 预期结果

现在测试应该能正确识别干扰类型：

```
测试 [LFM] 干扰...
  [1/10] ✓ 期望: 扫频干扰(LFM) | 检测: 扫频干扰(LFM) (置信度: 0.95)
  [2/10] ✓ 期望: 扫频干扰(LFM) | 检测: 扫频干扰(LFM) (置信度: 0.92)
  ...

总体准确率: 85.0% (34/40)
```

## 类别详细说明

### LFM (Linear Frequency Modulation)
- **中文**: 线性调频 / 扫频干扰
- **特征**: 频率随时间线性变化
- **生成**: `generate_lfm(f0=100kHz, f1=900kHz)`

### STJ (Single-Tone Jamming)
- **中文**: 单音干扰
- **特征**: 单一频率的连续波
- **生成**: `generate_stj(freq=500kHz)`

### MTJ (Multi-Tone Jamming)
- **中文**: 多音干扰
- **特征**: 多个频率的叠加
- **生成**: `generate_mtj(freqs=[300k, 500k, 700k])`

### SIN (Sinusoidal)
- **中文**: 正弦波
- **特征**: 纯正弦波信号
- **生成**: `generate_sin(freq=400kHz)`

### NAM (Narrowband AM)
- **中文**: 窄带调幅
- **特征**: 窄带幅度调制
- **注意**: 当前测试脚本未实现

### NFM (Narrowband FM)
- **中文**: 窄带调频
- **特征**: 窄带频率调制
- **注意**: 当前测试脚本未实现

## 重要提示

1. **旧测试脚本**: `usrp_loopback_test.py` 已更新类别定义，但仍包含模型不支持的类型
2. **新测试脚本**: `usrp_model_test.py` 只测试模型支持的类型，推荐使用
3. **准确率**: 天线测试的准确率可能在70-85%之间（受环境影响）
4. **信号质量**: 确保天线距离合适（10-50cm），避免过载或信号太弱

## 下一步

如果需要测试其他干扰类型（脉冲、宽带噪声等），需要：
1. 重新训练模型，包含这些类别
2. 或使用规则检测方法（不使用深度学习模型）

---

**现在可以开始正确的测试了！**

```bash
python3 usrp_model_test.py --tests 10
```
