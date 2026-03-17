import streamlit as st
from openai import OpenAI
import json
import plotly.graph_objects as go
import requests
import pandas as pd

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
    .stProgress > div > div > div > div { background-color: #673ab7; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 侧边栏：强化架构与黑天鹅控制 ---
with st.sidebar:
    st.title("⚙️ MiroFish 级引擎架构")
    
    st.markdown("### 🤖 核心模型分工")
    st.info("**GPT-4o (战略大脑)**: 负责高维度博弈与 PESTEL 深度研判。")
    st.info("**GPT-4o-Mini (演化大脑)**: 驱动数值矩阵波动与连锁反应生成。")
    st.info("**Serper.dev (实证事实库)**: 检索真实案例与链接。")

    st.divider()
    st.subheader("📊 社会系统初始矩阵")
    c1, c2 = st.columns(2)
    with c1:
        init_eff = st.slider("政府效能", 0, 100, 80)
        init_panic = st.slider("社会焦虑", 0, 100, 20)
    with c2:
        init_res = st.slider("资源储备", 0, 100, 95)
        init_risk = st.slider("初始风险", 0, 100, 10)
    
    st.divider()
    st.subheader("🔥 极端变量控制")
    black_swan = st.toggle("允许产生“黑天鹅”扰动事件", value=True)
    depth_level = st.select_slider("推演演化深度", options=["浅层观察", "中度模拟", "深度沙盘", "极端生存"], value="深度沙盘")
    temp_val = st.slider("思维发散率", 0.0, 1.0, 0.7)

# --- 3. 核心 API 配置 ---
SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
BASE_URL = "https://api.ohmygpt.com/v1"
SERPER_API_KEY = "d57fbcfd2ecd16f71b9b131984050fab2c64d707" 
client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)

def fetch_detailed_evidence(query):
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = json.dumps({"q": f"{query} 历史灾难 真实社会反应 处置教训 案例", "num": 5})
    try:
        res = requests.post(url, headers=headers, data=payload, timeout=15)
        return res.json().get('organic', [])
    except: return []

# --- 4. 增强推演逻辑 ---
st.title("🛡️ SHENCE (神策) | 极端环境深度演化仿真沙盘")
event_input = st.text_area("📡 仿真目标输入", placeholder="描述极端事件背景...", height=100)

if st.button("🚀 启动全维度深度演化推演"):
    if event_input:
        with st.status("🛠️ 正在构建复杂系统动态模型...", expanded=True) as status:
            # 1. 联网实证检索
            st.write("🌐 检索全球历史相似案例...")
            raw_evidence = fetch_detailed_evidence(event_input)
            facts_text = "\n".join([f"{e.get('snippet')}" for e in raw_evidence])
            
            # 2. 注入动态博弈背景
            lg = f"""
            实证基础：{facts_text}
            初始矩阵：行政{init_eff}, 焦虑{init_panic}, 资源{init_res}, 风险{init_risk}
            推演模式：{depth_level} | 黑天鹅事件：{'启用' if black_swan else '禁用'}
            """
            
            # 3. 增强数值矩阵演化 (GPT-4o-Mini)
            st.write("📊 模拟四维度指标演化环...")
            trend_prompt = f"基于背景，输出T0, T24, T48, T72, T7d五个阶段的指标动态，要求数据体现资源衰竭对焦虑的正向反馈。JSON格式。"
            try:
                res = client.chat.completions.create(
                    model="gpt-4o-mini", 
                    messages=[{"role":"system","content":lg},{"role":"user","content":trend_prompt}],
                    response_format={"type":"json_object"}
                ).choices[0].message.content
                time_data = json.loads(res)
            except:
                time_data = {"T0":[50]*4, "T24":[60]*4, "T48":[65]*4, "T72":[75]*4, "T7d":[85]*4}

            # 4. PESTEL 深度研判 (GPT-4o)
            st.write("🔄 启动 PESTEL 多维博弈推演...")
            def sim(role, p):
                return client.chat.completions.create(model="gpt-4o", messages=[{"role":"system","content":f"你是{role}。{lg}"},{"role":"user","content":p}], temperature=temp_val).choices[0].message.content
            
            off = sim("应急指挥部", "制定基于当前资源缺口的物理管控策略。")
            cit = sim("极端受灾个体", "描述生存物资断绝后的心理演变规律。")
            med = sim("信息流向官", "分析去中心化环境下的谣言传播动力学。")
            rsk = sim("逻辑审计官", "识别模型幻觉，预测可能的黑天鹅扰动点。")
            
            path = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":f"生成该事件的复杂连锁灾难链条"}]).choices[0].message.content
            status.update(label="✅ 仿真演化完成", state="complete")

        # --- 渲染视图 ---

        # A. 历史案例实证
        st.markdown("### 📚 历史相似案例实证 (Evidence Benchmarking)")
        if raw_evidence:
            e_cols = st.columns(len(raw_evidence))
            for idx, item in enumerate(raw_evidence):
                with e_cols[idx]:
                    st.markdown(f"""
                    <div class="evidence-card">
                        <strong>{item.get('title')[:25]}...</strong><br>
                        <p style="font-size: 0.85rem; color: #555; margin-top:8px;">{item.get('snippet')[:100]}...</p>
                        <a href="{item.get('link')}" target="_blank" class="evidence-link">查看源档案 →</a>
                    </div>
                    """, unsafe_allow_html=True)

        # B. 动态演化矩阵
        st.divider()
        st.markdown("### 📈 社会系统多维演化矩阵 (Matrix Evolution)")
        fig = go.Figure()
        names = ['行政效能', '社会焦虑', '资源储备', '动荡风险']
        steps = list(time_data.keys())
        for i in range(4):
            y_vals = [time_data.get(s, [50]*4)[i] for s in steps]
            fig.add_trace(go.Scatter(x=steps, y=y_vals, name=names[i], line=dict(width=6), mode='lines+markers'))
        fig.update_layout(height=450, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # C. 连锁反应路径
        st.markdown("### 🔗 复杂因果逻辑链条 (Causal Chain)")
        st.markdown(f"<div class='logic-box'>{path.replace('->', ' ➔ ')}</div>", unsafe_allow_html=True)

        # D. 智能体多维博弈
        st.divider()
        st.markdown("### 🔄 核心智能体动态决策博弈")
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f"<div class='role-card role-official'><b>🏛️ 指挥节点</b><br><br>{off}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='role-card role-citizen'><b>⚠️ 社会节点</b><br><br>{cit}</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='role-card role-media'><b>📢 传播节点</b><br><br>{med}</div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='role-card role-risk'><b>🛡️ 审计节点</b><br><br>{rsk}</div>", unsafe_allow_html=True)

        # E. PESTEL 深度研判报告
        st.divider()
        report_p = f"基于博弈事实，按照 PESTEL 模型（政治、经济、社会、技术、环境、法律）为该事件生成万字级深度研判报告。强调生存平衡点与系统崩溃临界值。"
        final_report = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":report_p}]).choices[0].message.content
        st.markdown(f"<div class='report-card'><h2>📝 PESTEL 全维度战略研判报告</h2><br>{final_report}</div>", unsafe_allow_html=True)
        
        # F. 导出功能
        st.download_button("📂 下载完整推演档案 (Markdown)", data=f"# 神策仿真报告\n\n## 初始事件\n{event_input}\n\n## 研判报告\n{final_report}", file_name="shence_report.md")

else:
    st.info("💡 请在左侧配置仿真参数并输入推演目标。系统将调用多脑协同引擎进行全维度计算。")
