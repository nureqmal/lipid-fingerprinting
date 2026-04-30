if sample_file and blank_file:
    try:
        # ... kod proses data kau kat sini ...
        # ... kod metrics/table kau kat sini ...

        # --- START PREMIUM EXCEL EXPORT ---
        # Pastikan baris bawah ni sejajar dengan kod 'st.subheader' atau 'st.table' kat atas dia
        output = io.BytesIO() 
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            wb = writer.book
            
            # --- 1. DEFINE PREMIUM FORMATS ---
            fmt_header = wb.add_format({'bold': True, 'font_size': 14, 'font_color': 'white', 'bg_color': '#1F4E78', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            # ... sambung kod formats yang lain ...
            
            # --- 2. DASHBOARD SHEET ---
            ws_dash = wb.add_worksheet('Executive Summary')
            # ... sambung kod dashboard ...

            # --- 3. ANALYTICAL REPORT SHEET ---
            rs = 'Validated_Fingerprint'
            ws_rep = wb.add_worksheet(rs)
            # ... sambung kod report ...

        # Butang download pun kena sejajar dalam blok try
        st.download_button("📥 Download Premium Analytical Report", output.getvalue(), "LipidExpert_Premium_Report.xlsx")

    except Exception as e:
        st.error(f"Error: {e}")
