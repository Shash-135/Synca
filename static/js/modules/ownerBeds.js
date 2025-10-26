import { showAlert } from './alerts.js';
import { getCookie } from './utils.js';

export function initOwnerBedToggle() {
  const toggles = document.querySelectorAll('.bed-toggle');
  if (!toggles.length) {
    return;
  }

  const csrftoken = getCookie('csrftoken') || '';

  toggles.forEach((toggle) => {
    toggle.addEventListener('change', () => {
      const bedId = toggle.getAttribute('data-bed-id');
      const isAvailable = toggle.checked;

      if (!bedId) {
        return;
      }

      fetch(`/api/beds/${bedId}/toggle/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({ is_available: isAvailable }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            const card = toggle.closest('.card');
            if (card) {
              const icon = card.querySelector('i');
              const statusText = card.querySelector('.bed-status-text');

              if (icon) {
                icon.className = isAvailable
                  ? 'bi bi-door-open text-success fs-3 mb-2'
                  : 'bi bi-door-closed text-muted fs-3 mb-2';
              }

              if (statusText) {
                statusText.textContent = isAvailable ? 'Available' : 'Occupied';
              }
            }

            showAlert('Bed availability updated successfully!', 'success');
          } else {
            showAlert((data && data.error) || 'Failed to update bed availability', 'error');
            toggle.checked = !isAvailable;
          }
        })
        .catch((error) => {
          console.error('Error updating bed availability', error);
          showAlert('Failed to update bed availability', 'error');
          toggle.checked = !isAvailable;
        });
    });
  });
}

export default initOwnerBedToggle;
