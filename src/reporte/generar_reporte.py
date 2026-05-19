"""Generador de informes automáticos trimestrales y anuales.

Carga KPIs desde data/processed/, genera gráficos con matplotlib,
renderiza templates Jinja2 en Markdown y convierte a PDF con WeasyPrint.

Uso:
    uv run python src/reporte/generar_reporte.py --tipo anual --año 2024
    uv run python src/reporte/generar_reporte.py --tipo trimestral --año 2024 --trimestre 4
"""

import argparse
import base64
import io
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from jinja2 import Environment, FileSystemLoader

from src.utils.config import PROCESSED_DIR, REPORTS_DIR
from src.utils.logging_config import setup_logging
from src.reporte.narrativa import generar_narrativa

matplotlib.use("Agg")  # Non-interactive backend
plt.rcParams["figure.dpi"] = 150
plt.rcParams["font.size"] = 10

logger = setup_logging(modulo="reporte")

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
COLOR_PRIMARIO = "#1B4332"
COLOR_SECUNDARIO = "#2D6A4F"
COLOR_PELIGRO = "#BC4749"
COLOR_AZUL = "#2E86AB"
COLOR_ARENA = "#D4A373"


# ── Carga de datos ─────────────────────────────────────────────────────────


def cargar_kpis() -> dict[str, pd.DataFrame]:
    """Carga todos los KPIs desde data/processed/."""
    kpis = {}
    for path in sorted(PROCESSED_DIR.glob("*.parquet")):
        nombre = path.stem
        kpis[nombre] = pd.read_parquet(path)
    return kpis


# ── Gráficos para reportes ─────────────────────────────────────────────────


def _fig_a_base64(fig: plt.Figure) -> str:
    """Convierte una figura matplotlib a string base64 para embed en Markdown."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{b64}"


def grafico_stock_evolucion_reporte(
    kpi_stock: pd.DataFrame,
) -> str:
    """Gráfico de barras: evolución del stock total 2020-2024."""
    stock_anual = kpi_stock.groupby("año")["cabezas"].sum().reset_index()
    stock_anual = stock_anual.dropna(subset=["cabezas"])

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(
        stock_anual["año"].astype(int),
        stock_anual["cabezas"] / 1e6,
        color=COLOR_PRIMARIO,
        edgecolor="white",
    )
    for bar in bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.01,
            f"{bar.get_height():.2f}M",
            ha="center",
            fontsize=8,
        )
    ax.set_title("Evolución del Stock Bovino — San Luis", fontweight="bold")
    ax.set_ylabel("Millones de cabezas")
    ax.set_xlabel("")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1fM"))
    return _fig_a_base64(fig)


def grafico_faena_mensual_reporte(
    kpi_faena_mensual: pd.DataFrame, año: int
) -> str:
    """Gráfico de faena mensual para un año específico."""
    df = kpi_faena_mensual[kpi_faena_mensual["año"] == año].copy()
    if df.empty:
        return ""

    meses_nombres = [
        "Ene", "Feb", "Mar", "Abr", "May", "Jun",
        "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
    ]
    df["mes_label"] = df["mes"].apply(lambda m: meses_nombres[int(m) - 1] if pd.notna(m) else "")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(df["mes_label"], df["faena_mensual_cab"] / 1000, color=COLOR_SECUNDARIO, edgecolor="white")
    ax.plot(
        df["mes_label"],
        df["faena_mm3"] / 1000,
        color=COLOR_PELIGRO,
        linewidth=2,
        marker="o",
        markersize=4,
        label="Media móvil 3M",
    )
    ax.set_title(f"Faena Mensual {año} — San Luis", fontweight="bold")
    ax.set_ylabel("Miles de cabezas")
    ax.legend(fontsize=8)
    return _fig_a_base64(fig)


def grafico_precios_reporte(
    kpi_precios_novillo: pd.DataFrame,
) -> str:
    """Gráfico de evolución del precio del novillo."""
    df = kpi_precios_novillo.dropna(subset=["precio_novillo_promedio"])

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.fill_between(
        df["año"].astype(int),
        df["precio_novillo_promedio"],
        alpha=0.3,
        color=COLOR_ARENA,
    )
    ax.plot(
        df["año"].astype(int),
        df["precio_novillo_promedio"],
        color=COLOR_PELIGRO,
        linewidth=2.5,
        marker="s",
        markersize=6,
    )
    # Etiquetas de precio
    for _, row in df.iterrows():
        ax.annotate(
            f"${row['precio_novillo_promedio']:,.0f}",
            (int(row["año"]), row["precio_novillo_promedio"]),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=8,
        )
    ax.set_title("Evolución del Precio del Novillo ($/kg vivo)", fontweight="bold")
    ax.set_ylabel("$/kg vivo")
    ax.set_xlabel("")
    return _fig_a_base64(fig)


def grafico_clima_reporte(
    kpi_clima_prov: pd.DataFrame,
) -> str:
    """Gráfico de precipitación anual con anomalías."""
    df = kpi_clima_prov.dropna(subset=["pp_provincial_mm"])

    colores = [
        COLOR_AZUL if row["anomalia_provincial_pct"] > 0 else COLOR_PELIGRO
        for _, row in df.iterrows()
    ]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(df["año"].astype(int), df["pp_provincial_mm"], color=colores, edgecolor="white")
    # Línea de media
    media = df["pp_provincial_mm"].mean()
    ax.axhline(y=media, color="gray", linestyle="--", linewidth=1, label=f"Media: {media:.0f} mm")
    ax.set_title("Precipitación Anual — San Luis", fontweight="bold")
    ax.set_ylabel("mm")
    ax.legend(fontsize=8)
    return _fig_a_base64(fig)


def grafico_stock_por_categoria_reporte(
    kpi_stock: pd.DataFrame, año: int
) -> str:
    """Gráfico de torta: composición del stock por categoría."""
    df = kpi_stock[kpi_stock["año"] == año].copy()
    if df.empty:
        return ""

    comp = df.groupby("categoria")["cabezas"].sum()
    colores = [COLOR_PRIMARIO, COLOR_SECUNDARIO, COLOR_ARENA, COLOR_AZUL, COLOR_PELIGRO, "#7B4B3A", "#95D5B2"]

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(
        comp.values,
        labels=comp.index,
        autopct="%1.1f%%",
        colors=colores[: len(comp)],
        startangle=90,
        textprops={"fontsize": 8},
    )
    ax.set_title(f"Composición del Stock por Categoría — {año}", fontweight="bold")
    return _fig_a_base64(fig)


# ── Construcción de contexto para templates ────────────────────────────────


def _fmt_num(valor: Any, dec: int = 1, sufijo: str = "") -> str:
    """Formatea número con separador de miles y decimales."""
    if pd.isna(valor) or valor is None:
        return "—"
    return f"{float(valor):,.{dec}f}{sufijo}"


def _fmt_pct(valor: Any) -> str:
    """Formatea porcentaje."""
    if pd.isna(valor) or valor is None:
        return "—"
    return f"{float(valor):+.1f}%"


def construir_contexto_anual(kpis: dict, año: int) -> dict:
    """Construye el diccionario de contexto para el template anual."""
    stock = kpis.get("kpi_stock")
    faena_anual = kpis.get("kpi_faena_anual")
    faena_mensual = kpis.get("kpi_faena_mensual")
    precios_novillo = kpis.get("kpi_precios_novillo")
    precios_ratio = kpis.get("kpi_precios_ratio")
    clima_prov = kpis.get("kpi_clima_provincial")
    clima_det = kpis.get("kpi_clima_detalle")
    compuestos = kpis.get("kpi_compuestos")

    ctx: dict[str, Any] = {
        "titulo": f"Informe Ganadero Anual — San Luis {año}",
        "fecha_generacion": datetime.now().strftime("%d/%m/%Y"),
        "año": año,
        "tipo": "anual",
    }

    # Stock
    if stock is not None:
        stock_anual = stock.groupby("año")["cabezas"].sum()
        ctx["stock_total"] = _fmt_num(stock_anual.get(año), 0, " cabezas")
        ctx["grafico_stock_evolucion"] = grafico_stock_evolucion_reporte(stock)
        ctx["grafico_stock_categoria"] = grafico_stock_por_categoria_reporte(stock, año)

        # Variación YoY
        if año in stock_anual.index and (año - 1) in stock_anual.index:
            var = (stock_anual[año] / stock_anual[año - 1] - 1) * 100
            ctx["stock_var_yoy"] = _fmt_pct(var)
        else:
            ctx["stock_var_yoy"] = "—"

        # Top departamentos
        stock_año = stock[stock["año"] == año]
        top_deptos = (
            stock_año.groupby("departamento")["cabezas"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
        )
        ctx["top_deptos"] = [
            {"nombre": d, "cabezas": _fmt_num(v, 0)} for d, v in top_deptos.items()
        ]

    # Faena
    if faena_anual is not None:
        fa = faena_anual[faena_anual["año"] == año]
        if not fa.empty:
            row = fa.iloc[0]
            ctx["faena_total"] = _fmt_num(row["faena_total_cab"], 0, " cabezas")
            ctx["faena_var_yoy"] = _fmt_pct(row.get("variacion_faena_yoy_pct"))
            ctx["faena_peso_promedio"] = _fmt_num(row["peso_promedio_kg"], 1, " kg")
            ctx["faena_produccion"] = _fmt_num(row["produccion_total_ton"], 0, " ton")
            ctx["faena_hembras_pct"] = _fmt_num(row.get("participacion_hembras_pct"), 1, "%")

    if faena_mensual is not None:
        ctx["grafico_faena_mensual"] = grafico_faena_mensual_reporte(faena_mensual, año)

    # Precios
    if precios_novillo is not None:
        pn = precios_novillo[precios_novillo["año"] == año]
        if not pn.empty:
            row = pn.iloc[0]
            ctx["precio_novillo_prom"] = _fmt_num(row["precio_novillo_promedio"], 0, " $/kg")
            ctx["precio_novillo_dic"] = _fmt_num(row.get("precio_novillo_dic"), 0, " $/kg")
            ctx["precio_var_yoy"] = _fmt_pct(row.get("variacion_novillo_yoy_pct"))
        ctx["grafico_precios"] = grafico_precios_reporte(precios_novillo)

    if precios_ratio is not None:
        pr = precios_ratio[precios_ratio["año"] == año]
        if not pr.empty:
            ctx["ratio_ternero_novillo"] = _fmt_num(
                pr["relacion_ternero_novillo"].mean(), 2
            )
            ctx["ratio_vaca_novillo"] = _fmt_num(
                pr["relacion_vaca_novillo"].mean(), 2
            )

    # Clima
    if clima_prov is not None:
        cp = clima_prov[clima_prov["año"] == año]
        if not cp.empty:
            row = cp.iloc[0]
            ctx["pp_anual"] = _fmt_num(row["pp_provincial_mm"], 0, " mm")
            ctx["pp_anomalia"] = _fmt_pct(row.get("anomalia_provincial_pct"))
            ctx["temp_media"] = _fmt_num(row.get("temp_media_provincial"), 1, " °C")
        ctx["grafico_clima"] = grafico_clima_reporte(clima_prov)

    if clima_det is not None:
        cd = clima_det[clima_det["año"] == año]
        if not cd.empty:
            seco = cd[cd["anomalia_pp_pct"] < -30]
            if not seco.empty:
                ctx["deptos_secos"] = [
                    f"{row['id_departamento']}" for _, row in seco.iterrows()
                ]

    # Compuestos
    if compuestos is not None:
        comp = compuestos[compuestos["año"] == año]
        if not comp.empty:
            row = comp.iloc[0]
            ctx["tasa_extraccion"] = _fmt_num(row.get("tasa_extraccion_pct"), 1, "%")

    return ctx


def construir_contexto_trimestral(kpis: dict, año: int, trimestre: int) -> dict:
    """Construye el diccionario de contexto para el template trimestral."""
    # Para simplificar, usamos el contexto anual + filtro trimestral
    ctx = construir_contexto_anual(kpis, año)
    ctx["titulo"] = f"Informe Ganadero Trimestral — San Luis Q{trimestre} {año}"
    ctx["tipo"] = "trimestral"
    ctx["trimestre"] = trimestre

    meses = {1: [1, 2, 3], 2: [4, 5, 6], 3: [7, 8, 9], 4: [10, 11, 12]}
    ctx["meses_trimestre"] = meses.get(trimestre, [])

    # Faena trimestral
    faena_mensual = kpis.get("kpi_faena_mensual")
    if faena_mensual is not None:
        ft = faena_mensual[
            (faena_mensual["año"] == año) & (faena_mensual["mes"].isin(meses.get(trimestre, [])))
        ]
        if not ft.empty:
            ctx["faena_trimestral"] = _fmt_num(ft["faena_mensual_cab"].sum(), 0, " cabezas")
            ctx["produccion_trimestral"] = _fmt_num(ft["produccion_mensual_ton"].sum(), 0, " ton")

    return ctx


# ── Renderizado ────────────────────────────────────────────────────────────


def generar_reporte(
    tipo: str = "anual",
    año: int = 2024,
    trimestre: int | None = None,
    salida_md: Path | None = None,
    salida_pdf: Path | None = None,
) -> Path:
    """Genera un informe en Markdown y opcionalmente PDF.

    Args:
        tipo: "anual" o "trimestral".
        año: Año del informe.
        trimestre: Trimestre (1-4), solo para tipo trimestral.
        salida_md: Ruta de salida Markdown. Si es None, se genera automáticamente.
        salida_pdf: Ruta de salida PDF. Si es None, no se genera PDF.

    Returns:
        Ruta del archivo Markdown generado.
    """
    logger.info("Generando informe %s — %d", tipo, año)

    kpis = cargar_kpis()

    # Construir contexto
    if tipo == "trimestral" and trimestre:
        ctx = construir_contexto_trimestral(kpis, año, trimestre)
        template_name = "informe_trimestral.md.j2"
    else:
        ctx = construir_contexto_anual(kpis, año)
        template_name = "informe_anual.md.j2"

    # Generar narrativa con Grok (o fallback por template)
    ctx["narrativa"] = generar_narrativa(ctx, tipo)

    # Renderizar template
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template(template_name)
    md_content = template.render(**ctx)

    # Guardar Markdown
    if salida_md is None:
        ts = f"Q{trimestre}" if trimestre else ""
        salida_md = REPORTS_DIR / f"{año}_{ts}_informe_{tipo}.md" if ts else REPORTS_DIR / f"{año}_informe_{tipo}.md"
    salida_md.parent.mkdir(parents=True, exist_ok=True)
    salida_md.write_text(md_content, encoding="utf-8")
    logger.info("Markdown guardado: %s", salida_md)

    # Convertir a PDF (Markdown → HTML → PDF)
    if salida_pdf is None:
        salida_pdf = salida_md.with_suffix(".pdf")

    try:
        import markdown
        from weasyprint import HTML

        # 1. Convertir Markdown a HTML
        html_body = markdown.markdown(
            md_content,
            extensions=["tables", "fenced_code"],
        )
        # 2. Envolver en HTML completo con estilos mínimos
        html_completo = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #333; }}
  h1 {{ color: #1B4332; border-bottom: 2px solid #1B4332; padding-bottom: 8px; }}
  h2 {{ color: #2D6A4F; margin-top: 30px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
  th {{ background: #1B4332; color: white; }}
  img {{ max-width: 100%; height: auto; }}
  .alert {{ padding: 12px; border-radius: 4px; margin: 10px 0; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
        # 3. Generar PDF
        HTML(string=html_completo).write_pdf(str(salida_pdf))
        logger.info("PDF guardado: %s", salida_pdf)
    except ImportError as e:
        logger.warning("Librería no instalada (%s). PDF no generado.", e)
    except Exception as e:
        logger.warning("Error al generar PDF: %s. Se requiere pandoc o weasyprint+markdown.", e)

    return salida_md


# ── CLI ────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Generar informes ganaderos automáticos")
    parser.add_argument("--tipo", choices=["anual", "trimestral"], default="anual")
    parser.add_argument("--año", type=int, required=True)
    parser.add_argument("--trimestre", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--salida-md", type=Path)
    parser.add_argument("--salida-pdf", type=Path)
    args = parser.parse_args()

    if args.tipo == "trimestral" and args.trimestre is None:
        parser.error("--trimestre es obligatorio para informes trimestrales")

    generar_reporte(
        tipo=args.tipo,
        año=args.año,
        trimestre=args.trimestre,
        salida_md=args.salida_md,
        salida_pdf=args.salida_pdf,
    )


if __name__ == "__main__":
    main()
