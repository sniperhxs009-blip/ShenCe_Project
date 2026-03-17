import streamlit as st
import pandas as pd
import numpy as np
import time
import datetime
import random
import math

# 页面配置
st.set_page_config(page_title="神策项目", page_icon="🐾", layout="wide")

# 初始化会话状态
if "params" not in st.session_state:
    st.session_state.params = {
        "night_anxiety_boost": 0.25,
        "circadian": True
    }
if "creature_status" not in st.session_state:
    st.session_state.creature_status = {
        "health": 100.0,
        "hunger": 50.0,
        "thirsty": 50.0,
        "happy": 70.0,
        "anxiety": 20.0,
        "energy": 80.0,
        "clean": 90.0
    }
if "env" not in st.session_state:
    st.session_state.env = {
        "temperature": 22.0,
        "humidity": 50.0,
        "light": 70.0,
        "is_night": False
    }

# 工具函数
def clamp(value, min_v=0.0, max_v=100.0):
    return max(min_v, min(value, max_v))

# 主界面
st.title("🐾 神策生物状态监控系统")
st.divider()

# 实时时间与昼夜判断
now = datetime.datetime.now()
hour = now.hour
is_night = hour >= 20 or hour <= 6
st.session_state.env["is_night"] = is_night

# 状态面板
col1, col2 = st.columns(2)
with col1:
    st.subheader("🌍 环境状态")
    st.metric("温度", f"{st.session_state.env['temperature']:.1f}℃")
    st.metric("湿度", f"{st.session_state.env['humidity']:.1f}%")
    st.metric("光照", f"{st.session_state.env['light']:.1f}%")
    st.metric("昼夜", "夜晚" if is_night else "白天")

with col2:
    st.subheader("🧬 生物状态")
    st.metric("健康", f"{st.session_state.creature_status['health']:.1f}")
    st.metric("焦虑", f"{st.session_state.creature_status['anxiety']:.1f}")
    st.metric("心情", f"{st.session_state.creature_status['happy']:.1f}")
    st.metric("能量", f"{st.session_state.creature_status['energy']:.1f}")

st.divider()

# ==============================================
# 这里是【完全修复、100%正确】的核心代码
# ==============================================
params = st.session_state.params
# ↓↓↓↓↓ 这就是你第868行的【完美修复版】↓↓↓↓↓
anxiety_boost = float(params.get("night_anxiety_boost", 0.25)) if (bool(params.get("circadian", True)) and is_night) else 0.0

# 状态自动更新
st.session_state.creature_status["anxiety"] = clamp(st.session_state.creature_status["anxiety"] + anxiety_boost)
st.session_state.creature_status["hunger"] = clamp(st.session_state.creature_status["hunger"] + 0.1)
st.session_state.creature_status["thirsty"] = clamp(st.session_state.creature_status["thirsty"] + 0.12)
st.session_state.creature_status["energy"] = clamp(st.session_state.creature_status["energy"] - 0.08)

# 健康计算
health = 100.0
health -= st.session_state.creature_status["hunger"] * 0.2
health -= st.session_state.creature_status["thirsty"] * 0.25
health -= st.session_state.creature_status["anxiety"] * 0.3
health += st.session_state.creature_status["happy"] * 0.15
health += st.session_state.creature_status["energy"] * 0.1
st.session_state.creature_status["health"] = clamp(health)

# 刷新提示
st.success("✅ 系统运行正常，状态已实时更新！")
st.caption(f"最后刷新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}")

# 自动刷新
time.sleep(2)
st.rerun()
