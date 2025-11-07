import os
import uuid
import logging
import smtplib, ssl
from email.message import EmailMessage

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

import pandas as pd
from pii_redactor import EnhancedProcessor  # your processor class

# === Config ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")  # backend/uploads folder
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")

os.makedirs(UPLOAD_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

processor = EnhancedProcessor()

# === Gmail Config ===
SENDER_EMAIL = "hackathon533@gmail.com"          # replace with your Gmail
APP_PASSWORD = "oalgfeohoaloyfcu" # Gmail App Password

# === Helper: send alert mail ===
def send_alert_email(file_id, recipient_email):
    attachments = []

    # Attach uploaded file(s)
    for f in os.listdir(UPLOAD_DIR):
        if f.startswith(file_id):
            attachments.append(os.path.abspath(os.path.join(UPLOAD_DIR, f)))

    if not attachments:
        raise FileNotFoundError("No files found to attach. Check file_id and uploads folder.")

    print("Attachments to send:", attachments)

    # Build email
    msg = EmailMessage()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = f"PII Detection Reports - {file_id}"
    msg.set_content("Attached are the uploaded file(s) for testing email delivery.")

    for filepath in attachments:
        with open(filepath, "rb") as f:
            data = f.read()
            msg.add_attachment(data, maintype='application', subtype='octet-stream', filename=os.path.basename(filepath))
            print("Attached file:", os.path.basename(filepath))

    # Send email
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
        print("Recipient Email:", recipient_email)
        print("Email sent successfully!")
        return f"Email sent to {recipient_email} with {len(attachments)} attachments."
    except Exception as e:
        print("Error sending email:", e)
        raise

# === API Routes ===
@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(FRONTEND_DIR, path)

@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")
    confidence_threshold = float(request.form.get("confidence_threshold", 0.7))

    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{file.filename}"  # e.g., 6f606ea3-f7f6-4486-af06-0945a4ac9227_sample.csv
    upload_path = os.path.join(UPLOAD_DIR, filename)
    file.save(upload_path)

    logging.info(f"Processing uploaded file: {upload_path}")

    # Process file
    work_output = upload_path  # we can overwrite the uploaded file or save elsewhere
    result = processor.process_file(upload_path, work_output, None, confidence_threshold)

    return jsonify({
        "id": file_id,
        "summary": result["summary"],
        "detections": result["detections"]
    })

@app.route("/alert", methods=["POST"])
def alert_mail():
    file_id = request.form.get("id")
    recipient = request.form.get("email")

    if not file_id or not recipient:
        return jsonify({"error": "Missing file ID or recipient"}), 400

    try:
        msg = send_alert_email(file_id, recipient)
        return jsonify({"message": msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Run App ===
if __name__ == "__main__":
    app.run(debug=True)
