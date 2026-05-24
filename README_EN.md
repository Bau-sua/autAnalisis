# 🐄 autAnalisis

**Automated reporting and dashboard system for livestock/agricultural data from San Luis, Argentina.**

> 🇪🇸 [Versión en español](README.md)

Complete pipeline from synthetic raw data to AI-powered narrative reports and an interactive dashboard. Designed for quarterly and annual execution without manual intervention.

---

## 🚀 Quick Start

```bash
git clone https://github.com/Bau-sua/autAnalisis.git
cd autAnalisis

# Install dependencies (uses uv)
uv sync

# Full pipeline
make generar    # Generate synthetic data
make etl        # Clean & transform
make kpis       # Calculate indicators
make reporte    # Generate annual report (Markdown + PDF)
```

---

## 📋 Available Commands

| Command | What it does |
|---------|-------------|
| `make generar` | Generates 10 CSVs with synthetic livestock data (2020–2025) |
| `make etl` | Cleaning pipeline: normalize, impute, treat outliers → Parquet |
| `make kpis` | Calculates indicators: stock, slaughter, prices, climate, composites |
| `make reporte` | Generates annual/quarterly report in Markdown with charts |
| `make dashboard` | Starts interactive dashboard at http://localhost:8501 |
| `make test` | Runs 22 unit tests |
| `make notebook` | Jupyter Lab for data exploration |

### Quarterly Reports

```bash
make reporte AÑO=2024                           # Annual
uv run python src/reporte/generar_reporte.py --tipo trimestral --año 2024 --trimestre 4
```

### AI Narrative (Grok)

```bash
export XAI_API_KEY="your-api-key"
make reporte AÑO=2024   # now includes Grok narrative analysis
```

---

## 🏗️ Pipeline Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  GENERATION  │ →  │  ETL / CLEAN │ →  │  KPIs        │
│  10 CSVs     │    │  10 Parquet  │    │  8 Parquet   │
│  (raw)       │    │  (clean)     │    │  (metrics)   │
└──────────────┘    └──────────────┘    └──────────────┘
                                               │
                    ┌──────────────────────────┤
                    ▼                          ▼
            ┌──────────────┐          ┌──────────────┐
            │  REPORTS      │          │  DASHBOARD   │
            │  MD + PDF     │          │  Streamlit   │
            │  (+ Grok AI)  │          │  + Plotly    │
            └──────────────┘          └──────────────┘
```

### Data Layers

| Layer | Format | Files | Characteristics |
|-------|--------|-------|----------------|
| **Raw** | CSV | 10 | "Dirty" data: 3% nulls, 2% outliers, 5% inconsistent dates, duplicates |
| **Clean** | Parquet | 10 | Normalized dates, imputed nulls, treated outliers, standardized text |
| **Processed** | Parquet | 8 | KPIs: stock, slaughter, prices, climate, composites |

### Cleaning Techniques

- **Dates**: dual parsing (ISO 8601 + Argentine DD/MM/YYYY)
- **Nulls**: median by group (department) for numeric, mode for categorical
- **Outliers**: z-score with MAD grouped by department + category + year (prevents false positives across inflation periods)
- **Duplicates**: detection and removal
- **Text**: uppercase/lowercase normalization

---

## 🖥️ Dashboard

Interactive dashboard with Streamlit and Plotly. Three views:

| Page | Content |
|------|---------|
| **Home** | 5 KPI cards, annual summary table, main charts |
| **Livestock** | Stock (evolution, dept, category), slaughter (monthly + annual), prices, calf/steer ratio |
| **Climate** | Precipitation, anomalies by department, temperature, 2022–2023 drought impact |

### Charts Included (10)

- Stock evolution with year-over-year variation
- Stock by department (horizontal bars)
- Composition by category (donut)
- Monthly slaughter with 3-month moving average
- Annual slaughter with variation
- Steer price with year-over-year variation
- Comparative prices (calf, steer, cow)
- Calf/steer ratio with cattle cycle bands
- Annual precipitation with anomaly colors
- Hydric anomaly by department
- Annual average temperature

---

## 📄 Automated Reports

### Annual Template

```
Executive Summary (KPI table)
AI Narrative Analysis (Grok AI or rule-based fallback)
Livestock Stock (evolution, top departments, composition)
Slaughter (annual, monthly, production, average weight)
Prices (evolution, calf/steer ratio)
Climate (precipitation, anomalies)
Conclusions
```

### Quarterly Template

Additionally includes:
- Quarterly slaughter and cumulative production
- Automatic alerts (drought, high female slaughter, high ratio)
- Projection for the rest of the year

### AI Narrative

When `XAI_API_KEY` is configured, Grok (xAI) generates a 3-paragraph analysis in Rioplatense Spanish:

> *"During 2024, the bovine stock of San Luis reached 1,295,755 head, with a year-over-year growth of 11%, driven by favorable climatic conditions. Annual precipitation of 497 mm, 53.4% above average..."*

Without API key, the system uses a rule-based fallback.

---

## ⚙️ CI/CD

Automated pipeline with GitHub Actions:

```
⏰ Schedule:   1st of January, April, July, October
🖐️ Manual:     workflow_dispatch from Actions tab
📦 Steps:      tests → generate → ETL → KPIs → report → upload
📤 Artifacts:  Markdown reports (90-day retention)
🔑 Secrets:    XAI_API_KEY (optional, for AI narratives)
```

---

## 🧪 Tests

```bash
make test
# 22 passed in 0.47s
```

Coverage: date normalization, type correction, null imputation, outlier treatment, duplicate removal, text standardization, schema validation.

---

## 🗂️ Project Structure

```
autAnalisis/
├── .github/workflows/pipeline.yml    # CI/CD quarterly pipeline
├── data/
│   ├── raw/                          # 10 CSVs with deliberate "dirt"
│   ├── clean/                        # 10 normalized Parquet files
│   └── processed/                    # 8 KPI Parquet files
├── src/
│   ├── generacion/
│   │   ├── schemas.py                # 7 categories, 9 depts, 60 establishments
│   │   └── generar_datos.py           # Synthetic data generator
│   ├── etl/
│   │   ├── validar.py                 # Schema and reference validation
│   │   └── limpiar.py                # 7-step ETL pipeline
│   ├── analisis/
│   │   └── kpis.py                   # Composite indicator calculation
│   ├── reporte/
│   │   ├── generar_reporte.py         # Jinja2 + matplotlib → Markdown
│   │   ├── narrativa.py              # Grok API → Spanish narrative
│   │   └── templates/
│   │       ├── informe_anual.md.j2
│   │       └── informe_trimestral.md.j2
│   └── utils/
│       ├── config.py                  # Paths, schemas, constants
│       └── logging_config.py          # Unified logging
├── dashboard/
│   ├── app.py                        # Streamlit — main view
│   ├── components/
│   │   └── graficos.py               # 10 reusable Plotly functions
│   └── pages/
│       ├── 1_ganaderia.py            # Stock, slaughter, prices
│       └── 2_clima.py                # Precipitation, temperature
├── docs/
│   └── arquitectura.md               # Complete architecture document
├── notebooks/
│   └── 01_exploracion_datos.ipynb    # Visual data validation
├── tests/
│   └── test_etl.py                   # 22 unit tests
├── reports/                          # Generated reports (gitignored)
├── pyproject.toml                     # Dependencies and configuration
└── Makefile                           # 7 targets
```

---

## 🛠️ Tech Stack

| Tool | Use |
|------|-----|
| **Python 3.12** | Base language |
| **uv** | Package manager and virtual environment |
| **pandas + numpy** | Data manipulation and generation |
| **Streamlit** | Interactive dashboard |
| **Plotly** | Interactive charts |
| **matplotlib** | Report charts (base64) |
| **Jinja2** | Report templates |
| **Grok (xAI)** | Automatic AI narrative |
| **pytest** | Unit tests |
| **GitHub Actions** | Scheduled CI/CD |
| **pyarrow** | Parquet format |

---

## 📊 Calculated KPIs

| Indicator | Description |
|-----------|------------|
| **Total Stock** | Head count by year, department, and category |
| **YoY Variation** | Year-over-year for stock, slaughter, and prices |
| **Extraction Rate** | Slaughter / Stock |
| **Calf/Steer Ratio** | Cattle cycle indicator |
| **% Females in Slaughter** | Alert for breeding stock liquidation |
| **Annual Precipitation** | With anomaly vs historical average |
| **Hydric Condition** | Dry / Normal / Wet by department |

---

## 🌾 Domain: San Luis Livestock Sector

San Luis has two main productive profiles:

| Zone | Departments | Activity |
|------|------------|----------|
| **North** | Ayacucho, Belgrano, San Martín, Junín | Extensive cattle breeding |
| **South** | Dupuy, Pedernera, Pringles | Mixed cattle + agriculture |
| **Center** | Chacabuco, Pueyrredón | Mixed |

**9 departments · ~60 fictitious establishments · 7 bovine categories · 5 years of data (2020–2024)**

### Bovine Categories (SENASA)
Calf (M), Calf (F), Steer, Heifer, Bull, Cow, Ox

### Reference Sources
Synthetic data is calibrated with public statistics from:
- **SENASA** (stock, movements, slaughter)
- **IPCVA** (prices, exports)
- **MAGyP** (agricultural estimates)
- **SMN** (climate data)

---

## 📝 License

Study project. Synthetic data, no real producer information.

---

*"The bovine stock of San Luis reached 1,295,755 head, with a year-over-year variation of +11.0%."* — 2024 Report
