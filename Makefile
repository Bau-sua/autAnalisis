.PHONY: help generar limpiar test notebook sync

help:  ## Mostrar esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

sync:  ## Sincronizar dependencias con uv
	uv sync

generar:  ## Generar datos sintéticos en data/raw/
	uv run python src/generacion/generar_datos.py

limpiar:  ## Eliminar datos generados
	rm -f data/raw/*.csv data/raw/*.xlsx data/clean/*.parquet data/processed/*.parquet

test:  ## Ejecutar tests
	uv run pytest tests/ -v

notebook:  ## Iniciar Jupyter Lab en notebooks/
	uv run jupyter lab notebooks/

etl:  ## Ejecutar pipeline ETL (limpieza + transformación)
	uv run python src/etl/limpiar.py

kpis:  ## Calcular KPIs e indicadores compuestos
	uv run python src/analisis/kpis.py
	uv run python src/etl/limpiar.py

reporte:  ## Generar informe anual (default: 2024)
	uv run python src/reporte/generar_reporte.py --tipo anual --año $${AÑO:-2024}
	uv run python src/reporte/generar_reporte.py

dashboard:  ## Iniciar dashboard Streamlit
	uv run streamlit run dashboard/app.py
	uv run streamlit run dashboard/app.py
