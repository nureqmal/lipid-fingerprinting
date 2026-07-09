"""Shared sidebar block: theme toggle + blacklist manager.

Rendered at the top of every page's sidebar so behaviour (and persisted
blacklist) stays consistent app-wide. Page-specific controls (quality
threshold, RT tolerance, batch pickers, etc.) are added by each page
*after* calling render_common_sidebar().
"""

import streamlit as st
from lib import db


def render_common_sidebar(T):
    st.markdown(f"""
    <div style="padding:4px 0 12px;">
        <div style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:{T['accent']}; margin-bottom:2px;">⚗️ Lipid EQ</div>
        <div style="font-size:10px; color:{T['muted']};">Analytical Control Panel</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"<div style='font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:{T['muted']}; margin-bottom:6px;'>Display</div>", unsafe_allow_html=True)
    toggle_label = "Switch to Light Mode ☀️" if st.session_state.get('dark_mode', True) else "Switch to Dark Mode 🌙"
    if st.button(toggle_label, width='stretch', key="theme_toggle"):
        st.session_state.dark_mode = not st.session_state.get('dark_mode', True)
        st.rerun()

    st.markdown("---")
    st.markdown(f"<div style='font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:{T['muted']}; margin-bottom:4px;'>🚫 Blacklist Manager</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:10px; color:{T['muted']}; margin-bottom:10px;'>Compounds whose name contains any keyword below are excluded as artifacts. Persisted in SQLite — shared across all pages.</div>", unsafe_allow_html=True)

    blacklist = db.get_blacklist()
    st.markdown(f"<div style='font-size:11px; font-weight:600; color:{T['text']}; margin-bottom:6px;'>Active keywords ({len(blacklist)})</div>", unsafe_allow_html=True)
    for kw in blacklist:
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"""
        <div style="background:{T['bg3']}; border:1px solid {T['border']}; border-radius:6px;
            padding:4px 10px; font-size:11px; color:{T['text']}; margin-bottom:2px;">
            {kw}
        </div>""", unsafe_allow_html=True)
        if c2.button("✕", key=f"rm_{kw}", help=f"Remove '{kw}'"):
            db.remove_blacklist_keyword(kw)
            st.rerun()

    st.markdown(f"<div style='font-size:11px; font-weight:600; color:{T['text']}; margin:10px 0 4px;'>Add keyword</div>", unsafe_allow_html=True)
    new_kw = st.text_input("New keyword", placeholder="e.g. trimethylsilyl", label_visibility="collapsed", key="new_kw")
    if st.button("➕ Add to Blacklist", width='stretch'):
        cleaned = new_kw.strip().lower()
        if not cleaned:
            st.warning("Enter a keyword first.")
        elif cleaned in blacklist:
            st.warning(f"'{cleaned}' already exists.")
        else:
            db.add_blacklist_keyword(cleaned)
            st.success(f"✅ '{cleaned}' added!")
            st.rerun()

    st.markdown("")
    if st.button("↺ Reset to Default", width='stretch', key="reset_bl"):
        db.reset_blacklist()
        st.rerun()

    st.markdown("---")
    return blacklist
