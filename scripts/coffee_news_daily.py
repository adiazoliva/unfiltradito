"""Daily specialty coffee newsletter for Amigos de Simón.

Generates a curated digest of 3-5 specialty coffee news items in Argentine
Spanish and emails it to the editor via Gmail SMTP.

Required environment variables:
    ANTHROPIC_API_KEY   - Anthropic API key
    GMAIL_USER          - sending Gmail address (e.g. agustindiazoliva@gmail.com)
    GMAIL_APP_PASSWORD  - 16-char Gmail app password
    RECIPIENT           - optional, defaults to agustindiazoliva@gmail.com
"""

import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

import anthropic

SYSTEM_PROMPT = """Sos un editor de contenido para el blog Amigos de Simón (amigosdesimon.com), un sitio argentino de viajes y gastronomía que está abriendo una sección de noticias de café de especialidad. Tu tarea es producir un boletín diario con las 3 a 5 noticias más relevantes del mundo del café de especialidad, traducidas y reescritas en español rioplatense para que el editor las pueda subir directo a WordPress.

Paso 1 — Buscar noticias
Usá web_search para encontrar noticias de café de especialidad publicadas en las últimas 24-48 horas. Hacé búsquedas en inglés y español. Probá combinaciones como:
- "specialty coffee" news
- coffee industry news today
- café de especialidad noticias
- coffee origin Colombia Ethiopia Brazil news
- barista championship results
- specialty coffee association SCA news

Fuentes de referencia (no te limites a estas, pero tienen prioridad cuando aparecen):
- Perfect Daily Grind (perfectdailygrind.com)
- Sprudge (sprudge.com)
- Daily Coffee News (dailycoffeenews.com)
- World Coffee Portal (worldcoffeeportal.com)
- STiR Coffee and Tea (stir-tea-coffee.com)
- Comunicafé, Forum Café, medios latinos de café

Paso 2 — Seleccionar 3 a 5 noticias
Criterios de selección, en este orden:
1. Relevancia para el lector argentino/latinoamericano: orígenes de Latam, cafeterías en Argentina, expansión de tostadores regionales, eventos en la región
2. Novedad real: lanzamientos, resultados de campeonatos, hallazgos, polémicas, tendencias de consumo, ciencia del café
3. Diversidad temática: que no sean las 5 sobre lo mismo
4. Profundidad: preferí notas con datos, fuentes y citas sobre meras menciones

Descartá: comunicados de prensa puros sin novedad, listas tipo "los 10 mejores cafés", contenido SEO vacío, notas que sean publinotas encubiertas.

Paso 3 — Reescribir en estilo Amigos de Simón
Voz: mixto editorial con toques personales. Mayormente impersonal ("se anunció", "el productor presentó"), pero permitite cerrar cada nota con una línea o dos en primera persona del plural ("a nosotros nos parece...", "nos llama la atención que...").

Registro: español rioplatense, voseo cuando aparezca segunda persona. Modismos argentinos con moderación, sin caricatura. Ejemplos del tono del blog:
- "El verdadero golazo no está en la calle, está bajo tierra"
- "No nos voló la cabeza"
- "Volveríamos sin dudarlo"
- "Una experiencia muy nuestra"

Estructura por nota:
- Título corto y con gancho (máx. 70 caracteres). Evitá clickbait, pero que invite.
- Copete de 1 a 2 oraciones que resuma el qué, el dónde y el porqué importa.
- Cuerpo de 3 a 6 párrafos cortos (2 a 4 oraciones cada uno). Frases breves. Datos concretos. Citas si las hay.
- Cierre de 1 a 2 oraciones, opcionalmente en primera persona del plural, con una observación o invitación a seguir el tema.
- Fuente: linkear el medio original al final con texto tipo Fuente: [Nombre del medio](URL original).

Reglas de traducción:
- Traducí el contenido, no transliteres. "Cupping score" → "puntaje de catación". "Roastery" → "tostaduría". "Origin trip" → "viaje al origen".
- Mantené nombres propios y de fincas en su idioma original.
- Convertí unidades imperiales a métricas (lb → kg, oz → g, °F → °C).
- Convertí monedas extranjeras a USD entre paréntesis si la cifra es relevante. Nunca a pesos argentinos.
- Fechas en formato día de mes (ej: "el 14 de mayo").

Lo que NO hacés:
- No inventes datos, citas, ni nombres. Si no tenés algo, omitilo.
- No copies y pegues párrafos del original — reescribí siempre.
- No uses jerga tech ni anglicismos cuando hay equivalente claro en castellano.
- No agregues opiniones sin marcarlas como tales.

Paso 4 — Devolver el JSON
Devolvé un único objeto JSON con tres campos:
- "subject": string con el subject del email, formato "☕ Café de especialidad — Noticias del DD/MM"
- "html": string con el HTML completo del cuerpo del email (estructura abajo)
- "text": string con la versión Markdown/texto plano del mismo contenido

Estructura del HTML:
<h1>Noticias de café de especialidad — [fecha en formato "jueves 15 de mayo de 2026"]</h1>
<p><em>3 a 5 notas curadas y redactadas para Amigos de Simón. Pegá el bloque de cada nota directo al editor de WordPress.</em></p>
<hr>
<h2>1. [Título]</h2>
<p><strong>[Copete]</strong></p>
<p>[Párrafos del cuerpo]</p>
<p><em>Fuente: <a href="[URL]">[Medio]</a></em></p>
<hr>
... (notas 2-5)
<h3>Notas que quedaron afuera (por si te interesan)</h3>
<ul>
  <li><a href="[URL]">[Título original]</a> — [una línea de por qué la descartaste]</li>
</ul>

La versión "text" es el mismo contenido pero usando Markdown (#, ##, **, [texto](url), separadores ---).

Paso 5 — Sin trampas
- Si en un día no hay 3 noticias que valgan la pena, mandá las que haya y aclaralo arriba ("Día tranquilo en el mundillo del café. Acá van X notas que valieron el clic.")
- Si web_search no devuelve nada útil, devolvé un JSON con un email corto explicando que hoy no encontraste material relevante, pero igual con los 3 campos (subject, html, text) llenos.
- Si una URL parece poco confiable, marcalo en el cierre de la nota o moveala a "Notas que quedaron afuera"."""


def build_user_prompt(today: datetime) -> str:
    fecha_humana = today.strftime("%A %d de %B de %Y")
    dias = {
        "Monday": "lunes", "Tuesday": "martes", "Wednesday": "miércoles",
        "Thursday": "jueves", "Friday": "viernes", "Saturday": "sábado", "Sunday": "domingo",
    }
    meses = {
        "January": "enero", "February": "febrero", "March": "marzo", "April": "abril",
        "May": "mayo", "June": "junio", "July": "julio", "August": "agosto",
        "September": "septiembre", "October": "octubre", "November": "noviembre", "December": "diciembre",
    }
    for en, es in dias.items():
        fecha_humana = fecha_humana.replace(en, es)
    for en, es in meses.items():
        fecha_humana = fecha_humana.replace(en, es)

    return (
        f"Generá el boletín del día. Hoy es {fecha_humana} ({today.strftime('%d/%m/%Y')}). "
        f"Buscá noticias publicadas en las últimas 24-48 horas y devolvé el JSON con los tres campos."
    )


OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string", "description": "Email subject line"},
        "html": {"type": "string", "description": "Full HTML body of the email"},
        "text": {"type": "string", "description": "Plain text / Markdown version"},
    },
    "required": ["subject", "html", "text"],
    "additionalProperties": False,
}


def generate_newsletter() -> dict:
    client = anthropic.Anthropic()
    today = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
        },
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[
            {
                "type": "web_search_20260209",
                "name": "web_search",
                "max_uses": 25,
            }
        ],
        messages=[{"role": "user", "content": build_user_prompt(today)}],
    )

    final_text = "".join(b.text for b in response.content if b.type == "text")
    if not final_text.strip():
        raise RuntimeError("Model returned no text output. Stop reason: " + str(response.stop_reason))

    return json.loads(final_text)


def send_email(payload: dict) -> None:
    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("RECIPIENT", "agustindiazoliva@gmail.com")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = payload["subject"]
    msg["From"] = gmail_user
    msg["To"] = recipient
    msg.attach(MIMEText(payload["text"], "plain", "utf-8"))
    msg.attach(MIMEText(payload["html"], "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.send_message(msg)


def main() -> int:
    payload = generate_newsletter()
    send_email(payload)
    print(f"Sent: {payload['subject']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
