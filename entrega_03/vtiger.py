
# aqui podemos dejar la logica de conexion a VTiger
# para el prototipo de bot, tenemos datos dummy


leads = [
  {
    "Nombre": "Carlos Pérez",
    "Email": "carlos@email.com",
    "Teléfono": "600000001",
    "Curso Interesado": "Electricidad",
    "Fecha entrada": "28/07/2025",
    "Origen del leads": "Google_ads"
  },
  {
    "Nombre": "Lucía Gómez",
    "Email": "lucia@email.com",
    "Teléfono": "600000002",
    "Curso Interesado": "Hostelería",
    "Fecha entrada": "28/07/2025",
    "Origen del leads": "Facebook_ads"
  },
  {
    "Nombre": "Antonio Ruiz",
    "Email": "antonio@email.com",
    "Teléfono": "600000003",
    "Curso Interesado": "Salud",
    "Fecha entrada": "28/07/2025",
    "Origen del leads": "Telefono"
  },
  {
    "Nombre": "Sara López",
    "Email": "sara@email.com",
    "Teléfono": "600000004",
    "Curso Interesado": "Electricidad",
    "Fecha entrada": "28/07/2025",
    "Origen del leads": "Referido"
  },
  {
    "Nombre": "Javier Torres",
    "Email": "javier@email.com",
    "Teléfono": "600000005",
    "Curso Interesado": "Hostelería",
    "Fecha entrada": "28/07/2025",
    "Origen del leads": "SEO"
  },
  {
    "Nombre": "Ana Sánchez",
    "Email": "ana@email.com",
    "Teléfono": "600000006",
    "Curso Interesado": "Electricidad",
    "Fecha entrada": "28/07/2025",
    "Origen del leads": "Portales"
  },
  {
    "Nombre": "Pedro Morales",
    "Email": "pedro@email.com",
    "Teléfono": "600000007",
    "Curso Interesado": "Salud",
    "Fecha entrada": "28/07/2025",
    "Origen del leads": "TikTok_ads"
  },
  {
    "Nombre": "Elena Ortega",
    "Email": "elena@email.com",
    "Teléfono": "600000008",
    "Curso Interesado": "Hostelería",
    "Fecha entrada": "28/07/2025",
    "Origen del leads": "Otros"
  },
  {
    "Nombre": "Raúl Díaz",
    "Email": "raul@email.com",
    "Teléfono": "600000009",
    "Curso Interesado": "Electricidad",
    "Fecha entrada": "28/07/2025",
    "Origen del leads": "LinkedIn_ads"
  },
  {
    "Nombre": "Marta Navarro",
    "Email": "marta@email.com",
    "Teléfono": "600000010",
    "Curso Interesado": "Salud",
    "Fecha entrada": "28/07/2025",
    "Origen del leads": "Emailing"
  }
]

cursos_disponibles = [
  {"curso": "Salud",
   "inicio" : "02/10/2025",
    "precio" : "200€"
  },
  {"curso": "Electricidad",
   "inicio" : "10/10/2025",
    "precio" : "300€"
  },
  {"curso": "Hostelería",
   "inicio" : "19/10/2025",
    "precio" : "240€"
  },
]



def get_leads_data(lead_data):
    for lead in leads:
        if lead_data in list(lead.values()):
            return lead
    return None


def get_cursos_disponibles():
    cursos = [c.get("curso") for c in cursos_disponibles]
    return cursos

def get_precio_curso(curso):
    for c in cursos_disponibles:
        if c.get("curso") == curso:
            return c.get("precio")
    return None
