"""Generación de resúmenes narrativos con Grok (xAI) para informes ganaderos.

Toma el contexto de KPIs y genera un resumen ejecutivo en español rioplatense
con análisis de los datos del período, tendencias detectadas y recomendaciones.

Requiere: variable de entorno XAI_API_KEY con la API key de xAI.
Si no está configurada, genera un resumen basado en templates.

Uso:
    from src.reporte.narrativa import generar_narrativa
    texto = generar_narrativa(ctx, tipo="anual")
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Modelo a usar
GROK_MODEL = os.environ.get("GROK_MODEL", "grok-3")

# Máximo de tokens para la respuesta narrativa
MAX_TOKENS = int(os.environ.get("GROK_MAX_TOKENS", "600"))


def _tiene_api_key() -> bool:
    """Verifica si hay una API key de xAI configurada."""
    return bool(os.environ.get("XAI_API_KEY"))


def _llamar_grok(system_prompt: str, user_prompt: str) -> str | None:
    """Llama a la API de Grok (xAI) usando el cliente OpenAI-compatible.

    Args:
        system_prompt: Instrucciones de sistema para el modelo.
        user_prompt: Datos y consulta del usuario.

    Returns:
        Texto de respuesta del modelo, o None si falla.
    """
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai no instalado. Instalalo con: uv add openai")
        return None

    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        return None

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )
        response = client.chat.completions.create(
            model=GROK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=MAX_TOKENS,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.warning("Error al llamar a Grok API: %s", e)
        return None


def _construir_prompt_sistema(tipo: str) -> str:
    """Construye el prompt de sistema para Grok según el tipo de informe."""
    base = (
        "Sos un analista ganadero senior de la provincia de San Luis, Argentina. "
        "Tu tarea es escribir un resumen ejecutivo profesional en español rioplatense "
        "para un informe del sector ganadero bovino.\n\n"
        "Reglas:\n"
        "- Usar voseo rioplatense (ej: 'podés observar', 'tenés que considerar').\n"
        "- Ser conciso: máximo 3 párrafos.\n"
        "- Incluir números y porcentajes concretos de los datos proporcionados.\n"
        "- Destacar tendencias, anomalías y relaciones entre indicadores.\n"
        "- Mencionar el impacto de las condiciones climáticas en la producción.\n"
        "- Si hay datos de sequía o exceso hídrico, señalarlo.\n"
        "- Interpretar la relación ternero/novillo como indicador del ciclo ganadero.\n"
        "- NO inventar datos que no estén en la información proporcionada.\n"
        "- NO usar markdown, solo texto plano."
    )
    if tipo == "trimestral":
        base += (
            "\n- El informe es TRIMESTRAL: enfocarse en lo ocurrido en el trimestre "
            "y comparar con el mismo trimestre del año anterior si hay datos.\n"
            "- Incluir proyecciones para el resto del año."
        )
    else:
        base += (
            "\n- El informe es ANUAL: hacer un balance completo del año."
        )
    return base


def _construir_prompt_usuario(ctx: dict[str, Any], tipo: str) -> str:
    """Construye el prompt con los datos del contexto para Grok."""
    lineas = ["# Datos del informe ganadero de San Luis", ""]

    if tipo == "anual":
        lineas.append(f"Año: {ctx.get('año', '?')}")
    else:
        lineas.append(f"Período: Q{ctx.get('trimestre', '?')} {ctx.get('año', '?')}")

    lineas.extend([
        "",
        "## Indicadores principales",
        f"- Stock bovino total: {ctx.get('stock_total', 'No disponible')}",
        f"- Variación interanual del stock: {ctx.get('stock_var_yoy', 'No disponible')}",
        f"- Faena total: {ctx.get('faena_total', 'No disponible')}",
        f"- Variación interanual de faena: {ctx.get('faena_var_yoy', 'No disponible')}",
        f"- Producción de carne: {ctx.get('faena_produccion', 'No disponible')}",
        f"- Peso promedio carcasa: {ctx.get('faena_peso_promedio', 'No disponible')}",
        f"- Participación de hembras en faena: {ctx.get('faena_hembras_pct', 'No disponible')}",
        f"- Precio promedio del novillo: {ctx.get('precio_novillo_prom', 'No disponible')}",
        f"- Variación interanual del precio: {ctx.get('precio_var_yoy', 'No disponible')}",
        f"- Relación ternero/novillo: {ctx.get('ratio_ternero_novillo', 'No disponible')}",
        f"- Precipitación anual: {ctx.get('pp_anual', 'No disponible')}",
        f"- Anomalía de precipitación: {ctx.get('pp_anomalia', 'No disponible')}",
        f"- Temperatura media: {ctx.get('temp_media', 'No disponible')}",
        f"- Tasa de extracción: {ctx.get('tasa_extraccion', 'No disponible')}",
        "",
        "## Top 5 departamentos por stock",
    ])

    for i, d in enumerate(ctx.get("top_deptos", []), 1):
        lineas.append(f"{i}. {d['nombre']}: {d['cabezas']}")

    if ctx.get("deptos_secos"):
        lineas.append("")
        lineas.append("## Departamentos con déficit hídrico severo")
        for d in ctx["deptos_secos"]:
            lineas.append(f"- ID: {d}")

    if tipo == "trimestral":
        lineas.extend([
            "",
            f"Faena del trimestre: {ctx.get('faena_trimestral', 'No disponible')}",
            f"Producción del trimestre: {ctx.get('produccion_trimestral', 'No disponible')}",
        ])

    lineas.append("")
    lineas.append("Escribí un resumen ejecutivo de 3 párrafos analizando estos datos.")

    return "\n".join(lineas)


def _narrativa_fallback(ctx: dict[str, Any], tipo: str) -> str:
    """Genera un resumen basado en templates cuando no hay API key disponible.

    Args:
        ctx: Contexto con los KPIs.
        tipo: "anual" o "trimestral".

    Returns:
        Texto narrativo basado en reglas.
    """
    partes = []

    # Párrafo 1: Stock
    stock = ctx.get("stock_total", "—")
    var_stock = ctx.get("stock_var_yoy", "—")
    if stock != "—":
        direccion = "creció" if var_stock.startswith("+") else "disminuyó"
        partes.append(
            f"El stock bovino de San Luis se ubicó en {stock}, lo que representa "
            f"una variación interanual del {var_stock}. Este comportamiento indica "
            f"una fase de {'retención' if var_stock.startswith('+') else 'liquidación'} "
            f"del ciclo ganadero provincial."
        )

    # Párrafo 2: Faena y precios
    faena = ctx.get("faena_total", "—")
    precio = ctx.get("precio_novillo_prom", "—")
    ratio = ctx.get("ratio_ternero_novillo", "—")
    if faena != "—" and precio != "—":
        partes.append(
            f"La faena total alcanzó {faena}, con un precio promedio del novillo "
            f"de {precio}. La relación ternero/novillo se ubicó en {ratio}, "
            f"{'por encima del equilibrio de largo plazo (1.15), señal de retención' if ratio != '—' and float(ratio) > 1.2 else 'dentro de parámetros normales'}."
        )

    # Párrafo 3: Clima
    pp = ctx.get("pp_anual", "—")
    anomalia = ctx.get("pp_anomalia", "—")
    if pp != "—":
        condicion = "favorables" if anomalia.startswith("+") else "desfavorables"
        partes.append(
            f"Las precipitaciones anuales totalizaron {pp} (anomalía: {anomalia}), "
            f"configurando un año con condiciones {condicion} para la actividad ganadera."
        )

    return "\n\n".join(partes) if partes else "No hay datos suficientes para generar un resumen."


def generar_narrativa(ctx: dict[str, Any], tipo: str = "anual") -> str:
    """Genera un resumen narrativo del informe usando Grok o fallback por template.

    Args:
        ctx: Contexto con todos los KPIs (de construir_contexto_anual/trimestral).
        tipo: "anual" o "trimestral".

    Returns:
        Texto narrativo en español rioplatense.
    """
    if _tiene_api_key():
        logger.info("Generando narrativa con Grok (%s)...", GROK_MODEL)
        system_prompt = _construir_prompt_sistema(tipo)
        user_prompt = _construir_prompt_usuario(ctx, tipo)
        resultado = _llamar_grok(system_prompt, user_prompt)
        if resultado:
            return resultado
        logger.info("Grok falló, usando fallback por template.")

    logger.info("Generando narrativa por template (sin API key).")
    return _narrativa_fallback(ctx, tipo)
