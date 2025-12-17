#!/usr/bin/env python3
"""
Aplicación standalone para procesar catálogos de cuentas y pólizas para CONTPAQi
"""

import streamlit as st
import os
import sys
import subprocess
import re
from pathlib import Path
import tempfile
import shutil
import base64

# Configuración de rutas
script_dir = Path(__file__).parent.absolute()
accounts_scripts_dir = script_dir.parent / "CuentasOdooToContpaqi"
policies_scripts_dir = script_dir.parent / "PolizasOdooToContpaqi"

# Cargar logo como base64
logo_path = script_dir / "logo.png"
logo_base64 = ""
if logo_path.exists():
    with open(logo_path, "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode()

# Configuración de página
st.set_page_config(
    page_title="EQIDIS - Procesador CONTPAQi",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personalizado - Tema claro y compacto
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    .stApp { background: #f8fafc; }
    
    /* Header compacto */
    .header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px 0;
        border-bottom: 1px solid #e2e8f0;
        margin-bottom: 16px;
    }
    .header img { height: 32px; width: auto; }
    .header h1 {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e293b;
        margin: 0;
    }
    .header span {
        font-size: 0.85rem;
        color: #64748b;
        margin-left: auto;
    }
    
    /* Tabs más compactos */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #fff;
        padding: 4px;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    .stTabs [data-baseweb="tab"] {
        height: 36px;
        border-radius: 6px;
        color: #64748b;
        font-weight: 500;
        font-size: 0.9rem;
        padding: 0 16px;
    }
    .stTabs [aria-selected="true"] {
        background: #6366f1 !important;
        color: white !important;
    }
    
    /* Cards compactas */
    .card {
        background: #fff;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #e2e8f0;
        margin-bottom: 12px;
    }
    .card-header {
        font-size: 1rem;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Botones */
    .stButton > button {
        background: #6366f1;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 500;
        font-size: 0.9rem;
    }
    .stButton > button:hover {
        background: #4f46e5;
    }
    
    .stDownloadButton > button {
        background: #10b981;
        color: white;
        border: none;
        border-radius: 6px;
    }
    .stDownloadButton > button:hover { background: #059669; }
    
    /* File uploader compacto */
    .stFileUploader > div > div {
        padding: 8px !important;
    }
    .stFileUploader label { font-size: 0.85rem !important; }
    
    /* Checkbox y inputs */
    .stCheckbox label { font-size: 0.9rem; color: #374151; }
    .stNumberInput label { font-size: 0.85rem; color: #374151; }
    
    /* Reducir espaciado general */
    .block-container { padding: 1rem 2rem !important; max-width: 1400px; }
    .stMarkdown { margin-bottom: 0 !important; }
    h4 { font-size: 0.95rem !important; color: #374151 !important; margin: 8px 0 !important; }
    
    /* Ocultar elementos Streamlit */
    #MainMenu, footer, header { visibility: hidden; }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #94a3b8;
        font-size: 0.75rem;
        padding: 12px 0;
        border-top: 1px solid #e2e8f0;
        margin-top: 16px;
    }
    
    /* Success/Error más compactos */
    .stSuccess, .stError { padding: 8px 12px !important; font-size: 0.9rem; }
    
    /* Divider */
    hr { margin: 12px 0 !important; border-color: #e2e8f0 !important; }
</style>
""", unsafe_allow_html=True)

# Header compacto
header_html = f"""
<div class="header">
    {"<img src='data:image/png;base64," + logo_base64 + "' alt='EQIDIS'>" if logo_base64 else ""}
    <h1>Procesador CONTPAQi</h1>
    <span>Importación de cuentas y pólizas</span>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# Verificar scripts
if not accounts_scripts_dir.exists() or not policies_scripts_dir.exists():
    st.error(f"❌ Scripts no encontrados en: {accounts_scripts_dir}")
    st.stop()

# Funciones de procesamiento
def process_accounts(accounts_file, total_digits, merge_with_base, base_file=None, is_contpaqi_base=True):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        accounts_path = temp_path / "entry.xlsx"
        with open(accounts_path, "wb") as f:
            f.write(accounts_file.getbuffer())
        
        template_path = accounts_scripts_dir / "template.xlsx"
        sat_path = accounts_scripts_dir / "SAT.xlsx"
        
        shutil.copy(template_path, temp_path / "template.xlsx")
        if sat_path.exists():
            shutil.copy(sat_path, temp_path / "SAT.xlsx")
        
        script_content = (accounts_scripts_dir / "entry_to_template.py").read_text()
        script_content = re.sub(r"TOTAL_DIGITS = \d+", f"TOTAL_DIGITS = {total_digits}", script_content, 1)
        temp_script = temp_path / "entry_to_template.py"
        temp_script.write_text(script_content)
        
        output_path = temp_path / "output.xlsx"
        subprocess.run([
            sys.executable, str(temp_script), str(temp_path / "template.xlsx"), str(accounts_path), str(output_path)
        ], check=True, capture_output=True, text=True, cwd=str(temp_path))
        
        final_output = output_path
        if merge_with_base:
            merge_scripts_dir = accounts_scripts_dir / "MergeAccounts"
            
            if is_contpaqi_base:
                merge_base_path = merge_scripts_dir / "contpaqi_base.xlsx"
            else:
                merge_base_path = temp_path / "base.xlsx"
                with open(merge_base_path, "wb") as f:
                    f.write(base_file.getbuffer())
            
            final_output = temp_path / "final_output.xls"
            subprocess.run([
                sys.executable, str(merge_scripts_dir / "merge_accounts.py"), str(merge_base_path), str(output_path), str(final_output)
            ], check=True, capture_output=True, text=True, cwd=str(merge_scripts_dir))
        
        return final_output.read_bytes()

def process_policies(policies_file, groups_file, total_digits):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        policies_path = temp_path / "entry.xml"
        groups_path = temp_path / "grupos.csv"
        
        with open(policies_path, "wb") as f:
            f.write(policies_file.getbuffer())
        with open(groups_path, "wb") as f:
            f.write(groups_file.getbuffer())
        
        shutil.copy(policies_scripts_dir / "template.xlsx", temp_path / "template.xlsx")
        
        script_content = (policies_scripts_dir / "xml_to_contpaqi_xls_v2.py").read_text()
        script_content = re.sub(r"TOTAL_DIGITS = \d+", f"TOTAL_DIGITS = {total_digits}", script_content, 1)
        temp_script = temp_path / "xml_to_contpaqi_xls_v2.py"
        temp_script.write_text(script_content)
        
        output_path = temp_path / "output.xls"
        subprocess.run([
            sys.executable, str(temp_script), str(temp_path / "template.xlsx"), str(policies_path), str(groups_path), str(output_path)
        ], check=True, capture_output=True, text=True, cwd=str(temp_path))
        
        return output_path.read_bytes()

# Tabs
tab1, tab2, tab3 = st.tabs(["💰 Cuentas", "📄 Pólizas", "🚀 Proceso Completo"])

# ==================== TAB CUENTAS ====================
with tab1:
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown("#### ⚙️ Configuración")
        is_contpaqi = st.checkbox("Base CONTPAQi (8 dígitos)", value=True, key="acc_cp")
        if not is_contpaqi:
            total_digits = st.number_input("Dígitos", min_value=1, max_value=20, value=8, key="acc_dig")
            merge = st.checkbox("Merge con base", key="acc_merge")
        else:
            total_digits, merge = 8, True
    
    with col2:
        st.markdown("#### 📁 Balanza de Comprobación XLSX")
        acc_file = st.file_uploader("Excel (.xlsx, .xls)", type=["xlsx", "xls"], key="acc_f", label_visibility="collapsed")
        if not is_contpaqi and merge:
            st.markdown("#### 📁 Archivo Base")
            base_file = st.file_uploader("Base para merge", type=["xlsx", "xls"], key="acc_b", label_visibility="collapsed")
        else:
            base_file = None
    
    with col3:
        st.markdown("#### 📥 Resultado")
        if st.button("🔄 Procesar", key="btn_acc", use_container_width=True):
            if not acc_file:
                st.error("❌ Selecciona archivo")
            elif not is_contpaqi and merge and not base_file:
                st.error("❌ Selecciona base")
            else:
                with st.spinner("Procesando..."):
                    try:
                        result = process_accounts(acc_file, total_digits, merge, base_file, is_contpaqi)
                        st.success("✅ Listo!")
                        st.download_button("📥 Descargar", result, "cuentas.xls", "application/vnd.ms-excel", key="dl_acc", use_container_width=True)
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

# ==================== TAB PÓLIZAS ====================
with tab2:
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown("#### ⚙️ Configuración")
        is_contpaqi_pol = st.checkbox("Base CONTPAQi (8 dígitos)", value=True, key="pol_cp")
        if not is_contpaqi_pol:
            total_digits_pol = st.number_input("Dígitos", min_value=1, max_value=20, value=8, key="pol_dig")
        else:
            total_digits_pol = 8
    
    with col2:
        st.markdown("#### 📁 Archivos (Pólizas XML y Grupos de Cuentas CSV)")
        pol_file = st.file_uploader("Pólizas XML", type=["xml"], key="pol_f", label_visibility="collapsed")
        grp_file = st.file_uploader("Grupos CSV", type=["csv"], key="pol_g", label_visibility="collapsed")
    
    with col3:
        st.markdown("#### 📥 Resultado")
        if st.button("🔄 Procesar", key="btn_pol", use_container_width=True):
            if not pol_file:
                st.error("❌ Selecciona XML")
            elif not grp_file:
                st.error("❌ Selecciona CSV")
            else:
                with st.spinner("Procesando..."):
                    try:
                        result = process_policies(pol_file, grp_file, total_digits_pol)
                        st.success("✅ Listo!")
                        st.download_button("📥 Descargar", result, "polizas.xls", "application/vnd.ms-excel", key="dl_pol", use_container_width=True)
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

# ==================== TAB PROCESO COMPLETO ====================
with tab3:
    st.markdown("**Procesa cuentas y pólizas en un solo paso**")
    
    col_cfg, col_acc, col_pol, col_grp = st.columns([1, 1, 1, 1])
    
    with col_cfg:
        st.markdown("#### ⚙️ Config")
        is_cp_full = st.checkbox("Base CONTPAQi", value=True, key="full_cp")
        if not is_cp_full:
            dig_full = st.number_input("Dígitos", min_value=1, max_value=20, value=8, key="full_dig")
            merge_full = st.checkbox("Merge cuentas", key="full_merge")
        else:
            dig_full, merge_full = 8, True
    
    with col_acc:
        st.markdown("#### 💰 Balanza de Comprobación XLSX")
        full_acc = st.file_uploader("Excel", type=["xlsx", "xls"], key="full_acc", label_visibility="collapsed")
        if not is_cp_full and merge_full:
            full_base = st.file_uploader("Base", type=["xlsx", "xls"], key="full_base", label_visibility="collapsed")
        else:
            full_base = None
    
    with col_pol:
        st.markdown("#### 📄 Pólizas XML")
        full_pol = st.file_uploader("XML", type=["xml"], key="full_pol", label_visibility="collapsed")
    
    with col_grp:
        st.markdown("#### 📊 Grupos de Cuentas CSV")
        full_grp = st.file_uploader("CSV", type=["csv"], key="full_grp", label_visibility="collapsed")
    
    st.markdown("---")
    
    col_btn, col_dl1, col_dl2 = st.columns([1, 1, 1])
    
    with col_btn:
        process_btn = st.button("🚀 Procesar Todo", key="btn_full", use_container_width=True)
    
    if process_btn:
        errors = []
        if not full_acc: errors.append("cuentas")
        if not full_pol: errors.append("pólizas")
        if not full_grp: errors.append("grupos")
        if not is_cp_full and merge_full and not full_base: errors.append("base")
        
        if errors:
            st.error(f"❌ Faltan: {', '.join(errors)}")
        else:
            results = {}
            
            with st.spinner("Procesando cuentas..."):
                try:
                    results['acc'] = process_accounts(full_acc, dig_full, merge_full, full_base, is_cp_full)
                except Exception as e:
                    st.error(f"❌ Cuentas: {str(e)}")
                    results['acc'] = None
            
            with st.spinner("Procesando pólizas..."):
                try:
                    results['pol'] = process_policies(full_pol, full_grp, dig_full)
                except Exception as e:
                    st.error(f"❌ Pólizas: {str(e)}")
                    results['pol'] = None
            
            if results['acc'] or results['pol']:
                st.success("✅ Completado!")
                
                with col_dl1:
                    if results['acc']:
                        st.download_button("📥 Cuentas", results['acc'], "cuentas.xls", "application/vnd.ms-excel", key="dl_f_acc", use_container_width=True)
                
                with col_dl2:
                    if results['pol']:
                        st.download_button("📥 Pólizas", results['pol'], "polizas.xls", "application/vnd.ms-excel", key="dl_f_pol", use_container_width=True)

# Footer
st.markdown('<div class="footer">EQIDIS © 2024 • Procesador CONTPAQi v2.0</div>', unsafe_allow_html=True)
