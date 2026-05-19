"""Cálculo de KPIs e indicadores compuestos ganaderos.

Lee datos limpios de data/clean/ y genera métricas para dashboard y reportes.

Indicadores calculados:
- Stock: total provincial, por departamento, por categoría, variación YoY
- Faena: mensual/anual, por categoría, peso promedio, producción
- Precios: evolución nominal, variación YoY, relación ternero/novillo
- Clima: precipitación anual, anomalía vs media histórica
- Compuestos: tasa de extracción, ternero/novillo, correlación stock-lluvia

Uso:
    uv run python src/analisis/kpis.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

from src.utils.config import CLEAN_DIR, PROCESSED_DIR
from src.utils.logging_config import setup_logging

logger = setup_logging(modulo="analisis")

# ── IDs de categorías (del esquema) ────────────────────────────────────────
ID_TERNERO = 1
ID_TERNERA = 2
ID_NOVILLITO = 3
ID_VAQUILLONA = 4
ID_NOVILLO = 5
ID_VACA = 6
ID_TORO = 7


# ── Carga ──────────────────────────────────────────────────────────────────


def cargar_limpios() -> dict[str, pd.DataFrame]:
    """Carga todos los Parquet de data/clean/ en un diccionario."""
    datasets = {}
    for path in CLEAN_DIR.glob("*.parquet"):
        nombre = path.name
        df = pd.read_parquet(path)
        # Convertir columnas de año/mes a int donde aplique
        for col in ["año", "mes", "trimestre"]:
            if col in df.columns and df[col].notna().any():
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        datasets[nombre] = df
        logger.info("Cargado %s — %d filas", nombre, len(df))
    return datasets


# ── KPI: Stock ─────────────────────────────────────────────────────────────


def calcular_kpi_stock(
    stock: pd.DataFrame,
    deptos: pd.DataFrame,
    categorias: pd.DataFrame,
) -> pd.DataFrame:
    """Calcula KPIs de stock bovino: total, por depto, por categoría, YoY.

    Args:
        stock: fact_stock_bovino.parquet.
        deptos: dim_departamentos.parquet.
        categorias: dim_categorias.parquet.

    Returns:
        DataFrame con columnas: año, id_departamento, id_categoria,
        cabezas, variacion_yoy_pct, participacion_cat_pct.
    """
    df = stock.merge(deptos[["id_departamento", "nombre"]], on="id_departamento").merge(
        categorias[["id_categoria", "nombre"]], on="id_categoria", suffixes=("_depto", "_cat")
    )
    df = df.rename(columns={"nombre_depto": "departamento", "nombre_cat": "categoria"})

    # Total provincial por año
    total_anual = df.groupby("año")["cabezas"].sum().reset_index()
    total_anual = total_anual.rename(columns={"cabezas": "total_provincial"})

    # Variación YoY
    total_anual["variacion_provincial_yoy_pct"] = total_anual["total_provincial"].pct_change() * 100

    # Calcular participación de cada categoría en el total
    total_cat_anual = df.groupby(["año", "id_categoria"])["cabezas"].sum().reset_index()
    total_cat_anual = total_cat_anual.merge(total_anual[["año", "total_provincial"]], on="año")
    total_cat_anual["participacion_cat_pct"] = (
        total_cat_anual["cabezas"] / total_cat_anual["total_provincial"] * 100
    )

    # Participación departamental
    total_depto_anual = df.groupby(["año", "id_departamento"])["cabezas"].sum().reset_index()
    total_depto_anual = total_depto_anual.merge(total_anual[["año", "total_provincial"]], on="año")
    total_depto_anual["participacion_depto_pct"] = (
        total_depto_anual["cabezas"] / total_depto_anual["total_provincial"] * 100
    )

    # Variación YoY por departamento
    total_depto_anual["variacion_depto_yoy_pct"] = total_depto_anual.groupby(
        "id_departamento"
    )["cabezas"].pct_change() * 100

    # Merge completo
    result = df.merge(
        total_anual[["año", "total_provincial", "variacion_provincial_yoy_pct"]], on="año"
    )
    result = result.merge(
        total_cat_anual[["año", "id_categoria", "participacion_cat_pct"]],
        on=["año", "id_categoria"],
    )
    result = result.merge(
        total_depto_anual[
            ["año", "id_departamento", "participacion_depto_pct", "variacion_depto_yoy_pct"]
        ],
        on=["año", "id_departamento"],
    )

    return result


# ── KPI: Faena ─────────────────────────────────────────────────────────────


def calcular_kpi_faena(
    faena: pd.DataFrame,
    categorias: pd.DataFrame,
) -> pd.DataFrame:
    """Calcula KPIs de faena: mensual, anual, por categoría, peso promedio.

    Returns:
        DataFrame con faena enriquecida.
    """
    df = faena.merge(
        categorias[["id_categoria", "nombre"]], on="id_categoria"
    ).rename(columns={"nombre": "categoria"})

    # Totales anuales
    anual = df.groupby("año").agg(
        faena_total_cab=("cabezas", "sum"),
        produccion_total_ton=("produccion_ton", "sum"),
        peso_promedio_kg=("peso_promedio_kg", "mean"),
    ).reset_index()

    anual["variacion_faena_yoy_pct"] = anual["faena_total_cab"].pct_change() * 100
    anual["variacion_produccion_yoy_pct"] = anual["produccion_total_ton"].pct_change() * 100

    # Participación de hembras en faena (indicador clave de ciclo)
    # IDs hembras: 2 (ternera), 4 (vaquillona), 6 (vaca)
    hembras_anual = (
        df[df["id_categoria"].isin([ID_TERNERA, ID_VAQUILLONA, ID_VACA])]
        .groupby("año")["cabezas"]
        .sum()
        .reset_index()
        .rename(columns={"cabezas": "faena_hembras"})
    )
    anual = anual.merge(hembras_anual, on="año", how="left")
    anual["participacion_hembras_pct"] = (
        anual["faena_hembras"] / anual["faena_total_cab"] * 100
    )

    # Totales mensuales con media móvil 3 meses
    mensual = df.groupby(["año", "mes"]).agg(
        faena_mensual_cab=("cabezas", "sum"),
        produccion_mensual_ton=("produccion_ton", "sum"),
        peso_promedio_kg=("peso_promedio_kg", "mean"),
    ).reset_index()

    mensual["faena_mm3"] = mensual["faena_mensual_cab"].rolling(window=3, min_periods=1).mean()

    result = {
        "detalle": df,
        "anual": anual,
        "mensual": mensual,
    }
    return result


# ── KPI: Precios ───────────────────────────────────────────────────────────


def calcular_kpi_precios(
    precios: pd.DataFrame,
    categorias: pd.DataFrame,
) -> pd.DataFrame:
    """Calcula KPIs de precios e indicadores compuestos.

    Returns:
        DataFrame con precios mensuales, ratios, variaciones.
    """
    df = precios.merge(
        categorias[["id_categoria", "nombre"]], on="id_categoria"
    ).rename(columns={"nombre": "categoria"})

    # Precio promedio ponderado por año (usando novillo como referencia)
    novillo = df[df["id_categoria"] == ID_NOVILLO].copy()
    novillo_anual = novillo.groupby("año").agg(
        precio_novillo_promedio=("precio_kg_vivo", "mean"),
        precio_novillo_dic=("precio_kg_vivo", "last"),
    ).reset_index()
    novillo_anual["variacion_novillo_yoy_pct"] = (
        novillo_anual["precio_novillo_promedio"].pct_change() * 100
    )

    # Relación ternero/novillo (indicador de ciclo ganadero)
    ternero = df[df["id_categoria"] == ID_TERNERO][["año", "mes", "precio_kg_vivo"]].rename(
        columns={"precio_kg_vivo": "precio_ternero"}
    )
    novillo_mensual = novillo[["año", "mes", "precio_kg_vivo"]].rename(
        columns={"precio_kg_vivo": "precio_novillo"}
    )
    ratio = ternero.merge(novillo_mensual, on=["año", "mes"])
    ratio["relacion_ternero_novillo"] = ratio["precio_ternero"] / ratio["precio_novillo"]

    # Relación vaca/novillo
    vaca = df[df["id_categoria"] == ID_VACA][["año", "mes", "precio_kg_vivo"]].rename(
        columns={"precio_kg_vivo": "precio_vaca"}
    )
    ratio = ratio.merge(vaca, on=["año", "mes"])
    ratio["relacion_vaca_novillo"] = ratio["precio_vaca"] / ratio["precio_novillo"]

    # Promedio anual de ratios
    ratio_anual = ratio.groupby("año").agg(
        relacion_ternero_novillo=("relacion_ternero_novillo", "mean"),
        relacion_vaca_novillo=("relacion_vaca_novillo", "mean"),
        precio_ternero_promedio=("precio_ternero", "mean"),
        precio_novillo_promedio=("precio_novillo", "mean"),
        precio_vaca_promedio=("precio_vaca", "mean"),
    ).reset_index()

    return {
        "novillo_anual": novillo_anual,
        "ratio_mensual": ratio,
        "ratio_anual": ratio_anual,
        "detalle": df,
    }


# ── KPI: Clima ─────────────────────────────────────────────────────────────


def calcular_kpi_clima(
    clima: pd.DataFrame,
    deptos: pd.DataFrame,
) -> pd.DataFrame:
    """Calcula KPIs climáticos: precipitación anual, anomalía vs media.

    Returns:
        DataFrame con precipitación anual y anomalías.
    """
    df = clima.merge(
        deptos[["id_departamento", "nombre", "zona"]], on="id_departamento"
    ).rename(columns={"nombre": "departamento"})

    # Precipitación anual por departamento
    pp_anual = df.groupby(["año", "id_departamento"]).agg(
        precipitacion_anual_mm=("precipitacion_mm", "sum"),
        temperatura_media_c=("temperatura_media_c", "mean"),
    ).reset_index()

    # Media histórica (2020-2024) por departamento
    pp_historica = pp_anual.groupby("id_departamento")["precipitacion_anual_mm"].mean().reset_index()
    pp_historica = pp_historica.rename(columns={"precipitacion_anual_mm": "pp_media_historica"})

    pp_anual = pp_anual.merge(pp_historica, on="id_departamento")
    pp_anual["anomalia_pp_mm"] = pp_anual["precipitacion_anual_mm"] - pp_anual["pp_media_historica"]
    pp_anual["anomalia_pp_pct"] = (
        pp_anual["anomalia_pp_mm"] / pp_anual["pp_media_historica"] * 100
    )

    # Clasificar año según anomalía
    condiciones = [
        pp_anual["anomalia_pp_pct"] < -30,
        (pp_anual["anomalia_pp_pct"] >= -30) & (pp_anual["anomalia_pp_pct"] <= 30),
        pp_anual["anomalia_pp_pct"] > 30,
    ]
    valores = ["Seco", "Normal", "Húmedo"]
    pp_anual["condicion"] = np.select(condiciones, valores, default="Normal")

    # Promedio provincial anual
    pp_provincial = pp_anual.groupby("año").agg(
        pp_provincial_mm=("precipitacion_anual_mm", "mean"),
        anomalia_provincial_pct=("anomalia_pp_pct", "mean"),
        temp_media_provincial=("temperatura_media_c", "mean"),
    ).reset_index()

    return {
        "detalle": pp_anual,
        "provincial": pp_provincial,
    }


# ── KPI: Indicadores compuestos ────────────────────────────────────────────


def calcular_kpi_compuestos(
    kpi_stock: pd.DataFrame,
    kpi_faena: dict,
    kpi_clima: dict,
) -> pd.DataFrame:
    """Calcula indicadores compuestos que integran múltiples fuentes.

    Returns:
        DataFrame anual con indicadores compuestos.
    """
    # Stock total provincial
    stock_prov = (
        kpi_stock.groupby("año")
        .agg(stock_total_cab=("cabezas", "sum"))
        .reset_index()
    )

    # Faena total anual
    faena_anual = kpi_faena["anual"]

    # Clima provincial
    clima_prov = kpi_clima["provincial"]

    # Merge
    compuesto = stock_prov.merge(faena_anual, on="año", how="outer").merge(
        clima_prov, on="año", how="outer"
    )

    # Tasa de extracción (faena / stock)
    compuesto["tasa_extraccion_pct"] = (
        compuesto["faena_total_cab"] / compuesto["stock_total_cab"] * 100
    )

    # Producción de carne por cabeza de stock (kg/cab)
    compuesto["produccion_kg_por_cab_stock"] = (
        compuesto["produccion_total_ton"] * 1000 / compuesto["stock_total_cab"]
    )

    # Correlación rodante stock vs precipitación (no calculable con estos datos,
    # la agregamos como placeholder para la fórmula)
    compuesto["stock_vs_pp_corr"] = np.nan

    return compuesto


# ── Orquestador ─────────────────────────────────────────────────────────────


def main() -> None:
    """Calcula todos los KPIs y los guarda en data/processed/."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("=" * 50)
    logger.info("CÁLCULO DE KPIs")
    logger.info("=" * 50)

    # Cargar datos limpios
    datasets = cargar_limpios()

    stock = datasets["fact_stock_bovino.parquet"]
    faena = datasets["fact_faena.parquet"]
    precios = datasets["fact_precios.parquet"]
    clima = datasets["fact_clima.parquet"]
    deptos = datasets["dim_departamentos.parquet"]
    categorias = datasets["dim_categorias.parquet"]

    # Calcular KPIs
    logger.info("\n--- KPI Stock ---")
    kpi_stock = calcular_kpi_stock(stock, deptos, categorias)
    logger.info("Stock: %d filas", len(kpi_stock))

    logger.info("\n--- KPI Faena ---")
    kpi_faena = calcular_kpi_faena(faena, categorias)
    logger.info(
        "Faena: detalle=%d, anual=%d, mensual=%d",
        len(kpi_faena["detalle"]),
        len(kpi_faena["anual"]),
        len(kpi_faena["mensual"]),
    )

    logger.info("\n--- KPI Precios ---")
    kpi_precios = calcular_kpi_precios(precios, categorias)
    logger.info("Precios: ratio mensual=%d, ratio anual=%d",
                len(kpi_precios["ratio_mensual"]), len(kpi_precios["ratio_anual"]))

    logger.info("\n--- KPI Clima ---")
    kpi_clima = calcular_kpi_clima(clima, deptos)
    logger.info("Clima: detalle=%d, provincial=%d",
                len(kpi_clima["detalle"]), len(kpi_clima["provincial"]))

    logger.info("\n--- Indicadores Compuestos ---")
    kpi_compuestos = calcular_kpi_compuestos(kpi_stock, kpi_faena, kpi_clima)
    logger.info("Compuestos: %d filas", len(kpi_compuestos))

    # Guardar
    logger.info("\n--- Guardado ---")

    kpi_stock.to_parquet(PROCESSED_DIR / "kpi_stock.parquet", index=False)
    logger.info("  kpi_stock.parquet")

    kpi_faena["anual"].to_parquet(PROCESSED_DIR / "kpi_faena_anual.parquet", index=False)
    logger.info("  kpi_faena_anual.parquet")

    kpi_faena["mensual"].to_parquet(PROCESSED_DIR / "kpi_faena_mensual.parquet", index=False)
    logger.info("  kpi_faena_mensual.parquet")

    kpi_precios["ratio_mensual"].to_parquet(PROCESSED_DIR / "kpi_precios_ratio.parquet", index=False)
    logger.info("  kpi_precios_ratio.parquet")

    kpi_precios["novillo_anual"].to_parquet(PROCESSED_DIR / "kpi_precios_novillo.parquet", index=False)
    logger.info("  kpi_precios_novillo.parquet")

    kpi_clima["provincial"].to_parquet(PROCESSED_DIR / "kpi_clima_provincial.parquet", index=False)
    logger.info("  kpi_clima_provincial.parquet")

    kpi_clima["detalle"].to_parquet(PROCESSED_DIR / "kpi_clima_detalle.parquet", index=False)
    logger.info("  kpi_clima_detalle.parquet")

    kpi_compuestos.to_parquet(PROCESSED_DIR / "kpi_compuestos.parquet", index=False)
    logger.info("  kpi_compuestos.parquet")

    # Mostrar resumen en pantalla (último año completo con stock)
    completo = kpi_compuestos.dropna(subset=["stock_total_cab"])
    if len(completo) == 0:
        logger.warning("No hay años completos con datos de stock.")
        return

    ultimo = completo.iloc[-1]
    año = int(ultimo["año"])
    logger.info("\n" + "=" * 60)
    logger.info(f"RESUMEN DE INDICADORES — {año}")
    logger.info("=" * 60)
    logger.info(f"  Stock total:          {ultimo['stock_total_cab']:>12,.0f} cabezas")
    logger.info(f"  Faena total:          {ultimo['faena_total_cab']:>12,.0f} cabezas")
    logger.info(f"  Tasa de extracción:   {ultimo['tasa_extraccion_pct']:>12.1f}%")
    logger.info(f"  Peso promedio:        {ultimo['peso_promedio_kg']:>12.1f} kg")
    logger.info(f"  % Hembras en faena:   {ultimo['participacion_hembras_pct']:>12.1f}%")
    logger.info(f"  Precipitación prov.:  {ultimo['pp_provincial_mm']:>12.1f} mm")
    logger.info(f"  Anomalía PP:          {ultimo['anomalia_provincial_pct']:>12.1f}%")

    # Relación ternero/novillo
    ratio = kpi_precios["ratio_anual"]
    ultimo_ratio = ratio[ratio["año"] == ultimo["año"]]
    if len(ultimo_ratio):
        logger.info(f"  Rel. ternero/novillo: {ultimo_ratio['relacion_ternero_novillo'].values[0]:>12.2f}")

    logger.info("\n✅ KPIs calculados y guardados en data/processed/")


if __name__ == "__main__":
    main()
