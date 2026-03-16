import streamlit as st
from openai import OpenAI
import json
import plotly.graph_objects as go
import requests

# --- 1. 恢复你要求的亮色全宽布局样式 ---
st.set_page_config(page_title="神策 - 战略级联动推演系统", layout="wide")

st.markdown("""
    <style>
    /* 恢复亮色全宽背景 */
    .block-container { max-width: 98% !important; padding: 2rem 1% !important; background-color: #ffffff; }
    
    /* 连锁反应路径 - 恢复你的紫色边框亮色设计 */
    .logic-box { 
        background-color: #f1f3f9; padding: 30px; border-left: 12px solid #673ab7; 
        border-radius: 10px; margin: 25px 0; width: 100%; font-size: 1.2rem; 
        line-height: 1.7; font-family: 'Courier New', monospace; color: #1a1a1a;
    }
    
    /* 角色卡片 - 恢复原有配色 */
    .role-card { padding: 25px; border-radius: 12px; min-height: 450px; box-shadow: 0 8px 20px rgba(0,0,0,0.1); margin-bottom: 25px; border: 1px solid #e0e0e0; color: #1a1a1a; }
    .role-official { background-color: #f0f7ff; border-top: 10px solid #0056b3; }
    .role-citizen { background-color: #fff9e6; border-top: 10px solid #ffcc00; }
    .role-media { background-color: #f2fff2; border-top: 10px solid #28a745; }
    .role-risk { background-color: #fff2f2; border-top: 10px solid #dc3545; }
    
    /* 深度研判报告 - 恢复置底巨幕卡片 */
    .report-card { 
        background-color: #ffffff; padding: 50px; border-radius: 20px; 
        border: 1px solid #d1d9e6; border-top: 20px solid #0056b3; 
        box-shadow: 0 15px 50px rgba(0,0,0,0.1); margin-top: 40px; width: 100%; color: #1a1a1a;
    }
    .report-card h2, .report-card h3, .report-card p { color: #1a1a1a !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 侧边栏控制面板 (新增功能集成) ---
with st.sidebar:
    st.header("⚙️ 仿真参数调节")
    model_choice = st.selectbox("核心推演引擎", ["gpt-4o", "gpt-4o-mini"], index=0)
    st.divider()
    st.subheader("📊 社会初始变量")
    # 将滑动条数值关联到后续 Prompt
    init_eff = st.slider("政府效能 (Efficiency)", 0, 100, 80)
    init_panic = st.slider("社会焦虑 (Panic)", 0, 100, 30)
    init_res = st.slider("资源储备 (Resource)", 0, 100, 90)
    st.divider()
    enable_serper = st.toggle("联网实证数据对齐", value=True)

# --- 3. 核心 API 配置 ---
SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
BASE_URL = "https://api.ohmygpt.com/v1"
SERPER_API_KEY = "d57fbcfd2ecd16f71b9b131984050fab2c64d707" 
client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)

def fetch_real_world_evidence(query):
    if not enable_serper: return "联网检索已关闭。"
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = json.dumps({"q": f"{query} 历史案例 真实社会反应 处置教训", "num": 8})
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=15)
        return "\n".join([f"• {r.get('snippet')}" for r in response.json().get('organic', [])])
    except: return "实证检索异常，启用预设逻辑。"

# --- 4. 主流程逻辑 ---
st.title("🔮 SHENCE (神策) | 实证数据驱动·极端环境仿真推演")
event_input = st.text_area("📡 仿真目标输入", placeholder="如：千万人口城市大规模停电超过24小时...", height=100)

if st.button("🚀 启动实证驱动仿真推演"):
    if event_input:
        with st.status("🛠️ 执行实证抓取与逻辑校准...", expanded=True) as status:
            # 1. 联网抓取实证
            facts = fetch_real_world_evidence(event_input)
            
            # 2. 注入逻辑防御 (结合侧边栏数值)
            logic_guard = f"""
            实证背景：{facts}
            当前状态：行政效能{init_eff}，焦虑度{init_panic}，储备{init_res}。
            【逻辑约束】：严禁断电下网络支付，必须体现马斯洛底层生存冲突。
            """

            # 3. 生成趋势数据 (加入防报错逻辑)
            st.write("📊 正在量化指标变动...")
            trend_p = f"基于背景，输出T0, T24, T72, T7d四阶段社会指标JSON。格式：{{'T0':[效,焦,匮,险],...}}"
            try:
                res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"system","content":logic_guard},{"role":"user","content":trend_p}], response_format={"type":"json_object"}).choices[0].message.content
                time_data = json.loads(res)
            except:
                time_data = {"T0":[50]*4, "T24":[60]*4, "T72":[70]*4, "T7d":[80]*4}

            # 4. 多角色博弈
            st.write("🔄 激活多主体博弈仿真...")
            def sim_role(role, p):
                return client.chat.completions.create(model=model_choice, messages=[{"role": "system", "content": f"你是{role}。{logic_guard}"},{"role": "user", "content": p}]).choices[0].message.content

            off = sim_role("应急指挥部", f"针对{event_input}提出强制物理管控手段。")
            cit = sim_role("受灾民众", f"描述生存24小时后的真实反应。")
            med = sim_role("信息传播者", f"描述谣言如何引发群体行为。")
            rsk = sim_role("逻辑审计官", f"基于物理常识修正推演。")

            path_code = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":f"基于{facts}生成连锁反应链条"}]).choices[0].message.content
            status.update(label="✅ 仿真完成", state="complete")

        # --- 渲染视图 (完全保留你的原有布局) ---
        
        # 指标趋势
        st.markdown("### 📈 社会风险趋势预测")
        fig = go.Figure()
        names = ['管控压力', '民众焦虑度', '资源匮乏率', '社会秩序风险']
        steps = ['T0', 'T24', 'T72', 'T7d']
        for i in range(4):
            y = [time_data.get(s, [50]*4)[i] for s in steps]
            fig.add_trace(go.Scatter(x=['当前','24h','72h','7d'], y=y, name=names[i], line=dict(width=6)))
        st.plotly_chart(fig, use_container_width=True)

        # 连锁反应
        st.markdown("### 🔗 连锁反应路径")
        st.markdown(f"<div class='logic-box'>{path_code.replace('->', ' ➔ ')}</div>", unsafe_allow_html=True)

        # 核心对策
        st.markdown("### 💡 核心对策推荐")
        strat = client.chat.completions.create(model=model_choice, messages=[{"role":"system","content":logic_guard},{"role":"user","content":"给出3条硬核对策。"}]).choices[0].message.content
        st.info(strat)

        # 四角色博弈 (恢复并排展示)
        st.divider()
        st.markdown("### 🔄 智能体多维博弈回溯")
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f"<div class='role-card role-official'><b>🏛️ 官方决策</b><br><br>{off}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='role-card role-citizen'><b>⚠️ 民众反应</b><br><br>{cit}</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='role-card role-media'><b>📢 舆论态势</b><br><br>{med}</div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='role-card role-risk'><b>🛡️ 逻辑审计</b><br><br>{rsk}</div>", unsafe_allow_html=True)

        # 研判报告 (恢复巨幕卡片)
        st.divider()
        report_p = f"基于实证{facts}为{event_input}撰写深度研判报告。"
        final_report = client.chat.completions.create(model=model_choice, messages=[{"role":"system","content":"专家"},{"role":"user","content":report_p}]).choices[0].message.content
        st.markdown(f"<div class='report-card'><h2>📝 全维度深度综合研判报告 (实证驱动)</h2><br>{final_report}</div>", unsafe_allow_html=True)

else:
    st.info("💡 请在侧边栏配置参数并输入目标启动仿真。")
