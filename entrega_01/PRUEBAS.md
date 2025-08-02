# Guía de pruebas automatizadas con pytest

## Requisitos

Antes de ejecutar las pruebas necesitas:

- Python 3.8+  
- Las dependencias del proyecto:  
  
  ```bash
  pip install requests python-dateutil pytest
  ```

El script de pruebas mokea las llamadas HTTP a la API de VTiger, por lo que no se requiere un servidor VTiger real para las pruebas unitarias básicas.

---

## Estructura esperada

La estructura mínima del proyecto para ejecutar correctamente las pruebas es la siguiente:

/proyecto/
├── distribuir_leads_api_vtiger.py # Script principal de distribución de leads
├── test_distribuir_leads_api_vtiger.py # Script de pruebas unitarias con pytest
├── PRUEBAS.md # Guía de pruebas en formato Markdown
├── Documentacion_Distribuidor_Leads.md # Documentación técnica del script
└── leads.csv # (Opcional) CSV de ejemplo para pruebas manuales

**Notas:**

- Todos los archivos `.py` deben estar en la misma carpeta o en el `PYTHONPATH`.  
- Si organizas el proyecto en un paquete, puedes crear un subdirectorio `src/` y ajustar los `import` en los tests.  
- El CSV de ejemplo no es requerido para los tests automáticos porque los tests crean sus propios archivos temporales.  

---

## Ejecutar las pruebas

1. Desde la terminal, en la carpeta del proyecto:

   ```bash
   pytest -v
   ```

2. Verás salida detallada de los casos de prueba. Ejemplo de tests incluidos:

- test_dry_run_assigns_equally: comprueba que en modo simulación se distribuyen los leads sin crearlos.

- test_skip_duplicate_in_csv: se salta leads duplicados dentro del CSV.

- test_skip_existing_in_vtiger: se omiten leads que ya existen en VTiger por email.

- test_capacity_limit: no asigna cuando todos los asesores están al tope.

- test_real_creation_creates_leads_and_writes_csv: simula la creación real y genera el CSV de salida.

---

## Ver solo fallos

Si quieres ver únicamente los test fallidos y resúmenes:

```bash
pytest -q
```

---

## Forzar recolección y ver cobertura (opcional)

Si tienes instalado `pytest-cov` puedes ejecutar:

```bash
pip install pytest-cov
pytest --cov=distribuir_leads_api_vtiger -v
```

Eso muestra qué parte del código está cubierta por las pruebas.

---

## Recomendaciones

- Ejecuta siempre los tests antes de desplegar un cambio.

- Si modificas lógica de asignación o deduplicación, agrega nuevos tests para cubrir casos límite.

- Puedes integrar esto en CI (GitHub Actions, GitLab CI, etc.) usando el comando `pytest`.

---

## Ejecución individual de un test

Para ejecutar un test específico:

```bash
pytest -v test_distribuir_leads_api_vtiger.py::test_skip_duplicate_in_csv
```
