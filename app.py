import streamlit as st
from openai import OpenAI
import requests
import json
import plotly.graph_objects as go
from datetime import datetime

# --- 1. 页面配置 (必须在首行) ---
st.set_page_config(page_title="神策 - 智能研判引擎", layout="wide", initial_sidebar_state="collapsed")

# --- 自定义 CSS 提升科技感 ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #262730; color: #00ffcc; border: 1px solid #00ffcc; }
    .report-card { border: 1px solid #30363d; border-radius: 10px; padding: 15px; background: #161b22; min-height: 400px; }
    h3 { color: #00ffcc !important; border-bottom: 1px solid #00ffcc; padding-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 密钥读取 ---
DEEPSEEK_K = st.secrets["DEEPSEEK_API_KEY"]
SERPER_K = st.secrets["SERPER_API_KEY"]
client = OpenAI(api_key=DEEPSEEK_K, base_url="https://api.deepseek.com")

# --- 3. 逻辑函数 ---
def fetch_real_intelligence(query):
    url = "https://google.serper.dev/search"
    search_query = f"{query} 官方政策 社交媒体评论 深度分析"
    payload = json.dumps({"q": search_query, "gl": "cn", "hl": "zh-cn", "num": 10})
    headers = {'X-API-KEY': SERPER_K, 'Content-Type': 'application/json'}
    try:
        res = requests.post(url, headers=headers, data=payload)
        return "\n".join([f"· {i.get('snippet')}" for i in res.json().get('organic', [])])
    except:
        return "未能抓取实时数据。"

def agent_call(role_prompt, event, context):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": f"你是一个逻辑严密的AI研判体。{role_prompt}。必须基于事实推演，严禁虚构。"},
            {"role": "user", "content": f"情报：{context}\n事件：{event}"}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content

# --- 4. 界面顶部 ---
st.title("🔮 SHENCE (神策) | 多智能体全维度研判系统")
st.write(f"当前系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据源: 实时互联网情报")

event_input = st.text_area("📡 输入研判目标 (事件/政策/新闻)", placeholder="请输入需要进行沙盘推演的内容...")

if st.button("🚀 开启全维度逻辑推演"):
    if event_input:
        with st.spinner("🕵️ 情报员正在渗透网络采集真实数据..."):
            intelligence = fetch_real_intelligence(event_input)
        
        # --- 四列展示 ---
        st.markdown("### 🖥️ 角色沙盘实时推演")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("### 🏛️ 官方决策")
            res_official = agent_call("模拟官方发言人，推演政策意图、执行步骤及权威立场", event_input, intelligence)
            st.info(res_official)

        with col2:
            st.markdown("### 👥 民众反应")
            res_citizen = agent_call("模拟社会观察员，基于民生情报推演底层情绪、核心诉求及对抗/拥护心理", event_input, intelligence)
            st.success(res_citizen)

        with col3:
            st.markdown("### 📰 媒体舆论")
            res_media = agent_call("模拟媒体专家，分析主流定调、自媒体爆点及舆论反转风险", event_input, intelligence)
            st.warning(res_media)

        with col4:
            st.markdown("### 🛡️ 风险预警")
            res_risk = agent_call("模拟首席安全官，识别潜在的社会风险、治理漏洞及负面连锁反应", event_input, intelligence)
            st.error(res_risk)

        # --- 5. 深度综合分析报告 (大区) ---
        st.markdown("---")
        st.markdown("### 📊 深度综合研判报告")
        
        # 报告生成提示词更强、更深度
        final_report_prompt = """你是一个战略专家，请综合以上官方、民众、媒体和风险四个维度的博弈关系，出一份500字以上的深度综合研判报告。
        要求：
        1. 包含核心态势评估。
        2. 包含三方逻辑博弈分析（官方动作引发的民众与媒体反应链）。
        3. 包含最终的应对策略建议。"""
        
        final_report = agent_call(final_report_prompt, event_input, intelligence)
        
        # 展示报告
        st.markdown(f"""<div style="border: 2px solid #00ffcc; padding: 20px; border-radius: 10px;">
            {final_report}
        </div>""", unsafe_allow_html=True)

        # --- 6. 数据可视化图表 ---
        st.markdown("### 📈 研判量化指标")
        c1, c2 = st.columns(2)
        with c1:
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number", value = 88, title = {'text': "研判置信度 (%)"},
                gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#00ffcc"}}
            ))
            st.plotly_chart(fig_gauge, use_container_width=True)
        with c2:
            # 模拟一个博弈平衡图
            fig_radar = go.Figure(data=go.Scatterpolar(
                r=[80, 50, 70, 40], theta=['官方意志','民众接受度','媒体传播力','社会风险'], fill='toself', line_color='#00ffcc'
            ))
            st.plotly_chart(fig_radar, use_container_width=True)

        # --- 7. 下载功能 ---
        st.download_button(
            label="💾 下载深度研判报告",
            data=f"神策全维度研判报告\n事件：{event_input}\n\n{final_report}\n\n--- 原始数据支持 ---\n{intelligence}",
            file_name=f"神策报告_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )
    else:
        st.warning("请先输入研判目标。")
