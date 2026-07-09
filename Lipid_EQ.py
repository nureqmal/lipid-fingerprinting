import streamlit as st
from lib import db

st.set_page_config(page_title="Lipid EQ", layout="wide", page_icon="⚗️")

if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True

db.init_db()

# All titles/icons are set here in code (not in filenames) so they can
# never be corrupted by a host's file-upload pipeline mangling unicode
# filenames — that was the root cause of the earlier broken sidebar /
# "page not found" error.
pg = st.navigation([
    st.Page("pages/home.py", title="Home", icon="⚗️", default=True),
    st.Page("pages/pipeline.py", title="Pipeline", icon="🧪"),
    st.Page("pages/blank_library.py", title="Blank Library", icon="📦"),
    st.Page("pages/batch_settings.py", title="Batch Settings", icon="⚙️"),
])
pg.run()
