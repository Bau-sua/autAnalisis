"""Validación de esquemas y calidad de datos crudos.

Detecta problemas estructurales antes de la limpieza:
- Columnas faltantes o sobrantes
- Tipos de datos incorrectos
- Valores fuera de rango
- Integridad referencial entre dimensiones y hechos
"""

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from src.utils.config import (
    ESQUEMAS_ESPERADOS,
    RANGOS_VALIDOS,
    TIPOS_ESTABLECIMIENTO_VALIDOS,
    TIPOS_MOVIMIENTO_VALIDOS,
    ZONAS_VALIDAS,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidacionResultado:
    """Resultado de la validación de un archivo."""

    archivo: str
    filas: int = 0
    columnas_esperadas: int = 0
    columnas_encontradas: int = 0
    columnas_faltantes: list[str] = field(default_factory=list)
    columnas_sobrantes: list[str] = field(default_factory=list)
    errores_tipo: list[str] = field(default_factory=list)
    valores_fuera_rango: int = 0
    errores_categoria: list[str] = field(default_factory=list)
    errores_referencia: list[str] = field(default_factory=list)

    @property
    def es_valido(self) -> bool:
        return (
            len(self.columnas_faltantes) == 0
            and len(self.errores_tipo) == 0
            and self.valores_fuera_rango == 0
            and len(self.errores_categoria) == 0
            and len(self.errores_referencia) == 0
        )

    def resumen(self) -> str:
        icono = "✅" if self.es_valido else "❌"
        partes = [f"{icono} {self.archivo}: {self.filas} filas"]
        if self.columnas_faltantes:
            partes.append(f"  Faltan: {self.columnas_faltantes}")
        if self.columnas_sobrantes:
            partes.append(f"  Sobran: {self.columnas_sobrantes}")
        if self.errores_tipo:
            partes.append(f"  Tipos erróneos: {len(self.errores_tipo)}")
        if self.valores_fuera_rango:
            partes.append(f"  Fuera de rango: {self.valores_fuera_rango}")
        if self.errores_categoria:
            partes.append(f"  Categorías inválidas: {len(self.errores_categoria)}")
        if self.errores_referencia:
            partes.append(f"  Ref. rotas: {len(self.errores_referencia)}")
        return "\n".join(partes)


def validar_esquema(
    df: pd.DataFrame, nombre_archivo: str
) -> ValidacionResultado:
    """Valida que un DataFrame cumpla con el esquema esperado.

    Args:
        df: DataFrame a validar.
        nombre_archivo: Nombre del archivo (clave en ESQUEMAS_ESPERADOS).

    Returns:
        ValidacionResultado con el diagnóstico.
    """
    if nombre_archivo not in ESQUEMAS_ESPERADOS:
        return ValidacionResultado(
            archivo=nombre_archivo,
            columnas_sobrantes=[f"Esquema no definido para {nombre_archivo}"],
        )

    esquema = ESQUEMAS_ESPERADOS[nombre_archivo]
    result = ValidacionResultado(
        archivo=nombre_archivo,
        filas=len(df),
        columnas_esperadas=len(esquema),
        columnas_encontradas=len(df.columns),
    )

    # Columnas faltantes
    for col in esquema:
        if col not in df.columns:
            result.columnas_faltantes.append(col)

    # Columnas sobrantes
    for col in df.columns:
        if col not in esquema:
            result.columnas_sobrantes.append(col)

    # Tipos de datos (solo en columnas que existen y no son nulas)
    for col, tipo_esperado in esquema.items():
        if col not in df.columns or df[col].dropna().empty:
            continue
        tipo_real = str(df[col].dropna().dtype)
        # Normalizar: 'object' y 'str' son equivalentes para columnas de texto
        tipo_real_norm = "object" if tipo_real in ("object", "str") else tipo_real
        tipo_esperado_norm = "object" if tipo_esperado in ("object", "str") else tipo_esperado
        if tipo_real_norm != tipo_esperado_norm:
            result.errores_tipo.append(
                f"{col}: esperado {tipo_esperado}, encontrado {tipo_real}"
            )

    return result


def validar_rangos(df: pd.DataFrame) -> int:
    """Detecta valores fuera de los rangos razonables definidos en RANGOS_VALIDOS.

    Returns:
        Número total de valores fuera de rango.
    """
    total = 0
    for col, (min_val, max_val) in RANGOS_VALIDOS.items():
        if col not in df.columns:
            continue
        serie = pd.to_numeric(df[col], errors="coerce")
        fuera = (serie < min_val) | (serie > max_val)
        fuera = fuera.fillna(False)
        n_fuera = fuera.sum()
        if n_fuera > 0:
            logger.debug("  %s: %d valores fuera de [%s, %s]", col, n_fuera, min_val, max_val)
        total += n_fuera
    return total


def validar_categorias(df: pd.DataFrame) -> list[str]:
    """Valida que columnas categóricas tengan valores del dominio esperado.

    Returns:
        Lista de mensajes de error.
    """
    errores = []

    if "zona" in df.columns:
        invalidas = set(df["zona"].dropna().unique()) - ZONAS_VALIDAS
        if invalidas:
            errores.append(f"zonas inválidas: {invalidas}")

    if "tipo" in df.columns:
        invalidas = set(df["tipo"].dropna().unique()) - TIPOS_ESTABLECIMIENTO_VALIDOS
        if invalidas:
            errores.append(f"tipos de establecimiento inválidos: {invalidas}")

    if "tipo_movimiento" in df.columns:
        invalidas = set(df["tipo_movimiento"].dropna().unique()) - TIPOS_MOVIMIENTO_VALIDOS
        if invalidas:
            errores.append(f"tipos de movimiento inválidos: {invalidas}")

    return errores


def validar_integridad_referencial(
    df: pd.DataFrame,
    col_fk: str,
    df_referencia: pd.DataFrame,
    col_pk: str,
) -> list[int]:
    """Verifica que los valores de una FK existan en la tabla de referencia.

    Returns:
        Lista de valores huérfanos.
    """
    if col_fk not in df.columns:
        return []
    valores = set(df[col_fk].dropna().astype(int))
    referencias = set(df_referencia[col_pk].dropna().astype(int))
    huerfanos = valores - referencias
    return sorted(huerfanos)


def validar_todos(
    datasets: dict[str, pd.DataFrame],
) -> dict[str, ValidacionResultado]:
    """Ejecuta todas las validaciones sobre los datasets cargados.

    Args:
        datasets: Diccionario {nombre_archivo: DataFrame}.

    Returns:
        Diccionario {nombre_archivo: ValidacionResultado}.
    """
    resultados = {}

    for nombre, df in datasets.items():
        # Validación estructural
        result = validar_esquema(df, nombre)
        # Rangos numéricos
        result.valores_fuera_rango = validar_rangos(df)
        # Categorías
        result.errores_categoria = validar_categorias(df)
        resultados[nombre] = result

    # Integridad referencial (usando datasets disponibles)
    for nombre, df in datasets.items():
        result = resultados[nombre]

        if nombre == "fact_stock_bovino.csv":
            for ref_nombre, col_fk, col_pk in [
                ("dim_departamentos.csv", "id_departamento", "id_departamento"),
                ("dim_categorias.csv", "id_categoria", "id_categoria"),
            ]:
                if ref_nombre in datasets:
                    h = validar_integridad_referencial(
                        df, col_fk, datasets[ref_nombre], col_pk
                    )
                    if h:
                        result.errores_referencia.append(
                            f"{col_fk} → {ref_nombre}: {len(h)} huérfanos"
                        )

        elif nombre == "fact_movimientos.csv":
            for ref_nombre, col_fk, col_pk in [
                ("dim_establecimientos.csv", "id_establecimiento", "id_establecimiento"),
                ("dim_categorias.csv", "id_categoria", "id_categoria"),
            ]:
                if ref_nombre in datasets:
                    h = validar_integridad_referencial(
                        df, col_fk, datasets[ref_nombre], col_pk
                    )
                    if h:
                        result.errores_referencia.append(
                            f"{col_fk} → {ref_nombre}: {len(h)} huérfanos"
                        )

        elif nombre == "fact_faena.csv" or nombre == "fact_precios.csv":
            if "dim_categorias.csv" in datasets:
                h = validar_integridad_referencial(
                    df, "id_categoria", datasets["dim_categorias.csv"], "id_categoria"
                )
                if h:
                    result.errores_referencia.append(
                        f"id_categoria → dim_categorias: {len(h)} huérfanos"
                    )

        elif nombre == "fact_clima.csv":
            if "dim_departamentos.csv" in datasets:
                h = validar_integridad_referencial(
                    df, "id_departamento", datasets["dim_departamentos.csv"], "id_departamento"
                )
                if h:
                    result.errores_referencia.append(
                        f"id_departamento → dim_departamentos: {len(h)} huérfanos"
                    )

    return resultados
