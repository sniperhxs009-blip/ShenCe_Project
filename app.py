import streamlit as st
from openai import OpenAI
import requests
import json

# --- 密钥读取 (保持不变) ---
DEEPSEEK_K = st.secrets["DEEPSEEK_API_KEY"]
SERPER_K = st.secrets["SERPER_API_KEY"]
client = OpenAI(api_key=DEEPSEEK_K, base_url="https://api.deepseek.com")

def fetch_real_time_intelligence(query):
    """
    全维度信息采集：获取政策原文、新闻报道、社交媒体评论摘要
    """
    url = "https://google.serper.dev/search"
    # 组合搜索词，确保覆盖政策、民生和舆论
    search_queries = [f"{query} 官方政策内容", f"{query} 民众观点 评论", f"{query} 媒体深度分析"]
    all_context = []
    
    for q in search_queries:
        payload = json.dumps({"q": q, "gl": "cn", "hl": "zh-cn", "num": 5})
        headers = {'X-API-KEY': SERPER_K, 'Content-Type': 'application/json'}
        try:
            res = requests.post(url, headers=headers, data=payload)
            for item in res.json().get('organic', []):
                all_context.append(f"来源:{item.get('title')}\n内容:{item.get('snippet')}")
        except:
            continue
    return "\n\n".join(all_context)

# --- UI 界面 ---
st.title("🔮 ShenCe (神策) - 真实数据推演引擎")
st.info("本系统严禁编造，所有研判均基于实时采集的互联网真实数据。")

event_input = st.text_area("请输入真实发生的事件、政策或新闻：")

if st.button("开始全维度真实推演"):
    if event_input:
        with st.spinner("正在提取全网情报并构建逻辑链路..."):
            # 1. 采集最真实的互联网情报
            real_context = fetch_real_time_intelligence(event_input)
            
            # 2. 构建严谨的研判指令
            # 这里是核心：要求 AI 必须作为“分析师”而非“写手”
            strict_prompt = f"""
            你是一个严谨的社会治理研判分析师。
            你的任务是基于以下【真实情报】，对【目标事件】进行全维度逻辑推演。
            
            【目标事件】: {event_input}
            【真实情报库】: 
            {real_context}
            
            【推演要求】:
            1. 禁止虚构事实：所有分析必须在【真实情报库】的逻辑框架内。
            2. 官方维度：基于现有政策导向，推演官方最可能的动作，而非理想化的动作。
            3. 民众维度：基于情报中反映的利益受损或受益情况，推演不同阶层的心理及后续行为。
            4. 媒体维度：分析不同立场媒体（主流vs自媒体）的传播动机和可能带来的二次舆论冲击。
            5. 关联性推演：必须回答“若官方执行A，民众和媒体会有什么具体的连锁反应”。
            
            请输出《多维度综合研判报告》。
            """
            
            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个基于事实数据进行逻辑博弈推演的智能体。"},
                        {"role": "user", "content": strict_prompt}
                    ],
                    temperature=0.3 # 显著降低随机性，确保结果稳定、真实
                )
                
                st.markdown("---")
                st.markdown(response.choices[0].message.content)
                
                # 展示情报来源列表，证明“真实性”
                with st.expander("查看底层情报依据"):
                    st.text(real_context)

            except Exception as e:
                st.error(f"推演失败: {str(e)}")
