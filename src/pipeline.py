"""
主流程 Pipeline - 编排完整的材料选型流程
"""

import os
import json
from typing import Optional, Dict, List

from .normalizer import RequirementNormalizer
from .retriever import MaterialRetriever
from .veto import VetoChecker
from .ranking import TopsisRanker
from .risk import RiskAnalyzer
from .reporter import ReportGenerator


class MaterialSelectionPipeline:
    """材料选型完整 Pipeline"""

    def __init__(self, csv_path: Optional[str] = None,
                 api_key: Optional[str] = None,
                 api_base: Optional[str] = None,
                 model: str = "qwen3-8b-max"):
        """
        初始化 Pipeline

        Args:
            csv_path: 材料数据库路径
            api_key: LLM API Key
            api_base: LLM API 地址
            model: LLM 模型名
        """
        self.normalizer = RequirementNormalizer(api_key=api_key, api_base=api_base, model=model)
        self.retriever = MaterialRetriever(csv_path=csv_path)
        self.veto_checker = VetoChecker()
        self.ranker = TopsisRanker()
        self.risk_analyzer = RiskAnalyzer()
        self.reporter = ReportGenerator()

    def run(self, user_input: str, options: Optional[Dict] = None) -> Dict:
        """
        运行完整选型 Pipeline

        Args:
            user_input: 自然语言需求
            options: 附加选项，支持:
                - top_n: 返回 Top N 个候选
                - weight_overrides: 权重覆盖
                - api_key: LLM API Key

        Returns:
            完整 JSON 输出
        """
        if options is None:
            options = {}

        top_n = options.get("top_n", 5)
        weight_overrides = options.get("weight_overrides", None)

        trace = {
            "retrieval_method": "关键词匹配 + 数值过滤",
            "tds_entries": 0,
            "sorting_algorithm": "TOPSIS 多属性决策",
            "steps": []
        }

        # ---- 步骤1: 需求规范化 ----
        print("[Pipeline] 步骤1/6: 需求规范化...")
        normalized = self.normalizer.normalize(user_input, options)
        requirements = normalized.get("requirements", [])
        constraints = normalized.get("constraints", {})
        priorities = normalized.get("priorities", [])
        application = normalized.get("application", "未指定场景")
        trace["steps"].append({"step": 1, "action": "需求规范化", "output": normalized})

        # ---- 步骤2: 混合检索 ----
        print("[Pipeline] 步骤2/6: 混合检索与初筛...")
        candidates = self.retriever.hybrid_retrieve(user_input, requirements, top_k=top_n * 3)
        trace["tds_entries"] = len(candidates)
        trace["steps"].append({"step": 2, "action": "混合检索", "candidates_count": len(candidates)})

        # ---- 步骤3: 否决检查 ----
        print("[Pipeline] 步骤3/6: 硬性否决检查...")
        passed, veto_details = self.veto_checker.check(candidates, requirements)

        # 成本约束否决
        cost_max = constraints.get("cost_per_kg_max")
        if cost_max is not None:
            passed, cost_vetoes = self.veto_checker.check_cost_constraint(passed, cost_max)
            veto_details.extend(cost_vetoes)

        # 法规约束否决
        regulations = constraints.get("regulations", [])
        if regulations:
            passed, reg_vetoes = self.veto_checker.check_regulation_constraint(passed, regulations)
            veto_details.extend(reg_vetoes)

        trace["steps"].append({
            "step": 3, "action": "否决检查",
            "passed_count": len(passed),
            "vetoed_count": len(veto_details)
        })

        # ---- 步骤4: TOPSIS 排序 ----
        print("[Pipeline] 步骤4/6: 多属性决策排序...")
        weights = weight_overrides or self.ranker.infer_weights(priorities)
        if len(passed) > 0:
            ranked = self.ranker.rank(passed, requirements, weights=weights, priorities=priorities)
        else:
            ranked = passed  # 空的 DataFrame

        trace["steps"].append({"step": 4, "action": "TOPSIS 排序", "weights": weights})

        # ---- 步骤5: 风险分析 ----
        print("[Pipeline] 步骤5/6: 适配风险分析...")
        risks = self.risk_analyzer.analyze(ranked.head(top_n), requirements, application)
        trace["steps"].append({"step": 5, "action": "风险分析", "risks_count": len(risks)})

        # ---- 步骤6: 报告生成 ----
        print("[Pipeline] 步骤6/6: 报告生成...")
        # 生成验证计划
        top_materials_list = []
        for _, row in ranked.head(2).iterrows():
            top_materials_list.append(row.to_dict())
        next_steps = self.reporter.generate_validation_plan(application, top_materials_list, requirements)

        json_output = self.reporter.generate_json_output(
            ranked=ranked.head(top_n),
            vetoed=veto_details,
            risks=risks,
            next_steps=next_steps,
            trace=trace,
            requirements=requirements,
            application=application
        )

        trace["steps"].append({"step": 6, "action": "报告生成"})
        json_output["trace"] = trace

        print("[Pipeline] 完成!")
        return json_output

    def run_and_report(self, user_input: str, options: Optional[Dict] = None) -> str:
        """
        运行 Pipeline 并生成 Markdown 报告

        Args:
            user_input: 自然语言需求
            options: 附加选项

        Returns:
            Markdown 格式报告
        """
        result = self.run(user_input, options)
        return self.reporter.generate_markdown_report(result)