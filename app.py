import streamlit as st
import pandas as pd
import io

# 🔥 GLOBAL STORE
EXCLUDED_STORE = {}

# Setup Page Configuration
st.set_page_config(page_title="Lipid EQ", layout="wide")
st.title("Lipid EQ- Sorting & Cleaning")

# --- SIDEBAR CONTROL ---
st.sidebar.header("⚙️ Analytical Controls")

q_threshold = st.sidebar.slider(
    "Select NIST Quality Threshold", 50, 95, 80, 5,
    help="**NIST Match Factor:** Filters compound identity accuracy. (Default: 80)"
)

rt_tolerance = st.sidebar.slider(
    "Select RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01,
    help="**Retention Time Buffer:** Time error limit for comparing Sample vs Blank.(Default: 0.05)"
)

area_threshold = st.sidebar.slider(
    "Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01,
    help="**Baseline Cut-off:** Removes small peaks/noise (Default: 0.00)."
)

st.markdown(f"""
---
### Standard Operating Procedure (SOP):
1.  **Metadata Preservation**: NIST headers (Rows 1–9) retained.
2.  **Quality Gate**: Filtering peaks with NIST Quality **≥ {q_threshold}**.
3.  **Noise Reduction**: Removing baseline peaks with Area **< {area_threshold:.2f}%**.
4.  **RT-Aware Matching**: Matching compounds using Name + RT Tolerance (**±{rt_tolerance} min**).
---
""")

# --- CODE EMAS ---
def run_strict_procedure(file, q_min, area_min):
    df_full_raw = pd.read_excel(file, sheet_name='LibRes', header=None)
    df_header = df_full_raw.iloc[0:9, :].copy()
    df = pd.read_excel(file, sheet_name='LibRes', header=8)
    df.columns = df.columns.str.strip()

    df = df.dropna(subset=['RT (min)', 'Area (Ab*s)']).copy()
    df['Quality'] = pd.to_numeric(df['Quality'], errors='coerce')

    total_area = df['Area (Ab*s)'].sum()
    df['Area (%)'] = (df['Area (Ab*s)'] / total_area) * 100
    df = df[(df['Quality'] >= q_min) & (df['Area (%)'] >= area_min)]

    blacklist = ['siloxane', 'phthalate', 'octaxilonaxe', 'bleed', 'plasticizer', 'adipate', 'column bleed']
    contaminants = ['iodo', 'chloro', 'bromo', 'fluoro', 'iodide', 'chloride', 'thiophene', 'benzo', 'benza', 'cyclo', 'sulphur', 'benzothiophene', 'naphthalene', 'benzene,']

    def classify_compound(name):
        n = str(name).lower()
        if any(x in n for x in blacklist): return "Discard (Artifact)"
        if any(x in n for x in contaminants): return "Review (Potential Contaminant)"
        return "Clean (Lipid/Oxidation)"

    df['Chemical_Status'] = df['Hit Name'].apply(classify_compound)

    # 🔥 capture excluded
    EXCLUDED_STORE[file.name] = df[df['Chemical_Status'] == "Discard (Artifact)"].copy()

    df = df[df['Chemical_Status'] != "Discard (Artifact)"]
    df = df.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first')

    return df_header, df.sort_values(by='RT (min)')


def check_match_expert(row, target_df, tol):
    matches = target_df[target_df['Hit Name'] == row['Hit Name']]
    if matches.empty: return "NO", None
    for _, t_row in matches.iterrows():
        diff = abs(row['RT (min)'] - t_row['RT (min)'])
        if diff <= tol: return "YES", diff
    closest_diff = matches.apply(lambda r: abs(row['RT (min)'] - r['RT (min)']), axis=1).min()
    return "RT_SHIFT_DETECTED", closest_diff


# --- TAB SYSTEM ---
tab1, tab2 = st.tabs(["Single File (Detail)", "Multiple Files (for PCA)"])

with tab1:
    st.warning("⚠️ **IMPORTANT**: Please ensure your files are in **.xlsx** format.")
    col1, col2 = st.columns(2)
    with col1:
        sample_file = st.file_uploader("Upload SAMPLE File (.xlsx only)", type=['xlsx'], key="s_file")
    with col2:
        blank_file = st.file_uploader("Upload BLANK File (.xlsx only)", type=['xlsx'], key="b_file")

    if sample_file and blank_file:
        try:
            h_s, df_s = run_strict_procedure(sample_file, q_threshold, area_threshold)
            h_b, df_b = run_strict_procedure(blank_file, q_threshold, area_threshold)

            res_s = df_s.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
            df_s['In_Blank'] = [x[0] for x in res_s]
            df_s['RT_Diff'] = [x[1] for x in res_s]

            res_b = df_b.apply(lambda r: check_match_expert(r, df_s, rt_tolerance), axis=1)
            df_b['In_Sample'] = [x[0] for x in res_b]

            df_final = df_s[df_s['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()

            # Tabs
            t1, t2, t3, t4, t5 = st.tabs([
                "1. Solvent Blank",
                "2. Sample Mapping",
                "3. Final Fingerprint",
                "4. RT Analysis",
                "5. Excluded Compounds 🚫"
            ])

            with t1:
                def highlight_blank(row):
                    styles = ['' for _ in row.index]
                    if row['In_Sample'] == "YES": styles = ['background-color: #FFEB9C' for _ in row.index]
                    elif row['In_Sample'] == "RT_SHIFT_DETECTED":
                        rt_idx = row.index.get_loc('RT (min)')
                        styles[rt_idx] = 'background-color: #002060; color: white'
                    return styles
                st.dataframe(df_b.style.apply(highlight_blank, axis=1))

            with t2:
                def highlight_sample(row):
                    styles = ['' for _ in row.index]
                    if row['In_Blank'] == "YES": styles = ['background-color: #FFEB9C' for _ in row.index]
                    elif row['In_Blank'] == "RT_SHIFT_DETECTED":
                        rt_idx = row.index.get_loc('RT (min)')
                        styles[rt_idx] = 'background-color: #002060; color: white'
                    return styles
                st.dataframe(df_s.style.apply(highlight_sample, axis=1))

            with t3:
                st.dataframe(df_final.drop(columns=['In_Blank', 'RT_Diff']))

            with t4:
                st.dataframe(df_s[df_s['In_Blank'] == "RT_SHIFT_DETECTED"])

            with t5:
                st.dataframe(EXCLUDED_STORE.get(sample_file.name, pd.DataFrame()))

            # Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                wb = writer.book
                yellow_fmt = wb.add_format({'bg_color': '#FFEB9C'})
                navy_fmt = wb.add_format({'bg_color': '#002060', 'font_color': 'white'})
                pink_fmt = wb.add_format({'bg_color': '#FFC0CB'})
                red_fmt = wb.add_format({'bg_color': '#FF0000', 'font_color': 'white'})

                df_b.to_excel(writer, sheet_name='Report', index=False)
                df_s.to_excel(writer, sheet_name='Report', startrow=len(df_b)+5, index=False)
                df_final.to_excel(writer, sheet_name='Report', startrow=len(df_b)+len(df_s)+10, index=False)

                ws = writer.sheets['Report']

                # restore coloring
                b_match_idx = df_b.columns.get_loc('In_Sample')
                ws.conditional_format(1,0,len(df_b),len(df_b.columns)-1,
                    {'type':'formula','criteria':f'=${chr(65+b_match_idx)}2="YES"','format':yellow_fmt})

                # excluded section
                ex = EXCLUDED_STORE.get(sample_file.name, pd.DataFrame())
                start_ex = len(df_b)+len(df_s)+len(df_final)+20
                ex.to_excel(writer, sheet_name='Report', startrow=start_ex, index=False)

                if not ex.empty:
                    ex_status_idx = ex.columns.get_loc('Chemical_Status')
                    ws.conditional_format(start_ex, ex_status_idx,
                        start_ex+len(ex), ex_status_idx,
                        {'type':'cell','criteria':'equal to','value':'"Discard (Artifact)"','format':red_fmt})

            st.download_button("Download Report", output.getvalue(), "LipidEQ.xlsx")

        except Exception as e:
            st.error(e)


with tab2:
    st.header("Multiple Files for PCA")
    m_blank = st.file_uploader("Upload ONE Blank File", type=['xlsx'])
    m_samples = st.file_uploader("Upload MULTIPLE Sample Files", type=['xlsx'], accept_multiple_files=True)

    if m_blank and m_samples:
        _, df_b_multi = run_strict_procedure(m_blank, q_threshold, area_threshold)

        pca_list = []
        all_compounds = set()

        for s_f in m_samples:
            _, df_s_raw = run_strict_procedure(s_f, q_threshold, area_threshold)
            res = df_s_raw.apply(lambda r: check_match_expert(r, df_b_multi, rt_tolerance), axis=1)
            df_clean = df_s_raw[res.apply(lambda x: x[0] in ["NO", "RT_SHIFT_DETECTED"])]

            s_dict = {row['Hit Name']: row['Area (Ab*s)'] for _, row in df_clean.iterrows()}
            s_dict['Sample Name'] = s_f.name

            pca_list.append(s_dict)
            all_compounds.update(df_clean['Hit Name'].tolist())

        df_pca = pd.DataFrame(pca_list)
        cols = ['Sample Name'] + sorted(list(all_compounds))
        df_pca = df_pca.reindex(columns=cols).fillna(0)

        st.dataframe(df_pca)
