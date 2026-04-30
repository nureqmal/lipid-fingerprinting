import streamlit as st
import pandas as pd
import io
import matplotlib.pyplot as plt

# --- 1. THEME & BRANDING ---
st.set_page_config(page_title="LipidExpert | High-Integrity Authentication", layout="wide")

# Custom CSS for Professional Look
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #f1f3f5; border-radius: 4px 4px 0px 0px; padding: 10px 20px;
    }
    </style>
    """, unsafe_allow_name_with_html=True)

st.title("🧪 LipidExpert: Professional Analytical Suite")

# --- 2. SIDEBAR ENHANCEMENTS ---
st.sidebar.header("📋 Project Information")
researcher_name = st.sidebar.text_input("Researcher Name", "Dr. Eqmal")
project_title = st.sidebar.text_input("Project Title", "Halal Lipidomics Study")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Analytical Controls")
q_threshold = st.sidebar.slider("NIST Quality Threshold", 50, 95, 80, 5)
rt_tol = st.sidebar.number_input("RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01)

st.markdown(f"""
**Project:** {project_title} | **Analyst:** {researcher_name}
---
### Standard Operating Procedure (SOP):
1. **Quality Gate:** Minimum NIST Match ≥ {q_threshold}.
2. **Artifact Purge:** Removal of column/instrument bleeding markers.
3. **Strict Authentication:** 100% removal of peaks matching Solvent Blank within ±{rt_tol} min.
---
""")

def process_data(file, threshold):
    df_raw = pd.read_excel(file, sheet_name='LibRes', header=None)
    header = df_raw.iloc[0:9, :].copy()
    data = pd.read_excel(file, sheet_name='LibRes', header=8)
    data.columns = data.columns.str.strip()
    
    clean = data.dropna(subset=['RT (min)', 'Area (Ab*s)']).copy()
    clean['Quality'] = pd.to_numeric(clean['Quality'], errors='coerce')
    clean = clean[clean['Quality'] >= threshold]
    
    blacklist = ['siloxane', 'phthalate', 'octaxilonaxe', 'bleed', 'plasticizer', 'adipate', 'column bleed']
    def classify(name):
        n = str(name).lower()
        if any(x in n for x in blacklist): return "Discard"
        return "Clean Lipid"

    clean['Status'] = clean['Hit Name'].apply(classify)
    clean = clean[clean['Status'] != "Discard"]
    clean = clean.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first')
    return header, clean.sort_values(by='RT (min)')

# --- 3. EXECUTION ---
col_u1, col_u2 = st.columns(2)
with col_u1: sample_f = st.file_uploader("Upload SAMPLE File", type=['xlsx'])
with col_u2: blank_f = st.file_uploader("Upload BLANK File", type=['xlsx'])

if sample_f and blank_f:
    h_s, df_s = process_data(sample_f, q_threshold)
    h_b, df_b = process_data(blank_f, q_threshold)

    def match_logic(row, ref_df):
        m = ref_df[ref_df['Hit Name'] == row['Hit Name']]
        for _, r in m.iterrows():
            if abs(row['RT (min)'] - r['RT (min)']) <= rt_tol: return "YES"
        return "NO"

    df_s['In_Blank'] = df_s.apply(lambda r: match_logic(r, df_b), axis=1)
    df_b['In_Sample'] = df_b.apply(lambda r: match_logic(r, df_s), axis=1)
    df_final = df_s[df_s['In_Blank'] == "NO"].copy()

    # --- 4. DASHBOARD & VISUALS ---
    st.subheader("📊 Executive Metrics")
    c1, c2, c3, c4 = st.columns(4)
    total, excl = len(df_s), len(df_s[df_s['In_Blank']=="YES"])
    c1.metric("Total Peaks", total)
    c2.metric("Excluded", excl, delta=f"-{excl}", delta_color="inverse")
    c3.metric("Final Unique", len(df_final))
    c4.metric("Purity Score", f"{(len(df_final)/total*100):.1f}%" if total > 0 else "0%")

    v1, v2 = st.columns([1, 2])
    with v1:
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.pie([len(df_final), excl], labels=['Unique', 'Blank-Matched'], autopct='%1.1f%%', 
               startangle=90, colors=['#2E75B6', '#dee2e6'], wedgeprops={'width': 0.5})
        ax.set_title("Data Integrity Composition")
        st.pyplot(fig)
    with v2:
        st.info(f"**Interpretation:** Analysis successfully identified **{len(df_final)}** unique biomarkers. "
                f"The exclusion of {excl} peaks ensures the profile is free from solvent artifacts.")

    # --- 5. TABS & EXPORT ---
    t1, t2, t3 = st.tabs(["Solvent Blank", "Sample Mapping", "Unique Fingerprint"])
    with t1: st.dataframe(df_b.style.apply(lambda x: ['background: #fff9db' if x['In_Sample']=='YES' else '' for _ in x], axis=1))
    with t2: st.dataframe(df_s.style.apply(lambda x: ['background: #fff9db' if x['In_Blank']=='YES' else '' for _ in x], axis=1))
    with t3: st.dataframe(df_final.drop(columns=['In_Blank']))

    # Final Professional Export
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Dashboard
        ws_d = writer.book.add_worksheet('Summary')
        fmt = writer.book.add_format({'bold':True, 'bg_color':'#2E75B6', 'font_color':'white', 'border':1})
        ws_d.write('B2', 'PROJECT SUMMARY', fmt)
        ws_d.write('B3', 'Project Name'); ws_d.write('C3', project_title)
        ws_d.write('B4', 'Analyst'); ws_d.write('C4', researcher_name)
        ws_d.write('B5', 'Unique Biomarkers'); ws_d.write('C5', len(df_final))
        
        # Report (Logic based on previous stable versions)
        rs = 'Analytical_Report'
        h_b.to_excel(writer, sheet_name=rs, startrow=1, index=False, header=False)
        df_b.to_excel(writer, sheet_name=rs, startrow=10, index=False, header=False)
        s2 = len(df_b) + 15
        h_s.to_excel(writer, sheet_name=rs, startrow=s2+1, index=False, header=False)
        df_s.to_excel(writer, sheet_name=rs, startrow=s2+10, index=False, header=False)
        s3 = s2 + len(df_s) + 15
        fh = h_s.copy(); fh.iloc[0,0] = f"{fh.iloc[0,0]} (CORRECTED UNIQUE)"
        fh.to_excel(writer, sheet_name=rs, startrow=s3+1, index=False, header=False)
        df_final.drop(columns=['In_Blank']).to_excel(writer, sheet_name=rs, startrow=s3+10, index=False, header=False)
        
        # Add Excel Formatting (Highlighting)
        wb, ws = writer.book, writer.sheets[rs]
        y_fmt = wb.add_format({'bg_color': '#fff9db'})
        ws.conditional_format(10, 0, 10+len(df_b), 20, {'type':'formula', 'criteria':f'=${chr(65+len(df_b.columns)-1)}11="YES"', 'format':y_fmt})
        ws.conditional_format(s2+10, 0, s2+10+len(df_s), 20, {'type':'formula', 'criteria':f'=${chr(65+len(df_s.columns)-1)}{s2+11}="YES"', 'format':y_fmt})

    st.download_button("📥 Download Executive Report", output.getvalue(), f"{project_title}_Report.xlsx")
