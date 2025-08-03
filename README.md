## 1. Reparto automático de leads EN crm VTIGER VERSIÓN 8.1
Diseñe un script que lea un archivo CSV y reparta equitativamente los leads entre asesores disponibles, evitando duplicados y respetando un máximo de 25 leads/día por asesor.

**Estructura de la entrega:**

```arduino
entrega_01/
├── distribuir_leads_vtiger.py
├── leads_ejemplo_albali.csv
├── pruebas.md
├── readme.md
├── requirements.txt
├── test_distribuir_leads_vtiger.py
```

- el fichero `distribuir_leads_vtiger.py` permite leer un fichero `.csv` y extraer los datos de los leads
- el script se conecta vtiger mediante la API web
- reparte los leads entre los asesores

- el fichero readme.md contiene le documentaciòn tecnica

- el fichero `test_distribuir_leads_vtiger.py` permite ejecutar pruebas unitarias mediante **pytest**
- el fichero `pruebas.md` documenta la ejecución de pruebas

---


## 2. Integración con centralita
Proponga una estructura técnica para registrar llamadas de una centralita VoIP en el CRM Vtiger. Incluya esquema, flujo o ejemplo de llamada API.

**Estructura de la entrega:**

```arduino
entrega_02/
├── guia_ejecucion.md
├── readme.md
├── voip_integration/
    ├── main.py
    ├── vtiger_client.py
    ├── db.py
    ├── config.py
    ├── security.py
    ├── models.py
    ├── utils.py
    ├── requirements.txt
```

- el fichero `readme.md` contiene la documentación tecnica
- el fichero `guia_ejecucion.md` tiene explicaciones para la ejecuciòn del script
- la carpeta `voip_integration` contiene los ficheros necesarios para la ejecucion del script


---


## 3. Chatbot IA con ChatGPT
Proponga cómo implementaría un chatbot que interactúe con leads según su estado en el CRM. Incluya ejemplos de mensajes, estructura JSON o flujo de automatización.

**Estructura de la entrega:**

```arduino
entrega_03/
├── chatbot.py.py
├── chatlogic.py.py
├── readme.md
├── requirements.txt
├── video_demo_chatbot.mkv
├── vtiger.py
```

- el fichero `readme.md` describe una solucion tecnica y como ejecutar el chatbot prototipo
- el fichero `chatbot.py` permite arrancar el chatbot

- el video `video_demo_chatbot.mkv` muestra une ejecución del prototipo, con un usuario interactuando con el chatbot