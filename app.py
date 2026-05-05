import streamlit as st
import pandas as pd
import io

# Setup Page Configuration
st.set_page_config(page_title="Lipid EQ", layout="wide")
st.title("Lipid EQ- Sorting & Cleaning")

# --- SIDEBAR CONTROL ---
st.sidebar.header("⚙️ Analytical Controls")

q_threshold = st.sidebar.slider(
    "Select NIST Quality Threshold", 50, 95, 80, 5,
)

rt_tolerance = st.sidebar.slider(
    "Select RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01,
)

area_threshold = st.sidebar.slider(
    "Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01,
)

st.markdown(f"""
---
### Standard Operating Procedure (SOP):
1. Metadata retained
2. Quality ≥ {q_threshold}
3. Area ≥ {area_threshold:.2f}%
4. RT tolerance ±{rt_tolerance}
---
""")

# --- UPDATED GOLD FUNCTION ---
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

    # 🔥 CAPTURE EXCLUDED BEFORE DROP
    df_excluded = df[df['Chemical_Status'] == "Discard (Artifact)"].copy()

    # ORIGINAL LOGIC
    df = df[df['Chemical_Status'] != "Discard (Artifact)"]
    df = df.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first')
    
    return df_header, df.sort_values(by='RT (min)'), df_excluded.sort_values(by='RT (min)')


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
    sample_file = st.file_uploader("Upload SAMPLE File", type=['xlsx'])
    blank_file = st.file_uploader("Upload BLANK File", type=['xlsx'])

    if sample_file and blank_file:
        try:
            h_s, df_s, ex_s = run_strict_procedure(sample_file, q_threshold, area_threshold)
            h_b, df_b, ex_b = run_strict_procedure(blank_file, q_threshold, area_threshold)

            res_s = df_s.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
            df_s['In_Blank'] = [x[0] for x in res_s]
            df_s['RT_Diff'] = [x[1] for x in res_s]

            df_final = df_s[df_s['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()

            # 🔥 NEW TAB SYSTEM
            t1, t2, t3, t4, t5 = st.tabs([
                "1. Blank",
                "2. Sample",
                "3. Final",
                "4. RT",
                "5. Excluded Compounds 🚫"
            ])

            with t1:
                st.dataframe(df_b)

            with t2:
                st.dataframe(df_s)

            with t3:
                st.dataframe(df_final)

            with t4:
                st.dataframe(df_s[df_s['In_Blank']=="RT_SHIFT_DETECTED"])

            # 🔥 NEW TAB CONTENT
            with t5:
                st.warning("These compounds were removed due to blacklist (artifact detection)")
                st.subheader("Sample Excluded")
                st.dataframe(ex_s)

                st.subheader("Blank Excluded")
                st.dataframe(ex_b)

            # --- EXPORT ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:

                # ORIGINAL
                df_b.to_excel(writer, sheet_name='Blank', index=False)
                df_s.to_excel(writer, sheet_name='Sample', index=False)
                df_final.to_excel(writer, sheet_name='Final', index=False)

                # 🔥 NEW SHEET
                ex_s.to_excel(writer, sheet_name='Excluded_Sample', index=False)
                ex_b.to_excel(writer, sheet_name='Excluded_Blank', index=False)

            st.download_button("Download Report", data=output.getvalue(), file_name="LipidEQ_Report.xlsx")

        except Exception as e:
            st.error(e)


with tab2:
    st.header("Multiple Files for PCA")

    m_blank = st.file_uploader("Upload ONE Blank File", type=['xlsx'])
    m_samples = st.file_uploader("Upload MULTIPLE Sample Files", type=['xlsx'], accept_multiple_files=True)

    if m_blank and m_samples:
        try:
            _, df_b_multi, _ = run_strict_procedure(m_blank, q_threshold, area_threshold)

            pca_list = []
            all_compounds = set()

            for s_f in m_samples:
                _, df_s_raw, _ = run_strict_procedure(s_f, q_threshold, area_threshold)

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

            pca_out = io.BytesIO()
            with pd.ExcelWriter(pca_out, engine='xlsxwriter') as writer:
                df_pca.to_excel(writer, sheet_name='PCA_Data', index=False)

            st.download_button("Download PCA Matrix", data=pca_out.getvalue(), file_name="PCA.xlsx")

        except Exception as e:
            st.error(e)
