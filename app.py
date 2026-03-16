import streamlit as st
from openai import OpenAI
import requests
import json
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- 1. 页面配置 ---
st.set_page_config(page_title="神策 - 时间轴动态推演沙盘", layout="wide")

# 深度科技感 CSS
st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #ffffff; }
    .stMetric { background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    .time-node { color: #00ffcc; font-weight: bold; border-left: 3px solid #00ffcc; padding-left: 10px; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 密钥读取 ---
DEEPSEEK_K = st.secrets["DEEPSEEK_API_KEY"]
SERPER_K = st.secrets["SERPER_API_KEY"]
client = OpenAI(api_key=DEEPSEEK_K, base_url="https://api.deepseek.com")

# --- 3. 核心功能函数 ---
def fetch_intelligence(query):
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": f"{query} 动态 趋势 预测", "gl": "cn", "hl": "zh-cn", "num": 10})
    headers = {'X-API-KEY': SERPER_K, 'Content-Type': 'application/json'}
    try:
        res = requests.post(url, headers=headers, data=payload)
        return "\n".join([item.get('snippet') for item in res.json().get('organic', [])])
    except: return "数据采集受限。"

def agent_time_series_call(event, context):
    """
    核心指令：要求 AI 生成 T+24h, T+72h, T+7d 的量化数值 JSON
    """
    prompt = f"""
    你是一个高保真时空推演引擎。请针对以下事件进行“时间轴演化推演”。
    
    【事件】: {event}
    【情报】: {context}
    
    请输出三个阶段的研判，每阶段必须包含：
    1. 官方压力、民众情绪、舆论热度、失稳风险 四个维度的分值（0-100）。
    2. 简要的情势描述。
    
    输出格式要求为严格的 JSON 字符串，以便系统解析，格式如下：
    {{
      "T24": {{"scores": [官方, 民众, 媒体, 风险], "desc": "..."}},
      "T72": {{"scores": [官方, 民众, 媒体, 风险], "desc": "..."}},
      "T7d": {{"scores": [官方, 民众, 媒体, 风险], "desc": "..."}}
    }}
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": "你是一个只输出JSON的推演引擎。"},
                  {"role": "user", "content": prompt}],
        temperature=0.3
    )
    return json.loads(response.choices[0].message.content)

# --- 4. 界面设计 ---
st.title("🔮 SHENCE (神策) | 时间轴动态推演沙盘")
event_input = st.text_area("📡 输入研判目标", placeholder="例如：某项新税收政策颁布后的社会反应演化...")

if st.button("🚀 开启跨时空全维度推演"):
    if event_input:
        with st.spinner("⏳ 正在构建时间轴沙盘，计算逻辑熵..."):
            intel = fetch_intelligence(event_input)
            data = agent_time_series_call(event_input, intel)
            
            # --- 整理数据用于图表 ---
            time_labels = ['初始态 (T+0)', '爆发期 (T+24h)', '博弈期 (T+72h)', '平稳期 (T+7d)']
            # 初始状态设为 50 基准或根据 T24 略微下调
            off_scores = [40, data['T24']['scores'][0], data['T72']['scores'][0], data['T7d']['scores'][0]]
            cit_scores = [30, data['T24']['scores'][1], data['T72']['scores'][1], data['T7d']['scores'][1]]
            med_scores = [20, data['T24']['scores'][2], data['T72']['scores'][2], data['T7d']['scores'][2]]
            rsk_scores = [10, data['T24']['scores'][3], data['T72']['scores'][3], data['T7d']['scores'][3]]

        # --- 第一部分：动态趋势曲线 ---
        st.markdown("### 📈 社会稳定风险演化趋势")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=time_labels, y=off_scores, name='官方压力', line=dict(color='#3498db', width=3)))
        fig.add_trace(go.Scatter(x=time_labels, y=cit_scores, name='民众情绪', line=dict(color='#e74c3c', width=3)))
        fig.add_trace(go.Scatter(x=time_labels, y=med_scores, name='舆论热度', line=dict(color='#f1c40f', width=3)))
        fig.add_trace(go.Scatter(x=time_labels, y=rsk_scores, name='整体风险', line=dict(color='#00ffcc', width=5, dash='dot')))
        
        fig.update_layout(height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white",
                          yaxis=dict(title="压力指数 (0-100)", range=[0, 105], gridcolor='#30363d'),
                          xaxis=dict(gridcolor='#30363d'))
        st.plotly_chart(fig, use_container_width=True)

        # --- 第二部分：四列角色深度研判 ---
        st.markdown("---")
        st.markdown("### 🖥️ 关键节点状态扫描")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("<div class='time-node'>T+24h: 爆发期</div>", unsafe_allow_html=True)
            st.write(data['T24']['desc'])
        with c2:
            st.markdown("<div class='time-node'>T+72h: 博弈期</div>", unsafe_allow_html=True)
            st.write(data['T72']['desc'])
        with c3:
            st.markdown("<div class='time-node'>T+7d: 转折/平稳期</div>", unsafe_allow_html=True)
            st.write(data['T7d']['desc'])

        # --- 第三部分：深度综合报告 ---
        st.markdown("---")
        st.markdown("### 📝 全维度综合推演报告")
        final_prompt = f"根据时间轴数据：{data}，为事件【{event_input}】编写一份深度的、具有未来视角的战略综合研判报告，字数800字左右。"
        final_res = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": final_prompt}],
            temperature=0.4
        ).choices[0].message.content
        
        st.markdown(f"<div style='background-color:#161b22; padding:25px; border-radius:10px; border:1px solid #00ffcc; line-height:1.6;'>{final_res}</div>", unsafe_allow_html=True)
        
        # 下载
        st.download_button("📥 导出全维度高保真研判报告", final_res, file_name=f"神策推演_{datetime.now().strftime('%Y%m%d')}.txt")

        # 隐藏的原始依据
        with st.expander("🔗 查看底层情报来源"):
            st.text(intel)
