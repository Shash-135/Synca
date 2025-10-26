export function initBookingForm() {
  const bookingForm = document.getElementById('bookingForm');
  if (!bookingForm) {
    return;
  }

  bookingForm.addEventListener('submit', () => {
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

export default initBookingForm;
