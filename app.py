import streamlit as st
from openai import OpenAI
import requests
import json
import plotly.graph_objects as go
import re

# --- 1. 页面配置与专业 UI 样式 ---
st.set_page_config(page_title="神策 - 全功能多模态推演沙盘", layout="wide")

st.markdown("""
    <style>
    /* 页面基础背景 */
    .main { background-color: #f8f9fa; color: #333; }
    
    /* 角色卡片 */
    .role-card { padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.1); }
    .role-label { font-weight: bold; font-size: 1.2rem; margin-bottom: 10px; display: block; border-bottom: 2px solid; padding-bottom: 5px; }
    .model-badge { background-color: rgba(255,255,255,0.7); color: #444; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; float: right; font-weight: normal; }

    /* 四角色专属配色 */
    .role-official { background-color: #e3f2fd; border-left: 5px solid #1565c0; }
    .role-official .role-label { color: #1565c0; border-color: #1565c0; }
    
    .role-citizen { background-color: #e8f5e9; border-left: 5px solid #2e7d32; }
    .role-citizen .role-label { color: #2e7d32; border-color: #2e7d32; }
    
    .role-media { background-color: #fff3e0; border-left: 5px solid #ef6c00; }
    .role-media .role-label { color: #ef6c00; border-color: #ef6c00; }
    
    .role-risk { background-color: #fce4ec; border-left: 5px solid #c2185b; }
    .role-risk .role-label { color: #c2185b; border-color: #c2185b; }

    /* 研判报告 */
    .report-card { background-color: #ffffff; padding: 30px; border-radius: 15px; border: 2px solid #673ab7; box-shadow: 0 10px 20px rgba(0,0,0,0.1); margin-top: 20px; }
    .report-header { color: #512da8; font-size: 1.6rem; font-weight: bold; margin-bottom: 15px; text-align: center; border-bottom: 1px solid #eee; padding-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心密钥与模型配置 ---
SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
BASE_URL = "https://api.ohmygpt.com/v1"

try:
    SERPER_K = st.secrets["SERPER_API_KEY"]
except:
    st.error("❌ 缺少 SERPER_API_KEY")
    st.stop()

client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)

# --- 3. 侧边栏：模型监控与调用面板 ---
with st.sidebar:
    st.title("🛡️ 系统监控面板")
    st.subheader("当前调度模型")
    
    # 模拟实时状态指示灯
    st.success("● 逻辑大脑: GPT-4o")
    st.info("● 量化引擎: GPT-4o-mini")
    st.warning("● 搜索插件: Serper Global")
    
    st.divider()
    st.write("**实时调度流 (Trace Logs):**")
    log_placeholder = st.empty()
    
    st.divider()
    if st.button("运行接口连通性自检"):
        try:
            client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":"hi"}], max_tokens=5)
            st.success("API 连通正常")
        except Exception as e:
            st.error(f"连接失败: {e}")

# --- 4. 核心功能函数 ---
def fetch_intel(query):
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": f"{query} 政策 影响 舆情", "gl": "cn", "hl": "zh-cn"})
    headers = {'X-API-KEY': SERPER_K, 'Content-Type': 'application/json'}
    try:
        res = requests.post(url, headers=headers, data=payload)
        return "\n".join([item.get('snippet') for item in res.json().get('organic', [])])
    except: return "情报采集暂时受限。"

def get_quantitative_data(event):
    prompt = f"针对【{event}】推演T0,T24,T72,T7d分值。输出严格JSON: {{\"T0\":[40,30,20,10], \"T24\":[..], \"T72\":[..], \"T7d\":[..]}}"
    try:
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
        match = re.search(r'(\{.*\})', res.choices[0].message.content, re.DOTALL)
        return json.loads(match.group(1))
    except: return None

# --- 5. 主页面逻辑 ---
st.title("🔮 SHENCE (神策) | 多模态博弈推演沙盘")
event_input = st.text_area("📡 目标事件输入", placeholder="输入事件，激活四角色博弈辩论...", height=80)

if st.button("🚀 启动全维度深度推演"):
    if event_input:
        log_placeholder.code("INIT: 引擎初始化完成\nFETCH: 正在同步全球情报...")
        
        with st.status("🛠️ 正在进行系统推演...", expanded=True) as status:
            # 第一阶段：情报与量化
            intel = fetch_intel(event_input)
            st.write("📈 正在生成社会稳定风险量化数据...")
            time_data = get_quantitative_data(event_input)
            
            # 第二阶段：四角色轮番博弈
            st.write("🏛️ **官方战略室** 正在制定对策...")
            off_res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":f"事件:{event_input}\n情报:{intel}\n你代表官方出台对策。"}]).choices[0].message.content
            log_placeholder.code("RUN: 官方节点计算完成...")
            
            st.write("👥 **民众代表** 正在基于官方对策进行质疑与反馈...")
            cit_res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":f"官方对策：{off_res}\n你代表受影响民众，请提出真实诉求或质疑。"}]).choices[0].message.content
            log_placeholder.code("RUN: 民众节点计算完成...")
            
            st.write("📰 **深度媒体** 正在解析各方冲突点...")
            med_res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":f"官方：{off_res}\n民众：{cit_res}\n你代表媒体，请进行舆论定调。"}]).choices[0].message.content
            log_placeholder.code("RUN: 媒体节点计算完成...")
            
            st.write("🛡️ **风险官** 正在捕捉隐蔽风险点...")
            rsk_res = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":f"前三方：{off_res}{cit_res}{med_res}\n你代表风险官，指出次生灾害风险。"}]).choices[0].message.content
            log_placeholder.code("DONE: 全路径博弈完成")
            
            status.update(label="✅ 全维度博弈对撞完成", state="complete")

        # A. 趋势图展现
        if time_data:
            st.markdown("### 📈 社会稳定风险演化趋势")
            fig = go.Figure()
            names = ['官方压力', '民众情绪', '舆论热度', '整体风险']
            colors = ['#1565c0', '#2e7d32', '#ef6c00', '#c2185b']
            labels = ['当前', '24h爆发期', '72h博弈期', '7d演化期']
            for i in range(4):
                try:
                    y = [time_data['T0'][i], time_data['T24'][i], time_data['T72'][i], time_data['T7d'][i]]
                    fig.add_trace(go.Scatter(x=labels, y=y, name=names[i], line=dict(color=colors[i], width=4)))
                except: continue
            fig.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

        # B. 四角色彩色卡片展示
        st.markdown("---")
        st.markdown("### 🔄 智能体实时辩论摘要")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"<div class='role-card role-official'><span class='role-label'>🏛️ 官方决策<span class='model-badge'>GPT-4o</span></span>{off_res}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='role-card role-citizen'><span class='role-label'>👥 民众反应<span class='model-badge'>GPT-4o</span></span>{cit_res}</div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='role-card role-media'><span class='role-label'>📰 媒体定调<span class='model-badge'>GPT-4o</span></span>{med_res}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='role-card role-risk'><span class='role-label'>🛡️ 风险监测<span class='model-badge'>GPT-4o</span></span>{rsk_res}</div>", unsafe_allow_html=True)

        # C. 最终研判报告 (无图片)
        st.markdown("---")
        with st.spinner("正在整合多维度信息生成深度报告..."):
            final_report = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role":"user","content":f"整合以下博弈内容出具800字研判报告：{off_res}{cit_res}{med_res}{rsk_res}"}]
            ).choices[0].message.content

        st.markdown(f"""
            <div class='report-card'>
                <div class='report-header'>📝 神策深度研判总结报告</div>
                <div class='report-text'>{final_report}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.download_button("📥 导出研判报告", final_report, file_name="神策深度推演报告.txt")
