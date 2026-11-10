/**
 * FraudGuard AI - Core Application Utilities
 * Global namespace: window.App
 */

(function (window, document) {
  'use strict';

  const App = window.App || {};

  // Config reference
  const CONFIG = window.CONFIG || {
    API_BASE: '',
    CHART_COLORS: {
      blue: '#58a6ff',
      cyan: '#39d5ff',
      green: '#3fb950',
      red: '#f85149',
      orange: '#e3b341',
      purple: '#bc8cff',
      textPrimary: '#e6edf3',
      textSecondary: '#8b949e',
      gridColor: '#30363d',
      surface: '#161b22',
      elevated: '#21262d'
    }
  };

  /**
   * 1. App.api - Robust fetch wrapper
   * @param {string} endpoint - API path e.g. '/api/analytics/overview'
   * @param {object} options - Fetch options
   * @returns {Promise<any>} - Parsed JSON response
   */
  App.api = async function (endpoint, options = {}) {
    const url = (CONFIG.API_BASE || '') + endpoint;
    const fetchOptions = {
      ...options,
      headers: { ...options.headers }
    };

    // If body is NOT FormData, set application/json
    if (!(options.body instanceof FormData)) {
      if (!fetchOptions.headers['Content-Type'] && !fetchOptions.headers['content-type']) {
        fetchOptions.headers['Content-Type'] = 'application/json';
      }
    }

    try {
      const response = await fetch(url, fetchOptions);
      let data = null;
      const contentType = response.headers.get('content-type') || '';

      if (contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        const errorMsg = (data && data.message) || (data && data.error) || `Request failed with status ${response.status}`;
        throw new Error(errorMsg);
      }

      return data;
    } catch (err) {
      console.error(`[App.api] Error fetching ${url}:`, err);
      // Suppress noisy toast for 404/overview when dataset hasn't been uploaded yet
      if (!options.silent) {
        App.showToast(err.message || 'Network communication error', 'error');
      }
      throw err;
    }
  };

  /**
   * 2. App.formatCurrency - Formats numerical values to USD ($12,345.67)
   */
  App.formatCurrency = function (val) {
    if (val === undefined || val === null || isNaN(val)) return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(val);
  };

  /**
   * 3. App.formatNumber - Format with commas (284,807)
   */
  App.formatNumber = function (val) {
    if (val === undefined || val === null || isNaN(val)) return '0';
    return new Intl.NumberFormat('en-US').format(val);
  };

  /**
   * 4. App.formatPercent - Format percentage (0.172%)
   */
  App.formatPercent = function (val, decimals = 3) {
    if (val === undefined || val === null || isNaN(val)) return '0.000%';
    const num = typeof val === 'number' ? val : parseFloat(val);
    // If given as ratio <= 1, convert to % unless it already looks like a percent
    const displayNum = num <= 1 && num > 0 ? num * 100 : num;
    return `${displayNum.toFixed(decimals)}%`;
  };

  /**
   * 5. App.formatDate - Format ISO date string into readable representation
   */
  App.formatDate = function (isoString) {
    if (!isoString) return 'Just now';
    try {
      const date = new Date(isoString);
      if (isNaN(date.getTime())) return isoString;
      return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }).format(date);
    } catch (e) {
      return isoString;
    }
  };

  /**
   * 6. App.showToast - Floating toast notifications
   * @param {string} message
   * @param {'success'|'error'|'info'|'warning'} type
   * @param {number} duration - ms
   */
  App.showToast = function (message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast-item';

    let iconClass = 'bi-info-circle-fill text-accent-blue';
    let borderColor = 'var(--accent-blue)';

    if (type === 'success') {
      iconClass = 'bi-check-circle-fill text-accent-green';
      borderColor = 'var(--accent-green)';
    } else if (type === 'error' || type === 'danger') {
      iconClass = 'bi-exclamation-triangle-fill text-accent-red';
      borderColor = 'var(--accent-red)';
    } else if (type === 'warning') {
      iconClass = 'bi-shield-exclamation text-accent-orange';
      borderColor = 'var(--accent-orange)';
    }

    toast.style.borderLeft = `4px solid ${borderColor}`;

    toast.innerHTML = `
      <i class="bi ${iconClass} fs-5"></i>
      <div class="flex-grow-1 text-xs" style="line-height: 1.4;">${message}</div>
      <button type="button" class="btn-close btn-close-white" style="font-size: 10px;" aria-label="Close"></button>
    `;

    const closeBtn = toast.querySelector('.btn-close');
    closeBtn.addEventListener('click', () => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(50px)';
      setTimeout(() => toast.remove(), 250);
    });

    container.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => {
        if (toast.parentElement) {
          toast.style.opacity = '0';
          toast.style.transform = 'translateX(50px)';
          setTimeout(() => toast.remove(), 250);
        }
      }, duration);
    }
  };

  /**
   * 7. App.showLoading - Injects skeleton placeholders into a container
   */
  App.showLoading = function (containerId, rows = 3) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let html = '<div class="p-3 w-100">';
    for (let i = 0; i < rows; i++) {
      html += `
        <div class="skeleton skeleton-title mb-2"></div>
        <div class="skeleton skeleton-text mb-3" style="width: ${85 - i * 15}%;"></div>
      `;
    }
    html += '</div>';
    container.innerHTML = html;
  };

  /**
   * 8. App.showError - Injects formatted error message into container
   */
  App.showError = function (containerId, message) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = `
      <div class="alert-custom alert-custom-danger m-3">
        <i class="bi bi-exclamation-octagon-fill alert-icon fs-5"></i>
        <div>
          <div class="fw-semibold text-accent-red mb-1">Error Loading Data</div>
          <div class="text-xs text-secondary-custom">${message}</div>
        </div>
      </div>
    `;
  };

  /**
   * 9. App.CHART_DEFAULTS - Global Chart.js default styling for dark mode
   */
  App.CHART_DEFAULTS = {
    responsive: true,
    maintainAspectRatio: false,
    color: CONFIG.CHART_COLORS.textSecondary,
    font: {
      family: 'Inter',
      size: 12
    },
    plugins: {
      legend: {
        labels: {
          color: CONFIG.CHART_COLORS.textPrimary,
          font: { family: 'Inter', size: 12 },
          boxWidth: 12,
          boxHeight: 12,
          usePointStyle: true,
          padding: 16
        }
      },
      tooltip: {
        backgroundColor: CONFIG.CHART_COLORS.elevated,
        titleColor: CONFIG.CHART_COLORS.textPrimary,
        bodyColor: CONFIG.CHART_COLORS.textSecondary,
        borderColor: CONFIG.CHART_COLORS.gridColor,
        borderWidth: 1,
        padding: 12,
        cornerRadius: 6,
        bodyFont: { family: 'Inter', size: 12 },
        titleFont: { family: 'Inter', size: 12, weight: 'bold' }
      }
    },
    scales: {
      x: {
        grid: { color: 'rgba(48, 54, 61, 0.4)', drawBorder: false },
        ticks: { color: CONFIG.CHART_COLORS.textSecondary, font: { family: 'Inter', size: 11 } }
      },
      y: {
        grid: { color: 'rgba(48, 54, 61, 0.4)', drawBorder: false },
        ticks: { color: CONFIG.CHART_COLORS.textSecondary, font: { family: 'Inter', size: 11 } }
      }
    }
  };

  // Registry of active charts to prevent canvas re-use crashes
  const activeCharts = new Map();

  /**
   * 10. App.createChart - Safe Chart.js instance creator with dark theme defaults
   */
  App.createChart = function (ctxOrId, config) {
    if (typeof Chart === 'undefined') {
      console.error('Chart.js not loaded!');
      return null;
    }

    const canvas = typeof ctxOrId === 'string' ? document.getElementById(ctxOrId) : ctxOrId;
    if (!canvas) {
      console.warn(`[App.createChart] Canvas not found:`, ctxOrId);
      return null;
    }

    // Destroy existing chart on this canvas if one exists
    if (activeCharts.has(canvas)) {
      try {
        activeCharts.get(canvas).destroy();
      } catch (e) {
        console.warn('Error destroying chart:', e);
      }
      activeCharts.delete(canvas);
    }

    // Deep merge defaults
    const mergedConfig = {
      type: config.type || 'line',
      data: config.data || { labels: [], datasets: [] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        ...App.CHART_DEFAULTS,
        ...(config.options || {}),
        plugins: {
          ...App.CHART_DEFAULTS.plugins,
          ...(config.options?.plugins || {})
        }
      }
    };

    // If chart type is pie/doughnut/polar, remove x/y scales by default
    if (['pie', 'doughnut', 'polarArea'].includes(mergedConfig.type)) {
      if (!config.options?.scales) {
        delete mergedConfig.options.scales;
      }
    }

    const newChart = new Chart(canvas, mergedConfig);
    activeCharts.set(canvas, newChart);
    return newChart;
  };

  /**
   * 11. Dataset status check on every page load
   */
  App.checkDatasetStatus = async function () {
    const statusDot = document.getElementById('sidebar-status-dot');
    const statusText = document.getElementById('sidebar-status-text');
    const statusMeta = document.getElementById('sidebar-dataset-meta');

    if (!statusDot || !statusText) return null;

    try {
      const data = await App.api('/api/analytics/overview', { silent: true });

      if (data && data.dataset_loaded) {
        statusDot.className = 'status-dot dot-green';
        statusText.innerHTML = `<span class="text-accent-green fw-semibold">Loaded</span> <span class="text-muted-custom">(${App.formatNumber(data.total_transactions)} tx)</span>`;
        if (statusMeta) {
          statusMeta.textContent = `${data.dataset_name || 'creditcard.csv'}`;
        }
        return data;
      } else {
        statusDot.className = 'status-dot dot-red';
        statusText.innerHTML = '<span class="text-accent-red">Not Loaded</span>';
        if (statusMeta) {
          statusMeta.textContent = 'Upload required';
        }
        return { dataset_loaded: false };
      }
    } catch (e) {
      statusDot.className = 'status-dot dot-red';
      statusText.innerHTML = '<span class="text-accent-red">Offline</span>';
      return { dataset_loaded: false };
    }
  };

  /**
   * 12. Global UI Initialization
   */
  document.addEventListener('DOMContentLoaded', () => {
    // Check dataset status
    App.checkDatasetStatus();

    // Mobile sidebar toggle handler
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('app-sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');

    if (sidebarToggle && sidebar && backdrop) {
      const toggleSidebar = () => {
        const isShow = sidebar.classList.toggle('show');
        backdrop.style.display = isShow ? 'block' : 'none';
      };

      sidebarToggle.addEventListener('click', toggleSidebar);
      backdrop.addEventListener('click', toggleSidebar);
    }
  });

  window.App = App;
})(window, document);
