#!/usr/bin/env python3
"""
entry_to_template.py

Uso:
  ([ -d .venv ] || python3 -m venv .venv) && source .venv/bin/activate && python -m pip install -U pip pandas openpyxl && python3 entry_to_template.py template.xlsx entry.xlsx output.xlsx

Si ya tienes el entorno:
  source .venv/bin/activate && python3 entry_to_template.py template.xlsx entry.xlsx output.xlsx

Requisitos:
  pip install pandas openpyxl
(La plantilla debe estar en .xlsx para conservar encabezados/estilos.)
"""

import sys, re, os
from datetime import datetime
import pandas as pd
from openpyxl import load_workbook

TOTAL_DIGITS = 8

# Mapeo de secciones a valores Tipo
TIPO_MAPPING = {
    1: {"deudora": "A", "acreedora": "B", "default": "A", "l_row": 4},
    2: {"deudora": "C", "acreedora": "D", "default": "D", "l_row": 6},
    3: {"deudora": "E", "acreedora": "F", "default": "F", "l_row": 8},
    4: {"deudora": "G", "acreedora": "H", "default": "H", "l_row": 10},
    5: {"deudora": "G", "acreedora": "H", "default": "G", "l_row": 10},
    6: {"deudora": "G", "acreedora": "H", "default": "G", "l_row": 10},
    7: {"deudora": "G", "acreedora": "H", "default": "G", "l_row": 10},
    8: {"deudora": "K", "acreedora": "L", "default": "L", "l_row": 18},
}

def find_columns(df):
    low = [str(c).lower().strip() for c in df.columns]
    code_idx = next((i for i,s in enumerate(low) if "cod" in s or "clave" in s), None) or 0
    name_idx = next((i for i,s in enumerate(low) if "nombre" in s or "cuenta" in s), None) or (1 if df.shape[1] > 1 else 0)
    tipo_idx = next((i for i,s in enumerate(low) if "tipo" in s), None)
    return code_idx, name_idx, tipo_idx

def extract_code_from_name(name):
    if not isinstance(name, str): return None, name
    m = re.match(r'^\s*([0-9]+(?:\.[0-9]+)*)\s+(.+)$', name)
    return (m.group(1).strip(), m.group(2).strip()) if m else (None, name.strip())

def sanitize_code_str(s):
    if not s: return ""
    s = re.sub(r'[^0-9\.]', '', str(s).strip())
    return re.sub(r'(?:\.0)+$', '', s)

def normalize_code(raw_code, total_digits=TOTAL_DIGITS):
    if not raw_code:
        return "0" * total_digits
    clean_code = re.sub(r'[^0-9]', '', str(raw_code))
    return clean_code.ljust(total_digits, "0") if clean_code else "0" * total_digits

def get_first_digit(text):
    """Obtiene el primer dígito de un texto"""
    if not text or not str(text).strip():
        return None
    first_char = str(text).strip()[0]
    return int(first_char) if first_char.isdigit() and first_char in "12345678" else None

def calculate_tipo(codigo, nombre, g_val, h_val):
    """Calcula el valor de Tipo basándose en la sección y valores G/H"""
    digit = get_first_digit(nombre) or get_first_digit(codigo)
    if not digit or digit not in TIPO_MAPPING:
        return "A"
    
    mapping = TIPO_MAPPING[digit]
    if g_val > h_val:
        return mapping["deudora"]
    elif h_val > g_val:
        return mapping["acreedora"]
    else:
        return mapping["default"]

def read_sat_lookup(sat_file_path):
    """Lee el archivo SAT.xlsx y retorna un diccionario nombre -> (nivel, codigo)"""
    try:
        wb = load_workbook(sat_file_path, data_only=False)
        ws = wb.active
        
        # Encontrar columnas
        headers = {str(ws.cell(1, col).value).lower().strip(): col 
                  for col in range(1, ws.max_column + 1) if ws.cell(1, col).value}
        
        nombre_col = next((headers[k] for k in headers if 'nombre' in k), None)
        nivel_col = next((headers[k] for k in headers if 'nivel' in k), None)
        codigo_col = next((headers[k] for k in headers if 'codigo' in k or 'código' in k), None)
        
        sat_lookup = {}
        for row in range(2, ws.max_row + 1):
            nombre = str(ws.cell(row, nombre_col).value).strip() if nombre_col and ws.cell(row, nombre_col).value else ""
            nivel = str(ws.cell(row, nivel_col).value).strip() if nivel_col and ws.cell(row, nivel_col).value else ""
            
            # Leer código preservando formato
            codigo = ""
            if codigo_col:
                cell = ws.cell(row, codigo_col)
                if cell.value is not None:
                    if cell.data_type == 's':
                        codigo = str(cell.value).strip()
                    elif isinstance(cell.value, (int, float)):
                        num_format = getattr(cell, 'number_format', '')
                        if num_format and '.' in num_format:
                            decimal_part = num_format.split('.')[-1].split(';')[0]
                            num_decimals = len([c for c in decimal_part if c in '0#?'])
                            codigo = f"{cell.value:.{num_decimals}f}" if num_decimals > 0 else str(int(cell.value))
                        else:
                            codigo = str(cell.value).strip()
                    else:
                        codigo = str(cell.value).strip()
            
            if nombre:
                sat_lookup[nombre.lower()] = (nivel, codigo)
        
        wb.close()
        return sat_lookup
    except Exception as e:
        print(f"⚠️ No se pudo leer el archivo SAT.xlsx: {e}")
        return {}

def read_entry_data(entry_path, df, name_idx):
    """Lee indents y valores G/H del archivo entry"""
    wb = load_workbook(entry_path, data_only=True)
    ws = wb.active
    indents, g_values, h_values = [], [], []
    
    for i in range(len(df)):
        row_num = i + 2
        name_col = (name_idx + 1) if name_idx is not None else 1
        
        # Leer indent
        cell = ws.cell(row=row_num, column=name_col)
        indent_val = cell.alignment.indent if cell and cell.alignment else 0
        raw_text = str(cell.value) if cell.value else ""
        leading_spaces = len(raw_text) - len(raw_text.lstrip(' '))
        indent_level = max(1, leading_spaces // 2) if indent_val == 0 and leading_spaces > 0 else indent_val + 1
        indents.append(indent_level)
        
        # Leer G y H
        g_val = float(ws.cell(row=row_num, column=7).value or 0)
        h_val = float(ws.cell(row=row_num, column=8).value or 0)
        g_values.append(g_val)
        h_values.append(h_val)
    
    wb.close()
    return indents, g_values, h_values

def build_catalog_rows(entry_path):
    df = pd.read_excel(entry_path, dtype=str, keep_default_na=False)
    code_idx, name_idx, tipo_idx = find_columns(df)
    
    # Leer SAT
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sat_lookup = read_sat_lookup(os.path.join(script_dir, 'SAT.xlsx'))
    
    # Leer datos del entry
    indents, g_values, h_values = read_entry_data(entry_path, df, name_idx)
    
    rows = []
    today = datetime.today().strftime("%Y%m%d")
    parent_code_by_indent = {}
    parent_name_by_indent = {}
    
    for i in range(len(df)):
        # Leer y procesar código y nombre
        raw_code_cell = str(df.iat[i, code_idx]).strip() if code_idx < df.shape[1] and not pd.isna(df.iat[i, code_idx]) else ""
        name_cell = str(df.iat[i, name_idx]).strip() if name_idx < df.shape[1] and not pd.isna(df.iat[i, name_idx]) else ""
        
        raw_code = sanitize_code_str(raw_code_cell)
        name = name_cell
        
        if not raw_code:
            extracted, cleaned_name = extract_code_from_name(name_cell)
            if extracted:
                raw_code = sanitize_code_str(extracted)
                name = cleaned_name
            else:
                continue
        else:
            m = re.match(r'^\s*' + re.escape(raw_code) + r'\s+(.+)$', name_cell)
            if m:
                name = m.group(1).strip()
        
        if not raw_code:
            continue
        
        # Calcular Tipo
        tipo_cell = calculate_tipo(raw_code, name, g_values[i] if i < len(g_values) else 0.0, h_values[i] if i < len(h_values) else 0.0)
        
        # Procesar jerarquía
        indent_level = indents[i] if i < len(indents) else 1
        codigo_normalizado = normalize_code(raw_code)
        parent_raw = parent_code_by_indent.get(indent_level - 1) if indent_level > 1 else None
        cta_sup = normalize_code(parent_raw) if parent_raw else "0" * TOTAL_DIGITS
        
        # Actualizar padres
        parent_code_by_indent[indent_level] = raw_code
        parent_name_by_indent[indent_level] = name
        for k in list(parent_code_by_indent.keys()):
            if k > indent_level:
                del parent_code_by_indent[k]
                del parent_name_by_indent[k]
        
        # Buscar en SAT
        nombre_busqueda = name.strip().lower()
        if nombre_busqueda in sat_lookup:
            nivel_sat, codigo_sat = sat_lookup[nombre_busqueda]
            cta_mayor = int(nivel_sat) if nivel_sat else 2
            id_agrupador = codigo_sat or ""
            found_in_sat = True
        else:
            cta_mayor = 2
            parent_name = parent_name_by_indent.get(indent_level - 1) if indent_level > 1 else None
            if parent_name and parent_name.strip().lower() in sat_lookup:
                _, parent_codigo_sat = sat_lookup[parent_name.strip().lower()]
                id_agrupador = parent_codigo_sat or ""
                found_in_sat = False
            else:
                id_agrupador = ""
                found_in_sat = None
        
        rows.append({
            'data': ["C", codigo_normalizado, name, name, cta_sup, tipo_cell, 0, cta_mayor, 0, today, 11, 1, 0, 0, 0, 0, id_agrupador],
            'found_in_sat': found_in_sat
        })
    
    return rows

def append_rows_to_template(template_path, rows, output_path):
    from openpyxl.styles import PatternFill
    
    wb = load_workbook(template_path)
    ws = wb.active
    
    yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
    red_fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
    
    for row_info in rows:
        row_data = row_info['data']
        found_in_sat = row_info['found_in_sat']
        ws.append(row_data)
        
        if found_in_sat is None:
            row_num = ws.max_row
            for col in range(1, len(row_data) + 1):
                ws.cell(row=row_num, column=col).fill = red_fill
        elif found_in_sat is False:
            row_num = ws.max_row
            for col in range(1, len(row_data) + 1):
                ws.cell(row=row_num, column=col).fill = yellow_fill
    
    wb.save(output_path)

def preprocess_entry_file(entry_path):
    """Preprocesa entry.xlsx: elimina filas, agrega columna Tipo con fórmulas y tabla de referencia"""
    wb = load_workbook(entry_path, data_only=False)
    ws = wb.active
    
    if ws.max_row < 5:
        print(f"⚠️ Advertencia: El archivo tiene muy pocas filas ({ws.max_row}). No se puede preprocesar correctamente.")
        wb.close()
        return
    
    # Eliminar filas
    for _ in range(3):
        if ws.max_row > 0:
            ws.delete_rows(ws.max_row)
    if ws.max_row >= 2:
        ws.delete_rows(1, 2)
    
    # Agregar encabezado Tipo
    ws.cell(row=1, column=9, value="Tipo")
    
    # Agregar tabla de referencia
    referencia_data = [
        ("A", "Activo Deudora"), ("B", "Activo Acreedora"), ("C", "Pasivo Deudora"), ("D", "Pasivo Acreedora"),
        ("E", "Capital Deudora"), ("F", "Capital Acredora"), ("G", "Resultados Deudora"), ("H", "Resultados Acreedora"),
        ("K", "Orden Deudora"), ("L", "Orden Acreedora"),
    ]
    for i, (letra, descripcion) in enumerate(referencia_data, start=4):
        ws.cell(row=i, column=12, value=letra)
        ws.cell(row=i, column=13, value=descripcion)
    
    # Agregar fórmulas Tipo
    for row_num in range(2, ws.max_row + 1):
        codigo = str(ws.cell(row=row_num, column=1).value or "")
        nombre = str(ws.cell(row=row_num, column=2).value or "")
        
        digit = get_first_digit(nombre) or get_first_digit(codigo)
        
        if digit and digit in TIPO_MAPPING:
            mapping = TIPO_MAPPING[digit]
            l_deudora = mapping["l_row"]
            l_acreedora = mapping["l_row"] + 1
            default_value = mapping["default"]
            first_char = str(digit)
            
            formula = f'=IFERROR(IF(MID(B{row_num},1,1)="{first_char}",IF(G{row_num}>H{row_num},$L${l_deudora},IF(H{row_num}>G{row_num},$L${l_acreedora},NA())),IF(MID(A{row_num},1,1)="{first_char}",IF(G{row_num}>H{row_num},$L${l_deudora},IF(H{row_num}>G{row_num},$L${l_acreedora},NA())))),"{default_value}")'
        else:
            formula = '="A"'
        
        ws.cell(row=row_num, column=9).value = formula
    
    wb.save(entry_path)
    wb.close()
    print(f"✅ Archivo entry.xlsx preprocesado: eliminadas 2 primeras y 3 últimas filas, agregadas columnas I, L y M")

def main(template_path, entry_path, output_path):
    preprocess_entry_file(entry_path)
    rows = build_catalog_rows(entry_path)
    append_rows_to_template(template_path, rows, output_path)
    print(f"✅ Generado {output_path} con {len(rows)} filas tipo 'C'.")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: ([ -d .venv ] || python3 -m venv .venv) && source .venv/bin/activate && python -m pip install -U pip pandas openpyxl && python3 entry_to_template.py template.xlsx entry.xlsx output.xlsx")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
