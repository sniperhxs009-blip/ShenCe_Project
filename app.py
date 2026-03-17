import streamlit as st
from openai import OpenAI
import json
import plotly.graph_objects as go
import requests
import time
from datetime import datetime
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
    .status-card {
        padding: 15px; border-radius: 8px; margin: 10px 0;
        background: #f8f9ff; border-left: 6px solid #673ab7;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 全局会话状态缓存（新增）---
if "simulation_history" not in st.session_state:
    st.session_state.simulation_history = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None

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
    enable_cache = st.toggle("启用推演结果缓存", value=True)  # 新增
    max_retries = st.slider("API 重试次数", 1, 3, 2)           # 新增
    temp_val = st.slider("思维发散率 (Temperature)", 0.0, 1.0, 0.7)

    st.divider()
    st.subheader("📜 推演历史记录")
    if st.button("清空历史记录"):
        st.session_state.simulation_history = []
        st.success("已清空所有推演历史")

# --- 3. 核心 API 配置 ---
# 从 secrets 读取（更安全），兼容原有写法
try:
    SECRET_KEY = st.secrets["OPENAI_API_KEY"]
    BASE_URL = st.secrets["OPENAI_BASE_URL"]
    SERPER_API_KEY = st.secrets["SERPER_API_KEY"]
except:
    SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
    BASE_URL = "https://api.ohmygpt.com/v1"
    SERPER_API_KEY = "d57fbcfd2ecd16f71b9b131984050fab2c64d707" 

client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)

# --- 增强工具函数 ---
def safe_api_call(func, max_retries=2, delay=2):
    """API 重试机制（新增）"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                st.error(f"API 调用失败：{str(e)}")
                return None
            time.sleep(delay)

def fetch_evidence(query):
    """优化证据检索，增加超时与异常处理"""
    if not enable_serper:
        return []
    
    url = "https://google.serper.dev/search"
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    payload = json.dumps({
        "q": f"{query} 真实历史案例 社会动态 处置教训",
        "num": 5,
        "page": 1
    })
    
    def call():
        res = requests.post(url, headers=headers, data=payload, timeout=20)
        res.raise_for_status()
        return res.json().get('organic', [])
    
    return safe_api_call(call, max_retries) or []

def get_time_data_fallback():
    """标准化兜底数据（新增）"""
    return {
        "T0": [init_eff, init_panic, init_res, 20],
        "T24": [50, 50, 50, 50],
        "T48": [50, 50, 50, 50],
        "T72": [50, 50, 50, 50],
        "T7d": [50, 50, 50, 50]
    }

# --- 4. 主程序流程 ---
st.title("🔮 SHENCE (神策) | 多脑协同·复杂演化仿真系统")
event_input = st.text_area(
    "📡 输入初始扰动事件",
    placeholder="输入极端事件，系统将启动多脑协同推演...",
    height=100
)

# 展示推演历史（新增）
if st.session_state.simulation_history:
    with st.expander("📜 查看最近推演记录", expanded=False):
        for idx, item in enumerate(reversed(st.session_state.simulation_history[-5:])):
            st.markdown(
                f"""<div class='status-card'>
                [{item['time']}] 事件：{item['event'][:30]}...
                </div>""",
                unsafe_allow_html=True
            )

col1, col2 = st.columns([3,1])
with col1:
    start_btn = st.button("🚀 启动全维度深度演化推演", type="primary")
with col2:
    reuse_last = st.button("♻️ 重新加载上一次结果", disabled=st.session_state.last_result is None)

# 复用上次结果（新增）
if reuse_last and st.session_state.last_result:
    data = st.session_state.last_result
    event_input = data["event"]
    raw_evidence = data["evidence"]
    time_data = data["matrix"]
    off, cit, med, rsk = data["roles"]
    path_code = data["chain"]
    report = data["report"]

    # 直接渲染结果
    st.markdown("### 📚 历史相似案例实证")
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
    else:
        st.info("未发现直接历史对标案例。")

    st.divider()
    st.markdown("### 📈 社会系统演化矩阵")
    fig = go.Figure()
    names = ['行政效能', '民众焦虑', '资源储备', '动荡风险']
    steps = ["T0", "T24", "T48", "T72", "T7d"]
    for i in range(4):
        y_vals = []
        for s in steps:
            stage_list = time_data.get(s, [50]*4)
            val = stage_list[i] if len(stage_list) > i else 50
            y_vals.append(val)
        fig.add_trace(go.Scatter(x=['当前','24h','48h','72h','7d'], y=y_vals, name=names[i], line=dict(width=6), mode='lines+markers'))
    fig.update_layout(height=450, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 🔗 连锁反应路径")
    st.markdown(f"<div class='logic-box'>{path_code.replace('->', ' ➔ ')}</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown("### 🔄 智能体多维博弈回溯")
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f"<div class='role-card role-official'><b>🏛️ 官方决策</b><br><br>{off}</div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='role-card role-citizen'><b>⚠️ 民众反应</b><br><br>{cit}</div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='role-card role-media'><b>📢 舆论态势</b><br><br>{med}</div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='role-card role-risk'><b>🛡️ 逻辑审计</b><br><br>{rsk}</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown(f"<div class='report-card'><h2>📝 全维度战略研判报告 (PESTEL 架构)</h2><br>{report}</div>", unsafe_allow_html=True)
    st.download_button("📂 导出推演档案 (.md)", data=f"# 神策推演报告\n\n{report}", file_name="shence_report.md")

elif start_btn:
    if not event_input.strip():
        st.warning("请输入扰动事件后再启动推演！")
        st.stop()

    with st.status("🧠 模型大脑协同计算中...", expanded=True) as status:
        # 1. 联网实证
        st.write("🌐 正在检索全球相似案例并对齐事实...")
        raw_evidence = fetch_evidence(event_input)
        facts_text = "\n".join([e.get('snippet', '') for e in raw_evidence]) if raw_evidence else "无历史案例参考"
        
        # 2. 构建逻辑矩阵
        lg = f"事实基础：{facts_text}\n初始状态：效能{init_eff}, 焦虑{init_panic}, 储备{init_res}"
        
        # 3. 趋势量化
        st.write("📊 正在量化社会系统演化矩阵...")
        trend_p = """
        输出 T0, T24, T48, T72, T7d 五阶段指标 JSON。
        格式严格为: {"T0": [效能,焦虑,储备,风险], "T24": [...], ...}
        每个列表必须包含且仅包含 4 个 0-100 的整数。
        不要输出多余文字，只返回JSON。
        """
        
        def get_trend():
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"system","content":lg},{"role":"user","content":trend_p}],
                response_format={"type":"json_object"},
                temperature=0.1
            )
            return json.loads(res.choices[0].message.content)
        
        time_data = safe_api_call(get_trend, max_retries) or get_time_data_fallback()

        # 4. 深度博弈
        st.write("🔄 启动多主体动态博弈仿真...")
        def sim(role, p):
            def call():
                return client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role":"system","content":f"你是{role}。{lg}"},{"role":"user","content":p}],
                    temperature=temp_val
                ).choices[0].message.content
            return safe_api_call(call, max_retries) or f"{role} 模块暂不可用"
        
        off = sim("应急指挥中心", "提出具体物理管控与资源调度方案。")
        cit = sim("真实受灾民众", "描述生理与心理在压力下的真实演变。")
        med = sim("信息观察员", "谣言传播路径与社会情绪拐点分析。")
        rsk = sim("逻辑审计官", f"指出前述内容的逻辑漏洞，并注入一个{'黑天鹅变量' if black_swan else '潜在风险'}。")
        
        # 连锁反应
        def get_chain():
            return client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":f"基于{facts_text}生成该事件的复杂连锁灾难链条"}]
            ).choices[0].message.content
        
        path_code = safe_api_call(get_chain, max_retries) or "无法生成连锁反应路径"
        
        status.update(label="✅ 仿真演化完成", state="complete")

    # 保存到缓存与历史（新增）
    st.session_state.last_result = {
        "event": event_input,
        "evidence": raw_evidence,
        "matrix": time_data,
        "roles": (off, cit, med, rsk),
        "chain": path_code,
        "report": ""
    }
    st.session_state.simulation_history.append({
        "time": datetime.now().strftime("%m-%d %H:%M"),
        "event": event_input
    })

    # --- 渲染视图 ---
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
    else:
        st.info("未发现直接历史对标案例。")

    st.divider()
    st.markdown("### 📈 社会系统演化矩阵 (Matrix Evolution)")
    fig = go.Figure()
    names = ['行政效能', '民众焦虑', '资源储备', '动荡风险']
    steps = ["T0", "T24", "T48", "T72", "T7d"]
    
    for i in range(4):
        y_vals = []
        for s in steps:
            stage_list = time_data.get(s, [50,50,50,50])
            val = stage_list[i] if len(stage_list) > i else 50
            y_vals.append(val)
        fig.add_trace(go.Scatter(x=['当前','24h','48h','72h','7d'], y=y_vals, name=names[i], line=dict(width=6), mode='lines+markers'))
    
    fig.update_layout(height=450, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 🔗 连锁反应路径")
    st.markdown(f"<div class='logic-box'>{path_code.replace('->', ' ➔ ')}</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown("### 🔄 智能体多维博弈回溯")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='role-card role-official'><b>🏛️ 官方决策</b><br><br>{off}</div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='role-card role-citizen'><b>⚠️ 民众反应</b><br><br>{cit}</div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='role-card role-media'><b>📢 舆论态势</b><br><br>{med}</div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='role-card role-risk'><b>🛡️ 逻辑审计</b><br><br>{rsk}</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown("### 📝 生成综合研判报告")
    with st.spinner("正在生成 PESTEL 深度报告..."):
        def get_report():
            report_p = f"基于实证与仿真结果，为该事件撰写深度 PESTEL 研判报告。"
            return client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role":"user","content":report_p}]
            ).choices[0].message.content
        
        report = safe_api_call(get_report, max_retries) or "报告生成失败"
        st.session_state.last_result["report"] = report

    st.markdown(f"<div class='report-card'><h2>📝 全维度战略研判报告 (PESTEL 架构)</h2><br>{report}</div>", unsafe_allow_html=True)
    
    # 导出功能
    export_content = f"""# 神策推演报告
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
事件：{event_input}

## 一、社会系统演化数据
{json.dumps(time_data, indent=2, ensure_ascii=False)}

## 二、多角色博弈
### 官方决策
{off}

### 民众反应
{cit}

### 舆论态势
{med}

### 逻辑审计
{rsk}

## 三、连锁反应
{path_code}

## 四、PESTEL 研判报告
{report}
"""
    st.download_button(
        "📂 导出完整推演档案 (.md)",
        data=export_content,
        file_name=f"神策推演_{datetime.now().strftime('%Y%m%d%H%M')}.md"
    )

else:
    st.info("💡 请在左侧配置仿真大脑参数并输入仿真目标。")
