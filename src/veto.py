"""
否决检查模块 - 逐项检查硬性条件，标记否决材料及原因
"""

import pandas as pd
from typing import List, Dict, Tuple


class VetoChecker:
    """否决检查器"""

    def __init__(self):
        pass

    def check(self, materials: pd.DataFrame, requirements: List[Dict]) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        执行否决检查

        Args:
            materials: 候选材料 DataFrame
            requirements: 需求列表

        Returns:
            (passed_df, veto_details)
            - passed_df: 通过检查的材料
            - veto_details: 被否决材料及原因列表
        """
        if len(materials) == 0:
            return materials, []

        passed = materials.copy()
        veto_details = []

        for req in requirements:
            prop = req.get("property", "")
            min_val = req.get("min")
            max_val = req.get("max")
            value = req.get("value")

            # 阻燃等级否决检查
            if prop == "flammability" and value:
                details = self._check_flammability(passed, value)
                passed = details["passed"]
                veto_details.extend(details["vetoed"])

            # 密度否决检查
            if prop == "density" and max_val is not None:
                mask = passed["density"] <= max_val
                vetoed = passed[~mask]
                for _, row in vetoed.iterrows():
                    veto_details.append({
                        "material_id": row["material_id"],
                        "grade": row["grade"],
                        "veto_reason": f"密度 {row['density']} g/cm³ 超过上限 {max_val} g/cm³",
                        "requirement": f"密度 ≤ {max_val} g/cm³",
                        "actual_value": f"{row['density']} g/cm³",
                        "status": "否决"
                    })
                passed = passed[mask]

            # 拉伸强度否决检查
            if prop == "tensile_strength" and min_val is not None:
                mask = passed["tensile_strength"] >= min_val
                vetoed = passed[~mask]
                for _, row in vetoed.iterrows():
                    veto_details.append({
                        "material_id": row["material_id"],
                        "grade": row["grade"],
                        "veto_reason": f"拉伸强度 {row['tensile_strength']} MPa 低于下限 {min_val} MPa",
                        "requirement": f"拉伸强度 ≥ {min_val} MPa",
                        "actual_value": f"{row['tensile_strength']} MPa",
                        "status": "否决"
                    })
                passed = passed[mask]

            # 导热系数否决检查
            if prop == "thermal_conductivity" and min_val is not None:
                mask = passed["thermal_conductivity"] >= min_val
                vetoed = passed[~mask]
                for _, row in vetoed.iterrows():
                    veto_details.append({
                        "material_id": row["material_id"],
                        "grade": row["grade"],
                        "veto_reason": f"导热系数 {row['thermal_conductivity']} W/mK 低于下限 {min_val} W/mK",
                        "requirement": f"导热系数 ≥ {min_val} W/mK",
                        "actual_value": f"{row['thermal_conductivity']} W/mK",
                        "status": "否决"
                    })
                passed = passed[mask]

            # 屈服强度否决检查
            if prop == "yield_strength" and min_val is not None:
                mask = passed["yield_strength"] >= min_val
                vetoed = passed[~mask]
                for _, row in vetoed.iterrows():
                    veto_details.append({
                        "material_id": row["material_id"],
                        "grade": row["grade"],
                        "veto_reason": f"屈服强度 {row['yield_strength']} MPa 低于下限 {min_val} MPa",
                        "requirement": f"屈服强度 ≥ {min_val} MPa",
                        "actual_value": f"{row['yield_strength']} MPa",
                        "status": "否决"
                    })
                passed = passed[mask]

        # 成本否决检查
        # (成本在 constraints 中处理，由 pipeline 传入)

        return passed, veto_details

    def _check_flammability(self, materials: pd.DataFrame, required_level: str) -> dict:
        """阻燃等级否决检查"""
        passed = materials.copy()
        veto_details = []

        for _, row in materials.iterrows():
            mat_level = str(row["flammability_UL94"]).strip()
            status = "通过"
            reason = ""

            if required_level == "V-0":
                if mat_level == "HB":
                    status = "否决"
                    reason = f"阻燃等级 HB 不满足 V-0 要求"
                elif "V-0" in mat_level and "涂层" in mat_level:
                    status = "有条件通过"
                    reason = "基材本身不阻燃，但可通过阻燃涂层满足 V-0，需验证涂层效果"
                elif mat_level == "V-0":
                    status = "通过"
                    reason = "满足 V-0 阻燃要求"

            if status == "否决":
                veto_details.append({
                    "material_id": row["material_id"],
                    "grade": row["grade"],
                    "veto_reason": reason,
                    "requirement": f"UL94 {required_level}",
                    "actual_value": mat_level,
                    "status": "否决"
                })
                passed = passed[passed["material_id"] != row["material_id"]]
            elif status == "有条件通过":
                veto_details.append({
                    "material_id": row["material_id"],
                    "grade": row["grade"],
                    "veto_reason": reason,
                    "requirement": f"UL94 {required_level}",
                    "actual_value": mat_level,
                    "status": "有条件通过"
                })

        return {"passed": passed, "vetoed": veto_details}

    def check_cost_constraint(self, materials: pd.DataFrame, cost_per_kg_max: float) -> Tuple[pd.DataFrame, List[Dict]]:
        """成本约束否决检查"""
        if cost_per_kg_max is None:
            return materials, []

        passed = materials.copy()
        veto_details = []

        mask = passed["estimated_cost_per_kg"] <= cost_per_kg_max
        vetoed = passed[~mask]
        for _, row in vetoed.iterrows():
            veto_details.append({
                "material_id": row["material_id"],
                "grade": row["grade"],
                "veto_reason": f"成本 ${row['estimated_cost_per_kg']}/kg 超过预算 ${cost_per_kg_max}/kg",
                "requirement": f"成本 ≤ ${cost_per_kg_max}/kg",
                "actual_value": f"${row['estimated_cost_per_kg']}/kg",
                "status": "否决"
            })
        passed = passed[mask]

        return passed, veto_details

    def check_regulation_constraint(self, materials: pd.DataFrame, regulations: List[str]) -> Tuple[pd.DataFrame, List[Dict]]:
        """法规约束否决检查"""
        if not regulations:
            return materials, []

        passed = materials.copy()
        veto_details = []

        for reg in regulations:
            if reg.upper() == "ROHS":
                mask = passed["rohs_compliant"] == True
                vetoed = passed[~mask]
                for _, row in vetoed.iterrows():
                    veto_details.append({
                        "material_id": row["material_id"],
                        "grade": row["grade"],
                        "veto_reason": f"不满足 RoHS 合规要求",
                        "requirement": "RoHS 合规",
                        "actual_value": "否",
                        "status": "否决"
                    })
                passed = passed[mask]

        return passed, veto_details