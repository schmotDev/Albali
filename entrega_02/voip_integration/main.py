import time
import logging
from fastapi import FastAPI, Request, HTTPException, Header
from vtiger_client import VtigerClient
from config import settings
from security import verify_hmac_signature
from db import get_conn
import json

app = FastAPI()
logger = logging.getLogger("voip_integration")
logging.basicConfig(level=logging.INFO)

def upsert_call_to_vtiger(payload: dict):
    vt = VtigerClient()
    vt.login()

    # resolver contacto por número (simple: buscar en Contacts)
    from_num = payload.get("from")
    to_num = payload.get("to")
    call_uuid = payload["call_uuid"]

    contact_id = None
    # Prioriza el número del cliente (suponiendo entrante: from es cliente)
    if from_num:
        q = f"SELECT * FROM Contacts WHERE phone LIKE '{from_num}%' LIMIT 1;"
        res = vt.query(q)
        if res.get("result"):
            contact_id = res["result"][0]["id"]
    if not contact_id and to_num:
        q = f"SELECT * FROM Contacts WHERE phone LIKE '{to_num}%' LIMIT 1;"
        res = vt.query(q)
        if res.get("result"):
            contact_id = res["result"][0]["id"]

    # Verificar si ya existe llamada con cf_call_uuid
    soql_call = f"SELECT * FROM Calls WHERE cf_call_uuid = '{call_uuid}' LIMIT 1;"
    existing = vt.query(soql_call)
    call_element = {
        "subject": f"Llamada {'entrante' if payload.get('direction')=='inbound' else 'saliente'} de {from_num or to_num}",
        "assigned_user_id": payload.get("assigned_user_id", "19x1"),  # default si no viene
        "calltype": "Inbound" if payload.get("direction") == "inbound" else "Outbound",
        "date_start": payload.get("start_time", "")[:10].replace("T", " "),
        "time_start": payload.get("start_time", "")[11:16] if payload.get("start_time") else "",
        "duration": str(payload.get("duration_seconds", 0)),
        "description": f"Grabación: {payload.get('recording_url','')}",
        "cf_call_uuid": call_uuid,
        "cf_from_number": from_num,
        "cf_to_number": to_num,
        "cf_recording_url": payload.get("recording_url", ""),
        "cf_pbx_system": payload.get("pbx_system", "default"),
        "cf_duration_seconds": payload.get("duration_seconds", 0),
        "status": "Completed" if payload.get("status") in ("completed","answered") else "Planned"
    }

    if contact_id:
        call_element["parent_id"] = contact_id

    if existing.get("result"):
        # actualizar
        existing_id = existing["result"][0]["id"]
        call_element["id"] = existing_id
        result = vt.update("Call", call_element)
    else:
        result = vt.create("Call", call_element)

    return result

@app.post("/webhook/call")
async def receive_call(request: Request, x_signature: str = Header(...)):
    body_bytes = await request.body()
    # validar HMAC
    if not verify_hmac_signature(body_bytes, x_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(body_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    call_uuid = payload.get("call_uuid")
    if not call_uuid:
        raise HTTPException(status_code=422, detail="Missing call_uuid")

    # Normalizar y calcular duración si no viene
    if "start_time" in payload and "end_time" in payload:
        fmt = "%Y-%m-%dT%H:%M:%SZ"  # esperar UTC
        try:
            from datetime import datetime
            st = datetime.strptime(payload["start_time"], fmt)
            et = datetime.strptime(payload["end_time"], fmt)
            duration = int((et - st).total_seconds())
            payload["duration_seconds"] = duration
        except Exception:
            payload["duration_seconds"] = 0

    # Insertar en buffer si nuevo
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO voip_call_buffer (call_uuid, raw_payload)
                VALUES (%s, %s)
                ON CONFLICT (call_uuid) DO NOTHING;
            """, (call_uuid, json.dumps(payload)))

    # Procesar (síncrono básico; en producción mover a cola/background job)
    try:
        result = upsert_call_to_vtiger(payload)
        # actualizar buffer
        with conn:
            with conn.cursor() as cur:
                vtiger_id = result.get("result", {}).get("id") if result.get("result") else None
                cur.execute("""
                    UPDATE voip_call_buffer
                    SET status='sent', vtiger_call_id=%s, last_attempt=now()
                    WHERE call_uuid=%s;
                """, (vtiger_id, call_uuid))
        return {"status": "ok", "vtiger": result}
    except Exception as e:
        logging.exception("Error al enviar a Vtiger")
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE voip_call_buffer
                    SET status='failed', retries = retries + 1, last_attempt=now()
                    WHERE call_uuid=%s;
                """, (call_uuid,))
        # implementar lógica de reintento en background / scheduler aparte
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
