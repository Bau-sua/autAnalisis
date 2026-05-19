"""Página 2: Panel Climático — Precipitaciones y Temperaturas.

Muestra datos climáticos de San Luis y su impacto en la producción ganadera.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from dashboard.components.graficos import (
    cargar_parquet,
    grafico_pp_anomalia_deptos,
    grafico_pp_anual,
    grafico_temperatura_anual,
)

st.set_page_config(
    page_title="Clima — autAnalisis",
    page_icon="🌧️",
    layout="wide",
)


# ── Carga de datos ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def cargar_datos():
    return {
        "clima_provincial": cargar_parquet("kpi_clima_provincial.parquet"),
        "clima_detalle": cargar_parquet("kpi_clima_detalle.parquet"),
        "compuestos": cargar_parquet("kpi_compuestos.parquet"),
    }


datos = cargar_datos()
clima_prov = datos["clima_provincial"]
clima_det = datos["clima_detalle"]
comp = datos["compuestos"].dropna(subset=["stock_total_cab"])

años_disponibles = sorted(clima_det["año"].dropna().unique().astype(int).tolist())
ultimo_año = años_disponibles[-1] if años_disponibles else 2024

# ── Sidebar ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🌧️ Clima")
    st.markdown("---")
    año_seleccionado = st.selectbox(
        "Año de análisis",
        options=años_disponibles,
        index=años_disponibles.index(ultimo_año) if ultimo_año in años_disponibles else 0,
    )

# ── KPI Cards ──────────────────────────────────────────────────────────────

prov_año = clima_prov[clima_prov["año"] == año_seleccionado]
if len(prov_año) > 0:
    row = prov_año.iloc[0]
    st.markdown("### 🌡️ Indicadores Climáticos")
    cols = st.columns(4)
    cols[0].metric(
        "Precipitación Anual",
        f"{row['pp_provincial_mm']:.0f} mm",
        delta=f"{row['anomalia_provincial_pct']:+.0f}% vs media"
        if pd.notna(row.get("anomalia_provincial_pct")) else None,
    )
    cols[1].metric(
        "Temperatura Media",
        f"{row['temp_media_provincial']:.1f} °C",
    )

    # Condición del año
    anomalia = row.get("anomalia_provincial_pct", 0)
    if pd.notna(anomalia):
        if anomalia > 30:
            condicion = "🟢 Año HÚMEDO"
            color = "green"
        elif anomalia < -30:
            condicion = "🔴 Año SECO"
            color = "red"
        else:
            condicion = "🟡 Año NORMAL"
            color = "orange"
        cols[2].metric("Condición", condicion)

    # Relación stock-lluvia
    comp_año = comp[comp["año"] == año_seleccionado]
    if len(comp_año) > 0:
        stock = comp_año.iloc[0].get("stock_total_cab", None)
        if pd.notna(stock):
            cols[3].metric(
                "Stock Bovino",
                f"{stock/1e6:.2f}M cab",
            )

st.markdown("---")


# ── Sección 1: Precipitaciones ─────────────────────────────────────────────

st.header("🌧️ Precipitaciones")

col1, col2 = st.columns([3, 2])

with col1:
    st.plotly_chart(grafico_pp_anual(clima_prov), use_container_width=True)

with col2:
    st.plotly_chart(
        grafico_pp_anomalia_deptos(clima_det, año_seleccionado),
        use_container_width=True,
    )

# Tabla detalle por departamento
with st.expander("📋 Ver detalle de precipitaciones por departamento"):
    det_año = clima_det[clima_det["año"] == año_seleccionado].copy()
    from dashboard.components.graficos import DEPARTAMENTOS
    det_año["Departamento"] = det_año["id_departamento"].map(DEPARTAMENTOS)
    det_año = det_año[[
        "Departamento", "precipitacion_anual_mm", "pp_media_historica",
        "anomalia_pp_mm", "anomalia_pp_pct", "condicion",
    ]].rename(columns={
        "precipitacion_anual_mm": "PP Anual (mm)",
        "pp_media_historica": "Media Hist. (mm)",
        "anomalia_pp_mm": "Anomalía (mm)",
        "anomalia_pp_pct": "Anomalía (%)",
        "condicion": "Condición",
    })
    st.dataframe(
        det_año.style.format({
            "PP Anual (mm)": "{:.0f}",
            "Media Hist. (mm)": "{:.0f}",
            "Anomalía (mm)": "{:+.0f}",
            "Anomalía (%)": "{:+.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
    )


# ── Sección 2: Temperaturas ────────────────────────────────────────────────

st.header("🌡️ Temperaturas")
st.plotly_chart(
    grafico_temperatura_anual(clima_prov),
    use_container_width=True,
)


# ── Sección 3: Impacto de la Sequía ────────────────────────────────────────

st.header("⚠️ Impacto de la Sequía 2022-2023")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### Contexto Regional
    
    Las campañas **2022 y 2023** fueron las más secas en décadas para la 
    provincia de San Luis. La precipitación anual cayó muy por debajo 
    de la media histórica, afectando:
    
    - 🌱 **Pasturas naturales**: reducción severa de la disponibilidad forrajera
    - 🐄 **Condición corporal**: deterioro del rodeo de cría
    - 📉 **Tasa de destete**: caída estimada del 10-15%
    - 🚛 **Movimientos**: aumento de ventas forzadas y traslados
    """)

with col2:
    # Comparar años secos vs normales
    if len(comp) >= 2:
        secos = comp[comp["año"].isin([2022, 2023])]
        resto = comp[~comp["año"].isin([2022, 2023])]

        st.markdown("### Comparación: Años Secos vs Normales")

        if len(secos) > 0 and len(resto) > 0:
            col_a, col_b = st.columns(2)
            stock_seco = secos["stock_total_cab"].mean()
            stock_normal = resto["stock_total_cab"].mean()
            stock_diff = (stock_seco - stock_normal) / stock_normal * 100

            col_a.metric("Stock en sequía", f"{stock_seco/1e6:.2f}M")
            col_b.metric("Stock normal", f"{stock_normal/1e6:.2f}M",
                        delta=f"{stock_diff:+.1f}%")

            pp_seco = secos["pp_provincial_mm"].mean()
            pp_normal = resto["pp_provincial_mm"].mean()
            col_a.metric("Lluvia en sequía", f"{pp_seco:.0f} mm")
            col_b.metric("Lluvia normal", f"{pp_normal:.0f} mm")


# ── Footer ─────────────────────────────────────────────────────────────────

st.markdown("---")
st.caption(
    "Datos sintéticos generados para demostración. Basados en estadísticas "
    "públicas de SENASA, IPCVA, MAGyP y SMN. Proyecto autAnalisis."
)
