---
name: industry-material-selector
description: 产业原材料智能选型。将自然语言描述的材料需求（如应用场景、密度/强度/导热/成本等性能约束、合规要求、采购地域）转化为数据驱动的材料推荐、TOPSIS 排序、否决原因、风险分析与验证计划，加速工业选材从"经验导向"转向"智能决策"。输入自然语言选型需求，输出排序后的候选材料清单、对比证据表、被否决材料及原因、风险提示和下一步验证建议。无 LLM API 时自动使用离线规则解析模式。
---

# 产业原材料智能选型 Skill

面向材料工程师与采购决策者的 AI Skill，将自然语言需求转化为数据驱动的材料推荐、对比证据、风险提示与验证规划。

## 功能特性

- **需求规范化**：自然语言 → 结构化 JSON 需求文档（无 LLM API 时自动离线规则解析）
- **混合检索**：关键词语义匹配 + 数值指标过滤
- **硬性否决检查**：自动检查 UL94 阻燃、RoHS、密度、强度、成本等硬性条件
- **TOPSIS 多属性排序**：基于逼近理想解排序法的综合评分与排序解释
- **风险分析**：工艺风险、供应链风险、数据质量风险评估
- **报告生成**：Markdown 可读报告 + 结构化 JSON 输出
- **验证计划**：自动生成下一步验证建议

## 输入

自然语言描述的材料选型需求，例如：

```
电动汽车电池包壳体，密度<2.0 g/cm³，拉伸强度>300 MPa，导热系数>100 W/mK，UL94 V-0，成本<$20/kg，RoHS合规，国内采购
```

## 输出

- `application`：应用场景
- `summary`：选型摘要
- `ranked_materials`：排序后的候选材料列表
- `evidence_table`：关键属性对比证据表
- `veto_details`：被否决材料及原因
- `risk_analysis`：适配风险分析
- `radar_chart_data`：雷达图数据
- `next_steps`：下一步验证计划
- `trace`：推理溯源信息

## 六步 Pipeline

1. 需求规范化（src.normalizer）
2. 混合检索与初筛（src.retriever）
3. 硬性否决检查（src.veto）
4. TOPSIS 排序（src.ranking）
5. 风险分析（src.risk）
6. 报告生成（src.reporter）

## 快速开始

```bash
cd skills/industry-material-selector
pip install -r requirements.txt

# 命令行运行
python -c "from src.pipeline import MaterialSelectionPipeline; p = MaterialSelectionPipeline(); r = p.run('电动汽车电池包壳体，密度<2.0 g/cm³，拉伸强度>300 MPa，成本<$20/kg，RoHS合规'); print(r)"

# Web Demo
python app.py
```

## 注意

- 无 LLM API Key 时自动使用离线模拟模式，基于规则解析需求
- 数据均为脱敏合成数据，仅供演示
- 供应链信息仅作演示，实际应用需更新数据库
