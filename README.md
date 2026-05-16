# Unfiltradito — Boletín diario de café de especialidad

Routine que arma todos los días un boletín de noticias de café de especialidad en estilo Amigos de Simón y lo envía por mail. **Usa tu suscripción a Claude MAX vía OAuth — no hay costo de API.**

## Cómo funciona

1. GitHub Actions corre `.github/workflows/coffee-news-daily.yml` todos los días a las 8:03 AM Argentina (11:03 UTC). Puede demorarse 5-10 min en horarios pico — eso es normal en GH Actions.
2. La action oficial `anthropics/claude-code-action@v1` ejecuta Claude Code autenticado con tu cuenta MAX:
   - Buscá noticias en la web (últimas 24-48 hs)
   - Selecciona 3-5, las redacta en español rioplatense
   - Escribe el resultado a `./email.json` (subject + html + text)
3. El step siguiente corre `scripts/send_email.py` que lee el JSON y envía el mail vía SMTP de Gmail.

## Setup (una sola vez)

### 1. Generar el OAuth token de Claude (necesita una compu)

Desde una computadora donde tengas (o instales) [Claude Code](https://claude.com/code):

```bash
# Si todavía no tenés Claude Code instalado:
npm install -g @anthropic-ai/claude-code

# Si nunca te logueaste:
claude login
# (te abre el browser, autorizás con tu cuenta MAX)

# Generar el token largo:
claude setup-token
# (te muestra una URL para autorizar y devuelve un token largo `sk-ant-oat...`)
```

Copiá el token. Es de larga duración pero conviene rotarlo cada tanto si te preocupa la seguridad.

### 2. Generar app password de Gmail

1. Activá la verificación en 2 pasos en https://myaccount.google.com/security
2. Andá a https://myaccount.google.com/apppasswords
3. Creá una app password (16 caracteres, sin espacios).

### 3. Cargar 3 secrets en GitHub

En el repo: Settings → Secrets and variables → Actions → New repository secret. Cargá:

| Nombre | Valor |
|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | El token `sk-ant-oat...` del paso 1 |
| `GMAIL_USER` | `agustindiazoliva@gmail.com` |
| `GMAIL_APP_PASSWORD` | El app password de 16 caracteres |

### 4. Probar manualmente

En el tab Actions del repo, elegí el workflow "Boletín diario de café de especialidad" y dale "Run workflow". Si todo está bien configurado, en menos de 5 min tenés el mail en la bandeja.

## Cambiar el destinatario

Por defecto va a `agustindiazoliva@gmail.com`. Para cambiarlo, editá `RECIPIENT` directamente en `scripts/send_email.py` o agregalo como env var en el step "Enviar email" del workflow.

## Costos

**Cero costo de API** — el trabajo de Claude se carga contra tu plan MAX. Lo único que podría costarte es uso intenso de Gmail SMTP, pero para 1 mail/día estás muy lejos de cualquier límite.
