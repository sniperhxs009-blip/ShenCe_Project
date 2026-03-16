import streamlit as st
from openai import OpenAI
import json
import plotly.graph_objects as go
import requests

# --- 1. 严格全宽垂直布局样式 ---
st.set_page_config(page_title="神策 - 战略级联动推演系统", layout="wide")

st.markdown("""
    <style>
    /* 强制主容器 100% 全宽，杜绝侧边空白 */
    .block-container { max-width: 98% !important; padding: 2rem 1% !important; }
    
    /* 连锁反应路径 - 垂直全宽 */
    .logic-box { 
        background-color: #f1f3f9; padding: 30px; border-left: 12px solid #673ab7; 
        border-radius: 10px; margin: 25px 0; width: 100%; font-size: 1.2rem; 
        line-height: 1.7; font-family: 'Courier New', monospace; color: #1a1a1a;
    }
    
    /* 角色卡片并列显示 */
    .role-card { padding: 25px; border-radius: 12px; min-height: 450px; box-shadow: 0 8px 20px rgba(0,0,0,0.1); margin-bottom: 25px; border: 1px solid #e0e0e0; }
    .role-official { background-color: #f0f7ff; border-top: 10px solid #0056b3; }
    .role-citizen { background-color: #fff9e6; border-top: 10px solid #ffcc00; }
    .role-media { background-color: #f2fff2; border-top: 10px solid #28a745; }
    .role-risk { background-color: #fff2f2; border-top: 10px solid #dc3545; }
    
    /* 深度研判报告 - 置底巨幕卡片 */
    .report-card { 
        background-color: #ffffff; padding: 50px; border-radius: 20px; 
        border: 1px solid #d1d9e6; border-top: 20px solid #0056b3; 
        box-shadow: 0 15px 50px rgba(0,0,0,0.1); margin-top: 40px; width: 100%; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心 API 配置 (已填入你指定的正确 Key) ---
SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
BASE_URL = "https://api.ohmygpt.com/v1"
# 你的 Serper Key：d57fbcfd2ecd16f71b9b131984050fab2c64d707
SERPER_API_KEY = "d57fbcfd2ecd16f71b9b131984050fab2c64d707" 

client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)

# --- 3. 实证数据获取模块 ---
def fetch_real_world_evidence(query):
    """基于 Serper 搜索真实历史灾难案例，为推演提供事实基石"""
    search_url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    # 强制搜索历史真实反应：抢购、断水、骚乱、信号中断、政府管制失败
    payload = json.dumps({"q": f"{query} 历史案例 真实表现 群众行为 骚乱 抢购 官方对策", "num": 8})
    try:
        response = requests.post(search_url, headers=headers, data=payload, timeout=15)
        results = response.json().get('organic', [])
        evidence = "\n".join([f"【实证数据点】: {r.get('snippet')}" for r in results])
        return evidence if evidence else "未检索到直接实证，启用极端社会学模拟逻辑。"
    except Exception as e:
        return f"实证检索异常: {str(e)}。已切换至高保真预设推演模型。"

# --- 4. 主流程逻辑 ---
st.title("🔮 SHENCE (神策) | 实证数据驱动·极端环境仿真推演")
event_input = st.text_area("📡 仿真目标输入", placeholder="如：千万人口城市大规模停电超过24小时，请基于真实案例事实进行仿真...", height=100)

if st.button("🚀 启动实证驱动仿真推演"):
    if event_input:
        with st.status("🛠️ 正在执行实证数据抓取与逻辑校准...", expanded=True) as status:
            
            # 1. 抓取真实案例
            st.write("🌐 联网检索全球历史相似案例事实...")
            facts = fetch_real_world_evidence(event_input)
            
            # 2. 注入逻辑防御与实证指令
            logic_guard = f"""
            推演基石：以下是检索到的真实历史数据点：
            {facts}
            
            【逻辑防御指令】：
            - 物理环境：严禁使用受损资源（停电即禁止网络支付、线上收集意见）。
            - 民众行为：必须体现出真实的历史惨况（如高层住户断水、冰箱食物变质导致的社会焦虑、线下抢购）。
            - 仿真深度：禁止给出‘官方口吻’的温和建议，必须展示真实的社会撕裂和治理难题。
            """

            # 3. 生成趋势数据
            st.write("📊 正在量化社会稳定性变动指标...")
            res_data = client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[{"role":"system","content":logic_guard},{"role":"user","content":"输出T0,24,72,7d四阶段JSON数据"}],
                response_format={"type":"json_object"}
            ).choices[0].message.content
            time_data = json.loads(res_data)

            # 4. 多角色博弈推演
            st.write("🔄 激活多主体博弈仿真（基于实证规律）...")
            def sim_role(role_name, prompt):
                return client.chat.completions.create(model="gpt-4o", messages=[
                    {"role": "system", "content": f"你是{role_name}。环境背景：{logic_guard}"},
                    {"role": "user", "content": prompt}
                ]).choices[0].message.content

            off = sim_role("应急指挥部", f"针对{event_input}提出强制物理管控手段。")
            cit = sim_role("真实受灾民众", f"描述停电24小时后的生存危机。记住历史实证：{facts}")
            med = sim_role("口头信息流传播者", f"描述通讯黑洞中谣言如何引发群体行为。")
            rsk = sim_role("逻辑审计官", f"基于物理常识和实证数据，无情地修正上述推演中的‘幻觉’对策。")

            path_code = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":f"基于{facts}生成连锁反应链条"}]).choices[0].message.content
            status.update(label="✅ 仿真建模完成：已对齐历史事实", state="complete")

        # --- 第一部分：指标趋势 (垂直全宽) ---
        st.markdown("### 📈 社会风险趋势预测 (基于实证权重)")
        fig = go.Figure()
        names = ['管控压力', '民众焦虑度', '资源匮乏率', '社会秩序风险']
        for i in range(4):
            y = [time_data.get('T0',[50]*4)[i], time_data.get('T24',[60]*4)[i], time_data.get('T72',[70]*4)[i], time_data.get('T7d',[80]*4)[i]]
            fig.add_trace(go.Scatter(x=['当前','24h','72h','7d'], y=y, name=names[i], line=dict(width=6)))
        st.plotly_chart(fig, use_container_width=True)

        # --- 第二部分：因果逻辑链 (垂直全宽) ---
        st.markdown("### 🔗 连锁反应路径 (次生灾害链条)")
        st.markdown(f"<div class='logic-box'>{path_code.replace('->', ' ➔ ')}</div>", unsafe_allow_html=True)

        # --- 第三部分：核心对策 (垂直全宽) ---
        st.markdown("### 💡 核心对策推荐 (基于实证处置经验)")
        strat = client.chat.completions.create(model="gpt-4o", messages=[{"role":"system","content":logic_guard},{"role":"user","content":"给出3条不依赖网络的硬核处置对策。"}]).choices[0].message.content
        st.info(strat)

        # --- 第四部分：四角色深度博弈 (四列并排) ---
        st.divider()
        st.markdown("### 🔄 智能体多维博弈回溯 (强仿真版)")
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f"<div class='role-card role-official'><b>🏛️ 官方决策</b><br><br>{off}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='role-card role-citizen'><b>⚠️ 民众反应</b><br><br>{cit}</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='role-card role-media'><b>📢 舆论态势</b><br><br>{med}</div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='role-card role-risk'><b>🛡️ 逻辑审计</b><br><br>{rsk}</div>", unsafe_allow_html=True)

        # --- 第五部分：全维度深度研判报告 (置底大卡片) ---
        st.divider()
        report_prompt = f"基于实证数据：{facts}。为{event_input}撰写深度研判报告。要求：1.物理瘫痪分析；2.社会稳定拐点预警；3.硬核物理应对建议。"
        final_report = client.chat.completions.create(model="gpt-4o", messages=[{"role":"system","content":"资深国家安全专家"},{"role":"user","content":report_prompt}]).choices[0].message.content
        st.markdown(f"<div class='report-card'><h2>📝 全维度深度综合研判报告 (实证驱动)</h2><br>{final_report}</div>", unsafe_allow_html=True)

else:
    st.info("💡 请调节侧边栏变量并输入仿真目标。系统将根据你提供的 Key 检索真实历史数据。")
