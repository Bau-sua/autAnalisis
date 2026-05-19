# 🐄 autAnalisis

**Automatización de reportes y dashboard agro-ganaderos para San Luis, Argentina.**

Pipeline completo desde datos crudos sintéticos hasta informes narrativos con IA y dashboard interactivo. Diseñado para ejecución trimestral y anual sin intervención manual.

---

## 🚀 Arranque rápido

```bash
git clone https://github.com/Bau-sua/autAnalisis.git
cd autAnalisis

# Instalar dependencias (usa uv)
uv sync

# Pipeline completo
make generar    # Datos sintéticos
make etl        # Limpieza
make kpis       # Indicadores
make reporte    # Informe anual (Markdown)
```

---

## 📋 Comandos disponibles

| Comando                 | Qué hace                                                          |
| ----------------------- | ----------------------------------------------------------------- |
| `make generar`          | Genera 10 CSVs con datos ganaderos sintéticos (2020-2025)         |
| `make etl`              | Pipeline de limpieza: normaliza, imputa, trata outliers → Parquet |
| `make kpis`             | Calcula indicadores: stock, faena, precios, clima, compuestos     |
| `make reporte AÑO=2024` | Genera informe anual/trimestral en Markdown + PDF con gráficos          |
| `make dashboard`        | Inicia dashboard interactivo en http://localhost:8501             |
| `make test`             | Corre 22 tests unitarios                                          |
| `make notebook`         | Jupyter Lab para exploración de datos                             |

### Informes trimestrales

```bash
make reporte AÑO=2024                           # Anual
uv run python src/reporte/generar_reporte.py --tipo trimestral --año 2024 --trimestre 4
```

### Narrativa con IA (Grok)

```bash
export XAI_API_KEY="tu-api-key"
make reporte AÑO=2024   # ahora incluye análisis narrativo de Grok
```

---

## 🏗️ Arquitectura del pipeline

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  GENERACIÓN  │ →  │  ETL / LIMP  │ →  │  KPIs        │
│  10 CSVs     │    │  10 Parquet  │    │  8 Parquet   │
│  (sucios)    │    │  (limpios)   │    │  (métricas)  │
└──────────────┘    └──────────────┘    └──────────────┘
                                               │
                    ┌──────────────────────────┤
                    ▼                          ▼
            ┌──────────────┐          ┌──────────────┐
            │  REPORTES     │          │  DASHBOARD   │
            │  MD + PDF     │          │  Streamlit   │
            │  (+ Grok IA)  │          │  + Plotly    │
            └──────────────┘          └──────────────┘
```

### Datos generados

| Capa          | Formato | Archivos | Características                                                                   |
| ------------- | ------- | -------- | --------------------------------------------------------------------------------- |
| **Raw**       | CSV     | 10       | Datos «sucios»: nulos (3%), outliers (2%), fechas inconsistentes (5%), duplicados |
| **Clean**     | Parquet | 10       | Fechas normalizadas, nulos imputados, outliers tratados, texto estandarizado      |
| **Processed** | Parquet | 8        | KPIs: stock, faena, precios, clima, compuestos                                    |

### Técnicas de limpieza

- **Fechas**: parseo dual (ISO 8601 + DD/MM/YYYY argentino)
- **Nulos**: mediana por grupo (departamento) para numéricos, moda para categóricos
- **Outliers**: z-score con MAD agrupado por departamento + categoría + año (evita falsos positivos en series inflacionarias)
- **Duplicados**: detección y eliminación
- **Texto**: normalización de mayúsculas/minúsculas

---

## 🖥️ Dashboard

Dashboard interactivo con Streamlit y Plotly. Tres vistas:

| Página        | Contenido                                                                                    |
| ------------- | -------------------------------------------------------------------------------------------- |
| **Inicio**    | 5 KPI cards, tabla resumen anual, gráficos principales                                       |
| **Ganadería** | Stock (evolución, depto, categoría), faena (mensual + anual), precios, ratio ternero/novillo |
| **Clima**     | Precipitaciones, anomalías por departamento, temperatura, impacto sequía 2022-2023           |

### Gráficos incluidos (10)

- Evolución del stock con variación interanual
- Stock por departamento (barras horizontales)
- Composición por categoría (donut)
- Faena mensual con media móvil 3 meses
- Faena anual con variación
- Precio del novillo con variación interanual
- Precios comparados (ternero, novillo, vaca)
- Relación ternero/novillo con bandas de ciclo ganadero
- Precipitación anual con colores de anomalía
- Anomalía hídrica por departamento
- Temperatura media anual

---

## 📄 Reportes automáticos

### Template anual

```
📊 Resumen Ejecutivo (tabla de KPIs)
🤖 Análisis narrativo (Grok IA o fallback por reglas)
🐄 Stock bovino (evolución, top departamentos, composición)
🔪 Faena (anual, mensual, producción, peso promedio)
💰 Precios (evolución, ratio ternero/novillo)
🌧️ Clima (precipitaciones, anomalías)
📈 Conclusiones
```

### Template trimestral

Incluye además:

- Faena y producción acumulada del trimestre
- Alertas automáticas (sequía, faena de hembras elevada, ratio alto)
- Proyección para el resto del año

### Narrativa con IA

Cuando se configura `XAI_API_KEY`, Grok (xAI) genera un análisis de 3 párrafos en español rioplatense con voseo:

> _"Durante 2024 el stock bovino de San Luis alcanzó 1.295.755 cabezas, con un crecimiento interanual del 11%, impulsado por las condiciones climáticas favorables. Las precipitaciones anuales de 497 mm, un 53,4% por encima del promedio..."_

Sin API key, el sistema usa un fallback basado en reglas.

---

## ⚙️ CI/CD

Pipeline automatizado con GitHub Actions:

```
⏰ Schedule:   cada 1° de enero, abril, julio, octubre
🖐️ Manual:     workflow_dispatch desde la pestaña Actions
📦 Steps:      tests → generar → ETL → KPIs → informe → upload
📤 Artifacts:  informes Markdown (90 días de retención)
🔑 Secrets:    XAI_API_KEY (opcional, para narrativas con IA)
```

---

## 🧪 Tests

```bash
make test
# 22 passed in 0.47s
```

Cobertura: normalización de fechas, corrección de tipos, imputación de nulos, tratamiento de outliers, eliminación de duplicados, estandarización de texto, validación de esquemas.

---

## 🗂️ Estructura del proyecto

```
autAnalisis/
├── .github/workflows/pipeline.yml    # CI/CD trimestral
├── data/
│   ├── raw/                          # 10 CSVs con «suciedad» deliberada
│   ├── clean/                        # 10 Parquet normalizados
│   └── processed/                    # 8 Parquet de KPIs
├── src/
│   ├── generacion/
│   │   ├── schemas.py                # 7 categorías, 9 deptos, 60 establecimientos
│   │   └── generar_datos.py           # Generador de datos sintéticos
│   ├── etl/
│   │   ├── validar.py                 # Validación de esquemas y referencias
│   │   └── limpiar.py                # Pipeline ETL de 7 pasos
│   ├── analisis/
│   │   └── kpis.py                   # Cálculo de indicadores compuestos
│   ├── reporte/
│   │   ├── generar_reporte.py         # Jinja2 + matplotlib → Markdown
│   │   ├── narrativa.py              # Grok API → narrativa en español
│   │   └── templates/
│   │       ├── informe_anual.md.j2
│   │       └── informe_trimestral.md.j2
│   └── utils/
│       ├── config.py                  # Rutas, esquemas, constantes
│       └── logging_config.py          # Logging unificado
├── dashboard/
│   ├── app.py                        # Streamlit — vista principal
│   ├── components/
│   │   └── graficos.py               # 10 funciones Plotly reutilizables
│   └── pages/
│       ├── 1_ganaderia.py            # Stock, faena, precios
│       └── 2_clima.py                # Precipitaciones, temperatura
├── docs/
│   └── arquitectura.md               # Documento de arquitectura completo
├── notebooks/
│   └── 01_exploracion_datos.ipynb    # Validación visual de datos
├── tests/
│   └── test_etl.py                   # 22 tests unitarios
├── reports/                          # Informes generados (gitignored)
├── pyproject.toml                     # Dependencias y configuración
└── Makefile                           # 7 targets
```

---

## 🛠️ Stack tecnológico

| Herramienta        | Uso                                |
| ------------------ | ---------------------------------- |
| **Python 3.12**    | Lenguaje base                      |
| **uv**             | Package manager y entorno virtual  |
| **pandas + numpy** | Manipulación y generación de datos |
| **Streamlit**      | Dashboard interactivo              |
| **Plotly**         | Gráficos interactivos              |
| **matplotlib**     | Gráficos para reportes (base64)    |
| **Jinja2**         | Templates de informes              |
| **Grok (xAI)**     | Narrativa automática con IA        |
| **pytest**         | Tests unitarios                    |
| **GitHub Actions** | CI/CD programado                   |
| **pyarrow**        | Formato Parquet                    |

---

## 📊 KPIs calculados

| Indicador                    | Descripción                               |
| ---------------------------- | ----------------------------------------- |
| **Stock total**              | Cabezas por año, departamento y categoría |
| **Variación YoY**            | Interanual de stock, faena y precios      |
| **Tasa de extracción**       | Faena / Stock                             |
| **Relación ternero/novillo** | Indicador de ciclo ganadero               |
| **% Hembras en faena**       | Alerta de liquidación de vientres         |
| **Precipitación anual**      | Con anomalía vs media histórica           |
| **Condición hídrica**        | Seco / Normal / Húmedo por departamento   |

---

## 🌾 Dominio: Sector ganadero de San Luis

San Luis tiene dos perfiles productivos principales:

| Zona       | Departamentos                         | Actividad                         |
| ---------- | ------------------------------------- | --------------------------------- |
| **Norte**  | Ayacucho, Belgrano, San Martín, Junín | Ganadería bovina extensiva (cría) |
| **Sur**    | Dupuy, Pedernera, Pringles            | Ganadería mixta + agricultura     |
| **Centro** | Chacabuco, Pueyrredón                 | Mixto                             |

**9 departamentos · ~60 establecimientos ficticios · 7 categorías bovinas · 5 años de datos (2020-2024)**

### Categorías bovinas (SENASA)

Ternero, Ternera, Novillito, Vaquillona, Novillo, Vaca, Toro

### Fuentes de referencia

Los datos sintéticos están calibrados con estadísticas públicas de:

- **SENASA** (stock, movimientos, faena)
- **IPCVA** (precios, exportaciones)
- **MAGyP** (estimaciones agrícolas)
- **SMN** (datos climáticos)

---

## 📝 Licencia

Proyecto de estudio. Datos sintéticos, sin información real de productores.

---

_«El stock bovino de San Luis se ubicó en 1.295.755 cabezas, con una variación interanual del +11.0%.»_ — Informe 2024
