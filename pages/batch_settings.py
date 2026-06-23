import streamlit as st
from lib import db
from lib.theme import get_theme, apply_global_css, render_header
from lib.sidebar import render_common_sidebar
from lib.ui import section_header, info_banner

if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True

db.init_db()
T = get_theme()
apply_global_css(T)
render_header(T, subtitle="Batch Settings")

with st.sidebar:
    render_common_sidebar(T)

st.markdown(f"""
<div style="font-size:22px; font-weight:700; color:{T['text']}; margin-bottom:4px; letter-spacing:-0.02em;">Batch Settings</div>
<div style="font-size:13px; color:{T['muted']}; margin-bottom:18px;">A batch groups everything that shares the same solvent system — its blanks AND the samples redissolved in it. Create one batch per solvent system before uploading anything else.</div>
""", unsafe_allow_html=True)

info_banner(T, "💡 Example: if you redissolve Batch 1 in <b>n-hexane</b> and Batch 2 in <b>ethyl acetate</b>, create two separate batches — each gets its own blank pool.", T['accent'])

section_header(T, "Create new batch")
with st.form("new_batch_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Batch name", placeholder="e.g. Hexane Batch 1")
    with c2:
        solvent_system = st.text_input("Solvent system", placeholder="e.g. n-Hexane, HEX:IPA (3:2)")
    notes = st.text_input("Notes (optional)", placeholder="e.g. lard adulteration series, 1-50% w/w")
    submitted = st.form_submit_button("➕ Create Batch", width='stretch')
    if submitted:
        if not name.strip() or not solvent_system.strip():
            st.warning("Batch name and solvent system are required.")
        else:
            ok, msg = db.add_batch(name, solvent_system, notes)
            if ok:
                st.success(f"✅ Batch '{name}' created.")
                st.rerun()
            else:
                st.error(msg)

st.markdown(f"<div style='height:10px'></div>", unsafe_allow_html=True)
section_header(T, "Existing batches", "Each batch's blank pool is managed in the Blank Library page")

batches = db.list_batches()
if batches.empty:
    st.info("No batches yet — create one above to get started.")
else:
    for _, row in batches.iterrows():
        c1, c2, c3, c4 = st.columns([3, 3, 2, 1])
        c1.markdown(f"**{row['name']}**")
        c2.markdown(f"<span style='color:{T['muted']}; font-size:12px;'>{row['solvent_system']}</span>", unsafe_allow_html=True)
        c3.markdown(f"<span style='color:{T['muted']}; font-size:12px;'>{row['n_blanks']} blank file(s)</span>", unsafe_allow_html=True)
        if c4.button("🗑️", key=f"del_batch_{row['id']}", help="Delete batch and all its blanks"):
            st.session_state[f"confirm_del_{row['id']}"] = True
        if st.session_state.get(f"confirm_del_{row['id']}"):
            st.warning(f"Delete batch '{row['name']}' and all {row['n_blanks']} linked blank(s)? This cannot be undone.")
            cc1, cc2 = st.columns(2)
            if cc1.button("Yes, delete", key=f"yes_del_{row['id']}"):
                db.delete_batch(int(row['id']))
                st.session_state[f"confirm_del_{row['id']}"] = False
                st.rerun()
            if cc2.button("Cancel", key=f"no_del_{row['id']}"):
                st.session_state[f"confirm_del_{row['id']}"] = False
                st.rerun()
        if row['notes']:
            st.caption(f"📝 {row['notes']}")
        st.markdown("---")
