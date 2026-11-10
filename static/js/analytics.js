/**
 * FraudGuard AI - Transaction Analytics Controller
 * Handles Amount Distribution, Hourly Fraud Timeline, Custom HTML Correlation Heatmap,
 * Statistical Summary Cards, and Class Imbalance Breakdown.
 */

document.addEventListener('DOMContentLoaded', () => {
  'use strict';

  const refreshBtn = document.getElementById('analytics-refresh-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      App.showToast('Refreshing transaction analytics...', 'info');
      loadAnalytics();
    });
  }

  /**
   * 1. Amount Distribution Chart
   */
  async function loadAmountDistributionChart() {
    try {
      const data = await App.api('/api/analytics/amount-ranges', { silent: true });
      if (!data || !data.ranges) return;

      App.createChart('chart-analytics-amounts', {
        type: 'bar',
        data: {
          labels: data.ranges,
          datasets: [
            {
              label: 'Legitimate Count',
              data: data.legit_counts,
              backgroundColor: 'rgba(88, 166, 255, 0.7)',
              borderColor: '#58a6ff',
              borderWidth: 1,
              borderRadius: 4
            },
            {
              label: 'Fraudulent Count',
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
                text: 'Frequency (Logarithmic Scale)',
                color: '#8b949e',
                font: { size: 11 }
              },
              grid: { color: 'rgba(48, 54, 61, 0.4)' }
            },
            x: {
              title: {
                display: true,
                text: 'Transaction Amount Range ($)',
                color: '#8b949e',
                font: { size: 11 }
              },
              grid: { color: 'rgba(48, 54, 61, 0.4)' }
            }
          }
        }
      });
    } catch (e) {
      console.warn('Analytics amount chart error:', e);
    }
  }

  /**
   * 2. Hourly Fraud Rate Bar Chart
   */
  async function loadHourlyFraudChart() {
    try {
      const data = await App.api('/api/analytics/time-series', { silent: true });
      if (!data || !data.bin_labels) return;

      // Use the first 24-48 bins
      const labels = data.bin_labels.slice(0, 24);
      const counts = data.fraud_counts.slice(0, 24);

      App.createChart('chart-hourly-fraud', {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Fraud Incident Count',
              data: counts,
              backgroundColor: 'rgba(248, 81, 73, 0.8)',
              borderColor: '#f85149',
              borderWidth: 1,
              borderRadius: 4
            }
          ]
        },
        options: {
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: 'Fraud Count',
                color: '#f85149',
                font: { size: 11 }
              },
              grid: { color: 'rgba(48, 54, 61, 0.4)' }
            },
            x: {
              title: {
                display: true,
                text: 'Hourly Timeline Intervals (0h - 24h)',
                color: '#8b949e',
                font: { size: 11 }
              },
              grid: { color: 'rgba(48, 54, 61, 0.4)' }
            }
          }
        }
      });
    } catch (e) {
      console.warn('Hourly fraud chart error:', e);
    }
  }

  /**
   * 3. Custom HTML Correlation Heatmap Table
   */
  async function loadCorrelationHeatmap() {
    const container = document.getElementById('correlation-table-container');
    if (!container) return;

    try {
      const data = await App.api('/api/analytics/correlation', { silent: true });
      if (!data || !data.features || !data.matrix) {
        container.innerHTML = `
          <div class="p-4 text-center text-muted-custom">
            Correlation matrix currently unavailable. Upload dataset to calculate feature correlations.
          </div>
        `;
        return;
      }

      const features = data.features;
      const matrix = data.matrix;

      // Build HTML Table
      let tableHtml = `
        <table class="table table-dark table-borderless text-center align-middle mb-0" style="font-size: 11px; white-space: nowrap;">
          <thead>
            <tr>
              <th class="p-2 text-start text-secondary-custom" style="position: sticky; left: 0; background: var(--bg-surface); z-index: 2;">Feature</th>
      `;

      // Header columns
      features.forEach((feat) => {
        tableHtml += `<th class="p-2 text-secondary-custom fw-bold" style="min-width: 48px;">${feat}</th>`;
      });
      tableHtml += `</tr></thead><tbody>`;

      // Matrix rows
      matrix.forEach((row, i) => {
        const rowFeature = features[i] || `V${i + 1}`;
        tableHtml += `
          <tr>
            <td class="p-2 text-start fw-bold text-accent-blue" style="position: sticky; left: 0; background: var(--bg-surface); z-index: 1;">${rowFeature}</td>
        `;

        row.forEach((val) => {
          const num = typeof val === 'number' ? val : parseFloat(val);
          const clamped = Math.max(-1, Math.min(1, num));
          const formatted = clamped.toFixed(2);

          // Calculate background color based on correlation:
          // Positive -> Blue rgba(88, 166, 255, alpha)
          // Negative -> Red rgba(248, 81, 73, alpha)
          let bgColor = '#21262d';
          let textColor = '#e6edf3';
          const absVal = Math.abs(clamped);

          if (clamped > 0.05) {
            const alpha = (absVal * 0.75 + 0.15).toFixed(2);
            bgColor = `rgba(88, 166, 255, ${alpha})`;
          } else if (clamped < -0.05) {
            const alpha = (absVal * 0.75 + 0.15).toFixed(2);
            bgColor = `rgba(248, 81, 73, ${alpha})`;
          }

          tableHtml += `
            <td class="p-2" style="background-color: ${bgColor}; color: ${textColor}; border: 1px solid #161b22; transition: transform 0.15s ease;" title="${rowFeature} &harr; corr: ${formatted}">
              ${formatted}
            </td>
          `;
        });

        tableHtml += `</tr>`;
      });

      tableHtml += `</tbody></table>`;
      container.innerHTML = tableHtml;
    } catch (e) {
      console.warn('Correlation heatmap error:', e);
      container.innerHTML = `
        <div class="p-4 text-center text-muted-custom">
          Failed to load correlation matrix. Please ensure dataset is loaded.
        </div>
      `;
    }
  }

  /**
   * 4. Statistical Summary Cards (Fraud vs Legit)
   */
  async function loadStatCards() {
    try {
      const data = await App.api('/api/analytics/stats', { silent: true });
      if (!data || !data.fraud_amount_stats || !data.legit_amount_stats) return;

      const f = data.fraud_amount_stats;
      const l = data.legit_amount_stats;

      // Fraud Stats
      const setF = (id, val, isCur = true) => {
        const el = document.getElementById(id);
        if (el) el.textContent = isCur ? App.formatCurrency(val) : val;
      };

      setF('f-stat-mean', f.mean);
      setF('f-stat-std', f.std);
      setF('f-stat-q50', f.q50);
      setF('f-stat-min', f.min);
      setF('f-stat-max', f.max);
      setF('f-stat-q25', f.q25);
      setF('f-stat-q75', f.q75);

      const fIqr = document.getElementById('f-stat-iqr');
      if (fIqr && f.q75 !== undefined && f.q25 !== undefined) {
        fIqr.textContent = App.formatCurrency(f.q75 - f.q25);
      }

      // Legit Stats
      const setL = (id, val, isCur = true) => {
        const el = document.getElementById(id);
        if (el) el.textContent = isCur ? App.formatCurrency(val) : val;
      };

      setL('l-stat-mean', l.mean);
      setL('l-stat-std', l.std);
      setL('l-stat-q50', l.q50);
      setL('l-stat-min', l.min);
      setL('l-stat-max', l.max);
      setL('l-stat-q25', l.q25);
      setL('l-stat-q75', l.q75);

      const lIqr = document.getElementById('l-stat-iqr');
      if (lIqr && l.q75 !== undefined && l.q25 !== undefined) {
        lIqr.textContent = App.formatCurrency(l.q75 - l.q25);
      }
    } catch (e) {
      console.warn('Stat cards loading error:', e);
    }
  }

  function loadAnalytics() {
    loadAmountDistributionChart();
    loadHourlyFraudChart();
    loadCorrelationHeatmap();
    loadStatCards();
  }

  loadAnalytics();
});
