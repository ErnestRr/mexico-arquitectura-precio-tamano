```
mexico-arquitectura-precio-tamano/
├── notebooks/        00 datos y selección · 01 escalera por marca · 02 rupturas
│                     03 cadenas y formatos · 04 qué revisar · 05 visualizaciones
├── config.yaml       objetivo, preguntas y textos del README y del reporte
├── src/              entorno.py, escalera.py (escalones por tamaño), graficas.py, reporte.py
├── data/processed/   escalones por tienda, rupturas por marca, escalón y cadena (CSV) y resultados.json
├── data/metadata/    parametros.json, manifiesto_insumos.json, seleccion_marcas.csv
├── outputs/charts/   gráficas PNG (la principal también en SVG)
├── outputs/social/   versiones de 1280×720 y 1080×1350
├── docs/index.html   reporte interactivo autocontenido
├── build_notebooks.py
└── verify_project.py
```

```powershell
python -m pip install -r requirements.txt
python build_notebooks.py
$env:OMP_NUM_THREADS = 1; $env:OPENBLAS_NUM_THREADS = 1; $env:MKL_NUM_THREADS = 1
foreach ($n in Get-ChildItem notebooks/0*.ipynb) {
  python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 $n.FullName
}
python verify_project.py
```

`verify_project.py` recalcula las cifras clave solo con pandas y numpy a partir de los precios originales y comprueba que
coinciden con este README.
