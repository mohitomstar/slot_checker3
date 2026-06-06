import os
import json
import requests
import smtplib

from bs4 import BeautifulSoup
from email.mime.text import MIMEText

LOGIN_URL = "https://www.e-license.jp/el26/?abc=5u0wVZP2Jec%2BbrGQYS%2B1OA%3D%3D&senisakiCd=4"

STATE_FILE = "state.json"

def send_email(subject, body):

    msg = MIMEText(body)

    msg["Subject"] = subject
    msg["From"] = os.environ["EMAIL_USER"]
    msg["To"] = os.environ["EMAIL_TO"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(
            os.environ["EMAIL_USER"],
            os.environ["EMAIL_APP_PASSWORD"]
        )

        smtp.send_message(msg)


def load_state():
    try:
        with open(STATE_FILE) as f:
            return set(json.load(f))
    except:
        return set()


def save_state(slots):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(list(slots)), f)

session = requests.Session()

landing = session.get(
    "https://www.e-license.jp/el26/?abc=5u0wVZP2Jec%2BbrGQYS%2B1OA%3D%3D&senisakiCd=4"
)

print("Cookies after GET:", session.cookies.get_dict())

payload = {
    "schoolCd": "5u0wVZP2Jec+brGQYS+1OA==",
    "studentId": os.environ["ELICENSE_ID"],
    "password": os.environ["ELICENSE_PASSWORD"]
}


req = requests.Request(
    "POST",
    LOGIN_URL,
    data=payload
)

prepared = session.prepare_request(req)

print(prepared.body)


response = session.post(
    LOGIN_URL,
    data=payload,
    allow_redirects=True
)

print("Cookies after POST:", session.cookies.get_dict())


print("Login URL:", response.url)

print("Final URL:", response.url)
print("Status:", response.status_code)


print("Contains login form:",
      'id="p01AForm"' in response.text)

print("Contains studentId field:",
      'id="studentId"' in response.text)

print("Contains password field:",
      'id="password"' in response.text)


print(response.text[:10000])



soup = BeautifulSoup(response.text, "html.parser")

slots = set()

for a in soup.select("td.status1 a.simei"):
    date = a.get("data-date")
    time = a.get("data-time")

    if date and time:
        slots.add(f"{date} {time}")

print("Slots found:", slots)
print(
    "status1 count:",
    len(soup.select("td.status1 a.simei"))
)

previous = load_state()

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
        "\n".join(body)
    )

save_state(slots)


