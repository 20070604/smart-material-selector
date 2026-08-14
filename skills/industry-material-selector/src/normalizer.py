"""
需求规范化器 - 将自然语言需求转化为结构化 JSON
支持 LLM 调用（OpenAI/Qwen 兼容接口）和离线模拟模式
"""

import json
import os
import re
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# 离线模拟的规则解析器
def _parse_offline(user_input: str) -> dict:
    """不使用 LLM，基于规则从自然语言中提取需求结构"""
    result = {
        "application": "未指定应用场景",
        "requirements": [],
        "constraints": {
            "cost_per_kg_max": None,
            "regulations": [],
            "supply_chain": {
                "location": None,
                "annual_volume_tons": None
            }
        },
        "priorities": []
    }

    # 提取应用场景（第一句作为摘要）
    sentences = re.split(r'[，。；\n]', user_input.strip())
    if sentences and sentences[0].strip():
        result["application"] = sentences[0].strip()[:30]

    # 提取密度
    density_match = re.search(r'密度\s*[<≤]\s*([\d.]+)', user_input)
    if density_match:
        result["requirements"].append({
            "property": "density",
            "min": None,
            "max": float(density_match.group(1)),
            "value": None,
            "unit": "g/cm³",
            "standard": None
        })

    # 提取拉伸强度
    ts_match = re.search(r'拉伸(?:强度)?\s*[>≥]\s*(\d+)', user_input)
    if ts_match:
        result["requirements"].append({
            "property": "tensile_strength",
            "min": float(ts_match.group(1)),
            "max": None,
            "value": None,
            "unit": "MPa",
            "standard": None
        })

    # 提取屈服强度
    ys_match = re.search(r'屈服(?:强度)?\s*[>≥]\s*(\d+)', user_input)
    if ys_match:
        result["requirements"].append({
            "property": "yield_strength",
            "min": float(ys_match.group(1)),
            "max": None,
            "value": None,
            "unit": "MPa",
            "standard": None
        })

    # 提取导热系数
    tc_match = re.search(r'导热(?:\s*系数)?\s*[>≥]\s*([\d.]+)', user_input)
    if tc_match:
        result["requirements"].append({
            "property": "thermal_conductivity",
            "min": float(tc_match.group(1)),
            "max": None,
            "value": None,
            "unit": "W/mK",
            "standard": None
        })

    # 提取阻燃等级
    fl_match = re.search(r'UL94\s*(V-[\dA-Z]+)', user_input, re.IGNORECASE)
    if fl_match:
        result["requirements"].append({
            "property": "flammability",
            "min": None,
            "max": None,
            "value": fl_match.group(1).upper(),
            "unit": "",
            "standard": "UL94"
        })

    # 提取成本
    cost_match = re.search(r'成本\s*[<≤]\s*\$?(\d+)', user_input)
    if cost_match:
        result["constraints"]["cost_per_kg_max"] = float(cost_match.group(1))

    # 提取法规
    if re.search(r'RoHS', user_input, re.IGNORECASE):
        result["constraints"]["regulations"].append("RoHS")
    if re.search(r'REACH', user_input, re.IGNORECASE):
        result["constraints"]["regulations"].append("REACH")

    # 提取供应链位置
    for loc in ["中国", "国内", "欧洲", "美国", "日本"]:
        if loc in user_input:
            result["constraints"]["supply_chain"]["location"] = loc
            break

    # 提取年产量（兼容 "1000吨"、"500吨/年"、"1000 吨" 等格式）
    volume_match = re.search(r'(\d+)\s*吨', user_input)
    if volume_match:
        result["constraints"]["supply_chain"]["annual_volume_tons"] = float(volume_match.group(1))

    # 提取优先级关键词
    priority_keywords = {
        "轻量化": ["轻量", "轻", "密度低"],
        "低成本": ["低成本", "便宜", "经济"],
        "高导热": ["导热", "散热"],
        "高强": ["高强", "强度高"],
        "阻燃": ["阻燃", "V-0", "UL94"],
        "耐腐蚀": ["耐腐蚀", "耐候"],
        "耐高温": ["耐高温", "耐热"]
    }
    for priority, keywords in priority_keywords.items():
        if any(kw in user_input for kw in keywords):
            result["priorities"].append(priority)

    return result


class RequirementNormalizer:
    """需求规范化器"""

    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None, model: str = "qwen3-8b-max"):
        """
        初始化规范化器

        Args:
            api_key: LLM API Key，None 时使用离线模式
            api_base: API 地址，None 时使用默认值
            model: 模型名称
        """
        self.api_key = api_key or os.environ.get("LLM_API_KEY")
        self.api_base = api_base or os.environ.get("LLM_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.model = model
        self._load_prompt()

    def _load_prompt(self):
        """加载需求提取 Prompt"""
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "requirement_extract.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()
        except FileNotFoundError:
            self.prompt_template = "请将以下需求转为JSON: {user_input}"

    def normalize(self, user_input: str, options: Optional[dict] = None) -> dict:
        """
        规范化用户输入

        Args:
            user_input: 自然语言需求
            options: 附加选项

        Returns:
            结构化需求文档
        """
        # 有 API Key 时使用 LLM
        if self.api_key and OpenAI is not None:
            try:
                return self._call_llm(user_input)
            except Exception as e:
                print(f"[Normalizer] LLM 调用失败，降级到离线模式: {e}")
                return _parse_offline(user_input)

        # 无 API Key 时使用离线规则解析
        print("[Normalizer] 使用离线模式（无 LLM API Key）")
        return _parse_offline(user_input)

    def _call_llm(self, user_input: str) -> dict:
        """调用 LLM 进行需求提取"""
        client = OpenAI(api_key=self.api_key, base_url=self.api_base)
        prompt = self.prompt_template.replace("{user_input}", user_input)

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个 JSON 输出助手，只输出 JSON 格式，不包含其他内容。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2000
        )

        content = response.choices[0].message.content.strip()
        # 尝试提取 JSON 部分
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试从 markdown 代码块中提取
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
            if json_match:
                return json.loads(json_match.group(1))
            raise


# 便捷函数
def normalize(user_input: str, **kwargs) -> dict:
    normalizer = RequirementNormalizer(**kwargs)
    return normalizer.normalize(user_input)