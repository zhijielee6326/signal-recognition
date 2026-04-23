# MATLAB vs Python 训练数据生成对比

## 1. 概述

| 对比项 | MATLAB | Python |
|--------|--------|--------|
| 代码位置 | `CCNN/matlab_data_generate/` | `gnuradio/usrp_model_test_v4.py` |
| 代码量 | 1457行 (16个.m文件) | 465行 (1个.py文件) |
| 生成数据量 | 3600个 .mat 文件 (127MB) | 按需在线生成 (0磁盘占用) |
| 干扰类型 | 6类 (LFM/MTJ/NAM/NFM/STJ/SIN) | 6类 + clean (7类) |
| 调制方式 | BPSK/QPSK/8PSK 随机 | QPSK 固定 (与传输系统一致) |
| JSR范围 | 固定 (6dB/8dB/10dB) | 可配置 (-2~16dB 宽范围) |
| 运行环境 | MATLAB + USRP Hardware Support | Python + UHD (开源) |

## 2. MATLAB 方案

### 文件结构
```
matlab_data_generate/
├── TX_STJ.m          # 单音干扰生成
├── TX_MTJ.m          # 多音干扰生成
├── TX_LFM.m          # 线性扫频干扰
├── TX_NAM.m          # 窄带AM干扰
├── TX_NFM.m          # 窄带FM干扰
├── TX_SIN.m          # 正弦波干扰
├── PSK_MOD.m         # PSK调制 (BPSK/QPSK/8PSK)
├── study.m           # 主脚本: 批量生成训练数据
├── LD_*.m            # 载荷检测相关函数
├── rs_generate_wave.m # Rohde&Schwarz 仪器控制
├── rs_visualize.m    # 可视化
├── data_process.py   # 数据后处理 (Python)
└── data/             # 3600个.mat文件
```

### 工作流程
1. `study.m` 遍历 参数组合 (调制方式 x 干扰类型 x 功率)
2. 调用 `PSK_MOD.m` 生成基带 PSK 信号
3. 调用 `TX_xxx.m` 生成对应类型干扰
4. 叠加后保存为 `.mat` 文件
5. `data_process.py` 将 `.mat` 转换为 `.npz` 供 PyTorch 训练

### 关键代码示例 (TX_STJ.m)
```matlab
function stj_sig = TX_STJ(rs, power, fs, T, randd)
    N = fs * T;
    t = 0:1/Fs:(N-1)*(1/Fs);
    up = 0.01 * Rs * 1.2;
    f0 = -0.6*Rs + up*randd;       % 干扰频率
    power = 10.^(power/10);
    y2 = sqrt(power)*exp(1i*2*pi*f0*t);
    m2 = mean(abs(y2).^2);
    c = sqrt(power/m2);
    stj_sig = c*y2;
end
```

## 3. Python 方案

### 设计理念
将 MATLAB 的 16 个文件整合为 1 个 Python 文件，**逐行精确复现** MATLAB 逻辑，
同时支持：
- 按需在线生成 (无需预存大量 .mat 文件)
- 可配置 JSR 范围 (支持 JSR sweep 测试)
- 直接输出 numpy 数组 (无需 .mat → .npz 转换)

### 关键代码示例 (gen_stj)
```python
def gen_stj(rs=RS, power_dbw=0, fs=FS, t_dur=T, randd=0.5):
    """精确复现 MATLAB TX_STJ.m"""
    N = int(fs * t_dur)
    t = np.arange(N) / fs
    up = 0.01 * rs * 1.2
    f0 = -0.6 * rs + up * randd
    power = 10 ** (power_dbw / 10)
    y2 = np.sqrt(power) * np.exp(1j * 2 * np.pi * f0 * t)
    m2 = np.mean(np.abs(y2) ** 2)
    c = np.sqrt(power / m2)
    return c * y2
```

### GEN_MAP 统一接口
```python
GEN_MAP = {
    'lfm': gen_lfm,
    'mtj': gen_mtj,
    'nam': gen_nam,
    'nfm': gen_nfm,
    'stj': gen_stj,
    'sin': gen_sin,
}
```
被以下模块直接调用：
- `SimulatedChannel._inject_jammer()` — 仿真信道干扰注入
- `generate_training_data.py` — 批量生成训练数据
- `jsr_sweep_test.py` — JSR 精度扫描测试

## 4. 核心差异对比

### 4.1 数据生成流程

| 步骤 | MATLAB | Python |
|------|--------|--------|
| 1. 生成基带信号 | PSK_MOD.m (单独文件) | gen_psk() (同文件内函数) |
| 2. 生成干扰 | TX_xxx.m (6个文件) | gen_xxx() (6个函数) |
| 3. 功率归一化 | 每个TX_xxx.m内单独实现 | _jammer_power() 统一 |
| 4. 滤波器设计 | rcosdesign() (MATLAB内置) | numpy手动实现 rcosdesign |
| 5. 叠加 | study.m 循环 | GEN_MAP 字典映射 |
| 6. 存储 | .mat文件 | .npz 或在线生成 |

### 4.2 精度一致性验证

通过对比 MATLAB 和 Python 生成的同参数信号，确认：
- PSK 调制：升余弦脉冲成型参数一致 (rolloff=0.25, span=10)
- 干扰频率范围：与 MATLAB TX_xxx.m 中公式完全对应
- 功率归一化：`10^(power/10)` 公式一致
- 采样率/码元速率：fs=2MHz, Rs=500kHz (sps=4)

**训练结果验证**：用 Python 生成的数据训练 CCNN 模型，在 MATLAB 生成的测试集上准确率 >99%，证实了两种生成方式的等价性。

### 4.3 扩展能力

| 特性 | MATLAB | Python |
|------|--------|--------|
| JSR 可配置 | 否 (固定6/8/10dB) | 是 (-2~16dB任意) |
| 新增干扰类型 | 需新增.m文件 | 添加函数+注册GEN_MAP |
| 在线生成 | 否 (需预生成文件) | 是 (实时生成) |
| 与系统集成 | 否 (离线工具) | 是 (SimulatedChannel直接调用) |
| clean信号支持 | 否 | 是 (7类含"无干扰") |

## 5. 演进路线

```
阶段1 (MATLAB)
  └── 离线生成 .mat 文件 → 转换 .npz → 训练6类模型 (99.13%)

阶段2 (Python v4)
  └── 在线生成 + USRP发射 → 扩展7类 → 训练7类模型 (99.91%)

阶段3 (集成系统)
  └── gen_xxx() → SimulatedChannel → VideoTransmissionSystem
      └── 实时可视化 + 自适应传输
```

## 6. 保留的MATLAB文件说明

`CCNN/matlab_data_generate/` 目录保留用于：
- 论文中对比说明
- 方法论溯源
- 数据生成逻辑参考
