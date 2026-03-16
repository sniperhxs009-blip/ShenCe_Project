import streamlit as st
from openai import OpenAI
import json
import plotly.graph_objects as go
import requests
import random
import time

# --- 1. 界面与专业推演样式配置 ---
st.set_page_config(page_title="SHENCE - 复杂社会系统大模型仿真沙盘", layout="wide")
st.markdown("""
    <style>
    .block-container { max-width: 98% !important; padding: 1rem 2% !important; background-color: #0b0e14; }
    .stMarkdown, p, h3, h2, h1 { color: #c9d1d9 !important; }
    
    /* 数值仪表盘：MiroFish 风格 */
    .metric-container {
        display: flex; justify-content: space-between; gap: 10px; margin-bottom: 25px;
    }
    .metric-card { 
        flex: 1; background-color: #161b22; padding: 20px; border-radius: 12px; 
        border: 1px solid #30363d; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .metric-value { font-size: 2.2rem; font-weight: bold; margin: 10px 0; font-family: 'Courier New'; }
    
    /* 逻辑演化路径 */
    .logic-box { 
        background-color: #0d1117; padding: 30px; border-left: 8px solid #58a6ff; 
        border-radius: 8px; margin: 20px 0; font-family: 'Consolas', monospace; 
        color: #8b949e; border: 1px solid #30363d; line-height: 1.8;
    }
    
    /* 角色博弈卡片 */
    .role-card { 
        padding: 25px; border-radius: 12px; min-height: 500px; 
        border: 1px solid #30363d; background: #161b22; margin-bottom: 20px;
    }
    .role-header { font-size: 1.3rem; font-weight: bold; margin-bottom: 15px; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
    
    /* 研判报告：政务级排版 */
    .report-card { 
        background-color: #ffffff; padding: 50px; border-radius: 20px; color: #1a1a1a !important;
        border-top: 20px solid #1f6feb; box-shadow: 0 20px 60px rgba(0,0,0,0.6); width: 100%; margin-top: 40px;
    }
    .report-card h2, .report-card h3, .report-card p { color: #1a1a1a !important; }
    .swan-alert { background-color: #3e1e1e; border: 2px solid #da3633; padding: 20px; border-radius: 10px; margin: 20px 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心 API 配置 ---
SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
BASE_URL = "https://api.ohmygpt.com/v1"
SERPER_API_KEY = "d57fbcfd2ecd16f71b9b131984050fab2c64d707" 
client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)

# --- 3. MiroFish 仿真逻辑模块 ---

def fetch_historical_evidence(query):
    """【功能一：实证搜寻】基于 Serper 抓取真实社会学事实"""
    search_url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    payload = json.dumps({"q": f"{query} 历史案例 真实民众表现 处置教训 供应链瘫痪 社会动荡", "num": 10})
    try:
        res = requests.post(search_url, headers=headers, data=payload, timeout=12)
        results = res.json().get('organic', [])
        return "\n".join([f"事实点: {r.get('snippet')}" for r in results])
    except: return "未获取到在线实证，启用高保真社会学经验模型推演。"

def initialize_matrix(event, facts):
    """【功能二：数值化社会矩阵】初始化四个核心参数"""
    prompt = f"基于事件 {event} 和实证 {facts}，请初始化四个数值(0-100)：1.行政效能、2.焦虑指数、3.资源缺口、4.动荡风险。仅返回 JSON 格式。"
    try:
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"}).choices[0].message.content
        return json.loads(res)
    except: return {"行政效能": 70, "焦虑指数": 40, "资源缺口": 30, "动荡风险": 20}

def simulate_step(step_id, facts, matrix, event):
    """【功能三：三步时空增量演化】模拟多智能体连续博弈"""
    prompt = f"""
    推演阶段: 第 {step_id} 阶段 (增量演化)
    环境实证: {facts}
    当前矩阵: {matrix}
    初始扰动: {event}
    请模拟该时段内各主体的真实表现：
    1. 官方：行政博弈与硬核管控决策。
    2. 民众：基于马斯洛生存需求的生存反应（体现真实的自私、互助、恐慌冲突）。
    3. 传播：非数字环境下的口头信息发酵。
    4. 风险：逻辑漏洞审计。
    返回 JSON 格式：{{'official': '', 'citizen': '', 'media': '', 'audit': ''}}
    """
    res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"}).choices[0].message.content
    return json.loads(res)

def generate_black_swan():
    """【功能四：随机黑天鹅扰动】增加仿真的不可控深度"""
    swans = ["核心应急仓库发生火灾","备用发电机组因燃油污染集体停摆","外部恶意势力利用短波电台煽动动乱","极端天气突然恶化导致物理救援完全中断","关键决策官员突发健康危机造成指挥真空"]
    return random.choice(swans)

# --- 4. 主程序流程 ---
st.title("🛡️ SHENCE (神策) | 实证数据驱动·复杂系统仿真沙盘")
st.caption("内核版本：MiroFish-v3.0 | 仿真模式：多主体增量演化博弈")

event_input = st.text_area("📡 输入初始扰动事件 (Initial Shock Event)", placeholder="例如：超大城市遭遇大规模黑客攻击导致电力、水利系统全面瘫痪48小时，且通讯信号基站大规模宕机...", height=100)

if st.button("🚀 启动全维度深度演化仿真"):
    if not event_input:
        st.warning("请输入事件关键词！")
    else:
        with st.status("🛠️ 系统正在初始化仿真环境并检索 PESTEL 事实...", expanded=True) as status:
            
            # 第一阶段：实证数据采集
            st.write("🌐 联网检索全球历史案例事实...")
            facts_data = fetch_historical_evidence(event_input)
            
            # 第二阶段：数值矩阵初始化
            st.write("📈 构建初始社会属性矩阵...")
            matrix_data = initialize_matrix(event_input, facts_data)
            
            # 第三阶段：演化模拟循环 (模拟核心博弈过程)
            st.write("🔄 正在运行 T+24H 演化循环 (智能体博弈)...")
            step_result = simulate_step("时空演化阶段-爆发期", facts_data, matrix_data, event_input)
            
            # 第四阶段：黑天鹅计算
            st.write("🦢 正在计算环境随机扰动 (Black Swan Event)...")
            random_swan = generate_black_swan()
            
            # 第五阶段：PESTEL 建模与报告生成
            st.write("📜 正在整合 PESTEL 数据撰写全维度战略报告...")
            report_prompt = f"基于实证 {facts_data}、演化结果 {step_result} 以及突发扰动 {random_swan}。为事件 {event_input} 撰写深度战略研判报告。要求：1.物理崩溃点分析；2.社会心理转折点预测；3.硬核行政干预方案。"
            final_report = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":report_prompt}]).choices[0].message.content
            
            status.update(label="✅ 仿真演化完毕：数据已对齐实证教训", state="complete")

        # --- 页面显示：MiroFish 专业版布局 ---

        # 1. 数值矩阵展示
        st.markdown("### 📊 当前社会系统状态矩阵 (Numerical Matrix)")
        m_keys = list(matrix_data.keys())
        m_vals = list(matrix_data.values())
        cols = st.columns(len(m_keys))
        for i, col in enumerate(cols):
            with col:
                color = "#58a6ff" if "效能" in m_keys[i] else "#da3633"
                st.markdown(f"""
                    <div class='metric-card'>
                        <div style='color: #8b949e'>{m_keys[i]}</div>
                        <div class='metric-value' style='color: {color}'>{m_vals[i]}%</div>
                    </div>
                """, unsafe_allow_html=True)

        # 2. PESTEL 因果链
        st.divider()
        st.markdown("### 🔗 PESTEL 深度因果演化链条 (Causal Chain Modeling)")
        causal_res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":f"为 {event_input} 生成基于 PESTEL 维度的深度因果环路文本链条"}]).choices[0].message.content
        st.markdown(f"<div class='logic-box'>{causal_res.replace('->', ' ➔ ')}</div>", unsafe_allow_html=True)

        # 3. 多主体演化博弈展示 (四列并排)
        st.divider()
        st.markdown("### 🔄 智能体多维博弈回溯 (Multi-Agent Interaction)")
        c1, c2, c3, c4 = st.columns(4)
        with c1: 
            st.markdown(f"<div class='role-card'><div class='role-header' style='color:#58a6ff'>🏛️ 官方决策</div>{step_result.get('official')}</div>", unsafe_allow_html=True)
        with c2: 
            st.markdown(f"<div class='role-card'><div class='role-header' style='color:#d29922'>⚠️ 民众反应</div>{step_result.get('citizen')}</div>", unsafe_allow_html=True)
        with c3: 
            st.markdown(f"<div class='role-card'><div class='role-header' style='color:#238636'>📢 信息传播</div>{step_result.get('media')}</div>", unsafe_allow_html=True)
        with c4: 
            st.markdown(f"<div class='role-card'><div class='role-header' style='color:#da3633'>🛡️ 逻辑审计</div>{step_result.get('audit')}</div>", unsafe_allow_html=True)

        # 4. 随机扰动 (黑天鹅)
        st.markdown(f"""
            <div class='swan-alert'>
                <h3 style='color:#ff7b72; margin-top:0;'>🚨 随机黑天鹅扰动 (Stochastic Shock)</h3>
                <p style='color:#e0e0e0; font-size:1.1rem;'>系统模拟过程中检测到低概率突发变量：<b>{random_swan}</b>。该变量已自动反馈至终期研判报告中。</p>
            </div>
        """, unsafe_allow_html=True)

        # 5. 战略研判报告 (全屏展示)
        st.divider()
        st.markdown(f"<div class='report-card'><h2>📝 全维度深度战略研判报告 (MiroFish-v3)</h2><br>{final_report}</div>", unsafe_allow_html=True)
        
        # 导出按钮
        st.download_button(label="📥 下载全量仿真推演报告", data=final_report, file_name="ShenCe_Report.md", mime="text/markdown")

else:
    st.info("💡 请输入初始扰动事件。系统将自动调用 Serper 联网接口抓取实证教训，并启动复杂系统仿真演化。")
