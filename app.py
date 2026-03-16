import streamlit as st
from openai import OpenAI
import json
import plotly.graph_objects as go
import requests
import random

# --- 1. 界面与样式配置 (暗黑/专业推演风格) ---
st.set_page_config(page_title="SHENCE - 复杂社会演化仿真引擎", layout="wide")
st.markdown("""
    <style>
    .block-container { max-width: 98% !important; padding: 1rem 2% !important; background-color: #0e1117; }
    .stMarkdown, p, h3, h2, h1 { color: #e0e0e0 !important; }
    .metric-card { 
        background-color: #161b22; padding: 20px; border-radius: 10px; 
        border: 1px solid #30363d; text-align: center;
    }
    .logic-box { 
        background-color: #0d1117; padding: 25px; border-left: 10px solid #58a6ff; 
        border-radius: 6px; margin: 20px 0; font-family: 'Consolas', monospace; 
        color: #8b949e; border: 1px solid #30363d;
    }
    .role-box { padding: 20px; border-radius: 10px; min-height: 400px; border: 1px solid #30363d; background: #161b22; margin-bottom: 20px; }
    .report-card { 
        background-color: #ffffff; padding: 40px; border-radius: 15px; color: #1a1a1a !important;
        border-top: 15px solid #1f6feb; box-shadow: 0 10px 40px rgba(0,0,0,0.5); width: 100%; 
    }
    .report-card * { color: #1a1a1a !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API 核心配置 ---
SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
BASE_URL = "https://api.ohmygpt.com/v1"
SERPER_API_KEY = "d57fbcfd2ecd16f71b9b131984050fab2c64d707" 
client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)

# --- 3. 核心功能函数 ---

def get_real_evidence(query):
    """【功能1：案例事实搜寻】"""
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = json.dumps({"q": f"{query} 历史案例 真实社会表现 PESTEL 供应链断裂 群众行为", "num": 8})
    try:
        res = requests.post(url, headers=headers, data=payload, timeout=10)
        return "\n".join([r.get('snippet') for r in res.json().get('organic', [])])
    except: return "检索失败，使用系统内置仿真模型。"

def run_step_evolution(facts, current_state, step_name):
    """【功能2：时空增量演化引擎】"""
    prompt = f"""
    环境事实：{facts}
    当前社会状态矩阵：{current_state}
    推演阶段：{step_name}
    请根据博弈演化逻辑，输出该阶段官方、民众、媒体的详细行为表现。要求：
    1. 严禁断电场景下的网络操作。
    2. 必须体现马斯洛生存需求导致的冲突。
    3. 输出格式为 JSON，包含'official', 'citizen', 'media', 'audit' 四个字段。
    """
    res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"}).choices[0].message.content
    return json.loads(res)

# --- 4. 主程序运行 ---
st.title("🛡️ SHENCE (神策) | MiroFish 级社会系统仿真")
event_input = st.text_area("📡 输入初始扰动事件", placeholder="输入事件，如：大城市断电断水48小时...", height=80)

if st.button("🚀 启动深度演化仿真"):
    if event_input:
        with st.status("🛠️ 正在初始化仿真矩阵并检索历史实证...", expanded=True) as status:
            
            # 第一步：获取事实
            st.write("🌐 联网检索 PESTEL 维度历史案例...")
            facts = get_real_evidence(event_input)
            
            # 第二步：【功能3：数值化社会矩阵】初始化
            st.write("📊 正在根据实证计算社会属性矩阵...")
            init_p = f"基于{facts}，为事件{event_input}初始化四维指标(0-100)：行政效能、焦虑指数、资源缺口、动荡风险。返回JSON。"
            matrix_res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":init_p}], response_format={"type":"json_object"}).choices[0].message.content
            matrix = json.loads(matrix_res)

            # 第三步：运行演化循环
            st.write("🔄 正在运行 T+24H 复杂博弈演化...")
            evo_data = run_step_evolution(facts, matrix, "爆发与初级震荡期")
            
            # 第四步：【功能4：随机扰动 (黑天鹅) 生成】
            st.write("🦢 正在计算环境随机扰动变量...")
            swan_p = f"在{event_input}背景下，产生一个极低概率但高破坏性的随机扰动事件（如备用电源起火、水源二次污染）。"
            black_swan = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":swan_p}]).choices[0].message.content

            status.update(label="✅ 仿真演化完毕", state="complete")

        # --- 第一部分：数值仪表盘 ---
        st.markdown("### 📊 社会属性矩阵演化 (Matrix State)")
        m_cols = st.columns(4)
        m_cols[0].markdown(f"<div class='metric-card'>🏛️ 行政效能<br><h2>{matrix.get('行政效能', 60)}%</h2></div>", unsafe_allow_html=True)
        m_cols[1].markdown(f"<div class='metric-card'>⚠️ 焦虑指数<br><h2>{matrix.get('焦虑指数', 40)}%</h2></div>", unsafe_allow_html=True)
        m_cols[2].markdown(f"<div class='metric-card'>📦 资源缺口<br><h2>{matrix.get('资源缺口', 30)}%</h2></div>", unsafe_allow_html=True)
        m_cols[3].markdown(f"<div class='metric-card'>🔥 动荡风险<br><h2>{matrix.get('动荡风险', 20)}%</h2></div>", unsafe_allow_html=True)

        # --- 第二部分：深度因果链与雷达图 ---
        st.divider()
        st.markdown("### 🔗 PESTEL 维度深度因果演化 (Causal Loop)")
        # 强制 AI 生成因果链
        causal = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":f"为{event_input}生成深度因果链"} ]).choices[0].message.content
        st.markdown(f"<div class='logic-box'>{causal}</div>", unsafe_allow_html=True)

        # --- 第三部分：四智能体博弈 (垂直排列，内容详细化) ---
        st.divider()
        st.markdown("### 🔄 智能体多维博弈回溯")
        
        # 官方
        with st.expander("🏛️ 官方决策演化", expanded=True):
            st.markdown(f"<div style='color:#58a6ff'>{evo_data.get('official', '推演中...')}</div>", unsafe_allow_html=True)
        # 民众
        with st.expander("⚠️ 民众生存反应", expanded=True):
            st.markdown(f"<div style='color:#d29922'>{evo_data.get('citizen', '推演中...')}</div>", unsafe_allow_html=True)
        # 风险审计与黑天鹅
        st.error(f"🚨 **突发随机扰动（黑天鹅事件）：** {black_swan}")
        st.warning(f"🛡️ **逻辑审计结论：** {evo_data.get('audit', '推演中...')}")

        # --- 第四部分：深度研判报告 (MiroFish 核心产出) ---
        st.divider()
        with st.spinner("🔍 正在整合实证与演化数据生成终期研判..."):
            report_p = f"结合事实{facts}、演化{evo_data}及随机扰动{black_swan}，撰写深度研判报告。要求：1.物理瘫痪分析；2.社会临界点预警；3.战略对冲建议。"
            report = client.chat.completions.create(model="gpt-4o", messages=[{"role":"system","content":"国家安全顾问"},{"role":"user","content":report_p}]).choices[0].message.content
        
        st.markdown(f"<div class='report-card'><h2>📝 全维度战略研判综合报告</h2><br>{report}</div>", unsafe_allow_html=True)
        st.download_button("📥 导出仿真完整数据集", report)

else:
    st.info("💡 系统已注入 Serper Key。请输入事件启动仿真。")
