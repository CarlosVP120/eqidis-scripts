#!/usr/bin/env python3
"""
Aplicación standalone para procesar catálogos de cuentas y pólizas para CONTPAQi

Deploy en Streamlit Cloud:
1. Subir este repositorio a GitHub
2. Ir a share.streamlit.io
3. Conectar el repositorio
4. Configurar el archivo principal como: streamlit_app.py
5. Deploy!

Uso local:
    streamlit run streamlit_app.py
"""

import streamlit as st
import os
import sys
import subprocess
import re
from pathlib import Path
import tempfile
import shutil

# Configuración de rutas
script_dir = Path(__file__).parent.absolute()
# Los scripts están en el mismo nivel que contpaqi-processor-app dentro de Scripts/
# script_dir = Scripts/contpaqi-processor-app
# Necesitamos: Scripts/CuentasOdooToContpaqi
accounts_scripts_dir = script_dir.parent / "CuentasOdooToContpaqi"
policies_scripts_dir = script_dir.parent / "PolizasOdooToContpaqi"

# Si no existen, mostrar error al inicio
if not accounts_scripts_dir.exists() or not policies_scripts_dir.exists():
    st.error(f"❌ No se encontraron los scripts necesarios. Verifica que existan:")
    st.code(f"""
    {accounts_scripts_dir}
    {policies_scripts_dir}
    """)
    st.stop()

st.set_page_config(
    page_title="Procesador CONTPAQi",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Procesador CONTPAQi")
st.markdown("Procesa catálogos de cuentas y pólizas para importar a CONTPAQi")

tab1, tab2 = st.tabs(["💰 Cuentas", "📄 Pólizas"])

with tab1:
    st.header("Procesar Catálogo de Cuentas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Configuración")
        is_contpaqi_base = st.checkbox(
            "Es base CONTPAQi",
            value=True,
            help="Si está marcado, usará 8 dígitos y hará merge automático con contpaqi_base.xlsx"
        )
        
        if not is_contpaqi_base:
            total_digits = st.number_input(
                "Número de dígitos",
                min_value=1,
                max_value=20,
                value=8,
                help="Número total de dígitos para normalizar códigos"
            )
            
            merge_with_base = st.checkbox(
                "Hacer merge con archivo base",
                value=False,
                help="Combinar con un archivo base personalizado"
            )
        else:
            total_digits = 8
            merge_with_base = True
    
    with col2:
        st.subheader("Archivos")
        accounts_file = st.file_uploader(
            "Archivo de Cuentas",
            type=["xlsx", "xls"],
            help="Catálogo de cuentas en formato Excel"
        )
        
        base_file = None
        if not is_contpaqi_base and merge_with_base:
            base_file = st.file_uploader(
                "Archivo Base para Merge",
                type=["xlsx", "xls"],
                help="Catálogo base en formato CONTPAQi"
            )
    
    if st.button("🔄 Procesar Cuentas", type="primary", use_container_width=True):
        if not accounts_file:
            st.error("❌ Por favor selecciona un archivo de cuentas")
        elif not is_contpaqi_base and merge_with_base and not base_file:
            st.error("❌ Por favor selecciona un archivo base para hacer merge")
        else:
            with st.spinner("Procesando cuentas..."):
                try:
                    # Crear directorio temporal
                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_path = Path(temp_dir)
                        
                        # Guardar archivo de cuentas
                        accounts_path = temp_path / "entry.xlsx"
                        with open(accounts_path, "wb") as f:
                            f.write(accounts_file.getbuffer())
                        
                        # Copiar archivos necesarios
                        template_path = accounts_scripts_dir / "template.xlsx"
                        sat_path = accounts_scripts_dir / "SAT.xlsx"
                        
                        temp_template = temp_path / "template.xlsx"
                        temp_sat = temp_path / "SAT.xlsx"
                        
                        shutil.copy(template_path, temp_template)
                        if sat_path.exists():
                            shutil.copy(sat_path, temp_sat)
                        
                        # Modificar TOTAL_DIGITS en el script temporal
                        script_content = (accounts_scripts_dir / "entry_to_template.py").read_text()
                        script_content = re.sub(
                            r"TOTAL_DIGITS = \d+",
                            f"TOTAL_DIGITS = {total_digits}",
                            script_content,
                            1
                        )
                        temp_script = temp_path / "entry_to_template.py"
                        temp_script.write_text(script_content)
                        
                        # Procesar cuentas ejecutando el script
                        output_path = temp_path / "output.xlsx"
                        result = subprocess.run([
                            sys.executable,
                            str(temp_script),
                            str(temp_template),
                            str(accounts_path),
                            str(output_path)
                        ], check=True, capture_output=True, text=True, cwd=str(temp_path))
                        
                        # Hacer merge si es necesario
                        final_output = output_path
                        if merge_with_base:
                            merge_scripts_dir = accounts_scripts_dir / "MergeAccounts"
                            contpaqi_base = merge_scripts_dir / "contpaqi_base.xlsx"
                            
                            if is_contpaqi_base:
                                merge_base_path = contpaqi_base
                            else:
                                merge_base_path = temp_path / "base.xlsx"
                                with open(merge_base_path, "wb") as f:
                                    f.write(base_file.getbuffer())
                            
                            final_output = temp_path / "final_output.xls"
                            
                            # Ejecutar merge
                            merge_script = merge_scripts_dir / "merge_accounts.py"
                            subprocess.run([
                                sys.executable,
                                str(merge_script),
                                str(merge_base_path),
                                str(output_path),
                                str(final_output)
                            ], check=True, capture_output=True, text=True, cwd=str(merge_scripts_dir))
                        
                        # Leer archivo final
                        result_bytes = final_output.read_bytes()
                        
                        st.success("✅ Cuentas procesadas exitosamente!")
                        st.download_button(
                            label="📥 Descargar Archivo Procesado",
                            data=result_bytes,
                            file_name="cuentas_procesadas.xls",
                            mime="application/vnd.ms-excel",
                            use_container_width=True
                        )
                        
                except subprocess.CalledProcessError as e:
                    st.error(f"❌ Error al procesar las cuentas")
                    st.code(f"Error: {e.stderr}")
                    st.exception(e)
                except Exception as e:
                    st.error(f"❌ Error al procesar las cuentas: {str(e)}")
                    st.exception(e)

with tab2:
    st.header("Procesar Pólizas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Configuración")
        is_contpaqi_base_pol = st.checkbox(
            "Es base CONTPAQi",
            value=True,
            key="is_contpaqi_base_pol",
            help="Si está marcado, usará 8 dígitos por defecto"
        )
        
        if not is_contpaqi_base_pol:
            total_digits_pol = st.number_input(
                "Número de dígitos",
                min_value=1,
                max_value=20,
                value=8,
                key="total_digits_pol",
                help="Número total de dígitos para normalizar códigos"
            )
        else:
            total_digits_pol = 8
    
    with col2:
        st.subheader("Archivos")
        policies_file = st.file_uploader(
            "Archivo de Pólizas (XML)",
            type=["xml"],
            help="Pólizas en formato XML"
        )
        
        groups_file = st.file_uploader(
            "Archivo de Grupos de Cuentas (CSV)",
            type=["csv"],
            help="Grupos de cuentas en formato CSV"
        )
    
    if st.button("🔄 Procesar Pólizas", type="primary", use_container_width=True):
        if not policies_file:
            st.error("❌ Por favor selecciona un archivo de pólizas")
        elif not groups_file:
            st.error("❌ Por favor selecciona un archivo de grupos de cuentas")
        else:
            with st.spinner("Procesando pólizas..."):
                try:
                    # Crear directorio temporal
                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_path = Path(temp_dir)
                        
                        # Guardar archivos
                        policies_path = temp_path / "entry.xml"
                        groups_path = temp_path / "grupos.csv"
                        
                        with open(policies_path, "wb") as f:
                            f.write(policies_file.getbuffer())
                        with open(groups_path, "wb") as f:
                            f.write(groups_file.getbuffer())
                        
                        # Copiar template
                        template_path = policies_scripts_dir / "template.xlsx"
                        temp_template = temp_path / "template.xlsx"
                        shutil.copy(template_path, temp_template)
                        
                        # Modificar TOTAL_DIGITS en el script
                        script_path = policies_scripts_dir / "xml_to_contpaqi_xls_v2.py"
                        script_content = script_path.read_text()
                        script_content = re.sub(
                            r"TOTAL_DIGITS = \d+",
                            f"TOTAL_DIGITS = {total_digits_pol}",
                            script_content,
                            1
                        )
                        temp_script = temp_path / "xml_to_contpaqi_xls_v2.py"
                        temp_script.write_text(script_content)
                        
                        # Procesar pólizas
                        output_path = temp_path / "output.xls"
                        subprocess.run([
                            sys.executable,
                            str(temp_script),
                            str(temp_template),
                            str(policies_path),
                            str(groups_path),
                            str(output_path)
                        ], check=True, capture_output=True, text=True, cwd=str(temp_path))
                        
                        # Leer archivo final
                        result_bytes = output_path.read_bytes()
                        
                        st.success("✅ Pólizas procesadas exitosamente!")
                        st.download_button(
                            label="📥 Descargar Archivo Procesado",
                            data=result_bytes,
                            file_name="polizas_procesadas.xls",
                            mime="application/vnd.ms-excel",
                            use_container_width=True
                        )
                        
                except subprocess.CalledProcessError as e:
                    st.error(f"❌ Error al procesar las pólizas")
                    st.code(f"Error: {e.stderr}")
                    st.exception(e)
                except Exception as e:
                    st.error(f"❌ Error al procesar las pólizas: {str(e)}")
                    st.exception(e)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>Procesador CONTPAQi v1.0 | Para uso interno</p>
    </div>
    """,
    unsafe_allow_html=True
)

