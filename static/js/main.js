(function () {
  const body = document.body;

  function getCookie(name) {
    const cookies = document.cookie ? document.cookie.split(';') : [];
    for (let i = 0; i < cookies.length; i += 1) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith(name + '=')) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return null;
  }

  function setupRegisterPage() {
    const occupationField = document.getElementById('occupation-field');
    if (!occupationField) {
      return;
    }

    const userTypeInputs = document.querySelectorAll('input[name="user_type"]');
    if (!userTypeInputs.length) {
      return;
    }

    function toggleOccupationField() {
      const checked = document.querySelector('input[name="user_type"]:checked');
      if (checked && checked.value === 'student') {
        occupationField.style.display = 'block';
      } else {
        occupationField.style.display = 'none';
      }
    }

    toggleOccupationField();
    userTypeInputs.forEach(function (input) {
      input.addEventListener('change', toggleOccupationField);
    });
  }

  function setupBookingForm() {
    const bookingForm = document.getElementById('bookingForm');
    if (!bookingForm) {
      return;
    }

    bookingForm.addEventListener('submit', function () {
      const confirmBtn = document.getElementById('confirmBtn');
      const spinner = document.getElementById('spinner');
      const btnText = document.getElementById('btnText');

      if (confirmBtn) {
        confirmBtn.disabled = true;
      }
      if (spinner) {
        spinner.classList.remove('d-none');
      }
      if (btnText) {
        btnText.textContent = ' Processing...';
      }
    });
  }

  function setupBedToggle() {
    const toggles = document.querySelectorAll('.bed-toggle');
    if (!toggles.length) {
      return;
    }

    const csrftoken = getCookie('csrftoken');

    toggles.forEach(function (toggle) {
      toggle.addEventListener('change', function () {
        const bedId = toggle.getAttribute('data-bed-id');
        const isAvailable = toggle.checked;

        if (!bedId) {
          return;
        }

        fetch(`/api/beds/${bedId}/toggle/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken || '',
          },
          body: JSON.stringify({ is_available: isAvailable }),
        })
          .then(function (response) {
            return response.json();
          })
          .then(function (data) {
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
              alert('Bed availability updated successfully!');
            } else {
              alert((data && data.error) || 'Failed to update bed availability');
              toggle.checked = !isAvailable;
            }
          })
          .catch(function (error) {
            console.error('Error updating bed availability', error);
            alert('Failed to update bed availability');
            toggle.checked = !isAvailable;
          });
      });
    });
  }

  function setupPgDetailBeds() {
    const pgDetail = document.getElementById('pgDetail');
    if (!pgDetail) {
      return;
    }

    const beds = pgDetail.querySelectorAll('.bed-available');
    if (!beds.length) {
      return;
    }

    const isAuthenticated = pgDetail.dataset.userAuth === 'true';
    const userType = (body && body.dataset.userType) || '';
    const loginUrl = pgDetail.dataset.loginUrl || '/login/';

    if (!isAuthenticated) {
      beds.forEach(function (bed) {
        bed.addEventListener('click', function (event) {
          event.preventDefault();
          alert('Please login to book a bed');
          window.location.href = loginUrl;
        });
      });
      return;
    }

    if (userType !== 'student') {
      beds.forEach(function (bed) {
        bed.addEventListener('click', function (event) {
          event.preventDefault();
          alert('Only students can book beds online');
        });
      });
    }
  }

  function setupSplash() {
    const splashContainer = document.getElementById('splashContainer');
    if (!splashContainer) {
      return;
    }

    const redirectUrl = splashContainer.dataset.redirectUrl || '/home/';

    setTimeout(function () {
      splashContainer.classList.add('fade-out');
      setTimeout(function () {
        window.location.href = redirectUrl;
      }, 500);
    }, 3000);
  }

  function onDomReady() {
    setupRegisterPage();
    setupBookingForm();
    setupBedToggle();
    setupPgDetailBeds();
    setupSplash();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onDomReady);
  } else {
    onDomReady();
  }
})();
