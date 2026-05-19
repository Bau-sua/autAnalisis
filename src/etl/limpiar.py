"""Pipeline ETL de limpieza de datos ganaderos.

Transforma los CSVs crudos (con suciedad deliberada) en Parquet limpios y validados.

Flujo:
1. Carga de archivos raw
2. Validación de esquemas
3. Normalización de fechas (formatos mixtos → YYYY-MM-DD)
4. Corrección de tipos de datos
5. Imputación de valores nulos
6. Detección y tratamiento de outliers
7. Eliminación de duplicados
8. Validación post-limpieza
9. Guardado en data/clean/

Uso:
    uv run python src/etl/limpiar.py
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Asegurar que src/ esté en el path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

from src.etl.validar import validar_esquema, validar_rangos
from src.utils.config import (
    ARCHIVOS_RAW,
    CLEAN_DIR,
    OUTLIER_ZSCORE_UMBRAL,
    RAW_DIR,
    RANGOS_VALIDOS,
    TIPOS_ESTABLECIMIENTO_VALIDOS,
    TIPOS_MOVIMIENTO_VALIDOS,
    ZONAS_VALIDAS,
)
from src.utils.logging_config import setup_logging

logger = setup_logging(modulo="etl")

# ── Carga ──────────────────────────────────────────────────────────────────


def cargar_datasets() -> dict[str, pd.DataFrame]:
    """Carga todos los archivos CSV crudos en un diccionario.

    Returns:
        Dict con {nombre_archivo: DataFrame}.
    """
    datasets = {}
    for clave, nombre_archivo in ARCHIVOS_RAW.items():
        path = RAW_DIR / nombre_archivo
        if not path.exists():
            logger.warning("Archivo no encontrado: %s", path)
            continue
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        # Convertir 'nan' strings a NaN real
        df.replace({"nan": np.nan, "": np.nan, "NaN": np.nan, "N/A": np.nan}, inplace=True)
        datasets[nombre_archivo] = df
        logger.info("Cargado %s — %d filas", nombre_archivo, len(df))
    return datasets


# ── Normalización de fechas ────────────────────────────────────────────────


def normalizar_fechas(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza columnas de fecha con formatos mixtos.

    Soporta:
    - YYYY-MM-DD (formato estándar)
    - DD/MM/YYYY (formato argentino inconsistente)
    - Valores datetime ya parseables

    Args:
        df: DataFrame con columna 'fecha'.

    Returns:
        DataFrame con columna 'fecha' normalizada (YYYY-MM-DD string).
    """
    # Solo columnas exactamente llamadas 'fecha', no 'id_fecha', 'fecha_dt', etc.
    cols_fecha = [c for c in df.columns if c.lower() == "fecha"]
    if not cols_fecha:
        return df

    for col in cols_fecha:
        serie = df[col].copy()

        # Si ya es datetime, convertir a string y devolver
        if pd.api.types.is_datetime64_any_dtype(serie):
            df[col] = serie.dt.strftime("%Y-%m-%d")
            continue

        # Intentar parseo unificado con coerción
        parsed = pd.to_datetime(serie, dayfirst=False, errors="coerce")
        # Las que fallaron con dayfirst=False, probar con dayfirst=True (DD/MM/YYYY)
        mask_na = parsed.isna() & serie.notna()
        if mask_na.any():
            parsed_arg = pd.to_datetime(
                serie[mask_na], dayfirst=True, errors="coerce"
            )
            parsed.loc[mask_na] = parsed_arg

        n_ok = parsed.notna().sum()
        n_fail = serie.notna().sum() - n_ok
        logger.debug(
            "  %s: %d fechas parseadas, %d fallidas",
            col, n_ok, max(0, n_fail),
        )

        # Reemplazar columna original con string YYYY-MM-DD
        df[col] = parsed.dt.strftime("%Y-%m-%d").where(parsed.notna(), None)

        # Extraer año/mes si no existen y la columna es de hechos (no dim_tiempo)
        if "año" not in df.columns and parsed.notna().any():
            df["año"] = parsed.dt.year
        if "mes" not in df.columns and parsed.notna().any():
            df["mes"] = parsed.dt.month

    return df


# ── Corrección de tipos ────────────────────────────────────────────────────


def corregir_tipos(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte columnas numéricas que llegaron como string a su tipo correcto.

    Args:
        df: DataFrame con columnas posiblemente string.

    Returns:
        DataFrame con tipos corregidos.
    """
    for col in df.columns:
        if col.endswith("_dt") or col.endswith("_fecha"):
            continue
        try:
            converted = pd.to_numeric(df[col], errors="coerce")
            # Si más del 80% de no-nulos son numéricos, convertir
            if converted.notna().sum() > df[col].notna().sum() * 0.8:
                df[col] = converted
        except (ValueError, TypeError):
            pass

        # Limpieza de texto: strip + normalizar espacios
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip().replace({"nan": np.nan, "None": np.nan})

    return df


# ── Imputación de nulos ────────────────────────────────────────────────────


def imputar_nulos(df: pd.DataFrame) -> pd.DataFrame:
    """Imputa valores nulos usando estrategias por tipo de columna.

    - Numéricas: mediana del grupo (por departamento o categoría)
    - Categóricas: moda

    Args:
        df: DataFrame con nulos.

    Returns:
        DataFrame con nulos imputados.
    """
    nulos_antes = df.isnull().sum().sum()

    for col in df.columns:
        if col.endswith("_dt"):
            continue
        if df[col].isnull().sum() == 0:
            continue

        if pd.api.types.is_numeric_dtype(df[col]):
            # Imputar con mediana del grupo si existe columna de agrupación
            if "id_departamento" in df.columns:
                df[col] = df.groupby("id_departamento")[col].transform(
                    lambda x: x.fillna(x.median())
                )
            elif "id_categoria" in df.columns:
                df[col] = df.groupby("id_categoria")[col].transform(
                    lambda x: x.fillna(x.median())
                )
            else:
                df[col] = df[col].fillna(df[col].median())
        else:
            df[col] = df[col].fillna(df[col].mode().iloc[0] if not df[col].mode().empty else "DESCONOCIDO")

    nulos_despues = df.isnull().sum().sum()
    if nulos_antes > 0:
        logger.debug("  Nulos imputados: %d → %d", nulos_antes, nulos_despues)

    return df


# ── Detección y tratamiento de outliers ────────────────────────────────────


def tratar_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """Detecta outliers por z-score agrupado y los reemplaza por la mediana del grupo.

    Agrupa por id_departamento y/o id_categoria si están presentes para
    detectar outliers dentro de cada contexto (evita falsos positivos
    entre categorías o departamentos de distinto tamaño).

    Args:
        df: DataFrame.

    Returns:
        DataFrame con outliers tratados.
    """
    total_tratados = 0
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        serie = df[col]
        if serie.isnull().all() or serie.nunique() < 2:
            continue

        # Determinar columnas de agrupación
        grupos = []
        for gcol in ["id_departamento", "id_categoria"]:
            if gcol in df.columns:
                grupos.append(gcol)

        # Calcular z-score por grupo usando numpy para evitar dtype conflicts
        zscore = pd.Series(0.0, index=df.index)
        for grp_keys, grp_idx in df.groupby(grupos).groups.items() if grupos else [((), df.index)]:
            vals = serie.loc[grp_idx].values
            mediana = np.median(vals[~np.isnan(vals)])
            mad = np.median(np.abs(vals[~np.isnan(vals)] - mediana))
            if mad == 0 or np.isnan(mad):
                std = np.std(vals[~np.isnan(vals)])
                if std == 0 or np.isnan(std):
                    continue
                zs = np.where(~np.isnan(vals), (vals - mediana) / std, 0)
            else:
                zs = np.where(~np.isnan(vals), 0.6745 * (vals - mediana) / mad, 0)
            zscore.loc[grp_idx] = zs

        mask_outlier = (zscore.abs() > OUTLIER_ZSCORE_UMBRAL) & serie.notna()
        if mask_outlier.sum() == 0:
            continue

        # Reemplazar con mediana del grupo (forzar cast al dtype original)
        if grupos:
            mediana_grupo = df.groupby(grupos)[col].transform("median")
            df.loc[mask_outlier, col] = mediana_grupo.loc[mask_outlier].astype(serie.dtype)
        else:
            df.loc[mask_outlier, col] = serie.dtype.type(np.median(serie.dropna().values))

        total_tratados += mask_outlier.sum()
        logger.debug("  %s: %d outliers tratados", col, mask_outlier.sum())

    if total_tratados > 0:
        logger.info("  Total outliers tratados: %d", total_tratados)

    return df


# ── Limpieza de duplicados ─────────────────────────────────────────────────


def eliminar_duplicados(df: pd.DataFrame, nombre: str) -> pd.DataFrame:
    """Elimina filas duplicadas y reporta cuántas se eliminaron.

    Args:
        df: DataFrame.
        nombre: Nombre del archivo para el log.

    Returns:
        DataFrame sin duplicados.
    """
    antes = len(df)
    # Usar columnas que no sean datetime internas para detectar duplicados
    cols = [c for c in df.columns if not c.endswith("_dt")]
    df = df.drop_duplicates(subset=cols, keep="first")
    despues = len(df)
    if antes != despues:
        logger.info("  %s: %d duplicados eliminados", nombre, antes - despues)
    return df


# ── Estandarización de texto ───────────────────────────────────────────────


def estandarizar_texto(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza valores en columnas categóricas conocidas.

    Args:
        df: DataFrame.

    Returns:
        DataFrame con texto estandarizado.
    """
    mapeos = {
        "zona": {"norte": "Norte", "NORTE": "Norte", "sur": "Sur", "SUR": "Sur",
                  "centro": "Centro", "CENTRO": "Centro"},
        "tipo": {
            "cria": "Cría", "CRIA": "Cría", "CRÍA": "Cría",
            "invernada": "Invernada", "INVERNADA": "Invernada",
            "ciclo completo": "Ciclo completo", "CICLO COMPLETO": "Ciclo completo",
            "feedlot": "Feedlot", "FEEDLOT": "Feedlot",
            "tambo": "Tambo", "TAMBO": "Tambo",
        },
        "tipo_movimiento": {
            "compra": "Compra", "COMPRA": "Compra",
            "venta": "Venta", "VENTA": "Venta",
            "traslado": "Traslado", "TRASLADO": "Traslado",
        },
    }
    for col, mapa in mapeos.items():
        if col in df.columns:
            df[col] = df[col].replace(mapa)

    return df


# ── Pipeline principal ─────────────────────────────────────────────────────


def limpiar_dataset(
    df: pd.DataFrame, nombre: str
) -> pd.DataFrame:
    """Aplica el pipeline completo de limpieza a un DataFrame.

    Args:
        df: DataFrame crudo.
        nombre: Nombre del archivo para logging.

    Returns:
        DataFrame limpio.
    """
    logger.info("Limpiando %s (%d filas)...", nombre, len(df))

    df = normalizar_fechas(df)
    df = corregir_tipos(df)
    df = imputar_nulos(df)
    df = tratar_outliers(df)
    df = eliminar_duplicados(df, nombre)
    df = estandarizar_texto(df)

    # Columnas de enteros: convertir float limpios a int64 nativo
    for col in df.columns:
        if df[col].dtype == "float64" and col.startswith("id_"):
            if df[col].notna().all():
                try:
                    df[col] = df[col].astype("int64")
                except (ValueError, TypeError):
                    pass
        if col in ("cabezas", "año", "mes", "trimestre"):
            if df[col].dtype == "float64" and df[col].notna().all():
                try:
                    df[col] = df[col].astype("int64")
                except (ValueError, TypeError):
                    pass

    logger.info("  → %d filas limpias", len(df))
    return df


def limpiar_todos(datasets: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Ejecuta limpieza sobre todos los datasets cargados.

    Args:
        datasets: Diccionario {nombre_archivo: DataFrame crudo}.

    Returns:
        Diccionario {nombre_archivo: DataFrame limpio}.
    """
    limpios = {}
    for nombre, df in datasets.items():
        limpios[nombre] = limpiar_dataset(df, nombre)
    return limpios


def guardar_limpios(datasets: dict[str, pd.DataFrame]) -> None:
    """Guarda los DataFrames limpios como Parquet en data/clean/.

    Args:
        datasets: Diccionario {nombre_archivo: DataFrame limpio}.
    """
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    for nombre, df in datasets.items():
        path = CLEAN_DIR / nombre.replace(".csv", ".parquet")
        # Convertir columnas datetime a string para compatibilidad Parquet/Polars
        df_out = df.copy()
        for col in df_out.columns:
            if col.endswith("_dt") or pd.api.types.is_datetime64_any_dtype(df_out[col]):
                df_out[col] = df_out[col].astype(str)
        df_out.to_parquet(path, index=False)
        logger.info("Guardado %s — %d filas", path, len(df_out))


def generar_reporte_limpieza(
    datasets_raw: dict[str, pd.DataFrame],
    datasets_clean: dict[str, pd.DataFrame],
) -> str:
    """Genera un resumen de la limpieza realizada.

    Args:
        datasets_raw: Datasets antes de limpiar.
        datasets_clean: Datasets después de limpiar.

    Returns:
        Texto con el resumen.
    """
    lineas = ["=" * 60, "RESUMEN DE LIMPIEZA ETL", "=" * 60, ""]
    for nombre in datasets_raw:
        if nombre not in datasets_clean:
            continue
        raw = datasets_raw[nombre]
        clean = datasets_clean[nombre]
        nulos_antes = raw.isnull().sum().sum()
        nulos_despues = clean.isnull().sum().sum()
        dups = len(raw) - len(clean)
        lineas.append(f"{nombre}:")
        lineas.append(f"  Filas: {len(raw)} → {len(clean)} ({dups} dups eliminados)"
                      if dups > 0 else f"  Filas: {len(raw)} (sin cambios)")
        lineas.append(f"  Nulos: {nulos_antes} → {nulos_despues}")
        lineas.append("")
    return "\n".join(lineas)


# ── Entry point ────────────────────────────────────────────────────────────


def main() -> None:
    """Punto de entrada del pipeline ETL."""
    logger.info("=" * 50)
    logger.info("INICIO PIPELINE ETL")
    logger.info("=" * 50)

    # 1. Cargar
    datasets = cargar_datasets()
    if not datasets:
        logger.error("No se encontraron archivos raw. Ejecutá 'make generar' primero.")
        return

    # 2. Validar (pre-limpieza)
    logger.info("\n--- Validación pre-limpieza ---")
    for nombre, df in datasets.items():
        result = validar_esquema(df, nombre)
        logger.info(result.resumen())

    # 3. Limpiar
    logger.info("\n--- Limpieza ---")
    limpios = limpiar_todos(datasets)

    # 4. Validar (post-limpieza)
    logger.info("\n--- Validación post-limpieza ---")
    for nombre, df in limpios.items():
        result = validar_esquema(df, nombre)
        # Rangos post-limpieza
        result.valores_fuera_rango = validar_rangos(df)
        logger.info(result.resumen())

    # 5. Guardar
    logger.info("\n--- Guardado ---")
    guardar_limpios(limpios)

    # 6. Reporte
    reporte = generar_reporte_limpieza(datasets, limpios)
    logger.info("\n" + reporte)

    logger.info("✅ Pipeline ETL completado.")


if __name__ == "__main__":
    main()
