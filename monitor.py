import os
import json
import smtplib
from email.mime.text import MIMEText

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

LOGIN_URL = "https://www.e-license.jp/el26/?abc=5u0wVZP2Jec%2BbrGQYS%2B1OA%3D%3D&senisakiCd=4"

STATE_FILE = "state.json"


def send_email(subject, body):
    sender = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_APP_PASSWORD"]
    recipient = os.environ["EMAIL_TO"]

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)


def load_previous_slots():
    if not os.path.exists(STATE_FILE):
        return set()

    with open(STATE_FILE, "r") as f:
        return set(json.load(f))


def save_slots(slots):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(list(slots)), f)


def get_available_slots():
    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        page.goto(LOGIN_URL)

        page.fill('input[name="studentId"]',
                  os.environ["ELICENSE_ID"])

        page.fill('input[name="password"]',
                  os.environ["ELICENSE_PASSWORD"])

        page.click("button[type='submit']")

        page.wait_for_load_state("networkidle")

        html = page.content()

        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    slots = set()

    for a in soup.select("td.status1 a.simei"):

        date = a.get("data-date")
        time = a.get("data-time")

        slots.add(f"{date} {time}")

    return slots


def main():

    current_slots = get_available_slots()
    previous_slots = load_previous_slots()

    new_slots = current_slots - previous_slots
    removed_slots = previous_slots - current_slots

    if new_slots or removed_slots:

        body = []

        if new_slots:
            body.append("NEW SLOTS\n")
            body.extend(sorted(new_slots))
            body.append("")

        if removed_slots:
            body.append("REMOVED SLOTS\n")
            body.extend(sorted(removed_slots))

        send_email(
            "Driving School Slot Update",
            "\n".join(body)
        )

    save_slots(current_slots)


if __name__ == "__main__":
    main()
