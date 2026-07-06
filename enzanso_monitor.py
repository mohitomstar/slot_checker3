#!/usr/bin/env python3
"""
Checks the reservation calendar at enzanso-reservation.jp for ONE specific
day (TARGET_DAY, default 18) and emails you if it opens up.

The target day is considered OPEN if its status text is anything other
than "満" (full) and is not blank/empty.

State (the last known status for the target day) is persisted to a JSON
file so re-running every 5 minutes doesn't send duplicate emails while
the status stays the same. An email IS re-sent if the status changes
again later (e.g. "△" -> "3" remaining), and also if it later flips back
to "満" and then opens again.
"""

import json
import os
import smtplib
import sys
from email.mime.text import MIMEText
from email.header import Header

import requests
from bs4 import BeautifulSoup

URL = os.environ.get("TARGET_URL", "https://enzanso-reservation.jp/reserve/enz0010.php")
STATE_FILE = os.environ.get("STATE_FILE", "enzanso_status.json")
FULL_STATUS = "満"
TARGET_DAY = int(os.environ.get("TARGET_DAY", "18"))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def fetch_html():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    # The site is a Japanese page; let requests/BS4 sort out encoding,
    # but fall back to explicit encoding if mojibake is detected.
    if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding
    return resp.text


def parse_calendar(html):
    """Returns dict: {day_int: status_str} and the calendar's displayed month label."""
    soup = BeautifulSoup(html, "html.parser")

    session = requests.Session()

    response = session.get(URL)
    
    with open("debug.html", "w", encoding="utf-8") as f:
    f.write(response.text)

    print("Saved debug.html")

    print("Status code:", response.status_code)
    print("Final URL:", response.url)
    
    calendar_div = soup.find("div", id="calendar")
    if calendar_div is None:
        raise RuntimeError("Could not find <div id='calendar'> on the page")

    cal_ul = calendar_div.find("ul", class_="cal")
    if cal_ul is None:
        raise RuntimeError("Could not find <ul class='cal'> on the page")

    month_label_tag = calendar_div.find("li", id="calendarDate")
    month_label = month_label_tag.get_text(strip=True) if month_label_tag else "unknown"

    days = {}
    for li in cal_ul.find_all("li"):
        classes = li.get("class") or []
        if "calh" in classes:
            continue  # weekday header row (日 月 火 ...)

        day_div = li.find("div", class_="day")
        if day_div is None:
            continue

        # Days that are clickable/open are wrapped in an <a>, others are plain text.
        container = day_div.find("a") or day_div

        parts = [p.replace("\xa0", "").strip() for p in container.stripped_strings]
        parts = [p for p in parts if p != ""]

        if not parts:
            continue  # blank filler cell (&nbsp; only)

        day_num_str = parts[0]
        if not day_num_str.isdigit():
            continue

        status = parts[1] if len(parts) > 1 else ""
        days[int(day_num_str)] = status

    return days, month_label


def get_target_day_status(days):
    """Returns the status string for TARGET_DAY, or None if it's not on this
    calendar page at all (e.g. wrong month, or day hasn't rendered)."""
    return days.get(TARGET_DAY)


def is_open(status):
    """A day is OPEN if its status is present and isn't '満' (full)."""
    return status is not None and status != FULL_STATUS and status != ""


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def send_email(subject, body):
    # Gmail's SMTP host/port are fixed, so no need to configure them.
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    gmail_address = os.environ["EMAIL_USER"]
    gmail_app_password = os.environ["EMAIL_APP_PASSWORD"]
    email_to = os.environ.get("EMAIL_TO", gmail_address)  # comma-separated allowed

    recipients = [addr.strip() for addr in email_to.split(",") if addr.strip()]

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = gmail_address
    msg["To"] = ", ".join(recipients)

    with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, recipients, msg.as_string())


def main():
    html = fetch_html()
    days, month_label = parse_calendar(html)
    status = get_target_day_status(days)

    state = load_state()
    last_status = state.get("last_status")  # None, "満", "", "◯", "3", etc.

    if status is None:
        print(f"Day {TARGET_DAY} not found on the current calendar page "
              f"({month_label}). No action taken.")
        return

    if is_open(status) and status != last_status:
        subject = f"[Slot Alert] Day {TARGET_DAY} is open! ({month_label})"
        body = (
            f"Day {TARGET_DAY} on the {month_label} calendar is now open.\n\n"
            f"Status: {status}\n\n"
            f"{URL}"
        )
        print(body)
        send_email(subject, body)
    elif is_open(status):
        print(f"Day {TARGET_DAY} is still open (status: '{status}'), "
              f"already notified - skipping email.")
    else:
        print(f"Day {TARGET_DAY} is full/unavailable (status: '{status}').")

    if status != last_status:
        save_state({"last_status": status})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
