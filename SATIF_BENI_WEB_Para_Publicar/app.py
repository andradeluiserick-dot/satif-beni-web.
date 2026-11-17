"""SATIF Beni Web — aplicación para publicar en Streamlit Community Cloud."""
from __future__ import annotations

import io
import os
from html import escape
from datetime import datetime, timedelta, timezone
from pathlib import Path

import folium
from folium.plugins import HeatMap, MarkerCluster, Fullscreen
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from core import (BENI_BBOX, SATELLITES, attribute_municipalities,
    load_beni_polygons, parse_hotspots, query_firms, to_geojson, to_kmz, to_shapefile_zip)

ROOT = Path(__file__).resolve().parent
GEOJSON_PATH = ROOT / 'datos' / 'municipios_beni_2024.geojson'
EXAMPLE_PATH = ROOT / 'datos' / 'datos_simulados.csv'

st.set_page_config(page_title='SATIF BENI | Monitoreo de incendios', page_icon='🔥',
                   layout='wide', initial_sidebar_state='expanded')

def get_server_key():
    # Nunca mostrar ni exponer al navegador el secreto del servidor.
    key = os.getenv('NASA_FIRMS_MAP_KEY', '').strip()
    if key:
        return key
    try:
        return str(st.secrets.get('NASA_FIRMS_MAP_KEY', '')).strip()
    except (OSError, FileNotFoundError, Exception):
        return ''

st.markdown('''
<style>
:root {color-scheme:light;}
.block-container {padding-top: 1.25rem; padding-bottom:2rem; max-width:1500px}
.main-title {font-size:2.1rem; font-weight:800; color:#142c29; line-height:1.12}
.eyebrow{font-size:.77rem;font-weight:750;color:#147b67;letter-spacing:.12em}
.subtitle{font-size:.94rem;color:#59736a;margin-top:.5rem}
.topband{border:1px solid #bfe2d5;background:#ecf9f3;border-radius:14px;padding:13px 16px;margin:1rem 0}
.small-note{color:#6a7973;font-size:.81rem}
[data-testid="stMetric"]{background:#ffffff;border:1px solid #dfe9e4;border-radius:14px;padding:10px 14px;}
[data-testid="stMetricLabel"]{color:#55746a;}
[data-testid="stSidebar"]{background:#f4faf6;}
[data-testid="stDataFrame"]{border-radius:10px;}
</style>
''',unsafe_allow_html=True)

@st.cache_data(ttl=12*3600, show_spinner=False)
def get_polygons():
    return load_beni_polygons(GEOJSON_PATH)

@st.cache_data(ttl=12*60, show_spinner=False)
def get_live_data(key, product, days):
    return query_firms(key, product, days)


def format_int(v): return f'{int(v):,}'.replace(',','.')


def status_frp(v):
    """Categorías visuales internas de FRP; NO nivel de riesgo de incendio."""
    if v >= 50: return '#b91c1c', 'FRP 50+ MW'
    if v >= 10: return '#f97316', 'FRP 10–49 MW'
    return '#facc15', 'FRP <10 MW'


def map_view(df, geojson, selected_mun, view):
    m = folium.Map(location=[-13.7,-65.2],zoom_start=7,tiles=None,control_scale=True,
                   prefer_canvas=True)
    folium.TileLayer('OpenStreetMap',name='Calles OSM',control=True).add_to(m)
    folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attr='Esri, Maxar, Earthstar Geographics',name='Satélite (Esri)',overlay=False).add_to(m)
    folium.TileLayer('CartoDB positron',name='Mapa claro',overlay=False).add_to(m)
    if geojson:
        geo = folium.GeoJson(
            geojson, name='Municipios del Beni',
            style_function=lambda f: {
                'color':'#086e64' if selected_mun == 'Todos' or f['properties'].get('nombre_mun') == selected_mun else '#8baa9e',
                'weight':2.4 if selected_mun != 'Todos' and f['properties'].get('nombre_mun') == selected_mun else 1.15,
                'fillColor':'#39ab80' if f['properties'].get('nombre_mun') == selected_mun else '#8bd6b0',
                'fillOpacity':0.17 if selected_mun == 'Todos' or f['properties'].get('nombre_mun') == selected_mun else 0.045,
            },
            tooltip=folium.GeoJsonTooltip(fields=['nombre_mun','nombre_prov'],
                aliases=['Municipio','Provincia'],sticky=False),
        )
        geo.add_to(m)
        # Encuadrar todo el departamento una sola vez: no suponer bordes arbitrarios.
        if selected_mun != 'Todos':
            fmatch = next((f for f in geojson['features'] if f['properties'].get('nombre_mun')==selected_mun),None)
            if fmatch:
                from shapely.geometry import shape
                w,s,e,n = shape(fmatch['geometry']).bounds
                m.fit_bounds([[s,w],[n,e]])
    if not df.empty:
        if view == 'Densidad de detecciones':
            HeatMap(df[['latitude','longitude']].values.tolist(),name='Densidad',radius=18,blur=13,
                    min_opacity=.3).add_to(m)
        else:
            points = MarkerCluster(name='Detecciones satelitales',disableClusteringAtZoom=10)
            for row in df.itertuples(index=False):
                color, group = status_frp(float(row.frp))
                popup = (f'<b>{escape(str(row.municipio))}</b><br>Fecha UTC: {escape(str(row.fecha))}'
                    f'<br>Hora UTC: {escape(str(row.hora_utc))}<br>Satélite: {escape(str(row.satellite))}'
                    f'<br>FRP: {row.frp:.1f} MW<br>Confianza: {escape(str(row.confidence))}'
                    f'<br><small>Detección térmica, no incendio confirmado</small>')
                icon = folium.DivIcon(html=(
                    f'<div style="width:13px;height:13px;background:{color};'
                    'border:1.7px solid white;border-radius:50%;'
                    'box-shadow:0 0 0 1px #42544f77;"></div>'))
                folium.Marker(location=[row.latitude,row.longitude],icon=icon,
                    tooltip=f'{escape(str(row.municipio))} · {escape(str(row.fecha))} · {group}',
                    popup=folium.Popup(popup,max_width=250)).add_to(points)
            points.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    Fullscreen(position='topright').add_to(m)
    return m


st.markdown('<div class="eyebrow">PLATAFORMA WEB DE VIGILANCIA AMBIENTAL · PROTOTIPO INDEPENDIENTE</div>',
            unsafe_allow_html=True)
st.markdown('<div class="main-title">🔥 SATIF BENI <span style="color:#24946a">/</span> Centro de monitoreo</div>',
            unsafe_allow_html=True)
st.markdown('<div class="subtitle">Mapa público de focos de calor del Beni · NASA FIRMS · Descargas para ArcGIS y QGIS</div>',
            unsafe_allow_html=True)

with st.sidebar:
    st.header('⚙️ Fuente de información')
    source = st.radio('Datos de detecciones', ['NASA FIRMS (actualizables)','Subir CSV','Datos simulados (prueba)'],
                      help='Los datos simulados son ficticios; no los uses para decisiones operativas.')
    if st.button('↻ Recargar límites municipales',use_container_width=True,
                 help='Borra la caché e intenta cargar de nuevo la capa municipal.'):
        get_polygons.clear()
        # La caché en servidores gratuitos puede ser efímera; no tocar archivos del proyecto.
        GEOJSON_PATH.unlink(missing_ok=True)
        st.rerun()
    polygons = None
    geo_err = None
    try:
        polygons = get_polygons()
    except Exception as exc:
        geo_err = str(exc)
    if polygons:
        n_mun = len(polygons['features'])
        st.success(f'Límites disponibles · {n_mun} unidades territoriales')
    else:
        st.warning('Sin límites municipales. Se usará un recuadro geográfico aproximado.')
        with st.expander('Cómo resolverlo'):
            st.write('Conéctate a Internet y pulsa «Recargar límites municipales». También puedes descargar el GeoJSON de la fuente indicada en el manual y guardarlo como `datos/municipios_beni_2024.geojson` (filtrado al Beni).')
            st.caption(geo_err or '')
    raw_data = None
    is_simulated = False
    if source == 'NASA FIRMS (actualizables)':
        st.markdown('**Datos cercanos al tiempo real**')
        server_key = get_server_key()
        if server_key:
            st.success('NASA FIRMS configurado para consultas desde la web.')
            api_key = server_key
        else:
            st.caption('Introduce tu MAP_KEY gratuita de NASA FIRMS para hacer consultas.')
            st.markdown('[Obtener MAP_KEY de NASA](https://firms.modaps.eosdis.nasa.gov/api/map_key/)')
            api_key = st.text_input('Tu MAP_KEY',type='password',placeholder='Clave NASA FIRMS')
        instrument_label = st.selectbox('Sensor',list(SATELLITES.keys()),index=0)
        lookback_days = st.slider('Últimos días',min_value=1,max_value=5,value=3)
        if st.button('🔄 Consultar focos en NASA',type='primary',use_container_width=True):
            if not api_key.strip():
                st.error('Introduce tu MAP_KEY antes de consultar.')
            else:
                st.session_state.pop('live_data', None)
                with st.spinner('Consultando detecciones satelitales…'):
                    try:
                        st.session_state['live_data'] = get_live_data(api_key,SATELLITES[instrument_label],lookback_days)
                        st.session_state['live_sensor'] = instrument_label
                        st.session_state['live_update'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
                    except Exception as exc:
                        st.error(f'No se pudo consultar NASA: {exc}')
        if 'live_data' in st.session_state:
            raw_data = st.session_state['live_data']
            st.caption('Última consulta: ' + st.session_state.get('live_update','—') +
                       ' · ' + st.session_state.get('live_sensor','—'))
    elif source == 'Subir CSV':
        uploaded = st.file_uploader('Importa CSV de FIRMS',type=['csv'],
                    help='Columnas: latitude, longitude, acq_date; opcionales acq_time, frp, satellite, confidence.')
        if uploaded is not None:
            try:
                raw_data = parse_hotspots(uploaded)
            except Exception as exc:
                st.error(f'Error en archivo CSV: {exc}')
    else:
        raw_data = parse_hotspots(EXAMPLE_PATH)
        is_simulated = True
        st.warning('Datos totalmente ficticios para verificar el funcionamiento.')
    st.divider()
    st.caption('**Información**')
    st.caption('FIRMS detecta anomalías térmicas por satélite. Un punto no equivale a un incendio confirmado. No es un sistema oficial de alerta ni reemplaza las verificaciones de campo.')

if is_simulated:
    st.error('🧪 MODO DEMOSTRACIÓN: TODOS LOS PUNTOS REPRESENTADOS SON FICTICIOS.',icon='⚠️')
if not polygons:
    st.warning('Los límites municipales no están cargados. Hasta descargarlos, el sistema muestra solo detecciones dentro de una caja aproximada y **no identifica municipios**.')

if raw_data is None:
    st.markdown('''<div class="topband"><b>Para comenzar:</b> selecciona «Datos simulados (prueba)» para explorar el programa inmediatamente, sube un CSV, o introduce tu MAP_KEY y consulta NASA FIRMS.</div>''',unsafe_allow_html=True)
    data = parse_hotspots(pd.DataFrame(columns=['latitude','longitude','acq_date','frp']))
    data['municipio'] = pd.Series(dtype=str)
    data['provincia'] = pd.Series(dtype=str)
else:
    data = attribute_municipalities(raw_data,polygons)

st.markdown('### Área de análisis')
left, mid, right = st.columns([2,1.25,1.25])
with left:
    mun_list = sorted({str(f['properties'].get('nombre_mun','')) for f in polygons['features']}) if polygons else []
    muni = st.selectbox('Municipio o territorio', ['Todos'] + mun_list,
          help='La atribución territorial requiere límites municipales cargados.')
with mid:
    if not data.empty:
        dates = sorted(data['fecha'].dropna().unique())
        picked_dates = st.select_slider('Intervalo de fechas (UTC)', options=dates, value=(dates[0],dates[-1])) if len(dates)>1 else (dates[0],dates[0])
    else:
        st.text_input('Intervalo UTC',value='Sin datos',disabled=True)
        picked_dates = (None,None)
with right:
    display_kind = st.selectbox('Visualización', ['Focos individuales','Densidad de detecciones'])

filtered = data.copy()
if picked_dates[0]:
    filtered = filtered[(filtered['fecha']>=picked_dates[0]) & (filtered['fecha']<=picked_dates[1])]
if muni != 'Todos':
    filtered = filtered[filtered['municipio'] == muni]
filtered = filtered.sort_values('instante_utc',ascending=False)

count = len(filtered)
count_munis = len(set(filtered['municipio'])) if count and polygons else 0
latest = filtered['instante_utc'].max() if count else None
latest_label = latest.strftime('%d/%m/%Y %H:%M UTC') if latest is not None else 'Sin detecciones'
avg_frp = float(filtered['frp'].mean()) if count else 0
k1,k2,k3,k4 = st.columns(4)
k1.metric('Detecciones',format_int(count),help='No es el número de incendios confirmados.')
k2.metric('Municipios con detecciones',format_int(count_munis))
k3.metric('FRP promedio',f'{avg_frp:.1f} MW',help='Potencia radiativa del fuego; depende del producto y condiciones de observación.')
k4.metric('Última detección (UTC)',latest_label)

# Aviso informativo limitado a observaciones reales de las últimas 24 horas.
if source == 'NASA FIRMS (actualizables)' and not filtered.empty:
    cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=24)
    recent_count = int((filtered['instante_utc'] >= cutoff).sum())
    if recent_count:
        st.warning(f'🛰️ Aviso de seguimiento: {format_int(recent_count)} detecciones satelitales en las últimas 24 horas dentro del filtro seleccionado. Verifica en terreno y en fuentes oficiales; no son incendios confirmados.')

st.markdown('### Mapa de focos de calor')
map_data = filtered.head(2500)
if len(filtered)>2500:
    st.info('Se muestran hasta 2.500 detecciones recientes en el mapa para cuidar el rendimiento; las descargas incluyen todas.')
map_col, stats_col = st.columns([3.15,1.1],gap='large')
with map_col:
    st_folium(map_view(map_data,polygons,muni,display_kind),height=530,width=None,
              returned_objects=[],key='mapa_beni')
    st.caption('Coordenadas: WGS84 (EPSG:4326) · Horarios de satélite: UTC · Base cartográfica: OpenStreetMap / Esri.')
with stats_col:
    st.markdown('**Resumen de detecciones**')
    if filtered.empty:
        st.info('No hay puntos para el filtro actual. Esto no prueba ausencia de incendios.')
    else:
        st.markdown('**Por fecha (UTC)**')
        daily = filtered.groupby('fecha').size().rename('Detecciones')
        st.bar_chart(daily,height=205)
        st.markdown('**Municipios principales**')
        if polygons:
            by_muni = filtered.groupby('municipio').size().sort_values(ascending=False).head(8)
            st.bar_chart(by_muni.rename('Detecciones'),height=205,horizontal=True)
        else:
            st.caption('Carga límites para ver estadísticas municipales.')
    st.markdown('''<div style="font-size:.80rem;color:#596f68;padding-top:6px"><b>FRP por colores (orientativo):</b><br>
      🟡 &lt; 10 MW · 🟠 10–49 MW · 🔴 ≥ 50 MW.<br>
      No representa niveles oficiales de peligro ni severidad.</div>''',unsafe_allow_html=True)

st.markdown('### Datos y descargas para SIG')
if not filtered.empty:
    shown_cols = ['fecha','hora_utc','municipio','provincia','latitude','longitude','frp','satellite','confidence']
    st.dataframe(filtered[shown_cols].rename(columns={
      'fecha':'Fecha UTC','hora_utc':'Hora UTC','municipio':'Municipio','provincia':'Provincia',
      'latitude':'Latitud','longitude':'Longitud','frp':'FRP (MW)',
      'satellite':'Satélite','confidence':'Confianza'}),hide_index=True,use_container_width=True,height=280)
    csv_bytes=filtered[shown_cols].to_csv(index=False).encode('utf-8-sig')
    a,b,c,d=st.columns(4)
    a.download_button('⬇ CSV',csv_bytes,file_name='detecciones_beni.csv',mime='text/csv',use_container_width=True)
    b.download_button('⬇ GeoJSON',to_geojson(filtered),file_name='detecciones_beni.geojson',mime='application/geo+json',use_container_width=True)
    c.download_button('⬇ KMZ',to_kmz(filtered),file_name='detecciones_beni.kmz',mime='application/vnd.google-earth.kmz',use_container_width=True)
    d.download_button('⬇ SHP para ArcGIS',to_shapefile_zip(filtered),file_name='focos_beni_shapefile.zip',mime='application/zip',use_container_width=True)
else:
    st.info('Cuando existan registros en el mapa, aquí podrás descargar CSV, GeoJSON, KMZ y Shapefile.')

with st.expander('📘 Metodología, fuentes y límites del prototipo'):
    st.markdown('''
**Fuentes:** [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/area) (detecciones térmicas), y [Lab TecnoSocial / INE / SDSN](https://lab-tecnosocial.github.io/municipios-bolivia-2024/) (límites municipales de referencia).

**Método:** descarga los focos en una caja geográfica que cubre Beni, realiza una intersección punto-en-polígono para incluir solamente detecciones dentro de los municipios/territorios de Beni y ofrece agregación por fecha y municipio. Si falla la descarga de límites, muestra la caja geográfica aproximada, sin asignación municipal.

**Limitaciones:** las detecciones no son incendios confirmados, ni predicciones de peligro. No incorpora clima, combustible, dirección de propagación, áreas quemadas, notificaciones automáticas ni operaciones de emergencia. La cobertura temporal y latencia dependen de NASA. Los límites municipales son referenciales; no resuelven controversias jurisdiccionales.

**SIG:** los resultados se exportan en WGS84 (EPSG:4326). Para trabajar en Guayaramerín con ArcGIS 10.8, puedes reproyectar las capas a WGS 1984 UTM Zone 20S (EPSG:32720). Para otros sectores del Beni verifica la zona UTM correspondiente.

**Uso:** prototipo de desarrollo independiente, sin vinculación institucional con SATIF Santa Cruz ni con la Gobernación del Beni.
    ''')
