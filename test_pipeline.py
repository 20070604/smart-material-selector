"""Pipeline 功能验证脚本"""
import sys
import os
import json

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.pipeline import MaterialSelectionPipeline
from src.reporter import ReportGenerator

pipeline = MaterialSelectionPipeline()
reporter = ReportGenerator()
all_pass = True

def test_case(name, user_input, expect_candidates=True):
    global all_pass
    print(f"\n{'=' * 60}")
    print(f"测试: {name}")
    print(f"输入: {user_input[:50]}...")
    print('=' * 60)

    result = pipeline.run(user_input)
    summary = result.get("summary", {})
    candidates = summary.get("total_candidates", 0)
    vetoed = summary.get("vetoed_count", 0)

    print(f"应用场景: {result.get('application', '')}")
    print(f"候选材料: {candidates} | 否决: {vetoed}")
    top_material = result.get('ranked_materials', [])
    if top_material:
        print(f"首选推荐: {summary.get('top_recommendation', '无')} (TOPSIS: {top_material[0].get('topsis_score', 0):.4f})")
    else:
        print(f"首选推荐: 无 (所有材料均被否决或无候选材料)")

    # 显示否决详情
    for v in result.get("veto_details", []):
        print(f"  否决: {v['grade']:20s} | {v['veto_reason']}")

    # 验证输出字段完整性
    for field in ["ranked_materials", "veto_details", "risk_analysis", "next_steps", "trace", "summary", "radar_chart_data"]:
        if field not in result:
            print(f"  [失败] 缺少字段: {field}")
            all_pass = False

    # 验证 Markdown 报告
    markdown = reporter.generate_markdown_report(result)
    if len(markdown) < 200:
        print(f"  [失败] Markdown 报告过短: {len(markdown)} 字符")
        all_pass = False
    else:
        print(f"  Markdown 报告: {len(markdown)} 字符 ✓")

    # 验证 TOPSIS 得分有效（仅当有候选材料时）
    if not result.get("ranked_materials", []):
        print(f"  (无候选材料, 跳过 TOPSIS 验证)")
    else:
        for m in result["ranked_materials"]:
            score = m.get("topsis_score", -1)
            if score < 0 or score > 1:
                print(f"  [失败] TOPSIS 得分异常: {m['grade']} = {score}")
                all_pass = False

    return result

# 测试用例 1: 汽车发动机罩盖
test_case("汽车发动机罩盖", "汽车发动机罩盖，密度<1.5 g/cm³，拉伸强度>150 MPa，UL94 V-0，成本<$10/kg，RoHS合规，国内采购")

# 测试用例 2: 散热器基板
test_case("散热器基板", "散热器基板，导热系数>150 W/mK，密度<3.0 g/cm³，成本<$50/kg，国内采购")

# 测试用例 3: 高强度结构件
test_case("高强度结构件", "高强度结构件，拉伸强度>500 MPa，屈服强度>400 MPa，密度<5.0 g/cm³，成本<$30/kg")

# 测试用例 4: EV 电池包壳体（严格条件 - 应无候选）
test_case("EV电池包壳体（严格）", "电动汽车电池包壳体，密度<2.0 g/cm³，拉伸强度>300 MPa，导热系数>100 W/mK，UL94 V-0，成本<$20/kg，RoHS合规，国内采购")

# 生成完整 Markdown 报告
report_path = os.path.join(project_root, "selection_report.md")
result = pipeline.run("汽车发动机罩盖，密度<1.5 g/cm³，拉伸强度>150 MPa，UL94 V-0，成本<$10/kg，RoHS合规，国内采购")
markdown = reporter.generate_markdown_report(result)
with open(report_path, "w", encoding="utf-8") as f:
    f.write(markdown)
print(f"\n完整 Markdown 报告已保存至: {report_path}")
print(f"Markdown 报告内容预览:\n{markdown[:500]}...")

if all_pass:
    print("\n✓ 所有测试通过!")
else:
    print("\n✗ 部分测试未通过，请检查输出")
    sys.exit(1)