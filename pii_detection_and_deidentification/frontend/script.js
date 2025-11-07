document.getElementById("uploadForm").addEventListener("submit", async function(e) {
  e.preventDefault();

  const fileInput = document.getElementById("fileInput").files[0];
  const confidenceThreshold = document.getElementById("confidenceThreshold").value;
  const alertEmail = document.getElementById("alertEmail").value;
  if (!fileInput) {
    showToast("Please select a file!", "error");
    return;
  }

  // Update file selected feedback
  document.getElementById("fileSelected").textContent = fileInput.name;
  document.getElementById("fileSelected").classList.add("show");

  // Show loading state and disable button
  document.getElementById("loadingSection").classList.add("show");
  document.getElementById("resultsSection").classList.remove("show");
  document.getElementById("processBtn").disabled = true;

  const formData = new FormData();
  formData.append("file", fileInput);
  formData.append("confidence_threshold", confidenceThreshold);
  if (alertEmail) {
    formData.append("alert_email", alertEmail);
  }

  try {
    const response = await fetch("http://127.0.0.1:5000/upload", {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
    }

    const data = await response.json();

    // Hide loading state and show results
    document.getElementById("loadingSection").classList.remove("show");
    document.getElementById("resultsSection").classList.add("show");
    document.getElementById("processBtn").disabled = false;

    // Update summary
    document.getElementById("summaryDetails").innerText = JSON.stringify(data.summary, null, 2);

    // Update Stats Grid
    const statsGrid = document.getElementById("statsGrid");
    statsGrid.innerHTML = `
      <div class="stat-card">
        <div class="stat-number">${data.summary.total_detections}</div>
        <div class="stat-label">Total Detections</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">${Object.values(data.summary.unique_values_by_type).reduce((a, b) => a + b, 0)}</div>
        <div class="stat-label">Unique PII Values</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">${Object.keys(data.summary.counts_by_type).length}</div>
        <div class="stat-label">PII Types</div>
      </div>
    `;

    // Update PII Types Chart
    const piiTypeCtx = document.getElementById("piiChart").getContext("2d");
    new Chart(piiTypeCtx, {
      type: "bar",
      data: {
        labels: Object.keys(data.summary.counts_by_type),
        datasets: [{
          label: "PII Detections",
          data: Object.values(data.summary.counts_by_type),
          backgroundColor: ["#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6", "#6366f1", "#f87171", "#4ade80", "#facc15"],
          borderColor: ["#1e3a8a"],
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: "Number of Detections" } },
          x: { title: { display: true, text: "PII Type" } }
        }
      }
    });

    // Update Detection Distribution Chart
    const piiDistCtx = document.getElementById("distributionChart").getContext("2d");
    new Chart(piiDistCtx, {
      type: "pie",
      data: {
        labels: Object.keys(data.summary.counts_by_type),
        datasets: [{
          data: Object.values(data.summary.counts_by_type),
          backgroundColor: ["#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6", "#6366f1", "#f87171", "#4ade80", "#facc15"]
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: "right" } }
      }
    });

    // Update Detections Table
    const tableBody = document.getElementById("detectionsTableBody");
    tableBody.innerHTML = "";
    data.detections.forEach(det => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${det.row_index}</td>
        <td>${det.column_name}</td>
        <td>${det.pii_type}</td>
        <td>${det.raw_value}</td>
        <td>${det.masked_value}</td>
        <td>${det.confidence.toFixed(3)}</td>
      `;
      tableBody.appendChild(row);
    });

    // Update Metrics
    const metricsGrid = document.getElementById("metricsGrid");
    metricsGrid.innerHTML = `
      <div class="metric-item">
        <h4>Total Detections</h4>
        <div class="value">${data.summary.total_detections}</div>
      </div>
      <div class="metric-item">
        <h4>Unique PII Values</h4>
        <div class="value">${Object.values(data.summary.unique_values_by_type).reduce((a, b) => a + b, 0)}</div>
      </div>
      <div class="metric-item">
        <h4>Average Confidence</h4>
        <div class="value">${Object.values(data.summary.average_confidence_by_type).reduce((a, b) => a + b, 0) / Object.keys(data.summary.average_confidence_by_type).length.toFixed(2) || 0}</div>
      </div>
      <div class="metric-item">
        <h4>Estimated Precision</h4>
        <div class="value">${Object.values(data.summary.estimated_precision).reduce((a, b) => a + b, 0) / Object.keys(data.summary.estimated_precision).length.toFixed(2) || 0}</div>
      </div>
    `;

    // Store file_id for downloads
    document.querySelectorAll(".download-btn").forEach(btn => {
      btn.dataset.fileId = data.id;
      btn.addEventListener("click", () => downloadFile(btn.dataset.filetype));
    });

    showToast("File processed successfully!", "success");
  } catch (error) {
    document.getElementById("loadingSection").classList.remove("show");
    document.getElementById("processBtn").disabled = false;
    showToast(`Error processing file: ${error.message}`, "error");
    console.error("Error details:", error);
  }
});

// Update confidence threshold display
document.getElementById("confidenceThreshold").addEventListener("input", function() {
  document.querySelector(".threshold-value").textContent = this.value;
});

// Update file selected feedback
document.getElementById("fileInput").addEventListener("change", function() {
  const fileName = this.files[0]?.name || "";
  const fileSelected = document.getElementById("fileSelected");
  fileSelected.textContent = fileName;
  fileSelected.classList.toggle("show", !!fileName);
});

// Download results
function downloadFile(type) {
  const fileId = document.querySelector(".download-btn").dataset.fileId;
  if (!fileId) {
    showToast("No file processed yet!", "error");
    return;
  }
  window.open(`http://127.0.0.1:5000/download/${type}?id=${fileId}`, "_blank");
}

// Toast notification
function showToast(message, type) {
  const toastContainer = document.querySelector(".toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <i class="fas fa-${type === "success" ? "check-circle" : "exclamation-circle"}"></i>
    ${message}
  `;
  toastContainer.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// Tab switching
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.target).classList.add("active");
  });
});