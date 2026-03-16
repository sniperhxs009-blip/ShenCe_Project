import streamlit as st
import openai
import pandas as pd
import plotly.graph_objects as go
import requests

# --- 1. 页面配置 ---
st.set_page_config(page_title="神策 - AI 预测系统", layout="wide")

# --- 2. 安全获取 API Key ---
# 优先从 Streamlit Secrets 获取，本地运行时请配置 .streamlit/secrets.toml
if "OPENAI_API_KEY" in st.secrets:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.warning("⚠️ 未检测到 API Key，请在 Streamlit Cloud 设置中配置 OPENAI_API_KEY。")

# --- 3. 侧边栏：参数设置 ---
with st.sidebar:
    st.title("⚙️ 系统设置")
    model_choice = st.selectbox("选择预测模型", ["gpt-3.5-turbo", "gpt-4"])
    temperature = st.slider("创新度 (Temperature)", 0.0, 1.0, 0.7)
    st.info("神策系统：基于多智能体模拟的事件预测引擎")

# --- 4. 主界面设计 ---
st.title("🔮 ShenCe (神策) - 多智能体模拟预测")
st.markdown("---")

# 输入区域
user_input = st.text_area("请输入您想要模拟预测的事件描述：", placeholder="例如：分析未来半年内 AIGC 行业的发展趋势...")

if st.button("开始神策模拟"):
    if not user_input:
        st.error("请输入内容后再运行。")
    elif not openai.api_key:
        st.error("API Key 未配置，无法调用 AI 脑。")
    else:
        with st.spinner("智能体正在模拟中..."):
            try:
                # 调用 OpenAI 进行预测
                response = openai.ChatCompletion.create(
                    model=model_choice,
                    messages=[
                        {"role": "system", "content": "你是一个名为“神策”的专家预测系统。请通过逻辑推演和趋势分析提供深度预测。"},
                        {"role": "user", "content": user_input}
                    ],
                    temperature=temperature
                )
                
                prediction_text = response.choices[0].message.content

                # 展示预测结果
                st.subheader("📝 模拟预测报告")
                st.write(prediction_text)

                # --- 5. 数据可视化示例 (Plotly) ---
                st.markdown("---")
                st.subheader("📊 概率分布模拟")
                
                # 这里生成一些模拟数据来演示 Plotly 图表
                labels = ['成功概率', '风险概率', '中立概率']
                values = [65, 20, 15]
                
                fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
                fig.update_layout(title_text="事件结果模拟分布图")
                
                st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"模拟过程中发生错误: {str(e)}")

# --- 6. 底部信息 ---
st.markdown("---")
st.caption("© 2026 ShenCe Project | 基于多智能体架构开发")
