# 材智引擎 · 产业原材料智能选型系统

## 概述
面向材料工程师与采购决策者的 AI Skill，将自然语言需求转化为数据驱动的材料推荐、对比证据、风险提示与验证规划，加速工业选材从"经验导向"转向"智能决策"。

## 功能特性
- **需求规范化**：自然语言 → 结构化 JSON 需求文档
- **混合检索**：关键词语义匹配 + 数值指标过滤
- **硬性否决检查**：自动检查 UL94、RoHS、密度、强度等硬性条件
- **TOPSIS 多属性排序**：基于逼近理想解排序法的综合评分
- **风险分析**：工艺风险、供应链风险、数据质量风险评估
- **报告生成**：Markdown 可读报告 + 结构化 JSON 输出
- **验证计划**：自动生成下一步验证建议

## 快速开始

### 1. 安装依赖
```bash
cd industry_material_selector
pip install -r requirements.txt
```

### 2. 运行 Demo
```bash
# 方式一：命令行
python -c "from src.pipeline import MaterialSelectionPipeline; p = MaterialSelectionPipeline(); result = p.run('电动汽车电池包壳体，密度<2.0 g/cm³，拉伸强度>300 MPa，导热系数>100 W/mK，UL94 V-0，成本<$20/kg，RoHS合规，国内采购'); print(result)"

# 方式二：Jupyter Notebook
jupyter notebook demo.ipynb
```

### 3. 使用示例
```python
from src.pipeline import MaterialSelectionPipeline

pipeline = MaterialSelectionPipeline()

# 运行完整 Pipeline
result = pipeline.run("我需要一种用于汽车发动机罩盖的材料，密度<1.5 g/cm³，拉伸强度>150 MPa，UL94 V-0，成本<$10/kg")

# 生成 Markdown 报告
report = pipeline.run_and_report("同上")
print(report)
```

## 项目结构
```
industry_material_selector/
├── skill.yaml                 # Skill 元数据
├── README.md                  # 本文件
├── requirements.txt           # 依赖清单
├── src/
│   ├── __init__.py
│   ├── normalizer.py          # 需求规范化器
│   ├── retriever.py           # 混合检索模块
│   ├── veto.py                # 否决检查模块
│   ├── ranking.py             # TOPSIS 排序引擎
│   ├── risk.py                # 风险分析模块
│   ├── reporter.py            # 报告生成模块
│   └── pipeline.py            # 主流程 Pipeline
├── data/
│   └── material_db.csv        # 脱敏材料数据库
├── prompts/
│   ├── requirement_extract.txt # 需求提取 Prompt
│   └── validation_plan.txt    # 验证计划 Prompt
├── examples/
│   ├── input_sample.json       # 输入示例
│   └── output_sample.json      # 输出示例
└── demo.ipynb                 # 可运行 Demo Notebook
```

## 技术栈
- Python 3.10+
- pandas, numpy (数据处理)
- openai (Qwen3.8-Max API 兼容接口)
- matplotlib (可视化)
- 算法：TOPSIS 多属性决策

## 数据说明
- 材料数据库包含 16 条典型材料卡片，覆盖铝合金、镁合金、碳纤维复材、工程塑料等
- 所有数据均为脱敏合成数据，仅供演示
- 实际应用需替换为真实材料数据库

## 离线模式
无需 API Key 即可运行。系统会自动使用离线规则解析器从自然语言中提取需求结构。如需使用 LLM 增强，设置环境变量：
```bash
set LLM_API_KEY=your_api_key
set LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
```