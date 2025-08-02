import requests
import csv
import hashlib
import argparse
from datetime import datetime, date
from dateutil import tz
import time
import sys
import logging

# -------- CONFIGURAR AQUI ----------
VTIGER_URL = "https://crm.albali.com/webservice.php"
USERNAME = "usuario_api"
ACCESS_KEY = "access_key"
MAX_LEADS_POR_DIA = 25
# ------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


def get_challenge():
    params = {"operation": "getchallenge", "username": USERNAME}
    r = requests.get(VTIGER_URL, params=params)
    r.raise_for_status()
    data = r.json()
    if data.get("success"):
        return data["result"]["challenge"]
    else:
        raise RuntimeError(f"Error obteniendo challenge: {data}")


def login():
    challenge = get_challenge()
    key = hashlib.md5((challenge + ACCESS_KEY).encode("utf-8")).hexdigest()
    payload = {
        "operation": "login",
        "username": USERNAME,
        "accessKey": key
    }
    r = requests.post(VTIGER_URL, data=payload)
    r.raise_for_status()
    data = r.json()
    if data.get("success"):
        sessionName = data["result"]["sessionName"]
        userId = data["result"]["userId"]
        logging.info("Login exitoso como %s (id=%s)", USERNAME, userId)
        return sessionName
    else:
        raise RuntimeError(f"Login fallido: {data}")


def vtiger_query(session, query):
    params = {
        "operation": "query",
        "sessionName": session,
        "query": query + " ;"  # vtiger exige punto y coma
    }
    r = requests.get(VTIGER_URL, params=params)
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(f"Query fallida: {data}")
    return data["result"]  # lista de registros


def lookup_email_or_phone(session, value, typ="email", modules=None):
    """
    Usa endpoint /lookup?type=email/phone para buscar duplicados.
    Si modules es lista se restringe, e.g. ['Leads']
    """
    # Según documentación moderna de REST API (lookup) se usa path /lookup
    # Como fallback si no está expuesto, se puede usar query con WHERE email/phone.
    params = {
        "operation": "lookup",
        "sessionName": session,
        "type": typ,
        "value": value,
    }
    if modules:
        # buscar en módulos concretos
        params["searchIn"] = str(modules)  # vtiger espera array-like
    r = requests.get(VTIGER_URL, params=params)
    if r.status_code != 200:
        return []
    data = r.json()
    if data.get("success") and data.get("result"):
        return data["result"]
    return []


def create_record(session, module, data):
    payload = {
        "operation": "create",
        "sessionName": session,
        "element": str(data).replace("'", '"'),  # vtiger acepta JSON con comillas dobles
        "elementType": module
    }
    r = requests.post(VTIGER_URL, data=payload)
    r.raise_for_status()
    data_resp = r.json()
    if not data_resp.get("success"):
        raise RuntimeError(f"Creación de {module} fallida: {data_resp}")
    return data_resp["result"]  # contiene id, assigned_user_id, etc.


def get_asesores_activos(session):
    # Obtener usuarios activos (status=Active y no eliminados)
    q = "SELECT id, user_name FROM Users WHERE status='Active' AND deleted=0"
    rows = vtiger_query(session, q)
    # map de id a nombre
    return {r["id"]: r["user_name"] for r in rows}


def contar_leads_hoy_por_asesor(session):
    """
    Cuenta leads creados hoy por cada smownerid (assigned user)
    """
    hoy = date.today().strftime("%Y-%m-%d")
    # vtiger almacena createdtime como yyyy-mm-dd hh:ii:ss
    q = (
        "SELECT smownerid, COUNT(*) AS cnt FROM vtiger_crmentity "
        "WHERE deleted=0 AND setype='Leads' AND DATE(createdtime) = '{0}' "
        "GROUP BY smownerid"
    ).format(hoy)
    rows = vtiger_query(session, q)
    result = {}
    for r in rows:
        result[r["smownerid"]] = int(r["cnt"])
    return result  # {user_id: count}


def repartir_leads(session, csv_path, dry_run=True):
    asesores = get_asesores_activos(session)
    if not asesores:
        logging.error("No se encontraron asesores activos.")
        return []

    leads_por_asesor = contar_leads_hoy_por_asesor(session)
    capacidad = {}
    for uid in asesores:
        usados = leads_por_asesor.get(uid, 0)
        capacidad[uid] = max(0, MAX_LEADS_POR_DIA - usados)
    logging.info("Capacidades iniciales (restantes hoy) por asesor: %s", capacidad)

    asignaciones = []  # lista de dicts con lead + asignado
    usado_keys = set()  # (email.lower(), phone) para dedup en batch

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lead = {
                "nombre": row.get("Nombre"),
                "email": (row.get("Email")).strip(),
                "telefono": (row.get("Teléfono")).strip(),
                "curso": row.get("Curso Interesado"),
                "entrada" : row.get("Fecha entrada"),
                "origen": row.get("Origen del leads", ""),
            }
            key = (lead["email"].lower(), lead["telefono"])
            if key in usado_keys:
                logging.info("Saltando duplicado en CSV: %s / %s", lead["email"], lead["telefono"])
                continue

            # Verificar duplicado en VTiger por email o teléfono
            existe = False
            if lead["email"]:
                res = lookup_email_or_phone(session, lead["email"], typ="email", modules=["Leads"])
                if res:
                    logging.info("Lead con email ya existe, se omite: %s", lead["email"])
                    existe = True
            if not existe and lead["telefono"]:
                res = lookup_email_or_phone(session, lead["telefono"], typ="phone", modules=["Leads"])
                if res:
                    logging.info("Lead con teléfono ya existe, se omite: %s", lead["telefono"])
                    existe = True
            if existe:
                continue

            # elegir asesor con más capacidad restante
            candidatos = sorted(
                [(uid, capacidad[uid]) for uid in capacidad if capacidad[uid] > 0],
                key=lambda x: (-x[1], x[0])
            )
            if not candidatos:
                logging.warning("Se agotó la capacidad diaria: no quedan asesores con espacio.")
                break
            asesor_id, restante = candidatos[0]
            asignaciones.append({"lead": lead, "asesor_id": asesor_id})
            capacidad[asesor_id] -= 1
            usado_keys.add(key)
            logging.info("Asignado lead %s/%s a asesor %s (queda %d)", lead["email"], lead["phone"], asesor_id, capacidad[asesor_id])

    resultados = []
    for item in asignaciones:
        lead = item["lead"]
        asesor_id = item["asesor_id"]
        if dry_run:
            resultados.append({
                **lead,
                "assigned_to": asesor_id,
                "assigned_to_name": asesores[asesor_id],
                "leadid": None,
                "status": "planned"
            })
            continue

        # montar payload para crear lead con assigned_user_id
        element = {
            "nombre": lead["nombre"],
            "curso": lead["curso"],
            "email": lead["email"],
            "telefono": lead["telefono"],
            "assigned_user_id": asesor_id,
            "origen": lead["origen"],
        }
        try:
            created = create_record(session, "Leads", element)
            resultados.append({
                **lead,
                "assigned_to": asesor_id,
                "assigned_to_name": asesores[asesor_id],
                "leadid": created.get("id"),
                "status": "created"
            })
            logging.info("Lead creado: %s -> %s (ID: %s)", lead["email"], asesores[asesor_id], created.get("id"))
        except Exception as e:
            logging.error("Error creando lead %s: %s", lead["email"], str(e))
            resultados.append({
                **lead,
                "assigned_to": asesor_id,
                "assigned_to_name": asesores[asesor_id],
                "leadid": None,
                "status": f"error: {e}"
            })

    return resultados


def escribir_csv(resultados, salida):
    campos = ["Nombre", "Email", "Teléfono", "Curso Interesado", "AssignedToID", "AssignedToName", "LeadID", "Status"]
    with open(salida, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(campos)
        for r in resultados:
            writer.writerow([
                r.get("nombre", ""),
                r.get("email", ""),
                r.get("telefono", ""),
                r.get("curso", ""),
                r.get("assigned_to", ""),
                r.get("assigned_to_name", ""),
                r.get("leadid", ""),
                r.get("status", ""),
            ])
    logging.info("Se escribió CSV de salida en %s", salida)


def main():
    parser = argparse.ArgumentParser(description="Distribución de leads usando API VTiger 8.1")
    parser.add_argument("csv", help="Archivo CSV de entrada con leads")
    parser.add_argument("--apply", action="store_true", help="Crear realmente los leads (sin esto es dry-run)")
    parser.add_argument("--output", default="output.csv", help="CSV de resultados")
    args = parser.parse_args()

    session = login()
    resultados = repartir_leads(session, args.csv, dry_run=not args.apply)
    escribir_csv(resultados, args.output)
    # resumen
    creados = [r for r in resultados if r["status"] == "created"]
    planificados = [r for r in resultados if r["status"] == "planned"]
    logging.info("Resumen: %d creados, %d planeados/omitidos.", len(creados), len(planificados))


if __name__ == "__main__":
    main()
