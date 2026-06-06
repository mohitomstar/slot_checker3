import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText


# -----------------------------
# EMAIL SENDER (same style as checker.py)
# -----------------------------
def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.environ["EMAIL_USER"]
    msg["To"] = os.environ["EMAIL_TO"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(
            os.environ["EMAIL_USER"],
            os.environ["EMAIL_APP_PASSWORD"],
        )
        smtp.send_message(msg)


# -----------------------------
# HEARTBEAT LOGIC
# -----------------------------
def send_heartbeat():
    now = datetime.utcnow().isoformat()

    body = "\n".join([
        "💓 Driving School Monitor Heartbeat",
        "",
        "Status: OK",
        "System: heartbeat.py (scheduled job)",
        f"Time (UTC): {now}",
        "",
        "This confirms that the 10-min checker pipeline is alive.",
    ])

    send_email(
        "💓 Heartbeat - Driving School Monitor",
        body
    )


# -----------------------------
# MAIN
# -----------------------------
def main():
    try:
        send_heartbeat()
        print("Heartbeat email sent successfully")
    except Exception as e:
        print(f"Heartbeat failed: {e}")
        raise


if __name__ == "__main__":
    main()
