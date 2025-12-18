#!/usr/bin/env python3
"""
EQIDIS - Procesador CONTPAQi
Aplicación para procesar catálogos de cuentas y pólizas de Odoo a formato CONTPAQi
"""

import streamlit as st
import streamlit.components.v1 as components
import subprocess
import sys
import re
import json
import csv
import io
import base64
import tempfile
import shutil
from pathlib import Path
from datetime import date, timedelta

# ==================== CONFIGURACIÓN ====================
ODOO_URL = "https://consola.eqidis.com"
ODOO_DB = "consola"

SCRIPT_DIR = Path(__file__).parent.absolute()
ACCOUNTS_SCRIPTS = SCRIPT_DIR.parent / "CuentasOdooToContpaqi"
POLICIES_SCRIPTS = SCRIPT_DIR.parent / "PolizasOdooToContpaqi"

# ==================== CONFIGURACIÓN DE PÁGINA ====================
st.set_page_config(
    page_title="EQIDIS - Procesador CONTPAQi",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Logo
logo_path = SCRIPT_DIR / "logo.png"
logo_b64 = base64.b64encode(open(logo_path, "rb").read()).decode() if logo_path.exists() else ""

# CSS
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background: #f8fafc; }}
    .header {{ display: flex; align-items: center; gap: 12px; padding: 16px 0; border-bottom: 1px solid #e2e8f0; margin-bottom: 16px; }}
    .header img {{ height: 32px; }}
    .header h1 {{ font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }}
    .header span {{ font-size: 0.85rem; color: #64748b; margin-left: auto; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 8px; background: #fff; padding: 8px; border-radius: 10px; border: 1px solid #e2e8f0; }}
    .stTabs [data-baseweb="tab"] {{ height: 44px; padding: 0 24px !important; border-radius: 8px; color: #64748b; font-weight: 500; font-size: 0.95rem; }}
    .stTabs [aria-selected="true"] {{ background: #6366f1 !important; color: white !important; }}
    .stButton > button {{ background: #6366f1; color: white; border: none; border-radius: 6px; font-weight: 500; }}
    .stButton > button:hover {{ background: #4f46e5; }}
    .stDownloadButton > button {{ background: #10b981; color: white; border: none; border-radius: 6px; }}
    .block-container {{ padding: 1rem 2rem !important; max-width: 1400px; }}
    h4 {{ font-size: 0.95rem !important; color: #374151 !important; margin: 8px 0 !important; }}
    #MainMenu, footer, header {{ visibility: hidden; }}
    .footer {{ text-align: center; color: #94a3b8; font-size: 0.75rem; padding: 12px 0; border-top: 1px solid #e2e8f0; margin-top: 16px; }}
    .info-box {{ background: #eff6ff; border: 1px solid #93c5fd; border-radius: 8px; padding: 12px; margin: 8px 0; }}
</style>
<div class="header">
    {"<img src='data:image/png;base64," + logo_b64 + "' alt='EQIDIS'>" if logo_b64 else ""}
    <h1>Procesador CONTPAQi</h1>
    <span>Importación de cuentas y pólizas</span>
</div>
""", unsafe_allow_html=True)

# Verificar scripts
if not ACCOUNTS_SCRIPTS.exists() or not POLICIES_SCRIPTS.exists():
    st.error("❌ Scripts no encontrados")
    st.stop()

# ==================== CLASE ODOO ====================
class OdooConnector:
    def __init__(self, username: str, password: str):
        import requests
        self.url = ODOO_URL
        self.db = ODOO_DB
        self.session = requests.Session()
        self.uid = None
        self._authenticate(username, password)
    
    def _authenticate(self, username: str, password: str):
        response = self.session.post(f"{self.url}/web/session/authenticate", json={
            "jsonrpc": "2.0", "method": "call",
            "params": {"db": self.db, "login": username, "password": password}, "id": 1
        })
        result = response.json().get('result', {})
        if not result.get('uid'):
            raise Exception("Credenciales inválidas")
        self.uid = result['uid']
    
    def _call(self, model: str, method: str, args=None, kwargs=None):
        response = self.session.post(f"{self.url}/web/dataset/call_kw/{model}/{method}", json={
            "jsonrpc": "2.0", "method": "call",
            "params": {"model": model, "method": method, "args": args or [], "kwargs": kwargs or {}}, "id": 2
        })
        result = response.json()
        if 'error' in result:
            raise Exception(result['error'].get('data', {}).get('message', 'Error'))
        return result.get('result')
    
    def get_companies(self) -> list:
        return self._call('res.company', 'search_read', [[]], {'fields': ['id', 'name', 'vat'], 'context': {'lang': 'es_MX'}})
    
    def get_account_groups(self, company_id: int) -> list:
        return self._call('account.group', 'search_read', [[]], 
            {'fields': ['name', 'code_prefix_start', 'code_prefix_end'], 'context': {'allowed_company_ids': [company_id], 'lang': 'es_MX'}})
    
    def export_trial_balance(self, company_id: int, date_from: str, date_to: str) -> bytes:
        """Exportar Balanza de Comprobación XLSX"""
        options = self._call('account.report', 'get_options', [[12], {}], {'context': {'allowed_company_ids': [company_id], 'lang': 'es_MX'}})
        options.update({'date': {"mode": "range", "date_from": date_from, "date_to": date_to}, 'unfold_all': True, 'hierarchy': True})
        response = self.session.post(f"{self.url}/account_reports", data={"options": json.dumps(options), "file_generator": "export_to_xlsx"})
        if response.status_code != 200 or response.content[:4] != b'PK\x03\x04':
            raise Exception("Error al exportar Balanza")
        return response.content
    
    def export_xml_polizas(self, company_id: int, date_from: str, date_to: str) -> bytes:
        """Exportar Pólizas XML desde Libro Mayor"""
        options = self._call('account.report', 'get_options', [[10], {}], {'context': {'allowed_company_ids': [company_id], 'lang': 'es_MX'}})
        options['date'] = {"mode": "range", "date_from": date_from, "date_to": date_to}
        ctx = {"allowed_company_ids": [company_id], "lang": "es_MX", "l10n_mx_xml_polizas_generation_options": options}
        wizard_id = self._call('l10n_mx_xml_polizas.xml_polizas_wizard', 'create', [{"export_type": "AF"}], {'context': ctx})
        result = self._call('l10n_mx_xml_polizas.xml_polizas_wizard', 'export_xml', [[wizard_id]], {'context': ctx})
        if not result or not result.get('url'):
            raise Exception("Error al exportar XML")
        response = self.session.get(self.url + result['url'])
        if response.status_code != 200:
            raise Exception("Error al descargar XML")
        return response.content

# ==================== FUNCIONES DE PROCESAMIENTO ====================
def groups_to_csv(groups: list) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    # Usar nombres de columna en español que espera el script xml_to_contpaqi_xls_v2.py
    writer.writerow(['Inicio de prefijo de código', 'Fin de prefijo de código', 'Nombre'])
    for g in groups:
        writer.writerow([g['code_prefix_start'], g['code_prefix_end'], g['name']])
    return output.getvalue()

def process_accounts(accounts_data, total_digits: int = 8, merge: bool = True) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        
        # Guardar archivo de entrada
        entry_path = tmp_path / "entry.xlsx"
        with open(entry_path, "wb") as f:
            f.write(accounts_data if isinstance(accounts_data, bytes) else accounts_data.getbuffer())
        
        # Copiar archivos necesarios
        shutil.copy(ACCOUNTS_SCRIPTS / "template.xlsx", tmp_path / "template.xlsx")
        if (ACCOUNTS_SCRIPTS / "SAT.xlsx").exists():
            shutil.copy(ACCOUNTS_SCRIPTS / "SAT.xlsx", tmp_path / "SAT.xlsx")
        
        # Modificar script con dígitos
        script = (ACCOUNTS_SCRIPTS / "entry_to_template.py").read_text()
        script = re.sub(r"TOTAL_DIGITS = \d+", f"TOTAL_DIGITS = {total_digits}", script, 1)
        (tmp_path / "entry_to_template.py").write_text(script)
        
        # Ejecutar
        output_path = tmp_path / "output.xlsx"
        subprocess.run([sys.executable, str(tmp_path / "entry_to_template.py"), 
            str(tmp_path / "template.xlsx"), str(entry_path), str(output_path)],
            check=True, capture_output=True, cwd=str(tmp_path))
        
        # Merge si aplica
        if merge:
            merge_dir = ACCOUNTS_SCRIPTS / "MergeAccounts"
            final_path = tmp_path / "final.xls"
            subprocess.run([sys.executable, str(merge_dir / "merge_accounts.py"),
                str(merge_dir / "contpaqi_base.xlsx"), str(output_path), str(final_path)],
                check=True, capture_output=True, cwd=str(merge_dir))
            return final_path.read_bytes()
        
        return output_path.read_bytes()

def process_policies(xml_data, groups_data, total_digits: int = 8) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        
        # Guardar archivos
        xml_path = tmp_path / "entry.xml"
        with open(xml_path, "wb") as f:
            f.write(xml_data if isinstance(xml_data, bytes) else xml_data.getbuffer())
        
        groups_path = tmp_path / "grupos.csv"
        with open(groups_path, "w" if isinstance(groups_data, str) else "wb") as f:
            f.write(groups_data if isinstance(groups_data, (str, bytes)) else groups_data.getbuffer())
        
        shutil.copy(POLICIES_SCRIPTS / "template.xlsx", tmp_path / "template.xlsx")
        
        # Modificar script
        script = (POLICIES_SCRIPTS / "xml_to_contpaqi_xls_v2.py").read_text()
        script = re.sub(r"TOTAL_DIGITS = \d+", f"TOTAL_DIGITS = {total_digits}", script, 1)
        (tmp_path / "xml_to_contpaqi_xls_v2.py").write_text(script)
        
        # Ejecutar
        output_path = tmp_path / "output.xls"
        subprocess.run([sys.executable, str(tmp_path / "xml_to_contpaqi_xls_v2.py"),
            str(tmp_path / "template.xlsx"), str(xml_path), str(groups_path), str(output_path)],
            check=True, capture_output=True, cwd=str(tmp_path))
        
        return output_path.read_bytes()

# ==================== SESSION STATE ====================
for key in ['odoo', 'companies', 'company_id', 'results', 'show_success']:
    if key not in st.session_state:
        st.session_state[key] = None if key not in ['results'] else {}
if 'show_success' not in st.session_state:
    st.session_state.show_success = False

# ==================== INTERFAZ ====================
tab1, tab2, tab3 = st.tabs(["📁 Manual", "🔗 Odoo Automático", "ℹ️ Ayuda"])

# ==================== TAB MANUAL ====================
with tab1:
    st.markdown("### Procesamiento Manual")
    st.markdown("Sube los archivos exportados manualmente desde Odoo")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 💰 Cuentas")
        acc_file = st.file_uploader("Balanza de Comprobación (XLSX)", type=["xlsx", "xls"], key="m_acc")
        if st.button("Procesar Cuentas", key="m_btn_acc", use_container_width=True, disabled=not acc_file):
            with st.spinner("Procesando..."):
                try:
                    result = process_accounts(acc_file)
                    st.success("✅ Listo")
                    st.download_button("📥 Descargar Cuentas", result, "cuentas.xls", use_container_width=True)
                except Exception as e:
                    st.error(f"❌ {e}")
    
    with col2:
        st.markdown("#### 📄 Pólizas")
        pol_file = st.file_uploader("Pólizas XML", type=["xml"], key="m_pol")
        grp_file = st.file_uploader("Grupos de Cuentas (CSV)", type=["csv"], key="m_grp")
        if st.button("Procesar Pólizas", key="m_btn_pol", use_container_width=True, disabled=not (pol_file and grp_file)):
            with st.spinner("Procesando..."):
                try:
                    result = process_policies(pol_file, grp_file)
                    st.success("✅ Listo")
                    st.download_button("📥 Descargar Pólizas", result, "polizas.xls", use_container_width=True)
                except Exception as e:
                    st.error(f"❌ {e}")

# ==================== TAB ODOO AUTOMÁTICO ====================
with tab2:
    st.markdown("### Proceso Automático desde Odoo")
    st.markdown(f"Conectado a: `{ODOO_URL}`")
    
    # Conexión
    if not st.session_state.odoo:
        col_u, col_p, col_b = st.columns([2, 2, 1])
        with col_u:
            username = st.text_input("Usuario", key="o_user")
        with col_p:
            password = st.text_input("Contraseña", type="password", key="o_pass")
        with col_b:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔌 Conectar", use_container_width=True):
                if username and password:
                    with st.spinner("Conectando..."):
                        try:
                            st.session_state.odoo = OdooConnector(username, password)
                            st.session_state.companies = st.session_state.odoo.get_companies()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ {e}")
                else:
                    st.error("❌ Ingresa usuario y contraseña")
    else:
        # Conectado
        col_status, col_disc = st.columns([3, 1])
        with col_status:
            st.success("✅ Conectado a Odoo")
        with col_disc:
            if st.button("🔓 Desconectar"):
                st.session_state.odoo = None
                st.session_state.companies = None
                st.session_state.results = {}
                st.rerun()
        
        st.markdown("---")
        
        # Selección
        col_emp, col_fecha = st.columns([2, 1])
        
        with col_emp:
            companies = st.session_state.companies
            options = {f"{c['name']} ({c.get('vat') or 'Sin RFC'})": c['id'] for c in companies}
            selected = st.selectbox("🏢 Empresa", list(options.keys()))
            st.session_state.company_id = options[selected] if selected else None
            
            company = next((c for c in companies if c['id'] == st.session_state.company_id), None)
            if company and not company.get('vat'):
                st.warning("⚠️ Sin RFC - El XML de pólizas requiere RFC")
        
        with col_fecha:
            # Selector de mes (más rápido y sin errores)
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            current_month = date.today().month
            current_year = date.today().year
            
            col_m, col_y = st.columns(2)
            with col_m:
                mes_idx = st.selectbox("Mes", range(1, 13), index=current_month - 1, format_func=lambda x: meses[x-1])
            with col_y:
                año = st.selectbox("Año", range(current_year - 5, current_year + 1), index=5)
            
            # Calcular fechas del mes seleccionado
            d_from = date(año, mes_idx, 1)
            if mes_idx == 12:
                d_to = date(año, 12, 31)
            else:
                d_to = date(año, mes_idx + 1, 1) - timedelta(days=1)
        
        st.markdown("---")
        
        # Proceso
        col_info, col_btn = st.columns([1, 2])
        
        with col_info:
            st.markdown("""
            <div style="background:#eff6ff;border:1px solid #93c5fd;border-radius:8px;padding:10px;font-size:0.85rem;">
            <strong>Se procesará:</strong><br>
            Balanza → Cuentas<br>
            XML + Grupos → Pólizas
            </div>
            """, unsafe_allow_html=True)
        
        with col_btn:
            if st.button("⚡ PROCESAR TODO", use_container_width=True, type="primary"):
                odoo = st.session_state.odoo
                cid = st.session_state.company_id
                df, dt = d_from.strftime("%Y-%m-%d"), d_to.strftime("%Y-%m-%d")
                
                # Stepper container
                stepper = st.container()
                results = {}
                steps = [
                    ("📊", "Balanza", "pending"),
                    ("📄", "Pólizas XML", "pending"),
                    ("📋", "Grupos", "pending"),
                    ("💰", "Cuentas", "pending"),
                    ("📑", "Pólizas", "pending"),
                ]
                
                def render_stepper(steps, current_step, error=None):
                    html = '<div style="display:flex;gap:8px;align-items:center;padding:12px 0;">'
                    for i, (icon, name, status) in enumerate(steps):
                        if i < current_step:
                            color, bg = "#10b981", "#d1fae5"  # Completado (verde)
                            display_icon = "✓"
                        elif i == current_step:
                            if error:
                                color, bg = "#ef4444", "#fee2e2"  # Error (rojo)
                                display_icon = "✗"
                            else:
                                color, bg = "#6366f1", "#e0e7ff"  # En proceso (morado)
                                display_icon = "⋯"
                        else:
                            color, bg = "#94a3b8", "#f1f5f9"  # Pendiente (gris)
                            display_icon = icon
                        html += f'''
                            <div style="display:flex;flex-direction:column;align-items:center;flex:1;">
                                <div style="width:32px;height:32px;border-radius:50%;background:{bg};color:{color};display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:600;">{display_icon}</div>
                                <span style="font-size:11px;color:{color};margin-top:4px;">{name}</span>
                            </div>
                        '''
                        if i < len(steps) - 1:
                            line_color = "#10b981" if i < current_step else "#e2e8f0"
                            html += f'<div style="flex:0.5;height:2px;background:{line_color};"></div>'
                    html += '</div>'
                    return html
                
                try:
                    with stepper:
                        placeholder = st.empty()
                        
                        # Paso 1: Balanza
                        placeholder.markdown(render_stepper(steps, 0), unsafe_allow_html=True)
                        balanza = odoo.export_trial_balance(cid, df, dt)
                        results['balanza_original'] = balanza
                        
                        # Paso 2: Pólizas XML
                        placeholder.markdown(render_stepper(steps, 1), unsafe_allow_html=True)
                        xml = odoo.export_xml_polizas(cid, df, dt)
                        results['xml_original'] = xml
                        
                        # Paso 3: Grupos
                        placeholder.markdown(render_stepper(steps, 2), unsafe_allow_html=True)
                        grupos = groups_to_csv(odoo.get_account_groups(cid))
                        results['grupos_original'] = grupos
                        
                        # Paso 4: Procesar Cuentas
                        placeholder.markdown(render_stepper(steps, 3), unsafe_allow_html=True)
                        results['cuentas'] = process_accounts(balanza)
                        
                        # Paso 5: Procesar Pólizas
                        placeholder.markdown(render_stepper(steps, 4), unsafe_allow_html=True)
                        results['polizas'] = process_policies(xml, grupos)
                        
                        # Completado
                        placeholder.markdown(render_stepper(steps, 5), unsafe_allow_html=True)
                        st.session_state.results = results
                        st.session_state.show_success = True
                    
                except Exception as e:
                    placeholder.markdown(render_stepper(steps, steps.index(next((s for s in steps if s[2] == "pending"), steps[0])), error=True), unsafe_allow_html=True)
                    st.error(f"❌ {e}")
        
        # Resultados
        if st.session_state.results:
            # Ancla para scroll automático
            st.markdown('<div id="resultados-section"></div>', unsafe_allow_html=True)
            st.markdown("### 📥 Descargar Resultados")
            
            # Scroll automático si hay resultados nuevos
            if st.session_state.get('show_success'):
                st.session_state.show_success = False
                components.html("""
                    <script>
                        setTimeout(function() {
                            const anchor = window.parent.document.getElementById('resultados-section');
                            if (anchor) {
                                anchor.scrollIntoView({behavior: 'smooth', block: 'start'});
                            }
                        }, 100);
                    </script>
                """, height=0)
            
            # Archivos procesados (CONTPAQi)
            st.markdown("#### Archivos CONTPAQi")
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                if st.session_state.results.get('cuentas'):
                    st.download_button("📥 CUENTAS CONTPAQi", st.session_state.results['cuentas'], 
                        "cuentas_contpaqi.xls", "application/vnd.ms-excel", use_container_width=True)
            with col_dl2:
                if st.session_state.results.get('polizas'):
                    st.download_button("📥 PÓLIZAS CONTPAQi", st.session_state.results['polizas'],
                        "polizas_contpaqi.xls", "application/vnd.ms-excel", use_container_width=True)
            
            # Archivos originales de Odoo
            st.markdown("#### Archivos Originales (Odoo)")
            col_o1, col_o2, col_o3 = st.columns(3)
            with col_o1:
                if st.session_state.results.get('balanza_original'):
                    st.download_button("📊 Balanza XLSX", st.session_state.results['balanza_original'],
                        "balanza_odoo.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            with col_o2:
                if st.session_state.results.get('xml_original'):
                    st.download_button("📄 Pólizas XML", st.session_state.results['xml_original'],
                        "polizas_odoo.xml", "application/xml", use_container_width=True)
            with col_o3:
                if st.session_state.results.get('grupos_original'):
                    st.download_button("📋 Grupos CSV", st.session_state.results['grupos_original'],
                        "grupos_odoo.csv", "text/csv", use_container_width=True)

# ==================== TAB AYUDA ====================
with tab3:
    st.markdown("""
    ### 📖 Guía de Uso
    
    #### Opción 1: Proceso Automático (Recomendado)
    1. Ve a la pestaña **Odoo Automático**
    2. Ingresa tu usuario y contraseña de Odoo
    3. Selecciona la empresa y el período
    4. Haz clic en **PROCESAR TODO**
    5. Descarga los archivos generados
    
    #### Opción 2: Proceso Manual
    1. Exporta manualmente desde Odoo:
       - Balanza de Comprobación (XLSX)
       - Pólizas XML (del Libro Mayor)
       - Grupos de Cuentas (CSV)
    2. Ve a la pestaña **Manual**
    3. Sube los archivos y procesa
    
    #### Requisitos para Pólizas XML
    - La empresa debe tener **RFC configurado** en Odoo
    - Debe haber movimientos contables en el período seleccionado
    
    ---
    **Versión 2.3** | EQIDIS © 2024
    """)

# Notificación de éxito
if st.session_state.get('show_success'):
    st.toast("🎉 ¡Proceso completado! Descarga tus archivos abajo.", icon="✅")

# Footer
st.markdown('<div class="footer">EQIDIS © 2024 • Procesador CONTPAQi v2.3</div>', unsafe_allow_html=True)
