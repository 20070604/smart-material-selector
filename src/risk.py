"""
风险分析模块 - 工艺风险、供应链风险、数据质量风险评估
"""

import pandas as pd
from typing import List, Dict, Tuple


# 工艺匹配规则表
PROCESS_RISK_RULES = {
    # 场景工艺关键词 -> 推荐工艺匹配
    "大批量": {"compatible": ["压铸", "注塑", "冲压"], "incompatible": ["热压罐", "真空导入", "锻造"]},
    "冲压": {"compatible": ["冲压", "挤压"], "incompatible": ["热压罐", "压铸", "注塑"]},
    "压铸": {"compatible": ["压铸"], "incompatible": ["热压罐", "冲压", "锻造"]},
    "注塑": {"compatible": ["注塑"], "incompatible": ["热压罐", "压铸", "锻造"]},
    "小批量": {"compatible": ["热压罐", "真空导入", "3D打印", "机加"], "incompatible": ["压铸", "注塑"]},
}

# 供应商标注
SINGLE_SUPPLIER_MARKERS = ["中国", "中国/德国", "中国/美国", "中国/日本"]
MULTI_SUPPLIER_MARKERS = ["中国/德国", "中国/美国", "中国/日本", "德国/中国", "美国/中国", "日本/中国"]


class RiskAnalyzer:
    """风险分析器"""

    def __init__(self):
        pass

    def analyze(self, materials: pd.DataFrame, requirements: List[Dict],
                application: str = "") -> List[Dict]:
        """
        分析候选材料的各类风险

        Args:
            materials: 候选材料 DataFrame
            requirements: 需求列表
            application: 应用场景描述

        Returns:
            风险报告列表
        """
        risks = []

        for _, row in materials.iterrows():
            material_risks = {
                "material_id": row["material_id"],
                "grade": row["grade"],
                "process_risks": [],
                "supply_risks": [],
                "data_quality_risks": [],
                "overall_risk_level": "低"
            }

            # 1. 工艺风险分析
            self._analyze_process_risk(material_risks, row, application)

            # 2. 供应链风险分析
            self._analyze_supply_risk(material_risks, row)

            # 3. 数据质量风险分析
            self._analyze_data_quality(material_risks, row)

            # 综合风险等级（仅中/高风险项计入等级，低风险项不影响）
            risk_counts = len(material_risks["process_risks"]) + \
                          len(material_risks["supply_risks"]) + \
                          sum(1 for r in material_risks["data_quality_risks"] if r["level"] in ("高", "中"))

            if risk_counts >= 3:
                material_risks["overall_risk_level"] = "高"
            elif risk_counts >= 1:
                material_risks["overall_risk_level"] = "中"

            risks.append(material_risks)

        return risks

    def _analyze_process_risk(self, material_risks: Dict, row: pd.Series, application: str):
        """分析工艺风险"""
        material_process = str(row.get("process", "")).strip()
        application_lower = application.lower()

        # 检查工艺兼容性
        for scene_key, rules in PROCESS_RISK_RULES.items():
            if scene_key in application_lower:
                if material_process:
                    # 检查是否与不兼容工艺匹配
                    for inc in rules["incompatible"]:
                        if inc in material_process:
                            material_risks["process_risks"].append({
                                "risk": f"工艺不匹配：材料推荐工艺「{material_process}」与场景隐含的「{scene_key}」工艺不兼容",
                                "level": "高",
                                "suggestion": f"建议改用适合{scene_key}的工艺，或评估{material_process}在小批量下的可行性"
                            })

        # 如果没有场景工艺匹配，给出通用建议
        if not material_risks["process_risks"] and material_process:
            if "热压罐" in material_process:
                material_risks["process_risks"].append({
                    "risk": f"工艺复杂度高：{material_process} 需要专用设备，产能受限",
                    "level": "中",
                    "suggestion": "评估热压罐产能是否满足量产需求，或考虑真空导入等替代工艺"
                })

    def _analyze_supply_risk(self, material_risks: Dict, row: pd.Series):
        """分析供应链风险"""
        location = str(row.get("supplier_location", "")).strip()
        lead_time = float(row.get("lead_time_weeks", 0))
        stability = float(row.get("supply_stability_score", 5))

        # 单一供应商风险
        is_single = True
        for multi in MULTI_SUPPLIER_MARKERS:
            if multi in location:
                is_single = False
                break
        # 实际上 "中国/德国" 表示多源供应
        if "/" in location:
            is_single = False

        if is_single:
            material_risks["supply_risks"].append({
                "risk": f"单一供应来源：{location}，存在供应中断风险",
                "level": "中",
                "suggestion": "建议开发备选供应商，或要求供应商建立安全库存"
            })

        # 长交期风险
        if lead_time > 8:
            material_risks["supply_risks"].append({
                "risk": f"交货周期长：{lead_time} 周，可能影响项目进度",
                "level": "中",
                "suggestion": f"提前 {lead_time + 4} 周下单，或与供应商协商缩短交期"
            })

        # 供应稳定性风险
        if stability <= 5:
            material_risks["supply_risks"].append({
                "risk": f"供应稳定性评分较低（{stability}/10）",
                "level": "中",
                "suggestion": "评估供应商产能和交付记录，考虑签订长期供货协议"
            })

        # 海外供应商风险
        if "日本" in location or "德国" in location or "美国" in location or "英国" in location:
            if "中国" not in location:
                material_risks["supply_risks"].append({
                    "risk": f"海外供应商：{location}，存在汇率、关税和物流风险",
                    "level": "中",
                    "suggestion": "评估国内替代供应商，或建立海外库存缓冲"
                })

    def _analyze_data_quality(self, material_risks: Dict, row: pd.Series):
        """分析数据质量风险"""
        source = str(row.get("source_TDS", "")).strip()
        page = str(row.get("page", "")).strip()
        table = str(row.get("table_number", "")).strip()

        # 缺少来源信息
        if not source or source == "nan":
            material_risks["data_quality_risks"].append({
                "risk": "缺少 TDS 来源文档，性能数据来源不可追溯",
                "level": "高",
                "suggestion": "向供应商索取正式 TDS 文档，确认数据来源"
            })

        # 数据为典型值而非实测值（通用提示）
        material_risks["data_quality_risks"].append({
            "risk": "性能数据为典型值，可能存在批次波动",
            "level": "低",
            "suggestion": "要求供应商提供 CPK 数据或质量保证书，确认性能波动范围"
        })

        # 缺少测试标准
        material_risks["data_quality_risks"].append({
            "risk": "缺少测试标准信息，不同供应商的数据可能不可比",
            "level": "低",
            "suggestion": "确认各性能数据的测试标准（ASTM、ISO、GB），确保数据可比性"
        })