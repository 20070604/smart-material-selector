"""
TOPSIS 排序引擎 - 基于逼近理想解排序法的多属性决策
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple


# 场景默认权重映射
SCENE_WEIGHTS = {
    "轻量化": {"density": 0.35, "tensile_strength": 0.25, "cost": 0.20, "thermal_conductivity": 0.10, "supply": 0.10},
    "高导热": {"density": 0.10, "tensile_strength": 0.10, "cost": 0.20, "thermal_conductivity": 0.45, "supply": 0.15},
    "高强度": {"density": 0.15, "tensile_strength": 0.40, "cost": 0.20, "thermal_conductivity": 0.10, "supply": 0.15},
    "低成本": {"density": 0.15, "tensile_strength": 0.15, "cost": 0.45, "thermal_conductivity": 0.10, "supply": 0.15},
    "均衡": {"density": 0.20, "tensile_strength": 0.25, "cost": 0.25, "thermal_conductivity": 0.15, "supply": 0.15},
}

# 默认权重
DEFAULT_WEIGHTS = {"density": 0.20, "tensile_strength": 0.25, "cost": 0.25, "thermal_conductivity": 0.15, "supply": 0.15}


class TopsisRanker:
    """TOPSIS 多属性排序器"""

    def __init__(self):
        pass

    def infer_weights(self, priorities: List[str]) -> Dict[str, float]:
        """
        基于优先级关键词推断权重

        Args:
            priorities: 优先级关键词列表

        Returns:
            权重字典
        """
        if not priorities:
            return dict(DEFAULT_WEIGHTS)

        # 从优先级中匹配场景
        weights = None
        for priority in priorities:
            for scene_key, scene_weights in SCENE_WEIGHTS.items():
                if scene_key in priority:
                    weights = scene_weights
                    break
            if weights:
                break

        if weights is None:
            return dict(DEFAULT_WEIGHTS)

        return dict(weights)

    def rank(self, materials: pd.DataFrame, requirements: List[Dict],
             weights: Optional[Dict[str, float]] = None,
             priorities: Optional[List[str]] = None) -> pd.DataFrame:
        """
        执行 TOPSIS 排序

        Args:
            materials: 候选材料 DataFrame
            requirements: 需求列表
            weights: 权重字典，None 时自动推断
            priorities: 优先级关键词（用于权重推断）

        Returns:
            排序后的 DataFrame，包含综合得分列
        """
        if len(materials) == 0:
            return materials

        # 确定权重
        if weights is None:
            weights = self.infer_weights(priorities or [])

        # 构建决策矩阵
        criteria = ["density", "tensile_strength", "thermal_conductivity", "estimated_cost_per_kg", "supply_stability_score"]
        available = [c for c in criteria if c in materials.columns]

        matrix = materials[available].copy().values.astype(float)

        # 处理缺失值
        matrix = np.nan_to_num(matrix, nan=0.0)

        # 步骤1: 向量规范化
        norms = np.sqrt(np.sum(matrix ** 2, axis=0))
        norms[norms == 0] = 1  # 避免除零
        normalized = matrix / norms

        # 步骤2: 加权规范化
        # 语义权重键(cost/supply) -> 实际列名(estimated_cost_per_kg/supply_stability_score) 映射
        WEIGHT_KEY_MAP = {"cost": "estimated_cost_per_kg", "supply": "supply_stability_score"}
        weight_vector = np.array([weights.get(WEIGHT_KEY_MAP.get(c, c), 0.15) for c in available])
        weighted = normalized * weight_vector

        # 步骤3: 确定正理想解和负理想解
        # 成本(density反向, estimated_cost_per_kg反向) 和 供应稳定性(supply_stability_score正向) 是成本型指标
        # 拉伸强度(tensile_strength) 和 导热系数(thermal_conductivity) 是效益型指标
        benefit_indices = []
        cost_indices = []
        for i, c in enumerate(available):
            if c in ["density", "estimated_cost_per_kg"]:
                cost_indices.append(i)  # 越小越好
            else:
                benefit_indices.append(i)  # 越大越好

        # 正理想解
        positive_ideal = np.zeros(len(available))
        for i in benefit_indices:
            positive_ideal[i] = np.max(weighted[:, i])
        for i in cost_indices:
            positive_ideal[i] = np.min(weighted[:, i])

        # 负理想解
        negative_ideal = np.zeros(len(available))
        for i in benefit_indices:
            negative_ideal[i] = np.min(weighted[:, i])
        for i in cost_indices:
            negative_ideal[i] = np.max(weighted[:, i])

        # 步骤4: 计算距离
        dist_positive = np.sqrt(np.sum((weighted - positive_ideal) ** 2, axis=1))
        dist_negative = np.sqrt(np.sum((weighted - negative_ideal) ** 2, axis=1))

        # 步骤5: 计算相对贴近度
        # 单材料情况：正负理想解相同，得分设为 1.0
        if len(materials) == 1:
            closeness = np.ones(1)
        else:
            denom = dist_positive + dist_negative
            denom[denom == 0] = 1  # 避免除零
            closeness = dist_negative / denom

        # 将结果添加到 DataFrame
        result = materials.copy()
        result["topsis_score"] = np.round(closeness, 4)
        result["_dist_positive"] = np.round(dist_positive, 4)
        result["_dist_negative"] = np.round(dist_negative, 4)

        # 按综合得分降序排列
        result = result.sort_values("topsis_score", ascending=False).reset_index(drop=True)

        return result

    def get_radar_data(self, materials: pd.DataFrame, requirements: List[Dict]) -> List[Dict]:
        """
        生成雷达图数据

        Args:
            materials: 候选材料 DataFrame
            requirements: 需求列表

        Returns:
            雷达图数据列表
        """
        radar_data = []
        # 选择用于雷达图的属性
        radar_properties = ["density", "tensile_strength", "thermal_conductivity", "estimated_cost_per_kg"]

        # 找到每个属性的最大值和最小值（用于归一化）
        for _, row in materials.head(5).iterrows():
            material_data = {
                "grade": row["grade"],
                "values": {}
            }
            for prop in radar_properties:
                if prop in row:
                    material_data["values"][prop] = float(row[prop])
            radar_data.append(material_data)

        # 添加目标值
        target = {"grade": "目标值", "values": {}}
        for req in requirements:
            prop = req.get("property", "")
            if prop in radar_properties:
                if req.get("max") is not None:
                    target["values"][prop] = req["max"]
                elif req.get("min") is not None:
                    target["values"][prop] = req["min"]
        if target["values"]:
            radar_data.insert(0, target)

        return radar_data