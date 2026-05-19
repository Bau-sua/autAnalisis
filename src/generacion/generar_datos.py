"""Generador de datos sintéticos ganaderos para San Luis, Argentina.

Genera archivos CSV en data/raw/ con datos deliberadamente "sucios" que simulan
datos reales llegados del campo, incluyendo valores nulos, outliers, formatos
inconsistentes y errores comunes.

Uso:
    uv run python src/generacion/generar_datos.py
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

from schemas import (
    CATEGORIAS_BOVINAS,
    DEPARTAMENTOS_SAN_LUIS,
    PESO_VIVO_PROMEDIO_KG,
    PRECIO_RELATIVO_BASE,
    PRODUCTOS_EXPORTACION,
    PREFIJOS_ESTABLECIMIENTO,
    RENDIMIENTO_FAENA,
    SUFIJOS_ESTABLECIMIENTO,
    GeneracionConfig,
    TipoEstablecimiento,
    ZonaDepartamento,
)

# ── Configuración ──────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s"
)
logger = logging.getLogger(__name__)

CONFIG = GeneracionConfig()
RNG = np.random.default_rng(CONFIG.random_seed)
FAKE = Faker("es_AR")
Faker.seed(CONFIG.random_seed)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

# ── Helpers ────────────────────────────────────────────────────────────────


def _semanar(series: pd.Series, factor: float = 0.15) -> pd.Series:
    """Agrega ruido multiplicativo a una serie (distribución log-normal)."""
    return series * np.exp(RNG.normal(0, factor, len(series)))


def _generar_meses_entre(inicio: str, fin: str) -> pd.DatetimeIndex:
    """Genera el primer día de cada mes en un rango."""
    return pd.date_range(inicio, fin, freq="MS")


def _trimestre(mes: int) -> int:
    """Devuelve el trimestre (1-4) para un mes (1-12)."""
    return (mes - 1) // 3 + 1


def _ensuciar_fechas(series: pd.Series) -> pd.Series:
    """Convierte algunas fechas a formato DD/MM/YYYY inconsistente."""
    series_dt = pd.to_datetime(series, errors="coerce")
    mask = RNG.random(len(series_dt)) < CONFIG.proporcion_formatos_inconsistentes
    mask = mask & series_dt.notna()
    dirty = series.astype(object)
    if mask.any():
        dirty_dates = series_dt[mask].dt.strftime("%d/%m/%Y")
        dirty[mask] = dirty_dates
    return dirty


def _ensuciar_nulos(df: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    """Introduce valores nulos en columnas seleccionadas."""
    for col in columnas:
        if col in df.columns:
            mask = RNG.random(len(df)) < CONFIG.proporcion_nulos
            df.loc[mask, col] = np.nan
    return df


def _ensuciar_outliers(
    df: pd.DataFrame, columna: str, factor: float = 5.0
) -> pd.DataFrame:
    """Multiplica algunos valores por un factor para crear outliers."""
    if columna not in df.columns:
        return df
    mask = (RNG.random(len(df)) < CONFIG.proporcion_outliers) & df[columna].notna()
    df.loc[mask, columna] = df.loc[mask, columna] * factor
    return df


def _ensuciar_duplicados(df: pd.DataFrame) -> pd.DataFrame:
    """Duplica algunas filas aleatorias."""
    n_dupes = max(1, int(len(df) * CONFIG.proporcion_duplicados))
    indices = RNG.choice(len(df), size=n_dupes, replace=False)
    dupes = df.iloc[indices].copy()
    return pd.concat([df, dupes], ignore_index=True)


def _guardar_csv(df: pd.DataFrame, nombre: str) -> None:
    """Guarda un DataFrame como CSV en data/raw/."""
    path = RAW_DIR / nombre
    df.to_csv(path, index=False, encoding="utf-8-sig")
    logger.info("Guardado %s — %d filas, %d columnas", path, len(df), len(df.columns))


# ── Generación de dimensiones ──────────────────────────────────────────────


def generar_dim_departamentos() -> pd.DataFrame:
    """Genera catálogo de departamentos de San Luis (datos limpios de referencia)."""
    registros = [
        {
            "id_departamento": d.id,
            "nombre": d.nombre,
            "zona": d.zona.value,
            "superficie_km2": d.superficie_km2,
        }
        for d in DEPARTAMENTOS_SAN_LUIS
    ]
    return pd.DataFrame(registros)


def generar_dim_categorias() -> pd.DataFrame:
    """Genera catálogo de categorías bovinas (datos limpios de referencia)."""
    registros = [
        {
            "id_categoria": c.id,
            "nombre": c.nombre,
            "nombre_corto": c.nombre_corto,
            "grupo_etario": c.grupo_etario.value,
            "sexo": c.sexo.value,
        }
        for c in CATEGORIAS_BOVINAS
    ]
    return pd.DataFrame(registros)


def generar_dim_establecimientos() -> pd.DataFrame:
    """Genera lista de establecimientos ficticios con nombres rurales creíbles."""
    establecimientos = []
    id_est = 1

    pesos = np.array([d.peso_establecimientos for d in DEPARTAMENTOS_SAN_LUIS])
    pesos = pesos / pesos.sum()

    for _ in range(CONFIG.num_establecimientos):
        depto_idx = RNG.choice(len(DEPARTAMENTOS_SAN_LUIS), p=pesos)
        depto = DEPARTAMENTOS_SAN_LUIS[depto_idx]

        if depto.zona == ZonaDepartamento.NORTE:
            tipos = [TipoEstablecimiento.CRIA, TipoEstablecimiento.CICLO_COMPLETO]
            p_tipos = [0.7, 0.3]
            ha_min, ha_max = 2000, 15000
        elif depto.zona == ZonaDepartamento.SUR:
            tipos = [
                TipoEstablecimiento.CRIA,
                TipoEstablecimiento.CICLO_COMPLETO,
                TipoEstablecimiento.INVERNADA,
                TipoEstablecimiento.FEEDLOT,
            ]
            p_tipos = [0.35, 0.25, 0.20, 0.20]
            ha_min, ha_max = 1000, 25000
        else:
            tipos = [TipoEstablecimiento.CRIA, TipoEstablecimiento.TAMBO]
            p_tipos = [0.8, 0.2]
            ha_min, ha_max = 500, 8000

        tipo_idx = RNG.choice(len(tipos), p=p_tipos)
        tipo = tipos[tipo_idx]
        hectareas = round(RNG.uniform(ha_min, ha_max), 1)
        stock_aprox = round(hectareas * RNG.uniform(0.3, 0.9))

        prefijo = RNG.choice(PREFIJOS_ESTABLECIMIENTO)
        sufijo = RNG.choice(SUFIJOS_ESTABLECIMIENTO)
        nombre = f"{prefijo} {sufijo}"

        establecimientos.append(
            {
                "id_establecimiento": id_est,
                "nombre": nombre,
                "id_departamento": depto.id,
                "tipo": tipo.value,
                "hectareas": hectareas,
                "stock_aprox": stock_aprox,
            }
        )
        id_est += 1

    return pd.DataFrame(establecimientos)


def generar_dim_tiempo(inicio: str, fin: str) -> pd.DataFrame:
    """Genera dimensión temporal día a día."""
    fechas = pd.date_range(inicio, fin, freq="D")
    return pd.DataFrame(
        {
            "id_fecha": range(1, len(fechas) + 1),
            "fecha": fechas,
            "año": fechas.year,
            "trimestre": fechas.month.map(_trimestre),
            "mes": fechas.month,
            "nombre_mes": fechas.month_name(),
        }
    )


# ── Generación de tablas de hechos ─────────────────────────────────────────


def generar_fact_stock_bovino(
    dim_deptos: pd.DataFrame, dim_cat: pd.DataFrame
) -> pd.DataFrame:
    """Genera existencias bovinas anuales por departamento y categoría.

    Simula el ciclo 2020-2024 con sequía severa en 2022-2023.
    """
    registros = []
    años = range(2020, 2025)
    # Factor de sequía: 2022 y 2023 tuvieron sequía histórica en Argentina
    factor_sequia = {2020: 1.0, 2021: 1.0, 2022: 0.88, 2023: 0.82, 2024: 0.92}

    for año in años:
        for _, depto_row in dim_deptos.iterrows():
            d_idx = depto_row["id_departamento"] - 1
            d = DEPARTAMENTOS_SAN_LUIS[d_idx]
            stock_total = int(d.stock_aprox_2024 * factor_sequia[año])

            # Calcular proporciones de categorías y normalizarlas
            cats_props = []
            for _, cat_row in dim_cat.iterrows():
                cat_id2 = cat_row["id_categoria"]
                cat2 = CATEGORIAS_BOVINAS[cat_id2 - 1]
                if d.zona == ZonaDepartamento.NORTE:
                    prop = cat2.proporcion_tipica_cria
                elif d.zona == ZonaDepartamento.SUR:
                    prop = cat2.proporcion_tipica_ciclo_completo
                else:
                    prop = (cat2.proporcion_tipica_cria + cat2.proporcion_tipica_invernada) / 2
                cats_props.append((cat_id2, prop))

            suma_props = sum(p for _, p in cats_props)

            for cat_id, proporcion in cats_props:
                proporcion_norm = proporcion / suma_props if suma_props > 0 else 0
                cabezas_base = int(stock_total * proporcion_norm)
                # Ruido: ±10% del valor
                cabezas = max(0, int(RNG.normal(cabezas_base, cabezas_base * 0.10)))

                if cabezas > 0:
                    registros.append(
                        {
                            "fecha": f"{año}-12-31",
                            "año": año,
                            "id_departamento": depto_row["id_departamento"],
                            "id_categoria": cat_id,
                            "cabezas": cabezas,
                        }
                    )

    df = pd.DataFrame(registros)
    df = _ensuciar_nulos(df, ["cabezas"])
    df = _ensuciar_outliers(df, "cabezas", factor=3.0)
    return df


def generar_fact_faena(
    dim_cat: pd.DataFrame, inicio: str, fin: str
) -> pd.DataFrame:
    """Genera faena mensual provincial por categoría.

    Faena nacional ~1.2 M cabezas/mes. San Luis ~3% = ~36.000 cabezas/mes.
    Peso promedio carcasa nacional ~231 kg (2025).
    """
    registros = []
    meses = _generar_meses_entre(inicio, fin)

    # Faena total mensual San Luis (aprox 3% de la faena nacional)
    faena_base_mensual = 36000
    # Estacionalidad: más faena en otoño-invierno (abril-septiembre)
    estacionalidad = {1: 0.95, 2: 0.90, 3: 0.95, 4: 1.05, 5: 1.10, 6: 1.15,
                      7: 1.12, 8: 1.10, 9: 1.05, 10: 1.00, 11: 0.95, 12: 0.98}

    # Tendencia temporal: ligero crecimiento
    tendencia_base = np.linspace(0.92, 1.02, len(meses))

    for i, fecha in enumerate(meses):
        mes = fecha.month
        faena_total_mes = int(
            faena_base_mensual * estacionalidad[mes] * tendencia_base[i]
        )
        faena_total_mes = int(_semanar(pd.Series([faena_total_mes]), 0.08).iloc[0])

        # Distribuir entre categorías (novillos y vacas son mayoría en faena)
        pesos_faena = np.array([0.03, 0.03, 0.18, 0.17, 0.25, 0.28, 0.06])
        pesos_faena = pesos_faena / pesos_faena.sum()

        for _, cat_row in dim_cat.iterrows():
            cat_id = cat_row["id_categoria"]
            cabezas_cat = int(faena_total_mes * pesos_faena[cat_id - 1])
            peso_vivo = PESO_VIVO_PROMEDIO_KG[cat_id]
            rend = RENDIMIENTO_FAENA[cat_id]
            peso_prom = round(RNG.normal(peso_vivo * rend, peso_vivo * rend * 0.05), 1)
            prod_ton = round(cabezas_cat * peso_prom / 1000, 2)

            if cabezas_cat > 0:
                registros.append(
                    {
                        "fecha": fecha.strftime("%Y-%m-%d"),
                        "id_categoria": cat_id,
                        "cabezas": cabezas_cat,
                        "peso_promedio_kg": peso_prom,
                        "produccion_ton": prod_ton,
                    }
                )

    df = pd.DataFrame(registros)
    df = _ensuciar_fechas(df["fecha"]).to_frame().join(df.drop(columns=["fecha"]))
    df = _ensuciar_nulos(df, ["peso_promedio_kg", "produccion_ton"])
    df = _ensuciar_outliers(df, "cabezas", factor=4.0)
    return df


def generar_fact_precios(
    dim_cat: pd.DataFrame, inicio: str, fin: str
) -> pd.DataFrame:
    """Genera precios mensuales por kg vivo en pesos corrientes.

    Precio base enero 2020: ~$85/kg novillo (pesos argentinos).
    Con inflación 2020: ~36%, 2021: ~50%, 2022: ~95%, 2023: ~211%, 2024: ~118%.
    Los precios del ganado no necesariamente siguen la inflación general.
    """
    registros = []
    meses = _generar_meses_entre(inicio, fin)
    precio_base = 85.0  # $/kg vivo novillo en enero 2020

    # Tasas mensuales aproximadas de aumento de precio ganadero
    # (no son la inflación general, son específicas del sector)
    tasas_mensuales: dict[int, float] = {}
    for año, tasa_anual_ganadera in [
        (2020, 0.30),  # 2020: precios estables, luego recuperación
        (2021, 0.55),  # 2021: fuerte suba
        (2022, 0.70),  # 2022: sequía reduce oferta, suben precios
        (2023, 1.50),  # 2023: explosión inflacionaria
        (2024, 0.90),  # 2024: moderación parcial
    ]:
        tasa_mensual = (1 + tasa_anual_ganadera) ** (1 / 12) - 1
        for mes in range(1, 13):
            key = año * 100 + mes
            if key >= 202001:  # desde enero 2020
                tasas_mensuales[key] = tasa_mensual

    # 2025 Q1: tasa similar a fin 2024
    tasa_mensual_2025 = (1 + 0.60) ** (1 / 12) - 1
    for mes in range(1, 4):
        tasas_mensuales[2025 * 100 + mes] = tasa_mensual_2025

    # Calcular precios acumulando
    precio_novillo = precio_base
    estacionalidad_precio = {
        1: 0.98, 2: 0.96, 3: 0.99, 4: 1.02, 5: 1.04,
        6: 1.05, 7: 1.06, 8: 1.05, 9: 1.03, 10: 1.01,
        11: 1.00, 12: 0.99,
    }

    for fecha in meses:
        key = fecha.year * 100 + fecha.month
        if key in tasas_mensuales:
            precio_novillo *= 1 + tasas_mensuales[key]

        for _, cat_row in dim_cat.iterrows():
            cat_id = cat_row["id_categoria"]
            relativo = PRECIO_RELATIVO_BASE[cat_id]
            precio_cat = precio_novillo * relativo
            precio_cat *= estacionalidad_precio[fecha.month]
            precio_cat = _semanar(pd.Series([precio_cat]), 0.03).iloc[0]
            precio_cat = round(precio_cat, 2)

            registros.append(
                {
                    "fecha": fecha.strftime("%Y-%m-%d"),
                    "id_categoria": cat_id,
                    "precio_kg_vivo": precio_cat,
                }
            )

    df = pd.DataFrame(registros)
    df = _ensuciar_fechas(df["fecha"]).to_frame().join(df.drop(columns=["fecha"]))
    df = _ensuciar_nulos(df, ["precio_kg_vivo"])
    # Outliers: algunos precios absurdos
    df = _ensuciar_outliers(df, "precio_kg_vivo", factor=10.0)
    return df


def generar_fact_clima(
    dim_deptos: pd.DataFrame, inicio: str, fin: str
) -> pd.DataFrame:
    """Genera datos climáticos mensuales por departamento.

    San Luis tiene clima semiárido con precipitaciones concentradas en verano
    (octubre-marzo) y estación seca en invierno. La media anual varía de
    ~800 mm (este, Pedernera) a ~400 mm (oeste, zona de Cuyo).
    """
    registros = []
    meses = _generar_meses_entre(inicio, fin)

    for _, depto_row in dim_deptos.iterrows():
        depto_id = depto_row["id_departamento"]
        d = DEPARTAMENTOS_SAN_LUIS[depto_id - 1]

        if d.zona == ZonaDepartamento.NORTE:
            pp_anual_media = 500
            temp_anual_media = 18.0
        elif d.zona == ZonaDepartamento.SUR:
            pp_anual_media = 650
            temp_anual_media = 16.5
        else:  # Centro
            pp_anual_media = 550
            temp_anual_media = 17.5

        # Distribución mensual de precipitaciones (% del total anual)
        pp_mensual_pct = {
            1: 0.12, 2: 0.10, 3: 0.12, 4: 0.06, 5: 0.03, 6: 0.02,
            7: 0.02, 8: 0.03, 9: 0.05, 10: 0.10, 11: 0.15, 12: 0.20,
        }

        # Temperatura mensual: sinusoidal
        temp_mensual_offset = {m: 8 * np.sin((m - 1) * np.pi / 6 - np.pi / 2)
                               for m in range(1, 13)}

        # Factores de sequía anual
        factor_pp_anual = {2020: 0.85, 2021: 1.00, 2022: 0.45, 2023: 0.40, 2024: 0.95, 2025: 1.00}

        for fecha in meses:
            año = fecha.year
            mes = fecha.month
            pp = pp_anual_media * pp_mensual_pct[mes] * factor_pp_anual[año]
            pp = max(0, RNG.normal(pp, pp * 0.5))
            temp = temp_anual_media + temp_mensual_offset[mes]
            temp = RNG.normal(temp, 2.0)

            registros.append(
                {
                    "fecha": fecha.strftime("%Y-%m-%d"),
                    "id_departamento": depto_id,
                    "precipitacion_mm": round(pp, 1),
                    "temperatura_media_c": round(temp, 1),
                }
            )

    df = pd.DataFrame(registros)
    df = _ensuciar_fechas(pd.to_datetime(df["fecha"])).to_frame().join(
        df.drop(columns=["fecha"])
    )
    df = _ensuciar_nulos(df, ["precipitacion_mm", "temperatura_media_c"])
    # Outliers: lluvias extremas
    df = _ensuciar_outliers(df, "precipitacion_mm", factor=4.0)
    return df


def generar_fact_movimientos(
    dim_establecimientos: pd.DataFrame,
    dim_cat: pd.DataFrame,
    inicio: str,
    fin: str,
) -> pd.DataFrame:
    """Genera movimientos de hacienda (compras/ventas/faena) por establecimiento.

    ~5-15 movimientos por establecimiento por año.
    """
    registros = []
    meses = _generar_meses_entre(inicio, fin)

    for _, est_row in dim_establecimientos.iterrows():
        # Cuántos meses con movimientos (30-60% de los meses)
        n_meses_con_mov = int(len(meses) * RNG.uniform(0.10, 0.30))
        meses_activos = RNG.choice(meses, size=n_meses_con_mov, replace=False)

        for fecha_np in meses_activos:
            fecha = pd.Timestamp(fecha_np)
            n_movimientos = RNG.integers(1, 4)
            for _ in range(n_movimientos):
                cat_id = int(RNG.choice(dim_cat["id_categoria"].values))
                tipos = ["Compra", "Venta", "Traslado"]
                p_tipos = [0.30, 0.50, 0.20]
                tipo = str(RNG.choice(np.array(tipos, dtype=object), p=p_tipos))

                peso_prom = PESO_VIVO_PROMEDIO_KG.get(cat_id, 300)
                if tipo in ("Compra", "Venta"):
                    cabezas = RNG.integers(5, 200)
                else:
                    cabezas = RNG.integers(5, 80)

                registros.append(
                    {
                        "fecha": fecha.strftime("%Y-%m-%d"),
                        "id_establecimiento": est_row["id_establecimiento"],
                        "id_categoria": cat_id,
                        "tipo_movimiento": tipo,
                        "cabezas": cabezas,
                        "peso_promedio_kg": round(RNG.normal(peso_prom, peso_prom * 0.10), 1),
                    }
                )

    df = pd.DataFrame(registros)
    df = _ensuciar_fechas(pd.to_datetime(df["fecha"])).to_frame().join(
        df.drop(columns=["fecha"])
    )
    df = _ensuciar_nulos(df, ["peso_promedio_kg"])
    df = _ensuciar_outliers(df, "cabezas", factor=6.0)
    df = _ensuciar_duplicados(df)
    return df


def generar_fact_exportaciones(
    inicio: str, fin: str
) -> pd.DataFrame:
    """Genera exportaciones mensuales de carne bovina argentina.

    Argentina exporta ~700-900 mil toneladas anuales de carne bovina.
    Datos a nivel nacional, usables como contexto macro.
    """
    registros = []
    meses = _generar_meses_entre(inicio, fin)
    export_mensual_base = 70000  # ~70k ton/mes promedio

    for fecha in meses:
        for producto in PRODUCTOS_EXPORTACION:
            if producto == "Carne bovina enfriada":
                ton_base = export_mensual_base * 0.40
                precio_ton = 5500  # USD/ton aproximado
            elif producto == "Carne bovina congelada":
                ton_base = export_mensual_base * 0.30
                precio_ton = 4200
            elif producto == "Menudencias y vísceras":
                ton_base = export_mensual_base * 0.10
                precio_ton = 1800
            elif producto == "Carne procesada / termoprocesada":
                ton_base = export_mensual_base * 0.08
                precio_ton = 3500
            else:  # Cuero
                ton_base = export_mensual_base * 0.12
                precio_ton = 2500

            ton = max(0, RNG.normal(ton_base, ton_base * 0.25))
            valor = round(ton * precio_ton, 2)

            registros.append(
                {
                    "fecha": fecha.strftime("%Y-%m-%d"),
                    "producto": producto,
                    "toneladas": round(ton, 2),
                    "valor_miles_usd": round(valor / 1000, 2),
                }
            )

    df = pd.DataFrame(registros)
    df = _ensuciar_fechas(pd.to_datetime(df["fecha"])).to_frame().join(
        df.drop(columns=["fecha"])
    )
    df = _ensuciar_nulos(df, ["toneladas", "valor_miles_usd"])
    return df


# ── Orquestador ─────────────────────────────────────────────────────────────


def generar_todos() -> None:
    """Genera todos los archivos CSV y los guarda en data/raw/."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Iniciando generación de datos sintéticos...")
    logger.info("Config: seed=%d, establecimientos=%d, rango=%s → %s",
                CONFIG.random_seed, CONFIG.num_establecimientos,
                CONFIG.fecha_inicio, CONFIG.fecha_fin)

    # Dimensiones (limpias, son catálogos de referencia)
    dim_deptos = generar_dim_departamentos()
    _guardar_csv(dim_deptos, "dim_departamentos.csv")

    dim_cat = generar_dim_categorias()
    _guardar_csv(dim_cat, "dim_categorias.csv")

    dim_est = generar_dim_establecimientos()
    _guardar_csv(dim_est, "dim_establecimientos.csv")

    dim_tiempo = generar_dim_tiempo(CONFIG.fecha_inicio, CONFIG.fecha_fin)
    _guardar_csv(dim_tiempo, "dim_tiempo.csv")

    # Hechos (con "suciedad" deliberada)
    stock = generar_fact_stock_bovino(dim_deptos, dim_cat)
    _guardar_csv(stock, "fact_stock_bovino.csv")

    faena = generar_fact_faena(dim_cat, CONFIG.fecha_inicio, CONFIG.fecha_fin)
    _guardar_csv(faena, "fact_faena.csv")

    precios = generar_fact_precios(dim_cat, CONFIG.fecha_inicio, CONFIG.fecha_fin)
    _guardar_csv(precios, "fact_precios.csv")

    clima = generar_fact_clima(dim_deptos, CONFIG.fecha_inicio, CONFIG.fecha_fin)
    _guardar_csv(clima, "fact_clima.csv")

    mov = generar_fact_movimientos(dim_est, dim_cat, CONFIG.fecha_inicio, CONFIG.fecha_fin)
    _guardar_csv(mov, "fact_movimientos.csv")

    export = generar_fact_exportaciones(CONFIG.fecha_inicio, CONFIG.fecha_fin)
    _guardar_csv(export, "fact_exportaciones.csv")

    logger.info("✅ Generación completada. %d archivos en %s",
                len(list(RAW_DIR.glob("*.csv"))), RAW_DIR)


if __name__ == "__main__":
    generar_todos()
