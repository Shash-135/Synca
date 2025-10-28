const ALERT_LEVELS = {
  success: 'success',
  error: 'danger',
  warning: 'warning',
  info: 'info',
};

function getAlertContainer() {
  let container = document.getElementById('app-alert-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'app-alert-container';
    container.className = 'position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1080';
    container.setAttribute('aria-live', 'polite');
    container.setAttribute('aria-atomic', 'true');
    document.body.appendChild(container);
  }
  return container;
}

export function showAlert(message, level = 'info', options = {}) {
  const variant = ALERT_LEVELS[level] || ALERT_LEVELS.info;
  const { autoHide = true, delay = 4000 } = options;
  const container = getAlertContainer();

  const alertEl = document.createElement('div');
  alertEl.className = `alert alert-${variant} alert-dismissible fade show shadow`;
  alertEl.setAttribute('role', 'alert');
  alertEl.innerHTML = message;

  const closeBtn = document.createElement('button');
  closeBtn.type = 'button';
  closeBtn.className = 'btn-close';
  closeBtn.setAttribute('data-bs-dismiss', 'alert');
  closeBtn.setAttribute('aria-label', 'Close alert');
  alertEl.appendChild(closeBtn);

  container.appendChild(alertEl);

  if (autoHide) {
    window.setTimeout(() => {
      const instance = window.bootstrap?.Alert.getOrCreateInstance(alertEl);
      instance?.close();
    }, delay);
  }

  return alertEl;
}

export function initAlertBridge() {
  if (typeof window !== 'undefined' && !window.showAlert) {
    window.showAlert = showAlert;
  }
}

initAlertBridge();
