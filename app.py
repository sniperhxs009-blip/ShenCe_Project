import streamlit as st
from openai import OpenAI
import requests
import json
import plotly.graph_objects as go
import re

# --- 1. 核心配置 ---
st.set_page_config(page_title="神策 - 视觉推演全功能版", layout="wide")

# 科技感 UI 样式
st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #ffffff; }
    .step-box { border-left: 4px solid #00ffcc; padding: 15px; background: #161b22; margin-bottom: 20px; border-radius: 0 10px 10px 0; }
    .role-label { color: #00ffcc; font-weight: bold; font-size: 1.1rem; margin-bottom: 10px; display: block; }
    .report-box { background-color: #161b22; padding: 25px; border-radius: 10px; border: 2px solid #00ffcc; line-height: 1.8; }
    .model-tag { background-color: #00ffcc; color: #000; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; margin-left: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 密钥与中转设置 ---
# 请确保使用你截图中那个“无限制”的 Secret Key
OHMYGPT_KEY = "sk-LMB...b3B3" # <--- 请在此处填入完整的第二个 Key
BASE_URL = "https://api.ohmygpt.com/v1" 

# 从 Secrets 获取 Serper Key
try:
    SERPER_K = st.secrets["SERPER_API_KEY"]
except:
    st.error("❌ 缺少 SERPER_API_KEY，请在 Streamlit Secrets 中配置。")
    st.stop()

# 初始化万能客户端
client = OpenAI(api_key=OHMYGPT_KEY, base_url=BASE_URL)

# --- 3. 辅助功能函数 ---
def fetch_intelligence(query):
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": f"{query} 政策影响 现状 评价", "gl": "cn", "hl": "zh-cn", "num": 8})
    headers = {'X-API-KEY': SERPER_K, 'Content-Type': 'application/json'}
    try:
        res = requests.post(url, headers=headers, data=payload)
        return "\n".join([item.get('snippet') for item in res.json().get('organic', [])])
    except: return "情报采集受限。"

def get_time_series_data(event):
    """量化数据获取，带防御逻辑"""
    prompt = f"针对事件【{event}】推演T0, T24, T72, T7d阶段[官方,民众,媒体,风险]分值(0-100)。严格输出JSON格式: {{\"T0\":[40,30,20,10], \"T24\":[..], \"T72\":[..], \"T7d\":[..]}}"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user", "content":prompt}],
            timeout=15
        )
        content = response.choices[0].message.content
        match = re.search(r'(\{.*\})', content, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return None
    except Exception as e:
        st.sidebar.error(f"量化引擎报错: {e}")
        return None

def generate_visual(report):
    """DALL-E 3 视觉仿真"""
    try:
        # 提炼描述
        extract = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user", "content":f"提炼DALL-E 3提示词：{report[:300]}"}]
        ).choices[0].message.content
        # 绘图
        res = client.images.generate(model="dall-e-3", prompt=f"Photorealistic field report photo: {extract}", size="1024x1024")
        return res.data[0].url
    except: return None

# --- 4. 侧边栏自检 ---
with st.sidebar:
    st.header("⚙️ 系统自检")
    if st.button("运行连通性测试"):
        try:
            client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":"hi"}], max_tokens=5)
            st.success("✅ 接口连通成功")
        except Exception as e:
            st.error(f"❌ 连通失败: {e}")

# --- 5. 主页面逻辑 ---
st.title("🔮 SHENCE (神策) | 多模态高保真推演沙盘")
event_input = st.text_area("📡 输入研判目标", placeholder="输入事件触发全球 AI 联合推演...")

if st.button("🚀 启动全维度推演"):
    if event_input:
        with st.spinner("🕵️ 采集情报并激活逻辑大脑..."):
            intel = fetch_intelligence(event_input)
            time_data = get_time_series_data(event_input)

        # A. 趋势图（防御性渲染）
        if time_data and 'T0' in time_data:
            st.markdown("### 📈 社会稳定风险演化趋势")
            labels = ['当前', '24h爆发期', '72h博弈期', '7d演化期']
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
        else:
            st.error("⚠️ 无法获取量化数据，请检查 OhMyGPT 余额或模型权限。")

        # B. 逻辑博弈
        st.markdown("---")
        st.markdown("### 🔄 智能体多轮博弈对撞")
        try:
            # 官方
            off_res = client.chat.completions.create(model="claude-3-5-sonnet", messages=[{"role":"user","content":f"事件:{event_input}\n对策？"}]).choices[0].message.content
            # 民众
            cit_res = client.chat.completions.create(model="claude-3-5-sonnet", messages=[{"role":"user","content":f"官方对策：{off_res}\n反馈？"}]).choices[0].message.content
            
            c1, c2 = st.columns(2)
            with c1: st.markdown(f"<div class='step-box'><span class='role-label'>🏛️ 官方决策</span><span class='model-tag'>Claude 3.5</span><br>{off_res}</div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='step-box'><span class='role-label'>👥 民众反应</span><span class='model-tag'>Claude 3.5</span><br>{cit_res}</div>", unsafe_allow_html=True)
            
            # C. 总结报告与视觉
            st.markdown("---")
            with st.spinner("生成高保真视觉模拟..."):
                final_report = client.chat.completions.create(model="claude-3-5-sonnet", messages=[{"role":"user","content":f"整合报告：{off_res}{cit_res}"}]).choices[0].message.content
                img_url = generate_visual(final_report)
            
            col_t, col_i = st.columns([2, 1])
            with col_t:
                st.markdown(f"<div class='report-box'>{final_report}</div>", unsafe_allow_html=True)
            with col_i:
                if img_url:
                    st.image(img_url, caption="📸 DALL-E 3 现场模拟", use_container_width=True)
                else:
                    st.warning("视觉引擎未响应（检查余额）")
        except Exception as e:
            st.error(f"博弈流程中断: {e}")
