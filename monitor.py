import json
import os
import smtplib
import requests

from bs4 import BeautifulSoup
from email.mime.text import MIMEText

LOGIN_PAGE_URL = (
    "https://www.e-license.jp/el26/"
    "?abc=5u0wVZP2Jec%2BbrGQYS%2B1OA%3D%3D&senisakiCd=4"
)

LOGIN_POST_URL = "https://www.e-license.jp/el26/pc/login"

STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")


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


def load_state():
    try:
        with open(STATE_FILE) as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_state(slots):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(slots), f)


def get_slots():
    session = requests.Session()

    session.get(LOGIN_PAGE_URL)

    payload = {
        "schoolCd": "5u0wVZP2Jec%2BbrGQYS%2B1OA%3D%3D",
        "studentId": os.environ["ELICENSE_ID"],
        "password": os.environ["ELICENSE_PASSWORD"],
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/137.0.0.0 Safari/537.36"
        ),
        "Referer": LOGIN_PAGE_URL,
        "Origin": "https://www.e-license.jp",
    }

    response = session.post(
        LOGIN_POST_URL,
        data=payload,
        headers=headers,
        allow_redirects=True,
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    slots = set()

    for a in soup.select("td.status1 a.simei"):
        date = a.get("data-date")
        time = a.get("data-time")

        if date and time:
            slots.add(f"{date} {time}")

    return slots
    
'''    
def send_status_email(slots):
    body = [
        "Driving School Monitor Status",
        "",
        "Monitor is running successfully.",
        f"Open slots found: {len(slots)}",
        "",
    ]

    if slots:
        body.append("Current open slots:")
        body.extend(sorted(slots))
    else:
        body.append("No open slots found.")

    send_email(
        "Driving School Monitor Status",
        "\n".join(body)
    )
'''

def main():
    slots = get_slots()

    print(f"Found {len(slots)} open slots")

    previous = load_state()

     # If this is the first run, just save and exit (no email)
    if not previous:
        save_state(slots)
        print("Initial run - state saved, no email sent.")
        return

    new_slots = slots - previous
    removed_slots = previous - slots

    if new_slots or removed_slots:
        body = []

        if new_slots:
            body.append("NEW SLOTS")
            body.extend(sorted(new_slots))
            body.append("")

        if removed_slots:
            body.append("REMOVED SLOTS")
            body.extend(sorted(removed_slots))

        send_email(
            "Driving School Slot Update",
            "\n".join(body),
        )

    save_state(slots)

    # Always send status email
    # send_status_email(slots)


if __name__ == "__main__":
    main()
