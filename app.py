import streamlit as st
from openai import OpenAI
import json
import plotly.graph_objects as go
import requests
import random

# --- 1. 样式与专业推演风格配置 ---
st.set_page_config(page_title="SHENCE - 复杂系统仿真沙盘", layout="wide")
st.markdown("""
    <style>
    .block-container { max-width: 98% !important; padding: 1rem 2% !important; background-color: #0b0e14; }
    .stMarkdown, p, h3, h2, h1 { color: #c9d1d9 !important; }
    
    /* MiroFish 风格数值仪表盘 */
    .metric-card { 
        background-color: #161b22; padding: 20px; border-radius: 12px; 
        border: 1px solid #30363d; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .metric-value { font-size: 2.2rem; font-weight: bold; margin: 10px 0; font-family: 'Courier New'; }
    
    /* 演化逻辑路径 */
    .logic-box { 
        background-color: #0d1117; padding: 25px; border-left: 8px solid #58a6ff; 
        border-radius: 8px; margin: 20px 0; font-family: 'Consolas', monospace; 
        color: #8b949e; border: 1px solid #30363d; line-height: 1.6;
    }
    
    /* 角色卡片 */
    .role-card { padding: 20px; border-radius: 12px; min-height: 450px; border: 1px solid #30363d; background: #161b22; margin-bottom: 20px; }
    
    /* 最终研判报告：政务黑白排版 */
    .report-card { 
        background-color: #ffffff; padding: 50px; border-radius: 15px; color: #1a1a1a !important;
        border-top: 15px solid #1f6feb; box-shadow: 0 20px 60px rgba(0,0,0,0.5); width: 100%; 
    }
    .report-card * { color: #1a1a1a !important; }
    .swan-alert { background-color: #3e1e1e; border: 2px solid #da3633; padding: 20px; border-radius: 10px; margin: 20px 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心 API 配置 ---
SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
BASE_URL = "https://api.ohmygpt.com/v1"
SERPER_API_KEY = "d57fbcfd2ecd16f71b9b131984050fab2c64d707" # 使用你提供的正确 Key

client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)

# --- 3. 仿真核心引擎 ---

def fetch_evidence(query):
    """【功能1：实证检索】"""
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = json.dumps({"q": f"{query} 历史案例 真实民众表现 处置失败教训 社会动荡", "num": 10})
    try:
        res = requests.post(url, headers=headers, data=payload, timeout=12)
        return "\n".join([r.get('snippet') for r in res.json().get('organic', [])])
    except: return "未获取到在线实证。"

def run_simulation_step(facts, matrix, step_id, event):
    """【功能2：多步增量演化逻辑】"""
    prompt = f"""
    事件：{event} | 推演阶段：{step_id}
    当前社会矩阵：{matrix} | 实证参考：{facts}
    请模拟该阶段下官方、民众、传播、风险四个维度的博弈演化：
    1. 官方：具体的行政管控决策。
    2. 民众：基于生存压力的真实反应（体现马斯洛底层冲突）。
    3. 传播：通讯受限下的信息流向。
    4. 风险：逻辑漏洞审计。
    返回 JSON 格式：{{'official': '', 'citizen': '', 'media': '', 'audit': ''}}
    """
    res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"}).choices[0].message.content
    return json.loads(res)

# --- 4. 主程序流程 ---
st.title("🛡️ SHENCE (神策) | 复杂系统仿真推演沙盘")
st.caption("内核版本：MiroFish-v3.2 | 仿真模式：数据实证 + 状态机演化")

event_input = st.text_area("📡 输入初始扰动事件", placeholder="如：超大城市遭遇大规模黑客攻击导致电力、水利全面瘫痪...", height=80)

if st.button("🚀 启动全维度深度仿真"):
    if not event_input:
        st.error("请输入事件内容！")
    else:
        with st.status("🛠️ 系统初始化：抓取实证并计算状态矩阵...", expanded=True) as status:
            # 1. 获取实证
            st.write("🌐 联网检索全球 PESTEL 维度事实...")
            facts = fetch_evidence(event_input)
            
            # 2. 初始化矩阵
            st.write("📊 计算初始社会属性矩阵...")
            init_p = f"基于{facts}，为{event_input}计算四个数值(0-100)：行政效能、焦虑指数、资源缺口、动荡风险。返回JSON。"
            matrix = json.loads(client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":init_p}], response_format={"type":"json_object"}).choices[0].message.content)

            # 3. 增量演化（核心博弈）
            st.write("🔄 正在运行 T+24H 演化循环...")
            evo_data = run_simulation_step(facts, matrix, "第一阶段：爆发与震荡期", event_input)
            
            # 4. 黑天鹅擾动
            st.write("🦢 正在注入随机扰动变量...")
            swan_p = f"在{event_input}背景下产生一个极低概率但致命的扰动。仅一句话。"
            black_swan = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":swan_p}]).choices[0].message.content

            status.update(label="✅ 仿真演化完毕", state="complete")

        # --- 第一部分：数值仪表盘 ---
        st.markdown("### 📊 当前系统属性矩阵 (Numerical Matrix)")
        m_cols = st.columns(4)
        for i, (k, v) in enumerate(matrix.items()):
            with m_cols[i]:
                color = "#58a6ff" if "效能" in k else "#da3633"
                st.markdown(f"<div class='metric-card'><div style='color:#8b949e'>{k}</div><div class='metric-value' style='color:{color}'>{v}%</div></div>", unsafe_allow_html=True)

        # --- 第二部分：PESTEL 因果链 ---
        st.divider()
        st.markdown("### 🔗 PESTEL 深度因果演化 (Causal Modeling)")
        causal = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":f"为{event_input}生成PESTEL因果链条"}]).choices[0].message.content
        st.markdown(f"<div class='logic-box'>{causal.replace('->', ' ➔ ')}</div>", unsafe_allow_html=True)

        # --- 第三部分：四智能体博弈 ---
        st.divider()
        st.markdown("### 🔄 智能体多维博弈回溯")
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f"<div class='role-card'><b>🏛️ 官方决策</b><br><br>{evo_data.get('official')}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='role-card'><b>⚠️ 民众反应</b><br><br>{evo_data.get('citizen')}</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='role-card'><b>📢 信息传播</b><br><br>{evo_data.get('media')}</div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='role-card'><b>🛡️ 逻辑审计</b><br><br>{evo_data.get('audit')}</div>", unsafe_allow_html=True)

        # 黑天鹅警告
        st.markdown(f"<div class='swan-alert'>🚨 **随机黑天鹅扰动：** {black_swan}</div>", unsafe_allow_html=True)

        # --- 第四部分：战略研判报告 ---
        st.divider()
        with st.spinner("📜 正在生成最终研判报告..."):
            report_p = f"基于实证{facts}、演化{evo_data}和黑天鹅{black_swan}，为{event_input}撰写深度报告。包含崩溃点预警和应急策。"
            report_content = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":report_p}]).choices[0].message.content
        
        st.markdown(f"<div class='report-card'><h2>📝 全维度深度战略研判报告</h2><br>{report_content}</div>", unsafe_allow_html=True)
        st.download_button("📥 导出仿真完整数据集", report_content)
