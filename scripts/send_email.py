"""Send the coffee newsletter email via Gmail SMTP.

Reads three plain files from the directory given as argv[1] and sends them
as a multipart text/html email. Using separate plain files (instead of a
single JSON) avoids JSON-escaping errors when the model writes large HTML
bodies by hand.

Expected files in the directory:
    subject.txt   - the email subject line (first non-empty line is used)
    body.html     - the HTML body
    body.md       - the plain-text / Markdown body

Required environment variables:
    GMAIL_USER          - sending Gmail address
    GMAIL_APP_PASSWORD  - 16-char Gmail app password
    RECIPIENT           - optional, defaults to agustindiazoliva@gmail.com
"""

import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def read_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def main(out_dir: str) -> int:
    subject = read_file(os.path.join(out_dir, "subject.txt")).strip()
    html = read_file(os.path.join(out_dir, "body.html")).strip()
    text = read_file(os.path.join(out_dir, "body.md")).strip()

    if not subject:
        raise ValueError("subject.txt is empty")
    if not html:
        raise ValueError("body.html is empty")
    if not text:
        raise ValueError("body.md is empty")

    # Subject must be a single line.
    subject = subject.splitlines()[0].strip()

    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("RECIPIENT", "agustindiazoliva@gmail.com")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = recipient
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.send_message(msg)

    print(f"Sent: {subject}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: send_email.py <output_dir>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
