import streamlit as st
from openai import OpenAI
import requests
import json
import plotly.graph_objects as go
import pandas as pd
import re
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(page_title="神策 - 高保真全维度沙盘", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #ffffff; }
    .role-card { border: 1px solid #30363d; border-radius: 10px; padding: 15px; background: #161b22; min-height: 250px; }
    h3 { color: #00ffcc !important; font-size: 1.2rem; }
    .report-box { background-color: #161b22; padding: 25px; border-radius: 10px; border: 2px solid #00ffcc; line-height: 1.8; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 密钥读取 ---
DEEPSEEK_K = st.secrets["DEEPSEEK_API_KEY"]
SERPER_K = st.secrets["SERPER_API_KEY"]
client = OpenAI(api_key=DEEPSEEK_K, base_url="https://api.deepseek.com")

# --- 3. 核心功能函数 ---
def fetch_intelligence(query):
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": f"{query} 政策影响 动态 现状", "gl": "cn", "hl": "zh-cn", "num": 10})
    headers = {'X-API-KEY': SERPER_K, 'Content-Type': 'application/json'}
    try:
        res = requests.post(url, headers=headers, data=payload)
        return "\n".join([item.get('snippet') for item in res.json().get('organic', [])])
    except: return "情报采集受限。"

def agent_full_call(event, context):
    """
    一次性获取时间轴 JSON 数据
    """
    prompt = f"""
    你是一个高保真推演引擎。针对事件【{event}】，基于情报【{context}】，推演四个阶段的压力值。
    输出严格 JSON 格式：
    {{
      "T0": [40, 30, 20, 15],
      "T24": [官方分, 民众分, 媒体分, 风险分],
      "T72": [官方分, 民众分, 媒体分, 风险分],
      "T7d": [官方分, 民众分, 媒体分, 风险分]
    }}
    (分数0-100)
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    raw = response.choices[0].message.content
    match = re.search(r'(\{.*\})', raw, re.DOTALL)
    return json.loads(match.group(1))

def agent_role_view(role, event, context):
    """
    获取单个角色的深度观点
    """
    role_prompts = {
        "官方": "你代表官方，推演决策逻辑与应对措施。",
        "民众": "你代表各阶层民众，反馈心理负荷与真实诉求。",
        "媒体": "你代表媒体专家，分析舆论走向与反转风险。",
        "风险": "你代表安全官，识别潜在社会风险与治理漏洞。"
    }
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": role_prompts[role]},
                  {"role": "user", "content": f"基于情报【{context}】，针对事件【{event}】发表深度观点。"}],
        temperature=0.4
    )
    return response.choices[0].message.content

# --- 4. 界面交互 ---
st.title("🔮 SHENCE (神策) | 全维度高保真研判沙盘")

event_input = st.text_area("📡 输入研判目标", height=100)

if st.button("🚀 启动全维度动态推演"):
    if event_input:
        with st.spinner("🕵️ 正在同步全网情报并构建博弈模型..."):
            intel = fetch_intelligence(event_input)
            time_data = agent_full_call(event_input, intel)
            
            # --- 第一部分：动态演化曲线 ---
            st.markdown("### 📈 社会稳定风险演化趋势")
            labels = ['当前', '24h爆发期', '72h博弈期', '7d演化期']
            fig = go.Figure()
            # 提取数据线
            colors = ['#3498db', '#e74c3c', '#f1c40f', '#00ffcc']
            names = ['官方压力', '民众情绪', '舆论热度', '整体风险']
            for i in range(4):
                y_data = [time_data['T0'][i], time_data['T24'][i], time_data['T72'][i], time_data['T7d'][i]]
                fig.add_trace(go.Scatter(x=labels, y=y_data, name=names[i], line=dict(color=colors[i], width=4)))
            
            fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig, use_container_width=True)

            # --- 第二部分：核心亮点：四个角色并列展示 ---
            st.markdown("---")
            st.markdown("### 🖥️ 角色并列研判视图")
            c1, c2, c3, c4 = st.columns(4)
            
            # 并行获取四个角色的深度观点
            with c1: st.info(f"**🏛️ 官方立场**\n\n{agent_role_view('官方', event_input, intel)}")
            with c2: st.success(f"**👥 民众反应**\n\n{agent_role_view('民众', event_input, intel)}")
            with c3: st.warning(f"**📰 媒体研判**\n\n{agent_role_view('媒体', event_input, intel)}")
            with c4: st.error(f"**🛡️ 风险预警**\n\n{agent_role_view('风险', event_input, intel)}")

            # --- 第三部分：深度总结报告 ---
            st.markdown("---")
            st.markdown("### 📝 深度综合研判分析报告")
            summary_res = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": f"基于情报{intel}和推演数据{time_data}，撰写800字深度报告。"}],
                temperature=0.4
            ).choices[0].message.content
            
            st.markdown(f"<div class='report-box'>{summary_res}</div>", unsafe_allow_html=True)
            
            st.download_button("📥 导出完整研判报告", summary_res, file_name="神策深度报告.txt")
