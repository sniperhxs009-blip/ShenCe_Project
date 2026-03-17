# ========== 调试定位：运行 streamlit run app.py 后，看终端打印停在哪一步 ==========
import sys
def _dbg(msg):
    print(f">>> [{msg}]", flush=True)
_dbg("1-开始导入")

import streamlit as st
_dbg("2-streamlit")
from openai import OpenAI
_dbg("3-openai")
import json
import os
_dbg("4-json,os")
import plotly.graph_objects as go
_dbg("5-plotly")
import requests
import random
from datetime import datetime
import pandas as pd
_dbg("6-pandas")
from fpdf import FPDF
import io
import time
import re
import math
_dbg("7-基础库完成")

# PDF 解析：优先 PyMuPDF（质量更好），其次 pypdf
PDF_AVAILABLE = False
PYMUPDF_AVAILABLE = False
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
    PDF_AVAILABLE = True
except ImportError:
    try:
        from pypdf import PdfReader
        PDF_AVAILABLE = True
    except ImportError:
        PDF_AVAILABLE = False

# Word 解析（可选依赖）
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# OCR 兜底（扫描版 PDF 文字极少时启用）
OCR_AVAILABLE = False
try:
    import pytesseract
    from pdf2image import convert_from_bytes
    OCR_AVAILABLE = True
except ImportError:
    pass
_dbg("8-PDF/DOCX可选依赖")

# --- 页面配置 ---
st.set_page_config(page_title="SHENCE 3.0 | 社会演化仿真旗舰版", layout="wide", initial_sidebar_state="expanded")
_dbg("9-set_page_config")

# 恢复接近 Streamlit 默认的浅色背景，只保留少量卡片样式
st.markdown("""
<style>
.block-container { max-width: 98% !important; padding: 1rem 2% !important; }
.metric-card { 
    background-color: #f8f9fa; padding: 20px; border-radius: 10px; 
    border: 1px solid #e0e0e0; text-align: center;
}
.logic-box { 
    background-color: #f8f9fa; padding: 25px; border-left: 10px solid #58a6ff; 
    border-radius: 6px; margin: 20px 0; font-family: 'Consolas', monospace; 
    color: #555555; border: 1px solid #e0e0e0;
}
.report-card { 
    background-color: #ffffff; padding: 40px; border-radius: 15px; color: #1a1a1a !important;
    border-top: 15px solid #1f6feb; box-shadow: 0 10px 40px rgba(0,0,0,0.05); 
}
.agent-card {
    background-color: #ffffff; padding:15px; border-radius:10px; min-height:260px;
    border:1px solid #e0e0e0; margin-bottom:10px;
}
.resource-card {
    background-color: #ffffff; padding:15px; border-radius:10px;
    border:1px solid #e0e0e0; margin-bottom:10px;
}
</style>
""", unsafe_allow_html=True)
_dbg("10-CSS样式")

# --- 侧边栏 API ---
st.sidebar.header("🔑 API 配置")
openai_key = st.sidebar.text_input("DeepSeek API Key（兼容 OpenAI SDK）", type="password")
base_url = st.sidebar.text_input("Base URL", value="https://api.deepseek.com/v1")
serper_key = st.sidebar.text_input("Serper API Key", type="password")

client = None
if openai_key:
    client = OpenAI(api_key=openai_key, base_url=base_url)
_dbg("11-侧栏API区")

# --- 仿真模式与可复现性 ---
st.sidebar.header("🧪 仿真模式")
sim_mode = st.sidebar.selectbox(
    "模式",
    ["高保真（机制内核 + 可审计）", "叙事（AI 主导）"],
    help="高保真模式：指标与资源由机制模型计算，AI 仅做文字解读并受审计约束；叙事模式：主要由模型生成并辅以随机扰动。"
)
seed = st.sidebar.number_input("随机种子（可复现）", min_value=0, max_value=10_000_000, value=2026, step=1)
force_crisis_mode = st.sidebar.checkbox(
    "强制危机推演模式",
    value=False,
    help="勾选后忽略智能判断，始终按政府/社会危机推演流程执行（即使输入是续写小说等）"
)

# --- 高保真参数校准面板 ---
hf_default = {
    "shock_anxiety_k": 1.0,
    "shock_gap_k": 1.0,
    "shock_risk_k": 1.0,
    "shock_admin_k": 1.0,
    "coupling_anxiety_k": 1.0,
    "coupling_risk_k": 1.0,
    "trigger_risk": 80,
    "trigger_gap": 75,
    "trigger_admin": 25,
    "min_infra_to_execute": 25,
    "step_hours": 12.0,
    "decay_scale_panic": 0.6,
    "decay_scale_supply_shock": 1.2,
    "decay_scale_power_outage": 1.0,
    "decay_scale_comms_outage": 0.8,
    "decay_scale_finance_risk": 1.1,
    "decay_scale_governance_stress": 0.9,
}
with st.sidebar.expander("🎛️ 高保真参数校准（进阶）", expanded=False):
    st.caption("这些参数只影响高保真模式，用于调参/回放对比。")
    shock_anxiety_k = st.slider("冲击→焦虑 系数", 0.0, 2.0, float(hf_default["shock_anxiety_k"]), 0.05)
    shock_gap_k = st.slider("冲击→缺口 系数", 0.0, 2.0, float(hf_default["shock_gap_k"]), 0.05)
    shock_risk_k = st.slider("冲击→动荡 系数", 0.0, 2.0, float(hf_default["shock_risk_k"]), 0.05)
    shock_admin_k = st.slider("冲击→行政 系数", 0.0, 2.0, float(hf_default["shock_admin_k"]), 0.05)
    coupling_anxiety_k = st.slider("耦合→焦虑 系数", 0.0, 2.0, float(hf_default["coupling_anxiety_k"]), 0.05)
    coupling_risk_k = st.slider("耦合→动荡 系数", 0.0, 2.0, float(hf_default["coupling_risk_k"]), 0.05)
    trigger_risk = st.slider("动荡阈值触发", 50, 95, int(hf_default["trigger_risk"]), 1)
    trigger_gap = st.slider("缺口阈值触发", 50, 95, int(hf_default["trigger_gap"]), 1)
    trigger_admin = st.slider("低行政阈值触发", 5, 50, int(hf_default["trigger_admin"]), 1)
    min_infra_to_execute = st.slider("执行最低基础设施阈值", 0, 60, int(hf_default["min_infra_to_execute"]), 1)
    step_hours = st.slider("每步代表小时数", 1.0, 48.0, float(hf_default["step_hours"]), 1.0, help="用于把证据持续时间换算为衰减曲线；相同证据下，步长越大衰减越快。")
    auto_steps_by_duration = st.checkbox("按总时长自动计算步数（高保真）", value=False, help="开启后，高保真模式将忽略上方“演化步数”滑块，改用总时长/每步小时数计算步数。")
    dur_cols = st.columns(2)
    total_duration_hours = dur_cols[0].number_input("总推演时长（小时）", min_value=0, max_value=24*60, value=0, step=12, help="0 表示不启用；启用后步数=ceil(总时长/每步小时数)。")
    total_duration_days = dur_cols[1].number_input("总推演时长（天）", min_value=0.0, max_value=60.0, value=0.0, step=0.5, help="可选：用天输入总时长；若>0 将优先于“小时”。")
    st.caption("起止时间（可选，用于昼夜节律与审计对齐）")
    time_cols = st.columns(2)
    start_time_str = time_cols[0].text_input("开始时间（YYYY-MM-DD HH:MM）", value="", placeholder="如：2026-03-17 08:00")
    end_time_str = time_cols[1].text_input("结束时间（YYYY-MM-DD HH:MM）", value="", placeholder="如：2026-03-19 20:00")

    circadian = st.checkbox("启用昼夜节律（高保真）", value=True, help="启用后，每一步会映射到具体时刻，夜间焦虑/动荡更敏感，白天执行更强。")
    night_anxiety_boost = st.slider("夜间焦虑增益", 0.0, 1.0, 0.25, 0.05)
    night_risk_boost = st.slider("夜间动荡增益", 0.0, 1.0, 0.20, 0.05)
    night_exec_penalty = st.slider("夜间执行折扣", 0.0, 1.0, 0.15, 0.05)
    st.caption("因子衰减倍率（>1 衰减更慢，<1 衰减更快）")
    decay_scale_panic = st.slider("恐慌/舆情 衰减倍率", 0.2, 2.5, float(hf_default["decay_scale_panic"]), 0.05)
    decay_scale_supply_shock = st.slider("供应链冲击 衰减倍率", 0.2, 2.5, float(hf_default["decay_scale_supply_shock"]), 0.05)
    decay_scale_power_outage = st.slider("电力故障 衰减倍率", 0.2, 2.5, float(hf_default["decay_scale_power_outage"]), 0.05)
    decay_scale_comms_outage = st.slider("通信故障 衰减倍率", 0.2, 2.5, float(hf_default["decay_scale_comms_outage"]), 0.05)
    decay_scale_finance_risk = st.slider("金融风险 衰减倍率", 0.2, 2.5, float(hf_default["decay_scale_finance_risk"]), 0.05)
    decay_scale_governance_stress = st.slider("治理压力 衰减倍率", 0.2, 2.5, float(hf_default["decay_scale_governance_stress"]), 0.05)

hf_params = {
    "shock_anxiety_k": shock_anxiety_k,
    "shock_gap_k": shock_gap_k,
    "shock_risk_k": shock_risk_k,
    "shock_admin_k": shock_admin_k,
    "coupling_anxiety_k": coupling_anxiety_k,
    "coupling_risk_k": coupling_risk_k,
    "trigger_risk": trigger_risk,
    "trigger_gap": trigger_gap,
    "trigger_admin": trigger_admin,
    "min_infra_to_execute": min_infra_to_execute,
    "step_hours": step_hours,
    "auto_steps_by_duration": bool(auto_steps_by_duration),
    "total_duration_hours": int(total_duration_hours),
    "total_duration_days": float(total_duration_days),
    "start_time_str": start_time_str,
    "end_time_str": end_time_str,
    "circadian": bool(circadian),
    "night_anxiety_boost": float(night_anxiety_boost),
    "night_risk_boost": float(night_risk_boost),
    "night_exec_penalty": float(night_exec_penalty),
    "decay_scales": {
        "panic": decay_scale_panic,
        "supply_shock": decay_scale_supply_shock,
        "power_outage": decay_scale_power_outage,
        "comms_outage": decay_scale_comms_outage,
        "finance_risk": decay_scale_finance_risk,
        "governance_stress": decay_scale_governance_stress,
    },
}
_dbg("12-高保真参数")

# --- 会话状态 ---
init_keys = [
    "event", "facts", "matrix_history", "timeline", "report",
    "agents", "resources", "swan", "causal_chain", "playback_index",
    "reset_requested", "autoplay_running", "scenario_name",
    "audit_log", "evidence_items", "infra_history", "hf_params",
    "evidence_factor_map",
    "decay_schedule", "time_axis",
    "uploaded_doc_text", "sim_phase", "stepping_current_step", "stepping_effective_steps",
    "stepping_matrix", "stepping_resources", "stepping_infra", "stepping_factors",
    "perspective_chat_history",
    "scenario_branches", "current_branch_view", "entity_graph", "history_scenarios",
    "doc_subject",
]
for k in init_keys:
    if k not in st.session_state:
        if k in ["timeline", "matrix_history", "audit_log", "evidence_items", "infra_history", "perspective_chat_history", "scenario_branches", "history_scenarios"]:
            st.session_state[k] = []
        elif k in ["history_scenarios"]:
            st.session_state[k] = []
        elif k in ["reset_requested", "autoplay_running"]:
            st.session_state[k] = False
        elif k in ["stepping_current_step", "stepping_effective_steps"]:
            st.session_state[k] = 0
        elif k == "sim_phase":
            st.session_state[k] = ""
        elif k == "doc_subject":
            st.session_state[k] = {}
        else:
            st.session_state[k] = ""

st.session_state.hf_params = hf_params

if st.session_state.get("playback_index") is None or not isinstance(st.session_state.get("playback_index"), int):
    st.session_state.playback_index = 0
_dbg("13-会话状态初始化")

# --- 文档解析（种子上传）---
def parse_uploaded_document(uploaded_file) -> str:
    """解析上传的 PDF、TXT、DOCX、MD，返回纯文本。PDF 优先 PyMuPDF 以提升提取质量。"""
    if not uploaded_file:
        return ""
    try:
        name = (uploaded_file.name or "").lower()
        raw = uploaded_file.read()
        if name.endswith(".txt"):
            return raw.decode("utf-8", errors="replace")[:25000]
        if name.endswith(".md") or name.endswith(".markdown"):
            return raw.decode("utf-8", errors="replace")[:25000]
        if name.endswith(".pdf") and PDF_AVAILABLE:
            text_parts = []
            if PYMUPDF_AVAILABLE:
                try:
                    doc = fitz.open(stream=raw, filetype="pdf")
                    for i in range(min(doc.page_count, 35)):
                        page = doc.load_page(i)
                        t = page.get_text("text", sort=True) or ""
                        if t.strip():
                            text_parts.append(t)
                    doc.close()
                except Exception:
                    pass
            if not text_parts and PDF_AVAILABLE:
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(io.BytesIO(raw))
                    for i, p in enumerate(reader.pages):
                        if i >= 35:
                            break
                        t = p.extract_text() or ""
                        if t.strip():
                            text_parts.append(t)
                except Exception:
                    pass
            out = "\n\n".join(text_parts)
            # OCR 兜底：文字极少（如扫描版）时尝试 OCR 前 5 页
            if OCR_AVAILABLE and len(out.strip()) < 500:
                try:
                    images = convert_from_bytes(raw, first_page=1, last_page=min(5, 35), dpi=150)
                    ocr_parts = []
                    for img in images:
                        ocr_text = pytesseract.image_to_string(img, lang="chi_sim+eng")
                        if ocr_text.strip():
                            ocr_parts.append(ocr_text)
                    if ocr_parts:
                        out = "\n\n".join(ocr_parts)[:25000]
                except Exception:
                    pass
            return out[:25000] if out else ""
        if name.endswith(".pdf") and not PDF_AVAILABLE:
            return "[PDF 解析需要安装 pypdf 或 pymupdf：pip install pymupdf]"
        if (name.endswith(".docx") or name.endswith(".doc")) and DOCX_AVAILABLE:
            doc = DocxDocument(io.BytesIO(raw))
            parts = [p.text for p in doc.paragraphs]
            return "\n".join(parts)[:25000]
        if (name.endswith(".docx") or name.endswith(".doc")) and not DOCX_AVAILABLE:
            return "[Word 解析需要安装 python-docx：pip install python-docx]"
    except Exception as e:
        return f"[文档解析异常] {str(e)[:80]}"
    return ""

def fetch_url_as_seed(url: str) -> str:
    """抓取网页内容作为种子，返回纯文本。"""
    if not url or not url.strip():
        return ""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (compatible; SHENCE/1.0)"})
        r.raise_for_status()
        html = r.text
        text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.I)
        text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:12000]
    except Exception as e:
        return f"[URL 抓取异常] {str(e)[:80]}"

def _heuristic_extract_subject(text: str) -> dict:
    """无 API 时用正则从文档前 5000 字提取。"""
    t = (text or "")[:5000]
    out = {"company": "", "year": "", "org": "", "doc_type": "", "key_points": ""}
    # 企业名：多种模式，取第一个匹配
    patterns = [
        r"([\u4e00-\u9fa5A-Za-z0-9]{2,30}(?:股份有限公司|集团有限公司|有限公司|实业有限公司|科技股份有限公司))",
        r"([\u4e00-\u9fa5]{2,20}(?:人民政府|市政府|发改委|工信部|财政部))",
    ]
    for pat in patterns:
        m = re.search(pat, t)
        if m:
            out["company"] = out["org"] = m.group(1).strip()
            break
    for y in re.findall(r"20[12][0-9]\s*年(?:度)?|二[〇零○]二[〇一二三四五六七八九]\s*年", t):
        digit = re.search(r"20[12][0-9]", y)
        if digit:
            out["year"] = digit.group(0) + "年"
            break
        if "二" in y:
            cn = {"〇":"0","零":"0","○":"0","一":"1","二":"2","三":"3","四":"4","五":"5","六":"6","七":"7","八":"8","九":"9"}
            d = "".join(cn.get(c,c) for c in y if c in cn)
            if len(d) == 1:
                out["year"] = "202" + d + "年"
                break
    if "政策" in t or "办法" in t or "通知" in t or "条例" in t:
        out["doc_type"] = "政策文件"
    elif "年报" in t or "年度报告" in t or "财务" in t:
        out["doc_type"] = "企业报告"
    out["key_points"] = t[:500].replace("\n", " ").strip()[:200]
    return out

def document_understanding(doc_text: str, api_client) -> dict:
    """
    专职文档理解：仅传入文档，无其他上下文。
    提取：主体/发文机关/企业名、日期/年度、文档类型、核心要点。
    """
    if not doc_text or doc_text.startswith("["):
        return {}
    # 企业名、年度多在文档前部，优先用前 6000 字
    sample = doc_text[:6000]
    if api_client:
        prompt = f"""任务：从以下文档中提取信息。org 和 year 必须是文档中出现的原文，逐字复制，不得改动。

文档内容：
---
{sample}
---

要求：
1. org：主体全称（企业名或发文机关），必须在文档中能找到完全相同的字符串
2. year：日期/年度，必须在文档中能找到完全相同的字符串
3. doc_type：文档类型（年报/财务报告/政策文件/通知等）
4. key_points：核心要点，100字内，仅基于文档内容

若文档中未出现则填空字符串。只输出JSON：{{"org":"","year":"","doc_type":"","key_points":""}}"""
        try:
            res = api_client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                timeout=35,
            )
            j = safe_json(res.choices[0].message.content)
            org = str(j.get("org") or "").strip()[:80]
            year = str(j.get("year") or "").strip()[:30]
            # 校验：提取结果必须在文档中出现，否则丢弃
            if org and org not in doc_text[:10000]:
                org = ""
            year_digits = re.sub(r"[^\d]","", year) if year else ""
            if year and year not in doc_text[:10000] and (not year_digits or year_digits not in doc_text[:10000]):
                year = ""
            out = {
                "company": org,
                "year": year,
                "org": org,
                "doc_type": str(j.get("doc_type") or "").strip()[:40],
                "key_points": str(j.get("key_points") or "").strip()[:300],
            }
            if not out["company"] and not out["year"]:
                return _heuristic_extract_subject(doc_text)
            return out
        except Exception:
            return _heuristic_extract_subject(doc_text)
    return _heuristic_extract_subject(doc_text)

# --- 核心工具函数 ---
def safe_json(res):
    try:
        return json.loads(res)
    except:
        fixed = res[res.find("{"):res.rfind("}")+1]
        try:
            return json.loads(fixed)
        except:
            return {
                "official": "数据异常", "citizen": "数据异常",
                "media": "数据异常", "audit": "数据异常"
            }

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

def clamp100(x: float) -> int:
    return int(max(0, min(100, round(float(x)))))

def _url_host(url: str) -> str:
    try:
        # extremely small parser; avoids extra deps
        u = (url or "").strip().lower()
        u = u.replace("https://", "").replace("http://", "")
        return u.split("/")[0]
    except Exception:
        return ""

def score_evidence_strength(item: dict) -> dict:
    """
    证据强度评分（0..1），用于因子权重（减少“随便命中关键词就很强”的问题）。
    这是启发式规则：可复现、可审计、可逐步替换为更严谨的打分器。
    """
    title = (item.get("title") or "").strip()
    snippet = (item.get("snippet") or "").strip()
    link = (item.get("link") or "").strip()
    host = _url_host(link)
    text = f"{title} {snippet}"

    length_score = clamp01(len(snippet) / 220.0)  # 片段越长信息越多
    has_numbers = 1.0 if re.search(r"\d", text) else 0.0
    has_time = 1.0 if re.search(r"(20\d{2}|19\d{2}|48\s*小时|7\s*天|周|月)", text) else 0.0

    # 域名可信度（保守：只给少量加分，避免“域名决定真伪”）
    host_bonus = 0.0
    if any(x in host for x in ["gov", "edu", "who.int", "un.org", "worldbank.org", "oecd.org", "imf.org"]):
        host_bonus = 0.15
    elif any(x in host for x in ["wikipedia.org", "reuters.com", "bbc.", "nytimes.com"]):
        host_bonus = 0.10

    strength = clamp01(0.15 + 0.35 * length_score + 0.20 * has_numbers + 0.15 * has_time + host_bonus)
    return {
        "host": host,
        "strength": round(float(strength), 2),
        "signals": {
            "length_score": round(float(length_score), 2),
            "has_numbers": bool(has_numbers),
            "has_time": bool(has_time),
            "host_bonus": round(float(host_bonus), 2),
        },
    }

def extract_evidence_struct(item: dict) -> dict:
    """
    结构化抽取（确定性规则）：事件类型/时间尺度/主题标签/数值片段。
    """
    text = f"{item.get('title','')} {item.get('snippet','')}".lower()
    tags = []
    if any(k in text for k in ["停电", "断电", "blackout", "power outage"]):
        tags.append("电力故障")
    if any(k in text for k in ["断网", "通信", "internet outage", "telecom"]):
        tags.append("通信故障")
    if any(k in text for k in ["供应链", "物流", "运输", "shortage", "supply chain"]):
        tags.append("供应链冲击")
    if any(k in text for k in ["挤兑", "bank run", "liquidity", "兑付"]):
        tags.append("金融风险")
    if any(k in text for k in ["恐慌", "抢购", "hoard", "panic", "rumor", "谣言"]):
        tags.append("舆情/恐慌")
    if any(k in text for k in ["宵禁", "curfew", "封控", "lockdown"]):
        tags.append("强制管控")

    nums = re.findall(r"(?:20\d{2}|19\d{2}|\d+\s*(?:小时|天|周|%|万人|万|亿|千|百))", item.get("snippet","") or "")
    time_scale = "未知"
    if re.search(r"48\s*小时|\d+\s*小时", text):
        time_scale = "小时级"
    elif re.search(r"\d+\s*天|周", text):
        time_scale = "天-周级"
    elif re.search(r"月|季度|年|20\d{2}|19\d{2}", text):
        time_scale = "月-年级"

    # 持续时间粗抽取（用于冲击衰减）
    duration_hours = None
    m_h = re.search(r"(\d+)\s*小时", text)
    m_d = re.search(r"(\d+)\s*天", text)
    m_w = re.search(r"(\d+)\s*周", text)
    if m_h:
        duration_hours = int(m_h.group(1))
    elif m_d:
        duration_hours = int(m_d.group(1)) * 24
    elif m_w:
        duration_hours = int(m_w.group(1)) * 24 * 7

    return {
        "tags": tags,
        "time_scale": time_scale,
        "numbers": nums[:6],
        "duration_hours": duration_hours,
    }

def compute_decay_schedule(evidence_items: list[dict], steps: int, step_hours: float, decay_scales: dict) -> dict:
    """
    根据证据中的持续时间/时间尺度，为各冲击因子生成随步数衰减的 multiplier（0..1）。
    规则：half_life_steps 与持续时间正相关；若未知则给中等半衰期。
    """
    # 从证据里估计一个总体持续时间（小时）
    durations = [it.get("duration_hours") for it in (evidence_items or []) if isinstance(it.get("duration_hours"), int)]
    if durations:
        dur_h = sorted(durations)[len(durations) // 2]  # 中位数
    else:
        # 用 time_scale 兜底
        scales = [it.get("time_scale") for it in (evidence_items or []) if it.get("time_scale")]
        if "小时级" in scales:
            dur_h = 36
        elif "天-周级" in scales:
            dur_h = 24 * 5
        elif "月-年级" in scales:
            dur_h = 24 * 30
        else:
            dur_h = 24 * 3

    # 将持续时间映射到半衰期（步）
    step_hours = float(step_hours or 12.0)
    dur_steps = max(1.0, dur_h / step_hours)
    half_life = max(1.0, dur_steps / 2.0)

    def decay(t: int) -> float:
        # t 从 1..steps；t 越大 multiplier 越小
        # multiplier = 0.5 ** ((t-1)/half_life)
        return float(0.5 ** ((max(0, t - 1)) / half_life))

    # 证据 tags 自动微调：若证据明确包含某类故障，对应因子半衰期更长（衰减更慢）
    tags = []
    for it in evidence_items or []:
        tags += (it.get("tags") or [])
    tags = list({t for t in tags if t})

    scales = decay_scales or {}
    def factor_half_life(f: str) -> float:
        s = float(scales.get(f, 1.0))
        boost = 1.0
        if f == "power_outage" and "电力故障" in tags:
            boost = 1.15
        if f == "comms_outage" and "通信故障" in tags:
            boost = 1.10
        if f == "supply_shock" and "供应链冲击" in tags:
            boost = 1.20
        if f == "finance_risk" and "金融风险" in tags:
            boost = 1.15
        if f == "panic" and "舆情/恐慌" in tags:
            boost = 0.95  # 舆情通常衰减更快一些
        return max(1.0, half_life * s * boost)

    schedule = {}
    for f in ["supply_shock", "power_outage", "comms_outage", "panic", "finance_risk", "governance_stress"]:
        hl = factor_half_life(f)
        schedule[f] = {t: round(float(0.5 ** (max(0, t - 1) / hl)), 3) for t in range(1, steps + 1)}
    schedule["_meta"] = {
        "duration_hours_est": int(dur_h),
        "step_hours": step_hours,
        "base_half_life_steps": round(float(half_life), 2),
        "factor_half_life_steps": {f: round(float(factor_half_life(f)), 2) for f in ["supply_shock","power_outage","comms_outage","panic","finance_risk","governance_stress"]},
        "tags_seen": tags,
    }
    return schedule

def parse_dt(s: str):
    try:
        s = (s or "").strip()
        if not s:
            return None
        return datetime.strptime(s, "%Y-%m-%d %H:%M")
    except Exception:
        return None

def build_time_axis(steps: int, step_hours: float, hf_params: dict) -> dict:
    """
    为每一步构建时间轴：step -> timestamp/时段标签。
    若提供 start/end，则以 start 为基准；否则仅生成“第N步/第N小时”。
    """
    hp = hf_params or {}
    sh = float(step_hours or 12.0)
    start_dt = parse_dt(hp.get("start_time_str", ""))
    end_dt = parse_dt(hp.get("end_time_str", ""))
    axis = {"start": None, "end": None, "step_hours": sh, "steps": int(steps), "points": {}}

    if start_dt and end_dt and end_dt > start_dt:
        # 若给了起止时间，使用真实跨度来微调 step_hours（保持不删原：只影响时间轴展示与昼夜节律）
        total_h = (end_dt - start_dt).total_seconds() / 3600.0
        sh = max(1.0, total_h / max(1, steps))
        axis["step_hours"] = sh
        axis["start"] = start_dt.strftime("%Y-%m-%d %H:%M")
        axis["end"] = end_dt.strftime("%Y-%m-%d %H:%M")
    elif start_dt:
        axis["start"] = start_dt.strftime("%Y-%m-%d %H:%M")

    for i in range(1, int(steps) + 1):
        if start_dt:
            t = start_dt + pd.Timedelta(hours=sh * (i - 1))
            hour = int(t.hour)
            is_night = bool(hour < 6 or hour >= 20)
            axis["points"][i] = {
                "ts": t.strftime("%Y-%m-%d %H:%M"),
                "hour": hour,
                "is_night": is_night,
            }
        else:
            axis["points"][i] = {"ts": None, "hour": None, "is_night": None}
    return axis

# --- 动态展示名称池：根据事件语义随机选择，体现“像真人分析”的灵活度 ---
RESOURCE_DISPLAY_POOLS = {
    "警力": ["警力", "消防力量", "救援队伍", "安保力量", "武警", "志愿者队伍", "秩序维护力量", "应急响应队", "治安力量", "抢险队伍", "维稳力量", "疏散引导队"],
    "医疗": ["医疗资源", "医护力量", "救护能力", "急救储备", "药品供应", "病床容量", "防疫物资", "医疗机构", "急救车辆", "医护梯队", "医疗保障", "卫生应急"],
    "物资": ["物资储备", "食品供应", "饮用水", "应急物资", "救灾物资", "生活必需品", "粮油储备", "救灾包", "储备粮", "应急装备", "补给物资", "生活保障"],
    "电力": ["电力供应", "能源储备", "供电能力", "燃油储备", "应急电源", "发电能力", "燃料储备", "电力保障", "备用电力", "能源调度", "供电设施", "发电容量"],
    "通信": ["通信保障", "网络覆盖", "信息传播", "广播系统", "联络能力", "通信能力", "互联网接入", "移动网络", "信息基础设施", "通信设施", "联络通道", "信息渠道"],
    "交通": ["交通运力", "物流能力", "运输保障", "道路通行", "配送能力", "交通管制", "疏散通道", "运输网络", "物流通道", "交通保障", "运力储备", "路网状况"],
}
INFRA_DISPLAY_POOLS = {
    "电力": ["电力供应网", "供电网络", "电网系统", "能源基础设施", "配电系统", "电力设施", "供电体系", "输电网络", "电网", "供电保障"],
    "通信": ["通信网络", "互联网", "移动网络", "信息基础设施", "通信设施", "网络接入", "通信系统", "信息网络", "通信保障", "网络覆盖"],
    "交通": ["交通路网", "道路系统", "物流通道", "交通基础设施", "运输网络", "疏散通道", "路网体系", "交通设施", "道路通行", "交通保障"],
    "供水": ["供水系统", "自来水网", "饮水保障", "供水基础设施", "水网", "水源供应", "供水设施", "供水管网", "饮水系统", "供水保障"],
}

def _select_display_names(pools: dict, event: str, seed_val: int) -> dict:
    """
    根据事件文本与随机种子，为每个内部键选取展示名称。
    事件关键词匹配的名称权重更高，其余随机；保证可复现（相同 event+seed 得相同结果）。
    """
    event_lower = (event or "").lower()
    rng = random.Random(seed_val)
    result = {}
    for internal_key, names in pools.items():
        scores = []
        for name in names:
            score = 1.0  # 基础随机权重
            # 整词或长词匹配：名称中的 2 字以上片段若出现在事件中则加分
            for i in range(len(name) - 1):
                seg = name[i:i+2]
                if seg in event_lower:
                    score += 1.5
            if len(name) >= 3:
                for i in range(len(name) - 2):
                    seg = name[i:i+3]
                    if seg in event_lower:
                        score += 2.0
            if name in event_lower:
                score += 3.0
            scores.append(max(0.1, score))
        total = sum(scores) + 1e-6
        weights = [s / total for s in scores]
        chosen = rng.choices(names, weights=weights, k=1)[0]
        result[internal_key] = chosen
    return result

def select_resource_display_names(event: str, seed_val: int) -> dict:
    return _select_display_names(RESOURCE_DISPLAY_POOLS, event, seed_val)

def select_infra_display_names(event: str, seed_val: int) -> dict:
    return _select_display_names(INFRA_DISPLAY_POOLS, event, seed_val)

def extract_evidence_factors(facts_text: str) -> dict:
    """
    将检索片段做轻量结构化：仅用于机制模型的参数调制（不是“让 AI 编造”）。
    返回 0..1 的因子：supply_shock, power_outage, comms_outage, panic, finance_risk, governance_stress
    """
    t = (facts_text or "").lower()
    # 关键词触发（可逐步替换成更严谨的抽取器/分类器）
    def has_any(keys):
        return any(k in t for k in keys)

    supply = 0.2 + (0.4 if has_any(["供应链", "运输", "物流", "断供", "shortage", "supply chain"]) else 0)
    power = 0.1 + (0.6 if has_any(["停电", "断电", "电力", "power outage", "blackout"]) else 0)
    comms = 0.1 + (0.5 if has_any(["通信", "断网", "网络中断", "comms", "internet outage"]) else 0)
    panic = 0.1 + (0.6 if has_any(["恐慌", "抢购", "谣言", "panic", "hoard"]) else 0)
    finance = 0.1 + (0.6 if has_any(["挤兑", "bank run", "流动性", "金融危机", "兑付"]) else 0)
    gov = 0.2 + (0.4 if has_any(["应急", "救援", "治理", "维稳", "emergency response"]) else 0)

    return {
        "supply_shock": clamp01(supply),
        "power_outage": clamp01(power),
        "comms_outage": clamp01(comms),
        "panic": clamp01(panic),
        "finance_risk": clamp01(finance),
        "governance_stress": clamp01(gov),
    }

def extract_evidence_factors_from_items(evidence_items: list[dict], fallback_text: str = "") -> tuple[dict, dict]:
    """
    高保真证据映射：
    - 对每条证据（snippet/title）进行关键词匹配，得到各因子 0..1 的贡献分
    - 输出：factors（全局因子 0..1）与 factor_map（每个因子对应的证据贡献列表）
    """
    items = evidence_items or []
    # factor -> keywords (lowercase)
    kw = {
        "supply_shock": ["供应链", "运输", "物流", "断供", "缺货", "shortage", "supply chain", "transport", "logistics"],
        "power_outage": ["停电", "断电", "电力", "blackout", "power outage", "grid failure"],
        "comms_outage": ["通信", "断网", "网络中断", "internet outage", "comms", "telecom", "cellular"],
        "panic": ["恐慌", "抢购", "囤积", "谣言", "panic", "hoard", "rumor"],
        "finance_risk": ["挤兑", "bank run", "流动性", "兑付", "金融危机", "liquidity"],
        "governance_stress": ["应急", "救援", "治理", "维稳", "emergency", "response", "enforcement"],
    }

    factor_map = {k: [] for k in kw.keys()}
    counter_map = {k: [] for k in kw.keys()}
    # 反向（缓解/恢复）关键词：用于冲突检测与净效应计算
    counter_kw = {
        "supply_shock": ["恢复供应", "供给恢复", "补货", "恢复运输", "resumed supply", "restored logistics"],
        "power_outage": ["恢复供电", "电力恢复", "抢修完成", "power restored", "restored power"],
        "comms_outage": ["恢复通信", "网络恢复", "通信恢复", "service restored", "network restored"],
        "panic": ["秩序恢复", "安抚", "澄清", "rumor debunked", "calmed"],
        "finance_risk": ["流动性充足", "挤兑缓解", "稳定金融", "liquidity improved", "stabilized"],
        "governance_stress": ["协调顺畅", "响应有效", "处置到位", "effective response"],
    }
    # 对每条证据打分（0..1）：命中关键词越多越高，并乘以证据强度（strength）
    for it in items:
        text = f"{it.get('title','')} {it.get('snippet','')}".lower()
        eid = it.get("evidence_id", "")
        strength = float(it.get("strength", 0.5))
        for f, keys in kw.items():
            matched = [k for k in keys if k.lower() in text]
            if matched:
                # 轻量权重：命中数量/3，封顶 1
                hit_score = clamp01(len(matched) / 3.0)
                score = clamp01(hit_score * strength)
                factor_map[f].append(
                    {
                        "evidence_id": eid,
                        "score": round(float(score), 2),
                        "matched": matched[:6],
                        "strength": round(float(strength), 2),
                    }
                )
            # 反向证据（缓解/恢复）
            ckeys = counter_kw.get(f, [])
            c_matched = [k for k in ckeys if k.lower() in text]
            if c_matched:
                c_hit = clamp01(len(c_matched) / 2.0)
                c_score = clamp01(c_hit * strength)
                counter_map[f].append(
                    {
                        "evidence_id": eid,
                        "score": round(float(c_score), 2),
                        "matched": c_matched[:6],
                        "strength": round(float(strength), 2),
                    }
                )

    # 聚合全局因子：净支持（support - counter），并给出冲突/置信度
    factors = {}
    confidence = {}
    conflicts = {}
    for f, contribs in factor_map.items():
        top = sorted(contribs, key=lambda x: x["score"], reverse=True)[:3]
        top_c = sorted(counter_map.get(f, []), key=lambda x: x["score"], reverse=True)[:3]
        base = 0.10
        support = sum([float(c["score"]) for c in top])
        counter = sum([float(c["score"]) for c in top_c])
        net = max(0.0, support - 0.8 * counter)
        factors[f] = clamp01(base + net * 0.35)
        # 置信度：支持占比（避免“强反证”时仍给高置信度）
        confidence[f] = round(float(support / (support + counter + 1e-6)), 2)
        conflicts[f] = {
            "support": round(float(support), 2),
            "counter": round(float(counter), 2),
            "has_conflict": bool(counter >= max(0.15, 0.6 * support)),
        }
        factor_map[f] = top
        counter_map[f] = top_c

    # 若没有任何证据条目（或全部未命中），回退到旧的文本抽取逻辑
    if not items or all(len(v) == 0 for v in factor_map.values()):
        factors = extract_evidence_factors(fallback_text or "")
        factor_map = {k: [] for k in factors.keys()}
        counter_map = {k: [] for k in factors.keys()}
        confidence = {k: 0.0 for k in factors.keys()}
        conflicts = {k: {"support": 0.0, "counter": 0.0, "has_conflict": False} for k in factors.keys()}

    factor_map_meta = {
        "top_contributions": factor_map,
        "counter_contributions": counter_map,
        "confidence": confidence,
        "conflicts": conflicts,
    }
    return factors, factor_map_meta

def intervention_profile(name: str) -> dict:
    # 成本（消耗资源）与效果（降低风险/焦虑、提升行政）的机制化参数
    profiles = {
        "无": {"cost": {"警力": 1, "物资": 0, "电力": 0, "通信": 0, "交通": 0, "医疗": 0}, "effect": {"calm": 0.00, "order": 0.00, "restore": 0.00}},
        "紧急物资投放": {"cost": {"警力": 2, "物资": 12, "交通": 6, "医疗": 2}, "effect": {"calm": 0.10, "order": 0.03, "restore": 0.04}},
        "媒体安抚": {"cost": {"通信": 4, "警力": 1}, "effect": {"calm": 0.14, "order": 0.02, "restore": 0.00}},
        "加强安保": {"cost": {"警力": 10, "交通": 4}, "effect": {"calm": 0.03, "order": 0.12, "restore": 0.00}},
        "全城宵禁": {"cost": {"警力": 14, "交通": 10, "物资": 3}, "effect": {"calm": 0.05, "order": 0.18, "restore": 0.00}},
        "电力抢修": {"cost": {"电力": 10, "交通": 4, "物资": 4, "医疗": 1}, "effect": {"calm": 0.02, "order": 0.04, "restore": 0.16}},
    }
    return profiles.get(name, profiles["无"])

def init_infrastructure(factors: dict) -> dict:
    """
    基础设施子系统（0-100）：电力/通信/交通/供水。
    由证据因子影响初始水平，后续演化会反向影响社会与资源执行效率。
    """
    power = 80 - 45 * factors.get("power_outage", 0.0) + random.uniform(-5, 5)
    comms = 80 - 40 * factors.get("comms_outage", 0.0) + random.uniform(-5, 5)
    transport = 78 - 25 * factors.get("supply_shock", 0.0) + random.uniform(-6, 6)
    water = 82 - 18 * factors.get("supply_shock", 0.0) + random.uniform(-4, 4)
    return {"电力": clamp100(power), "通信": clamp100(comms), "交通": clamp100(transport), "供水": clamp100(water)}

def infra_degrade_and_restore(infra: dict, factors: dict, intervention: str, effect_scale: float) -> dict:
    """
    基础设施演化：冲击会持续侵蚀，特定干预可修复（电力抢修/媒体安抚影响通信等）。
    """
    inf = {k: float(infra.get(k, 80)) for k in ["电力", "通信", "交通", "供水"]}
    # 冲击侵蚀
    inf["电力"] -= 4.0 * factors.get("power_outage", 0.0) + random.uniform(-1.2, 1.2)
    inf["通信"] -= 3.5 * factors.get("comms_outage", 0.0) + random.uniform(-1.0, 1.0)
    inf["交通"] -= 2.5 * factors.get("supply_shock", 0.0) + random.uniform(-1.5, 1.5)
    inf["供水"] -= 1.8 * factors.get("supply_shock", 0.0) + random.uniform(-1.0, 1.0)

    # 干预修复
    if intervention == "电力抢修":
        inf["电力"] += 10.0 * effect_scale + random.uniform(-1.0, 1.0)
        inf["通信"] += 2.0 * effect_scale
    if intervention == "媒体安抚":
        inf["通信"] += 5.0 * effect_scale + random.uniform(-0.8, 0.8)
    if intervention == "全城宵禁":
        inf["交通"] -= 6.0  # 宵禁直接抑制交通可用性

    return {k: clamp100(v) for k, v in inf.items()}

def mechanistic_step(state: dict, resources: dict, factors: dict, intervention: str, step: int, infra: dict, params: dict, evidence_items: list[dict], factor_map: dict, decay_schedule: dict, time_axis: dict) -> tuple[dict, dict, dict, dict]:
    """
    机制化演化：状态由可审计规则决定（资源约束、冲击因子、干预成本/效果、阈值触发）
    返回 (new_state, new_resources, new_infra, audit)
    """
    s = {k: float(state.get(k, 50)) for k in ["行政效能", "焦虑指数", "资源缺口", "动荡风险"]}
    r = {k: float(resources.get(k, 50)) for k in ["警力", "医疗", "物资", "电力", "通信", "交通"]}
    inf = {k: float(infra.get(k, 80)) for k in ["电力", "通信", "交通", "供水"]}

    prof = intervention_profile(intervention)
    cost = prof["cost"]
    eff = prof["effect"]

    # 证据引用：使用 factor_map 的 top 贡献证据作为可追溯引用
    cited = []
    top_map = (factor_map or {}).get("top_contributions", {}) if isinstance(factor_map, dict) else {}
    for f, top in (top_map or {}).items():
        for c in (top or []):
            if isinstance(c, dict) and c.get("evidence_id"):
                cited.append(c["evidence_id"])
    cited = sorted(list({c for c in cited if c}))

    # 资源可用性（不足时效果打折 + 产生“执行失败”审计项）
    shortage_ratio = 0.0
    for k, c in cost.items():
        avail = r.get(k, 0.0)
        if c > 0:
            shortage_ratio = max(shortage_ratio, max(0.0, (c - avail) / c))

    execution_penalty = clamp01(shortage_ratio)
    # 可行性硬约束：基础设施与关键资源不足时，判定“不可执行”，不扣资源、不产生效果
    min_infra = float(params.get("min_infra_to_execute", 25))
    infra_ok = min(inf["电力"], inf["通信"], inf["交通"]) >= min_infra
    resources_ok = execution_penalty <= 0.15
    executable = bool(infra_ok and resources_ok)
    effect_scale = (1.0 - 0.7 * execution_penalty) if executable else 0.0

    # 昼夜节律：夜间更易焦虑/动荡，且执行折扣（不改变原结构，只对高保真新增）
    is_night = False
    if isinstance(time_axis, dict):
        p = (time_axis.get("points") or {}).get(step) or {}
        is_night = bool(p.get("is_night")) if p.get("is_night") is not None else False
    if bool(params.get("circadian", True)) and is_night:
        effect_scale = max(0.0, effect_scale * (1.0 - float(params.get("night_exec_penalty", 0.15))))

    # 先扣资源（不低于 0）
    if executable:
        for k, c in cost.items():
            r[k] = max(0.0, r.get(k, 0.0) - float(c))

    # 冲击：由证据因子调制（越像真实案例/危机类型，对应维度冲击更强）
    ds = decay_schedule or {}
    d = {
        "panic": float(((ds.get("panic") or {}).get(step, 1.0))),
        "comms_outage": float(((ds.get("comms_outage") or {}).get(step, 1.0))),
        "finance_risk": float(((ds.get("finance_risk") or {}).get(step, 1.0))),
        "supply_shock": float(((ds.get("supply_shock") or {}).get(step, 1.0))),
        "power_outage": float(((ds.get("power_outage") or {}).get(step, 1.0))),
        "governance_stress": float(((ds.get("governance_stress") or {}).get(step, 1.0))),
    }
    shock_anxiety = params.get("shock_anxiety_k", 1.0) * (
        8.0 * factors["panic"] * d["panic"]
        + 6.0 * factors["comms_outage"] * d["comms_outage"]
        + 5.0 * factors["finance_risk"] * d["finance_risk"]
    )
    shock_gap = params.get("shock_gap_k", 1.0) * (
        9.0 * factors["supply_shock"] * d["supply_shock"]
        + 7.0 * factors["power_outage"] * d["power_outage"]
    )
    shock_risk = params.get("shock_risk_k", 1.0) * (
        7.0 * factors["panic"] * d["panic"]
        + 8.0 * factors["supply_shock"] * d["supply_shock"]
        + 6.0 * factors["finance_risk"] * d["finance_risk"]
    )
    shock_admin = -params.get("shock_admin_k", 1.0) * (
        6.0 * factors["power_outage"] * d["power_outage"]
        + 4.0 * factors["comms_outage"] * d["comms_outage"]
        + 5.0 * factors["supply_shock"] * d["supply_shock"]
    )

    # 干预效果：降低焦虑/动荡，提升行政，缓解缺口（restore 主要影响电力/通信带来的行政恢复）
    calm = 12.0 * eff["calm"] * effect_scale
    order = 12.0 * eff["order"] * effect_scale
    restore = 12.0 * eff["restore"] * effect_scale

    # 动力学耦合：缺口↑ 会推高焦虑与风险；行政↓ 会推高风险
    coupling_anxiety = params.get("coupling_anxiety_k", 1.0) * (0.10 * (s["资源缺口"] - 50.0) + 0.08 * (50.0 - s["行政效能"]))
    coupling_risk = params.get("coupling_risk_k", 1.0) * (0.12 * (s["焦虑指数"] - 50.0) + 0.10 * (s["资源缺口"] - 50.0) + 0.10 * (50.0 - s["行政效能"]))

    # 基础设施对行政与缺口的反馈：电力/交通越差，行政越难、缺口越大；通信差会推高焦虑
    infra_admin_pen = (80.0 - inf["电力"]) * 0.06 + (80.0 - inf["交通"]) * 0.04
    infra_gap_pen = (80.0 - inf["交通"]) * 0.06 + (80.0 - inf["电力"]) * 0.05
    infra_anx_pen = (80.0 - inf["通信"]) * 0.05

    # 宵禁副作用：焦虑上升、交通受限 -> 缺口可能加剧
    curfew_penalty = 0.0
    if intervention == "全城宵禁":
        curfew_penalty = 6.0
        s["资源缺口"] += 4.0

    # 计算新状态（加入少量噪声但可复现：由外部 seed 控制 random）
    s2 = {}
    s2["行政效能"] = s["行政效能"] + shock_admin + restore - infra_admin_pen + random.uniform(-1.5, 1.5)
    s2["资源缺口"] = s["资源缺口"] + shock_gap - 6.0 * eff["restore"] * effect_scale + infra_gap_pen + random.uniform(-1.5, 1.5)
    anxiety_boost = float(params.get("night_anxiety_boost", 0.25)) if (bool(params.get("circadian", True)) and is_night) else 0.0
    risk_boost = float(params.get("night_risk_boost", 0.20)) if (bool(params.get("circadian", True)) and is_night) else 0.0
    s2["焦虑指数"] = s["焦虑指数"] + shock_anxiety * (1.0 + anxiety_boost) - calm + coupling_anxiety + infra_anx_pen + curfew_penalty + random.uniform(-2.0, 2.0)
    s2["动荡风险"] = s["动荡风险"] + shock_risk * (1.0 + risk_boost) - order + coupling_risk + random.uniform(-2.0, 2.0)

    # 更新基础设施（冲击持续 + 干预修复）
    new_infra = infra_degrade_and_restore(infra, factors, intervention, effect_scale)

    # 阈值触发：风险过高触发“骚乱/踩踏”事件，消耗警力医疗并进一步推高焦虑
    triggered = []
    if s2["动荡风险"] >= float(params.get("trigger_risk", 80)):
        triggered.append("高动荡阈值触发：局部骚乱/聚集事件")
        r["警力"] = max(0.0, r["警力"] - 8.0)
        r["医疗"] = max(0.0, r["医疗"] - 4.0)
        s2["焦虑指数"] += 4.0
    if s2["资源缺口"] >= float(params.get("trigger_gap", 75)):
        triggered.append("高缺口阈值触发：排队与争抢加剧")
        s2["焦虑指数"] += 3.0
        s2["动荡风险"] += 2.0
    if s2["行政效能"] <= float(params.get("trigger_admin", 25)):
        triggered.append("低行政阈值触发：协调失灵与执行落差")
        s2["动荡风险"] += 3.0

    new_state = {k: clamp100(v) for k, v in s2.items()}
    new_resources = {k: clamp100(v) for k, v in r.items()}

    audit = {
        "step": step,
        "intervention": intervention,
        "executable": executable,
        "resource_shortage_ratio": round(execution_penalty, 2),
        "effect_scale": round(effect_scale, 2),
        "triggered": triggered,
        "resource_cost": cost,
        "factors": {k: round(float(v), 2) for k, v in factors.items()},
        "infra": {k: clamp100(v) for k, v in inf.items()},
        "infra_after": new_infra,
        "evidence_citations": cited,
        "factor_contributions": (factor_map or {}).get("top_contributions", factor_map) if isinstance(factor_map, dict) else (factor_map or {}),
        "factor_confidence": (factor_map or {}).get("confidence", {}) if isinstance(factor_map, dict) else {},
        "factor_conflicts": (factor_map or {}).get("conflicts", {}) if isinstance(factor_map, dict) else {},
        "decay_meta": (decay_schedule or {}).get("_meta", {}),
        "time_point": ((time_axis or {}).get("points") or {}).get(step, {}),
    }
    return new_state, new_resources, new_infra, audit

def narrate_from_mechanism(event: str, facts: str, step: int, intervention: str, state: dict, prev_state: dict, resources: dict, audit: dict) -> dict:
    """
    将“机制计算结果”转成四方叙事。AI 只能基于输入的状态/审计，不允许凭空造数据。
    """
    delta = {k: int(state[k]) - int(prev_state.get(k, 0)) for k in ["行政效能", "焦虑指数", "资源缺口", "动荡风险"]}
    base_context = f"""事件：{event}
阶段：第{step}步
干预：{intervention}
状态（0-100）：{state}
变化量：{delta}
资源（0-100）：{resources}
审计要点：可执行={audit.get('executable')}；资源不足比例={audit.get('resource_shortage_ratio')}；触发事件={audit.get('triggered')}；证据引用={audit.get('evidence_citations')}
实证摘要（仅供背景，不要求逐字引用）：{(facts or '')[:600]}
"""
    if client is None:
        # 无模型时使用规则化模板（仍然基于机制结果）
        return {
            "official": f"第{step}阶段，官方尝试执行「{intervention}」（可执行={audit.get('executable')}）。行政效能{delta['行政效能']:+d}，资源缺口{delta['资源缺口']:+d}。重点风险为动荡风险{state['动荡风险']}%，需围绕资源与秩序联动处置。",
            "citizen": f"民众焦虑指数{state['焦虑指数']}%（变化{delta['焦虑指数']:+d}），对物资与信息的可获得性更敏感，出现排队/囤积倾向的概率上升。",
            "media": f"媒体报道聚焦指标变化与触发事件：{'; '.join(audit.get('triggered') or ['无'])}。舆情可能放大焦虑并影响社会预期。",
            "audit": f"审计结论：可执行={audit.get('executable')}；资源不足比例={audit.get('resource_shortage_ratio')}；效果缩放={audit.get('effect_scale')}；证据引用={audit.get('evidence_citations')}。建议优先保障关键资源并避免指标与叙事不一致。"
        }

    prompt = f"""你是推演系统的“叙事生成器”，必须严格遵守审计约束：
1) 不得编造任何未在输入中出现的数字、事件、资源水平；
2) 所有结论必须可追溯到状态/变化量/审计要点；
3) 输出必须是 JSON，键为 official/citizen/media/audit，值为中文文本，每段 120-220 字。

输入如下：
{base_context}
"""
    try:
        res = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            timeout=30
        )
        j = safe_json(res.choices[0].message.content)
        return {
            "official": str(j.get("official", ""))[:1200],
            "citizen": str(j.get("citizen", ""))[:1200],
            "media": str(j.get("media", ""))[:1200],
            "audit": str(j.get("audit", ""))[:1200],
        }
    except Exception as e:
        return {
            "official": f"[叙事生成异常] {str(e)[:80]}",
            "citizen": "叙事生成失败（请检查 API）。",
            "media": "叙事生成失败（请检查 API）。",
            "audit": "叙事生成失败（请检查 API）。"
        }

def get_evidence(q):
    if not serper_key:
        return "离线仿真模式"
    try:
        r = requests.post("https://google.serper.dev/search",
            headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
            json={"q": f"{q} 社会演化 历史案例 危机应对 PESTEL", "num": 8}, timeout=12)
        return "\n".join([x.get("snippet","") for x in r.json().get("organic", [])])
    except:
        return "实证检索失败，使用内部模型"

def get_evidence_items(q: str) -> tuple[str, list[dict]]:
    """
    证据条目化：为高保真模式提供可引用 evidence_id。
    返回 (facts_text, items)。facts_text 仍然兼容原有流程。
    """
    if not serper_key:
        return "离线仿真模式", []
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
            json={"q": f"{q} 社会演化 历史案例 危机应对 PESTEL", "num": 8},
            timeout=12,
        )
        organic = r.json().get("organic", []) or []
        items = []
        for idx, x in enumerate(organic, start=1):
            base = {
                "evidence_id": f"E{idx:02d}",
                "title": x.get("title", ""),
                "link": x.get("link", ""),
                "snippet": x.get("snippet", ""),
            }
            base.update(score_evidence_strength(base))
            base.update(extract_evidence_struct(base))
            items.append(base)
        facts_text = "\n".join([it.get("snippet", "") for it in items if it.get("snippet")])
        return facts_text, items
    except Exception:
        return "实证检索失败，使用内部模型", []

def _default_matrix():
    return {"行政效能": 50, "焦虑指数": 50, "资源缺口": 50, "动荡风险": 50}

def init_state(event, facts):
    subject = st.session_state.get("doc_subject") or {}
    ctx = ""
    if subject.get("org") or subject.get("company") or subject.get("year"):
        ctx = f"分析对象：{subject.get('org','') or subject.get('company','')}，{subject.get('year','')}。\n"
    prompt = f"{ctx}事件：{event}\n事实：{facts}\n返回JSON（0-100）：行政效能、焦虑指数、资源缺口、动荡风险"
    try:
        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
        j = safe_json(res.choices[0].message.content)
        return {k: max(0, min(100, int(j.get(k, 50)))) for k in ["行政效能", "焦虑指数", "资源缺口", "动荡风险"]}
    except Exception:
        return _default_matrix()

def init_resources():
    return {
        "警力": random.randint(60,95), "医疗": random.randint(50,90),
        "物资": random.randint(30,85), "电力": random.randint(20,70),
        "通信": random.randint(40,90), "交通": random.randint(30,80)
    }

def evolve_step(event, facts, matrix, step, intervention, resources):
    prompt = f"""
事件：{event}
实证：{facts}
社会状态：{matrix}
资源状态：{resources}
干预措施：{intervention}
第{step}阶段演化。
严格返回JSON：official、citizen、media、audit（详细专业）
"""
    try:
        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"}, timeout=30)
        return safe_json(res.choices[0].message.content)
    except Exception as e:
        return {
            "official": f"[API 异常] 官方应对：{str(e)[:80]}",
            "citizen": "[API 异常] 民众反应数据暂不可用",
            "media": "[API 异常] 媒体视角数据暂不可用",
            "audit": "[API 异常] 审计结论暂不可用"
        }

def update_state(old, evo, intervention):
    adj = {
        "无": (-3,5,-2,6),
        "紧急物资投放": (-2,-5,10,-4),
        "媒体安抚": (-1,-10,2,-3),
        "加强安保": (4,2,-5,-8),
        "全城宵禁": (6,-8,-3,-10),
        "电力抢修": (8,0,-5,2)
    }
    a,b,c,d = adj.get(intervention, adj["无"])
    base = _default_matrix()
    for k in base:
        base[k] = old.get(k, 50)
    return {
        "行政效能": max(0, min(100, base["行政效能"] + a + random.randint(-2,3))),
        "焦虑指数": max(0, min(100, base["焦虑指数"] + b + random.randint(-4,6))),
        "资源缺口": max(0, min(100, base["资源缺口"] + c + random.randint(-3,5))),
        "动荡风险": max(0, min(100, base["动荡风险"] + d + random.randint(-3,7)))
    }

def update_resources(res):
    return {
        k: max(0, min(100, v + random.randint(-8,6)))
        for k,v in res.items()
    }

def gen_black_swan(event):
    if random.random() < 0.3:
        return "无黑天鹅事件"
    try:
        prompt = f"{event} 背景下，生成低概率高冲击突发事件"
        return client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}]).choices[0].message.content
    except Exception as e:
        return f"[生成异常] 黑天鹅模块暂不可用：{str(e)[:60]}"

def gen_causal(event):
    try:
        prompt = f"为 {event} 生成PESTEL全维度因果链，结构化输出"
        return client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}]).choices[0].message.content
    except Exception as e:
        return f"[因果链生成异常] {str(e)[:100]}\n请检查 API 配置后重新运行。"

def gen_report(event, facts, timeline, swan, matrix, resources):
    subject = st.session_state.get("doc_subject") or {}
    # 有提取结果时：报告只基于提取结果，不塞整篇长文档
    if subject.get("org") or subject.get("year"):
        c = subject.get("org", "") or subject.get("company", "")
        y = subject.get("year", "")
        doc_type = subject.get("doc_type", "")
        kp = subject.get("key_points", "")
        empirical = f"""【文档提取结果-研判唯一依据】
主体/企业：{c}
日期/年度：{y}
文档类型：{doc_type}
关键要点：{kp}

报告必须针对上述主体与年度，开头须写明「分析对象：{c}，{y}」。禁止使用其他主体名称。"""
    else:
        empirical = facts
    prompt = f"""
你是国家级战略安全顾问，生成正式研判报告。

事件：{event}
实证材料：{empirical}
演化时序：{timeline}
黑天鹅：{swan}
社会状态：{matrix}
资源状态：{resources}
报告必须包含：1. 事件定级 2. 物理瘫痪分析 3. 社会临界点 4. 演化复盘 5. 风险预警 6. 干预建议 7. 结论
"""
    try:
        return client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], timeout=60).choices[0].message.content
    except Exception as e:
        return f"【报告生成异常】API 调用失败：{str(e)[:120]}\n请检查网络与 API 配置后重新运行仿真并导出报告。"

def classify_event_relevance(event: str) -> dict:
    """
    智能化判断用户输入是否与政府政策、社会资源、公共危机相关。
    若无关（如续写小说、一般创作），则不应启动危机推演模块。
    返回 {"is_crisis_simulation": bool, "reason": str}
    """
    if not client:
        return {"is_crisis_simulation": True, "reason": "无API时默认启用危机推演"}
    prompt = """你是一个意图分类器。判断用户的输入是否适合进行「政府/社会危机推演仿真」。

以下情况应返回 is_crisis_simulation=true：
- 涉及政府应对、公共政策、社会资源调度
- 涉及基础设施故障（停电/断水/通信/交通中断）
- 涉及金融挤兑、供应链中断、民生保障
- 涉及治安、秩序、救援、应急响应
- 涉及民众恐慌、抢购、动荡等社会演化

以下情况应返回 is_crisis_simulation=false：
- 纯文学创作（续写小说、写诗、写故事）
- 预测虚构作品的情节走向
- 与政府/社会资源无关的创作、问答

用户输入：「{event}」

严格返回JSON，仅包含两个键：is_crisis_simulation（布尔）、reason（一句话说明原因，中文）""".format(event=(event or "")[:500])
    try:
        res = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            timeout=15,
        )
        j = safe_json(res.choices[0].message.content)
        is_crisis = bool(j.get("is_crisis_simulation", True))
        reason = str(j.get("reason", ""))[:200] or ("适合危机推演" if is_crisis else "与政府社会资源无关，采用创意模式")
        return {"is_crisis_simulation": is_crisis, "reason": reason}
    except Exception as e:
        return {"is_crisis_simulation": True, "reason": f"分类异常，默认启用危机推演：{str(e)[:60]}"}

def run_branch_from_step(fork_step: int, new_intervention: str, event: str, facts: str) -> dict:
    """从第 fork_step 步之后用新干预策略继续推演，返回 branch 数据。"""
    timeline = st.session_state.get("timeline") or []
    mh = st.session_state.get("matrix_history") or []
    rh = st.session_state.get("resources") or []
    ih = st.session_state.get("infra_history") or []
    idx = min(fork_step + 1, len(mh) - 1) if mh else 0
    matrix = dict(mh[idx]) if idx < len(mh) and mh else {"行政效能":50,"焦虑指数":50,"资源缺口":50,"动荡风险":50}
    resources = dict(rh[idx]) if idx < len(rh) and rh else {}
    infra = dict(ih[idx]) if idx < len(ih) and ih else {"电力":80,"通信":80,"交通":80,"供水":80}
    factors = st.session_state.get("init_factors") or st.session_state.get("stepping_factors")
    if not factors or (isinstance(factors, dict) and "top_contributions" in factors):
        factors = extract_evidence_factors(facts[:2000])
    eff = int(st.session_state.get("stepping_effective_steps") or len(timeline))
    branch_timeline = []
    branch_matrix_hist = list(st.session_state.matrix_history[:fork_step+2])  # init + steps 1..fork_step+1
    branch_resources = list(st.session_state.resources[:fork_step+2])
    branch_infra = list((st.session_state.get("infra_history") or [])[:fork_step+2])
    for i in range(fork_step + 2, eff + 1):  # 从 step fork_step+2 开始（即分支后的第一步）
        if sim_mode.startswith("高保真"):
            prev = matrix
            matrix, resources, infra, audit = mechanistic_step(
                matrix, resources, factors, new_intervention, i, infra,
                st.session_state.hf_params, st.session_state.evidence_items,
                st.session_state.evidence_factor_map, st.session_state.decay_schedule,
                st.session_state.time_axis,
            )
            evo = narrate_from_mechanism(event, facts, i, new_intervention, matrix, prev, resources, audit)
            branch_timeline.append({"step": i, "data": evo, "audit": audit, "state": matrix.copy(), "resources": resources.copy(), "infra": infra.copy()})
        else:
            evo = evolve_step(event, facts, matrix, i, new_intervention, resources)
            branch_timeline.append({"step": i, "data": evo})
            matrix = update_state(matrix, evo, new_intervention)
            resources = update_resources(resources)
        branch_matrix_hist.append(matrix.copy())
        branch_resources.append(resources.copy())
        if sim_mode.startswith("高保真"):
            branch_infra.append(infra.copy())
    full_tl = list(timeline[:fork_step+1]) + branch_timeline
    report = gen_report(event, facts, full_tl, st.session_state.get("swan",""), matrix, resources)
    return {"fork_step": fork_step, "intervention": new_intervention, "timeline": branch_timeline, "matrix_history": branch_matrix_hist, "resources": branch_resources, "infra_history": branch_infra, "report": report, "full_timeline": full_tl}

def extract_entity_graph(event: str, facts: str) -> dict:
    """从事件与实证中抽取实体与关系，构建简单知识图。"""
    if not client:
        return {"entities": [], "relations": []}
    text = f"事件：{event}\n\n实证/背景：{(facts or '')[:3000]}"
    prompt = f"""从以下文本中抽取关键实体（人物、组织、地点、资源、事件类型等）及其关系。

文本：
{text}

严格返回JSON，格式：
{{"entities": [{{"name": "实体名", "type": "人物|组织|地点|资源|事件"}}], "relations": [{{"source": "实体1", "target": "实体2", "relation": "关系描述"}}]}}

每类实体最多5个，关系最多8条。只输出JSON，无其他内容。"""
    try:
        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"}, timeout=15)
        j = safe_json(res.choices[0].message.content)
        return {"entities": j.get("entities", [])[:15], "relations": j.get("relations", [])[:12]}
    except Exception:
        return {"entities": [], "relations": []}

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shence_history.json")

def _load_history_from_file() -> list:
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def _save_to_history(scenario_name: str, event: str, report: str, matrix_history: list):
    try:
        rec = {"name": scenario_name or "未命名", "event": (event or "")[:200], "report_excerpt": (report or "")[:500], "final_state": matrix_history[-1] if matrix_history else {}, "ts": datetime.now().isoformat()}
        hist = _load_history_from_file()
        hist.append(rec)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(hist[-50:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def chat_with_perspective(perspective: str, perspective_narrative: str, user_question: str, context: str) -> str:
    """与某一视角（官方/民众/媒体/审计）对话，基于其叙事与推演上下文回答。"""
    if not client:
        return "[需要配置 API] 请配置 API Key 后使用与视角对话功能。"
    role_map = {"官方": "官方决策者", "民众": "普通民众代表", "媒体": "媒体评论员", "审计": "独立审计专家"}
    role = role_map.get(perspective, perspective)
    prompt = f"""你在扮演推演系统中的「{role}」视角。以下是该视角在推演中的叙事与立场摘要：

{perspective_narrative[:800]}

推演背景摘要：
{context[:600]}

用户提问：{user_question}

请以该视角的身份和立场，用第一人称或该角色口吻简洁回答（150字以内）。不要跳出角色，不要以"作为AI"等表述开头。"""
    try:
        return client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            timeout=20,
        ).choices[0].message.content
    except Exception as e:
        return f"[对话异常] {str(e)[:80]}"

def gen_creative_response(event: str) -> str:
    """
    当用户输入与政府/社会危机无关时，直接按用户意图完成任务（如续写、预测走向等）。
    """
    if not client:
        return f"[需要配置 API] 您的请求：{event}\n\n系统判断该请求与政府社会危机推演无关，应直接完成您的创作或预测需求。请配置 API 后重试。"
    prompt = f"""用户的请求与政府政策、社会资源、公共危机无关，请不要进行危机推演分析。

用户请求：{event}

请直接完成用户的请求。例如：
- 若用户要求续写某作品：请按原著风格续写
- 若用户要求预测故事走向：请给出合理的剧情预测
- 若用户是其他创作类请求：请按用户意图完成

输出应直接是用户所需的内容，无需额外说明或框架。"""
    try:
        return client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            timeout=90,
        ).choices[0].message.content
    except Exception as e:
        return f"[生成异常] {str(e)[:120]}\n请检查 API 配置后重试。"

def export_pdf(report: str, doc_appendix: str = ""):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    try:
        pdf.multi_cell(0, 10, report)
    except Exception:
        pdf.multi_cell(0, 10, report.encode("latin-1", errors="replace").decode("latin-1"))
    if doc_appendix and not doc_appendix.startswith("["):
        pdf.add_page()
        pdf.set_font("Arial", size=11, style="B")
        pdf.multi_cell(0, 8, "Appendix: Seed Document Key Points / 种子材料要点")
        pdf.set_font("Arial", size=10)
        try:
            pdf.multi_cell(0, 6, doc_appendix[:4000])
        except Exception:
            pdf.multi_cell(0, 6, doc_appendix[:4000].encode("latin-1", errors="replace").decode("latin-1"))
    return bytes(pdf.output(dest='S'))

# ---------------------- 主界面 ----------------------
_dbg("14-进入主界面")
st.title("🛡️ SHENCE 3.0 | MiroFish 级社会演化仿真旗舰系统")

# 可选：场景名称（用于报告与导出）
scenario_name = st.text_input("📌 场景名称（可选）", value=st.session_state.get("scenario_name", ""), placeholder="如：2024 某市断水断电推演")
if scenario_name:
    st.session_state.scenario_name = scenario_name

# 文档种子上传（补充背景知识）
st.subheader("📎 种子上传（可选）")
uploaded_doc = st.file_uploader("上传 PDF、TXT、Word、Markdown 作为背景材料", type=["pdf", "txt", "docx", "md"], help="支持 .pdf .txt .docx .md，将融入推演的知识上下文")
seed_url = st.text_input("或输入网页 URL 抓取内容", placeholder="https://...", key="seed_url_input")
if st.button("🔄 加载网页", key="fetch_url_btn") and seed_url:
    url_text = fetch_url_as_seed(seed_url)
    st.session_state.uploaded_doc_text = url_text
    if url_text and not url_text.startswith("["):
        st.caption(f"已抓取 {len(url_text)} 字符")
if uploaded_doc:
    doc_text = parse_uploaded_document(uploaded_doc)
    st.session_state.uploaded_doc_text = doc_text
    if doc_text and not doc_text.startswith("["):
        st.caption(f"已解析 {len(doc_text)} 字符，将并入实证上下文")
doc_preview = st.session_state.get("uploaded_doc_text") or ""
if doc_preview and not doc_preview.startswith("[") and len(doc_preview) > 50:
    st.info(f"📄 **文档提取预览**（共 {len(doc_preview)} 字，请核对系统读到的内容是否正确）")
    st.text_area("系统读取到的文档内容（前 2500 字）", value=doc_preview[:2500], height=200, disabled=True, key="doc_preview_ta")
    st.caption("若此处内容乱码或缺失，说明 PDF 解析不佳，建议更换文件或使用 TXT/Word 格式")
if not PDF_AVAILABLE:
    st.caption("💡 支持 PDF：pip install pymupdf 或 pip install pypdf")
if not OCR_AVAILABLE:
    st.caption("💡 扫描版 PDF 可启用 OCR：pip install pdf2image pytesseract（另需安装 Tesseract 程序）")
if not DOCX_AVAILABLE:
    st.caption("💡 支持 Word：pip install python-docx")

# 多轮记忆：引用历史推演
_dbg("15-加载历史文件")
hist_list = _load_history_from_file()
if hist_list:
    with st.expander("📚 引用历史推演", expanded=False):
        hist_sel = st.selectbox("选择历史场景作为参考", [""] + [f"{h.get('name','')} - {h.get('event','')[:50]}..." for h in reversed(hist_list[-10:])], key="hist_ref")
        if hist_sel and hist_sel != "":
            opts = [f"{h.get('name','')} - {h.get('event','')[:50]}..." for h in reversed(hist_list[-10:])]
            idx = opts.index(hist_sel) if hist_sel in opts else 0
            ref = list(reversed(hist_list[-10:]))[idx]
            st.info(f"**参考摘要**：{ref.get('report_excerpt','')[:300]}...")
            st.session_state.history_ref = ref.get("report_excerpt", "")[:1500]
        else:
            st.session_state.history_ref = ""

# 事件输入（自主输入，无需模板）
st.subheader("📡 初始扰动事件")
event = st.text_area(
    "请自主描述您要推演的事件场景",
    value=st.session_state.get("event", ""),
    height=120,
    placeholder="例如：一线城市核心区域停电停水 48 小时，通信不稳，民众恐慌抢购；或：粮食供应链中断 7 天，米面油库存下降，物价上涨……\n\n也可输入与政府社会无关的请求（如：请续写红楼梦、预测某故事走向），系统将智能识别并直接完成，不启动危机推演模块。"
)

# 控制面板
with st.expander("⚙️ 仿真控制面板", expanded=True):
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        steps = st.slider("演化步数", 1, 8, 4)
    with c2:
        step_mode = st.radio("推演节奏", ["连续运行", "逐步推演（可中途干预）"], horizontal=True, help="逐步推演：每步可修改干预策略或注入新事件")
    with c3:
        intervention = st.selectbox("🎯 官方干预策略", [
            "无","紧急物资投放","媒体安抚","加强安保","全城宵禁","电力抢修"
        ], help="无/物资/媒体/安保/宵禁/电力，不同策略会改变社会矩阵演化系数")
    with c4:
        enable_swan = st.checkbox("启用黑天鹅", value=True)
    with st.expander("📖 干预策略说明", expanded=False):
        st.markdown("""
- **无**：无专项干预，按自然演化
- **紧急物资投放**：缓解资源缺口与焦虑，可能略增行政压力
- **媒体安抚**：显著降焦虑，轻微影响行政与资源
- **加强安保**：提升行政效能、压制动荡，略增资源消耗
- **全城宵禁**：强控动荡与行政，但会推高焦虑
- **电力抢修**：优先恢复行政与秩序，缓解资源与动荡
        """)
        # 干预策略成本与效果可视化
        st.markdown("**📊 干预策略成本与效果对比**")
        all_interventions = ["无","紧急物资投放","媒体安抚","加强安保","全城宵禁","电力抢修"]
        resource_keys = ["警力","医疗","物资","电力","通信","交通"]
        cost_data = {k: [] for k in resource_keys}
        for inv in all_interventions:
            prof = intervention_profile(inv)
            for rk in resource_keys:
                cost_data[rk].append(prof["cost"].get(rk, 0))
        fig_cost = go.Figure()
        colors_r = ["#58a6ff","#2ea043","#f85149","#f0883e","#a371f7","#8b949e"]
        for i, rk in enumerate(resource_keys):
            fig_cost.add_trace(go.Bar(name=rk, x=all_interventions, y=cost_data[rk], marker_color=colors_r[i]))
        fig_cost.update_layout(barmode="stack", height=220, margin=dict(t=30,b=30), xaxis_tickangle=-25, legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_cost, use_container_width=True)
        eff_data = {"calm":[], "order":[], "restore":[]}
        for inv in all_interventions:
            prof = intervention_profile(inv)
            eff_data["calm"].append(round(prof["effect"]["calm"]*100))
            eff_data["order"].append(round(prof["effect"]["order"]*100))
            eff_data["restore"].append(round(prof["effect"]["restore"]*100))
        fig_eff = go.Figure()
        fig_eff.add_trace(go.Bar(name="降焦虑", x=all_interventions, y=eff_data["calm"], marker_color="#f8c447"))
        fig_eff.add_trace(go.Bar(name="压动荡", x=all_interventions, y=eff_data["order"], marker_color="#e34c26"))
        fig_eff.add_trace(go.Bar(name="恢复力", x=all_interventions, y=eff_data["restore"], marker_color="#58a6ff"))
        fig_eff.update_layout(barmode="group", height=220, margin=dict(t=30,b=30), xaxis_tickangle=-25, yaxis_title="效果系数×100", legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_eff, use_container_width=True)
    with st.expander("🦢 黑天鹅触发配置", expanded=False):
        swan_trigger_step = st.selectbox("触发时机", [0,1,2,3,4,5,6,7,8], format_func=lambda x: "仿真开始时" if x==0 else f"第{x}步", index=0, key="swan_trigger_step")
        swan_trigger_risk = st.slider("最低动荡阈值", 0, 95, 0, 5, help="0=不限制；>0 时仅当动荡风险≥该值才可能触发黑天鹅", key="swan_trigger_risk")
    st.caption(f"当前模式：{sim_mode}；随机种子：{seed}（相同输入 + 相同种子可复现演化轨迹）")

# 启动按钮
col_launch1, col_launch2 = st.columns([3,1])
with col_launch1:
    run = st.button("🚀 启动全流程仿真", type="primary", use_container_width=True)
with col_launch2:
    reset = st.button("🔁 重置仿真", use_container_width=True)

def request_reset():
    st.session_state.reset_requested = True

if reset:
    request_reset()
if st.session_state.get("reset_requested"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# ---------------------- 仿真运行 ----------------------
_dbg("16-仿真分支判断")
if run and client and event:
    try:
        random.seed(int(seed))
        # 智能化判断：是否与政府/社会危机相关
        if force_crisis_mode:
            relevance = {"is_crisis_simulation": True, "reason": "用户强制启用危机推演模式"}
        else:
            relevance = classify_event_relevance(event)
        st.session_state.event_relevance = relevance

        if not relevance["is_crisis_simulation"]:
            # 创意模式：不启动政府/社会资源相关功能，直接完成用户请求
            with st.status("✅ 智能识别为创意模式...", expanded=True) as s:
                s.update(label="🧠 判定与政府社会资源无关，跳过危机推演")
                st.session_state.run_mode = "creative"
                st.session_state.creative_output = gen_creative_response(event)
                s.update(label="✅ 完成", state="complete")
            st.success("已完成！系统判断您的请求与政府/社会危机无关，已直接按您的要求生成内容。")
        else:
            # 危机推演模式：完整流程
            st.session_state.run_mode = "crisis"
            # 根据事件生成动态展示名称（资源与基础设施），体现真人分析般的灵活度
            st.session_state.resource_display_map = select_resource_display_names(event, int(seed))
            st.session_state.infra_display_map = select_infra_display_names(event, int(seed))
            effective_steps = int(steps)
            if sim_mode.startswith("高保真"):
                hp = st.session_state.get("hf_params", {}) or {}
                if hp.get("auto_steps_by_duration") and int(hp.get("total_duration_hours") or 0) > 0:
                    sh = float(hp.get("step_hours") or 12.0)
                    effective_steps = max(1, int(math.ceil(int(hp["total_duration_hours"]) / max(1.0, sh))))
                    if effective_steps > 24:
                        effective_steps = 24
            with st.status("✅ 仿真启动中...", expanded=True) as s:
                s.update(label="🌐 检索实证案例")
                doc_text = st.session_state.get("uploaded_doc_text") or ""
                if doc_text and not doc_text.startswith("[") and len(doc_text) > 200:
                    s.update(label="📄 专职文档理解（提取主体、年度、要点）")
                    extract = document_understanding(doc_text, client)
                    st.session_state.doc_subject = extract
                    anchor = ""
                    if extract.get("org") or extract.get("year"):
                        anchor = f"【系统提取的分析对象】主体：{extract.get('org','')}，日期/年度：{extract.get('year','')}，类型：{extract.get('doc_type','')}。\n关键要点：{extract.get('key_points','')}\n\n以下研判必须与此一致。\n\n"
                    facts = f"""{anchor}【用户上传的种子材料（供参考）】
---
{doc_text[:15000]}
---
【以上为种子材料】"""
                    evidence_items = []
                else:
                    st.session_state.doc_subject = {}
                    facts, evidence_items = get_evidence_items(event)
                st.session_state.event = event
                hist_ref = st.session_state.get("history_ref") or ""
                if hist_ref:
                    facts = (facts or "") + "\n\n[历史推演参考]\n" + hist_ref
                st.session_state.facts = facts
                st.session_state.evidence_items = evidence_items
                factors, factor_map = extract_evidence_factors_from_items(evidence_items, facts)
                st.session_state.evidence_factor_map = factor_map
                st.session_state.init_factors = factors
                st.session_state.decay_schedule = compute_decay_schedule(
                    evidence_items,
                    int(effective_steps),
                    float(st.session_state.hf_params.get("step_hours", 12.0)),
                    (st.session_state.hf_params.get("decay_scales") or {}),
                )
                st.session_state.time_axis = build_time_axis(
                    int(effective_steps),
                    float(st.session_state.hf_params.get("step_hours", 12.0)),
                    st.session_state.hf_params,
                )

                s.update(label="📊 初始化社会矩阵")
                matrix = init_state(event, facts)
                st.session_state.matrix_history = [matrix]

                s.update(label="🚚 初始化资源调度系统")
                resources = init_resources()
                st.session_state.resources = [resources]
                st.session_state.audit_log = []
                infra = init_infrastructure(factors)
                st.session_state.infra_history = [infra]

                s.update(label="🔗 生成因果链")
                chain = gen_causal(event)
                st.session_state.causal_chain = chain

                swan_trigger_step = int(st.session_state.get("swan_trigger_step") or 0)
                swan_trigger_risk = int(st.session_state.get("swan_trigger_risk") or 0)
                if enable_swan and swan_trigger_step == 0:
                    s.update(label="🦢 生成黑天鹅")
                    swan = gen_black_swan(event)
                    st.session_state.swan = swan
                elif enable_swan and swan_trigger_step > 0:
                    st.session_state.swan = f"待定（将在第{swan_trigger_step}步评估）"
                    st.session_state.swan_trigger_step = swan_trigger_step
                    st.session_state.swan_trigger_risk = swan_trigger_risk
                else:
                    st.session_state.swan = "无黑天鹅"

                use_stepping = True  # 逐步与连续均进控制台，支持暂停/继续
                st.session_state.sim_phase = "stepping"
                st.session_state.stepping_effective_steps = effective_steps
                st.session_state.stepping_current_step = 0
                st.session_state.stepping_matrix = matrix
                st.session_state.stepping_resources = resources
                st.session_state.stepping_infra = infra
                st.session_state.stepping_factors = factors
                st.session_state.timeline = []
                st.session_state.continuous_mode = step_mode.startswith("连续运行")
                st.session_state.continuous_auto_run = False
                s.update(label="✅ 初始化完成，请在下方控制台逐步执行或连续运行", state="complete")
                st.session_state.timeline = []

                s.update(label="📝 生成研判报告")
                if sim_mode.startswith("高保真"):
                    # 在高保真模式下，将审计日志拼入提示，强化“可追溯”
                    audit_summary = json.dumps(st.session_state.audit_log, ensure_ascii=False)
                    report = gen_report(event, facts + "\n\n[机制审计日志摘要]\n" + audit_summary[:2500], timeline, st.session_state.get("swan",""), matrix, resources)
                else:
                    report = gen_report(event, facts, timeline, st.session_state.get("swan",""), matrix, resources)
                st.session_state.report = report
                _save_to_history(st.session_state.get("scenario_name",""), event, report, st.session_state.matrix_history)
                s.update(label="✅ 仿真完成", state="complete")
            st.success("仿真完成！" if not use_stepping else "初始化完成，请在下方逐步推演并干预。")
    except Exception as e:
        st.error(f"仿真流程异常：{str(e)}。请检查 API Key、Base URL 与网络后重试。")
        if "matrix_history" in st.session_state and st.session_state.matrix_history:
            pass
        else:
            st.session_state.timeline = []

# ---------------------- 结果展示 ----------------------
_dbg("17-结果展示分支")
# 创意模式：与政府/社会资源无关，仅展示生成内容
if st.session_state.get("run_mode") == "creative":
    st.divider()
    rel = st.session_state.get("event_relevance") or {}
    st.info(f"🧠 **智能判断**：{rel.get('reason', '与政府社会资源无关')}\n\n以下政府/社会相关板块已跳过：资源调度、基础设施、社会矩阵、干预策略、演化推演等。")
    st.subheader("📝 生成内容")
    st.markdown(f"<div class='report-card'>{st.session_state.get('creative_output', '')}</div>", unsafe_allow_html=True)
    if st.button("🔁 重置", key="reset_creative"):
        request_reset()
        st.rerun()

# 逐步推演模式：每步可干预，支持连续运行的暂停/继续
elif st.session_state.get("sim_phase") == "stepping" and st.session_state.get("run_mode") == "crisis":
    st.divider()
    st.subheader("⏳ 逐步推演控制台")
    eff = int(st.session_state.get("stepping_effective_steps") or 4)
    cur = int(st.session_state.get("stepping_current_step") or 0)
    matrix = st.session_state.get("stepping_matrix") or st.session_state.matrix_history[-1] if st.session_state.matrix_history else {}
    resources = st.session_state.get("stepping_resources") or st.session_state.resources[-1] if st.session_state.resources else {}
    infra = st.session_state.get("stepping_infra") or st.session_state.infra_history[-1] if st.session_state.infra_history else {}
    factors = st.session_state.get("stepping_factors") or {}
    facts = st.session_state.get("facts") or ""
    event = st.session_state.get("event") or ""
    continuous_mode = st.session_state.get("continuous_mode", False)
    continuous_auto_run = st.session_state.get("continuous_auto_run", False)

    def _run_one_step(next_step, step_intervention, step_injected, matrix, resources, infra, factors):
        event_ctx = event
        if step_injected and str(step_injected).strip():
            event_ctx = event + "\n[本步注入]" + str(step_injected).strip()
            inj_factors = extract_evidence_factors(str(step_injected))
            factors = {k: min(1.0, v + 0.25 * inj_factors.get(k, 0)) for k, v in factors.items()}
        if sim_mode.startswith("高保真"):
            prev = matrix
            matrix, resources, infra, audit = mechanistic_step(
                matrix, resources, factors, step_intervention, next_step, infra,
                st.session_state.hf_params, st.session_state.evidence_items,
                st.session_state.evidence_factor_map, st.session_state.decay_schedule,
                st.session_state.time_axis,
            )
            st.session_state.audit_log.append(audit)
            evo = narrate_from_mechanism(event_ctx, facts, next_step, step_intervention, matrix, prev, resources, audit)
            timeline = st.session_state.get("timeline") or []
            timeline.append({"step": next_step, "data": evo, "audit": audit, "state": matrix, "resources": resources, "infra": infra})
        else:
            evo = evolve_step(event_ctx, facts, matrix, next_step, step_intervention, resources)
            timeline = st.session_state.get("timeline") or []
            timeline.append({"step": next_step, "data": evo})
            matrix = update_state(matrix, evo, step_intervention)
            resources = update_resources(resources)
        st.session_state.timeline = timeline
        st.session_state.matrix_history = st.session_state.matrix_history + [matrix]
        st.session_state.resources = st.session_state.resources + [resources]
        st.session_state.stepping_matrix = matrix
        st.session_state.stepping_resources = resources
        st.session_state.stepping_infra = infra
        st.session_state.stepping_current_step = next_step
        swan_step = int(st.session_state.get("swan_trigger_step") or 0)
        swan_risk = int(st.session_state.get("swan_trigger_risk") or 0)
        if enable_swan and swan_step > 0 and next_step == swan_step:
            if swan_risk == 0 or matrix.get("动荡风险", 0) >= swan_risk:
                st.session_state.swan = gen_black_swan(event)
            else:
                st.session_state.swan = "无黑天鹅（动荡未达阈值）"
        if next_step >= eff:
            report = gen_report(event, facts, st.session_state.timeline, st.session_state.get("swan",""), matrix, resources)
            st.session_state.report = report
            _save_to_history(st.session_state.get("scenario_name",""), event, report, st.session_state.matrix_history)
            st.session_state.sim_phase = "complete"
        if sim_mode.startswith("高保真"):
            st.session_state.infra_history = st.session_state.get("infra_history") or []
            st.session_state.infra_history.append(infra)
        return matrix, resources, infra

    # 连续模式自动步进：在渲染前执行一步，渲染后根据是否继续决定是否 rerun
    if continuous_mode and continuous_auto_run and cur < eff and matrix:
        step_intervention = st.session_state.get("step_intervention", "无")
        step_injected = st.session_state.get("step_injected", "") or ""
        next_step = cur + 1
        with st.spinner(f"连续运行中：第 {next_step}/{eff} 步..."):
            _run_one_step(next_step, step_intervention, step_injected, matrix, resources, infra, factors)
        cur = st.session_state.stepping_current_step
        matrix = st.session_state.stepping_matrix
        resources = st.session_state.stepping_resources
        infra = st.session_state.stepping_infra

    if cur < eff and matrix:
        next_step = cur + 1
        st.info(f"将执行第 **{next_step}** 步（共 {eff} 步）" + ("（连续运行中，可随时⏸️暂停）" if continuous_mode and continuous_auto_run else ""))
        step_col1, step_col2 = st.columns(2)
        with step_col1:
            step_intervention = st.selectbox("本步干预策略", ["无","紧急物资投放","媒体安抚","加强安保","全城宵禁","电力抢修"], key="step_intervention")
        with step_col2:
            step_injected = st.text_input("注入事件（可选）", placeholder="如：突发火灾、谣言扩散等，留空则无", key="step_injected")
        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
        with btn_col1:
            step_next = st.button("▶️ 执行下一步", type="primary", key="step_next_btn")
        with btn_col2:
            run_rest = st.button(f"▶️ 连续运行剩余{eff - cur}步", key="continuous_run_btn") if continuous_mode else False
        with btn_col3:
            if continuous_mode and continuous_auto_run:
                if st.button("⏸️ 暂停", key="pause_btn"):
                    st.session_state.continuous_auto_run = False
                    st.rerun()
        if step_next:
            with st.spinner(f"正在执行第 {next_step} 步..."):
                _run_one_step(next_step, step_intervention, step_injected, matrix, resources, infra, factors)
            st.rerun()
        if continuous_mode and run_rest:
            st.session_state.continuous_auto_run = True
            st.rerun()
        # 连续模式：若自动运行中且还有剩余步数，自动触发下一轮以继续推演
        if continuous_mode and continuous_auto_run and cur < eff:
            st.rerun()
    else:
        if cur >= eff and not st.session_state.get("report"):
            timeline = st.session_state.get("timeline") or []
            m = st.session_state.stepping_matrix or (st.session_state.matrix_history[-1] if st.session_state.matrix_history else {})
            r = st.session_state.stepping_resources or (st.session_state.resources[-1] if st.session_state.resources else {})
            st.session_state.report = gen_report(event, facts, timeline, st.session_state.get("swan",""), m, r)
            st.session_state.sim_phase = "complete"
        st.rerun()

# 危机推演模式：完整展示
elif st.session_state.timeline:
    st.divider()
    subj = st.session_state.get("doc_subject") or {}
    if subj.get("org") or subj.get("company") or subj.get("year"):
        st.info(f"📄 **系统识别的分析对象**：{subj.get('org','') or subj.get('company','')}，{subj.get('year','')} | {subj.get('doc_type','')}")
    st.subheader("📺 实时态势总面板")

    # 1. 状态指标
    m = st.session_state.matrix_history[-1]
    m_cols = st.columns(4)
    labels = ["行政效能","焦虑指数","资源缺口","动荡风险"]
    colors = ["#58a6ff","#f8c447","#f85149","#e34c26"]
    for i,k in enumerate(labels):
        m_cols[i].markdown(f"""
<div class='metric-card'>
{labels[i]}<br>
<h2 style='color:{colors[i]}'>{m[k]}%</h2>
</div>
""", unsafe_allow_html=True)

    # 2. 资源调度面板（展示名称根据事件动态生成，体现灵活分析）
    st.subheader("🚚 资源与兵力调度面板")
    r = st.session_state.resources[-1]
    r_cols = st.columns(6)
    res_display = st.session_state.get("resource_display_map") or {}
    r_keys = list(r.keys())
    for i, k in enumerate(r_keys):
        label = res_display.get(k, k)
        r_cols[i].markdown(f"""
<div class='resource-card'>
{label}<br>
<h3>{r[k]}%</h3>
</div>
""", unsafe_allow_html=True)

    # 2.1 基础设施子系统（高保真模式，展示名称根据事件动态生成）
    if sim_mode.startswith("高保真") and st.session_state.get("infra_history"):
        st.subheader("🏗️ 基础设施子系统面板（高保真）")
        inf = st.session_state.infra_history[-1]
        inf_cols = st.columns(4)
        inf_keys = ["电力", "通信", "交通", "供水"]
        inf_display = st.session_state.get("infra_display_map") or {}
        for i, k in enumerate(inf_keys):
            label = inf_display.get(k, k)
            inf_cols[i].markdown(
                f"""
<div class='resource-card'>
{label}<br>
<h3>{inf.get(k, 0)}%</h3>
</div>
""",
                unsafe_allow_html=True,
            )

    # 3. 时序曲线 + 雷达图
    st.subheader("📈 指标演化曲线 & 风险雷达图")
    g1,g2 = st.columns(2)
    with g1:
        df = pd.DataFrame(st.session_state.matrix_history)
        fig = go.Figure()
        for idx,col in enumerate(df.columns):
            fig.add_trace(go.Scatter(y=df[col], name=col, line=dict(color=colors[idx])))
        fig.update_layout(height=350, paper_bgcolor="#161b22", font=dict(color="#e0e0e0"))
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        fig = go.Figure(go.Scatterpolar(r=list(m.values()), theta=list(m.keys()), fill="toself", fillcolor="rgba(31,111,235,0.3)"))
        fig.update_layout(polar=dict(radialaxis=dict(range=[0,100])), height=350, paper_bgcolor="#0e1117", font=dict(color="white"))
        st.plotly_chart(fig, use_container_width=True)

    # 3.1 关键节点摘要
    st.subheader("📌 关键节点摘要")
    df_m = pd.DataFrame(st.session_state.matrix_history)
    step_labels = ["初始"] + [f"第{i}步" for i in range(1, len(df_m))]
    df_m.insert(0, "阶段", step_labels)
    max_risk_step = df_m["动荡风险"].idxmax()
    max_anxiety_step = df_m["焦虑指数"].idxmax()
    key_cols = st.columns(4)
    key_cols[0].metric("动荡风险峰值阶段", step_labels[max_risk_step], f"值 {df_m.loc[max_risk_step, '动荡风险']:.0f}")
    key_cols[1].metric("焦虑指数峰值阶段", step_labels[max_anxiety_step], f"值 {df_m.loc[max_anxiety_step, '焦虑指数']:.0f}")
    key_cols[2].metric("最终行政效能", f"{m['行政效能']}%", "当前步")
    key_cols[3].metric("最终资源缺口", f"{m['资源缺口']}%", "当前步")

    # 3.2 分支对比（如有分支）
    branches = st.session_state.get("scenario_branches") or []
    if branches:
        st.subheader("🌿 分支对比")
        tab_names = ["主路径"] + [b.get("name", f"分支{i+1}") for i, b in enumerate(branches)]
        tabs = st.tabs(tab_names)
        with tabs[0]:
            df_main = pd.DataFrame(st.session_state.matrix_history)
            fig = go.Figure()
            for idx, col in enumerate(df_main.columns):
                fig.add_trace(go.Scatter(y=df_main[col], name=col, line=dict(color=colors[idx % len(colors)])))
            fig.update_layout(height=280, title="主路径指标演化")
            st.plotly_chart(fig, use_container_width=True)
        for i, b in enumerate(branches):
            with tabs[i + 1]:
                df_b = pd.DataFrame(b.get("matrix_history", []))
                if not df_b.empty:
                    fig_b = go.Figure()
                    for idx, col in enumerate(df_b.columns):
                        fig_b.add_trace(go.Scatter(y=df_b[col], name=col, line=dict(color=colors[idx % len(colors)])))
                    fig_b.update_layout(height=280, title=f"分支：{b.get('intervention','')}")
                    st.plotly_chart(fig_b, use_container_width=True)
                st.caption(f"从第 {b.get('fork_step',0)+1} 步起采用「{b.get('intervention','')}」")
                if st.button(f"删除此分支", key=f"del_branch_{i}"):
                    branches.pop(i)
                    st.session_state.scenario_branches = branches
                    st.rerun()

    # 4. 多智能体对抗视图
    st.divider()
    st.subheader("🏛️ 多智能体对抗视图")
    last_evo = st.session_state.timeline[-1]["data"]
    a_cols = st.columns(3)
    with a_cols[0]:
        st.markdown(f"<div class='agent-card'><h4>🏛️ 官方</h4><p>{last_evo.get('official', '—')}</p></div>", unsafe_allow_html=True)
    with a_cols[1]:
        st.markdown(f"<div class='agent-card'><h4>👥 民众</h4><p>{last_evo.get('citizen', '—')}</p></div>", unsafe_allow_html=True)
    with a_cols[2]:
        st.markdown(f"<div class='agent-card'><h4>📺 媒体</h4><p>{last_evo.get('media', '—')}</p></div>", unsafe_allow_html=True)

    # 4.1 与视角对话（支持按步选择）
    st.divider()
    st.subheader("💬 与视角对话")
    st.caption("选择步骤与视角，向该步骤下的该视角提问；系统基于该步的叙事与立场作答")
    if st.session_state.get("perspective_chat_history"):
        if st.button("清空对话记录", key="clear_chat"):
            st.session_state.perspective_chat_history = []
            st.rerun()
    tl = st.session_state.get("timeline") or []
    max_step_idx = len(tl) - 1
    chat_col1, chat_col2, chat_col3 = st.columns([1, 1, 2])
    with chat_col1:
        chat_step_options = [f"第{i+1}步" for i in range(max_step_idx + 1)]
        chat_step_idx = st.selectbox("选择步骤", range(max_step_idx + 1), format_func=lambda x: chat_step_options[x], key="chat_step_select")
    with chat_col2:
        chat_perspective = st.selectbox("选择视角", ["官方", "民众", "媒体", "审计"], key="chat_perspective")
    with chat_col3:
        chat_q = st.chat_input("输入您的问题，如：为什么采取这一策略？民众反应如何？")
    if chat_q:
        nav_map = {"官方": "official", "民众": "citizen", "媒体": "media", "审计": "audit"}
        nav_key = nav_map.get(chat_perspective, "official")
        step_data = tl[chat_step_idx]["data"] if chat_step_idx < len(tl) else last_evo
        narrative = step_data.get(nav_key, "")
        step_state = tl[chat_step_idx].get("state", m) if chat_step_idx < len(tl) and "state" in tl[chat_step_idx] else m
        step_res = tl[chat_step_idx].get("resources", st.session_state.resources[-1]) if chat_step_idx < len(tl) and "resources" in tl[chat_step_idx] else (st.session_state.resources[chat_step_idx] if chat_step_idx < len(st.session_state.resources) else st.session_state.resources[-1])
        ctx = f"事件：{event}\n第{chat_step_idx+1}步状态：{step_state}\n资源：{step_res}"
        reply = chat_with_perspective(chat_perspective, narrative, chat_q, ctx)
        hist = st.session_state.get("perspective_chat_history") or []
        hist.append({"role": "user", "content": chat_q, "perspective": chat_perspective, "step": chat_step_idx + 1})
        hist.append({"role": "assistant", "content": reply, "perspective": chat_perspective, "step": chat_step_idx + 1})
        st.session_state.perspective_chat_history = hist[-20:]
        st.rerun()
    for h in (st.session_state.get("perspective_chat_history") or []):
        with st.chat_message("user" if h["role"] == "user" else "assistant"):
            st.caption(f"【第{h.get('step','')}步·{h.get('perspective','')}视角】")
            st.write(h["content"])

    # 5. 推演回放
    st.divider()
    st.subheader("⏪ 演化推演回放")
    max_step = len(st.session_state.timeline) - 1
    # 自动播放：每轮 rerun 推进一帧，直到结束
    if st.session_state.get("autoplay_running"):
        idx = min(st.session_state.playback_index + 1, max_step)
        st.session_state.playback_index = idx
        if idx >= max_step:
            st.session_state.autoplay_running = False
        time.sleep(1.2)
        st.rerun()
    pb_cols = st.columns([4,1])
    with pb_cols[0]:
        playback = st.slider("回放阶段", 0, max_step, st.session_state.playback_index, key="playback_slider")
    with pb_cols[1]:
        st.markdown("<br>", unsafe_allow_html=True)
        auto = st.button("▶️ 自动播放")
    if auto:
        st.session_state.autoplay_running = True
        st.session_state.playback_index = 0
        st.rerun()
    st.session_state.playback_index = playback
    play_data = st.session_state.timeline[playback]["data"]
    # 场景分支：从当前步创建分支
    with st.expander("🌿 从本步创建分支（对比不同干预路径）", expanded=False):
        branch_interv = st.selectbox("假设从本步起改用干预策略", ["无","紧急物资投放","媒体安抚","加强安保","全城宵禁","电力抢修"], key="branch_intervention")
        branch_name = st.text_input("分支名称（可选）", value=f"第{playback+1}步起→{branch_interv}", key="branch_name")
        if st.button("创建并推演分支", key="create_branch_btn"):
            with st.spinner("正在推演分支..."):
                branch_data = run_branch_from_step(playback, branch_interv, event, st.session_state.get("facts",""))
                branch_data["name"] = branch_name or f"分支-第{playback+1}步起→{branch_interv}"
                st.session_state.scenario_branches = st.session_state.get("scenario_branches") or []
                st.session_state.scenario_branches.append(branch_data)
                st.success(f"分支「{branch_name}」推演完成，可在下方查看对比")
                st.rerun()
    st.info(f"📌 第 {playback+1} 阶段 演化内容")
    st.markdown(f"**官方**：{play_data.get('official', '—')}")
    st.markdown(f"**民众**：{play_data.get('citizen', '—')}")
    st.markdown(f"**媒体**：{play_data.get('media', '—')}")
    st.markdown(f"**审计**：{play_data.get('audit', '—')}")

    # 5.1 实体与知识图
    with st.expander("🕸️ 实体与知识图谱", expanded=False):
        if st.button("提取实体与关系", key="extract_entities_btn"):
            with st.spinner("正在抽取..."):
                eg = extract_entity_graph(event, st.session_state.get("facts",""))
                st.session_state.entity_graph = eg
        eg = st.session_state.get("entity_graph") or {}
        if eg.get("entities") or eg.get("relations"):
            e_col1, e_col2 = st.columns(2)
            with e_col1:
                st.markdown("**实体**")
                for ent in eg.get("entities", []):
                    st.write(f"- {ent.get('name','')}（{ent.get('type','')}）")
            with e_col2:
                st.markdown("**关系**")
                for rel in eg.get("relations", []):
                    st.write(f"- {rel.get('source','')} → {rel.get('target','')}：{rel.get('relation','')}")
            # 简单网络图（需 networkx，可选）
            try:
                import networkx as nx
                G = nx.DiGraph()
                for e in eg.get("entities", []):
                    G.add_node(e.get("name", ""), type=e.get("type", ""))
                for r in eg.get("relations", []):
                    G.add_edge(r.get("source",""), r.get("target",""), label=r.get("relation",""))
                if G.number_of_nodes() > 0:
                    pos = nx.spring_layout(G, seed=42)
                    edge_trace = go.Scatter(x=[], y=[], line=dict(width=1, color="#888"), hoverinfo="text", mode="lines")
                    node_trace = go.Scatter(x=[], y=[], text=[], mode="markers+text", marker=dict(size=20, color="#58a6ff"), textposition="top center")
                    for e in G.edges():
                        x0, y0 = pos[e[0]]
                        x1, y1 = pos[e[1]]
                        edge_trace["x"] += (x0, x1, None)
                        edge_trace["y"] += (y0, y1, None)
                    for n in G.nodes():
                        node_trace["x"] += (pos[n][0],)
                        node_trace["y"] += (pos[n][1],)
                        node_trace["text"] += (n,)
                    fig_g = go.Figure(data=[edge_trace, node_trace])
                    fig_g.update_layout(title="知识图谱", showlegend=False, height=300)
                    st.plotly_chart(fig_g, use_container_width=True)
            except ImportError:
                st.caption("安装 networkx 可显示图谱：pip install networkx")

    # 6. 因果链 + 黑天鹅
    st.divider()
    st.subheader("🔗 深度因果演化链")
    st.markdown(f"<div class='logic-box'>{st.session_state.causal_chain}</div>", unsafe_allow_html=True)
    st.error(f"🦢 黑天鹅事件：{st.session_state.swan}")
    st.warning(f"🛡️ 系统审计：{last_evo.get('audit', '—')}")
    if sim_mode.startswith("高保真") and st.session_state.get("audit_log"):
        with st.expander("🧾 机制审计日志（高保真模式）", expanded=False):
            st.json(st.session_state.audit_log)
    if sim_mode.startswith("高保真") and st.session_state.get("evidence_items"):
        with st.expander("📎 证据清单（可引用）", expanded=False):
            st.json(st.session_state.evidence_items)
    if sim_mode.startswith("高保真") and st.session_state.get("evidence_factor_map"):
        with st.expander("🧩 证据→因子映射（高保真）", expanded=False):
            st.json(st.session_state.evidence_factor_map)
            conf = (st.session_state.evidence_factor_map or {}).get("confidence", {})
            if conf:
                st.caption("因子置信度（由 top 证据贡献合成，范围 0~1，越高表示证据支持越强）")
                st.json(conf)
            conflicts = (st.session_state.evidence_factor_map or {}).get("conflicts", {})
            if conflicts:
                st.caption("冲突检测（counter≥0.6*support 或 counter≥0.15 视为存在冲突）")
                st.json(conflicts)
    if sim_mode.startswith("高保真") and st.session_state.get("decay_schedule"):
        with st.expander("⏳ 冲击衰减曲线（高保真）", expanded=False):
            st.json(st.session_state.decay_schedule.get("_meta", {}))
    if sim_mode.startswith("高保真") and st.session_state.get("time_axis"):
        with st.expander("🕒 时间轴（高保真）", expanded=False):
            st.json(st.session_state.time_axis)
    if sim_mode.startswith("高保真") and st.session_state.get("hf_params"):
        hp = st.session_state.get("hf_params") or {}
        if hp.get("auto_steps_by_duration") and int(hp.get("total_duration_hours") or 0) > 0:
            st.caption(f"时间设定（高保真）：总时长={int(hp['total_duration_hours'])}h，每步={float(hp.get('step_hours', 12.0))}h（步数自动计算并可能上限为 24）")

    # 7. 报告 + 导出
    st.divider()
    st.subheader("📝 国家级战略研判报告")
    report_title = f"**场景：{st.session_state.get('scenario_name', '未命名')}**\n\n" if st.session_state.get("scenario_name") else ""
    st.markdown(f"<div class='report-card'>{report_title}{st.session_state.report}</div>", unsafe_allow_html=True)

    # 导出区
    d_cols = st.columns(4)
    with d_cols[0]:
        doc_text = st.session_state.get("uploaded_doc_text") or ""
        doc_summary = doc_text[:1500] + ("..." if len(doc_text) > 1500 else "") if doc_text and not doc_text.startswith("[") else ""
        json_data = json.dumps({
            "scenario_name": st.session_state.get("scenario_name", ""),
            "event": event, "facts": st.session_state.facts,
            "matrix": st.session_state.matrix_history,
            "timeline": st.session_state.timeline,
            "report": st.session_state.report,
            "seed_document_summary": doc_summary,
            "audit_log": st.session_state.get("audit_log", []),
            "evidence_items": st.session_state.get("evidence_items", []),
            "evidence_factor_map": st.session_state.get("evidence_factor_map", {}),
            "decay_schedule": st.session_state.get("decay_schedule", {}),
            "time_axis": st.session_state.get("time_axis", {}),
            "infra_history": st.session_state.get("infra_history", []),
            "hf_params": st.session_state.get("hf_params", {}),
            "resource_display_map": st.session_state.get("resource_display_map", {}),
            "infra_display_map": st.session_state.get("infra_display_map", {}),
        }, ensure_ascii=False, indent=2)
        fname_json = (st.session_state.get("scenario_name") or "SHENCE").replace(" ", "_") + "_数据.json"
        st.download_button("💾 导出JSON数据包", json_data, fname_json, use_container_width=True)
    with d_cols[1]:
        csv_df = pd.DataFrame(st.session_state.matrix_history)
        csv_df.insert(0, "阶段", ["初始"] + [f"第{i}步" for i in range(1, len(csv_df))])
        fname_csv = (st.session_state.get("scenario_name") or "SHENCE").replace(" ", "_") + "_指标演化.csv"
        st.download_button("📊 导出指标CSV", csv_df.to_csv(index=False).encode("utf-8-sig"), fname_csv, "text/csv", use_container_width=True)
    with d_cols[2]:
        pdf_report = (report_title + st.session_state.report) if st.session_state.get("scenario_name") else st.session_state.report
        pdf_doc_appendix = (st.session_state.get("uploaded_doc_text") or "")[:4000]
        if pdf_doc_appendix and pdf_doc_appendix.startswith("["):
            pdf_doc_appendix = ""
        st.download_button("📄 导出PDF报告", export_pdf(pdf_report, pdf_doc_appendix), (st.session_state.get("scenario_name") or "SHENCE").replace(" ", "_") + "_研判报告.pdf", use_container_width=True)
    with d_cols[3]:
        if st.button("🔁 重置仿真", use_container_width=True, key="reset_bottom"):
            request_reset()
            st.rerun()

elif not client:
    st.warning("请在左侧填写 API Key 后启动仿真")
_dbg("18-脚本执行完毕")
