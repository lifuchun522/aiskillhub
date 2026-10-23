"""Streamlit 界面 —— 控件文案就是产品经理视角的功能清单。"""
import streamlit as st

st.title("DemoClip")
st.text_input("视频主题", "最小可跑示例")
st.text_area("视频脚本（手填可跳过 LLM）")
st.selectbox("配音音色", ["edge-zh-CN-Xiaoxiao", "azure-zh-CN-Yunxi"])
st.selectbox("素材来源", ["local", "pexels"])
st.slider("字幕字号", 12, 72, 36)
st.button("生成视频")
