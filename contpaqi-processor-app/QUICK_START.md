# 🚀 Inicio Rápido - Deploy en Streamlit Cloud

## Para Compartir con tus Compañeros (5 minutos)

### 1. Subir a GitHub
```bash
# Si ya tienes el código en GitHub, salta este paso
git add .
git commit -m "Add CONTPAQi processor app"
git push
```

### 2. Deploy en Streamlit Cloud

1. Ve a **[share.streamlit.io](https://share.streamlit.io)**
2. Inicia sesión con GitHub
3. Click en **"New app"**
4. Configura:
   - **Repository**: Tu repositorio
   - **Branch**: `main`
   - **Main file path**: `Scripts/contpaqi-processor-app/streamlit_app.py`
5. Click en **"Deploy!"**

### 3. ¡Listo! 🎉

Obtendrás una URL como: `https://tu-app.streamlit.app`

**Comparte esta URL con tus compañeros** - No necesitan instalar nada, solo abrir el link.

## Estructura Requerida en GitHub

Asegúrate de que tu repositorio tenga:

```
tu-repo/
└── Scripts/
    ├── CuentasOdooToContpaqi/
    │   ├── entry_to_template.py
    │   ├── template.xlsx
    │   ├── SAT.xlsx
    │   └── MergeAccounts/
    │       ├── merge_accounts.py
    │       └── contpaqi_base.xlsx
    ├── PolizasOdooToContpaqi/
    │   ├── xml_to_contpaqi_xls_v2.py
    │   └── template.xlsx
    └── contpaqi-processor-app/
        ├── streamlit_app.py  ← Este archivo
        └── requirements.txt
```

## Actualizaciones

Cada vez que hagas `git push`, Streamlit Cloud actualizará automáticamente la app.

## ¿Problemas?

Ver [DEPLOY_STREAMLIT.md](DEPLOY_STREAMLIT.md) para más detalles.

