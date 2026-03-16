import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from openai import OpenAI

# --- 1. 网页外观与高级设置 ---
st.set_page_config(page_title="神策 - 全网态势推演引擎", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050a14; color: #e0e0e0; }
    .stMetric { background: #112244; border: 1px solid #1f4287; border-radius: 8px; padding: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 侧边栏：API 密钥管理 ---
with st.sidebar:
    st.header("⚙️ 系统机能配置")
    st.markdown("---")
    # 这里我们把默认值留空，让你手动输入，确保安全
    llm_key = st.text_input("DeepSeek/OpenAI Key", type="password")
    serper_key = st.text_input("Serper Search Key", type="password")
    base_url = st.text_input("API Base URL", value="https://api.deepseek.com")
    
    st.markdown("---")
    rounds = st.slider("推演迭代深度", 1, 5, 3)
    st.caption("轮次越高，演化分析越深，但耗时越长。")

# --- 3. 核心功能引擎 ---
def search_live_info(query, key):
    """接入 Serper API 实现实时全网情报感知"""
    if not key: return "未连接实时情报源。"
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': key, 'Content-Type': 'application/json'}
    try:
        response = requests.post(url, headers=headers, json={"q": query, "num": 5})
        data = response.json().get('organic', [])
        return "\n".join([f"【实时消息】{r['title']}: {r['snippet']}" for r in data])
    except: return "情报感知系统连接超时。"

def ai_brain(client, system_msg, user_msg):
    """驱动大模型进行深度思考"""
    try:
        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            temperature=0.8
        )
        return completion.choices[0].message.content
    except Exception as e: return f"思维阻断: {str(e)}"

# --- 4. 主界面展示 ---
st.title("🛰️ 神策：全网舆情态势仿真与演化推演系统")
st.write("本系统通过多 Agent 博弈模型，针对突发事件进行社会学与情报学维度的演化预测。")

input_event = st.text_area("🔍 输入目标事件或潜在威胁关键词", placeholder="请输入如：'某跨国企业服务器遭受勒索攻击，涉及数千万用户信息'...")

if st.button("启动全维度态势推演"):
    if not llm_key:
        st.error("请在侧边栏配置 API Key 后启动。")
    else:
        # 初始化 AI 客户端
        client = OpenAI(api_key=llm_key, base_url=base_url)
        
        # 第一阶段：情报注入
        with st.status("📡 正在全网搜寻实时情报...", expanded=True) as s:
            news = search_live_info(input_event, serper_key)
            st.markdown(news)
            s.update(label="情报注入完毕", state="complete")
        
        # 第二阶段：多维度博弈推演
        metrics = {"轮次": [0], "稳定度": [85], "恐慌度": [15]}
        context = f"初始事件: {input_event}\n注入情报: {news}"
        
        tab_flow, tab_data = st.tabs(["🕒 演化博弈过程", "📊 量化态势面板"])
        
        with tab_flow:
            for r in range(rounds):
                st.subheader(f"第 {r+1} 轮博弈分析")
                cols = st.columns(3)
                agents = {
                    "🏛️ 官方决策层": "分析应对政策与公信力维护。格式：【行动】内容 【数值】稳定度(+/-)",
                    "👥 社会公众层": "分析民意走向与恐慌蔓延。格式：【情绪】内容 【数值】恐慌度(+/-)",
                    "📢 传播媒介层": "分析信息扩散与真伪博弈。格式：【传播】内容 【数值】热度(+/-)"
                }
                
                round_log = ""
                for i, (name, prompt) in enumerate(agents.items()):
                    with cols[i]:
                        response = ai_brain(client, prompt, f"当前态势: {context}")
                        st.info(f"**{name}**\n\n{response}")
                        round_log += f"{name}: {response}\n"
                
                context += f"\n第{r+1}轮演化结论: {round_log}"
                
                # 动态更新量化指标
                metrics["轮次"].append(r+1)
                metrics["稳定度"].append(max(0, metrics["稳定度"][-1] - 5))
                metrics["恐慌度"].append(min(100, metrics["恐慌度"][-1] + 12))

        with tab_data:
            st.subheader("📈 态势动态演化曲线")
            df = pd.DataFrame(metrics)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['轮次'], y=df['稳定度'], name='稳定指数', line=dict(color='#00ff88', width=3)))
            fig.add_trace(go.Scatter(x=df['轮次'], y=df['恐慌度'], name='恐慌指数', line=dict(color='#ff4444', width=3)))
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            st.subheader("📜 最终战略预测报告")
            final_rpt = ai_brain(client, "你是一名顶级战略分析师，请基于以上推演输出一份针对该事件的最终风险总结和3条具体应对建议。", context)
            st.success(final_rpt)
else:
    st.info("等待任务下达...")