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

# --- 2. 侧边栏：完整功能面板回归 ---
with st.sidebar:
    st.title("⚙️ 系统控制中心")
    
    # 按照你要求的，最上面显示三个核心推演大脑
    st.subheader("🧠 推演大脑选择")
    model_option = st.radio(
        "选择核心推演引擎：",
        ["GPT-4o (战略级-高逻辑)", "GPT-4o-Mini (快速级-高响应)", "o1-preview (深思级-长链逻辑)"],
        index=0
    )
    # 映射模型 ID
    model_map = {
        "GPT-4o (战略级-高逻辑)": "gpt-4o",
        "GPT-4o-Mini (快速级-快速响应)": "gpt-4o-mini",
        "o1-preview (深思级-长链逻辑)": "o1-preview"
    }
    selected_model = model_map.get(model_option, "gpt-4o")
    
    st.divider()
    
    # 社会初始变量调节
    st.subheader("📊 社会系统初始值")
    init_eff = st.slider("初始政府效能 (Efficiency)", 0, 100, 80)
    init_panic = st.slider("初始民众焦虑 (Panic)", 0, 100, 20)
    init_res = st.slider("初始资源储备 (Resource)", 0, 100, 95)
    
    st.divider()
    
    # 仿真深度控制
    st.subheader("🛡️ 仿真深度设定")
    enable_serper = st.toggle("开启 Serper 真实案例对齐", value=True)
    logic_strict = st.toggle("开启物理环境强制约束", value=True)
    temp_val = st.slider("推演随机波动率", 0.0, 1.0, 0.7)

# --- 3. 核心 API 配置 ---
SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
BASE_URL = "https://api.ohmygpt.com/v1"
SERPER_API_KEY = "d57fbcfd2ecd16f71b9b131984050fab2c64d707" 
client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)

def fetch_evidence(query):
    if not enable_serper: return "未开启联网实证。"
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = json.dumps({"q": f"{query} 真实历史案例 群众反应 处置失败", "num": 8})
    try:
        res = requests.post(url, headers=headers, data=payload, timeout=15)
        return "\n".join([f"• {r.get('snippet')}" for r in res.json().get('organic', [])])
    except: return "实证抓取失败。"

# --- 4. 主程序 ---
st.title("🔮 SHENCE (神策) | 实证驱动·全维度演化仿真")
event_input = st.text_area("📡 初始扰动事件", placeholder="如：超大城市遭遇极端网络攻击，导致能源与银行系统全面瘫痪...", height=100)

if st.button("🚀 启动深度演化仿真"):
    if event_input:
        with st.status("🛠️ 环境建模与博弈推演中...", expanded=True) as status:
            # 1. 联网实证
            facts = fetch_evidence(event_input)
            # 2. 逻辑哨兵
            lg = f"事实：{facts}\n初始状态：效能{init_eff}, 焦虑{init_panic}, 储备{init_res}"
            
            # 3. 趋势计算 (防 KeyError)
            trend_p = f"输出T0, T24, T72, T7d四阶段指标JSON: {{'T0':[效,焦,匮,险],...}}"
            try:
                res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"system","content":lg},{"role":"user","content":trend_p}], response_format={"type":"json_object"}).choices[0].message.content
                time_data = json.loads(res)
            except:
                time_data = {"T0":[50]*4, "T24":[60]*4, "T72":[70]*4, "T7d":[80]*4}

            # 4. 多角色演化
            def sim(role, p):
                return client.chat.completions.create(model=selected_model, messages=[{"role":"system","content":f"你是{role}。{lg}"},{"role":"user","content":p}], temperature=temp_val).choices[0].message.content
            
            off = sim("应急指挥中心", "提出具体管控手段。")
            cit = sim("真实民众", "生存24小时后的真实状态。")
            med = sim("信息流向观察员", "谣言与群体心理变化。")
            rsk = sim("逻辑审计官", "基于物理常识修正前述内容。")
            
            path = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":f"基于{facts}生成连锁反应链条"}]).choices[0].message.content
            status.update(label="✅ 仿真完成", state="complete")

        # --- 布局渲染 ---
        st.markdown("### 📈 社会风险趋势预测 (基于实证权重)")
        fig = go.Figure()
        names = ['管控压力', '民众焦虑度', '资源匮乏率', '社会秩序风险']
        steps = ['T0', 'T24', 'T72', 'T7d']
        for i in range(4):
            y_vals = [time_data.get(s, [50]*4)[i] for s in steps]
            fig.add_trace(go.Scatter(x=['当前','24h','72h','7d'], y=y_vals, name=names[i], line=dict(width=5)))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 🔗 连锁反应路径")
        st.markdown(f"<div class='logic-box'>{path.replace('->', ' ➔ ')}</div>", unsafe_allow_html=True)

        st.divider()
        st.markdown("### 🔄 智能体多维博弈回溯")
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f"<div class='role-card role-official'><b>🏛️ 官方决策</b><br><br>{off}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='role-card role-citizen'><b>⚠️ 民众反应</b><br><br>{cit}</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='role-card role-media'><b>📢 舆论态势</b><br><br>{med}</div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='role-card role-risk'><b>🛡️ 逻辑审计</b><br><br>{rsk}</div>", unsafe_allow_html=True)

        st.divider()
        report_p = f"结合实证{facts}撰写深度研判报告。"
        report = client.chat.completions.create(model=selected_model, messages=[{"role":"user","content":report_p}]).choices[0].message.content
        st.markdown(f"<div class='report-card'><h2>📝 全维度综合研判报告 (实证驱动)</h2><br>{report}</div>", unsafe_allow_html=True)

else:
    st.info("💡 请在左侧选择推演大脑并调节初始变量，然后启动仿真。")
