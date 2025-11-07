

# PII Detection Dashboard

![PII Detection Dashboard](https://raw.githubusercontent.com/S-Karthikeyan-17/pii_detection_and_deidentification/main/output_screenshots/output2.png)

**Securely Detect and Anonymize Sensitive Data with Ease!**

The **PII Detection Dashboard** is a state-of-the-art web application crafted for **Hackathon Activity 6**, designed to identify and de-identify personally identifiable information (PII) in CSV files, with a special focus on Indian datasets. Protect sensitive data like Aadhaar numbers, PAN cards, phone numbers, and more with advanced detection algorithms, customizable confidence thresholds, and a visually stunning, interactive dashboard.

## 🚀 Key Features

- **Advanced PII Detection**: Detects Indian-specific PII (Aadhaar, PAN, phone, email, IFSC, credit card, bank account) using regex patterns and validation algorithms (Verhoeff for Aadhaar, Luhn for credit cards).
- **Customizable Confidence Threshold**: Fine-tune detection sensitivity (0.5–1.0) via an intuitive slider to balance accuracy and coverage.
- **Interactive Visualizations**:
  - Bar and pie charts showcasing PII type distribution.
  - Tabbed views for Summary (JSON), Detections (detailed table), and Metrics (totals).
  - Stats grid for instant insights (total detections, unique PII values).
- **Downloadable Reports**:
  - De-identified CSV with masked/anonymized data.
  - Detections CSV detailing row, column, PII type, original/masked values, and confidence.
  - Summary TXT/JSON with processing details and timestamps.
- **User-Friendly Interface**:
  - Responsive design with vibrant gradients, particle animations, and Tailwind-inspired styling.
  - Toast notifications for success and error feedback.
  - Real-time updates for charts, tables, and metrics.
- **Secure Anonymization**: Irreversible hashing for PAN, IFSC, and bank accounts; partial masking for phone, Aadhaar, and credit cards.
- **Detailed Logging**: Backend logs with timestamps (e.g., `2025-08-27 00:06:00`) for debugging and tracking.

![Upload Interface](https://raw.githubusercontent.com/S-Karthikeyan-17/pii_detection_and_deidentification/main/output_screenshots/output1.png)

## 🛠 Tech Stack

### Frontend
- **HTML5**: Dashboard structure.
- **CSS3**: Custom styles with gradients, animations, and responsive design.
- **JavaScript (ES6)**: Dynamic interactions and fetch API for backend communication.
- **Chart.js**: Bar and pie charts for data visualization.
- **Font Awesome**: Icons for enhanced UI.

### Backend
- **Python 3.12+**: Core PII detection and processing logic.
- **Flask**: Lightweight API for `/upload` and `/download` endpoints.
- **flask-cors**: Enables cross-origin requests from frontend.
- **pii_redactor.py**: Custom module for PII detection and anonymization.

### Dependencies
- Backend: Flask, flask-cors (install via `pip`).
- Frontend: No setup needed (uses CDNs for Chart.js, Font Awesome).

## 🏗 Architecture

- **Frontend** (`http://localhost:8000`): Served via Python’s HTTP server, sends CSV files to the backend via `POST /upload`, and renders results (charts, tables) from JSON responses.
- **Backend** (`http://127.0.0.1:5000`): Flask API processes uploads and serves files:
  - **/upload (POST)**: Processes CSV, calls `pii_redactor.py`, and saves results in `reports/<file_id>`.
  - **/download/<filetype> (GET)**: Serves de-identified CSV, detections CSV, or summary TXT.
- **Data Flow**:
  1. User uploads CSV → Frontend sends to `/upload`.
  2. Backend processes, returns JSON (`id`, `summary`, `detections`).
  3. Frontend updates visualizations and enables downloads via `/download`.
- **Storage**:
  - `uploads/`: Temporary CSV storage.
  - `reports/`: Processed files per `file_id` (UUID-based).

![Results Dashboard](https://raw.githubusercontent.com/S-Karthikeyan-17/pii_detection_and_deidentification/main/output_screenshots/output3.png)
![Results Dashboard](https://raw.githubusercontent.com/S-Karthikeyan-17/pii_detection_and_deidentification/main/output_screenshots/output4.png)
## 📦 Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/S-Karthikeyan-17/pii_detection_and_deidentification.git
   cd pii_detection_and_deidentification
   ```

2. **Project Structure**:
   ```
   pii_detection_and_deidentification/
   ├── frontend/
   │   ├── index.html
   │   ├── script.js
   │   ├── style.css
   ├── backend/
   │   ├── app.py
   │   ├── pii_redactor.py
   ├── output_screenshots/
   │   ├── output1.png
   │   ├── output2.png
   │   ├── output3.png
   │   ├── output4.png
   ├── README.md
   ├── sample.csv
   ├── .gitignore
   ```

3. **Install Backend Dependencies**:
   ```bash
   cd backend
   pip install flask flask-cors
   ```

4. **Frontend Setup**: No additional setup required (uses CDNs).

## 🚀 Execution Steps

### 1. Start the Backend
```bash
cd backend
python app.py
```
- Runs on `http://127.0.0.1:5000`.
- Verify: `curl http://127.0.0.1:5000/` → `{"message": "PII Detection Dashboard Backend. Use /upload to process files."}`.
- **Port Conflict**: If “Address already in use”, change port in `app.py`:
  ```python
  if __name__ == "__main__":
      app.run(debug=True, port=5001)
  ```
  Update `script.js`:
  ```javascript
  const response = await fetch("http://127.0.0.1:5001/upload", {
  window.open(`http://127.0.0.1:5001/download/${type}?id=${fileId}`, "_blank");
  ```

### 2. Start the Frontend
In a new terminal:
```bash
cd frontend
python -m http.server 8000
```
- Access: `http://localhost:8000`.

### 3. Test the Application
- Open `http://localhost:8000`.
- Upload a CSV (e.g., `sample.csv`), adjust confidence threshold, and view results.
- Download reports (de-identified CSV, detections, summary).

### 4. Stop Servers
Press `Ctrl+C` in each terminal.

## 🎮 Usage Guide

### Access the Dashboard
Navigate to `http://localhost:8000` to see the upload interface with a file picker and confidence threshold slider.

### Upload a CSV
- Select a CSV file (e.g., `sample.csv`).
- Adjust confidence threshold (0.5–1.0, default 0.7).
- Click **Process File**.

### View Results
- **Stats Grid**: Total detections, unique PII values.
- **Charts**: Bar (PII types), pie (distribution).
- **Tabs**:
  - **Summary**: JSON details with timestamp (e.g., `2025-08-27T00:06:00+05:30`).
  - **Detections**: Table with row, column, PII type, original/masked values, confidence.
  - **Metrics**: Totals and unique counts.
- **Downloads**: De-identified CSV, detections CSV, summary TXT.

### Adjust Confidence Threshold
- **Lower (0.5)**: More detections, including potential false positives.
- **Higher (0.9)**: Fewer, high-accuracy detections.

## 🔍 Confidence Threshold Explained

The **confidence threshold** (0.5–1.0) filters PII detections based on scores calculated in `pii_redactor.py`:
- **Scoring**:
  - **Aadhaar**: 0.95 (Verhoeff-validated), 0.7 (12 digits), 0.3 (invalid).
  - **Phone**: 0.9 (valid Indian number), 0.4 (invalid).
  - **PAN, Email**: 1.0 (regex match).
  - **IFSC**: 0.95 (valid format), 0.5 (invalid).
  - **Bank Account**: 0.8 (context keywords), 0.6 (9-18 digits).
- **Impact**:
  - Lower threshold: Larger charts/tables, more detections.
  - Higher threshold: Higher accuracy, fewer detections.
- **Usage**: Adjust via slider; impacts charts, tables, and reports.

## 📊 Sample CSV for Testing

Save as `sample.csv`:
```csv
Name,Phone,Email,Aadhaar,PAN,IFSC,BankAccount
Amit Sharma,+919876543210,amit.sharma@example.com,1234 5678 9012,ABCDE1234F,SBIN0001234,123456789012
Priya Patel,9876543210,priya.patel@test.com,2345 6789 0123,FGHIJ5678K,HDFC0005678,987654321098
Rahul Verma,+91-9123456789,rahul.verma@sample.org,3456 7890 1234,KLMNO9012P,ICIC0009012,456789123456
Sneha Gupta,9123456789,sneha.gupta@demo.in,4567 8901 2345,PQRST3456U,AXIS0003456,789123456789
Vikram Singh,+919123456789,vikram.singh@example.com,5678 9012 3456,UVWXY7890Z,SBIN0007890,234567890123
```
- **Test**: Upload with thresholds 0.5, 0.7, 0.9 to observe detection counts (e.g., ~30 at 0.5, ~20 at 0.9).

## 🛠 Troubleshooting

### Frontend Not Fetching Backend
- **Issue**: "Failed to fetch" at `http://127.0.0.1:5000/upload`.
- **Fix**:
  - Ensure backend is running:
    ```bash
    cd backend
    python app.py
    ```
  - Test: `curl http://127.0.0.1:5000/`.
  - Check browser console (F12, Network tab) for `/upload` status (200, 500, etc.).
  - Verify CORS: `CORS(app)` in `app.py`, `flask-cors` installed (`pip install flask-cors`).
  - **Port Conflict**:
    ```powershell
    netstat -aon | findstr :5000
    taskkill /PID <PID> /F
    ```
    Or use port 5001 (update `app.py`, `script.js`).
  - **Permissions**: Ensure `uploads/` and `reports/` are writable:
    ```powershell
    icacls backend\uploads /grant Everyone:F /T
    icacls backend\reports /grant Everyone:F /T
    ```

### Processing Errors
- Check backend logs (e.g., `2025-08-27 00:06:00 - ERROR - Error processing file`).
- Ensure `pii_redactor.py` is in `backend/`.
- Verify file permissions (see above).

### Charts Not Rendering
- Confirm Chart.js CDN in `index.html`.
- Check browser console for JavaScript errors.

### Git Push Issues
- **Error**: `src refspec main does not match any`:
  - Ensure commits exist: `git log`.
  - Check branch: `git branch` (rename if needed: `git branch -m master main`).
  - Push: `git push -u origin main`.
- **Authentication**: Use a personal access token ([generate here](https://github.com/settings/tokens)).

## 🤝 Contributing

We welcome contributions! To contribute:
1. Fork the repository.
2. Create a branch: `git checkout -b feature/your-feature`.
3. Commit changes: `git commit -m "Add your feature"`.
4. Push: `git push origin feature/your-feature`.
5. Open a pull request.

Report issues or suggest features via GitHub Issues.

## 📬 Contact

For questions or support, contact su.karthikeyan17@gmail.com or open a GitHub issue at [S-Karthikeyan-17/pii_detection_and_deidentification](https://github.com/S-Karthikeyan-17/pii_detection_and_deidentification).




