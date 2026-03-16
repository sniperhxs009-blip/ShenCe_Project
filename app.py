import streamlit as st
from openai import OpenAI
import json
import plotly.graph_objects as go
import requests
import pandas as pd

# --- 1. 页面配置与全宽样式 ---
st.set_page_config(page_title="神策 - 战略级联动推演系统", layout="wide")

st.markdown("""
    <style>
    .block-container { max-width: 98% !important; padding: 1.5rem 1% !important; }
    .logic-box { 
        background-color: #f1f3f9; padding: 25px; border-left: 10px solid #673ab7; 
        border-radius: 8px; margin: 20px 0; font-size: 1.1rem; line-height: 1.6;
    }
    .role-card { padding: 20px; border-radius: 12px; min-height: 450px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #eef0f2; }
    .role-official { background-color: #f0f7ff; border-top: 8px solid #0056b3; }
    .role-citizen { background-color: #fff9e6; border-top: 8px solid #ffcc00; }
    .role-media { background-color: #f2fff2; border-top: 8px solid #28a745; }
    .role-risk { background-color: #fff2f2; border-top: 8px solid #dc3545; }
    .report-card { 
        background-color: #ffffff; padding: 40px; border-radius: 15px; border: 1px solid #d1d9e6; 
        border-top: 15px solid #0056b3; box-shadow: 0 10px 30px rgba(0,0,0,0.1); width: 100%; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 侧边栏：核心控制面板 ---
with st.sidebar:
    st.header("⚙️ 推演控制中心")
    
    st.subheader("🤖 模型配置")
    model_choice = st.selectbox("选择仿真大脑", ["gpt-4o", "gpt-4o-mini"], index=0)
    temperature = st.slider("推演随机性 (Temperature)", 0.0, 1.0, 0.7)
    
    st.divider()
    
    st.subheader("📊 社会系统初始状态")
    init_eff = st.slider("初始行政效能", 0, 100, 80)
    init_panic = st.slider("初始民众焦虑", 0, 100, 30)
    init_res = st.slider("初始资源储备", 0, 100, 90)
    
    st.divider()
    
    st.subheader("🛡️ 仿真深度开关")
    enable_serper = st.toggle("开启真实历史实证 (Serper)", value=True)
    strict_logic = st.toggle("强制物理环境约束 (断网/断电)", value=True)
    
    if st.button("🗑️ 清除推演历史"):
        st.cache_data.clear()
        st.rerun()

# --- 3. 核心 API 配置 ---
SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
BASE_URL = "https://api.ohmygpt.com/v1"
SERPER_API_KEY = "d57fbcfd2ecd16f71b9b131984050fab2c64d707" 

client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)

# --- 4. 功能函数 ---
def fetch_real_world_evidence(query):
    if not enable_serper:
        return "实证检索已关闭，基于通用社会学模型推演。"
    search_url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = json.dumps({"q": f"{query} 历史案例 真实表现 群众行为 骚乱 抢购 处置教训", "num": 8})
    try:
        response = requests.post(search_url, headers=headers, data=payload, timeout=15)
        results = response.json().get('organic', [])
        return "\n".join([f"【历史实证】: {r.get('snippet')}" for r in results])
    except:
        return "联网检索失败，启用离线高保真模拟。"

# --- 5. 主流程界面 ---
st.title("🔮 SHENCE (神策) | 极端环境仿真推演平台")
event_input = st.text_area("📡 仿真目标输入", placeholder="输入极端事件（如：超大城市供水系统遭网络攻击瘫痪48小时）...", height=100)

if st.button("🚀 启动全维度深度推演"):
    if event_input:
        with st.status("🛠️ 正在初始化仿真环境...", expanded=True) as status:
            
            # 1. 抓取实证
            st.write("🌐 联网提取历史相似案例规律...")
            facts = fetch_real_world_evidence(event_input)
            
            # 2. 构建逻辑约束 (带侧边栏初始值)
            logic_guard = f"""
            推演基石：以下是检索到的真实历史数据点：{facts}
            当前系统初始状态：行政效能{init_eff}，民众焦虑{init_panic}，资源储备{init_res}。
            
            【逻辑约束】：
            - {'强制物理环境约束：严禁使用受损资源（如断电场景禁止APP办公）。' if strict_logic else '常规环境约束。'}
            - 仿真深度：体现马斯洛生存底层需求，拒绝温和口吻，展示真实治理难题。
            """

            # 3. 生成趋势数据
            st.write("📊 正在量化社会稳定性变动指标...")
            res_data = client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[{"role":"system","content":logic_guard},{"role":"user","content":"输出T0,24,72,7d四阶段JSON数据：[管控压力, 焦虑度, 匮乏率, 风险指]"}],
                response_format={"type":"json_object"}
            ).choices[0].message.content
            time_data = json.loads(res_data)

            # 4. 多角色博弈
            st.write("🔄 激活多主体博弈仿真...")
            def sim_role(role_name, prompt):
                return client.chat.completions.create(
                    model=model_choice, 
                    messages=[{"role": "system", "content": f"你是{role_name}。{logic_guard}"},{"role":"user","content":prompt}],
                    temperature=temperature
                ).choices[0].message.content

            off = sim_role("应急指挥部", f"针对{event_input}提出管控手段。")
            cit = sim_role("受灾民众", f"描述生存24小时后的真实反应。")
            med = sim_role("信息流传播者", f"描述通讯黑洞中的谣言演化。")
            rsk = sim_role("逻辑审计官", f"指出以上推演中不切实际的幻觉部分。")

            path_code = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":f"基于{facts}生成此事件的连锁反应路径"}]).choices[0].message.content
            status.update(label="✅ 仿真建模完成", state="complete")

        # --- 第一部分：指标趋势 ---
        st.markdown("### 📈 社会风险趋势预测")
        fig = go.Figure()
        names = ['管控压力', '民众焦虑度', '资源匮乏率', '社会秩序风险']
        for i in range(4):
            # 提取数据点
            y = [time_data.get('T0',[50]*4)[i], time_data.get('T24',[60]*4)[i], time_data.get('T72',[70]*4)[i], time_data.get('T7d',[80]*4)[i]]
            fig.add_trace(go.Scatter(x=['当前','24h','72h','7d'], y=y, name=names[i], line=dict(width=6)))
        fig.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

        # --- 第二部分：因果逻辑链 ---
        st.markdown("### 🔗 连锁反应路径")
        st.markdown(f"<div class='logic-box'>{path_code.replace('->', ' ➔ ')}</div>", unsafe_allow_html=True)

        # --- 第三部分：核心对策 ---
        st.markdown("### 💡 核心对策推荐")
        strat = client.chat.completions.create(model=model_choice, messages=[{"role":"system","content":logic_guard},{"role":"user","content":"给出3条基于物理事实的硬核处置对策。"}]).choices[0].message.content
        st.success(strat)

        # --- 第四部分：四角色博弈 ---
        st.divider()
        st.markdown("### 🔄 智能体多维博弈回溯")
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f"<div class='role-card role-official'><b>🏛️ 官方决策</b><br><br>{off}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='role-card role-citizen'><b>⚠️ 民众反应</b><br><br>{cit}</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='role-card role-media'><b>📢 舆论态势</b><br><br>{med}</div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='role-card role-risk'><b>🛡️ 逻辑审计</b><br><br>{rsk}</div>", unsafe_allow_html=True)

        # --- 第五部分：深度研判报告 ---
        st.divider()
        report_prompt = f"基于实证数据：{facts}。为{event_input}撰写深度研判报告。要求：1.物理瘫痪分析；2.社会稳定拐点预警；3.战略应对建议。"
        final_report = client.chat.completions.create(model=model_choice, messages=[{"role":"system","content":"国家安全专家"},{"role":"user","content":report_prompt}]).choices[0].message.content
        st.markdown(f"<div class='report-card'><h2>📝 全维度深度综合研判报告</h2><br>{final_report}</div>", unsafe_allow_html=True)

else:
    st.info("💡 请在左侧侧边栏配置仿真参数，并在上方输入框输入仿真目标。")
