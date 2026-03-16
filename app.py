import streamlit as st
from openai import OpenAI
import requests
import json
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# --- 1. 页面设置 ---
st.set_page_config(page_title="神策 - 高保真推演系统", layout="wide")

# 科技感 CSS
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 密钥读取 ---
DEEPSEEK_K = st.secrets["DEEPSEEK_API_KEY"]
SERPER_K = st.secrets["SERPER_API_KEY"]
client = OpenAI(api_key=DEEPSEEK_K, base_url="https://api.deepseek.com")

# --- 3. 核心功能函数 ---
def fetch_intelligence(query):
    url = "https://google.serper.dev/search"
    search_query = f"{query} 政策影响 现状 评价"
    payload = json.dumps({"q": search_query, "gl": "cn", "hl": "zh-cn", "num": 8})
    headers = {'X-API-KEY': SERPER_K, 'Content-Type': 'application/json'}
    try:
        res = requests.post(url, headers=headers, data=payload)
        return "\n".join([item.get('snippet') for item in res.json().get('organic', [])])
    except:
        return "数据采集受限。"

def agent_quant_call(role_prompt, event, context):
    """
    要求 AI 输出固定格式：[分数] + 理由
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": f"你是一个量化研判专家。{role_prompt}。注意：你必须在回复的第一行首先给出当前维度的“压力分值”（0-100，分数越高代表压力或冲突越大），格式必须为：【分值：XX】。"},
            {"role": "user", "content": f"情报：{context}\n事件：{event}"}
        ],
        temperature=0.3
    )
    content = response.choices[0].message.content
    # 简单的分值提取逻辑
    try:
        score_str = content.split('】')[0].split('：')[1]
        score = int(''.join(filter(str.isdigit, score_str)))
    except:
        score = 50 # 默认兜底分
    return score, content

# --- 4. 界面设计 ---
st.title("🔮 SHENCE (神策) | 高保真量化推演沙盘")
event_input = st.text_area("📡 输入研判目标", placeholder="输入事件，系统将自动进行量化建模...")

if st.button("🚀 启动高保真推演"):
    if event_input:
        with st.spinner("🕵️ 正在采集情报并进行数值建模..."):
            intel = fetch_intelligence(event_input)
            
            # 执行四个维度的量化推演
            s1, res1 = agent_quant_call("模拟官方，推演决策压力", event_input, intel)
            s2, res2 = agent_quant_call("模拟民众，推演心理负荷与抵触感", event_input, intel)
            s3, res3 = agent_quant_call("模拟媒体，推演舆论热度与敏感度", event_input, intel)
            s4, res4 = agent_quant_call("模拟风险，推演社会失稳可能性", event_input, intel)

        # --- 第一部分：量化指标卡 ---
        st.markdown("### 📊 维度实时压力指标")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("官方决策压力", f"{s1}%", delta="行政负荷")
        m2.metric("民众心理负荷", f"{s2}%", delta="情绪波幅")
        m3.metric("舆论敏感度", f"{s3}%", delta="传播速率")
        m4.metric("失稳风险值", f"{s4}%", delta="预警级别", delta_color="inverse")

        # --- 第二部分：四角色研判详情 ---
        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.info(f"**🏛️ 官方**\n\n{res1}")
        with c2: st.success(f"**👥 民众**\n\n{res2}")
        with c3: st.warning(f"**📰 媒体**\n\n{res3}")
        with c4: st.error(f"**🛡️ 风险**\n\n{res4}")

        # --- 第三部分：动态风险指数图 ---
        st.markdown("---")
        st.markdown("### 📈 社会稳定风险指数推演图")
        
        # 模拟一个随时间轴变化的趋势（当前时刻为中间点）
        # 这里展示各维度的对比折线
        chart_data = pd.DataFrame({
            '维度': ['官方', '民众', '媒体', '整体风险'],
            '当前压力值': [s1, s2, s3, s4]
        })
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=chart_data['维度'], y=chart_data['当前压力值'], 
                                 mode='lines+markers', name='当前态势',
                                 line=dict(color='#00ffcc', width=4),
                                 marker=dict(size=10)))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color="white",
            yaxis=dict(range=[0, 100], gridcolor='#30363d'),
            xaxis=dict(gridcolor='#30363d'),
            title="多维博弈平衡点分析"
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- 第四部分：深度研判报告与下载 ---
        st.markdown("### 📝 深度全维度综合研判结论")
        final_p = f"综合以下量化分值（官方{s1}, 民众{s2}, 媒体{s3}, 风险{s4}），出一份深度的、具备战略高度的研判报告。"
        final_res = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": f"{final_p}\n情报：{intel}"}],
            temperature=0.4
        ).choices[0].message.content
        
        st.markdown(f"<div style='background-color:#161b22; padding:20px; border-left:5px solid #00ffcc;'>{final_res}</div>", unsafe_allow_html=True)
        
        st.download_button("📥 点击下载完整高保真研判报告", final_res, file_name="神策高保真报告.txt")
