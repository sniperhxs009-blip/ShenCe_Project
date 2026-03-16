import streamlit as st
from openai import OpenAI
import requests
import json
import plotly.graph_objects as go
import re

# --- 1. 界面与专业样式配置 ---
st.set_page_config(page_title="神策 - 战略级联动推演系统", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    /* 功能 6: 四角色彩色卡片 */
    .role-card { padding: 18px; border-radius: 12px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .role-official { background-color: #e3f2fd; border-left: 5px solid #1565c0; color: #0d47a1; }
    .role-citizen { background-color: #e8f5e9; border-left: 5px solid #2e7d32; color: #1b5e20; }
    .role-media { background-color: #fff3e0; border-left: 5px solid #ef6c00; color: #e65100; }
    .role-risk { background-color: #fce4ec; border-left: 5px solid #c2185b; color: #880e4f; }
    /* 功能 7: 逻辑链条解析框 */
    .logic-box { background-color: #ffffff; padding: 15px; border: 1px dashed #673ab7; border-radius: 10px; font-family: monospace; }
    /* 侧边栏样式 */
    .status-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 5px; }
    .dot-green { background-color: #28a745; }
    .dot-blue { background-color: #007bff; }
    .dot-orange { background-color: #fd7e14; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心密钥配置 ---
SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
BASE_URL = "https://api.ohmygpt.com/v1"
client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)

try:
    SERPER_K = st.secrets["SERPER_API_KEY"]
except:
    st.error("❌ 缺少 SERPER_API_KEY")
    st.stop()

# --- 3. 侧边栏 (严格对照你的 8 项要求，确保滑块第一优先级显示) ---
with st.sidebar:
    st.title("🛡️ 系统监控面板")
    
    # 【功能 1: 模型展示指示灯】
    st.markdown("### 当前调度模型")
    st.markdown('<div style="background-color:#e8f5e9;padding:10px;border-radius:5px;margin-bottom:5px;"><span class="status-dot dot-green"></span> 逻辑大脑: GPT-4o</div>', unsafe_allow_html=True)
    st.markdown('<div style="background-color:#e3f2fd;padding:10px;border-radius:5px;margin-bottom:5px;"><span class="status-dot dot-blue"></span> 量化引擎: GPT-4o-mini</div>', unsafe_allow_html=True)
    st.markdown('<div style="background-color:#fffde7;padding:10px;border-radius:5px;margin-bottom:10px;"><span class="status-dot dot-orange"></span> 搜索插件: Serper Global</div>', unsafe_allow_html=True)
    
    st.divider()

    # 【功能 2: 三个变量滑块 - 放在这里确保初始加载就显示】
    st.subheader("⚙️ 仿真参数注入")
    v_control = st.slider("⚖️ 官方干预力度", 0, 100, 50, help="调节管控强度")
    v_media = st.slider("📢 舆论开放程度", 0, 100, 50, help="调节信息透明度")
    v_fund = st.slider("💰 资源保障投入", 0, 100, 30, help="调节资源丰富度")
    
    st.divider()
    
    # 【功能 3: Trace Logs 动态显示】
    st.write("**实时调度流 (Trace Logs):**")
    log_stream = st.empty()
    log_stream.code("READY: 系统就绪\nWAITING: 等待事件输入...")
    
    st.divider()
    
    # 【功能 4: 自检与重启按钮】
    if st.button("运行接口连通性自检"):
        try:
            client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":"hi"}], max_tokens=5)
            st.success("API 链路通畅")
        except: st.error("连接异常")
            
    if st.button("🔄 重启系统引擎"):
        st.rerun()

# --- 4. 核心功能函数 ---
def get_logic_path(event):
    prompt = f"针对【{event}】，生成简短因果链条（A -> B -> C）。只输出代码。"
    try:
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
        return res.choices[0].message.content
    except: return "数据计算中..."

# --- 5. 主页面逻辑 ---
st.title("🔮 SHENCE (神策) | 多模态博弈推演沙盘")
event_input = st.text_area("📡 目标事件输入", placeholder="在此输入研判目标...", height=100)

if st.button("🚀 启动全维度深度推演"):
    if event_input:
        log_stream.code(f"INIT: 引擎启动\nVAR: 注入参数({v_control}, {v_media}, {v_fund})")
        
        with st.status("🛠️ 系统正在进行深度建模...", expanded=True) as status:
            # 1. 量化数据
            st.write("📈 构建动态演化模型...")
            d_prompt = f"事件:{event_input}。变量:干预={v_control},舆论={v_media},资金={v_fund}。输出JSON:{{\"T0\":[..],\"T24\":[..],\"T72\":[..],\"T7d\":[..]}}"
            res_data = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":d_prompt}])
            time_data = json.loads(re.search(r'(\{.*\})', res_data.choices[0].message.content, re.DOTALL).group(1))

            # 2. 逻辑路径 (功能 7)
            path_code = get_logic_path(event_input)

            # 3. 多智能体博弈 (功能 6)
            st.write("🔄 激活多主体博弈对撞...")
            off = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":f"强度{v_control}下官方对策？"}]).choices[0].message.content
            cit = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":f"民众反馈？"}]).choices[0].message.content
            med = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":f"媒体定调？"}]).choices[0].message.content
            rsk = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":f"次生风险风险研判？"}]).choices[0].message.content
            
            status.update(label="✅ 推演完成", state="complete")

        # 渲染主界面
        col_left, col_right = st.columns([3, 2])
        with col_left:
            # 【功能 5: 数字化趋势图】
            st.markdown("### 📈 社会稳定风险演化趋势")
            fig = go.Figure()
            names = ['官方压力', '民众情绪', '舆论热度', '整体风险']
            colors = ['#1565c0', '#2e7d32', '#ef6c00', '#c2185b']
            for i in range(4):
                try:
                    y = [time_data['T0'][i], time_data['T24'][i], time_data['T72'][i], time_data['T7d'][i]]
                    fig.add_trace(go.Scatter(x=['当前','24h','72h','7d'], y=y, name=names[i], line=dict(color=colors[i], width=4)))
                except: continue
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            # 【功能 7: 逻辑链条解析】
            st.markdown("### 🔗 连锁反应路径 (次生灾害)")
            st.markdown(f"<div class='logic-box'>{path_code.replace('->', ' ➔ ')}</div>", unsafe_allow_html=True)
            
            # 【功能 8: 对策推荐】
            st.markdown("### 💡 对策方案推荐")
            strat = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":f"风险值{time_data['T7d'][3]}给出方案"}]).choices[0].message.content
            st.info(strat)

        # 【功能 6: 四角色彩色卡片】
        st.markdown("---")
        st.markdown("### 🔄 智能体实时博弈回放")
        cx, cy = st.columns(2)
        with cx:
            st.markdown(f"<div class='role-card role-official'><b>🏛️ 官方决策</b><br>{off}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='role-card role-citizen'><b>👥 民众反馈</b><br>{cit}</div>", unsafe_allow_html=True)
        with cy:
            st.markdown(f"<div class='role-card role-media'><b>📰 媒体定调</b><br>{med}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='role-card role-risk'><b>🛡️ 风险监测</b><br>{rsk}</div>", unsafe_allow_html=True)

        st.divider()
        st.download_button("📥 导出研判报告", "Report...")

else:
    st.info("💡 系统已备妥。请先在左侧调节仿真变量，然后输入事件并启动推演。")
