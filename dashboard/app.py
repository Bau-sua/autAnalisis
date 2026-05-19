"""Dashboard principal — autAnalisis San Luis Ganadero.

Panel de control interactivo para monitorear indicadores del sector
ganadero bovino de la provincia de San Luis, Argentina.

Uso:
    uv run streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from dashboard.components.graficos import (
    cargar_parquet,
    formatear_numero,
    grafico_pp_anual,
    grafico_stock_evolucion,
)

st.set_page_config(
    page_title="autAnalisis — San Luis Ganadero",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Carga de datos ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def cargar_datos():
    return {
        "stock": cargar_parquet("kpi_stock.parquet"),
        "compuestos": cargar_parquet("kpi_compuestos.parquet"),
        "faena_anual": cargar_parquet("kpi_faena_anual.parquet"),
        "clima_prov": cargar_parquet("kpi_clima_provincial.parquet"),
        "precios_novillo": cargar_parquet("kpi_precios_novillo.parquet"),
        "precios_ratio": cargar_parquet("kpi_precios_ratio.parquet"),
    }


datos = cargar_datos()
comp = datos["compuestos"].dropna(subset=["stock_total_cab"])
ultimo = comp.iloc[-1] if len(comp) > 0 else None
penultimo = comp.iloc[-2] if len(comp) > 1 else None
año_actual = int(ultimo["año"]) if ultimo is not None else 2024


# ── Sidebar ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image(
        "https://img.icons8.com/color/96/cow.png",
        width=64,
    )
    st.title("autAnalisis")
    st.caption("San Luis — Argentina")
    st.markdown("---")

    st.markdown("### 📑 Navegación")
    st.page_link("app.py", label="🏠 Inicio", icon="🏠")
    st.page_link("pages/1_ganaderia.py", label="🐄 Ganadería", icon="🐄")
    st.page_link("pages/2_clima.py", label="🌧️ Clima", icon="🌧️")
    st.markdown("---")

    st.markdown(f"### 📅 Datos hasta {año_actual}")
    st.caption("Datos sintéticos generados con fines demostrativos.")

    st.markdown("---")
    st.caption("Hecho en San Luis, Argentina 🇦🇷")


# ── Header ─────────────────────────────────────────────────────────────────

st.title("🐄 autAnalisis — San Luis Ganadero")
st.caption(
    "Panel de monitoreo del sector ganadero bovino provincial. "
    "Datos trimestrales/anuales sintetizados a partir de estadísticas públicas."
)

# ── KPI Cards principales ──────────────────────────────────────────────────

if ultimo is not None:
    st.markdown("---")
    st.subheader(f"📊 Resumen {año_actual}")

    col1, col2, col3, col4, col5 = st.columns(5)

    # Deltas: diferencia vs año anterior
    delta_stock = None
    delta_faena = None
    delta_lluvia = None
    if penultimo is not None:
        if pd.notna(ultimo.get("stock_total_cab")) and pd.notna(penultimo.get("stock_total_cab")):
            delta_stock = (ultimo["stock_total_cab"] - penultimo["stock_total_cab"]) / penultimo["stock_total_cab"] * 100
        if pd.notna(ultimo.get("faena_total_cab")) and pd.notna(penultimo.get("faena_total_cab")):
            delta_faena = (ultimo["faena_total_cab"] - penultimo["faena_total_cab"]) / penultimo["faena_total_cab"] * 100
        if pd.notna(ultimo.get("pp_provincial_mm")) and pd.notna(penultimo.get("pp_provincial_mm")):
            delta_lluvia = (ultimo["pp_provincial_mm"] - penultimo["pp_provincial_mm"]) / penultimo["pp_provincial_mm"] * 100

    col1.metric(
        "🐮 Stock Bovino",
        formatear_numero(ultimo["stock_total_cab"], sufijo=" cab"),
        delta=f"{delta_stock:+.1f}%" if delta_stock is not None else None,
    )
    col2.metric(
        "🔪 Faena Anual",
        formatear_numero(ultimo["faena_total_cab"], sufijo=" cab"),
        delta=f"{delta_faena:+.1f}%" if delta_faena is not None else None,
    )
    col3.metric(
        "📈 Tasa de Extracción",
        f"{ultimo.get('tasa_extraccion_pct', 0):.1f}%",
    )
    col4.metric(
        "💧 Precipitación",
        f"{ultimo.get('pp_provincial_mm', 0):.0f} mm" if pd.notna(ultimo.get('pp_provincial_mm')) else "—",
        delta=f"{delta_lluvia:+.0f}%" if delta_lluvia is not None else None,
    )
    # Precio novillo: buscar en kpi_precios_novillo (no en compuestos)
    precios_nov = datos["precios_novillo"]
    precio_novillo_val = precios_nov[precios_nov["año"] == año_actual]["precio_novillo_promedio"]
    if len(precio_novillo_val) > 0 and pd.notna(precio_novillo_val.iloc[0]):
        precio_str = f"${precio_novillo_val.iloc[0]:,.0f}/kg"
    else:
        precio_str = "—"
    col5.metric(
        "💰 Precio Novillo",
        precio_str,
    )


# ── Gráficos principales ───────────────────────────────────────────────────

st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(grafico_stock_evolucion(datos["stock"]), use_container_width=True)

with col2:
    st.plotly_chart(grafico_pp_anual(datos["clima_prov"]), use_container_width=True)


# ── Últimos datos ──────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("📋 Tabla Resumen Anual")

# Construir tabla resumen
tabla = comp[["año", "stock_total_cab", "faena_total_cab",
               "tasa_extraccion_pct", "peso_promedio_kg",
               "participacion_hembras_pct", "pp_provincial_mm"]].copy()
tabla.columns = [
    "Año", "Stock (cab)", "Faena (cab)",
    "Tasa Ext. (%)", "Peso Prom. (kg)",
    "% Hembras", "PP (mm)",
]
tabla["Año"] = tabla["Año"].astype(int)
tabla = tabla.sort_values("Año", ascending=False)

st.dataframe(
    tabla.style.format({
        "Stock (cab)": "{:,.0f}",
        "Faena (cab)": "{:,.0f}",
        "Tasa Ext. (%)": "{:.1f}",
        "Peso Prom. (kg)": "{:.1f}",
        "% Hembras": "{:.1f}",
        "PP (mm)": "{:.0f}",
    }),
    use_container_width=True,
    hide_index=True,
)


# ── Footer ─────────────────────────────────────────────────────────────────

st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📅 Datos generados", "2020 — 2025")
with col2:
    st.metric("📊 Indicadores", "8 KPI + compuestos")
with col3:
    st.metric("📍 Cobertura", "9 departamentos")

st.caption(
    "**autAnalisis** — Proyecto de automatización de reportes y dashboard "
    "para el sector agro-ganadero de San Luis. Datos sintéticos basados en "
    "estadísticas públicas de SENASA, IPCVA, MAGyP y SMN."
)
