# 🚀 Deploy en Streamlit Community Cloud

Streamlit Community Cloud es **gratis** y permite desplegar aplicaciones con un solo clic desde GitHub.

## Pasos para Deploy

### 1. Preparar el Repositorio

Asegúrate de que tu repositorio tenga esta estructura:

```
tu-repositorio/
├── Scripts/
│   ├── CuentasOdooToContpaqi/
│   │   ├── entry_to_template.py
│   │   ├── template.xlsx
│   │   ├── SAT.xlsx
│   │   └── MergeAccounts/
│   │       ├── merge_accounts.py
│   │       └── contpaqi_base.xlsx
│   ├── PolizasOdooToContpaqi/
│   │   ├── xml_to_contpaqi_xls_v2.py
│   │   └── template.xlsx
│   └── contpaqi-processor-app/
│       ├── streamlit_app.py  ← Archivo principal
│       ├── requirements.txt
│       └── .streamlit/
│           └── config.toml
└── README.md
```

### 2. Subir a GitHub

Si aún no tienes el código en GitHub:

```bash
# Inicializar repositorio (si no existe)
git init
git add .
git commit -m "Initial commit: Procesador CONTPAQi"

# Crear repositorio en GitHub y luego:
git remote add origin https://github.com/tu-usuario/tu-repositorio.git
git branch -M main
git push -u origin main
```

### 3. Deploy en Streamlit Cloud

1. **Ir a [share.streamlit.io](https://share.streamlit.io)**
2. **Iniciar sesión** con tu cuenta de GitHub
3. **Hacer clic en "New app"**
4. **Configurar:**
   - **Repository**: Seleccionar tu repositorio
   - **Branch**: `main` (o la rama que uses)
   - **Main file path**: `Scripts/contpaqi-processor-app/streamlit_app.py`
5. **Hacer clic en "Deploy!"**

### 4. ¡Listo!

Streamlit Cloud:
- ✅ Instalará automáticamente las dependencias de `requirements.txt`
- ✅ Desplegará la aplicación en una URL pública
- ✅ Actualizará automáticamente cuando hagas push a GitHub

## URL de la Aplicación

Una vez deployado, tendrás una URL como:
```
https://tu-app.streamlit.app
```

Puedes compartir esta URL con tus compañeros. **No necesitan instalar nada**, solo abrir el enlace en su navegador.

## Actualizaciones

Cada vez que hagas cambios y hagas push a GitHub, Streamlit Cloud actualizará automáticamente la aplicación.

## Límites de Streamlit Community Cloud

- ✅ **Gratis** para siempre
- ✅ Aplicaciones públicas (cualquiera con el link puede acceder)
- ✅ Hasta 3 aplicaciones por cuenta
- ⚠️ Límite de uso: 200 horas de CPU/mes (suficiente para uso interno)

## Seguridad

Si quieres restringir el acceso:
- Usar autenticación de Streamlit (requiere cuenta de pago)
- O implementar autenticación básica en el código

## Troubleshooting

### Error: "Module not found"
- Verifica que `requirements.txt` tenga todas las dependencias
- Streamlit Cloud instalará automáticamente lo que esté en requirements.txt

### Error: "File not found"
- Verifica que los scripts estén en las rutas correctas
- Las rutas son relativas al directorio raíz del repositorio

### La aplicación es lenta
- Streamlit Cloud tiene límites de recursos
- Para más recursos, considera Streamlit Cloud for Teams (de pago)

