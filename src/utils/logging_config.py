"""Utilidades de logging compartidas."""

import logging
import sys
from pathlib import Path


def setup_logging(
    nivel: int = logging.INFO,
    archivo: Path | None = None,
    modulo: str = "autAnalisis",
) -> logging.Logger:
    """Configura logging con formato unificado.

    Args:
        nivel: Nivel de logging (INFO por defecto).
        archivo: Si se provee, loggea también a archivo.
        modulo: Nombre del módulo para el logger.

    Returns:
        Logger configurado.
    """
    logger = logging.getLogger(modulo)
    logger.setLevel(nivel)

    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Consola
    handler_consola = logging.StreamHandler(sys.stdout)
    handler_consola.setFormatter(fmt)
    logger.addHandler(handler_consola)

    # Archivo opcional
    if archivo:
        archivo.parent.mkdir(parents=True, exist_ok=True)
        handler_archivo = logging.FileHandler(archivo, encoding="utf-8")
        handler_archivo.setFormatter(fmt)
        logger.addHandler(handler_archivo)

    return logger
