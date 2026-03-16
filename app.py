import streamlit as st
from openai import OpenAI
import requests
import json
import plotly.graph_objects as go
import re

# --- 1. 页面配置 ---
st.set_page_config(page_title="神策 - 四角色博弈推演沙盘", layout="wide")

# --- 2. 界面样式配置 (核心修复：恢复彩色背景，优化视觉) ---
st.markdown("""
    <style>
    /* 整体背景与文字颜色优化，不再是纯黑 */
    .main { background-color: #f0f2f5; color: #333; }
    
    /* 角色卡片通用样式 */
    .role-card {
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        border: 1px solid rgba(0,0,0,0.05);
    }
    .role-label {
        font-weight: bold;
        font-size: 1.3rem;
        margin-bottom: 15px;
        display: block;
        border-bottom: 2px solid;
        padding-bottom: 5px;
    }
    .role-content {
        line-height: 1.7;
        font-size: 1rem;
    }

    /* 核心修复：四个角色的专属彩色背景 */
    .role-official { background-color: #e3f2fd; border-color: #90caf9; } /* 蓝色 - 官方 */
    .role-official .role-label { color: #1565c0; border-color: #1565c0; }

    .role-citizen { background-color: #e8f5e9; border-color: #a5d6a7; } /* 绿色 - 民众 */
    .role-citizen .role-label { color: #2e7d32; border-color: #2e7d32; }

    .role-media { background-color: #fff3e0; border-color: #ffcc80; } /* 橙色 - 媒体 */
    .role-media .role-label { color: #ef6c00; border-color: #ef6c00; }

    .role-risk { background-color: #fce4ec; border-color: #f48fb1; } /* 粉色 - 风险官 */
    .role-risk .role-label { color: #c2185b; border-color: #c2185b; }

    /* 研判报告卡片样式 */
    .report-card {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 15px;
        border: 2px solid #9575cd;
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        margin-top: 25px;
    }
    .report-header {
        color: #512da8;
        font-size: 1.8rem;
        font-weight: bold;
        margin-bottom: 20px;
        text-align: center;
    }
    .report-text {
        line-height: 1.8;
        font-size: 1.1rem;
        color: #444;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 密钥配置 (硬编码整合 Secret Key 用于文本博弈) ---
# 核心修复：仅保留文本博弈所需的 Key，图片生成的 Key 已移除
SECRET_KEY = "sk-LMB9VBTefa210eFC3581T3BLbkFJB0a3Bc8553a8406eb3B3"
BASE_URL = "https://api.ohmygpt.com/v1"

# 从 Secrets 获取 Serper Key (用于联网搜索)
try:
    SERPER_K = st.secrets["SERPER_API_KEY"]
except:
    st.error("❌ 缺少 SERPER_API_KEY，请在 Streamlit 云端 Secrets 中配置。")
    st.stop()

# 初始化文本博弈客户端 (使用兼容性最好的 gpt-4o)
client = OpenAI(api_key=SECRET_KEY, base_url=BASE_URL)
MAIN_MODEL = "gpt-4o" 

# --- 4. 核心功能函数 ---
def fetch_intelligence(query):
    """联网采集实时情报"""
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": f"{query} 最新政策 现状 影响", "gl": "cn", "hl": "zh-cn", "num": 8})
    headers = {'X-API-KEY': SERPER_K, 'Content-Type': 'application/json'}
    try:
        res = requests.post(url, headers=headers, data=payload)
        return "\n".join([item.get('snippet') for item in res.json().get('organic', [])])
    except: return "实时情报采集暂时受限，将基于大模型基础知识进行推演。"

def get_time_series_data(event):
    """生成量化推演数据"""
    prompt = f"针对事件【{event}】推演当前(T0)、24小时爆发期(T24)、72小时博弈期(T72)、7天演化期(T7d)四个阶段的官方压力、民众情绪、舆论热度、整体风险分值(0-100)。严格输出JSON格式: {{\"T0\":[40,30,20,10], \"T24\":[..], \"T72\":[..], \"T7d\":[..]}}"
    try:
        response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user", "content":prompt}])
        match = re.search(r'(\{.*\})', response.choices[0].message.content, re.DOTALL)
        return json.loads(match.group(1)) if match else None
    except: return None

# --- 5. 界面逻辑 ---
st.title("🔮 SHENCE (神策) | 四角色博弈推演沙盘")
st.markdown("---")

event_input = st.text_area("📡 目标事件输入", placeholder="请输入需要进行深度博弈推演的事件...", height=100)

if st.button("🚀 启动全维度博弈推演"):
    if event_input:
        with st.spinner("🕵️ 正在采集情报并激活各方智能体进行博弈对撞..."):
            # 1. 情报采集与数据生成
            intel = fetch_intelligence(event_input)
            time_data = get_time_series_data(event_input)

        # A. 趋势图展示
        if time_data:
            st.markdown("### 📈 社会稳定风险演化趋势")
            labels = ['当前', '24h爆发', '72h博弈', '7d演化']
            fig = go.Figure()
            colors = ['#1565c0', '#2e7d32', '#ef6c00', '#c2185b'] # 对应四个角色的颜色
            names = ['官方压力', '民众情绪', '舆论热度', '整体风险']
            for i in range(4):
                try:
                    y_val = [time_data['T0'][i], time_data['T24'][i], time_data['T72'][i], time_data['T7d'][i]]
                    fig.add_trace(go.Scatter(x=labels, y=y_val, name=names[i], line=dict(color=colors[i], width=4), mode='lines+markers'))
                except: continue
            fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#333", margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)

        # B. 核心修复：四角色彩色博弈辩论 (轮番对撞)
        st.markdown("---")
        st.markdown("### 🔄 智能体多轮博弈辩论对撞")
        
        try:
            with st.status("各方智能体正在激烈博弈辩论中...", expanded=True) as status:
                # 1. 官方视角：出台对策
                st.write("🏛️ **官方战略室** 正在制定应对策...")
                off_res = client.chat.completions.create(model=MAIN_MODEL, messages=[{"role":"user","content":f"事件:{event_input}\n最新情报:{intel}\n你代表官方，请出台具体的应对战略和对策。"}]).choices[0].message.content
                
                # 2. 民众视角：对官方对策提出反馈/质疑
                st.write("👥 **受影响民众** 正在评估官方对策并给出反馈...")
                cit_res = client.chat.completions.create(model=MAIN_MODEL, messages=[{"role":"user","content":f"事件:{event_input}\n官方出台对策：{off_res}\n你代表受影响民众，请给出你们的真实反馈、诉求或质疑。"}]).choices[0].message.content
                
                # 3. 媒体视角：分析双方冲突，进行舆论定调
                st.write("📰 **深度媒体** 正在分析局势进行舆论定调...")
                med_res = client.chat.completions.create(model=MAIN_MODEL, messages=[{"role":"user","content":f"官方对策：{off_res}\n民众反馈：{cit_res}\n你代表深度媒体，请分析双方的冲突点，指出局势的关键，并进行舆论定调。"}]).choices[0].message.content
                
                # 4. 风险官视角：审视前三方，指出潜在次生风险
                st.write("🛡️ **首席风险官** 正在进行整体风险审视...")
                rsk_res = client.chat.completions.create(model=MAIN_MODEL, messages=[{"role":"user","content":f"官方对策：{off_res}\n民众反馈：{cit_res}\n媒体定调：{med_res}\n你代表首席风险官，请审视前三方的观点和局势演化，指出当前最隐蔽的潜在风险和次生灾害。"}]).choices[0].message.content
                
                status.update(label="✅ 多轮博弈辩论完成", state="complete")

            # 界面展示：恢复四角色彩色卡片布局
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""<div class='role-card role-official'><span class='role-label'>🏛️ 官方决策</span><div class='role-content'>{off_res}</div></div>""", unsafe_allow_html=True)
                st.markdown(f"""<div class='role-card role-citizen'><span class='role-label'>👥 民众反应</span><div class='role-content'>{cit_res}</div></div>""", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""<div class='role-card role-media'><span class='role-label'>📰 媒体定调</span><div class='role-content'>{med_res}</div></div>""", unsafe_allow_html=True)
                st.markdown(f"""<div class='role-card role-risk'><span class='role-label'>🛡️ 风险风险</span><div class='role-content'>{rsk_res}</div></div>""", unsafe_allow_html=True)

            # C. 最终深度研判报告 (不生成图片)
            st.markdown("---")
            with st.spinner("正在整合博弈辩论内容，撰写最终深度研判报告..."):
                final_report = client.chat.completions.create(
                    model=MAIN_MODEL,
                    messages=[{"role":"user","content":f"请全面整合以上四方（官方、民众、媒体、风险官）的博弈辩论内容和核心观点，出具一份800字左右的专业、深度的最终研判报告。不要生成图片描述。"}]
                ).choices[0].message.content

            # 核心修复：取消图片生成功能，仅展示报告
            st.markdown(f"""
                <div class='report-card'>
                    <div class='report-header'>📝 神策深度研判总结报告</div>
                    <div class='report-text'>{final_report}</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button("📥 导出研判报告", final_report, file_name="神策深度推演报告.txt")

        except Exception as e:
            st.error(f"❌ 博弈流程因未知错误中断，请检查 OhMyGPT 余额或 API 状态：{e}")
else:
    st.info("💡 请在上方输入框输入研判事件并点击启动，系统将呈现各方激烈博弈辩论的全过程。")
