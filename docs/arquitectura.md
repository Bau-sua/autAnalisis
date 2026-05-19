# autAnalisis — Arquitectura del Proyecto

## 1. Dominio: Sector Agro-Ganadero de San Luis, Argentina

San Luis tiene dos perfiles productivos bien marcados:

| Zona | Actividad principal |
|------|-------------------|
| **Norte** (departamentos Ayacucho, Belgrano, San Martín) | Ganadería bovina extensiva (cría y recría) |
| **Centro-Sur** (departamentos Pedernera, Dupuy, Pringles) | Agricultura de secano + ganadería mixta |
| **Cuenca del Morro** | Agricultura bajo riego (maíz, soja, trigo) + feedlots |

### 1.1 Indicadores ganaderos más relevantes

| Indicador | Fuente típica | Frecuencia real |
|-----------|-------------|-----------------|
| **Stock bovino** por categoría (terneros/as, novillitos, vaquillonas, vacas, toros, novillos) | SENASA - campaña de vacunación aftosa | Anual / semestral |
| **Faena** (cabezas faenadas, peso promedio, rendimiento) | Ministerio de Agricultura / IPCVA | Mensual |
| **Precio del kg vivo** (novillo, vaquillona, ternero) | Mercado de Liniers / Mercados regionales | Semanal |
| **Precio al consumidor** (cortes vacunos) | IPC / INDEC | Mensual |
| **Exportaciones de carne** (volumen y valor) | SENASA / IPCVA | Mensual |
| **Movimientos de hacienda** (ingresos/egresos por DTe) | SENASA - SIGSA | Diario |
| **Tasa de extracción** (faena/stock) | Cálculo propio | Anual |
| **Producción de carne** (toneladas equivalente res con hueso) | Cálculo propio | Anual |
| **Condición corporal** del rodeo | Estimación por imágenes satelitales / NDVI | Trimestral |

### 1.2 Indicadores agrícolas más relevantes

| Indicador | Fuente típica | Frecuencia real |
|-----------|-------------|-----------------|
| **Superficie sembrada** por cultivo (soja, maíz, trigo, sorgo, girasol) | Ministerio de Agricultura / MAGyP | Campaña |
| **Superficie cosechada** por cultivo | MAGyP | Campaña |
| **Rendimiento** (kg/ha) por cultivo y departamento | Estimaciones agrícolas provinciales | Campaña |
| **Producción** (toneladas) por cultivo | MAGyP | Campaña |
| **Precio pizarra / FAS** de granos | Bolsa de Cereales / MATba-ROFEX | Diario |
| **Avance de siembra y cosecha** (% avance) | Bolsa de Cereales / Informes zonales | Semanal (en campaña) |
| **Humedad de suelo** (mm en perfil) | Imágenes satelitales / SMN | Semanal |
| **Precipitaciones** acumuladas | SMN / estaciones meteorológicas | Diario |
| **Exportaciones del complejo oleaginoso/cerealero** | INDEC / CIARA-CEC | Mensual |

### 1.3 Indicadores climáticos y cruzados

| Indicador | Relevancia |
|-----------|-----------|
| **Precipitación mensual/trimestral** vs media histórica | Impacto directo en pasturas y rindes |
| **Índice NDVI** (verdor) trimestral | Condición de pastizales naturales |
| **Relación de precios** ternero/novillo | Termómetro del ciclo ganadero |
| **Relación insumo-producto** (maíz/novillo) | Rentabilidad del feedlot |
| **Margen bruto** agrícola y ganadero estimado | Indicador síntesis |

---

## 2. Datos Sintéticos — Estrategia de Generación

**Principio**: No usar datos reales de ningún productor. Sintetizar con distribuciones verosímiles basadas en estadísticas públicas provinciales.

### 2.1 Fuentes públicas de referencia (para calibrar la síntesis)

- Anuarios estadísticos de San Luis (Dirección Provincial de Estadística)
- Informes del IPCVA (Instituto de Promoción de la Carne Vacuna)
- Estimaciones agrícolas del MAGyP (Ministerio de Agricultura, Ganadería y Pesca)
- Datos abiertos de SENASA (stock, movimientos, faena)
- SMN (Servicio Meteorológico Nacional) — datos climáticos históricos
- Datos del INDEC (precios, exportaciones)

### 2.2 Enfoque de síntesis

Para cada indicador generaremos datos sintéticos con estas propiedades:

```
datos_sintéticos = tendencia_base 
                   + estacionalidad (trimestral/anual) 
                   + ruido_controlado (distribución normal con media y desvío calibrados)
                   + anomalías_realistas_controladas
```

**Técnicas**:
- `numpy` + `scipy` para distribuciones estadísticas
- `Faker` para datos categóricos (nombres de establecimientos, localidades, etc.)
- `pandas` para estructurar series temporales
- Datos **desde 2020 hasta 2025** para tener serie histórica suficiente
- Unos **50-80 establecimientos** ficticios distribuidos en los 9 departamentos de San Luis
- Generación con **semilla fija** (`random_seed=42`) para reproducibilidad

### 2.3 Granularidad de los datos sintéticos

```
Nivel 1: Provincial (San Luis total)
Nivel 2: Departamentos (9 departamentos)
Nivel 3: Establecimientos (~50-80 ficticios, anonimizados con IDs)
Nivel 4: Lotes/potreros (~5-20 por establecimiento, opcional)
```

### 2.4 Esquema de tablas sintéticas propuesto

```
┌─────────────────────────────────────────────────┐
│                  DIMENSIONES                      │
├─────────────────────────────────────────────────┤
│ dim_departamentos    (id, nombre, zona, has_riego)│
│ dim_establecimientos (id, nombre_ficticio,        │
│                       id_departamento, tipo, ha)  │
│ dim_cultivos         (id, nombre, tipo, campaña)  │
│ dim_categorias_bovinas(id, nombre, grupo_etario)  │
│ dim_tiempo           (fecha, año, trimestre, mes) │
├─────────────────────────────────────────────────┤
│                  HECHOS                           │
├─────────────────────────────────────────────────┤
│ fact_stock_bovino     (fecha, dpto, cat, cabezas) │
│ fact_faena            (fecha, dpto, cat, cab, kg) │
│ fact_precios_ganado   (fecha, cat, precio_kg_vivo)│
│ fact_siembra          (campaña, dpto, cultivo, ha)│
│ fact_cosecha          (campaña, dpto, cultivo, ha,│
│                        rendimiento_kg_ha, prod_ton)│
│ fact_precios_granos   (fecha, cultivo, precio_tn) │
│ fact_clima            (fecha, dpto, pp_mm, t_media)│
│ fact_exportaciones    (fecha, producto, ton, usd) │
└─────────────────────────────────────────────────┘
```

---

## 3. Pipeline Completo: de Datos Crudos a Dashboard

```
+------------------+     +------------------+     +------------------+
|  1. GENERACIÓN   | --> |  2. ETL / LIMPIEZA| --> |  3. ANÁLISIS     |
|  datos sintéticos|     |  raw → staging    |     |  métricas + KPI  |
+------------------+     +------------------+     +------------------+
                                                            |
                                                            v
+------------------+     +------------------+     +------------------+
|  6. DESPLIEGUE   | <-- |  5. DASHBOARD     | <-- |  4. REPORTE      |
|  static site /   |     |  interactivo     |     |  markdown/PDF    |
|  servicio        |     |                  |     |  automático      |
+------------------+     +------------------+     +------------------+
```

### Fase 1: Generación de datos sintéticos
- Script `generar_datos.py`: genera todos los CSVs crudos con ruido e imperfecciones realistas
- Salida: `data/raw/*.csv` con datos deliberadamente "sucios" (nulos, outliers, formatos inconsistentes)
- **Esto es clave**: simulamos datos crudos como llegarían del campo

### Fase 2: ETL / Limpieza
- Script `etl_limpiar.py`:
  - Lectura de CSVs crudos
  - Validación de esquemas
  - Normalización de formatos (fechas, números, categorías)
  - Detección y tratamiento de outliers (IQR, z-score)
  - Imputación de valores faltantes (interpolación temporal o mediana por grupo)
  - Joins dimensionales
- Salida: `data/clean/*.parquet` (formato eficiente)

### Fase 3: Análisis y Cálculo de KPIs
- Script `analisis_kpi.py`:
  - Tasas de variación interanual e intertrimestral
  - Medias móviles (trimestrales y anuales)
  - Tendencias por regresión lineal simple
  - Rankings por departamento
  - Indicadores compuestos (margen bruto, relación ternero/novillo, etc.)
  - Detección de anomalías
- Salida: `data/processed/kpi_*.parquet` + `data/processed/resumen_trimestral.json`

### Fase 4: Generación de Reporte Automático
- Script `generar_reporte.py`:
  - Template en Markdown con variables Jinja2
  - Gráficos emebebidos generados con matplotlib/seaborn/plotly
  - Secciones: resumen ejecutivo, ganadería, agricultura, clima, comercio exterior
  - Conversión a PDF con `weasyprint` o `pandoc`
- Salida: `reports/YYYY-Q{N}_informe_trimestral.md` + `.pdf`

### Fase 5: Dashboard Interactivo
- Opción A: **Streamlit** — más simple, perfecto para dashboards de datos, deploy trivial
- Opción B: **Dash (Plotly)** — más control visual, más boilerplate
- Componentes:
  - Mapa de San Luis con indicadores por departamento (choropleth)
  - Series temporales con controles de fecha y filtros
  - Rankings y tablas dinámicas
  - Exportación a PDF/Excel
- Salida: app en `dashboard/app.py`

### Fase 6: Despliegue
- Generar sitio estático con informes o servir con Streamlit Cloud / Render / VPS
- GitHub Actions para automatizar pipeline completo:
  ```yaml
  schedule: "0 0 1 1,4,7,10 *"  # primer día de cada trimestre
  ```
- Opcional: envío automático por email del PDF generado

---

## 4. Stack Tecnológico Recomendado

| Capa | Herramienta | Justificación |
|------|------------|--------------|
| **Lenguaje** | Python 3.11+ | Ecosistema maduro para datos |
| **Datos** | Pandas, NumPy, Polars (opcional) | Manipulación eficiente |
| **Síntesis** | Faker, NumPy (random) | Generación realista |
| **Visualización** | Plotly + Plotly Express | Interactivo, mapas, exportable |
| **Dashboard** | **Streamlit** | El más rápido para prototipar dashboards |
| **Reportes** | Jinja2 + WeasyPrint / Pandoc | Templates → PDF |
| **Pipeline** | Prefect o scripts Python simples + cron | Orquestación |
| **Base de datos** | SQLite / DuckDB (embebida) | Sin servidor, archivo único |
| **Testing** | Pytest | Calidad de datos y transformaciones |
| **Versionado** | Git + GitHub | Código y configuración |
| **CI/CD** | GitHub Actions | Automatización trimestral/anual |
| **AI (opcional)** | LLM local u OpenAI API | Resumen narrativo del reporte |

### ¿Cuándo usar AI?

- **Resumen narrativo automático**: "Este trimestre el stock bovino cayó un 3.2% respecto al mismo período del año anterior, principalmente en los departamentos del norte..."
- **Detección de anomalías con contexto**: "Se detectó una caída atípica en la faena de mayo, posiblemente relacionada con las lluvias que impidieron el traslado de hacienda..."
- **No usar AI para**: cálculos numéricos, gráficos, ETL. Eso es Python puro.

---

## 5. Estructura de Directorios Propuesta

```
autAnalisis/
├── data/
│   ├── raw/              # CSVs crudos generados sintéticamente
│   ├── clean/            # Parquet limpios
│   └── processed/        # KPIs y resúmenes calculados
├── src/
│   ├── generacion/       # generar_datos.py, schemas.py
│   ├── etl/              # limpiar.py, validar.py, normalizar.py
│   ├── analisis/         # kpis.py, tendencias.py, anomalias.py
│   ├── reporte/          # generar_reporte.py, templates/
│   └── utils/            # config.py, logging_config.py, helpers.py
├── dashboard/
│   ├── app.py            # Streamlit principal
│   ├── pages/            # Páginas del dashboard
│   └── components/       # Gráficos reutilizables
├── reports/              # Informes generados (MD + PDF)
├── tests/                # Pytest
├── notebooks/            # Exploración y prototipado (Jupyter)
├── docs/                 # Documentación (esta carpeta)
├── .github/
│   └── workflows/
│       └── pipeline.yml  # CI/CD trimestral
├── Makefile              # Tareas comunes
├── pyproject.toml        # Dependencias y config
└── README.md
```

---

## 6. Hoja de Ruta (Roadmap)

### Milestone 1: Fundación (sesión actual)
- [x] Inicializar repo Git
- [x] Definir arquitectura (este documento)
- [ ] Elegir stack concreto (Streamlit vs Dash, etc.)
- [ ] Configurar entorno Python (uv o pip + venv)

### Milestone 2: Datos Sintéticos
- [ ] Diseñar esquemas de datos (tablas, columnas, tipos)
- [ ] Implementar `generar_datos.py` con datos ganaderos
- [ ] Implementar datos agrícolas
- [ ] Implementar datos climáticos
- [ ] Generar primeros CSVs de prueba

### Milestone 3: ETL y Limpieza
- [ ] Implementar pipeline de limpieza
- [ ] Validación de calidad de datos
- [ ] Tests unitarios para transformaciones

### Milestone 4: Análisis y KPIs
- [ ] Calcular indicadores trimestrales
- [ ] Calcular indicadores anuales
- [ ] Tests para KPIs

### Milestone 5: Dashboard
- [ ] Streamlit app con layout base
- [ ] Gráficos por sección (ganadería, agricultura, clima)
- [ ] Filtros interactivos (fecha, departamento)

### Milestone 6: Reporte Automático
- [ ] Template Jinja2 del informe
- [ ] Generación MD + PDF
- [ ] Integración con pipeline

### Milestone 7: CI/CD y Despliegue
- [ ] GitHub Actions para pipeline programado
- [ ] Deploy del dashboard
- [ ] Documentación final

---

## 7. Decisiones Tomadas

| Decisión | Elección | Fecha |
|----------|---------|-------|
| **Dashboard** | **Streamlit** — Simplicidad, deploy trivial, gran ecosistema | 2026-05-19 |
| **Foco inicial** | **Ganadería primero** — Stock bovino, faena, precios. Agricultura en milestone posterior | 2026-05-19 |
| **LLM para resumen narrativo** | **Grok (xAI)** — recomendado por relación costo/calidad. OpenAI como alternativa válida | 2026-05-19 |
| **Base de datos** | SQLite/DuckDB (embebida, sin servidor) — consistente con el objetivo de simplicidad | 2026-05-19 |
| **Package manager** | **uv** — rápido, moderno, reemplaza pip + venv + pip-tools en una sola herramienta | 2026-05-19 |
| **Alcance sesión inicial** | Solo planificación. Implementación en sesiones siguientes | 2026-05-19 |

### Stack confirmado (completo)

| Herramienta | Uso |
|-------------|-----|
| uv | Package manager y entorno virtual |
| Python 3.11+ | Lenguaje base |
| Pandas + NumPy | Manipulación de datos |
| Streamlit | Dashboard interactivo |
| Plotly | Visualizaciones |
| SQLite / DuckDB | Base de datos embebida |
| Jinja2 + WeasyPrint | Templates de reporte → PDF |
| Grok (xAI) | Resumen narrativo automático (fase futura) |
| Pytest | Testing |
| GitHub Actions | CI/CD programado |

### Pendientes para definir en milestones futuros
- Despliegue concreto del dashboard (Streamlit Cloud vs VPS propio)

---

## 8. Lo Más Relevante para el Dashboard (Resumen Ejecutivo)

Si tuviera que elegir **los 8 indicadores que más impacto visual y analítico** tendrían en un dashboard trimestral:

| # | Indicador | Visualización | ¿Por qué? |
|---|----------|--------------|-----------|
| 1 | **Stock bovino provincial** (serie temporal 5 años) | Línea + barra por categoría | Refleja el ciclo ganadero completo |
| 2 | **Mapa de stock por departamento** | Choropleth San Luis | Dimensión geográfica, impacto visual |
| 3 | **Faena mensual + precio kg vivo** | Doble eje Y (barras + línea) | Relación oferta-precio |
| 4 | **Producción de granos por campaña** | Barras apiladas por cultivo | Foto completa del agro |
| 5 | **Rendimientos (kg/ha) vs media histórica** | Línea con banda de confianza | Performance relativa |
| 6 | **Precipitaciones trimestrales vs normal** | Barras con línea de referencia | Impacto climático en producción |
| 7 | **Relación ternero/novillo** | Línea de tiempo + umbrales | Termómetro del ciclo ganadero |
| 8 | **Exportaciones (volumen + valor)** | Barras + línea | Dimensión macroeconómica |
