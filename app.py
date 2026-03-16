import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from openai import OpenAI

# --- 1. 网页外观设置（回归经典亮色版） ---
st.set_page_config(page_title="神策 - 全网态势推演引擎", layout="wide")

# 移除之前的黑色 CSS 样式，恢复默认外观
st.markdown("""
    <style>
    .stMetric { 
        background-color: #f0f2f6; 
        border-radius: 10px; 
        padding: 15px; 
        border: 1px solid #dcdfe6;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 侧边栏：核心功能与配置 ---
with st.sidebar:
    st.title("⚙️ 系统配置")
    st.info("请完成 API 授权以启动推演引擎")
    
    # 侧边栏功能项
    llm_key = st.text_input("DeepSeek/OpenAI API Key", type="password", help="用于驱动 AI 角色的思维")
    serper_key = st.text_input("Serper (联网) Key", type="password", help="用于获取全网实时情报")
    base_url = st.text_input("API Base URL", value="https://api.deepseek.com")
    
    st.divider()
    st.subheader("推演参数设定")
    rounds = st.slider("迭代博弈轮次", 1, 5, 3)
    temp = st.slider("思维发散度", 0.0, 1.0, 0.7)
    
    st.divider()
    st.caption("版本：神策 v2.1 (Classic White)")

# --- 3. 核心处理引擎 ---
def get_osint_data(query, key):
    if not key: return "未连接实时情报源，将使用静态数据。"
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': key, 'Content-Type': 'application/json'}
    try:
        resp = requests.post(url, headers=headers, json={"q": query, "num": 5})
        data = resp.json().get('organic', [])
        return "\n".join([f"【实时消息】{r['title']}: {r['snippet']}" for r in data])
    except: return "情报获取失败。"

def run_ai_logic(client, system_prompt, user_input):
    try:
        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}],
            temperature=temp
        )
        return completion.choices[0].message.content
    except Exception as e: return f"调用失败: {str(e)}"

# --- 4. 主界面布局 ---
st.title("🛰️ 神策：全网舆情态势仿真与演化推演系统")
st.write("欢迎使用神策系统。本平台结合实时 OSINT 情报与多智能体博弈技术，通过模拟不同社会角色的对抗与协作，预判事件演化趋势。")

# 事件输入区
event_input = st.text_area("🚀 输入目标推演事件", placeholder="请输入需要分析的突发事件关键词...", height=100)

if st.button("开始全维度推演", type="primary"):
    if not llm_key:
        st.warning("请在侧边栏配置 API Key 后再试。")
    else:
        client = OpenAI(api_key=llm_key, base_url=base_url)
        
        # 步骤 A: 实时搜索
        with st.status("正在搜寻全网情报...", expanded=True) as status:
            real_news = get_osint_data(event_input, serper_key)
            st.write(real_news)
            status.update(label="情报抓取完成", state="complete")
        
        # 步骤 B: 推演博弈
        metrics_data = {"轮次": [0], "稳定度指数": [80], "恐慌指数": [20]}
        current_context = f"初始事件: {event_input}\n搜集情报: {real_news}"
        
        tab_flow, tab_chart = st.tabs(["🕒 博弈演化过程", "📊 态势量化面板"])
        
        with tab_flow:
            for r in range(rounds):
                st.markdown(f"#### 第 {r+1} 轮：利益相关方博弈")
                c1, c2, c3 = st.columns(3)
                
                agents = {
                    "政府/官方": "侧重政策解读与秩序维护。格式：【行动】内容 【数值】稳定度(+/-)",
                    "公众/媒体": "侧重情绪反应与舆论传播。格式：【反馈】内容 【数值】恐慌度(+/-)",
                    "外部观察者": "客观分析潜在风险与未来走向。格式：【观察】内容 【数值】热度(+/-)"
                }
                
                round_log = ""
                for i, (name, prompt) in enumerate(agents.items()):
                    with [c1, c2, c3][i]:
                        st.markdown(f"**{name}**")
                        ans = run_ai_logic(client, prompt, f"背景: {current_context}")
                        st.info(ans)
                        round_log += f"{name}: {ans}\n"
                
                current_context += f"\n第{r+1}轮推演: {round_log}"
                
                # 模拟数据变化
                metrics_data["轮次"].append(r+1)
                metrics_data["稳定度指数"].append(max(0, metrics_data["稳定度指数"][-1] - 5))
                metrics_data["恐慌指数"].append(min(100, metrics_data["恐慌指数"][-1] + 8))

        with tab_chart:
            st.subheader("📈 态势演化趋势图")
            df = pd.DataFrame(metrics_data)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['轮次'], y=df['稳定度指数'], name='稳定度', line=dict(color='#2ecc71', width=3)))
            fig.add_trace(go.Scatter(x=df['轮次'], y=df['恐慌指数'], name='恐慌度', line=dict(color='#e74c3c', width=3)))
            fig.update_layout(xaxis_title="博弈轮次", yaxis_title="指数分值")
            st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            st.subheader("📜 综合研判报告")
            final_rpt = run_ai_logic(client, "你是首席战略分析师，请根据上述所有推演过程给出一份最终研判结论和应对对策。", current_context)
            st.success(final_rpt)
else:
    st.caption("系统就绪，请输入指令后点击启动。")
