"""
混合检索模块 - 基于关键词语义匹配 + 数值过滤的候选材料检索
"""

import os
import re
import pandas as pd
from typing import List, Dict, Optional, Tuple


class MaterialRetriever:
    """材料检索器"""

    def __init__(self, csv_path: Optional[str] = None):
        """
        初始化检索器

        Args:
            csv_path: 材料数据库 CSV 路径，默认使用内置数据
        """
        if csv_path is None:
            csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "material_db.csv")
        self.df = self.load_database(csv_path)
        self._build_keyword_index()

    def load_database(self, csv_path: str) -> pd.DataFrame:
        """加载材料数据库"""
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        # 数值列类型转换
        numeric_cols = ["density", "tensile_strength", "yield_strength",
                        "thermal_conductivity", "estimated_cost_per_kg",
                        "lead_time_weeks", "supply_stability_score"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        # 布尔列转换
        df["rohs_compliant"] = df["rohs_compliant"].map({"TRUE": True, "True": True, True: True, False: False}).fillna(False)
        return df

    def _build_keyword_index(self):
        """构建关键词索引（材料描述）"""
        self.df["_keywords"] = self.df["description"].fillna("") + " " + \
                               self.df["grade"].fillna("") + " " + \
                               self.df["category"].fillna("") + " " + \
                               self.df["process"].fillna("")

    def semantic_search(self, query: str, top_k: int = 10) -> pd.DataFrame:
        """
        基于关键词的语义匹配

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            匹配分数排序后的 DataFrame
        """
        query_lower = query.lower()
        # 提取关键词
        keywords = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', query_lower))

        # 在副本上计算得分，避免污染 self.df
        df = self.df.copy()

        # 评分规则：匹配的关键词越多，得分越高
        scores = []
        for idx, row in df.iterrows():
            text = row["_keywords"].lower()
            score = sum(1 for kw in keywords if kw in text)
            # 类别权重加成
            category_boost = {
                "铝合金": 1.0 if "铝" in query_lower else 0.0,
                "镁合金": 1.5 if "镁" in query_lower or "轻量" in query_lower else 0.0,
                "碳纤维复材": 2.0 if "碳纤维" in query_lower or "复材" in query_lower else 0.0,
                "工程塑料": 1.0 if "塑料" in query_lower or "工程塑料" in query_lower else 0.0,
            }.get(row["category"], 0.0)
            # 工艺匹配
            process_boost = 1.5 if row["process"] and any(p in query_lower for p in row["process"].split("/")) else 0.0
            total_score = score + category_boost + process_boost
            scores.append(total_score)

        df["_score"] = scores
        result = df.nlargest(top_k, "_score")
        return result[result["_score"] > 0] if len(result) > 0 else df.head(top_k)

    def numeric_filter(self, requirements: List[Dict]) -> pd.DataFrame:
        """
        按数值指标过滤

        Args:
            requirements: 需求列表

        Returns:
            过滤后的 DataFrame
        """
        df = self.df.copy()

        for req in requirements:
            prop = req.get("property", "")
            min_val = req.get("min")
            max_val = req.get("max")
            value = req.get("value")

            # 数值型属性过滤
            if prop in df.columns:
                if min_val is not None:
                    df = df[df[prop] >= min_val]
                if max_val is not None:
                    df = df[df[prop] <= max_val]

            # 阻燃等级过滤（特殊处理）
            if prop == "flammability" and value:
                if value == "V-0":
                    # V-0 要求：材料标注为 V-0 或 V-0(需涂层)
                    df = df[df["flammability_UL94"].str.contains("V-0", na=False)]

        return df

    def hybrid_retrieve(self, query: str, requirements: List[Dict], top_k: int = 10) -> pd.DataFrame:
        """
        混合检索：先语义匹配，再数值过滤

        Args:
            query: 查询文本
            requirements: 需求列表
            top_k: 返回数量

        Returns:
            候选材料 DataFrame
        """
        # 步骤1: 语义匹配
        candidates = self.semantic_search(query, top_k=top_k * 2)

        # 步骤2: 数值过滤
        filtered = self.numeric_filter(requirements)

        # 合并：取交集，保留语义得分
        merged = candidates[candidates["material_id"].isin(filtered["material_id"])]
        if len(merged) == 0:
            # 如果交集为空，返回数值过滤结果（放宽语义匹配）
            return filtered.head(top_k)

        return merged.head(top_k)

    def get_all_materials(self) -> pd.DataFrame:
        """获取所有材料"""
        return self.df

    def get_material_by_id(self, material_id: str) -> Optional[Dict]:
        """按 ID 获取材料"""
        row = self.df[self.df["material_id"] == material_id]
        if len(row) == 0:
            return None
        return row.iloc[0].to_dict()