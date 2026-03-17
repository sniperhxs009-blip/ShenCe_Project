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
                f"""
                [{item['time']}] 事件：{item['event'][:30]}...
                """,
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
                {item.get('title')[:25]}...{item.get('snippet')[:100]}...查看详情 →
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
    st.markdown(f"{path_code.replace('->', ' ➔ ')}", unsafe_allow_html=True)

    st.divider()
    st.markdown("### 🔄 智能体多维博弈回溯")
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f"{off}", unsafe_allow_html=True)
    with c2: st.markdown(f"{cit}", unsafe_allow_html=True)
    with c3: st.markdown(f"{med}", unsafe_allow_html=True)
    with c4: st.markdown(f"{rsk}", unsafe_allow_html=True)

    st.divider()
    st.markdown(f"📝 全维度战略研判报告 (PESTEL 架构){report}", unsafe_allow_html=True)
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
                {item.get('title')[:25]}...{item.get('snippet')[:100]}...查看详情 →
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
    st.markdown(f"{path_code.replace('->', ' ➔ ')}", unsafe_allow_html=True)

    st.divider()
    st.markdown("### 🔄 智能体多维博弈回溯")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"{off}", unsafe_allow_html=True)
    with c2: st.markdown(f"{cit}", unsafe_allow_html=True)
    with c3: st.markdown(f"{med}", unsafe_allow_html=True)
    with c4: st.markdown(f"{rsk}", unsafe_allow_html=True)

    st.divider()
    st.markdown("### 📝 生成综合研判报告")
    with st.spinner("正在生成 PESTEL 深度报告..."):
        # ======================= 【核心修改：PESTEL报告生成逻辑】 =======================
        # 重写Prompt，强制报告紧扣事件、基于所有推演结果，给出可落地对策
        def get_report():
            # 构建完整的推演上下文，让AI能调用所有前期结果
            report_prompt = f"""
            你是顶级战略研判专家，专注于复杂事件的全维度分析，本次任务是为【{event_input}】事件，基于本次完整推演结果，撰写PESTEL架构的深度研判报告，要求如下：

            一、核心要求（必须严格遵守，否则报告无效）
            1.  全文紧扣【{event_input}】事件，不脱离事件本身泛泛而谈，所有分析、结论、对策都要对应本次事件场景；
            2.  严格基于本次推演的所有核心数据，不得编造信息，所有观点必须有推演结果支撑：
                - 初始社会状态：政府效能{init_eff}分、民众焦虑{init_panic}分、资源储备{init_res}分；
                - 社会演化趋势：{json.dumps(time_data, ensure_ascii=False, indent=2)}（T0到7天的4项核心指标变化）；
                - 多主体博弈结果：官方决策[{off}]、民众反应[{cit}]、舆论态势[{med}]、风险漏洞[{rsk}]；
                - 连锁反应链条：{path_code}；
                - 历史参考：{facts_text}（无则忽略，但需说明）；
            3.  PESTEL六个维度（政治、经济、社会、技术、环境、法律），每个维度都要结合上述推演结果分析，不遗漏任何一个维度；
            4.  每个维度分析后，必须给出【针对性、可落地】的对策建议，对策要对应维度痛点，不能空洞，要结合本次事件的演化趋势和风险点；
            5.  报告结尾需有【综合总结】，提炼核心风险、关键结论和整体应对思路，呼应前期所有推演结果；
            6.  语言严谨、专业，符合战略研判报告调性，避免口语化，逻辑连贯，层层递进，不出现与事件无关的废话。

            二、报告结构（严格按照此结构撰写，无需额外标题）
            1.  引言：简要说明本次事件背景、推演目的，关联初始社会状态，引出PESTEL分析；
            2.  PESTEL各维度分析（每维度含“现状分析+问题痛点+可落地对策”）：
                - 政治维度（Political）：结合政府效能演化、官方决策，分析政策响应、管控能力等，给出优化建议；
                - 经济维度（Economic）：结合资源储备变化、连锁反应，分析经济影响、资源调度等，给出应对方案；
                - 社会维度（Social）：结合民众焦虑变化、民众反应、舆论态势，分析社会情绪、谣言管控等，给出疏导建议；
                - 技术维度（Technological）：结合事件处置需求，分析技术支撑（如信息发布、资源调度技术）的不足与优化方向；
                - 环境维度（Environmental）：结合事件本身（如极端灾害、公共卫生等），分析环境影响、次生灾害防控；
                - 法律维度（Legal）：结合事件处置中的合规性、责任界定，分析法律风险，给出合规建议；
            3.  综合总结：提炼核心风险（结合风险漏洞和演化趋势）、关键结论，给出整体应对策略，呼应推演目标。

            三、禁忌
            - 禁止脱离本次事件和推演结果，编造分析内容；
            - 禁止对策空洞（如“加强管理”“提升能力”类废话），必须具体可落地；
            - 禁止遗漏PESTEL任何一个维度；
            - 禁止出现与【{event_input}】事件无关的内容，不泛谈通用理论。
            """
            return client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role":"system","content":"你是严谨的战略研判专家，只输出符合要求的PESTEL报告，不添加任何多余内容"},
                         {"role":"user","content":report_prompt}],
                temperature=0.3  # 降低发散率，确保报告严谨、贴合事实
            ).choices[0].message.content
        
        report = safe_api_call(get_report, max_retries) or "报告生成失败，建议重试或检查API配置"
        st.session_state.last_result["report"] = report

    st.markdown(f"📝 全维度战略研判报告 (PESTEL 架构){report}", unsafe_allow_html=True)
    
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
