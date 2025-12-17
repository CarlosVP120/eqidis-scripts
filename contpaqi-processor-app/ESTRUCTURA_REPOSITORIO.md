# 📁 Estructura del Repositorio para GitHub

Esta es la estructura que debe tener tu repositorio en GitHub para que funcione correctamente en Streamlit Cloud:

```
tu-repositorio/
│
├── Scripts/
│   │
│   ├── CuentasOdooToContpaqi/
│   │   ├── entry_to_template.py          ✅ REQUERIDO
│   │   ├── template.xlsx                  ✅ REQUERIDO
│   │   ├── SAT.xlsx                        ✅ REQUERIDO
│   │   └── MergeAccounts/
│   │       ├── merge_accounts.py           ✅ REQUERIDO
│   │       └── contpaqi_base.xlsx         ✅ REQUERIDO
│   │
│   ├── PolizasOdooToContpaqi/
│   │   ├── xml_to_contpaqi_xls_v2.py      ✅ REQUERIDO
│   │   └── template.xlsx                   ✅ REQUERIDO
│   │
│   └── contpaqi-processor-app/
│       ├── streamlit_app.py                ✅ REQUERIDO (archivo principal)
│       ├── requirements.txt                ✅ REQUERIDO
│       ├── README.md
│       ├── DEPLOY_STREAMLIT.md
│       ├── QUICK_START.md
│       └── .streamlit/
│           └── config.toml
│
└── README.md (opcional, del repositorio principal)
```

## ✅ Checklist antes de subir a GitHub

- [ ] Todos los scripts de Python están en `Scripts/CuentasOdooToContpaqi/`
- [ ] Todos los scripts de pólizas están en `Scripts/PolizasOdooToContpaqi/`
- [ ] El archivo `streamlit_app.py` está en `Scripts/contpaqi-processor-app/`
- [ ] El archivo `requirements.txt` está presente
- [ ] Los archivos `.xlsx` necesarios están incluidos (template.xlsx, SAT.xlsx, contpaqi_base.xlsx)
- [ ] No hay archivos temporales o de build (build/, dist/, .venv/, etc.)

## 📝 Archivos que NO deben subirse

Agrega esto a tu `.gitignore`:

```
# Python
__pycache__/
*.py[cod]
.venv/
venv/

# Build
build/
dist/
*.spec

# OS
.DS_Store
Thumbs.db

# Streamlit
.streamlit/secrets.toml
```

## 🚀 Configuración en Streamlit Cloud

Cuando despliegues en Streamlit Cloud, configura:

- **Main file path**: `Scripts/contpaqi-processor-app/streamlit_app.py`
- **Python version**: 3.8 o superior (se detecta automáticamente)

## ⚠️ Importante

- Los archivos `.xlsx` (template.xlsx, SAT.xlsx, contpaqi_base.xlsx) **DEBEN estar en el repositorio**
- Las rutas en `streamlit_app.py` asumen que los scripts están en `../CuentasOdooToContpaqi` y `../PolizasOdooToContpaqi`
- Si cambias la estructura, actualiza las rutas en `streamlit_app.py`

