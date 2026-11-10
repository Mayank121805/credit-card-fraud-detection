/**
 * FraudGuard AI - Dashboard Controller
 * Handles Overview KPIs, Distribution Doughnut, 48-Hour Dual-Axis Time Series,
 * Amount Range Distribution, Stats Table, and Dataset Drag-and-Drop Upload.
 */

document.addEventListener('DOMContentLoaded', () => {
  'use strict';

  // Elements
  const uploadSection = document.getElementById('upload-section');
  const trainingCtaSection = document.getElementById('training-cta-section');
  const dropzone = document.getElementById('dataset-dropzone');
  const fileInput = document.getElementById('dataset-file-input');
  const browseBtn = document.getElementById('browse-btn');
  const fileNameDisplay = document.getElementById('upload-file-name');
  const progressWrap = document.getElementById('upload-progress-wrap');
  const progressBar = document.getElementById('upload-progress-bar');
  const progressText = document.getElementById('upload-progress-text');
  const progressPercent = document.getElementById('upload-progress-percent');
  const uploadFeedback = document.getElementById('upload-feedback');

  // KPI elements
  const kpiTotalTx = document.getElementById('kpi-total-tx');
  const kpiFraudTx = document.getElementById('kpi-fraud-tx');
  const kpiLegitTx = document.getElementById('kpi-legit-tx');
  const kpiFraudRate = document.getElementById('kpi-fraud-rate');
  const kpiTotalAmount = document.getElementById('kpi-total-amount');
  const kpiAvgAmount = document.getElementById('kpi-avg-amount');
  const kpiDatasetName = document.getElementById('kpi-dataset-name');

  // Distribution extra labels
  const distRatioBadge = document.getElementById('dist-ratio-badge');
  const distLegitCount = document.getElementById('dist-legit-count');
  const distFraudCount = document.getElementById('dist-fraud-count');

  /**
   * 1. Load Overview KPIs
   */
  async function loadOverview() {
    try {
      const data = await App.api('/api/analytics/overview', { silent: true });

      if (!data || !data.dataset_loaded) {
        // Dataset not loaded: show upload section prominently
        if (uploadSection) uploadSection.classList.remove('d-none');
        if (kpiTotalTx) kpiTotalTx.innerHTML = '<span class="text-secondary-custom">0</span>';
        if (kpiFraudTx) kpiFraudTx.innerHTML = '<span class="text-secondary-custom">0</span>';
        if (kpiLegitTx) kpiLegitTx.innerHTML = '<span class="text-secondary-custom">0</span>';
        if (kpiFraudRate) kpiFraudRate.innerHTML = '<span class="text-secondary-custom">0.00%</span>';
        if (kpiTotalAmount) kpiTotalAmount.innerHTML = '<span class="text-secondary-custom">$0.00</span>';
        if (kpiAvgAmount) kpiAvgAmount.innerHTML = '<span class="text-secondary-custom">$0.00</span>';
        return false;
      }

      // Dataset loaded: optionally collapse or hide upload section
      if (uploadSection) {
        uploadSection.classList.add('d-none');
      }

      // Populate KPI cards
      if (kpiTotalTx) kpiTotalTx.textContent = App.formatNumber(data.total_transactions);
      if (kpiFraudTx) kpiFraudTx.textContent = App.formatNumber(data.fraud_count);
      if (kpiLegitTx) kpiLegitTx.textContent = App.formatNumber(data.legit_count);
      if (kpiFraudRate) kpiFraudRate.textContent = App.formatPercent(data.fraud_rate, 3);
      if (kpiTotalAmount) kpiTotalAmount.textContent = App.formatCurrency(data.total_amount);
      if (kpiAvgAmount) kpiAvgAmount.textContent = App.formatCurrency(data.avg_amount);
      if (kpiDatasetName) kpiDatasetName.textContent = data.dataset_name || 'creditcard.csv';

      return true;
    } catch (err) {
      console.warn('Overview API not ready or dataset not found:', err);
      if (uploadSection) uploadSection.classList.remove('d-none');
      return false;
    }
  }

  /**
   * 2. Load Class Distribution Chart
   */
  async function loadDistributionChart() {
    try {
      const data = await App.api('/api/analytics/distribution', { silent: true });
      if (!data || !data.class_counts) return;

      const legitCount = data.class_counts[0] ?? 284315;
      const fraudCount = data.class_counts[1] ?? 492;
      const total = legitCount + fraudCount;
      const legitPct = total > 0 ? ((legitCount / total) * 100).toFixed(2) : 99.83;
      const fraudPct = total > 0 ? ((fraudCount / total) * 100).toFixed(2) : 0.17;

      if (distRatioBadge) distRatioBadge.textContent = `${legitPct}% / ${fraudPct}%`;
      if (distLegitCount) distLegitCount.textContent = App.formatNumber(legitCount);
      if (distFraudCount) distFraudCount.textContent = App.formatNumber(fraudCount);

      App.createChart('chart-distribution', {
        type: 'doughnut',
        data: {
          labels: ['Legitimate (Class 0)', 'Fraudulent (Class 1)'],
          datasets: [
            {
              data: [legitCount, fraudCount],
              backgroundColor: ['#3fb950', '#f85149'],
              borderColor: '#161b22',
              borderWidth: 3,
              hoverOffset: 6
            }
          ]
        },
        options: {
          cutout: '72%',
          plugins: {
            legend: {
              position: 'bottom'
            },
            tooltip: {
              callbacks: {
                label: function (context) {
                  const val = context.raw || 0;
                  const pct = total > 0 ? ((val / total) * 100).toFixed(3) : 0;
                  return ` ${context.label}: ${App.formatNumber(val)} (${pct}%)`;
                }
              }
            }
          }
        }
      });
    } catch (e) {
      console.warn('Distribution chart data error:', e);
    }
  }

  /**
   * 3. Load 48-Hour Dual-Axis Time Series
   */
  async function loadTimeSeriesChart() {
    try {
      const data = await App.api('/api/analytics/time-series', { silent: true });
      if (!data || !data.bin_labels) return;

      App.createChart('chart-timeseries', {
        type: 'line',
        data: {
          labels: data.bin_labels,
          datasets: [
            {
              label: 'Legitimate Volume',
              data: data.legit_counts,
              borderColor: '#58a6ff',
              backgroundColor: 'rgba(88, 166, 255, 0.08)',
              borderWidth: 2,
              pointRadius: 2,
              pointHoverRadius: 5,
              tension: 0.35,
              fill: true,
              yAxisID: 'y'
            },
            {
              label: 'Fraud Incidents',
              data: data.fraud_counts,
              borderColor: '#f85149',
              backgroundColor: 'rgba(248, 81, 73, 0.15)',
              borderWidth: 2.5,
              pointRadius: 3,
              pointHoverRadius: 6,
              tension: 0.25,
              fill: true,
              yAxisID: 'y1'
            }
          ]
        },
        options: {
          interaction: {
            mode: 'index',
            intersect: false
          },
          scales: {
            x: {
              title: {
                display: true,
                text: 'Timeline (Hours)',
                color: '#8b949e',
                font: { size: 11 }
              },
              grid: { color: 'rgba(48, 54, 61, 0.4)' }
            },
            y: {
              type: 'linear',
              display: true,
              position: 'left',
              title: {
                display: true,
                text: 'Legitimate Tx Count',
                color: '#58a6ff',
                font: { size: 11 }
              },
              grid: { color: 'rgba(48, 54, 61, 0.4)' }
            },
            y1: {
              type: 'linear',
              display: true,
              position: 'right',
              title: {
                display: true,
                text: 'Fraud Incidents Count',
                color: '#f85149',
                font: { size: 11 }
              },
              grid: { drawOnChartArea: false } // Only draw grid for primary axis
            }
          }
        }
      });
    } catch (e) {
      console.warn('Time-series chart data error:', e);
    }
  }

  /**
   * 4. Load Amount Ranges Chart
   */
  async function loadAmountRangesChart() {
    try {
      const data = await App.api('/api/analytics/amount-ranges', { silent: true });
      if (!data || !data.ranges) return;

      App.createChart('chart-amount-ranges', {
        type: 'bar',
        data: {
          labels: data.ranges,
          datasets: [
            {
              label: 'Legitimate Transactions',
              data: data.legit_counts,
              backgroundColor: 'rgba(88, 166, 255, 0.65)',
              borderColor: '#58a6ff',
              borderWidth: 1,
              borderRadius: 4
            },
            {
              label: 'Fraudulent Transactions',
              data: data.fraud_counts,
              backgroundColor: 'rgba(248, 81, 73, 0.85)',
              borderColor: '#f85149',
              borderWidth: 1,
              borderRadius: 4
            }
          ]
        },
        options: {
          scales: {
            y: {
              type: 'logarithmic',
              title: {
                display: true,
                text: 'Transaction Volume (Log Scale)',
                color: '#8b949e',
                font: { size: 11 }
              },
              grid: { color: 'rgba(48, 54, 61, 0.4)' }
            },
            x: {
              title: {
                display: true,
                text: 'Amount Range (USD)',
                color: '#8b949e',
                font: { size: 11 }
              },
              grid: { color: 'rgba(48, 54, 61, 0.4)' }
            }
          }
        }
      });
    } catch (e) {
      console.warn('Amount ranges chart data error:', e);
    }
  }

  /**
   * 5. Load Statistical Comparison Table
   */
  async function loadStatsTable() {
    try {
      const data = await App.api('/api/analytics/stats', { silent: true });
      if (!data || !data.fraud_amount_stats || !data.legit_amount_stats) return;

      const f = data.fraud_amount_stats;
      const l = data.legit_amount_stats;

      const setText = (id, val, isCur = true) => {
        const el = document.getElementById(id);
        if (el) el.textContent = isCur ? App.formatCurrency(val) : val;
      };

      setText('stat-legit-mean', l.mean);
      setText('stat-fraud-mean', f.mean);
      setText('stat-legit-q50', l.q50);
      setText('stat-fraud-q50', f.q50);
      setText('stat-legit-std', l.std);
      setText('stat-fraud-std', f.std);
      setText('stat-legit-min', l.min);
      setText('stat-fraud-min', f.min);
      setText('stat-legit-max', l.max);
      setText('stat-fraud-max', f.max);
      setText('stat-legit-q75', l.q75);
      setText('stat-fraud-q75', f.q75);
    } catch (e) {
      console.warn('Stats table data error:', e);
    }
  }

  /**
   * 6. Check ML Models Trained Status
   */
  async function checkModelStatus() {
    try {
      const data = await App.api('/api/ml/metrics', { silent: true });
      if (trainingCtaSection) {
        if (!data || !data.model_trained) {
          trainingCtaSection.classList.remove('d-none');
        } else {
          trainingCtaSection.classList.add('d-none');
        }
      }
    } catch (e) {
      if (trainingCtaSection) trainingCtaSection.classList.remove('d-none');
    }
  }

  /**
   * 7. Upload Handler (File select & Drag/Drop)
   */
  function setupUploadHandlers() {
    if (!dropzone || !fileInput) return;

    if (browseBtn) {
      browseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
      });
    }

    dropzone.addEventListener('click', () => {
      fileInput.click();
    });

    // Drag-over styling
    ['dragenter', 'dragover'].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('drag-active');
      });
    });

    ['dragleave', 'drop'].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('drag-active');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        handleFileUpload(files[0]);
      }
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files.length > 0) {
        handleFileUpload(fileInput.files[0]);
      }
    });
  }

  async function handleFileUpload(file) {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      App.showToast('Please select a valid CSV file (creditcard.csv)', 'warning');
      return;
    }

    if (fileNameDisplay) {
      fileNameDisplay.textContent = `Selected: ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB)`;
      fileNameDisplay.classList.remove('d-none');
    }

    // Show progress bar
    if (progressWrap) progressWrap.classList.remove('d-none');
    if (progressBar) progressBar.style.width = '35%';
    if (progressPercent) progressPercent.textContent = 'Uploading...';
    if (progressText) progressText.textContent = `Streaming ${file.name} to server...`;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await App.api('/api/dataset/upload', {
        method: 'POST',
        body: formData
      });

      if (progressBar) progressBar.style.width = '100%';
      if (progressPercent) progressPercent.textContent = '100%';
      if (progressText) progressText.textContent = 'Dataset successfully ingested!';

      App.showToast(`Dataset loaded: ${App.formatNumber(res.row_count || 284807)} transactions processed!`, 'success');

      // Refresh overview, charts, and sidebar status
      setTimeout(async () => {
        if (progressWrap) progressWrap.classList.add('d-none');
        await App.checkDatasetStatus();
        await loadDashboard();
      }, 800);
    } catch (err) {
      if (progressBar) progressBar.style.width = '0%';
      if (progressText) progressText.textContent = 'Upload failed';
      App.showToast(err.message || 'Dataset upload failed', 'error');
    }
  }

  /**
   * Main Dashboard Initializer
   */
  async function loadDashboard() {
    const isLoaded = await loadOverview();
    // Load charts even if mock or partial data is available
    await Promise.allSettled([
      loadDistributionChart(),
      loadTimeSeriesChart(),
      loadAmountRangesChart(),
      loadStatsTable(),
      checkModelStatus()
    ]);
  }

  setupUploadHandlers();
  loadDashboard();
});
