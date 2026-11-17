# SATIF BENI — versión web pública v1.1

Aplicación **web** para monitorear detecciones de focos de calor del Beni, Bolivia. Basada en **Streamlit, NASA FIRMS y Folium**. Es un prototipo independiente, no un sistema oficial, y **no confirma incendios**. El servidor tiene que estar conectado a Internet.

## Publicar en Internet — sin instalar Python en la computadora del visitante

**A. Crear repositorio GitHub**

1. Abre https://github.com/new y crea un repositorio, por ejemplo `satif-beni-web` (público o privado, según tu configuración en Streamlit).
2. Usa la opción **Add file > Upload files** para subir los archivos y carpetas de este proyecto a la **raíz** del repositorio: `app.py`, `core.py`, `requirements.txt`, `datos`, `.streamlit`, `.gitignore` y `README.md`. No subas un ZIP sin extraer. En caso de que el navegador o Windows no muestre carpetas ocultas, crea `.streamlit/config.toml` directamente en GitHub y pega su contenido.
3. Haz clic en **Commit changes**.

**B. Publicar en Streamlit Community Cloud**

1. Abre https://share.streamlit.io/ e inicia sesión con GitHub.
2. Selecciona **Create app** → **Yup, I have an app**.
3. Selecciona tu repositorio, rama `main` y archivo principal `app.py`.
4. Elige un subdominio disponible, por ejemplo `satif-beni-monitor` (es solo un ejemplo, no está reservado).
5. Pulsa **Deploy**. La plataforma proporcionará una URL pública real terminada en `.streamlit.app`.

**C. Configurar NASA FIRMS (opcional, recomendado)**

1. Solicita la MAP_KEY gratuita en https://firms.modaps.eosdis.nasa.gov/api/map_key/ .
2. En Streamlit Cloud entra a **App settings → Secrets** (o **Advanced settings → Secrets** durante el despliegue).
3. Pega la línea siguiente, sustituyendo el texto por tu clave real:

   ```toml
   NASA_FIRMS_MAP_KEY = "TU_MAP_KEY_REAL"
   ```

4. Guarda. Con eso los visitantes pueden consultar las detecciones con el botón sin escribir una clave personal. **No introduzcas esta clave en el repositorio, README, pantallas compartidas o código público.** Respeta la cuota y condiciones de NASA FIRMS. Si no configuras una clave del servidor, cada usuario puede introducir su clave personal en la interfaz.

## Funciones

- Mapa interactivo del Beni, modo calles/satélite.
- Datos actuales al consultar NASA FIRMS con clave (1 a 5 días), datos CSV propios o datos simulados claramente etiquetados.
- Filtros por municipio/territorio y fechas UTC, además de mapas de densidad, gráficos y valores FRP.
- Exportación CSV, GeoJSON, KMZ y Shapefile, en WGS84 (EPSG:4326). Puedes reproyectar el SHP en ArcGIS 10.8 a UTM 20S (EPSG:32720) para Guayaramerín cuando corresponda.
- Consulta por Internet desde celular o computadora sin instalar nada en esos dispositivos.

## Fuentes y advertencias

- API NASA FIRMS: https://firms.modaps.eosdis.nasa.gov/api/area
- Límites municipales de referencia (CPV 2024) de Lab TecnoSocial, licencia CC BY 4.0: https://github.com/lab-tecnosocial/municipios-bolivia-2024 . Se obtienen al iniciarse la web; si no hay conexión con la fuente, la plataforma trabaja con un rectángulo aproximado **sin atribución municipal**. No es un límite legal.
- Un foco térmico satelital **no** es un incendio confirmado. La latencia depende de los satélites y del procesamiento. Las horas satelitales se muestran en UTC (Bolivia: UTC–4).
- Esta versión no calcula áreas quemadas, amenazas meteorológicas ni envía alertas automáticas.

## Desarrollo local opcional

```bash
pip install -r requirements.txt
streamlit run app.py
```

Para pruebas: `python -m unittest discover -s pruebas -v`.
