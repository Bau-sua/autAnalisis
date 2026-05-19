"""Configuración centralizada del proyecto autAnalisis.

Define rutas, constantes y parámetros usados por todos los módulos.
"""

from pathlib import Path

# ── Rutas del proyecto ─────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
TESTS_DIR = PROJECT_ROOT / "tests"

# ── Archivos de entrada (raw) ──────────────────────────────────────────────

ARCHIVOS_RAW: dict[str, str] = {
    "departamentos": "dim_departamentos.csv",
    "categorias": "dim_categorias.csv",
    "establecimientos": "dim_establecimientos.csv",
    "tiempo": "dim_tiempo.csv",
    "stock": "fact_stock_bovino.csv",
    "faena": "fact_faena.csv",
    "precios": "fact_precios.csv",
    "clima": "fact_clima.csv",
    "movimientos": "fact_movimientos.csv",
    "exportaciones": "fact_exportaciones.csv",
}

# ── Esquemas esperados (columnas y tipos) ──────────────────────────────────

ESQUEMAS_ESPERADOS: dict[str, dict[str, str]] = {
    "dim_departamentos.csv": {
        "id_departamento": "int64",
        "nombre": "object",
        "zona": "object",
        "superficie_km2": "float64",
    },
    "dim_categorias.csv": {
        "id_categoria": "int64",
        "nombre": "object",
        "nombre_corto": "object",
        "grupo_etario": "object",
        "sexo": "object",
    },
    "dim_establecimientos.csv": {
        "id_establecimiento": "int64",
        "nombre": "object",
        "id_departamento": "int64",
        "tipo": "object",
        "hectareas": "float64",
        "stock_aprox": "int64",
    },
    "fact_stock_bovino.csv": {
        "fecha": "object",
        "año": "float64",
        "id_departamento": "float64",
        "id_categoria": "float64",
        "cabezas": "float64",
    },
    "fact_faena.csv": {
        "fecha": "object",
        "id_categoria": "float64",
        "cabezas": "float64",
        "peso_promedio_kg": "float64",
        "produccion_ton": "float64",
    },
    "fact_precios.csv": {
        "fecha": "object",
        "id_categoria": "float64",
        "precio_kg_vivo": "float64",
    },
    "fact_clima.csv": {
        "fecha": "object",
        "id_departamento": "float64",
        "precipitacion_mm": "float64",
        "temperatura_media_c": "float64",
    },
    "fact_movimientos.csv": {
        "fecha": "object",
        "id_establecimiento": "float64",
        "id_categoria": "float64",
        "tipo_movimiento": "object",
        "cabezas": "float64",
        "peso_promedio_kg": "float64",
    },
    "fact_exportaciones.csv": {
        "fecha": "object",
        "producto": "object",
        "toneladas": "float64",
        "valor_miles_usd": "float64",
    },
}

# ── Parámetros de limpieza ─────────────────────────────────────────────────

# Outliers: z-score > umbral se reemplaza por mediana del grupo
OUTLIER_ZSCORE_UMBRAL: float = 2.5

# Imputación de nulos
ESTRATEGIA_IMPUTACION_NUMERICA: str = "mediana_por_grupo"
ESTRATEGIA_IMPUTACION_CATEGORICA: str = "moda"

# Dominios válidos para validación
ZONAS_VALIDAS: set[str] = {"Norte", "Centro", "Sur"}
TIPOS_ESTABLECIMIENTO_VALIDOS: set[str] = {
    "Cría",
    "Invernada",
    "Ciclo completo",
    "Feedlot",
    "Tambo",
}
TIPOS_MOVIMIENTO_VALIDOS: set[str] = {"Compra", "Venta", "Traslado"}
PRODUCTOS_EXPORTACION_VALIDOS: set[str] = {
    "Carne bovina enfriada",
    "Carne bovina congelada",
    "Menudencias y vísceras",
    "Carne procesada / termoprocesada",
    "Cuero fresco",
}

# Rangos razonables para valores numéricos
RANGOS_VALIDOS: dict[str, tuple[float, float]] = {
    "cabezas": (0, 1_000_000),
    "peso_promedio_kg": (50, 1_200),
    "precio_kg_vivo": (0.01, 1_000_000),
    "precipitacion_mm": (0, 1_000),
    "temperatura_media_c": (-5, 45),
    "hectareas": (1, 100_000),
    "produccion_ton": (0, 100_000),
    "toneladas": (0, 1_000_000),
    "valor_miles_usd": (0, 10_000_000),
}
