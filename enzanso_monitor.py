import json
import os
import requests
import smtplib

from bs4 import BeautifulSoup
from email.mime.text import MIMEText

URL = "https://enzanso-reservation.jp/reserve/enz0010.php?p=10&type=10"

STATUS_FILE = "enzanso_status.json"

TARGET_DATES = {
    "18": "2026/07/18",
    "19": "2026/07/19",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# Email settings (GitHub Secrets)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

EMAIL_FROM = os.environ["EMAIL_USER"]
EMAIL_PASSWORD = os.environ["EMAIL_APP_PASSWORD"]
EMAIL_TO = os.environ["EMAIL_TO"]


def get_current_status():

    response = requests.get(URL, headers=HEADERS, timeout=20)
    response.raise_for_status()
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")

    calendar = soup.find("div", id="calendar")

    current = {}

    for div in calendar.find_all("div", class_="day"):

        text = div.get_text("\n", strip=True)

        if not text:
            continue

        parts = text.split("\n")

        if len(parts) < 2:
            continue

        day = parts[0].strip()
        status = parts[1].strip()

        if day in TARGET_DATES:

            current[TARGET_DATES[day]] = {
                "open": status != "満",
                "status": "FULL" if status == "満" else status
            }

    return current


def load_previous():

    if not os.path.exists(STATUS_FILE):
        return {}

    with open(STATUS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_status(status):

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=4, ensure_ascii=False)


def build_changes(old, new):

    changes = []

    for date in sorted(new):

        if old.get(date) != new[date]:

            previous = old.get(date, {"status": "Unknown"})["status"]

            current = new[date]["status"]

            changes.append(
                f"{date}: {previous} → {current}"
            )

    return changes


def send_email(changes):

    body = [
        "Reservation status changed.",
        "",
        "Changes:",
        ""
    ]

    body.extend(changes)

    msg = MIMEText("\n".join(body), "plain", "utf-8")
    msg["Subject"] = "Mountain Hut Reservation Update"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
        smtp.send_message(msg)


def main():

    current = get_current_status()

    previous = load_previous()

    changes = build_changes(previous, current)

    if changes:
        print("Changes detected.")
        send_email(changes)
        save_status(current)
    else:
        print("No changes.")


if __name__ == "__main__":
    main()
