import os
import uuid
import logging
import smtplib, ssl
from email.message import EmailMessage

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

import pandas as pd
from pii_redactor import EnhancedProcessor  # Your processor class

# === Config ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

processor = EnhancedProcessor()

# === Gmail Config ===
SENDER_EMAIL = "hackathon533@gmail.com"          # Replace with your Gmail
APP_PASSWORD = "oalgfeohoaloyfcu" # Gmail App Password

# === Helper: send alert mail ===
# === Helper: send alert mail with attractive HTML body ===
def send_alert_email(file_id, recipient_email):
    attachments = []

    # Original uploaded file
    for f in os.listdir(UPLOAD_DIR):
        if f.startswith(file_id):
            attachments.append(os.path.abspath(os.path.join(UPLOAD_DIR, f)))

    # All reports in the report folder
    report_dir = os.path.join(REPORTS_DIR, file_id)
    if os.path.exists(report_dir):
        for f in os.listdir(report_dir):
            attachments.append(os.path.abspath(os.path.join(report_dir, f)))

    if not attachments:
        raise FileNotFoundError("No files found to attach. Check file_id and uploads/reports folder.")

    logging.info(f"Attachments to send: {attachments}")

    # Build email
    msg = EmailMessage()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = f"🚀 PII Detection Reports Ready - {file_id}"

    # HTML body
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #1a73e8;">PII Detection Dashboard</h2>
        <p>Hello,</p>
        <p>Your <b>PII detection reports</b> have been successfully generated! 🎉</p>
        <ul>
            <li><b>File ID:</b> {file_id}</li>
            <li><b>Total attachments:</b> {len(attachments)}</li>
        </ul>
        <p>Attached are the uploaded file(s) and detailed reports:</p>
        <ol>
            {''.join([f"<li>{os.path.basename(f)}</li>" for f in attachments])}
        </ol>
        <p style="color: #555;">Please review the reports and take necessary actions on sensitive data.</p>
        <p style="margin-top: 20px;">Thank you for using our <b>PII Detection System</b>!<br>🔒 Your data security is our priority.</p>
        <hr>
        <p style="font-size: 12px; color: #888;">This is an automated email. Please do not reply.</p>
    </body>
    </html>
    """
    msg.add_alternative(html_content, subtype='html')

    # Attach files
    for filepath in attachments:
        with open(filepath, "rb") as f:
            data = f.read()
            msg.add_attachment(
                data,
                maintype='application',
                subtype='octet-stream',
                filename=os.path.basename(filepath)
            )
            logging.info(f"Attached file: {os.path.basename(filepath)}")

    # Send email
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
        logging.info(f"Email sent successfully to {recipient_email}")
        return f"Email sent to {recipient_email} with {len(attachments)} attachments."
    except Exception as e:
        logging.error(f"Error sending email: {e}")
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
    recipient_email = request.form.get("alert_email")  # Matches frontend input id

    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{file.filename}"
    upload_path = os.path.join(UPLOAD_DIR, filename)
    file.save(upload_path)
    logging.info(f"Processing uploaded file: {upload_path}")

    # Create report folder
    work_report = os.path.join(REPORTS_DIR, file_id)
    os.makedirs(work_report, exist_ok=True)

    # Process file
    work_output = os.path.join(UPLOAD_DIR, f"{file_id}_processed.csv")
    result = processor.process_file(upload_path, work_output, work_report, confidence_threshold)

    # Generate visual report if supported
    if hasattr(processor, "generate_visual_report"):
        processor.generate_visual_report(work_report, os.path.join(work_report, "visual_report.pdf"))

    # Automatically send email if recipient provided
    email_status = None
    if recipient_email:
        try:
            email_status = send_alert_email(file_id, recipient_email)
        except Exception as e:
            logging.error(f"Error sending email: {e}")
            email_status = f"Email failed: {str(e)}"

    return jsonify({
        "id": file_id,
        "summary": result.get("summary", {}),
        "detections": result.get("detections", []),
        "email_status": email_status
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

# Download files endpoint
@app.route("/download/<filetype>")
def download_file(filetype):
    file_id = request.args.get("id")
    if not file_id:
        return jsonify({"error": "Missing file ID"}), 400

    if filetype == "deidentified":
        folder = UPLOAD_DIR
        files = [f for f in os.listdir(folder) if f.startswith(f"{file_id}_processed")]
    elif filetype == "detections":
        folder = os.path.join(REPORTS_DIR, file_id)
        files = [f for f in os.listdir(folder) if "detections" in f.lower()]
    elif filetype == "summary":
        folder = os.path.join(REPORTS_DIR, file_id)
        files = [f for f in os.listdir(folder) if "summary" in f.lower()]
    elif filetype == "visual_report":
        folder = os.path.join(REPORTS_DIR, file_id)
        files = [f for f in os.listdir(folder) if f.endswith(".pdf")]
    else:
        return jsonify({"error": f"Invalid filetype: {filetype}"}), 400

    if not files:
        return jsonify({"error": "File not found"}), 404

    return send_file(os.path.join(folder, files[0]), as_attachment=True)

# === Run App ===
if __name__ == "__main__":
    app.run(debug=True)
