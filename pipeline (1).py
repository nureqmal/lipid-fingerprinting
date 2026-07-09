"""Tiny presentational helpers shared across pages."""

import streamlit as st


def section_header(T, title, subtitle=""):
    st.markdown(f"""
    <div style="margin:18px 0 10px;">
        <div style="font-size:14px; font-weight:700; color:{T['text']};">{title}</div>
        {f'<div style="font-size:11px; color:{T["muted"]}; margin-top:2px;">{subtitle}</div>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def info_banner(T, msg, color=None):
    c = color or T['accent']
    st.markdown(f"""
    <div style="background:{c}15; border:1px solid {c}40; border-radius:10px;
        padding:10px 16px; font-size:12px; color:{T['text']}; margin-bottom:10px; line-height:1.6;">
        {msg}
    </div>
    """, unsafe_allow_html=True)
