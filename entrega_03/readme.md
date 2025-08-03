# ChatBot CRM

## 1. Visión general mínima viable

Un visitante de la web (lead) chatea con un bot; el bot identifica al lead (por email, cookie o primer dato que dé), consulta su ficha en Vtiger para ver su estado y contexto, genera una respuesta adecuada vía OpenRouter y la muestra en la interfaz web. Si se detecta interés fuerte o caso especial, escala a un asesor humano.

Componentes:

**1. Widget de chat en la web** (JavaScript ligero).

**2. Backend Python** (ej. FastAPI):

- Consulta Vtiger CRM para obtener/crear lead.

- Construye prompt según estado.

- Llama a OpenRouter para obtener respuesta.

- Retorna la respuesta al front.

- Opcional: registra la conversación como nota/tarea en Vtiger.

**3. OpenAI o OpenRouter API:** generación de texto.

**4. Vtiger API v8.1:** lectura y actualización de lead.

---

## 2. Flujo básico

**1.** Usuario abre chat en la web.

**2.** Bot pregunta, por ejemplo: “¿Cómo te llamas y qué formación te interesa?”

**3.** Se captura email/nombre/curso de interés.

**4.** Backend busca en Vtiger lead por email; si no existe, lo crea con estado “Nuevo”.

**5.** Se obtiene el status y campos relevantes (curso de interés, último contacto, etc.).

**6.** Se arma un prompt contextualizado (según estado).

**7.** Se llama a la API del LLM, se recibe texto.

**8.** Se muestra al visitante y se guarda interacción en Vtiger (nota y/o actualización de “última interacción”).

**9.** Si se detecta trigger de escalado (ej. “quiero inscribirme”, “hablar con asesor”), se marca y notifica al asesor.

--- 

## 3. Estados mínimos y lógica sencilla

Ejemplo de mapeo reducido:

| Estado Vtiger	| Qué hace el bot |
|---------------|----------------------------------------------------------------------------------|
|Nuevo |	Da bienvenida, pregunta interés, sugiere cursos disponibles. |
|Interesado |	Ofrece detalles (fechas, precios), pregunta si quiere agendar llamada/demo. |
|Inscrito |	Da información logística (inicio, materiales, recordatorios). |
|Inactivo |	Reengage con mensaje tipo “¿sigues interesado? Tenemos próximas fechas y descuentos.” |


Reglas simples, por ejemplo:

   -  Si el lead menciona “precio”, “inscribirme” o “empezar”, sugerir acción concreta y marcar como “fuerte interés”.

   - Si no responde tras X intercambios, recomendar escalado o enviar opción de dejar correo para seguimiento.


## 4. Escalado simple

Detectar en la respuesta del lead (puedes hacer un paso extra de análisis de intención con palabras clave) 

términos como:
- “Quiero inscribirme”

- “Hablar con un asesor”

- “Precio final”
    
Si se detectan, el backend:

- Cambia un campo del lead en Vtiger a algo como Necesita asesor

- Crea una tarea para un asesor

- Opcional: notifica por email/Slack al equipo


## 5. Persistencia y seguimiento

- Registrar cada intercambio como nota en la ficha del lead.

- Guardar timestamp y “tipo de interacción” (bot, escalado, confirmación).

- Mantener en sesión (cookie/localStorage) identificación mínima para relacionar visitas con lead.


## 6. Seguridad y consideraciones mínimas

- Validar y sanitizar lo que viene del front (evitar inyección en prompts).

- No exponer claves en cliente.

- Limitar frecuencia de mensajes por lead (rate limit básico).

- Gestionar consentimiento: hacer visible aviso de privacidad / opt-in antes de recabar email.


## 7. Prototipo

El código python entregado es una prototipo de chatbot para ilustrar el funcionamiento descrito anteriormente.

**1. Ejecución**

   - Es necesario instalar los módulos python requeridos
   ```sh
   pip install -r requirements.txt
   ```


   - Renombrar el fichero `env_file.txt` en fichero `.env`

   - Es necesario editar el fichero `.env` para introducir el valor de la Key de acceso a la API OpenRouter (se puede utilizar OpenAI)

   ```conf
   # OPENROUTER LLM API
   OPENROUTER_API_KEY=OpenRouteur_api_key
   ```

   - se puede ejecutar el fichero `chatbot.py`

   - el programa arranca un servidor local disponible en `http://localhost:5006`. El navegador debería abrirse automáticamente

**2. Diálogo con el chatbot**

   - el chatbot puedo contestar a cualquier pregunta como un chatbot normal
   - si el chatbot detecta ciertas preguntas, llama a funciones propias para recuperar datos de VTiger (mockeado)
   - el prototipo tiene 3 funciones de ejemplos:
      - recuperar datos del usuario, en función de su nombre, email o número de teléfono.
      - recuperar lista de cursos disponibles
      - recuperar precio de un curso en particular

**3. Video de demo**

El video muestra una interacción básica de un usuario con el chatbot.
- pregunta por cursos
- pregunta por el precio de un curso
- indica su nombre y el chatbot le indica en que curso está interesado.
- el usuario pide matricularse a ese curso

