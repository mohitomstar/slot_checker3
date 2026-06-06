import os
import json
import requests
import smtplib

from bs4 import BeautifulSoup
from email.mime.text import MIMEText

LOGIN_URL = "https://www.e-license.jp/el26/?abc=5u0wVZP2Jec%2BbrGQYS%2B1OA%3D%3D&senisakiCd=4"

LOGIN_PAGE_URL = "https://www.e-license.jp/el26/?abc=5u0wVZP2Jec%2BbrGQYS%2B1OA%3D%3D&senisakiCd=4"

LOGIN_POST_URL = "https://www.e-license.jp/el26/pc/login"

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

landing = session.get(LOGIN_PAGE_URL)

print("Cookies after GET:", session.cookies.get_dict())

payload = {
    "schoolCd": "5u0wVZP2Jec%2BbrGQYS%2B1OA%3D%3D",
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


headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.e-license.jp/el26/?abc=5u0wVZP2Jec%2BbrGQYS%2B1OA%3D%3D&senisakiCd=4",
    "Origin": "https://www.e-license.jp"
}

response = session.post(
    LOGIN_POST_URL,
    data=payload,
    headers=headers,
    allow_redirects=True
)


print("POST URL:", LOGIN_POST_URL)
print("Response URL:", response.url)
print("Response status:", response.status_code)

from bs4 import BeautifulSoup

soup = BeautifulSoup(response.text, "html.parser")

print("===== POSSIBLE ERROR TEXT =====")

for text in soup.stripped_strings:
    if any(word in text for word in [
        "エラー",
        "失敗",
        "パスワード",
        "教習生番号",
        "ログイン",
        "入力",
        "認証"
    ]):
        print(text)

print("TITLE:", soup.title.text if soup.title else "NO TITLE")



print("Cookies after POST:", session.cookies.get_dict())

print("Redirect history:")
for r in response.history:
    print(r.status_code, r.url)

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


