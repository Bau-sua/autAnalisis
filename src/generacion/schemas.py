"""Esquemas de datos para el módulo de generación de datos sintéticos ganaderos.

Define las estructuras de tablas dimensionales y de hechos basadas en datos
reales de SENASA, IPCVA y MAGyP para la provincia de San Luis, Argentina.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

# ── Enums ──────────────────────────────────────────────────────────────────


class ZonaDepartamento(StrEnum):
    NORTE = "Norte"
    CENTRO = "Centro"
    SUR = "Sur"


class TipoEstablecimiento(StrEnum):
    CRIA = "Cría"
    INVERNADA = "Invernada"
    CICLO_COMPLETO = "Ciclo completo"
    FEEDLOT = "Feedlot"
    TAMBO = "Tambo"


class GrupoEtario(StrEnum):
    CRIA = "Cría"
    RECRIA = "Recría"
    ADULTO = "Adulto"


class SexoBovino(StrEnum):
    MACHO = "Macho"
    HEMBRA = "Hembra"
    AMBOS = "Ambos"


class TipoMovimientoHacienda(StrEnum):
    COMPRA = "Compra"
    VENTA = "Venta"
    FAENA_PROPIA = "Faena propia"
    TRASLADO = "Traslado"


# ── Dataclasses dimensionales ──────────────────────────────────────────────


@dataclass
class Departamento:
    id: int
    nombre: str
    zona: ZonaDepartamento
    superficie_km2: float
    # Calibración: stock bovino aproximado 2024 según fuentes públicas
    stock_aprox_2024: int
    # Peso para distribuir establecimientos (mayor stock = más establecimientos)
    peso_establecimientos: float = 1.0


@dataclass
class Establecimiento:
    id: int
    nombre_ficticio: str
    id_departamento: int
    tipo: TipoEstablecimiento
    hectareas: float
    stock_aprox: int  # cabezas aproximadas


@dataclass
class CategoriaBovina:
    id: int
    nombre: str
    nombre_corto: str  # para archivos crudos mal formateados
    grupo_etario: GrupoEtario
    sexo: SexoBovino
    # Proporción típica en rodeo de cría (se usa como prior de generación)
    proporcion_tipica_cria: float
    proporcion_tipica_invernada: float
    proporcion_tipica_ciclo_completo: float


# ── Dataclasses de hechos ──────────────────────────────────────────────────


@dataclass
class StockBovino:
    """Registro de existencias bovinas por departamento y categoría."""
    fecha: str  # YYYY-MM-DD
    id_departamento: int
    id_categoria: int
    cabezas: int


@dataclass
class Faena:
    """Registro mensual de faena bovina provincial."""
    fecha: str
    id_categoria: int
    cabezas: int
    peso_promedio_kg: float
    produccion_ton: float  # toneladas res con hueso


@dataclass
class PrecioGanado:
    """Precio por kg vivo por categoría (frecuencia mensual)."""
    fecha: str
    id_categoria: int
    precio_kg_vivo: float  # pesos argentinos corrientes


@dataclass
class Clima:
    """Datos climáticos mensuales por departamento."""
    fecha: str
    id_departamento: int
    precipitacion_mm: float
    temperatura_media_c: float


@dataclass
class MovimientoHacienda:
    """Movimientos de hacienda (compras/ventas/faena) a nivel establecimiento."""
    fecha: str
    id_establecimiento: int
    id_categoria: int
    tipo: TipoMovimientoHacienda
    cabezas: int
    peso_promedio_kg: Optional[float] = None


@dataclass
class ExportacionCarne:
    """Exportaciones mensuales de carne bovina desde San Luis / Argentina."""
    fecha: str
    producto: str  # "Carne enfriada", "Carne congelada", "Menudencias", etc.
    toneladas: float
    valor_miles_usd: float


# ── Configuración de generación ────────────────────────────────────────────


@dataclass
class GeneracionConfig:
    """Parámetros globales para la generación de datos sintéticos."""
    random_seed: int = 42
    fecha_inicio: str = "2020-01-01"
    fecha_fin: str = "2025-03-31"
    num_establecimientos: int = 60
    # Parámetros de "suciedad" en los datos crudos
    proporcion_nulos: float = 0.03  # 3% de celdas con valores nulos
    proporcion_outliers: float = 0.02  # 2% de registros con outliers
    proporcion_duplicados: float = 0.01  # 1% de filas duplicadas
    proporcion_formatos_inconsistentes: float = 0.05  # 5% con fechas/texto mal


# ── Catálogos estáticos (fuente de verdad para la generación) ──────────────


DEPARTAMENTOS_SAN_LUIS: list[Departamento] = [
    Departamento(1, "Ayacucho", ZonaDepartamento.NORTE, 9681, 95000, 0.08),
    Departamento(2, "Belgrano", ZonaDepartamento.NORTE, 6626, 120000, 0.10),
    Departamento(3, "Chacabuco", ZonaDepartamento.CENTRO, 2651, 65000, 0.05),
    Departamento(4, "Coronel Pringles", ZonaDepartamento.SUR, 4484, 100000, 0.09),
    Departamento(5, "General Pedernera", ZonaDepartamento.SUR, 15345, 352000, 0.25),
    Departamento(6, "Gobernador Dupuy", ZonaDepartamento.SUR, 19632, 500000, 0.30),
    Departamento(7, "Junín", ZonaDepartamento.NORTE, 2474, 55000, 0.04),
    Departamento(8, "Libertador Gral. San Martín", ZonaDepartamento.NORTE, 3021, 80000, 0.06),
    Departamento(9, "Juan Martín de Pueyrredón", ZonaDepartamento.CENTRO, 13120, 33000, 0.03),
]

CATEGORIAS_BOVINAS: list[CategoriaBovina] = [
    CategoriaBovina(1, "Ternero", "ternero", GrupoEtario.CRIA, SexoBovino.MACHO,
                     proporcion_tipica_cria=0.10, proporcion_tipica_invernada=0.02,
                     proporcion_tipica_ciclo_completo=0.06),
    CategoriaBovina(2, "Ternera", "ternera", GrupoEtario.CRIA, SexoBovino.HEMBRA,
                     proporcion_tipica_cria=0.10, proporcion_tipica_invernada=0.01,
                     proporcion_tipica_ciclo_completo=0.06),
    CategoriaBovina(3, "Novillito", "novillito", GrupoEtario.RECRIA, SexoBovino.MACHO,
                     proporcion_tipica_cria=0.05, proporcion_tipica_invernada=0.30,
                     proporcion_tipica_ciclo_completo=0.15),
    CategoriaBovina(4, "Vaquillona", "vaquillona", GrupoEtario.RECRIA, SexoBovino.HEMBRA,
                     proporcion_tipica_cria=0.15, proporcion_tipica_invernada=0.05,
                     proporcion_tipica_ciclo_completo=0.12),
    CategoriaBovina(5, "Novillo", "novillo", GrupoEtario.ADULTO, SexoBovino.MACHO,
                     proporcion_tipica_cria=0.02, proporcion_tipica_invernada=0.40,
                     proporcion_tipica_ciclo_completo=0.18),
    CategoriaBovina(6, "Vaca", "vaca", GrupoEtario.ADULTO, SexoBovino.HEMBRA,
                     proporcion_tipica_cria=0.35, proporcion_tipica_invernada=0.05,
                     proporcion_tipica_ciclo_completo=0.20),
    CategoriaBovina(7, "Toro", "toro", GrupoEtario.ADULTO, SexoBovino.MACHO,
                     proporcion_tipica_cria=0.03, proporcion_tipica_invernada=0.01,
                     proporcion_tipica_ciclo_completo=0.03),
]

# Relación típica de precios entre categorías (base = novillo = 1.0)
PRECIO_RELATIVO_BASE: dict[int, float] = {
    1: 1.30,  # Ternero: más caro por kg (lo paga el invernador)
    2: 1.15,  # Ternera
    3: 0.95,  # Novillito
    4: 0.90,  # Vaquillona
    5: 1.00,  # Novillo (base)
    6: 0.70,  # Vaca (menor valor, conserva/faena)
    7: 0.65,  # Toro
}

# Peso vivo promedio por categoría (kg) — guía para generar pesos en faena
PESO_VIVO_PROMEDIO_KG: dict[int, float] = {
    1: 180.0,   # Ternero ~180 kg
    2: 160.0,   # Ternera ~160 kg
    3: 320.0,   # Novillito ~320 kg
    4: 280.0,   # Vaquillona ~280 kg
    5: 450.0,   # Novillo ~450 kg
    6: 420.0,   # Vaca ~420 kg
    7: 700.0,   # Toro ~700 kg
}

# Rendimiento de faena (% del peso vivo que es res)
RENDIMIENTO_FAENA: dict[int, float] = {
    1: 0.52,
    2: 0.52,
    3: 0.55,
    4: 0.54,
    5: 0.56,
    6: 0.50,
    7: 0.52,
}

# Productos de exportación de carne
PRODUCTOS_EXPORTACION = [
    "Carne bovina enfriada",
    "Carne bovina congelada",
    "Menudencias y vísceras",
    "Carne procesada / termoprocesada",
    "Cuero fresco",
]

# Nombres ficticios de establecimientos — tipología rural argentina
PREFIJOS_ESTABLECIMIENTO = [
    "El", "La", "Los", "Las", "San", "Santa", "Don",
]
SUFIJOS_ESTABLECIMIENTO = [
    "Escondido", "Aguada", "Tala", "Chañar", "Caldenes",
    "Algarrobo", "Bajo", "Pampa", "Alto", "Cortadera",
    "Totoral", "Médano", "Quebracho", "Socorro", "Palmar",
    "Rincón", "Cerrillo", "Laguna", "Totoras", "Tunas",
    "Molle", "Chimango", "Zampal", "Jarilla", "Retamo",
    "Guadal", "Morro", "Trapal", "Bagual", "Overo",
]
