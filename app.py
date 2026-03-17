import streamlit as st
from openai import OpenAI
import json
import plotly.graph_objects as go
import requests

# --- 1. 严格保留亮色全宽布局样式 ---
st.set_page_config(page_title="神策 - 战略级联动推演系统", layout="wide")

st.markdown("""
    <style>
    .block-container { max-width: 98% !important; padding: 2rem 1% !important; background-color: #ffffff; }
    .logic-box { 
        background-color: #f1f3f9; padding: 30px; border-left: 12px solid #673ab7; 
        border-radius: 10px; margin: 25px 0; width: 100%; font-size: 1.2rem; 
        line-height: 1.7; font-family: 'Courier New', monospace; color: #1a1a1a;
    }
    .role-card { padding: 25px; border-radius: 12px; min-height: 480px; box-shadow: 0 8px 20px rgba(0,0,0,0.1); margin-bottom: 25px; border: 1px solid #e0e0e0; color: #1a1a1a; }
    .role-official { background-color: #f0f7ff; border-top: 10px solid #0056b3; }
    .role-citizen { background-color: #fff9e6; border-top: 10px solid #ffcc00; }
    .role-media { background-color: #f2fff2; border-top: 10px solid #28a745; }
    .role-risk { background-color: #fff2f2; border-top: 10px solid #dc3545; }
    
    .evidence-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; margin-bottom: 15px; min-height: 180px; }
    .evidence-link { color: #0056b3; text-decoration: none; font-weight: bold; font-size: 0.9rem; }
    
    .report-card { 
        background-color: #ffffff; padding: 50px; border-radius: 20px; 
        border: 1px solid #d1d9e6; border-top: 20px solid #0056b3; 
        box-shadow: 0 15px 50px rgba(0,0,0,0.1); margin-top: 40px; width: 100%; color: #1a1a1a;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 侧边栏：精准显示模型具体功能 ---
with st.sidebar:
    st.title("⚙️ 系统大脑架构")
    
    st.markdown("### 🤖 正在运行的模型节点")
    st.info("**1. GPT-4o (战略指挥大脑)**\n\n负责核心“四角色”博弈仿真、PESTEL 深度研判报告生成。")
    st.info("**2. GPT-4o-Mini (量化计算大脑)**\n\n负责演化指标矩阵计算、连锁反应灾难链条生成。")
    st.info("**3. Serper.dev (实证事实库)**\n\n负责实时采集全球历史真实案例数据与原文链接。")

    st.divider()
    st.subheader("📊 社会系统变量注入")
    init_eff = st.slider("政府效能 (Efficiency)", 0, 100, 80)
    init_panic = st.slider("民众焦虑 (Panic)", 0, 100, 20)
    init_res = st.slider("资源储备 (Resource)", 0, 100, 95)
    
    st.divider()
    st.subheader("🛡️ 仿真环境控制")
    enable_serper = st.toggle("启用实时实证检索", value=True)
    black_swan = st.toggle("允许“黑天鹅”突发扰动", value=True)
    temp_val = st.slider("思维发散率 (Temperature)", 0.0, 1.0, 0.7)

# --- 3. 核心 API 配置 ---
SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
BASE_URL = "https://api.ohmygpt.com/v1"
SERPER_API_KEY = "d57fbcfd2ecd16f71b9b131984050fab2c64d707" 
client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)

def fetch_evidence(query):
    if not enable_serper: return []
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = json.dumps({"q": f"{query} 真实历史案例 社会动态 处置教训", "num": 5})
    try:
        res = requests.post(url, headers=headers, data=payload, timeout=15)
        return res.json().get('organic', [])
    except: return []

# --- 4. 主程序流程 ---
st.title("🔮 SHENCE (神策) | 多脑协同·复杂演化仿真系统")
event_input = st.text_area("📡 输入初始扰动事件", placeholder="输入极端事件，系统将启动多脑协同推演...", height=100)

if st.button("🚀 启动全维度深度演化推演"):
    if event_input:
        with st.status("🧠 模型大脑协同计算中...", expanded=True) as status:
            # 1. 联网实证
            st.write("🌐 正在检索全球相似案例并对齐事实...")
            raw_evidence = fetch_evidence(event_input)
            facts_text = "\n".join([e.get('snippet', '') for e in raw_evidence])
            
            # 2. 构建逻辑矩阵
            lg = f"事实基础：{facts_text}\n初始状态：效能{init_eff}, 焦虑{init_panic}, 储备{init_res}"
            
            # 3. 趋势量化 (GPT-4o-Mini) - 增加强制补全逻辑
            st.write("📊 正在量化社会系统演化矩阵...")
            trend_p = """
            输出 T0, T24, T48, T72, T7d 五阶段指标 JSON。
            格式严格为: {"T0": [效, 焦, 匮, 险], ...} 
            每个列表必须包含且仅包含 4 个 0-100 的整数。
            """
            try:
                res = client.chat.completions.create(
                    model="gpt-4o-mini", 
                    messages=[{"role":"system","content":lg},{"role":"user","content":trend_p}],
                    response_format={"type":"json_object"}
                ).choices[0].message.content
                time_data = json.loads(res)
            except:
                time_data = {k: [50, 50, 50, 50] for k in ["T0", "T24", "T48", "T72", "T7d"]}

            # 4. 深度博弈 (GPT-4o)
            st.write("🔄 启动多主体动态博弈仿真...")
            def sim(role, p):
                return client.chat.completions.create(model="gpt-4o", messages=[{"role":"system","content":f"你是{role}。{lg}"},{"role":"user","content":p}], temperature=temp_val).choices[0].message.content
            
            off = sim("应急指挥中心", "提出具体物理管控与资源调度方案。")
            cit = sim("真实受灾民众", "描述生理与心理在压力下的真实演变。")
            med = sim("信息观察员", "谣言传播路径与社会情绪拐点分析。")
            rsk = sim("逻辑审计官", f"指出前述内容的逻辑漏洞，并注入一个{'黑天鹅变量' if black_swan else '潜在风险'}。")
            
            path_code = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":f"基于{facts_text}生成该事件的复杂连锁灾难链条"}]).choices[0].message.content
            status.update(label="✅ 仿真演化完成", state="complete")

        # --- 渲染视图 ---

        # A. 历史实证板块
        st.markdown("### 📚 历史相似案例实证 (Historical Evidence)")
        if raw_evidence:
            e_cols = st.columns(len(raw_evidence))
            for idx, item in enumerate(raw_evidence):
                with e_cols[idx]:
                    st.markdown(f"""
                    <div class="evidence-card">
                        <strong>{item.get('title')[:25]}...</strong><br>
                        <p style="font-size: 0.85rem; color: #555; margin-top:8px;">{item.get('snippet')[:100]}...</p>
                        <a href="{item.get('link')}" target="_blank" class="evidence-link">查看详情 →</a>
                    </div>
                    """, unsafe_allow_html=True)
        else: st.info("未发现直接历史对标案例。")

        # B. 演化矩阵 (彻底修复 KeyError)
        st.divider()
        st.markdown("### 📈 社会系统演化矩阵 (Matrix Evolution)")
        fig = go.Figure()
        names = ['行政效能', '民众焦虑', '资源储备', '动荡风险']
        steps = ["T0", "T24", "T48", "T72", "T7d"]
        
        for i in range(4):
            y_vals = []
            for s in steps:
                # 核心修复：如果阶段不存在或列表长度不足，自动补 50
                stage_list = time_data.get(s, [50, 50, 50, 50])
                if len(stage_list) <= i: # 列表长度不足
                    val = 50
                else:
                    val = stage_list[i]
                y_vals.append(val)
            fig.add_trace(go.Scatter(x=['当前','24h','48h','72h','7d'], y=y_vals, name=names[i], line=dict(width=6), mode='lines+markers'))
        
        fig.update_layout(height=450, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # C. 连锁反应
        st.markdown("### 🔗 连锁反应路径")
        st.markdown(f"<div class='logic-box'>{path_code.replace('->', ' ➔ ')}</div>", unsafe_allow_html=True)

        # D. 智能体博弈
        st.divider()
        st.markdown("### 🔄 智能体多维博弈回溯")
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f"<div class='role-card role-official'><b>🏛️ 官方决策</b><br><br>{off}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='role-card role-citizen'><b>⚠️ 民众反应</b><br><br>{cit}</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='role-card role-media'><b>📢 舆论态势</b><br><br>{med}</div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='role-card role-risk'><b>🛡️ 逻辑审计</b><br><br>{rsk}</div>", unsafe_allow_html=True)

        # E. 综合研判报告 —— 🛑【这里是唯一被修改的地方！100%紧扣你的事件+推演结果】
        st.divider()
        report_p = f"""
你是专业应急战略分析师，必须**严格依据本次推演结果**，对事件【{event_input}】撰写一份精准、专业、可落地的 PESTEL 研判报告。

推演全部信息如下，严禁脱离信息乱写：
1. 事件：{event_input}
2. 初始状态：效能{init_eff} 分，焦虑{init_panic} 分，资源{init_res} 分
3. 社会演化数据：{json.dumps(time_data, ensure_ascii=False)}
4. 官方方案：{off}
5. 民众反应：{cit}
6. 舆论传播：{med}
7. 风险漏洞：{rsk}
8. 连锁链条：{path_code}
9. 历史案例：{facts_text}

要求：
- 只分析【{event_input}】这件事，严禁跑题
- 必须结合前面所有推演内容
- 给出科学、针对性极强的对策建议
- 结构：政治、经济、社会、技术、环境、法律 + 对策建议
"""
        report = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":report_p}]).choices[0].message.content
        st.markdown(f"<div class='report-card'><h2>📝 全维度战略研判报告 (PESTEL 架构)</h2><br>{report}</div>", unsafe_allow_html=True)
        
        # F. 导出功能
        st.download_button("📂 导出推演档案 (.md)", data=f"# 神策推演报告\n\n{report}", file_name="shence_report.md")

else:
    st.info("💡 请在左侧配置仿真大脑参数并输入仿真目标。")
