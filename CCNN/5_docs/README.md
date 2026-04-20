# 5_docs/ - 文档说明

## 📂 目录结构

```
5_docs/
├── reports/           # 实验报告（重要）
│   ├── EXPERIMENT_REPORT.md
│   └── EXPERIMENT_REPORT.docx
├── guides/            # 使用指南
│   ├── QUICKSTART.md
│   ├── README_USAGE.md
│   └── COMMANDS_CHEATSHEET.md
├── checklists/        # 检查清单和记录
│   ├── SUCCESS_REPORT.md
│   ├── BUGFIX_REPORT.md
│   ├── OPTIMIZATION_SUMMARY.md
│   ├── OPTIMIZATION_COMPLETE.txt
│   ├── FINAL_SUMMARY.md
│   ├── PROJECT_SUMMARY.md
│   ├── CHANGES.md
│   └── FILES_MANIFEST.md
└── README.md          # 本文件
```

---

## 📄 reports/ - 实验报告

### EXPERIMENT_REPORT.md（必读）
**格式**：Markdown  
**大小**：~50 KB  

**内容包括**：
- ✓ 实验背景与目标
- ✓ 研究方法（数据处理、模型架构、训练配置）
- ✓ 详细实验结果（训练、验证、测试、TX_know）
- ✓ 深度分析（模型对比、问题诊断、原因分析）
- ✓ 结论与建议
- ✓ 附录（命令、环境、参考）

**关键内容**：
```
✓ 最佳验证准确率：99.13%
✓ 独立测试准确率：99.71%
⚠️ TX_know 准确率：40%（6类）vs 100%（5类）
✓ 发现 SIN 类导致的问题
✓ 详细的改进建议
```

**查看方式**：
```bash
# 在 VS Code 中打开
code 5_docs/reports/EXPERIMENT_REPORT.md

# 在浏览器中预览（本地）
python -m http.server  # 然后访问 localhost:8000
```

### EXPERIMENT_REPORT.docx（Word 版本）
**格式**：Microsoft Word  
**大小**：~44 KB  
**内容**：同上 Markdown 版本

**使用场景**：
- 在 Word 中编辑和打印
- 发送给不熟悉 Markdown 的人
- 添加图片和格式调整

---

## 🚀 guides/ - 使用指南

### QUICKSTART.md - 5 分钟快速开始
**用途**：新用户快速上手  
**阅读时间**：5 分钟  
**内容**：
- 环境设置
- 三个基本命令
- 常见问题

### README_USAGE.md - 详细使用说明
**用途**：全面的使用文档  
**阅读时间**：20 分钟  
**内容**：
- 安装依赖
- 数据准备
- 模型训练
- 推理使用
- 常见错误排查

### COMMANDS_CHEATSHEET.md - 命令速查表
**用途**：快速查找常用命令  
**格式**：命令列表  
**内容**：
```
# 训练
python 3_scripts/training/CCNN.py --mode train ...

# 测试
python 3_scripts/training/CCNN.py --mode test ...

# 推理（6类）
python 3_scripts/training/CCNN.py --mode infer \
  --num-classes 6 \
  --model 2_models/best/ccnn_epoch_86_acc_0.9913.pth ...

# 推理（5类，TX_know）
python 3_scripts/training/CCNN.py --mode infer \
  --num-classes 5 \
  --model 2_models/legacy/TXCCNNmodel1013.pth ...
```

---

## ✅ checklists/ - 检查清单和记录

### SUCCESS_REPORT.md
**用途**：项目成功指标  
**内容**：
- ✓ 完成的目标
- ✓ 达成的性能指标
- ✓ 验证的功能

### BUGFIX_REPORT.md
**用途**：已修复问题记录  
**内容**：
- CUDA 硬编码移除
- 可视化问题修复
- 模型兼容性改进
- 数据处理优化

### OPTIMIZATION_SUMMARY.md
**用途**：项目优化总结  
**内容**：
- 数据集扩展（32→3600）
- 模型训练优化
- 代码效率提升
- 文件存储优化

### FILES_MANIFEST.md
**用途**：完整的文件清单  
**内容**：
- 所有文件的用途
- 文件大小和数量
- 版本信息

### CHANGES.md
**用途**：版本更新记录  
**内容**：
```
v1.1 (2026-01-29)
- 整理项目文件结构
- 创建详细文档
- 优化文件组织

v1.0 (2026-01-28)
- 初始版本发布
- 6类模型训练完成
```

---

## 📖 阅读路线图

### 新用户推荐阅读顺序
```
1. 本文件（5_docs/README.md）- 2 分钟
   ↓
2. QUICKSTART.md - 5 分钟
   ↓
3. README_USAGE.md - 20 分钟
   ↓
4. EXPERIMENT_REPORT.md - 30 分钟
   ↓
5. COMMANDS_CHEATSHEET.md - 按需查阅
```

### 快速问题查找
```
Q: 如何安装？
A: 见 README_USAGE.md

Q: 如何训练模型？
A: 见 COMMANDS_CHEATSHEET.md 或 README_USAGE.md

Q: 为什么 TX_know 准确率低？
A: 见 EXPERIMENT_REPORT.md 的"深层原因分析"

Q: 使用哪个模型？
A: 见 2_models/README.md 的"模型选择决策树"

Q: 如何处理我的新数据？
A: 见 1_datasets/README.md
```

---

## 🔍 快速查找

### 按主题分类

**数据相关**：
- 1_datasets/README.md
- EXPERIMENT_REPORT.md 的第 2 节

**模型相关**：
- 2_models/README.md
- EXPERIMENT_REPORT.md 的第 3 节

**脚本相关**：
- 3_scripts/README.md
- COMMANDS_CHEATSHEET.md

**结果相关**：
- 4_results/README.md
- EXPERIMENT_REPORT.md 的第 4 节

**问题诊断**：
- BUGFIX_REPORT.md
- EXPERIMENT_REPORT.md 的第 4 节

---

## 📊 关键数据速查

### 模型对比
| 指标 | 6类模型 | 5类模型 |
|------|--------|--------|
| 验证准确率 | 99.13% | - |
| 测试准确率 | 99.71% | - |
| TX_know | 40% ❌ | 100% ✓ |

### 数据集统计
```
训练集：3600 样本（6类均衡）
测试集：1200 样本（独立）
TX_know：20 样本（真实数据）
```

### 环境要求
```
Python >= 3.8
PyTorch >= 1.9
NumPy >= 1.19
Matplotlib >= 3.3
```

---

## 📝 编辑和更新指南

### 更新文档
```bash
# 编辑 Markdown 文件
vim 5_docs/reports/EXPERIMENT_REPORT.md

# 生成新的 Word 版本
python 3_scripts/utils/md_to_docx.py

# 提交更改
git add 5_docs/
git commit -m "Update documentation"
```

### 添加新文档
1. 在适当的子目录中创建文件
2. 使用 `.md` 格式
3. 添加清晰的标题和结构
4. 在本 README 中记录
5. 如需 Word 版本，运行转换脚本

### 文档规范
```markdown
# 一级标题（文件标题）

## 二级标题（主要章节）

### 三级标题（子章节）

**粗体**用于强调
`代码`用于技术术语
- 列表用于项目
> 引用用于重要信息
```

---

## 🔗 文档索引

| 文件 | 用途 | 对象 |
|------|------|------|
| QUICKSTART.md | 快速开始 | 新用户 |
| README_USAGE.md | 详细使用 | 实验人员 |
| COMMANDS_CHEATSHEET.md | 命令查询 | 所有人 |
| EXPERIMENT_REPORT.md | 研究报告 | 学术/管理 |
| PROJECT_STRUCTURE.md | 项目结构 | 开发者 |

---

## ⚠️ 重要警告

### 关于 TX_know 数据
```
⚠️ 6 类模型在 TX_know 上表现差（40%）
✓ 5 类模型在 TX_know 上表现好（100%）

请选择正确的模型！
详见：2_models/README.md
```

### 关于 SIN 类
```
⚠️ 新增 SIN 类导致其他类混淆
📋 需要进一步诊断和改进
详见：EXPERIMENT_REPORT.md 的"深层原因分析"
```

---

## 📞 问题排查

### 文档找不到？
1. 检查文件路径（应在 CCNN 目录下）
2. 使用 `find` 搜索文件
3. 查看项目结构（PROJECT_STRUCTURE.md）

### 文档内容过时？
1. 检查"最后更新"日期
2. 对比代码和文档
3. 提出更新请求

### 需要补充文档？
1. 描述需要的文档
2. 提供示例或大纲
3. 联系项目维护者

---

**最后更新**：2026-01-29  
**文档版本**：v1.0  
**总文档数**：15+ 文件  
**总内容**：50+ KB
