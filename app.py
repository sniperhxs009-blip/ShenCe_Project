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

# --- 页面配置 ---
st.set_page_config(page_title="SHENCE 3.0 | 社会演化仿真旗舰版", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.block-container { max-width: 98% !important; padding: 1rem 2% !important; background-color: #0e1117; }
.stMarkdown, p, h3, h2, h1 { color: #e0e0e0 !important; }
.metric-card { 
    background-color: #161b22; padding: 20px; border-radius: 10px; 
    border: 1px solid #30363d; text-align: center;
}
.logic-box { 
    background-color: #0d1117; padding: 25px; border-left: 10px solid #58a6ff; 
    border-radius: 6px; margin: 20px 0; font-family: 'Consolas', monospace; 
    color: #8b949e; border: 1px solid #30363d;
}
.report-card { 
    background-color: #ffffff; padding: 40px; border-radius: 15px; color: #1a1a1a !important;
    border-top: 15px solid #1f6feb; box-shadow: 0 10px 40px rgba(0,0,0,0.5); 
}
.agent-card {
    background-color: #161b22; padding:15px; border-radius:10px; min-height:260px;
    border:1px solid #30363d; margin-bottom:10px;
}
.resource-card {
    background-color: #161b22; padding:15px; border-radius:10px;
    border:1px solid #30363d; margin-bottom:10px;
}
</style>
""", unsafe_allow_html=True)

# --- 侧边栏 API ---
st.sidebar.header("🔑 API 配置")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
base_url = st.sidebar.text_input("Base URL", value="https://api.ohmygpt.com/v1")
serper_key = st.sidebar.text_input("Serper API Key", type="password")

client = None
if openai_key:
    client = OpenAI(api_key=openai_key, base_url=base_url)

# --- 会话状态 ---
init_keys = [
    "event", "facts", "matrix_history", "timeline", "report",
    "agents", "resources", "swan", "causal_chain", "playback_index",
    "reset_requested", "autoplay_running", "scenario_name"
]
for k in init_keys:
    if k not in st.session_state:
        st.session_state[k] = [] if k in ["timeline", "matrix_history"] else (False if k in ["reset_requested", "autoplay_running"] else "")

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

def _default_matrix():
    return {"行政效能": 50, "焦虑指数": 50, "资源缺口": 50, "动荡风险": 50}

def init_state(event, facts):
    prompt = f"事件：{event}\n事实：{facts}\n返回JSON（0-100）：行政效能、焦虑指数、资源缺口、动荡风险"
    try:
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
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
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"}, timeout=30)
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
        return client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}]).choices[0].message.content
    except Exception as e:
        return f"[生成异常] 黑天鹅模块暂不可用：{str(e)[:60]}"

def gen_causal(event):
    try:
        prompt = f"为 {event} 生成PESTEL全维度因果链，结构化输出"
        return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}]).choices[0].message.content
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
        return client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}], timeout=60).choices[0].message.content
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
        with st.status("✅ 仿真启动中...", expanded=True) as s:
            s.update(label="🌐 检索实证案例")
            facts = get_evidence(event)
            st.session_state.facts = facts

            s.update(label="📊 初始化社会矩阵")
            matrix = init_state(event, facts)
            st.session_state.matrix_history = [matrix]

            s.update(label="🚚 初始化资源调度系统")
            resources = init_resources()
            st.session_state.resources = [resources]

            s.update(label="🔗 生成因果链")
            chain = gen_causal(event)
            st.session_state.causal_chain = chain

            s.update(label="🦢 生成黑天鹅")
            swan = gen_black_swan(event) if enable_swan else "无黑天鹅"
            st.session_state.swan = swan

            s.update(label=f"🔄 执行 {steps} 步演化")
            timeline = []
            for i in range(1, steps+1):
                evo = evolve_step(event, facts, matrix, i, intervention, resources)
                timeline.append({"step":i, "data":evo})
                matrix = update_state(matrix, evo, intervention)
                resources = update_resources(resources)
                st.session_state.matrix_history.append(matrix)
                st.session_state.resources.append(resources)
                time.sleep(0.2)
            st.session_state.timeline = timeline

            s.update(label="📝 生成研判报告")
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
            "report": st.session_state.report
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
