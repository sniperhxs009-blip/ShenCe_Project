import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from openai import OpenAI

# --- 1. 页面基础配置 (回归经典亮色版) ---
st.set_page_config(page_title="神策 - 全网态势推演引擎", layout="wide", initial_sidebar_state="expanded")

# 亮色模式下的 UI 细节美化
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    .stMetric { 
        background-color: #f0f2f6; 
        border: 1px solid #dcdfe6;
        border-radius: 10px; 
        padding: 15px; 
    }
    .stChatMessage { border-radius: 10px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 侧边栏：核心情报与参数配置 ---
with st.sidebar:
    st.title("🛡️ 神策系统配置")
    st.markdown("---")
    
    # API 密钥输入区
    llm_key = st.text_input("DeepSeek/OpenAI Key", type="password", help="驱动 AI 大脑的核心密钥")
    serper_key = st.text_input("Serper (OSINT) Key", type="password", help="用于接入全网实时搜索情报")
    base_url = st.text_input("API Base URL", value="https://api.deepseek.com")
    
    st.divider()
    st.subheader("🎲 模拟参数控制")
    rounds = st.slider("推演博弈轮次", 1, 5, 3)
    temp = st.slider("模型随机性 (Temperature)", 0.0, 1.0, 0.7)
    
    st.divider()
    st.caption("神策 v4.0 | 竞赛专业版 (Classic White)")

# --- 3. 核心功能函数定义 ---
def fetch_live_osint(query, api_key):
    """通过 Serper API 获取实时全网情报"""
    if not api_key:
        return "【提示】未检测到 Serper Key，系统将进入离线推演模式。"
    
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    try:
        response = requests.post(url, headers=headers, json={"q": query, "num": 5}, timeout=10)
        results = response.json().get('organic', [])
        context = "\n".join([f"· {r['title']}: {r['snippet']}" for r in results])
        return context if context else "未搜寻到相关实时动态。"
    except Exception:
        return "【错误】情报抓取连接失败。"

def call_ai_brain(client, sys_prompt, user_content):
    """驱动大模型进行深度逻辑推演"""
    try:
        completion = client.chat.completions.create(
            model="deepseek-chat", # 也可根据需要改为 gpt-4-turbo
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=temp
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"系统思维阻断: {str(e)}"

# --- 4. 主界面展示逻辑 ---
st.title("🛰️ 神策：全网舆情态势仿真与演化推演系统")
st.write("本系统通过整合 OSINT 实时情报流，利用多智能体博弈模型，对突发事件的社会演化趋势进行量化模拟与预测。")

# 目标事件输入框
target_event = st.text_area("🚀 输入目标推演事件或关键词", placeholder="请输入例如：'某大型社交平台发生大规模隐私泄露，引发社会广泛讨论'...", height=100)

if st.button("启动全维度态势推演", type="primary"):
    if not llm_key:
        st.warning("请先在左侧侧边栏填入 API Key 后启动！")
    else:
        # 初始化 AI 客户端
        client = OpenAI(api_key=llm_key, base_url=base_url)
        
        # 第一阶段：实时情报注入 (OSINT 环节)
        with st.status("正在扫描全网实时 OSINT 情报...", expanded=True) as status:
            real_news = fetch_live_osint(target_event, serper_key)
            st.markdown(f"**实时感知背景：**\n{real_news}")
            status.update(label="情报抓取完成", state="complete")
        
        # 第二阶段：量化指标初始化
        metrics_history = {"轮次": [0], "社会稳定度": [85], "公众恐慌度": [15], "舆情热度": [10]}
        current_context = f"初始事件定义: {target_event}\n全网实时情报: {real_news}"
        
        # 页面布局：过程展示与数据看板
        tab_flow, tab_data = st.tabs(["🕒 博弈演化过程", "📊 态势量化面板"])
        
        with tab_flow:
            for r in range(rounds):
                st.markdown(f"### 第 {r+1} 轮演化博弈")
                col1, col2, col3 = st.columns(3)
                
                # 定义三个核心 Agent 角色
                agents = {
                    "🏛️ 政府/官方": "侧重于政策引导、辟谣与秩序维护。输出格式：【行动】内容 【数值评分】稳定度变化(-10到10)",
                    "👥 公众/受众": "侧重于情绪波动、诉求表达与二次传播。输出格式：【情绪反馈】内容 【数值评分】恐慌度变化(0到20)",
                    "📢 媒体/观察员": "侧重于事实挖掘、深度评论与影响预测。输出格式：【深度观察】内容 【数值评分】热度变化(0到20)"
                }
                
                round_log = ""
                for i, (name, prompt) in enumerate(agents.items()):
                    with [col1, col2, col3][i]:
                        st.markdown(f"**{name}**")
                        ai_response = call_ai_brain(client, prompt, f"当前全景态势历史:\n{current_context}")
                        st.info(ai_response)
                        round_log += f"{name}: {ai_response}\n"
                
                # 更新上下文以进行下一轮迭代
                current_context += f"\n第{r+1}轮演化结论: {round_log}"
                
                # 模拟数据更新（在比赛演示中体现趋势演化）
                metrics_history["轮次"].append(r+1)
                metrics_history["社会稳定度"].append(max(0, metrics_history["社会稳定度"][-1] - 5))
                metrics_history["公众恐慌度"].append(min(100, metrics_history["公众恐慌度"][-1] + 10))
                metrics_history["舆情热度"].append(min(100, metrics_history["舆论热度"][-1] + 15))

        with tab_data:
            st.subheader("📈 态势动态演化曲线")
            df = pd.DataFrame(metrics_history)
            
            # 使用 Plotly 绘制美观的动态折线图
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['轮次'], y=df['社会稳定度'], name='稳定度指数', line=dict(color='#28a745', width=3)))
            fig.add_trace(go.Scatter(x=df['轮次'], y=df['公众恐慌度'], name='恐慌度指数', line=dict(color='#dc3545', width=3)))
            fig.add_trace(go.Scatter(x=df['轮次'], y=df['舆情热度'], name='传播热度指数', line=dict(color='#007bff', width=3)))
            
            fig.update_layout(
                xaxis_title="博弈轮次",
                yaxis_title="量化评分 (0-100)",
                legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            st.subheader("📜 综合风险研判总结")
            final_report_prompt = "你是一名资深战略预测专家，请基于上述所有演化博弈过程，给出一份深度总结报告。包含：1. 核心风险点识别；2. 未来48小时走势预测；3. 三条针对性的应对策略。"
            final_report = call_ai_brain(client, final_report_prompt, current_context)
            st.success(final_report)

else:
    st.write("---")
    st.caption("系统就绪。请在侧边栏输入密钥并填写推演目标，随后点击启动。")
