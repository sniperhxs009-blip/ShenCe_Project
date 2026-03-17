import streamlit as st
from openai import OpenAI
import json
import plotly.graph_objects as go
import requests
import random
from datetime import datetime
import pandas as pd
from fpdf import FPDF
import io
import time
import re
import math

# --- 页面配置 ---
st.set_page_config(page_title="SHENCE 3.0 | 社会演化仿真旗舰版", layout="wide", initial_sidebar_state="expanded")

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

# --- 侧边栏 API ---
st.sidebar.header("🔑 API 配置")
openai_key = st.sidebar.text_input("DeepSeek API Key（兼容 OpenAI SDK）", type="password")
base_url = st.sidebar.text_input("Base URL", value="https://api.deepseek.com/v1")
serper_key = st.sidebar.text_input("Serper API Key", type="password")

client = None
if openai_key:
    client = OpenAI(api_key=openai_key, base_url=base_url)

# --- 仿真模式与可复现性 ---
st.sidebar.header("🧪 仿真模式")
sim_mode = st.sidebar.selectbox(
    "模式",
    ["高保真（机制内核 + 可审计）", "叙事（AI 主导）"],
    help="高保真模式：指标与资源由机制模型计算，AI 仅做文字解读并受审计约束；叙事模式：主要由模型生成并辅以随机扰动。"
)
seed = st.sidebar.number_input("随机种子（可复现）", min_value=0, max_value=10_000_000, value=2026, step=1)

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

# --- 会话状态 ---
init_keys = [
    "event", "facts", "matrix_history", "timeline", "report",
    "agents", "resources", "swan", "causal_chain", "playback_index",
    "reset_requested", "autoplay_running", "scenario_name",
    "audit_log", "evidence_items", "infra_history", "hf_params",
    "evidence_factor_map",
    "decay_schedule"
    , "time_axis"
]
for k in init_keys:
    if k not in st.session_state:
        st.session_state[k] = [] if k in ["timeline", "matrix_history", "audit_log", "evidence_items", "infra_history"] else (False if k in ["reset_requested", "autoplay_running"] else "")

st.session_state.hf_params = hf_params

if st.session_state.get("playback_index") is None or not isinstance(st.session_state.get("playback_index"), int):
    st.session_state.playback_index = 0

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
    prompt = f"事件：{event}\n事实：{facts}\n返回JSON（0-100）：行政效能、焦虑指数、资源缺口、动荡风险"
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
    prompt = f"""
你是国家级战略安全顾问，生成正式研判报告：
事件：{event}
实证：{facts}
演化时序：{timeline}
黑天鹅：{swan}
社会状态：{matrix}
资源状态：{resources}
报告必须包含：
1. 事件定级 2. 物理瘫痪分析 3. 社会临界点 4. 演化复盘 5. 风险预警 6. 干预建议 7. 结论
"""
    try:
        return client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], timeout=60).choices[0].message.content
    except Exception as e:
        return f"【报告生成异常】API 调用失败：{str(e)[:120]}\n请检查网络与 API 配置后重新运行仿真并导出报告。"

def export_pdf(report):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    try:
        pdf.multi_cell(0, 10, report)
    except Exception:
        pdf.multi_cell(0, 10, report.encode("latin-1", errors="replace").decode("latin-1"))
    return bytes(pdf.output(dest='S'))

# ---------------------- 主界面 ----------------------
st.title("🛡️ SHENCE 3.0 | MiroFish 级社会演化仿真旗舰系统")

# 可选：场景名称（用于报告与导出）
scenario_name = st.text_input("📌 场景名称（可选）", value=st.session_state.get("scenario_name", ""), placeholder="如：2024 某市断水断电推演")
if scenario_name:
    st.session_state.scenario_name = scenario_name

# 场景模板
templates = {
    "城市断水断电48小时": "一线城市核心区域停电停水，通信不稳，恐慌抢购",
    "粮食供应链中断7天": "粮食运输受阻，米面油库存下降，物价上涨",
    "区域金融挤兑": "地方银行流动性危机，居民集中取现，支付承压",
    "省级网络切断": "互联网出口中断，移动通信不稳，信息传播失控"
}
st.subheader("📋 快速场景模板")
t_cols = st.columns(4)
for i,(name,val) in enumerate(templates.items()):
    if t_cols[i].button(f"🚨 {name}", use_container_width=True):
        st.session_state.event = val

# 事件输入
event = st.text_area("📡 初始扰动事件", value=st.session_state.get("event",""), height=80)

# 控制面板
with st.expander("⚙️ 仿真控制面板", expanded=True):
    c1,c2,c3 = st.columns(3)
    with c1:
        steps = st.slider("演化步数", 1, 8, 4)
    with c2:
        intervention = st.selectbox("🎯 官方干预策略", [
            "无","紧急物资投放","媒体安抚","加强安保","全城宵禁","电力抢修"
        ], help="无/物资/媒体/安保/宵禁/电力，不同策略会改变社会矩阵演化系数")
    with c3:
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
if run and client and event:
    try:
        random.seed(int(seed))
        effective_steps = int(steps)
        if sim_mode.startswith("高保真"):
            hp = st.session_state.get("hf_params", {}) or {}
            if hp.get("auto_steps_by_duration") and int(hp.get("total_duration_hours") or 0) > 0:
                sh = float(hp.get("step_hours") or 12.0)
                effective_steps = max(1, int(math.ceil(int(hp["total_duration_hours"]) / max(1.0, sh))))
                # 防止一次跑太多导致耗时/费用过高（不影响原功能：只是高保真新增能力的保护）
                if effective_steps > 24:
                    effective_steps = 24
        with st.status("✅ 仿真启动中...", expanded=True) as s:
            s.update(label="🌐 检索实证案例")
            facts, evidence_items = get_evidence_items(event)
            st.session_state.facts = facts
            st.session_state.evidence_items = evidence_items
            factors, factor_map = extract_evidence_factors_from_items(evidence_items, facts)
            st.session_state.evidence_factor_map = factor_map
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

            s.update(label="🦢 生成黑天鹅")
            swan = gen_black_swan(event) if enable_swan else "无黑天鹅"
            st.session_state.swan = swan

            s.update(label=f"🔄 执行 {effective_steps} 步演化")
            timeline = []
            for i in range(1, effective_steps+1):
                if sim_mode.startswith("高保真"):
                    prev = matrix
                    matrix, resources, infra, audit = mechanistic_step(
                        matrix,
                        resources,
                        factors,
                        intervention,
                        i,
                        infra,
                        st.session_state.hf_params,
                        st.session_state.evidence_items,
                        st.session_state.evidence_factor_map,
                        st.session_state.decay_schedule,
                        st.session_state.time_axis,
                    )
                    st.session_state.audit_log.append(audit)
                    evo = narrate_from_mechanism(event, facts, i, intervention, matrix, prev, resources, audit)
                    timeline.append({"step": i, "data": evo, "audit": audit, "state": matrix, "resources": resources, "infra": infra})
                else:
                    evo = evolve_step(event, facts, matrix, i, intervention, resources)
                    timeline.append({"step": i, "data": evo})
                    matrix = update_state(matrix, evo, intervention)
                    resources = update_resources(resources)
                st.session_state.matrix_history.append(matrix)
                st.session_state.resources.append(resources)
                if sim_mode.startswith("高保真"):
                    st.session_state.infra_history.append(infra)
                time.sleep(0.2)
            st.session_state.timeline = timeline

            s.update(label="📝 生成研判报告")
            if sim_mode.startswith("高保真"):
                # 在高保真模式下，将审计日志拼入提示，强化“可追溯”
                audit_summary = json.dumps(st.session_state.audit_log, ensure_ascii=False)
                report = gen_report(event, facts + "\n\n[机制审计日志摘要]\n" + audit_summary[:2500], timeline, swan, matrix, resources)
            else:
                report = gen_report(event, facts, timeline, swan, matrix, resources)
            st.session_state.report = report
            s.update(label="✅ 仿真完成", state="complete")
            st.success("仿真完成！")
    except Exception as e:
        st.error(f"仿真流程异常：{str(e)}。请检查 API Key、Base URL 与网络后重试。")
        if "matrix_history" in st.session_state and st.session_state.matrix_history:
            pass
        else:
            st.session_state.timeline = []

# ---------------------- 结果展示 ----------------------
if st.session_state.timeline:
    st.divider()
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

    # 2. 资源调度面板
    st.subheader("🚚 资源与兵力调度面板")
    r = st.session_state.resources[-1]
    r_cols = st.columns(6)
    r_keys = list(r.keys())
    for i,k in enumerate(r_keys):
        r_cols[i].markdown(f"""
<div class='resource-card'>
{list(r.keys())[i]}<br>
<h3>{r[k]}%</h3>
</div>
""", unsafe_allow_html=True)

    # 2.1 基础设施子系统（高保真模式）
    if sim_mode.startswith("高保真") and st.session_state.get("infra_history"):
        st.subheader("🏗️ 基础设施子系统面板（高保真）")
        inf = st.session_state.infra_history[-1]
        inf_cols = st.columns(4)
        inf_keys = ["电力", "通信", "交通", "供水"]
        for i, k in enumerate(inf_keys):
            inf_cols[i].markdown(
                f"""
<div class='resource-card'>
{k}<br>
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
    # 同步 slider 与 session 的 playback_index
    st.session_state.playback_index = playback
    play_data = st.session_state.timeline[playback]["data"]
    st.info(f"📌 第 {playback+1} 阶段 演化内容")
    st.markdown(f"**官方**：{play_data.get('official', '—')}")
    st.markdown(f"**民众**：{play_data.get('citizen', '—')}")
    st.markdown(f"**媒体**：{play_data.get('media', '—')}")
    st.markdown(f"**审计**：{play_data.get('audit', '—')}")

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
        json_data = json.dumps({
            "scenario_name": st.session_state.get("scenario_name", ""),
            "event": event, "facts": st.session_state.facts,
            "matrix": st.session_state.matrix_history,
            "timeline": st.session_state.timeline,
            "report": st.session_state.report,
            "audit_log": st.session_state.get("audit_log", []),
            "evidence_items": st.session_state.get("evidence_items", []),
            "evidence_factor_map": st.session_state.get("evidence_factor_map", {}),
            "decay_schedule": st.session_state.get("decay_schedule", {}),
            "time_axis": st.session_state.get("time_axis", {}),
            "infra_history": st.session_state.get("infra_history", []),
            "hf_params": st.session_state.get("hf_params", {}),
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
        st.download_button("📄 导出PDF报告", export_pdf(pdf_report), (st.session_state.get("scenario_name") or "SHENCE").replace(" ", "_") + "_研判报告.pdf", use_container_width=True)
    with d_cols[3]:
        if st.button("🔁 重置仿真", use_container_width=True, key="reset_bottom"):
            request_reset()
            st.rerun()

elif not client:
    st.warning("请在左侧填写 API Key 后启动仿真")
