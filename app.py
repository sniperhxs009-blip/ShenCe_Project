import streamlit as st
from openai import OpenAI
import requests
import json
import plotly.graph_objects as go
import re

# --- 1. 页面配置 ---
st.set_page_config(page_title="神策 - 高保真多模态推演沙盘", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #ffffff; }
    .step-box { border-left: 4px solid #00ffcc; padding: 15px; background: #161b22; margin-bottom: 20px; border-radius: 0 10px 10px 0; }
    .role-label { color: #00ffcc; font-weight: bold; font-size: 1.1rem; margin-bottom: 10px; display: block; }
    .report-box { background-color: #161b22; padding: 25px; border-radius: 10px; border: 2px solid #00ffcc; line-height: 1.8; }
    .model-tag { background-color: #00ffcc; color: #000; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; margin-left: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 密钥配置 (已硬编码整合) ---
# 使用你提供的两个 Key
DALLE_KEY = "sk-VIK37O4GF7A9Ddd34e0cT3BLBkFJ7641BF332588437787D8"
SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
BASE_URL = "https://api.ohmygpt.com/v1"

# 从 Secrets 获取 Serper Key (用于联网搜素)
try:
    SERPER_K = st.secrets["SERPER_API_KEY"]
except:
    st.error("❌ 缺少 SERPER_API_KEY，请在 Streamlit 云端 Secrets 中配置。")
    st.stop()

# 初始化客户端 (默认使用无限制的 Secret Key)
client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)

# --- 3. 核心功能函数 ---
def fetch_intelligence(query):
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": f"{query} 最新政策 现状 影响", "gl": "cn", "hl": "zh-cn", "num": 8})
    headers = {'X-API-KEY': SERPER_K, 'Content-Type': 'application/json'}
    try:
        res = requests.post(url, headers=headers, data=payload)
        return "\n".join([item.get('snippet') for item in res.json().get('organic', [])])
    except: return "情报采集暂时受限。"

def get_time_series_data(event):
    prompt = f"针对事件【{event}】推演T0, T24, T72, T7d四个阶段的官方、民众、媒体、风险压力值(0-100)。严格输出JSON: {{\"T0\":[40,30,20,10], \"T24\":[..], \"T72\":[..], \"T7d\":[..]}}"
    try:
        response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user", "content":prompt}])
        match = re.search(r'(\{.*\})', response.choices[0].message.content, re.DOTALL)
        return json.loads(match.group(1)) if match else None
    except: return None

def generate_visual_simulation(report_text):
    """使用 DALL-E 3 生成现场模拟图"""
    try:
        # 1. 用 GPT 提炼视觉描述
        extract = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user", "content":f"为以下研判报告生成一个100字内的写实摄影提示词：{report_text[:400]}"}]
        ).choices[0].message.content
        
        # 2. 调用 DALL-E 3 (使用 Dalle Key 确保权限)
        img_client = OpenAI(api_key=DALLE_KEY, base_url=BASE_URL)
        response = img_client.images.generate(
            model="dall-e-3",
            prompt=f"Photorealistic cinematic simulation of: {extract}. High detail, intelligence agency style.",
            size="1024x1024"
        )
        return response.data[0].url
    except: return None

# --- 4. 界面逻辑 ---
st.title("🔮 SHENCE (神策) | 多模态高保真推演沙盘")
event_input = st.text_area("📡 目标事件输入", placeholder="输入研判目标，启动全球模型协同对撞...")

if st.button("🚀 启动全维度跨时空推演"):
    if event_input:
        with st.spinner("🕵️ 正在同步全球情报并激活逻辑大脑..."):
            intel = fetch_intelligence(event_input)
            time_data = get_time_series_data(event_input)

        # A. 趋势图展示
        if time_data:
            st.markdown("### 📈 社会稳定风险演化趋势")
            labels = ['当前', '24h爆发', '72h博弈', '7d演化']
            fig = go.Figure()
            colors = ['#3498db', '#e74c3c', '#f1c40f', '#00ffcc']
            names = ['官方压力', '民众情绪', '舆论热度', '整体风险']
            for i in range(4):
                try:
                    y_val = [time_data['T0'][i], time_data['T24'][i], time_data['T72'][i], time_data['T7d'][i]]
                    fig.add_trace(go.Scatter(x=labels, y=y_val, name=names[i], line=dict(color=colors[i], width=4)))
                except: continue
            fig.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig, use_container_width=True)

        # B. 核心博弈对撞 (使用 Claude 3.5 Sonnet)
        st.markdown("---")
        st.markdown("### 🔄 智能体多轮博弈对撞")
        
        with st.status("正在调配 Claude 3.5 进行深度博弈...", expanded=True) as status:
            # 官方视角
            off_res = client.chat.completions.create(model="claude-3-5-sonnet", messages=[{"role":"user","content":f"事件:{event_input}\n情报:{intel}\n请给出战略对策。"}]).choices[0].message.content
            # 民众视角
            cit_res = client.chat.completions.create(model="claude-3-5-sonnet", messages=[{"role":"user","content":f"针对对策：{off_res}\n请给出民意反馈。"}]).choices[0].message.content
            status.update(label="✅ 博弈对撞完成", state="complete")

        c1, c2 = st.columns(2)
        with c1: st.markdown(f"<div class='step-box'><span class='role-label'>🏛️ 官方决策</span><span class='model-tag'>Claude 3.5</span><br>{off_res}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='step-box'><span class='role-label'>👥 民众反应</span><span class='model-tag'>Claude 3.5</span><br>{cit_res}</div>", unsafe_allow_html=True)

        # C. 最终研判与视觉仿真
        st.markdown("---")
        with st.spinner("撰写深度研判报告并生成视觉仿真图..."):
            final_report = client.chat.completions.create(
                model="claude-3-5-sonnet",
                messages=[{"role":"user","content":f"整合以上博弈出具一份800字专业研判报告：{off_res}{cit_res}"}]
            ).choices[0].message.content
            img_url = generate_visual_simulation(final_report)

        col_text, col_img = st.columns([2, 1])
        with col_text:
            st.markdown(f"<div class='report-box'>{final_report}</div>", unsafe_allow_html=True)
        with col_img:
            st.markdown("### 🖼️ 现场仿真")
            if img_url:
                st.image(img_url, use_container_width=True)
            else:
                st.warning("视觉生成受阻（请确认 OhMyGPT 余额或 DALL-E 3 权限）")
                
        st.download_button("📥 导出研判报告", final_report, file_name="神策深度报告.txt")

else:
    st.info("💡 请在上方输入框输入研判事件，例如：‘某地突发大型社会突发事件的影响推演’")
