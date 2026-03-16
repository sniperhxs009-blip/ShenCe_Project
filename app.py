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
    /* 侧边栏指示灯 */
    .status-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 5px; }
    .dot-green { background-color: #28a745; }
    .dot-blue { background-color: #007bff; }
    .dot-orange { background-color: #fd7e14; }
    /* 全维度研判报告卡片 */
    .report-card { background-color: #ffffff; padding: 35px; border-radius: 20px; border: 3px solid #1565c0; box-shadow: 0 15px 45px rgba(0,0,0,0.15); margin-top: 30px; line-height: 1.8; }
    .report-header { color: #1565c0; border-bottom: 2px solid #1565c0; padding-bottom: 10px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心密钥配置 ---
SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
BASE_URL = "https://api.ohmygpt.com/v1"
client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)

try:
    SERPER_K = st.secrets["SERPER_API_KEY"]
except:
    st.error("❌ 缺少 SERPER_API_KEY，请在 Secrets 中配置。")
    st.stop()

# --- 3. 侧边栏 (严格对照 8 项功能，滑块第一优先级常驻) ---
with st.sidebar:
    st.title("🛡️ 系统监控面板")
    
    # 【功能 1: 模型展示指示灯】
    st.markdown("### 当前调度模型")
    st.markdown('<div style="background-color:#e8f5e9;padding:10px;border-radius:5px;margin-bottom:5px;"><span class="status-dot dot-green"></span> 逻辑大脑: GPT-4o</div>', unsafe_allow_html=True)
    st.markdown('<div style="background-color:#e3f2fd;padding:10px;border-radius:5px;margin-bottom:5px;"><span class="status-dot dot-blue"></span> 量化引擎: GPT-4o-mini</div>', unsafe_allow_html=True)
    st.markdown('<div style="background-color:#fffde7;padding:10px;border-radius:5px;margin-bottom:10px;"><span class="status-dot dot-orange"></span> 搜索插件: Serper Global</div>', unsafe_allow_html=True)
    
    st.divider()

    # 【功能 2: 三个变量滑块 - 强制常驻】
    st.subheader("⚙️ 仿真参数注入")
    v_control = st.slider("⚖️ 官方干预力度", 0, 100, 50)
    v_media = st.slider("📢 舆论开放程度", 0, 100, 50)
    v_fund = st.slider("💰 资源保障投入", 0, 100, 30)
    
    st.divider()
    
    # 【功能 3: Trace Logs 动态显示】
    st.write("**实时调度流 (Trace Logs):**")
    log_stream = st.empty()
    log_stream.code("READY: 系统就绪\nWAITING: 等待事件输入...")
    
    st.divider()
    
    # 【功能 4: 自检与重启按钮】
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("🔌 链路自检"):
            try:
                client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":"hi"}], max_tokens=5)
                st.sidebar.success("正常")
            except: st.sidebar.error("异常")
    with c_btn2:
        if st.button("🔄 重启引擎"): st.rerun()

# --- 4. 核心功能函数 ---
def get_logic_path(event):
    """【功能 7】逻辑链条解析"""
    prompt = f"针对【{event}】，生成简短因果链条（A -> B -> C）。只输出代码。"
    try:
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
        return res.choices[0].message.content
    except: return "数据计算中..."

# --- 5. 主页面逻辑 ---
st.title("🔮 SHENCE (神策) | 多模态博弈推演沙盘")
event_input = st.text_area("📡 目标事件输入", placeholder="在此输入研判目标，调节左侧变量后启动...", height=100)

if st.button("🚀 启动全维度深度推演"):
    if event_input:
        log_stream.code(f"INIT: 引擎启动\nVAR: 注入参数({v_control}, {v_media}, {v_fund})")
        
        with st.status("🛠️ 系统正在进行深度建模与角色博弈...", expanded=True) as status:
            # 1. 联网情报获取
            st.write("🌐 检索全球 OSINT 情报...")
            intel_res = requests.post("https://google.serper.dev/search", json={"q": event_input}, headers={'X-API-KEY': SERPER_K}).json()
            log_stream.code("FETCH: 联网情报同步完成")

            # 2. 量化数据分析 (功能 5)
            st.write("📈 构建动态演化模型...")
            d_prompt = f"事件:{event_input}。变量:干预={v_control},舆论={v_media},资金={v_fund}。输出JSON:{{\"T0\":[..],\"T24\":[..],\"T72\":[..],\"T7d\":[..]}}"
            res_data = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":d_prompt}])
            time_data = json.loads(re.search(r'(\{.*\})', res_data.choices[0].message.content, re.DOTALL).group(1))

            # 3. 逻辑路径 (功能 7)
            path_code = get_logic_path(event_input)

            # 4. 多智能体博弈 (功能 6)
            st.write("🔄 激活多主体博弈对撞...")
            off = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":f"强度{v_control}下官方对策？"}]).choices[0].message.content
            log_stream.code("AGENT: 官方决策完成")
            cit = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":f"民众反馈？"}]).choices[0].message.content
            log_stream.code("AGENT: 民众反应完成")
            med = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":f"媒体定调？"}]).choices[0].message.content
            rsk = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":f"风险研判？"}]).choices[0].message.content
            log_stream.code("DONE: 流程仿真结束")
            
            status.update(label="✅ 推演完成", state="complete")

        # --- 展示区：趋势图与逻辑路径 ---
        col_l, col_r = st.columns([3, 2])
        with col_l:
            st.markdown("### 📈 社会稳定风险演化趋势")
            fig = go.Figure()
            names, colors = ['官方压力', '民众情绪', '舆论热度', '整体风险'], ['#1565c0', '#2e7d32', '#ef6c00', '#c2185b']
            for i in range(4):
                try:
                    y = [time_data['T0'][i], time_data['T24'][i], time_data['T72'][i], time_data['T7d'][i]]
                    fig.add_trace(go.Scatter(x=['当前','24h','72h','7d'], y=y, name=names[i], line=dict(color=colors[i], width=4)))
                except: continue
            st.plotly_chart(fig, use_container_width=True)
        with col_r:
            st.markdown("### 🔗 连锁反应路径")
            st.markdown(f"<div class='logic-box'>{path_code.replace('->', ' ➔ ')}</div>", unsafe_allow_html=True)
            st.markdown("### 💡 实时对策推荐")
            strat = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":f"风险{time_data['T7d'][3]}。给出方案。"}]).choices[0].message.content
            st.info(strat)

        # --- 展示区：彩色卡片 ---
        st.markdown("---")
        st.markdown("### 🔄 智能体实时博弈对撞回放")
        cx, cy = st.columns(2)
        with cx:
            st.markdown(f"<div class='role-card role-official'><b>🏛️ 官方决策</b><br>{off}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='role-card role-citizen'><b>👥 民众反馈</b><br>{cit}</div>", unsafe_allow_html=True)
        with cy:
            st.markdown(f"<div class='role-card role-media'><b>📰 媒体定调</b><br>{med}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='role-card role-risk'><b>🛡️ 风险监测</b><br>{rsk}</div>", unsafe_allow_html=True)

        # --- 【核心新增：深度综合研判报告】 ---
        st.divider()
        with st.spinner("🔍 正在撰写全维度深度研判报告..."):
            report_p = f"""
            基于以上博弈数据，撰写深度综合研判报告：
            事件：{event_input}
            数据：官方策略({off})，民众反馈({cit})，媒体倾向({med})，核心风险({rsk})。
            
            要求：
            1. 必须覆盖政府稳态、民众诉求、媒体引导、社会平衡四个维度。
            2. 提出符合现有国情和政策的平衡性对策。
            3. 确保建议兼顾各方利益，具备极强实操性，解决社会各界矛盾。
            4. 语气严谨，具备战略参考价值。
            """
            final_report = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":report_p}]).choices[0].message.content
            log_stream.code("REPORT: 综合研判报告已生成")
            
        st.markdown(f"<div class='report-card'><h2 class='report-header'>📝 全维度深度综合研判报告</h2>{final_report}</div>", unsafe_allow_html=True)
        st.download_button("📥 导出全量仿真报告", final_report)
else:
    st.info("💡 系统已就绪。请调节左侧变量并输入事件启动深度推演。")
