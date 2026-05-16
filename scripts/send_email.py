"""Send the coffee newsletter email via Gmail SMTP.

Reads a JSON payload from the path given as argv[1] and sends it as a
multipart text/html email to the configured recipient.

Required environment variables:
    GMAIL_USER          - sending Gmail address
    GMAIL_APP_PASSWORD  - 16-char Gmail app password
    RECIPIENT           - optional, defaults to agustindiazoliva@gmail.com

Expected JSON shape: {"subject": "...", "html": "...", "text": "..."}
"""

import json
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def main(payload_path: str) -> int:
    with open(payload_path, encoding="utf-8") as f:
        payload = json.load(f)

    for field in ("subject", "html", "text"):
        if not payload.get(field):
            raise ValueError(f"Payload is missing or empty field: {field}")

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

    print(f"Sent: {payload['subject']}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: send_email.py <payload.json>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
