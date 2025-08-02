# Guía de ejecución y prueba del proyecto

Esta sección explica paso a paso cómo poner en marcha, probar y validar la integración desde cero.

## 1. Preparación inicial (entorno)

#### 1. Clonar el repositorio en el servidor objetivo.

```sh
git clone <repo-url> voip_integration
cd voip_integration
```

#### 2. Crear y editar el archivo .env con los valores reales. 

Ejemplo:
```ini
VTIGER_URL=https://crm.albali.com/webservice.php
VTIGER_USERNAME=apiuser
VTIGER_ACCESS_KEY=CLAVE_USUARIO

WEBHOOK_SECRET=supersecreto123

DB_HOST=localhost
DB_PORT=5432
DB_NAME=voip_integration
DB_USER=voip_user
DB_PASSWORD=securepassword

MAX_RETRIES=5
```

#### 3. Instalar dependencias Python.

```sh
pip install fastapi uvicorn requests psycopg2-binary python-dotenv pydantic
```
o 

```sh
pip3 install -r requirements.txt
```

#### 4. Preparar PostgreSQL y crear esquema.
Conéctate y ejecuta (ajustar credenciales):
```sql
CREATE DATABASE voip_integration;
\c voip_integration
CREATE TABLE voip_call_buffer (
  id SERIAL PRIMARY KEY,
  call_uuid VARCHAR UNIQUE NOT NULL,
  raw_payload JSONB NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  retries INT NOT NULL DEFAULT 0,
  last_attempt TIMESTAMP,
  vtiger_call_id VARCHAR,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);
```

#### 5. Verificar que en Vtiger existen los campos personalizados en el módulo Call:

- `cf_call_uuid`, `cf_from_number`, `cf_to_number`, `cf_recording_url`, `cf_pbx_system`, `cf_duration_seconds`.

- Asegurarse que el usuario API tiene permisos de lectura/escritura sobre Calls y Contacts.


#### 6. Levantar el servicio localmente (modo prueba).
```sh
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Verificar que en `http://localhost:8000/docs` aparece la documentación de FastAPI (si está accesible).

---

## 2. Probar con una llamada simulada

#### **Paso 1: Construir payload y firma**

En shell (Linux/macOS):
```sh
CALL_PAYLOAD='{
  "call_uuid": "uuid-555",
  "from": "+34123456789",
  "to": "+34900112233",
  "direction": "inbound",
  "start_time": "2025-08-02T14:00:00Z",
  "end_time": "2025-08-02T14:02:30Z",
  "status": "completed",
  "recording_url": "https://pbx.example.com/recordings/uuid-555.mp3",
  "agent_ext": "1001",
  "pbx_system": "centralita1"
}'
```

Calcular firma HMAC (coincide con `WEBHOOK_SECRET` en `.env`):

```sh
SIGNATURE=$(python - <<'PY'
import hmac, hashlib, json, os
secret="supersecreto123"  # Debe ser idéntico a WEBHOOK_SECRET
payload=json.loads(os.environ["CALL_PAYLOAD"])
payload_bytes=json.dumps(payload).encode()
print(hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest())
PY
')
```


#### **Paso 2: Enviar el webhook simulado**

```sh
curl -X POST http://localhost:8000/webhook/call \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$CALL_PAYLOAD"
```

**Flujo:**

**1. Recepción:** El middleware recibe el POST y valida la firma HMAC.

**2. Buffer:** Inserta el payload en `voip_call_buffer` con `status='pending'`.

**3. Resolución de contacto:** Busca en Vtiger un contacto con teléfono que coincida.

**4. Autenticación:** Hace `getchallenge` + `login` contra Vtiger.

**5. Creación o actualización:** Inserta un `Call` en Vtiger con todos los campos, incluyendo `cf_call_uuid`.

**6. Respuesta:** Devuelve JSON con `status: ok` y datos de la API de Vtiger.

**7. Buffer actualizado:** En la DB local, el buffer pasa a `status='sent'` con `vtiger_call_id`.

#### **Paso 3: Verificar resultados**

- **En la base de datos local:**
```sql
SELECT call_uuid, status, vtiger_call_id FROM voip_call_buffer WHERE call_uuid='uuid-555';
```

Debe mostrar `status = sent` y un `vtiger_call_id` no nulo.

- **En Vtiger CRM:**

    - Buscar el registro de llamada (Call) con `cf_call_uuid = 'uuid-555'`.

    - Verificar que:

        - `subject` está acorde ("Llamada entrante de +34123456789").

        - Está vinculado al contacto si existía.

        - Aparecen los campos personalizados (`cf_recording_url`, duración, tipo).

        - `assigned_user_id` corresponde a la extensión `1001` (fallback si no existe mapeo más elaborado).

- **Logs del servicio:**
Revisar la salida de logs en consola para ver la traza: se debe haber registrado un evento `call_processed` con los datos.

--- 

## 3. Pruebas adicionales

- **Reenvío del mismo payload (idempotencia):**
Vuelve a enviar exactamente el mismo webhook. La llamada **no debe duplicarse** en Vtiger; el registro existente se debe actualizar (o dejar igual), y en el buffer no debe crearse un duplicado.

- **Payload con error en firma:**
Cambia un bit de la firma y vuelve a enviar: la respuesta debe ser `401 Unauthorized`. Verificar que no se inserta nada en el buffer.

- **Llamada sin contacto asociado:**
Usa un número que no esté en Vtiger; verificar que el Call se crea sin `parent_id` y se puede revisar manualmente desde CRM.

- **Simulación de fallo en Vtiger (por ejemplo, credenciales incorrectas):**
Cambia temporalmente `VTIGER_ACCESS_KEY` a incorrecta y envía un webhook. Debe caer en el bloque de error, el buffer debe quedar en `status='failed'` y verse el incremento en `retries`.

---
