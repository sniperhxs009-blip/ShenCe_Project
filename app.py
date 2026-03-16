import streamlit as st
from openai import OpenAI
import requests
import json
import plotly.graph_objects as go

# --- 1. 页面设置 ---
st.set_page_config(page_title="神策预测系统", layout="wide")

# --- 2. 从 Secrets 安全读取 Key ---
# 确保你在 Streamlit 网页后台填了这两个名字
try:
    DEEPSEEK_K = st.secrets["DEEPSEEK_API_KEY"]
    SERPER_K = st.secrets["SERPER_API_KEY"]
except KeyError:
    st.error("请在 Streamlit Cloud 的 Secrets 设置中配置 DEEPSEEK_API_KEY 和 SERPER_API_KEY")
    st.stop()

# --- 3. 初始化 DeepSeek 客户端 ---
client = OpenAI(api_key=DEEPSEEK_K, base_url="https://api.deepseek.com")

# --- 4. 定义联网搜索函数 (Serper) ---
def serper_search(query):
    url = "https://google.serper.dev/search"
    # 增加中文搜索优化 (gl:cn 为中国区, hl:zh-cn 为中文)
    payload = json.dumps({"q": query, "gl": "cn", "hl": "zh-cn"})
    headers = {
        'X-API-KEY': SERPER_K,
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(url, headers=headers, data=payload)
        result = response.json()
        # 提取前3条搜索结果的摘要
        snippets = [item['snippet'] for item in result.get('organic', [])[:3]]
        return "\n".join(snippets)
    except Exception as e:
        return f"搜索失败: {str(e)}"

# --- 5. 主界面 UI ---
st.title("🔮 ShenCe (神策) - 联网增强版")
st.markdown("---")

user_input = st.text_input("请输入您想预测的事件描述：", placeholder="例如：预测未来一个月内某科技公司的股价趋势...")

if st.button("开始神策模拟"):
    if user_input:
        with st.spinner("🕵️ 神策正在联网搜集情报并进行多智能体推演..."):
            # 第一步：联网搜索背景资料
            search_context = serper_search(user_input)
            
            # 第二步：将资料喂给 DeepSeek 进行预测
            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个名为“神策”的专家预测系统。请结合提供的联网搜索实时资料进行深度逻辑推演。"},
                        {"role": "user", "content": f"实时背景资料：\n{search_context}\n\n请根据以上资料分析并预测：{user_input}"}
                    ],
                    temperature=0.7
                )
                
                # 展示预测结果
                st.markdown("### 📝 深度预测报告")
                st.write(response.choices[0].message.content)

                # 展示一个简单的可视化图表（示例）
                st.markdown("---")
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = 85,
                    title = {'text': "预测置信度"},
                    gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "darkblue"}}
                ))
                st.plotly_chart(fig)

            except Exception as e:
                st.error(f"DeepSeek 响应出错: {str(e)}")
    else:
        st.warning("请输入内容后再点击运行。")
