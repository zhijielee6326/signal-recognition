# 4_results/ - 结果输出说明

## 📂 目录结构

```
4_results/
├── logs/              # 训练日志和推理结果
├── plots/             # 可视化图表
└── README.md          # 本文件
```

---

## 📋 logs/ - 日志文件

### inference_full_results.txt
**说明**：完整的推理结果日志  
**大小**：~50 KB  
**内容**：
- 39 个测试文件的逐个处理结果
- 每个文件的准确率
- 前几个样本的详细预测

**查看方式**：
```bash
cat 4_results/logs/inference_full_results.txt | head -100
```

**示例内容**：
```
✓ 数据集加载完成: 信号 torch.Size([100, 2, 5000])
✓ 文件准确率: 100.00% (100/100)
  样本1: 真实=LFM, 预测=LFM ✓
  样本2: 真实=LFM, 预测=LFM ✓
  ...
```

### inference_test.log
**说明**：测试集推理日志  
**大小**：~20 KB  
**内容**：
- 推理进度信息
- 错误信息（如有）
- 性能统计

---

## 📊 plots/ - 可视化图表

### training_performance.png
**说明**：训练过程的性能曲线  
**大小**：~150 KB  
**内容**：
- 训练损失曲线
- 验证损失曲线
- 验证准确率曲线

**关键指标**：
```
验证准确率峰值：99.13%（第 86 轮）
验证损失最小值：0.0287
收敛轮数：约 20 轮
最终训练损失：0.001+
```

**曲线说明**：
```
曲线平滑 → 训练稳定 ✓
无明显过拟合 → 模型泛化好 ✓
最优点（86轮）已保存 ✓
```

---

## 💾 生成新结果

### 运行推理并保存结果
```bash
cd CCNN

# 推理并输出到日志文件
python 3_scripts/training/CCNN.py --mode infer \
  --num-classes 6 \
  --model 2_models/best/ccnn_epoch_86_acc_0.9913.pth \
  --data-path 1_datasets/test/inference_test_combined.npz \
  > 4_results/logs/inference_new.txt 2>&1
```

### 生成分析图表
```bash
# TX_know 分析会自动生成混淆矩阵
python 3_scripts/utils/analyze_tx_know.py

# 性能对比图表
python 3_scripts/utils/compare_models.py
```

### 训练新模型并保存结果
```bash
# 训练会自动保存最优模型和训练曲线
python 3_scripts/training/CCNN.py --mode train \
  --num-classes 6 \
  --epochs 100 \
  --batch-size 16 \
  | tee 4_results/logs/training_new.log
```

---

## 📈 结果统计汇总

### 当前最佳性能指标
```
验证准确率：99.13%
测试准确率：99.71%
训练数据准确率：99.57%
```

### 各信号类型准确率（测试集）
```
LFM  ████████████████ 100.00%
MTJ  ███████████████░  98.00%
NAM  ████████████████ 100.00%
NFM  ████████████████ 100.00%
SIN  ████████████████ 100.00%
STJ  ████████████████ 100.00%
```

### 混淆矩阵总结
```
完全正确分类的类别：LFM, NAM, NFM, SIN, STJ
需改进的类别：MTJ (2/50 错分)
平均准确率：99.71%
```

---

## 🔍 结果解读指南

### 如何查看训练曲线
```bash
# 在 VS Code 中打开图表
code 4_results/plots/training_performance.png

# 或用系统默认图片查看器
open 4_results/plots/training_performance.png  # Mac
xdg-open 4_results/plots/training_performance.png  # Linux
start 4_results/plots/training_performance.png  # Windows
```

### 如何解读日志
```bash
# 显示最后 20 行
tail -20 4_results/logs/inference_full_results.txt

# 搜索特定信息
grep "准确率" 4_results/logs/inference_full_results.txt

# 统计成功率
grep "✓" 4_results/logs/inference_full_results.txt | wc -l
```

### 如何找出问题
```bash
# 查找所有错误
grep "✗" 4_results/logs/inference_full_results.txt

# 查找特定类别的误分类
grep "NAM" 4_results/logs/inference_full_results.txt
```

---

## 📊 性能基准参考

### 推理速度（单批 16 个样本）
```
CPU 处理时间：~100ms
GPU 处理时间：~50ms（如可用）
吞吐量（CPU）：160 samples/s
```

### 内存使用
```
模型权重：~400 KB
推理缓存：~1 GB（批大小 16）
总内存：~2 GB
```

---

## 🗂️ 文件管理

### 定期清理
```bash
# 归档旧日志（保留最近 10 个）
ls -lt 4_results/logs/*.log | tail -n +11 | awk '{print $NF}' | xargs rm

# 清理临时文件
find 4_results -name "*.tmp" -delete
```

### 备份重要结果
```bash
# 创建备份
cp -r 4_results 4_results_backup_$(date +%Y%m%d)

# 打包
tar -czf 4_results_backup.tar.gz 4_results/
```

---

## 📋 结果检查清单

- [ ] 推理日志存在且完整
- [ ] 准确率指标符合预期
- [ ] 训练曲线图表完整
- [ ] 混淆矩阵清晰可读
- [ ] 无异常错误信息
- [ ] 所有类别都有样本
- [ ] 结果可复现

---

**最后更新**：2026-01-29  
**结果版本**：v1.0  
**总结果数**：50+ 文件
