"""Página 1: Panel Ganadero — Stock, Faena y Precios.

Muestra los indicadores clave del sector ganadero bovino de San Luis.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from dashboard.components.graficos import (
    cargar_parquet,
    formatear_numero,
    grafico_faena_anual,
    grafico_faena_mensual,
    grafico_precios_categorias,
    grafico_precios_evolucion,
    grafico_ratio_ternero_novillo,
    grafico_stock_evolucion,
    grafico_stock_por_categoria,
    grafico_stock_por_departamento,
)

st.set_page_config(
    page_title="Ganadería — autAnalisis",
    page_icon="🐄",
    layout="wide",
)


# ── Carga de datos ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def cargar_datos():
    return {
        "stock": cargar_parquet("kpi_stock.parquet"),
        "faena_anual": cargar_parquet("kpi_faena_anual.parquet"),
        "faena_mensual": cargar_parquet("kpi_faena_mensual.parquet"),
        "precios_novillo": cargar_parquet("kpi_precios_novillo.parquet"),
        "precios_ratio": cargar_parquet("kpi_precios_ratio.parquet"),
        "compuestos": cargar_parquet("kpi_compuestos.parquet"),
    }


datos = cargar_datos()
comp = datos["compuestos"].dropna(subset=["stock_total_cab"])
ultimo = comp.iloc[-1] if len(comp) > 0 else None
año_actual = int(ultimo["año"]) if ultimo is not None else 2024
años_disponibles = sorted(datos["stock"]["año"].dropna().unique().astype(int).tolist())

# Calcular variación YoY del stock manualmente (no está en compuestos)
stock_anual = datos["stock"].groupby("año")["cabezas"].sum()
var_stock_yoy = None
if len(stock_anual) >= 2:
    var_stock_yoy = (stock_anual.iloc[-1] / stock_anual.iloc[-2] - 1) * 100

# ── Sidebar ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🐄 Ganadería")
    st.markdown("---")
    año_seleccionado = st.selectbox(
        "Año de análisis",
        options=años_disponibles,
        index=años_disponibles.index(año_actual) if año_actual in años_disponibles else 0,
    )

# ── KPI Cards ──────────────────────────────────────────────────────────────

if ultimo is not None:
    st.markdown("### 📊 Indicadores Clave")
    cols = st.columns(5)
    cols[0].metric(
        "Stock Bovino",
        formatear_numero(ultimo["stock_total_cab"], sufijo=" cab"),
        delta=f"{var_stock_yoy:+.1f}%" if var_stock_yoy is not None else None,
    )
    cols[1].metric(
        "Faena Anual",
        formatear_numero(ultimo.get("faena_total_cab", None), sufijo=" cab"),
        delta=f"{ultimo.get('variacion_faena_yoy_pct', 0):+.1f}%"
        if pd.notna(ultimo.get("variacion_faena_yoy_pct"))
        else None,
    )
    cols[2].metric(
        "Tasa de Extracción",
        f"{ultimo.get('tasa_extraccion_pct', 0):.1f}%",
    )
    cols[3].metric(
        "Peso Promedio Carcasa",
        f"{ultimo.get('peso_promedio_kg', 0):.0f} kg",
    )
    cols[4].metric(
        "% Hembras en Faena",
        f"{ultimo.get('participacion_hembras_pct', 0):.1f}%",
    )

st.markdown("---")


# ── Sección 1: Stock Bovino ────────────────────────────────────────────────

st.header("🐮 Stock Bovino")

col1, col2 = st.columns([3, 2])

with col1:
    st.plotly_chart(grafico_stock_evolucion(datos["stock"]), use_container_width=True)

with col2:
    st.plotly_chart(
        grafico_stock_por_categoria(datos["stock"], año_seleccionado),
        use_container_width=True,
    )

st.plotly_chart(
    grafico_stock_por_departamento(datos["stock"], año_seleccionado),
    use_container_width=True,
)

# Tabla resumen de stock
with st.expander("📋 Ver tabla de stock por departamento y categoría"):
    stock_año = datos["stock"][datos["stock"]["año"] == año_seleccionado]
    pivot = stock_año.pivot_table(
        index="departamento", columns="categoria",
        values="cabezas", aggfunc="sum", fill_value=0,
    )
    pivot["Total"] = pivot.sum(axis=1)
    st.dataframe(pivot.style.format("{:,.0f}"), use_container_width=True)


# ── Sección 2: Faena ───────────────────────────────────────────────────────

st.header("🔪 Faena")

col1, col2 = st.columns([3, 2])

with col1:
    st.plotly_chart(grafico_faena_mensual(datos["faena_mensual"]), use_container_width=True)

with col2:
    st.plotly_chart(grafico_faena_anual(datos["faena_anual"]), use_container_width=True)

# Tabla anual de faena
with st.expander("📋 Ver tabla de faena anual"):
    faena_tabla = datos["faena_anual"].copy()
    cols_mostrar = [
        "año", "faena_total_cab", "produccion_total_ton",
        "peso_promedio_kg", "participacion_hembras_pct",
    ]
    faena_tabla = faena_tabla[cols_mostrar].rename(columns={
        "faena_total_cab": "Cabezas",
        "produccion_total_ton": "Prod. (ton)",
        "peso_promedio_kg": "Peso prom. (kg)",
        "participacion_hembras_pct": "% Hembras",
    })
    st.dataframe(
        faena_tabla.style.format({
            "Cabezas": "{:,.0f}",
            "Prod. (ton)": "{:,.1f}",
            "Peso prom. (kg)": "{:.1f}",
            "% Hembras": "{:.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
    )


# ── Sección 3: Precios ─────────────────────────────────────────────────────

st.header("💰 Precios")

col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(
        grafico_precios_evolucion(datos["precios_novillo"]),
        use_container_width=True,
    )

with col2:
    st.plotly_chart(
        grafico_ratio_ternero_novillo(datos["precios_ratio"]),
        use_container_width=True,
    )

st.plotly_chart(
    grafico_precios_categorias(datos["precios_ratio"]),
    use_container_width=True,
)

# Explicación del ratio ternero/novillo
with st.expander("ℹ️ ¿Qué significa la Relación Ternero/Novillo?"):
    st.markdown("""
    La **relación ternero/novillo** es un termómetro del ciclo ganadero argentino:
    - **< 1.10**: Fase de **liquidación** — el productor vende más hembras y terneros, 
      presionando los precios a la baja. Suele ocurrir en sequías.
    - **1.10 — 1.25**: **Ciclo normal** — equilibrio entre cría e invernada.
    - **> 1.25**: Fase de **retención** — el productor retiene vientres para crecer el rodeo.
      Los terneros escasean y su precio sube relativamente.
    """)
