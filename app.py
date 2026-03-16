import streamlit as st
from openai import OpenAI
import requests
import json
import plotly.graph_objects as go
import pandas as pd
import re
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(page_title="神策 - 高保真时间轴推演", layout="wide")

# 科技感 CSS 美化
st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #ffffff; }
    .stMetric { background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    .time-node { color: #00ffcc; font-weight: bold; border-left: 3px solid #00ffcc; padding-left: 10px; margin-top: 20px; }
    .report-box { background-color: #161b22; padding: 25px; border-radius: 10px; border: 1px solid #00ffcc; line-height: 1.8; color: #e0e0e0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 密钥读取 ---
# 确保在 Streamlit Cloud 的 Settings -> Secrets 中已配置以下两个 Key
try:
    DEEPSEEK_K = st.secrets["DEEPSEEK_API_KEY"]
    SERPER_K = st.secrets["SERPER_API_KEY"]
except KeyError:
    st.error("❌ 密钥未配置！请在 Secrets 中添加 DEEPSEEK_API_KEY 和 SERPER_API_KEY")
    st.stop()

client = OpenAI(api_key=DEEPSEEK_K, base_url="https://api.deepseek.com")

# --- 3. 核心功能函数 ---
def fetch_intelligence(query):
    """从互联网采集真实情报"""
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": f"{query} 现状 政策 评价 趋势", "gl": "cn", "hl": "zh-cn", "num": 10})
    headers = {'X-API-KEY': SERPER_K, 'Content-Type': 'application/json'}
    try:
        res = requests.post(url, headers=headers, data=payload)
        return "\n".join([item.get('snippet') for item in res.json().get('organic', [])])
    except Exception as e:
        return f"数据采集受限: {str(e)}"

def agent_time_series_call(event, context):
    """推演时间轴数据，并包含鲁棒的 JSON 解析逻辑"""
    prompt = f"""
    你是一个高保真时空推演引擎。请针对以下事件进行“时间轴演化推演”。
    
    【事件】: {event}
    【情报库】: {context}
    
    请输出三个阶段（T+24h, T+72h, T+7d）的研判。要求：
    1. 每阶段给出[官方压力, 民众情绪, 舆论热度, 失稳风险]的量化分值（0-100）。
    2. 每阶段给出简要的情势描述。
    
    必须且只能输出严格的 JSON 字符串，禁止任何 Markdown 标签或解释文字：
    {{
      "T24": {{"scores": [官方, 民众, 媒体, 风险], "desc": "描述"}},
      "T72": {{"scores": [官方, 民众, 媒体, 风险], "desc": "描述"}},
      "T7d": {{"scores": [官方, 民众, 媒体, 风险], "desc": "描述"}}
    }}
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": "你是一个严谨的 JSON 数据接口。"},
                  {"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    raw_content = response.choices[0].message.content.strip()
    
    # 使用正则表达式提取 JSON 部分，防止 AI 返回 Markdown 代码块
    match = re.search(r'(\{.*\}|\[.*\])', raw_content, re.DOTALL)
    clean_json = match.group(1) if match else raw_content

    try:
        return json.loads(clean_json)
    except json.JSONDecodeError:
        st.error(f"解析失败。AI 返回了非规范数据。")
        with st.expander("查看原始异常数据"):
            st.text(raw_content)
        st.stop()

# --- 4. 界面交互 ---
st.title("🔮 SHENCE (神策) | 高保真时间轴动态推演")
st.caption("基于多智能体博弈算法与实时互联网情报")

event_input = st.text_area("📡 请输入研判目标", placeholder="例如：某地新出台的交通管制政策、突发行业罢工事件等...", height=100)

if st.button("🚀 启动全维度跨时空推演"):
    if event_input:
        with st.spinner("⏳ 正在构建逻辑沙盘并计算时间轴熵值..."):
            # 1. 采集情报
            intel = fetch_intelligence(event_input)
            # 2. 获取推演数据
            data = agent_time_series_call(event_input, intel)
            
            # --- 数据准备 ---
            time_labels = ['当前 (T+0)', '爆发期 (T+24h)', '博弈期 (T+72h)', '平稳期 (T+7d)']
            off_scores = [40, data['T24']['scores'][0], data['T72']['scores'][0], data['T7d']['scores'][0]]
            cit_scores = [35, data['T24']['scores'][1], data['T72']['scores'][1], data['T7d']['scores'][1]]
            med_scores = [30, data['T24']['scores'][2], data['T72']['scores'][2], data['T7d']['scores'][2]]
            rsk_scores = [20, data['T24']['scores'][3], data['T72']['scores'][3], data['T7d']['scores'][3]]

        # --- 布局：图表展示 ---
        st.markdown("### 📈 社会稳定风险演化曲线")
        fig = go.Figure()
        colors = ['#3498db', '#e74c3c', '#f1c40f', '#00ffcc']
        metrics = ['官方压力', '民众情绪', '舆论热度', '失稳风险']
        series = [off_scores, cit_scores, med_scores, rsk_scores]
        
        for i in range(4):
            fig.add_trace(go.Scatter(
                x=time_labels, y=series[i], name=metrics[i],
                line=dict(color=colors[i], width=3 if i<3 else 5, dash='solid' if i<3 else 'dot')
            ))
        
        fig.update_layout(
            height=450, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white",
            yaxis=dict(title="压力指数", range=[0, 105], gridcolor='#30363d'),
            xaxis=dict(gridcolor='#30363d')
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- 布局：节点扫描 ---
        st.markdown("---")
        st.markdown("### 🖥️ 关键时间节点状态扫描")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("<div class='time-node'>T+24h: 爆发期</div>", unsafe_allow_html=True)
            st.write(data['T24']['desc'])
        with c2:
            st.markdown("<div class='time-node'>T+72h: 博弈期</div>", unsafe_allow_html=True)
            st.write(data['T72']['desc'])
        with c3:
            st.markdown("<div class='time-node'>T+7d: 演化期</div>", unsafe_allow_html=True)
            st.write(data['T7d']['desc'])

        # --- 布局：深度综合报告 ---
        st.markdown("---")
        st.markdown("### 📝 全维度综合推演研判报告")
        with st.spinner("撰写深度战略报告中..."):
            report_prompt = f"针对事件【{event_input}】，结合以下推演数据：{data}。请作为首席战略研判官，撰写一份具备前瞻性、逻辑严密的综合研判报告。包含风险点识别、三方博弈分析及最终对策建议。字数约800字。"
            report_res = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": report_prompt}],
                temperature=0.4
            ).choices[0].message.content
            
            st.markdown(f"<div class='report-box'>{report_res}</div>", unsafe_allow_html=True)

        # 下载功能
        st.download_button(
            label="📥 导出高保真研判报告",
            data=f"神策高保真推演报告\n生成时间：{datetime.now()}\n\n{report_res}",
            file_name=f"神策推演_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain"
        )
        
        with st.expander("🔗 查看底层原始情报来源"):
            st.text(intel)
    else:
        st.warning("⚠️ 请先输入研判目标。")

# --- 底部信息 ---
st.markdown("---")
st.caption("© 2026 ShenCe Intelligence System | 高保真推演引擎 v2.5")
