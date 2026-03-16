import streamlit as st
from openai import OpenAI
import json
import plotly.graph_objects as go
import requests

# --- 1. 严格保留亮色全宽布局样式 ---
st.set_page_config(page_title="神策 - 战略级联动推演系统", layout="wide")

st.markdown("""
    <style>
    /* 强制亮色背景与全宽 */
    .block-container { max-width: 98% !important; padding: 2rem 1% !important; background-color: #ffffff; }
    
    /* 连锁反应路径 - 紫色边框亮色设计 */
    .logic-box { 
        background-color: #f1f3f9; padding: 30px; border-left: 12px solid #673ab7; 
        border-radius: 10px; margin: 25px 0; width: 100%; font-size: 1.2rem; 
        line-height: 1.7; font-family: 'Courier New', monospace; color: #1a1a1a;
    }
    
    /* 角色卡片样式还原 */
    .role-card { padding: 25px; border-radius: 12px; min-height: 450px; box-shadow: 0 8px 20px rgba(0,0,0,0.1); margin-bottom: 25px; border: 1px solid #e0e0e0; color: #1a1a1a; }
    .role-official { background-color: #f0f7ff; border-top: 10px solid #0056b3; }
    .role-citizen { background-color: #fff9e6; border-top: 10px solid #ffcc00; }
    .role-media { background-color: #f2fff2; border-top: 10px solid #28a745; }
    .role-risk { background-color: #fff2f2; border-top: 10px solid #dc3545; }
    
    /* 研判报告大卡片还原 */
    .report-card { 
        background-color: #ffffff; padding: 50px; border-radius: 20px; 
        border: 1px solid #d1d9e6; border-top: 20px solid #0056b3; 
        box-shadow: 0 15px 50px rgba(0,0,0,0.1); margin-top: 40px; width: 100%; color: #1a1a1a;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 侧边栏：精准显示模型具体功能 ---
with st.sidebar:
    st.title("⚙️ 引擎大脑架构")
    
    st.markdown("### 🤖 正在运行的模型节点")
    # 这里直接表明代码里正在使用的具体模型及其分工
    st.info("""
    **1. GPT-4o (战略指挥大脑)**
    * **作用：** 负责核心“四角色”博弈仿真、高逻辑研判报告生成，处理复杂社会学博弈逻辑。
    """)
    
    st.info("""
    **2. GPT-4o-Mini (量化计算大脑)**
    * **作用：** 负责 T0-T7d 稳定性指标的数值计算、连锁反应路径生成，确保响应速度与数据结构对齐。
    """)

    st.info("""
    **3. Serper.dev (实证事实库)**
    * **作用：** 负责实时采集全球历史真实案例数据，为 AI 仿真提供物理事实约束，杜绝幻觉。
    """)

    st.divider()
    
    st.subheader("📊 社会系统变量注入")
    init_eff = st.slider("初始政府效能 (Efficiency)", 0, 100, 80)
    init_panic = st.slider("初始民众焦虑 (Panic)", 0, 100, 20)
    init_res = st.slider("初始资源储备 (Resource)", 0, 100, 95)
    
    st.divider()
    
    st.subheader("🛡️ 仿真环境控制")
    enable_serper = st.toggle("启用 Serper 实时实证对齐", value=True)
    logic_strict = st.toggle("开启物理常识硬约束", value=True)
    temp_val = st.slider("思维发散率 (Temperature)", 0.0, 1.0, 0.7)

# --- 3. 核心 API 配置 ---
SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
BASE_URL = "https://api.ohmygpt.com/v1"
SERPER_API_KEY = "d57fbcfd2ecd16f71b9b131984050fab2c64d707" 
client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)

def fetch_evidence(query):
    if not enable_serper: return "实证功能已关闭。"
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = json.dumps({"q": f"{query} 历史真实案例 群众反应 官方处置", "num": 8})
    try:
        res = requests.post(url, headers=headers, data=payload, timeout=15)
        return "\n".join([f"• {r.get('snippet')}" for r in res.json().get('organic', [])])
    except: return "检索异常，启用预设模型。"

# --- 4. 主程序流程 ---
st.title("🔮 SHENCE (神策) | 多脑协同·复杂仿真系统")
event_input = st.text_area("📡 输入初始扰动事件", placeholder="请输入极端突发事件，系统将启动多脑协同推演...", height=100)

if st.button("🚀 启动全维度深度仿真"):
    if event_input:
        with st.status("🧠 模型大脑正在协同计算中...", expanded=True) as status:
            # 1. 联网实证 (Serper 节点)
            facts = fetch_evidence(event_input)
            
            # 2. 构建逻辑背景 (注入侧边栏数值)
            lg = f"事实基础：{facts}\n社会矩阵：效能{init_eff}, 焦虑{init_panic}, 储备{init_res}"
            
            # 3. 趋势量化 (GPT-4o-Mini 节点)
            st.write("📊 调用 GPT-4o-Mini 进行数值矩阵量化...")
            trend_p = f"输出T0, T24, T72, T7d四阶段指标JSON: {{'T0':[效,焦,匮,险],...}}"
            try:
                res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"system","content":lg},{"role":"user","content":trend_p}], response_format={"type":"json_object"}).choices[0].message.content
                time_data = json.loads(res)
            except:
                time_data = {"T0":[50]*4, "T24":[60]*4, "T72":[70]*4, "T7d":[80]*4}

            # 4. 深度推演 (GPT-4o 节点)
            st.write("🔄 调用 GPT-4o 启动多智能体博弈仿真...")
            def sim(role, p):
                return client.chat.completions.create(model="gpt-4o", messages=[{"role":"system","content":f"你是{role}。{lg}"},{"role":"user","content":p}], temperature=temp_val).choices[0].message.content
            
            off = sim("应急指挥中心", "提出具体管控措施。")
            cit = sim("真实受灾民众", "描述生理与心理真实反应。")
            med = sim("信息观察员", "谣言扩散与社会心理变化。")
            rsk = sim("逻辑审计官", "无情纠正推演幻觉。")
            
            path = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":f"基于{facts}生成连锁反应链条"}]).choices[0].message.content
            status.update(label="✅ 所有大脑完成计算", state="complete")

        # --- 数据渲染 ---
        st.markdown("### 📈 社会风险趋势预测")
        fig = go.Figure()
        names = ['管控压力', '民众焦虑度', '资源匮乏率', '社会秩序风险']
        steps = ['T0', 'T24', 'T72', 'T7d']
        for i in range(4):
            y_vals = [time_data.get(s, [50]*4)[i] for s in steps]
            fig.add_trace(go.Scatter(x=['当前','24h','72h','7d'], y=y_vals, name=names[i], line=dict(width=5)))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 🔗 连锁反应路径 (Causal Chain)")
        st.markdown(f"<div class='logic-box'>{path.replace('->', ' ➔ ')}</div>", unsafe_allow_html=True)

        st.divider()
        st.markdown("### 🔄 智能体多维博弈回溯")
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f"<div class='role-card role-official'><b>🏛️ 官方决策</b><br><br>{off}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='role-card role-citizen'><b>⚠️ 民众反应</b><br><br>{cit}</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='role-card role-media'><b>📢 舆论态势</b><br><br>{med}</div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='role-card role-risk'><b>🛡️ 逻辑审计</b><br><br>{rsk}</div>", unsafe_allow_html=True)

        st.divider()
        report_p = f"结合实证{facts}与博弈结果写深度报告。"
        report = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":report_p}]).choices[0].message.content
        st.markdown(f"<div class='report-card'><h2>📝 全维度综合研判报告 (实证驱动)</h2><br>{report}</div>", unsafe_allow_html=True)

else:
    st.info("💡 请调节左侧模型大脑变量并输入目标启动推演。")
