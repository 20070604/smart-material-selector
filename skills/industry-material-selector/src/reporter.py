"""
报告生成模块 - 组装完整 JSON 输出和 Markdown 报告
"""

import json
import os
from typing import List, Dict, Optional
import pandas as pd


class ReportGenerator:
    """报告生成器"""

    def __init__(self):
        self._load_validation_prompt()

    def _load_validation_prompt(self):
        """加载验证计划 Prompt"""
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "validation_plan.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.validation_prompt = f.read()
        except FileNotFoundError:
            self.validation_prompt = ""

    def generate_json_output(self, ranked: pd.DataFrame, vetoed: List[Dict],
                             risks: List[Dict], next_steps: List[str],
                             trace: Dict, requirements: List[Dict],
                             application: str) -> Dict:
        """
        组装完整 JSON 输出

        Args:
            ranked: 排序后的候选材料
            vetoed: 被否决材料详情
            risks: 风险分析结果
            next_steps: 验证计划
            trace: 推理溯源信息
            requirements: 需求列表
            application: 应用场景

        Returns:
            完整 JSON 输出
        """
        # 1. 排序材料列表
        ranked_materials = []
        for idx, (_, row) in enumerate(ranked.head(10).iterrows()):
            material = {
                "rank": idx + 1,
                "material_id": row["material_id"],
                "grade": row["grade"],
                "category": row["category"],
                "supplier": row["supplier"],
                "key_properties": {
                    "density": float(row["density"]) if pd.notna(row["density"]) else None,
                    "tensile_strength": float(row["tensile_strength"]) if pd.notna(row["tensile_strength"]) else None,
                    "yield_strength": float(row["yield_strength"]) if pd.notna(row["yield_strength"]) else None,
                    "thermal_conductivity": float(row["thermal_conductivity"]) if pd.notna(row["thermal_conductivity"]) else None,
                    "flammability_UL94": str(row["flammability_UL94"]),
                    "cost_per_kg": float(row["estimated_cost_per_kg"]) if pd.notna(row["estimated_cost_per_kg"]) else None,
                },
                "process": row["process"],
                "supplier_location": row["supplier_location"],
                "lead_time_weeks": float(row["lead_time_weeks"]) if pd.notna(row["lead_time_weeks"]) else None,
                "topsis_score": float(row["topsis_score"]) if "topsis_score" in row else 0.0,
                "source": {
                    "tds": str(row["source_TDS"]),
                    "page": str(row["page"]),
                    "table": str(row["table_number"])
                }
            }
            ranked_materials.append(material)

        # 2. 证据表
        evidence_table = []
        for _, row in ranked.head(5).iterrows():
            entry = {
                "grade": row["grade"],
                "comparison": []
            }
            for req in requirements:
                prop = req.get("property", "")
                if prop in ["density", "tensile_strength", "yield_strength", "thermal_conductivity"]:
                    actual = float(row[prop]) if pd.notna(row[prop]) else None
                    target_min = req.get("min")
                    target_max = req.get("max")
                    status = "满足" if (
                        (target_min is None or actual >= target_min) and
                        (target_max is None or actual <= target_max)
                    ) else "不满足"
                    entry["comparison"].append({
                        "property": prop,
                        "target_min": target_min,
                        "target_max": target_max,
                        "actual_value": actual,
                        "unit": req.get("unit", ""),
                        "status": status,
                        "source": {
                            "tds": str(row.get("source_TDS", "")),
                            "page": str(row.get("page", "")),
                            "table": str(row.get("table_number", ""))
                        }
                    })
            evidence_table.append(entry)

        # 3. 雷达图数据
        radar_data = self._build_radar_data(ranked, requirements)

        # 4. 风险分析
        risk_analysis = []
        for r in risks:
            all_risks = r.get("process_risks", []) + r.get("supply_risks", []) + r.get("data_quality_risks", [])
            risk_analysis.append({
                "material_id": r["material_id"],
                "grade": r["grade"],
                "overall_risk_level": r["overall_risk_level"],
                "process_risks": r["process_risks"],
                "supply_risks": r["supply_risks"],
                "data_quality_risks": r["data_quality_risks"]
            })

        # 5. 否决标准详情
        veto_details = []
        for v in vetoed:
            veto_details.append({
                "material_id": v.get("material_id", ""),
                "grade": v.get("grade", ""),
                "requirement": v.get("requirement", ""),
                "actual_value": v.get("actual_value", ""),
                "veto_reason": v.get("veto_reason", ""),
                "status": v.get("status", "否决")
            })

        return {
            "application": application,
            "summary": {
                "total_candidates": len(ranked_materials),
                "vetoed_count": len(veto_details),
                "top_recommendation": ranked_materials[0]["grade"] if ranked_materials else "无",
                "recommendation_confidence": "高" if ranked_materials and ranked_materials[0]["topsis_score"] > 0.7 else "中"
            },
            "ranked_materials": ranked_materials,
            "evidence_table": evidence_table,
            "veto_details": veto_details,
            "risk_analysis": risk_analysis,
            "radar_chart_data": radar_data,
            "next_steps": next_steps,
            "trace": trace
        }

    def _build_radar_data(self, materials: pd.DataFrame, requirements: List[Dict]) -> List[Dict]:
        """构建雷达图数据"""
        radar_props = ["density", "tensile_strength", "thermal_conductivity", "estimated_cost_per_kg"]
        radar_data = []

        # 目标值
        target = {"grade": "目标值", "values": {}}
        for req in requirements:
            prop = req.get("property", "")
            if prop in radar_props:
                if req.get("max") is not None:
                    target["values"][prop] = req["max"]
                elif req.get("min") is not None:
                    target["values"][prop] = req["min"]
        if target["values"]:
            radar_data.append(target)

        # Top 材料
        for _, row in materials.head(5).iterrows():
            entry = {
                "grade": row["grade"],
                "values": {}
            }
            for prop in radar_props:
                if prop in row and pd.notna(row[prop]):
                    entry["values"][prop] = float(row[prop])
            radar_data.append(entry)

        return radar_data

    def generate_markdown_report(self, json_output: Dict) -> str:
        """
        生成人类可读的 Markdown 报告

        Args:
            json_output: 完整 JSON 输出

        Returns:
            Markdown 格式报告
        """
        lines = []
        lines.append("# 产业原材料智能选型报告")
        lines.append("")
        lines.append(f"## 应用场景")
        lines.append(f"{json_output.get('application', '未指定')}")
        lines.append("")

        # 摘要
        summary = json_output.get("summary", {})
        lines.append("## 选型摘要")
        lines.append(f"- **候选材料数**: {summary.get('total_candidates', 0)}")
        lines.append(f"- **否决材料数**: {summary.get('vetoed_count', 0)}")
        lines.append(f"- **首选推荐**: {summary.get('top_recommendation', '无')}")
        lines.append(f"- **推荐置信度**: {summary.get('recommendation_confidence', '中')}")
        lines.append("")

        # 候选材料排序表
        ranked = json_output.get("ranked_materials", [])
        if ranked:
            lines.append("## 候选材料排序表")
            lines.append("")
            lines.append("| 排名 | 牌号 | 类别 | 供应商 | 密度(g/cm³) | 拉伸强度(MPa) | 导热(W/mK) | 阻燃 | 成本($/kg) | TOPSIS得分 |")
            lines.append("|------|------|------|--------|-------------|---------------|------------|------|------------|------------|")
            for m in ranked:
                props = m["key_properties"]
                lines.append(
                    f"| {m['rank']} | {m['grade']} | {m['category']} | {m['supplier']} | "
                    f"{props['density'] or '-'} | {props['tensile_strength'] or '-'} | "
                    f"{props['thermal_conductivity'] or '-'} | {props['flammability_UL94']} | "
                    f"{props['cost_per_kg'] or '-'} | {m['topsis_score']:.4f} |"
                )
            lines.append("")

        # 否决标准详情
        vetoed = json_output.get("veto_details", [])
        if vetoed:
            lines.append("## 否决标准详情")
            lines.append("")
            lines.append("| 材料牌号 | 否决项 | 要求 | 实际值 | 原因 | 状态 |")
            lines.append("|----------|--------|------|--------|------|------|")
            for v in vetoed:
                lines.append(f"| {v['grade']} | {v['requirement']} | {v['requirement']} | {v['actual_value']} | {v['veto_reason']} | {v['status']} |")
            lines.append("")

        # 风险分析
        risks = json_output.get("risk_analysis", [])
        if risks:
            lines.append("## 适配风险分析")
            lines.append("")
            for r in risks:
                lines.append(f"### {r['grade']}（风险等级: {r['overall_risk_level']}）")
                if r["process_risks"]:
                    lines.append("- **工艺风险**:")
                    for pr in r["process_risks"]:
                        lines.append(f"  - [{pr['level']}] {pr['risk']}")
                        lines.append(f"    - 建议: {pr['suggestion']}")
                if r["supply_risks"]:
                    lines.append("- **供应链风险**:")
                    for sr in r["supply_risks"]:
                        lines.append(f"  - [{sr['level']}] {sr['risk']}")
                        lines.append(f"    - 建议: {sr['suggestion']}")
                if r["data_quality_risks"]:
                    lines.append("- **数据质量风险**:")
                    for dq in r["data_quality_risks"]:
                        lines.append(f"  - [{dq['level']}] {dq['risk']}")
                        lines.append(f"    - 建议: {dq['suggestion']}")
                lines.append("")

        # 证据表
        evidence = json_output.get("evidence_table", [])
        if evidence:
            lines.append("## 证据表（关键属性 vs 目标值）")
            lines.append("")
            for e in evidence:
                lines.append(f"### {e['grade']}")
                lines.append("| 属性 | 目标下限 | 目标上限 | 实测值 | 单位 | 状态 | 来源 |")
                lines.append("|------|----------|----------|--------|------|------|------|")
                for c in e["comparison"]:
                    src = c.get("source", {})
                    src_str = f"{src.get('tds', '')} P{src.get('page', '')} {src.get('table', '')}"
                    lines.append(
                        f"| {c['property']} | {c['target_min'] or '-'} | {c['target_max'] or '-'} | "
                        f"{c['actual_value'] or '-'} | {c['unit']} | {c['status']} | {src_str} |"
                    )
                lines.append("")

        # 下一步验证计划
        next_steps = json_output.get("next_steps", [])
        if next_steps:
            lines.append("## 下一步验证计划")
            lines.append("")
            for step in next_steps:
                lines.append(f"- [ ] {step}")
            lines.append("")

        # 推理溯源
        trace = json_output.get("trace", {})
        lines.append("## 推理溯源")
        lines.append(f"- **检索方式**: {trace.get('retrieval_method', '混合检索')}")
        lines.append(f"- **TDS 条目数**: {trace.get('tds_entries', 0)}")
        lines.append(f"- **排序算法**: TOPSIS 多属性决策")
        lines.append("")

        return "\n".join(lines)

    def generate_validation_plan(self, application: str, top_materials: List[Dict],
                                 requirements: List[Dict]) -> List[str]:
        """
        生成验证计划（基于规则 + LLM）

        Args:
            application: 应用场景
            top_materials: Top 推荐材料
            requirements: 需求列表

        Returns:
            验证计划清单
        """
        steps = []

        # 基于规则生成通用验证项
        steps.append("对推荐材料进行实验室小批量性能测试，验证关键性能指标是否达标")
        steps.append("向供应商索取正式 TDS 文档和认证证书（如 UL 黄卡、RoHS 报告）")
        steps.append("评估材料在不同的加工工艺条件下的性能表现")

        # 按材料类别添加针对性验证项
        for m in top_materials[:2]:
            category = m.get("key_properties", {}).get("category", m.get("category", ""))
            grade = m.get("grade", "")

            if "塑料" in category or "工程塑料" in category:
                steps.append(f"对 {grade} 进行注塑成型试模，评估收缩率和尺寸稳定性")
                steps.append(f"测试 {grade} 在长期热老化后的性能衰减")
            elif "铝合金" in category or "镁合金" in category or "金属" in category:
                steps.append(f"对 {grade} 进行盐雾腐蚀测试，评估耐候性")
                steps.append(f"评估 {grade} 的焊接工艺参数和接头性能")
            elif "复材" in category or "碳纤维" in category:
                steps.append(f"对 {grade} 进行无损检测（超声 C 扫描），确认内部质量")
                steps.append(f"评估 {grade} 在不同环境条件下的吸湿性和性能变化")

        # 应用场景相关验证
        if "电池" in application:
            steps.append("进行电池包相关的安全测试（热失控、短路、过充）")
            steps.append("评估材料在电解液环境下的化学稳定性")
        if "散热" in application or "导热" in str(requirements):
            steps.append("制作导热测试样件，使用热阻测试仪验证实际导热性能")

        return steps