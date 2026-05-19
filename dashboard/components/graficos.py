"""Componentes gráficos reutilizables para el dashboard de autAnalisis.

Todas las funciones retornan objetos plotly listos para ser usados con st.plotly_chart().
Los datos se esperan limpios — la lógica de carga y filtrado está en las páginas.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Paleta de colores corporativa ──────────────────────────────────────────

COLOR_PRIMARIO = "#1B4332"  # verde oscuro (pradera)
COLOR_SECUNDARIO = "#2D6A4F"  # verde medio
COLOR_TERCIARIO = "#40916C"  # verde claro
COLOR_ACCENTO = "#D4A373"  # beige/arena
COLOR_PELIGRO = "#BC4749"  # rojo (sequía, alerta)
COLOR_AZUL = "#2E86AB"  # azul (agua)
COLOR_VACA = "#7B4B3A"  # marrón (ganado)

PALETA_VERDES = [
    COLOR_PRIMARIO,
    COLOR_SECUNDARIO,
    COLOR_TERCIARIO,
    "#52B788",
    "#95D5B2",
    "#B7E4C7",
]
PALETA_CATEGORIAS = [
    "#1B4332",
    "#2D6A4F",
    "#40916C",
    "#D4A373",
    "#7B4B3A",
    "#BC4749",
    "#2E86AB",
]

# ── Catálogos estáticos ─────────────────────────────────────────────────────

DEPARTAMENTOS: dict[int, str] = {
    1: "Ayacucho",
    2: "Belgrano",
    3: "Chacabuco",
    4: "Cnel. Pringles",
    5: "Gral. Pedernera",
    6: "Gdor. Dupuy",
    7: "Junín",
    8: "Lib. Gral. San Martín",
    9: "J.M. de Pueyrredón",
}

LAYOUT_BASE = dict(
    template="plotly_white",
    font=dict(family="sans-serif", size=12),
    margin=dict(l=40, r=40, t=80, b=40),
    hovermode="x unified",
)

COLORES_ANOMALIA = {True: COLOR_AZUL, False: COLOR_PELIGRO}
COLOR_SEQUIA = COLOR_PELIGRO
COLOR_HUMEDO = COLOR_AZUL


# ── Carga de datos (cacheada por Streamlit, función pura aquí) ────────────


def cargar_parquet(nombre: str) -> pd.DataFrame:
    """Carga un archivo Parquet desde data/processed/. Ruta relativa al proyecto."""
    root = Path(__file__).resolve().parents[2]
    path = root / "data" / "processed" / nombre
    return pd.read_parquet(path)


# ── Gráficos de Stock ──────────────────────────────────────────────────────


def grafico_stock_evolucion(df: pd.DataFrame) -> go.Figure:
    """Gráfico de líneas: evolución del stock bovino provincial 2020-2024."""
    anual = (
        df.groupby("año", as_index=False)
        .agg(
            total=("cabezas", "sum"),
            variacion=("variacion_provincial_yoy_pct", "first"),
        )
        .dropna(subset=["total"])
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=anual["año"],
            y=anual["total"] / 1e6,
            mode="lines+markers",
            line=dict(color=COLOR_PRIMARIO, width=3),
            marker=dict(size=10, color=COLOR_PRIMARIO),
            name="Stock total",
            hovertemplate="%{x}<br>%{y:.2f}M cabezas<extra></extra>",
        )
    )

    # Barras de variación YoY
    variacion = anual["variacion"].tolist()
    colores_var = [
        COLOR_PELIGRO if v and v < 0 else COLOR_AZUL if v and v > 0 else "#888"
        for v in variacion
    ]
    textos_var = [f"{v:+.1f}%" if pd.notna(v) else "" for v in variacion]

    # Preparar datos para hover de barras (variación como porcentaje legible)
    hover_var = [
        f"Variación: {v:+.1f}%<br>vs año anterior" if pd.notna(v) else ""
        for v in variacion
    ]

    fig.add_trace(
        go.Bar(
            x=anual["año"],
            y=[
                (anual["total"].iloc[i - 1] / 1e6 * (v / 100))
                if i > 0 and pd.notna(v)
                else 0
                for i, v in enumerate(variacion)
            ],
            marker_color=colores_var,
            text=textos_var,
            textposition="auto",
            name="Variación interanual",
            yaxis="y2",
            opacity=0.6,
            hovertemplate="%{x}<br>%{customdata}<extra></extra>",
            customdata=hover_var,
        )
    )

    fig.update_layout(
        **LAYOUT_BASE,
        title="Evolución del Stock Bovino — San Luis",
        xaxis=dict(title="Año", dtick=1),
        yaxis=dict(title="Millones de cabezas", side="left"),
        yaxis2=dict(
            title="",
            overlaying="y",
            side="right",
            showgrid=False,
            showticklabels=False,
            range=[-0.5, None],
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        bargap=0.4,
    )
    return fig


def grafico_stock_por_departamento(df: pd.DataFrame, año: int) -> go.Figure:
    """Barras horizontales: stock bovino por departamento en un año dado."""
    df_año = df[df["año"] == año].copy()
    if df_año.empty:
        fig = go.Figure()
        fig.add_annotation(text=f"Sin datos para {año}", showarrow=False)
        return fig

    depto = df_año.groupby("departamento", as_index=False)["cabezas"].sum()
    depto = depto.sort_values("cabezas", ascending=True)

    fig = px.bar(
        depto,
        x="cabezas",
        y="departamento",
        orientation="h",
        title=f"Stock Bovino por Departamento — {año}",
        color="cabezas",
        color_continuous_scale="Greens",
        text=[f"{v / 1000:,.0f}k" for v in depto["cabezas"]],
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        **LAYOUT_BASE,
        xaxis=dict(title="Cabezas", range=[0, depto["cabezas"].max() * 1.15]),
        yaxis=dict(title=""),
        coloraxis_showscale=False,
        showlegend=False,
    )
    return fig


def grafico_stock_por_categoria(df: pd.DataFrame, año: int) -> go.Figure:
    """Gráfico de torta: composición del stock por categoría en un año dado."""
    df_año = df[df["año"] == año].copy()
    if df_año.empty:
        fig = go.Figure()
        fig.add_annotation(text=f"Sin datos para {año}", showarrow=False)
        return fig

    cat = df_año.groupby("categoria", as_index=False)["cabezas"].sum()
    cat = cat.sort_values("cabezas", ascending=True)

    fig = px.pie(
        cat,
        values="cabezas",
        names="categoria",
        title=f"Composición del Stock por Categoría — {año}",
        color_discrete_sequence=PALETA_CATEGORIAS,
    )
    fig.update_traces(textinfo="label+percent", hole=0.3)
    fig.update_layout(**LAYOUT_BASE, showlegend=False)
    return fig


# ── Gráficos de Faena ──────────────────────────────────────────────────────


def grafico_faena_mensual(df: pd.DataFrame) -> go.Figure:
    """Barras mensuales de faena + línea de media móvil 3 meses."""
    df = df.copy()
    df["fecha"] = pd.to_datetime(
        df["año"].astype(str) + "-" + df["mes"].astype(str) + "-01", errors="coerce"
    )

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["fecha"],
            y=df["faena_mensual_cab"] / 1000,
            name="Faena mensual",
            marker_color=COLOR_VACA,
            marker_opacity=0.7,
            hovertemplate="%{x|%b %Y}<br>%{y:,.1f}k cabezas<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["fecha"],
            y=df["faena_mm3"] / 1000,
            name="Media móvil 3M",
            line=dict(color=COLOR_PELIGRO, width=2.5),
            hovertemplate="%{x|%b %Y}<br>MM3: %{y:,.1f}k<extra></extra>",
        )
    )

    fig.update_layout(
        **LAYOUT_BASE,
        title="Faena Mensual — San Luis",
        xaxis=dict(title="", dtick="M6", tickformat="%b %Y"),
        yaxis=dict(title="Miles de cabezas"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        bargap=0.15,
    )
    return fig


def grafico_faena_anual(df: pd.DataFrame) -> go.Figure:
    """Barras anuales de faena con variación YoY."""
    df = df.copy().dropna(subset=["faena_total_cab"])

    fig = go.Figure()
    max_faena = (df["faena_total_cab"] / 1000).max()
    fig.add_trace(
        go.Bar(
            x=df["año"],
            y=df["faena_total_cab"] / 1000,
            marker_color=COLOR_VACA,
            text=[f"{v / 1000:,.0f}k" for v in df["faena_total_cab"]],
            textposition="auto",
            name="Faena total",
            hovertemplate="%{x}<br>%{y:,.0f}k cabezas<extra></extra>",
        )
    )

    # Anotar variación (offset dinámico basado en el máximo)
    offset = max_faena * 0.05
    for _, row in df.iterrows():
        if pd.notna(row.get("variacion_faena_yoy_pct")):
            color = COLOR_PELIGRO if row["variacion_faena_yoy_pct"] < 0 else COLOR_AZUL
            fig.add_annotation(
                x=row["año"],
                y=row["faena_total_cab"] / 1000 + offset,
                text=f"{row['variacion_faena_yoy_pct']:+.1f}%",
                showarrow=False,
                font=dict(color=color, size=11, weight="bold"),
            )

    fig.update_layout(
        **LAYOUT_BASE,
        title="Faena Anual — San Luis",
        xaxis=dict(title="Año", dtick=1),
        yaxis=dict(title="Miles de cabezas", range=[0, max_faena * 1.2]),
        showlegend=False,
    )
    return fig


# ── Gráficos de Precios ────────────────────────────────────────────────────


def grafico_precios_evolucion(df_novillo: pd.DataFrame) -> go.Figure:
    """Línea de evolución del precio del novillo ($/kg vivo) con variación YoY."""
    df = df_novillo.dropna(subset=["precio_novillo_promedio"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["año"],
            y=df["precio_novillo_promedio"],
            mode="lines+markers+text",
            line=dict(color=COLOR_PRIMARIO, width=3),
            marker=dict(size=8),
            text=[f"${v:,.0f}" for v in df["precio_novillo_promedio"]],
            textposition="top center",
            name="Precio promedio anual",
        )
    )

    # Anotaciones de variación
    for _, row in df.iterrows():
        if pd.notna(row.get("variacion_novillo_yoy_pct")):
            color = (
                COLOR_PELIGRO if row["variacion_novillo_yoy_pct"] < 0 else COLOR_AZUL
            )
            fig.add_annotation(
                x=row["año"],
                y=row["precio_novillo_promedio"] * 1.08,
                text=f"{row['variacion_novillo_yoy_pct']:+.0f}%",
                showarrow=False,
                font=dict(color=color, size=10, weight="bold"),
            )

    fig.update_layout(
        **LAYOUT_BASE,
        title="Precio del Novillo — Promedio Anual ($/kg vivo)",
        xaxis=dict(title="Año", dtick=1),
        yaxis=dict(title="$/kg vivo"),
        showlegend=False,
    )
    return fig


def grafico_precios_categorias(df_ratio: pd.DataFrame) -> go.Figure:
    """Líneas de precio para ternero, novillo y vaca (mensual)."""
    df = df_ratio.copy()
    df["fecha"] = pd.to_datetime(
        df["año"].astype(str) + "-" + df["mes"].astype(str) + "-01", errors="coerce"
    )

    fig = go.Figure()
    for col, nombre, color in [
        ("precio_ternero", "Ternero", COLOR_TERCIARIO),
        ("precio_novillo", "Novillo", COLOR_PRIMARIO),
        ("precio_vaca", "Vaca", COLOR_VACA),
    ]:
        fig.add_trace(
            go.Scatter(
                x=df["fecha"],
                y=df[col],
                mode="lines",
                name=nombre,
                line=dict(color=color, width=2),
                hovertemplate="%{x|%b %Y}<br>"
                + nombre
                + ": $%{y:,.0f}/kg<extra></extra>",
            )
        )

    fig.update_layout(
        **LAYOUT_BASE,
        title="Evolución de Precios por Categoría ($/kg vivo)",
        xaxis=dict(title="", dtick="M6", tickformat="%b %Y"),
        yaxis=dict(title="$/kg vivo"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def grafico_ratio_ternero_novillo(df_ratio: pd.DataFrame) -> go.Figure:
    """Línea del ratio ternero/novillo con bandas de alerta del ciclo ganadero."""
    df = df_ratio.copy()
    df["fecha"] = pd.to_datetime(
        df["año"].astype(str) + "-" + df["mes"].astype(str) + "-01", errors="coerce"
    )

    fig = go.Figure()

    # Bandas de referencia
    fig.add_hrect(
        y0=1.10,
        y1=1.25,
        fillcolor="green",
        opacity=0.1,
        layer="below",
        annotation_text="Ciclo normal",
        annotation_position="top right",
    )
    fig.add_hrect(
        y0=0.90,
        y1=1.10,
        fillcolor="orange",
        opacity=0.1,
        layer="below",
        annotation_text="Liquidación",
        annotation_position="bottom right",
    )
    fig.add_hrect(
        y0=1.25,
        y1=1.50,
        fillcolor=COLOR_PELIGRO,
        opacity=0.1,
        layer="below",
        annotation_text="Retención",
        annotation_position="top right",
    )
    fig.add_hrect(
        y0=1.50,
        y1=5.0,
        fillcolor="darkred",
        opacity=0.08,
        layer="below",
        annotation_text="Retención intensa",
        annotation_position="top right",
    )

    fig.add_trace(
        go.Scatter(
            x=df["fecha"],
            y=df["relacion_ternero_novillo"],
            mode="lines",
            name="Relación Ternero/Novillo",
            line=dict(color=COLOR_PRIMARIO, width=2.5),
            hovertemplate="%{x|%b %Y}<br>Ratio: %{y:.2f}<extra></extra>",
        )
    )

    # Línea de equilibrio (1.15)
    fig.add_hline(
        y=1.15,
        line_dash="dash",
        line_color="gray",
        annotation_text="Equilibrio (1.15)",
        annotation_position="bottom left",
    )

    fig.update_layout(
        **LAYOUT_BASE,
        title="Relación Ternero/Novillo — Termómetro del Ciclo Ganadero",
        xaxis=dict(title="", dtick="M6", tickformat="%b %Y"),
        yaxis=dict(title="Ratio"),
        showlegend=False,
    )
    return fig


# ── Gráficos de Clima ──────────────────────────────────────────────────────


def grafico_pp_anual(df_clima_prov: pd.DataFrame) -> go.Figure:
    """Barras de precipitación anual provincial con anomalía."""
    df = df_clima_prov.dropna(subset=["pp_provincial_mm"])

    colores = []
    textos = []
    for _, row in df.iterrows():
        if row.get("anomalia_provincial_pct", 0) > 15:
            colores.append(COLOR_AZUL)
            textos.append(f"{row['anomalia_provincial_pct']:+.0f}%")
        elif row.get("anomalia_provincial_pct", 0) < -15:
            colores.append(COLOR_PELIGRO)
            textos.append(f"{row['anomalia_provincial_pct']:+.0f}%")
        else:
            colores.append("#AAA")
            textos.append("")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["año"],
            y=df["pp_provincial_mm"],
            marker_color=colores,
            text=[f"{v:,.0f}" for v in df["pp_provincial_mm"]],
            textposition="auto",
            hovertemplate="%{x}<br>%{y:,.0f} mm<extra></extra>",
        )
    )

    # Anotaciones de anomalía (solo valores significativos, posicionadas mejor)
    max_pp = df["pp_provincial_mm"].max()
    offset = max_pp * 0.05  # 5% del valor máximo para espaciado dinámico
    for i, (_, row) in enumerate(df.iterrows()):
        if textos[i] and abs(row.get("anomalia_provincial_pct", 0)) > 15:
            fig.add_annotation(
                x=row["año"],
                y=row["pp_provincial_mm"] + offset,
                text=textos[i],
                showarrow=False,
                font=dict(color=colores[i], size=11, weight="bold"),
            )

    # Media histórica
    media = df["pp_provincial_mm"].mean()
    fig.add_hline(
        y=media,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Media: {media:,.0f} mm",
        annotation_position="right",
    )

    fig.update_layout(
        **LAYOUT_BASE,
        title="Precipitación Anual — San Luis",
        xaxis=dict(title="Año", dtick=1),
        yaxis=dict(title="Milímetros", rangemode="tozero"),
        showlegend=False,
    )
    return fig


def grafico_pp_anomalia_deptos(df_detalle: pd.DataFrame, año: int) -> go.Figure:
    """Barras horizontales: anomalía de precipitación por departamento."""
    df_año = df_detalle[df_detalle["año"] == año].copy()
    if df_año.empty:
        fig = go.Figure()
        fig.add_annotation(text=f"Sin datos para {año}", showarrow=False)
        return fig

    df_año["depto_nombre"] = df_año["id_departamento"].map(DEPARTAMENTOS)
    df_año = df_año.sort_values("anomalia_pp_pct", ascending=True)

    colores = [
        COLOR_AZUL if v > 0 else COLOR_PELIGRO for v in df_año["anomalia_pp_pct"]
    ]

    max_anom = df_año["anomalia_pp_pct"].abs().max()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df_año["depto_nombre"],
            x=df_año["anomalia_pp_pct"],
            orientation="h",
            marker_color=colores,
            text=[f"{v:+.1f}%" for v in df_año["anomalia_pp_pct"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>Anomalía: %{x:+.1f}%<extra></extra>",
        )
    )

    fig.add_vline(x=0, line_width=1, line_color="black")

    fig.update_layout(
        **LAYOUT_BASE,
        title=f"Anomalía de Precipitación por Departamento — {año}",
        xaxis=dict(title="Anomalía (%)", range=[-max_anom * 1.2, max_anom * 1.2]),
        yaxis=dict(title=""),
        showlegend=False,
    )
    return fig


def grafico_temperatura_anual(df_clima_prov: pd.DataFrame) -> go.Figure:
    """Línea de temperatura media anual provincial."""
    df = df_clima_prov.dropna(subset=["temp_media_provincial"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["año"],
            y=df["temp_media_provincial"],
            mode="lines+markers",
            line=dict(color=COLOR_PELIGRO, width=2.5),
            marker=dict(size=8),
            fill="tozeroy",
            fillcolor="rgba(188, 71, 73, 0.1)",
        )
    )

    fig.update_layout(
        **LAYOUT_BASE,
        title="Temperatura Media Anual — San Luis",
        xaxis=dict(title="Año", dtick=1),
        yaxis=dict(title="°C"),
        showlegend=False,
    )
    return fig


# ── KPI Cards ──────────────────────────────────────────────────────────────


def formatear_numero(valor, decimales: int = 1, sufijo: str = "") -> str:
    """Formatea un número para mostrar en cards."""
    if pd.isna(valor):
        return "—"
    if abs(valor) >= 1_000_000:
        return f"{valor / 1_000_000:,.{decimales}f}M{sufijo}"
    if abs(valor) >= 1_000:
        return f"{valor / 1_000:,.{decimales}f}K{sufijo}"
    return f"{valor:,.{decimales}f}{sufijo}"
