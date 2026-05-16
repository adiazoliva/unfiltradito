# Unfiltradito — Boletín diario de café de especialidad

Routine que arma todos los días un boletín de noticias de café de especialidad en estilo Amigos de Simón y lo envía por mail.

## Cómo funciona

1. GitHub Actions corre `.github/workflows/coffee-news-daily.yml` todos los días a las 8:03 AM Argentina (11:03 UTC).
2. El job ejecuta `scripts/coffee_news_daily.py`:
   - Llama a Claude Opus 4.7 con web search habilitado.
   - Claude busca noticias de las últimas 24-48hs, selecciona 3-5 y las redacta en español rioplatense.
   - Devuelve un JSON estructurado con `subject`, `html` y `text`.
3. El script envía el email vía SMTP de Gmail.

## Setup (una sola vez)

### 1. Generar app password de Gmail

1. Activá la verificación en 2 pasos en https://myaccount.google.com/security
2. Andá a https://myaccount.google.com/apppasswords
3. Creá una app password (16 caracteres, sin espacios).

### 2. Cargar secrets en GitHub

En el repo: Settings → Secrets and variables → Actions → New repository secret. Cargá tres:

| Nombre | Valor |
|---|---|
| `ANTHROPIC_API_KEY` | Tu API key de Anthropic (https://console.anthropic.com) |
| `GMAIL_USER` | `agustindiazoliva@gmail.com` |
| `GMAIL_APP_PASSWORD` | El app password de 16 caracteres |

### 3. Probar manualmente

En el tab Actions del repo, elegí el workflow "Boletín diario de café de especialidad" y dale "Run workflow". Si todo está bien configurado, en menos de 2 minutos tenés el mail en la bandeja.

## Cambiar el destinatario

Por defecto va a `agustindiazoliva@gmail.com`. Para cambiarlo, agregá la env var `RECIPIENT` al workflow o seteala como secret.

## Costo estimado

~USD 0.30-0.50 por día con Opus 4.7 + prompt caching (~USD 15/mes). Para bajarlo, cambiá `model="claude-opus-4-7"` por `claude-sonnet-4-6` en `scripts/coffee_news_daily.py`.
