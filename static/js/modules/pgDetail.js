import { showAlert } from './alerts.js';

export function initPgDetailBeds() {
  const pgDetail = document.getElementById('pgDetail');
  if (!pgDetail) {
    return;
  }

  const beds = pgDetail.querySelectorAll('.bed-available');
  if (!beds.length) {
    return;
  }

  const isAuthenticated = pgDetail.dataset.userAuth === 'true';
  const userType = document.body.dataset.userType || '';
  const loginUrl = pgDetail.dataset.loginUrl || '/login/';

  if (!isAuthenticated) {
    beds.forEach((bed) => {
      bed.addEventListener('click', (event) => {
        event.preventDefault();
        showAlert('Please login to book a bed', 'warning');
        window.setTimeout(() => {
          window.location.href = loginUrl;
        }, 1500);
      });
    });
    return;
  }

  if (userType !== 'student') {
    beds.forEach((bed) => {
      bed.addEventListener('click', (event) => {
        event.preventDefault();
        showAlert('Only students can book beds online', 'warning');
      });
    });
  }
}

export default initPgDetailBeds;
