import os
import json
import time
from fastapi import FastAPI
import firebase_admin
from firebase_admin import credentials, firestore
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
import smtplib
from email.message import EmailMessage

# -----------------------------
# TIMEZONE
# -----------------------------
IST = pytz.timezone("Asia/Kolkata")

# -----------------------------
# FIREBASE INITIALIZATION
# (FROM ENV VARIABLE)
# -----------------------------
cred = credentials.Certificate(
    json.loads(os.environ["FIREBASE_KEY"])
)
firebase_admin.initialize_app(cred)
db = firestore.client()

# -----------------------------
# EMAIL CONFIG (FROM ENV)
# -----------------------------
EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]
EMAIL_APP_PASSWORD = os.environ["EMAIL_APP_PASSWORD"]

# -----------------------------
# FASTAPI APP
# -----------------------------
app = FastAPI()

@app.get("/")
def home():
    return {"status": "Reminder backend running"}

# -----------------------------
# EMAIL FUNCTION
# -----------------------------
def send_email(to_email: str, message: str):
    msg = EmailMessage()
    msg["Subject"] = "⏰ Daily Reminder For You!"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg.set_content(message)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        smtp.send_message(msg)

# -----------------------------
# REMINDER JOB
# -----------------------------
def reminder_job():
    now_time = datetime.now(IST).strftime("%H:%M")
    today = datetime.now(IST).strftime("%Y-%m-%d")

    print("Checking reminders at", now_time)

    users = db.collection("users").stream()

    for user in users:
        user_data = user.to_dict()
        email = user_data.get("email")

        if not email:
            continue

        reminders = (
            db.collection("users")
            .document(user.id)
            .collection("reminders")
            .stream()
        )

        for reminder in reminders:
            data = reminder.to_dict()
            reminder_time = data.get("time")
            last_sent = data.get("lastSent")

            if reminder_time == now_time and last_sent != today:
                try:
                    send_email(
                        email,
                        data.get("message", "This is your daily reminder 🚀"),
                    )

                    reminder.reference.update({
                        "lastSent": today
                    })

                    print(f"Email sent to {email} at {now_time}")

                except Exception as e:
                    print("Email sending failed:", e)

# -----------------------------
# SCHEDULER
# -----------------------------
scheduler = BackgroundScheduler()
scheduler.add_job(reminder_job, "interval", minutes=1)

@app.on_event("startup")
def start_scheduler():
    if not scheduler.running:
        scheduler.start()


