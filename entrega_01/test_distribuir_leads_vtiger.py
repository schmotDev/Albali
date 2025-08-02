import csv
import os
import pytest
from pathlib import Path
import builtins

# Se asume que el script original está en el mismo directorio o en el PYTHONPATH
import distribuir_leads_vtiger as dl

# --- Helpers de mocking ---

class DummyResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception(f"HTTP {self.status_code}")

@pytest.fixture(autouse=True)
def patch_requests(monkeypatch):
    """
    Intercepta requests.get y requests.post usadas en login/query/create.
    Se delega el comportamiento a funciones reemplazadas durante cada test.
    """
    # Default fallback, individual tests pueden sobreescribir estos dicts
    state = {
        "challenge": "fakechallenge",
        "sessionName": "fakesession",
        "users": [
            {"id": "19x1", "user_name": "asesor.uno"},
            {"id": "20x1", "user_name": "asesor.dos"},
        ],
        "leads_count_today": [],  # para contar_leads_hoy_por_asesor
        "lookup_email": [],
        "lookup_phone": [],
        "created_leads": [],
    }

    def fake_get(url, params=None, **kwargs):
        op = params.get("operation")
        if op == "getchallenge":
            return DummyResponse({"success": True, "result": {"challenge": state["challenge"]}})
        elif op == "query":
            q = params.get("query", "")
            # Usuarios activos
            if "FROM Users" in q:
                return DummyResponse({"success": True, "result": state["users"]})
            # Leads hoy por asesor
            if "FROM vtiger_crmentity" in q and "setype='Leads'" in q:
                # Devuelve filas con smownerid y cnt
                return DummyResponse({"success": True, "result": state["leads_count_today"]})
            # Fallback
            return DummyResponse({"success": True, "result": []})
        elif op == "lookup":
            typ = params.get("type")
            val = params.get("value", "")
            if typ == "email" and val.lower() in [e.lower() for e in state["lookup_email"]]:
                return DummyResponse({"success": True, "result": [{"id": "dummy_existing_email"}]})
            if typ == "phone" and val in state["lookup_phone"]:
                return DummyResponse({"success": True, "result": [{"id": "dummy_existing_phone"}]})
            return DummyResponse({"success": True, "result": []})
        else:
            return DummyResponse({"success": False, "error": "unknown operation"}, status_code=400)

    def fake_post(url, data=None, **kwargs):
        op = data.get("operation")
        if op == "login":
            return DummyResponse({"success": True, "result": {"sessionName": state["sessionName"], "userId": "19x1"}})
        if op == "create":
            element = data.get("element", "{}")
            assigned_to = "created-id-" + str(len(state["created_leads"]) + 1)
            # Simular que se crea y devolver id
            result = {"id": assigned_to}
            state["created_leads"].append((element, assigned_to))
            return DummyResponse({"success": True, "result": result})
        return DummyResponse({"success": False, "error": "unknown operation"}, status_code=400)

    monkeypatch.setattr(dl.requests, "get", fake_get)
    monkeypatch.setattr(dl.requests, "post", fake_post)
    # Exponer el estado al test si lo quiere modificar
    return state

# --- Fixtures de CSV ---

@pytest.fixture
def sample_csv(tmp_path):
    path = tmp_path / "leads_ejemplo_albali.csv"
    content = [
        ["Nombre", "Email", "Teléfono", "Curso Interesado", "Fecha entrada", "Origen del leads"],
        ["Juan Pérez", "juan.perez@example.com", "600123456", "Salud", "28/07/2025", "Portales"],
        ["Ana Gómez", "ana.gomez@example.com", "600654321", "Electricidad", "28/07/2025", "SEO"],
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(content)
    return str(path)

@pytest.fixture
def csv_with_duplicate_in_csv(tmp_path):
    path = tmp_path / "leads_dup.csv"
    content = [
        ["Nombre", "Email", "Teléfono", "Curso Interesado", "Fecha entrada", "Origen del leads"],
        ["Juan Pérez", "juan.perez@example.com", "600123456", "Salud", "28/07/2025", "Portales"],
        ["Juan Pérez", "juan.perez@example.com", "600123456", "Salud", "28/07/2025", "SEO"],
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(content)
    return str(path)

# --- Tests ---

def test_dry_run_assigns_equally(patch_requests, sample_csv, tmp_path):
    state = patch_requests
    # No leads hoy, no duplicados
    state["leads_count_today"] = []
    session = dl.login()  # debería usar los mocks
    resultados = dl.repartir_leads(session, sample_csv, dry_run=True)
    # Debería asignar 2 leads, ambos con status planned
    assert len(resultados) == 2
    assert all(r["status"] == "planned" for r in resultados)
    # Ambos tienen assigned_to y nombre
    ids = {r["assigned_to"] for r in resultados}
    assert ids.issubset(set(state["users"][i]["id"] for i in range(len(state["users"]))))
    # No se creó ningún lead real
    assert state["created_leads"] == []

def test_skip_duplicate_in_csv(patch_requests, csv_with_duplicate_in_csv):
    state = patch_requests
    state["leads_count_today"] = []
    session = dl.login()
    resultados = dl.repartir_leads(session, csv_with_duplicate_in_csv, dry_run=True)
    # Solo uno debe procesarse porque el segundo es duplicado en el CSV
    assert len(resultados) == 1
    assert resultados[0]["status"] == "planned"

def test_skip_existing_in_vtiger(patch_requests, sample_csv):
    state = patch_requests
    # Simular que el primer email ya existe
    state["lookup_email"] = ["juan.perez@example.com"]
    state["leads_count_today"] = []
    session = dl.login()
    resultados = dl.repartir_leads(session, sample_csv, dry_run=True)
    # Uno se omite, queda solo Ana
    assert len(resultados) == 1
    assert resultados[0]["email"].lower() == "ana.gomez@example.com"
    assert resultados[0]["status"] == "planned"

def test_capacity_limit(patch_requests, sample_csv):
    state = patch_requests
    # Simular que cada asesor ya tiene 25 leads hoy para forzar límite; se asignará ninguno
    state["leads_count_today"] = [
        {"smownerid": state["users"][0]["id"], "cnt": 25},
        {"smownerid": state["users"][1]["id"], "cnt": 25},
    ]
    session = dl.login()
    resultados = dl.repartir_leads(session, sample_csv, dry_run=True)
    # No se puede asignar porque no hay capacidad
    assert len(resultados) == 0

def test_real_creation_creates_leads_and_writes_csv(patch_requests, sample_csv, tmp_path):
    state = patch_requests
    state["leads_count_today"] = []
    session = dl.login()
    output_csv = tmp_path / "out.csv"
    resultados = dl.repartir_leads(session, sample_csv, dry_run=False)
    # Se crearon dos leads
    assert len(resultados) == 2
    assert all(r["status"] == "created" for r in resultados)
    # Escribir CSV y verificar contenido
    dl.escribir_csv(resultados, str(output_csv))
    assert output_csv.exists()
    # Leer y comprobar filas (header + 2)
    with open(output_csv, newline="", encoding="utf-8") as f:
        reader = list(csv.reader(f))
    assert len(reader) == 3  # header + 2
    headers = reader[0]
    assert "AssignedToID" in headers
    assert "LeadID" in headers
