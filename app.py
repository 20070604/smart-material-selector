#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
产业原材料智能选型 Skill - Web Demo
"""

import os
import sys
import json
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, render_template_string
from src.pipeline import MaterialSelectionPipeline

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CSV_PATH = os.path.join(DATA_DIR, "material_db.csv")

pipeline = None

def get_pipeline():
    global pipeline
    if pipeline is None:
        csv_path = CSV_PATH
        if not os.path.exists(csv_path):
            csv_path = None
        pipeline = MaterialSelectionPipeline(
            csv_path=csv_path,
            api_key=None
        )
    return pipeline


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>产业原材料智能选型 Demo</title>
<style>
/* ===== Reset & Base ===== */
*{margin:0;padding:0;box-sizing:border-box;}
:root{
  --c-purple:#7c3aed;--c-pink:#ec4899;--c-cyan:#22d3ee;--c-violet:#a78bfa;
  --c-lavender:#c4b5fd;--c-text:#e2e2f0;--c-muted:rgba(255,255,255,0.5);
  --c-card-bg:rgba(255,255,255,0.07);--c-card-border:rgba(255,255,255,0.12);
  --c-success:#34d399;--c-warn:#fbbf24;--c-danger:#f87171;
}
body{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  background:#0a0a1a;color:var(--c-text);min-height:100vh;
  line-height:1.7;overflow-x:hidden;
}

/* ===== Aurora Background ===== */
.aurora{position:fixed;top:0;left:0;width:100%;height:100%;z-index:-1;overflow:hidden;}
.aurora::before,.aurora::after,.aurora-bg{
  content:'';position:absolute;border-radius:50%;filter:blur(80px);opacity:0.35;
}
.aurora-bg{
  width:100%;height:100%;
  background:linear-gradient(135deg,#0a0a1a 0%,#1a1a3e 40%,#2d1b4e 100%);
}
.aurora::before{
  width:600px;height:600px;top:-200px;left:-150px;
  background:radial-gradient(circle,#7c3aed,transparent 70%);
  animation:float1 20s ease-in-out infinite;
}
.aurora::after{
  width:500px;height:500px;bottom:-150px;right:-100px;
  background:radial-gradient(circle,#ec4899,transparent 70%);
  animation:float2 25s ease-in-out infinite;
}
.aurora-mid{
  position:fixed;top:30%;left:40%;width:450px;height:450px;
  border-radius:50%;filter:blur(70px);opacity:0.2;z-index:-1;
  background:radial-gradient(circle,#22d3ee,transparent 70%);
  animation:float3 30s ease-in-out infinite;
}
@keyframes float1{0%,100%{transform:translate(0,0)scale(1);}33%{transform:translate(100px,80px)scale(1.1);}66%{transform:translate(-50px,120px)scale(0.95);}}
@keyframes float2{0%,100%{transform:translate(0,0)scale(1);}33%{transform:translate(-80px,-60px)scale(1.15);}66%{transform:translate(60px,-100px)scale(0.9);}}
@keyframes float3{0%,100%{transform:translate(0,0)scale(1);}50%{transform:translate(-120px,60px)scale(1.2);}}

/* ===== Layout ===== */
.container{max-width:1200px;margin:0 auto;padding:48px 24px;}

/* ===== Header ===== */
.header{text-align:center;margin-bottom:48px;animation:fadeDown 0.8s ease;}
.header h1{
  font-size:2.6em;font-weight:800;letter-spacing:-1px;
  background:linear-gradient(135deg,#a78bfa 0%,#22d3ee 50%,#f472b6 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;margin-bottom:12px;
  filter:drop-shadow(0 0 30px rgba(167,139,250,0.3));
}
.header p{color:var(--c-muted);font-size:1.1em;font-weight:300;}
.header .badge-row{display:flex;justify-content:center;gap:8px;margin-top:16px;flex-wrap:wrap;}
.header-badge{
  background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);
  border-radius:50px;padding:4px 14px;font-size:0.78em;color:var(--c-lavender);
  backdrop-filter:blur(8px);
}

/* ===== Glass Card ===== */
.card{
  background:var(--c-card-bg);
  backdrop-filter:blur(20px) saturate(180%);
  -webkit-backdrop-filter:blur(20px) saturate(180%);
  border:1px solid var(--c-card-border);
  border-radius:20px;padding:36px;margin-bottom:32px;
  box-shadow:0 8px 32px rgba(0,0,0,0.3),inset 0 1px 0 rgba(255,255,255,0.08);
  transition:box-shadow 0.3s,border-color 0.3s;
  animation:fadeUp 0.6s ease;
}
.card:hover{
  border-color:rgba(124,58,237,0.2);
  box-shadow:0 8px 32px rgba(0,0,0,0.3),0 0 24px rgba(124,58,237,0.1),inset 0 1px 0 rgba(255,255,255,0.08);
}
.card h2{font-size:1.4em;margin-bottom:20px;color:var(--c-lavender);display:flex;align-items:center;gap:10px;}
.card h2 .icon{width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,var(--c-purple),var(--c-pink));display:inline-flex;align-items:center;justify-content:center;font-size:0.7em;color:#fff;}

/* ===== Textarea ===== */
textarea{
  width:100%;min-height:130px;
  background:rgba(0,0,0,0.25);
  border:1px solid rgba(255,255,255,0.1);
  border-radius:14px;color:var(--c-text);
  font-size:1em;padding:16px;resize:vertical;
  font-family:inherit;transition:border-color 0.3s,box-shadow 0.3s;
}
textarea:focus{outline:none;border-color:var(--c-purple);box-shadow:0 0 0 3px rgba(124,58,237,0.15);}
textarea::placeholder{color:rgba(255,255,255,0.3);}

/* ===== Examples ===== */
.examples{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px;}
.example-tag{
  border-radius:50px;padding:8px 20px;font-size:0.85em;cursor:pointer;
  transition:all 0.3s;font-weight:500;border:1px solid transparent;
}
.example-tag:nth-child(1){background:rgba(124,58,237,0.15);border-color:rgba(124,58,237,0.3);color:#c4b5fd;}
.example-tag:nth-child(2){background:rgba(34,211,238,0.15);border-color:rgba(34,211,238,0.3);color:#67e8f9;}
.example-tag:nth-child(3){background:rgba(236,72,153,0.15);border-color:rgba(236,72,153,0.3);color:#f9a8d4;}
.example-tag:nth-child(4){background:rgba(52,211,153,0.15);border-color:rgba(52,211,153,0.3);color:#6ee7b7;}
.example-tag:hover{transform:translateY(-3px);box-shadow:0 4px 16px rgba(0,0,0,0.2);}

/* ===== Button ===== */
.btn{
  background:linear-gradient(135deg,#7c3aed,#ec4899);
  border:none;border-radius:14px;color:#fff;
  font-size:1.1em;font-weight:600;padding:14px 48px;cursor:pointer;
  transition:all 0.3s;position:relative;overflow:hidden;
  box-shadow:0 4px 20px rgba(124,58,237,0.3);
}
.btn:hover{transform:translateY(-2px) scale(1.03);box-shadow:0 8px 30px rgba(124,58,237,0.5);}
.btn:active{transform:translateY(0) scale(0.98);}
.btn:disabled{opacity:0.5;cursor:not-allowed;transform:none;}
.btn-row{text-align:center;margin-top:20px;}

/* ===== Loading ===== */
.loading{display:none;text-align:center;padding:40px;}
.loading.show{display:block;animation:fadeUp 0.4s ease;}
.loader-rings{position:relative;width:64px;height:64px;margin:0 auto 16px;}
.loader-rings div{
  position:absolute;border-radius:50%;border:3px solid transparent;
}
.loader-rings div:nth-child(1){top:0;left:0;width:100%;height:100%;border-top-color:#7c3aed;animation:spin 1s linear infinite;}
.loader-rings div:nth-child(2){top:8px;left:8px;width:48px;height:48px;border-top-color:#22d3ee;animation:spin 1.5s linear infinite reverse;}
.loader-rings div:nth-child(3){top:16px;left:16px;width:32px;height:32px;border-top-color:#ec4899;animation:spin 0.8s linear infinite;}
.loader-rings div:nth-child(4){top:24px;left:24px;width:16px;height:16px;background:linear-gradient(135deg,#a78bfa,#f472b6);border-radius:50%;animation:pulse 1s ease-in-out infinite;}
.loading p{
  background:linear-gradient(90deg,#a78bfa,#22d3ee,#f472b6);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;font-size:1.05em;font-weight:500;
  animation:textShimmer 2s ease-in-out infinite;
}

/* ===== Result ===== */
.result{display:none;}
.result.show{display:block;animation:fadeUp 0.5s ease;}
.result-section{margin-top:24px;animation:fadeUp 0.5s ease both;}
.result-section:nth-child(1){animation-delay:0s;}
.result-section:nth-child(2){animation-delay:0.08s;}
.result-section:nth-child(3){animation-delay:0.16s;}
.result-section:nth-child(4){animation-delay:0.24s;}
.result-section:nth-child(5){animation-delay:0.32s;}
.result-section:nth-child(6){animation-delay:0.40s;}
.result-section h3{color:var(--c-lavender);margin-bottom:14px;font-size:1.15em;display:flex;align-items:center;gap:8px;}

/* ===== Material Cards Grid ===== */
.material-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;}
.material-card{
  background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);
  border-radius:16px;padding:24px;transition:all 0.3s;position:relative;overflow:hidden;
}
.material-card::before{
  content:'';position:absolute;top:0;left:0;width:4px;height:100%;
  background:linear-gradient(180deg,var(--c-purple),var(--c-pink));
}
.material-card.rank-1::before{background:linear-gradient(180deg,#7c3aed,#a78bfa);}
.material-card.rank-2::before{background:linear-gradient(180deg,#06b6d4,#22d3ee);}
.material-card.rank-3::before{background:linear-gradient(180deg,#ec4899,#f472b6);}
.material-card:hover{transform:translateY(-4px);box-shadow:0 12px 36px rgba(0,0,0,0.3);border-color:rgba(124,58,237,0.2);}
.material-card .mc-header{display:flex;align-items:center;gap:12px;margin-bottom:16px;}
.rank-badge{
  width:36px;height:36px;border-radius:12px;display:flex;
  align-items:center;justify-content:center;font-weight:800;font-size:1em;flex-shrink:0;
  color:#fff;box-shadow:0 4px 12px rgba(0,0,0,0.2);
}
.rank-badge.rank-1{background:linear-gradient(135deg,#7c3aed,#a78bfa);}
.rank-badge.rank-2{background:linear-gradient(135deg,#06b6d4,#22d3ee);}
.rank-badge.rank-3{background:linear-gradient(135deg,#ec4899,#f472b6);}
.rank-badge.rank-4,.rank-badge.rank-5{background:rgba(255,255,255,0.1);color:var(--c-muted);}
.material-card .mc-name{font-size:1.15em;font-weight:700;color:#fff;}
.material-card .mc-cat{
  display:inline-block;background:rgba(167,139,250,0.12);border:1px solid rgba(167,139,250,0.2);
  border-radius:50px;padding:2px 12px;font-size:0.75em;color:var(--c-violet);margin-top:4px;
}
.material-card .mc-props{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px;}
.mc-prop{
  background:rgba(0,0,0,0.2);border-radius:10px;padding:10px 12px;
}
.mc-prop .mc-label{font-size:0.72em;color:var(--c-muted);text-transform:uppercase;letter-spacing:0.5px;}
.mc-prop .mc-value{font-size:1.05em;font-weight:600;color:var(--c-text);margin-top:2px;}
.score-bar-wrap{margin-top:8px;}
.score-bar-label{display:flex;justify-content:space-between;font-size:0.8em;color:var(--c-muted);margin-bottom:6px;}
.score-bar{height:8px;background:rgba(0,0,0,0.3);border-radius:50px;overflow:hidden;}
.score-bar-fill{height:100%;border-radius:50px;transition:width 1s ease;animation:growBar 1s ease;}
.score-bar-fill.rank-1{background:linear-gradient(90deg,#7c3aed,#a78bfa);box-shadow:0 0 12px rgba(124,58,237,0.4);}
.score-bar-fill.rank-2{background:linear-gradient(90deg,#06b6d4,#22d3ee);box-shadow:0 0 12px rgba(34,211,238,0.4);}
.score-bar-fill.rank-3{background:linear-gradient(90deg,#ec4899,#f472b6);box-shadow:0 0 12px rgba(236,72,153,0.4);}
.score-bar-fill.rank-4,.score-bar-fill.rank-5{background:linear-gradient(90deg,#666,#999);}

/* ===== Veto / Risk / Steps ===== */
.veto-item{
  background:rgba(248,113,113,0.08);border:1px solid rgba(248,113,113,0.15);
  border-left:3px solid var(--c-danger);padding:12px 16px;margin-bottom:8px;
  border-radius:10px;font-size:0.9em;transition:all 0.3s;
}
.veto-item:hover{background:rgba(248,113,113,0.12);transform:translateX(4px);}
.risk-card{
  padding:14px 16px;margin-bottom:8px;border-radius:10px;font-size:0.9em;
  transition:all 0.3s;border:1px solid;
}
.risk-card:hover{transform:translateX(4px);}
.risk-card.risk-high{background:rgba(248,113,113,0.08);border-color:rgba(248,113,113,0.15);border-left:3px solid var(--c-danger);}
.risk-card.risk-mid{background:rgba(251,191,36,0.08);border-color:rgba(251,191,36,0.15);border-left:3px solid var(--c-warn);}
.risk-card.risk-low{background:rgba(52,211,153,0.08);border-color:rgba(52,211,153,0.15);border-left:3px solid var(--c-success);}
.risk-high{color:var(--c-danger);}.risk-mid{color:var(--c-warn);}.risk-low{color:var(--c-success);}
.step-list{list-style:none;padding:0;}
.step-list li{
  padding:10px 0 10px 28px;position:relative;font-size:0.9em;color:var(--c-text);
  border-bottom:1px solid rgba(255,255,255,0.04);
}
.step-list li:last-child{border-bottom:none;}
.step-list li::before{
  content:'';position:absolute;left:0;top:14px;width:12px;height:12px;
  border-radius:50%;background:linear-gradient(135deg,var(--c-purple),var(--c-pink));
  box-shadow:0 0 8px rgba(124,58,237,0.3);
}

/* ===== Trace Timeline ===== */
.trace-timeline{position:relative;padding-left:8px;}
.trace-step{
  display:flex;gap:16px;align-items:flex-start;padding:12px 0;
  position:relative;
}
.trace-step:not(:last-child)::after{
  content:'';position:absolute;left:21px;top:44px;width:2px;height:calc(100% - 24px);
  background:linear-gradient(180deg,rgba(124,58,237,0.3),rgba(236,72,153,0.1));
}
.step-num{
  width:44px;height:44px;border-radius:14px;flex-shrink:0;
  display:flex;align-items:center;justify-content:center;
  font-weight:700;font-size:1em;color:#fff;
  background:linear-gradient(135deg,var(--c-purple),var(--c-pink));
  box-shadow:0 4px 12px rgba(124,58,237,0.2);
}
.trace-step .step-content{flex:1;padding-top:4px;}
.trace-step .step-action{font-weight:600;color:var(--c-lavender);font-size:0.95em;}
.trace-step .step-detail{color:var(--c-muted);font-size:0.82em;margin-top:2px;}

/* ===== Summary Bar ===== */
.summary-bar{
  display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px;
}
.summary-chip{
  background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);
  border-radius:50px;padding:6px 16px;font-size:0.85em;color:var(--c-muted);
}
.summary-chip strong{color:var(--c-violet);font-weight:600;}

/* ===== Error ===== */
.error-box{
  background:rgba(248,113,113,0.08);border:1px solid rgba(248,113,113,0.2);
  border-radius:14px;padding:20px;color:var(--c-danger);
  white-space:pre-wrap;font-size:0.9em;
}

/* ===== JSON Output ===== */
.json-output{
  background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.06);
  border-radius:14px;padding:18px;font-size:0.8em;
  overflow-x:auto;max-height:360px;color:rgba(255,255,255,0.4);
  font-family:'SF Mono','Fira Code','Cascadia Code',monospace;
}

/* ===== Footer ===== */
.footer{text-align:center;padding:32px 20px;color:rgba(255,255,255,0.25);font-size:0.85em;}

/* ===== Animations ===== */
@keyframes spin{to{transform:rotate(360deg);}}
@keyframes pulse{0%,100%{transform:scale(1);opacity:1;}50%{transform:scale(1.3);opacity:0.6;}}
@keyframes fadeUp{from{opacity:0;transform:translateY(24px);}to{opacity:1;transform:translateY(0);}}
@keyframes fadeDown{from{opacity:0;transform:translateY(-24px);}to{opacity:1;transform:translateY(0);}}
@keyframes growBar{from{width:0;}}
@keyframes textShimmer{0%,100%{opacity:0.7;}50%{opacity:1;}}

/* ===== Responsive ===== */
@media(max-width:768px){
  .container{padding:24px 14px;}
  .header h1{font-size:1.7em;}
  .card{padding:22px;border-radius:16px;}
  .material-grid{grid-template-columns:1fr;}
  .material-card .mc-props{grid-template-columns:1fr;}
  .btn{padding:12px 32px;font-size:1em;}
}
</style>
</head>
<body>
<div class="aurora-bg" style="position:fixed;top:0;left:0;width:100%;height:100%;z-index:-2;background:linear-gradient(135deg,#0a0a1a 0%,#1a1a3e 40%,#2d1b4e 100%);"></div>
<div class="aurora"></div>
<div class="aurora-mid"></div>
<div class="container">
  <div class="header">
    <h1>产业原材料智能选型</h1>
    <p>基于 TOPSIS 多属性决策引擎，输入需求即可智能推荐最优原材料</p>
    <div class="badge-row">
      <span class="header-badge">TOPSIS 排序</span>
      <span class="header-badge">混合检索</span>
      <span class="header-badge">风险分析</span>
      <span class="header-badge">否决检查</span>
    </div>
  </div>

  <div class="card">
    <h2><span class="icon">+</span> 输入材料需求</h2>
    <textarea id="inputText" placeholder="请输入自然语言描述的材料需求，例如：&#10;电动汽车电池包壳体，密度&lt;2.0 g/cm3，拉伸强度&gt;300 MPa，UL94 V-0，成本&lt;$20/kg，RoHS合规，国内采购">汽车结构件，密度&lt;2.0 g/cm3，拉伸强度&gt;150 MPa，成本&lt;$15/kg，RoHS合规，国内采购</textarea>
    <div class="examples">
      <span class="example-tag" onclick="fillExample(this)">电池包壳体</span>
      <span class="example-tag" onclick="fillExample(this)">LED散热器</span>
      <span class="example-tag" onclick="fillExample(this)">航空结构件</span>
      <span class="example-tag" onclick="fillExample(this)">化工管道</span>
    </div>
    <div class="btn-row">
      <button class="btn" onclick="runPipeline()">开始选型</button>
    </div>
  </div>

  <div class="loading" id="loading">
    <div class="loader-rings"><div></div><div></div><div></div><div></div></div>
    <p>AI 正在分析材料需求...</p>
  </div>

  <div class="result" id="result">
    <div class="card" id="resultContent"></div>
  </div>

  <div class="footer">产业原材料智能选型 Skill Demo &copy; 2026</div>
</div>

<script>
var examples = {
  '电池包壳体': '电动汽车电池包壳体，密度<2.5 g/cm3，拉伸强度>100 MPa，UL94 V-0，成本<$30/kg，RoHS合规，国内采购',
  'LED散热器': 'LED灯具散热器，导热系数>100 W/mK，密度<3.0 g/cm3，成本<$10/kg，加工性能好，批量生产',
  '航空结构件': '航空座椅结构件，拉伸强度>500 MPa，密度<2.0 g/cm3，成本<$40/kg',
  '化工管道': '化工输送管道，耐腐蚀，拉伸强度>200 MPa，成本<$10/kg，国内采购'
};

function fillExample(el) {
  var key = el.textContent.trim();
  if (examples[key]) {
    document.getElementById('inputText').value = examples[key];
  }
}

async function runPipeline() {
  var input = document.getElementById('inputText').value.trim();
  if (!input) { alert('请先输入材料需求'); return; }

  var loading = document.getElementById('loading');
  var result = document.getElementById('result');
  result.classList.remove('show');
  loading.classList.add('show');

  try {
    var resp = await fetch('/api/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_input: input, top_n: 5 })
    });
    var data = await resp.json();
    renderResult(data);
  } catch (e) {
    document.getElementById('resultContent').innerHTML =
      '<div class="error-box">请求失败: ' + e.message + '</div>';
  } finally {
    loading.classList.remove('show');
    result.classList.add('show');
  }
}

function gp(m, k) {
  try {
    return m.key_properties && m.key_properties[k] !== undefined
      ? m.key_properties[k]
      : (m[k] !== undefined ? m[k] : '-');
  } catch (e) { return '-'; }
}

function renderResult(data) {
  var html = '';
  if (data.error) {
    html += '<div class="error-box">' + data.error + '</div>';
    document.getElementById('resultContent').innerHTML = html;
    return;
  }

  html += '<h2><span class="icon">*</span> 选型结果</h2>';

  // 应用场景
  html += '<p style="margin-bottom:16px;color:var(--c-muted);">应用场景: <strong style="color:var(--c-violet);font-size:1.05em;">' + (data.application || '未指定') + '</strong></p>';

  // 摘要
  if (data.summary) {
    html += '<div class="summary-bar">';
    html += '<span class="summary-chip">候选 <strong>' + data.summary.total_candidates + '</strong></span>';
    html += '<span class="summary-chip">否决 <strong>' + data.summary.vetoed_count + '</strong></span>';
    html += '<span class="summary-chip">推荐 <strong>' + (data.summary.top_recommendation || '无') + '</strong></span>';
    html += '<span class="summary-chip">置信度 <strong>' + (data.summary.recommendation_confidence || '中') + '</strong></span>';
    html += '</div>';
  }

  // 推荐材料卡片网格
  if (data.ranked_materials && data.ranked_materials.length > 0) {
    html += '<div class="result-section"><h3>推荐材料排名</h3><div class="material-grid">';
    data.ranked_materials.forEach(function(m, i) {
      var rank = i + 1;
      var rc = 'rank-' + rank;
      var score = m.topsis_score !== undefined ? m.topsis_score : 0;
      var scorePct = Math.round(score * 100);
      html += '<div class="material-card ' + rc + '">';
      html += '<div class="mc-header">';
      html += '<div class="rank-badge ' + rc + '">' + rank + '</div>';
      html += '<div><div class="mc-name">' + (m.grade || '-') + '</div>';
      html += '<span class="mc-cat">' + (m.category || '-') + '</span></div>';
      html += '</div>';
      html += '<div class="mc-props">';
      html += '<div class="mc-prop"><div class="mc-label">密度 (g/cm3)</div><div class="mc-value">' + gp(m, 'density') + '</div></div>';
      html += '<div class="mc-prop"><div class="mc-label">拉伸强度 (MPa)</div><div class="mc-value">' + gp(m, 'tensile_strength') + '</div></div>';
      html += '<div class="mc-prop"><div class="mc-label">导热系数 (W/mK)</div><div class="mc-value">' + gp(m, 'thermal_conductivity') + '</div></div>';
      html += '<div class="mc-prop"><div class="mc-label">成本 ($/kg)</div><div class="mc-value">' + gp(m, 'cost_per_kg') + '</div></div>';
      html += '</div>';
      html += '<div class="score-bar-wrap">';
      html += '<div class="score-bar-label"><span>TOPSIS 得分</span><span>' + score.toFixed(4) + ' (' + scorePct + '%)</span></div>';
      html += '<div class="score-bar"><div class="score-bar-fill ' + rc + '" style="width:' + scorePct + '%"></div></div>';
      html += '</div>';
      html += '</div>';
    });
    html += '</div></div>';
  } else {
    html += '<div class="result-section"><p style="color:var(--c-danger);">未找到匹配的材料</p></div>';
  }

  // 被否决的材料
  if (data.veto_details && data.veto_details.length > 0) {
    html += '<div class="result-section"><h3>被否决的材料</h3>';
    data.veto_details.forEach(function(v) {
      html += '<div class="veto-item"><strong>' + (v.grade || v.material_id || '-') + '</strong>: ' + (v.veto_reason || v.requirement || '不满足约束条件') + '</div>';
    });
    html += '</div>';
  }

  // 风险分析
  if (data.risk_analysis && data.risk_analysis.length > 0) {
    html += '<div class="result-section"><h3>适配风险分析</h3>';
    data.risk_analysis.forEach(function(r) {
      var level = (r.overall_risk_level || 'low').toLowerCase();
      var isHigh = (level === 'high' || level === '高');
      var isMid = (level === 'medium' || level === 'mid' || level === '中');
      var cls = isHigh ? 'risk-high' : isMid ? 'risk-mid' : 'risk-low';
      var risks = [];
      if (r.process_risks) r.process_risks.forEach(function(p) { risks.push(p.risk); });
      if (r.supply_risks) r.supply_risks.forEach(function(p) { risks.push(p.risk); });
      if (r.data_quality_risks) r.data_quality_risks.forEach(function(p) { risks.push(p.risk); });
      var desc = risks.join('; ') || 'N/A';
      var levelLabel = isHigh ? '高' : isMid ? '中' : '低';
      html += '<div class="risk-card ' + cls + '"><span class="' + cls + '">[' + levelLabel + ']</span> <strong>' + (r.grade || '-') + '</strong>: ' + desc + '</div>';
    });
    html += '</div>';
  }

  // 验证计划
  if (data.next_steps && data.next_steps.length > 0) {
    html += '<div class="result-section"><h3>验证计划建议</h3><ul class="step-list">';
    data.next_steps.forEach(function(s) {
      html += '<li>' + s + '</li>';
    });
    html += '</ul></div>';
  }

  // 处理过程时间线
  if (data.trace && data.trace.steps) {
    html += '<div class="result-section"><h3>处理过程</h3><div class="trace-timeline">';
    data.trace.steps.forEach(function(s) {
      html += '<div class="trace-step">';
      html += '<div class="step-num">' + s.step + '</div>';
      html += '<div class="step-content">';
      html += '<div class="step-action">' + (s.action || '') + '</div>';
      if (s.candidates_count !== undefined) {
        html += '<div class="step-detail">检索到 ' + s.candidates_count + ' 条候选</div>';
      }
      if (s.passed_count !== undefined) {
        html += '<div class="step-detail">通过 ' + s.passed_count + ' / 否决 ' + (s.vetoed_count || 0) + '</div>';
      }
      html += '</div></div>';
    });
    html += '</div></div>';
  }

  // 原始 JSON
  html += '<div class="result-section"><h3>原始 JSON 输出</h3>';
  html += '<pre class="json-output">' + JSON.stringify(data, null, 2) + '</pre></div>';

  document.getElementById('resultContent').innerHTML = html;
  window.scrollTo({ top: document.getElementById('result').offsetTop - 20, behavior: 'smooth' });
}
</script>
</body>
</html>"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/select', methods=['POST'])
def api_select():
    try:
        req = request.get_json(force=True)
        user_input = req.get('user_input', '')
        top_n = int(req.get('top_n', 5))

        if not user_input.strip():
            return jsonify({"error": "请输入材料需求描述"})

        pipe = get_pipeline()
        result = pipe.run(user_input, {"top_n": top_n})

        # 直接返回 pipeline 完整结果，前端适配实际结构
        return jsonify(result)

    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        })


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=False)