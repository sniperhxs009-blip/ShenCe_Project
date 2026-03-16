import streamlit as st
from openai import OpenAI
import requests
import json
import plotly.graph_objects as go
import pandas as pd
import re
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(page_title="神策 - 全球模型协同推演沙盘", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #ffffff; }
    .step-box { border-left: 4px solid #00ffcc; padding: 15px; background: #161b22; margin-bottom: 20px; border-radius: 0 10px 10px 0; }
    .role-label { color: #00ffcc; font-weight: bold; font-size: 1.1rem; margin-bottom: 10px; display: block; }
    .report-box { background-color: #161b22; padding: 25px; border-radius: 10px; border: 2px solid #00ffcc; line-height: 1.8; }
    .model-tag { background-color: #00ffcc; color: #000; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 密钥与中转设置 ---
# 填入你获取的 OhMyGPT 密钥
OHMYGPT_KEY = "sk-VIK37O4GF7A9Ddd34e0cT3BLBkFJ7641BF332588437787D8"
BASE_URL = "https://api.ohmygpt.com/v1"

# 从 Secrets 获取 Serper Key
try:
    SERPER_K = st.secrets["SERPER_API_KEY"]
except:
    st.error("❌ 缺少 SERPER_API_KEY，请在 Secrets 中配置。")
    st.stop()

# 初始化万能客户端
client = OpenAI(api_key=OHMYGPT_KEY, base_url=BASE_URL)

# --- 3. 侧边栏：模型监控开关 ---
with st.sidebar:
    st.title("🛡️ 系统监控面板")
    st.subheader("模型调度状态")
    
    show_monitor = st.checkbox("开启模型实时监测", value=True)
    
    if show_monitor:
        st.success("✅ 中转站连接成功")
        st.info(f"📍 节点: {BASE_URL}")
        st.divider()
        st.write("**当前逻辑大脑 (Logic):**")
        st.code("claude-3-5-sonnet")
        st.write("**当前视觉引擎 (Vision):**")
        st.code("dall-e-3")
        st.write("**辅助决策引擎 (Helper):**")
        st.code("gpt-4o-mini")

# --- 4. 核心功能函数 ---
def fetch_intelligence(query):
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": f"{query} 政策影响 现状 评价", "gl": "cn", "hl": "zh-cn", "num": 8})
    headers = {'X-API-KEY': SERPER_K, 'Content-Type': 'application/json'}
    try:
        res = requests.post(url, headers=headers, data=payload)
        return "\n".join([item.get('snippet') for item in res.json().get('organic', [])])
    except: return "情报采集受限。"

def get_time_series_data(event, context):
    # 使用较轻量但逻辑好的模型获取 JSON 数据
    prompt = f"针对事件【{event}】推演T0, T24, T72, T7d阶段[官方,民众,媒体,风险]分值。只输出JSON: {{\"T0\":[..], \"T24\":[..], \"T72\":[..], \"T7d\":[..]}}"
    response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user", "content":prompt}])
    match = re.search(r'(\{.*\})', response.choices[0].message.content, re.DOTALL)
    return json.loads(match.group(1))

def generate_sim_image(report):
    try:
        # 1. 提炼描述 (使用 GPT-4o-mini 节省成本)
        extract = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user", "content":f"提炼DALL-E 3写实摄影提示词，展现此报告的核心风险点：{report[:500]}"}]
        ).choices[0].message.content
        
        # 2. 调用 DALL-E 3 绘图
        response = client.images.generate(
            model="dall-e-3",
            prompt=f"A photorealistic, cinematic intelligence surveillance photo: {extract}",
            size="1024x1024"
        )
        return response.data[0].url
    except Exception as e:
        st.sidebar.error(f"视觉引擎报错: {e}")
        return None

# --- 5. 界面主逻辑 ---
st.title("🔮 SHENCE (神策) | 全球模型联合推演沙盘")

event_input = st.text_area("📡 输入研判目标", height=80, placeholder="请输入需要推演的事件，系统将启动全球模型博弈...")

if st.button("🚀 启动全维度跨时空推演"):
    if event_input:
        with st.spinner("🕵️ 正在同步全球情报并调配顶级 AI 资源..."):
            intel = fetch_intelligence(event_input)
            time_data = get_time_series_data(event_input, intel)

        # --- A. 时间轴演化 (量化展示) ---
        st.markdown("### 📈 社会稳定风险演化趋势")
        labels = ['当前', '24h爆发期', '72h博弈期', '7d演化期']
        fig = go.Figure()
        colors = ['#3498db', '#e74c3c', '#f1c40f', '#00ffcc']
        names = ['官方压力', '民众情绪', '舆论热度', '整体风险']
        for i in range(4):
            y = [time_data['T0'][i], time_data['T24'][i], time_data['T72'][i], time_data['T7d'][i]]
            fig.add_trace(go.Scatter(x=labels, y=y, name=names[i], line=dict(color=colors[i], width=4)))
        fig.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
        st.plotly_chart(fig, use_container_width=True)

        # --- B. Agent-Based 逻辑博弈 (Claude 3.5 驱动) ---
        st.markdown("---")
        st.markdown("### 🔄 智能体多轮对撞博弈回溯")
        
        with st.status("🛠️ 正在进行模型博弈...", expanded=True) as status:
            st.write("🏛️ **Claude 3.5** 正在模拟官方对策...")
            off_res = client.chat.completions.create(model="claude-3-5-sonnet", messages=[{"role":"user","content":f"事件:{event_input}\n情报:{intel}\n给出对策"}]).choices[0].message.content
            
            st.write("👥 **Claude 3.5** 正在模拟民众反馈...")
            cit_res = client.chat.completions.create(model="claude-3-5-sonnet", messages=[{"role":"user","content":f"官方对策：{off_res}\n民众反馈？"}]).choices[0].message.content
            
            st.write("📰 **Claude 3.5** 正在分析媒体舆论...")
            med_res = client.chat.completions.create(model="claude-3-5-sonnet", messages=[{"role":"user","content":f"冲突点：{off_res} vs {cit_res}"}]).choices[0].message.content
            
            status.update(label="✅ 博弈对撞完成", state="complete")

        # 展示博弈列
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"<div class='step-box'><span class='role-label'>🏛️ 官方决策</span><span class='model-tag'>Claude 3.5</span><br><br>{off_res}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='step-box'><span class='role-label'>👥 民众反应</span><span class='model-tag'>Claude 3.5</span><br><br>{cit_res}</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='step-box'><span class='role-label'>📰 媒体定调</span><span class='model-tag'>Claude 3.5</span><br><br>{med_res}</div>", unsafe_allow_html=True)

        # --- C. 深度总结与视觉仿真 ---
        st.markdown("---")
        with st.spinner("正在生成高保真视觉推演图..."):
            report = client.chat.completions.create(
                model="claude-3-5-sonnet",
                messages=[{"role":"user","content":f"整合以上内容出具800字研判报告：{off_res}{cit_res}"}]
            ).choices[0].message.content
            img_url = generate_sim_image(report)

        st.markdown("### 📝 全维度研判深度报告 & 视觉仿真")
        col_text, col_img = st.columns([2, 1])
        with col_text:
            st.markdown(f"<div class='report-box'>{report}</div>", unsafe_allow_html=True)
        with col_img:
            if img_url:
                st.image(img_url, caption="📸 高保真现场模拟图 (由 DALL-E 3 生成)", use_container_width=True)
            else:
                st.error("视觉生成失败，请检查余额。")
                
        st.download_button("📥 导出完整研判报告", report, file_name="神策深度报告.txt")

    else:
        st.warning("请输入目标事件。")
