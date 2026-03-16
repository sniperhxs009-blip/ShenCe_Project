import streamlit as st
from openai import OpenAI
import json
import plotly.graph_objects as go
import requests
import pandas as pd

# --- 1. 样式配置 ---
st.set_page_config(page_title="神策 - 战略级联动推演系统", layout="wide")
st.markdown("""
    <style>
    .block-container { max-width: 98% !important; padding: 1.5rem 1% !important; background-color: #0b0e14; }
    .stMarkdown, p, h3, h2, h1 { color: #c9d1d9 !important; }
    .logic-box { background-color: #161b22; padding: 25px; border-left: 10px solid #673ab7; border-radius: 8px; margin: 20px 0; color: #8b949e; }
    .role-card { padding: 20px; border-radius: 12px; min-height: 450px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-bottom: 20px; border: 1px solid #30363d; background: #1c2128; }
    .report-card { background-color: #ffffff; padding: 40px; border-radius: 15px; color: #1a1a1a !important; border-top: 15px solid #0056b3; width: 100%; }
    .report-card * { color: #1a1a1a !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 推演控制中心")
    model_choice = st.selectbox("选择仿真大脑", ["gpt-4o", "gpt-4o-mini"], index=0)
    temperature = st.slider("推演随机性", 0.0, 1.0, 0.7)
    st.divider()
    st.subheader("📊 社会系统初始状态")
    init_eff = st.slider("初始行政效能", 0, 100, 80)
    init_panic = st.slider("初始民众焦虑", 0, 100, 30)
    init_res = st.slider("初始资源储备", 0, 100, 90)
    st.divider()
    enable_serper = st.toggle("开启实时实证 (Serper)", value=True)

# --- 3. 核心 API 配置 ---
SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
BASE_URL = "https://api.ohmygpt.com/v1"
SERPER_API_KEY = "d57fbcfd2ecd16f71b9b131984050fab2c64d707" 
client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)

def fetch_evidence(query):
    if not enable_serper: return "未开启联网实证。"
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = json.dumps({"q": f"{query} 历史案例 真实表现 处置教训", "num": 8})
    try:
        res = requests.post(url, headers=headers, data=payload, timeout=15)
        return "\n".join([f"• {r.get('snippet')}" for r in res.json().get('organic', [])])
    except: return "搜索失败，启用预设模型。"

# --- 4. 主流程 ---
st.title("🔮 SHENCE (神策) | MiroFish 级深度仿真")
event_input = st.text_area("📡 仿真目标输入", placeholder="描述极端事件...", height=100)

if st.button("🚀 启动全维度深度推演"):
    if event_input:
        with st.status("🛠️ 正在进行复杂系统建模...", expanded=True) as status:
            # 1. 获取实证
            facts = fetch_evidence(event_input)
            lg = f"事实：{facts}\n状态：效能{init_eff}, 焦虑{init_panic}, 储备{init_res}"
            
            # 2. 生成趋势数据 (修正后的逻辑)
            st.write("📊 正在量化社会稳定性指标...")
            trend_prompt = """
            请为该事件输出四个阶段(T0, T24, T72, T7d)的社会指标数据。
            必须严格返回如下JSON格式，不要有任何解释：
            {"T0": [80, 20, 90, 10], "T24": [60, 50, 40, 40], "T72": [40, 80, 20, 70], "T7d": [20, 95, 5, 90]}
            列表内四个数字依次代表：[行政效能, 民众焦虑, 资源储备, 动荡风险]
            """
            try:
                res = client.chat.completions.create(
                    model="gpt-4o-mini", 
                    messages=[{"role":"system","content":lg},{"role":"user","content":trend_prompt}],
                    response_format={"type":"json_object"}
                )
                time_data = json.loads(res.choices[0].message.content)
            except:
                time_data = {"T0":[50]*4, "T24":[50]*4, "T72":[50]*4, "T7d":[50]*4} # 容错垫底数据

            # 3. 多角色博弈
            st.write("🔄 激活多主体博弈仿真...")
            def sim(role, p):
                return client.chat.completions.create(model=model_choice, messages=[{"role":"system","content":f"你是{role}。{lg}"},{"role":"user","content":p}]).choices[0].message.content

            off = sim("应急指挥部", "硬核管控手段")
            cit = sim("民众", "生存24小时真实反应")
            med = sim("传播者", "谣言扩散态势")
            rsk = sim("逻辑审计官", "指出推演幻觉")

            path = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":f"基于{facts}生成连锁反应链条"}]).choices[0].message.content
            status.update(label="✅ 仿真完成", state="complete")

        # --- 渲染视图 (修复 KeyError) ---
        st.markdown("### 📈 社会风险趋势预测")
        fig = go.Figure()
        names = ['行政效能', '民众焦虑', '资源储备', '动荡风险']
        steps = ['T0', 'T24', 'T72', 'T7d']
        
        for i in range(4):
            try:
                # 增强容错：如果某个键丢失，使用前一个阶段的值
                y_vals = []
                for s in steps:
                    val = time_data.get(s, [50, 50, 50, 50])[i]
                    y_vals.append(val)
                fig.add_trace(go.Scatter(x=['当前','24h','72h','7d'], y=y_vals, name=names[i], line=dict(width=4)))
            except: continue
        
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 🔗 连锁反应路径")
        st.markdown(f"<div class='logic-box'>{path}</div>", unsafe_allow_html=True)

        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f"<div class='role-card'><b>🏛️ 官方决策</b><br>{off}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='role-card'><b>⚠️ 民众反应</b><br>{cit}</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='role-card'><b>📢 舆论态势</b><br>{med}</div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='role-card'><b>🛡️ 逻辑审计</b><br>{rsk}</div>", unsafe_allow_html=True)

        st.divider()
        report = client.chat.completions.create(model=model_choice, messages=[{"role":"user","content":f"为{event_input}写深度报告"}]).choices[0].message.content
        st.markdown(f"<div class='report-card'><h2>📝 全维度综合研判报告</h2><br>{report}</div>", unsafe_allow_html=True)
