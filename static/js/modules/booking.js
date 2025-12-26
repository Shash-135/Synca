export function initBookingForm() {
  const bookingForm = document.getElementById('bookingForm');
  if (!bookingForm) {
    return;
  }

  const checkInInput = bookingForm.querySelector('input[name="check_in"]');
  const checkOutInput = bookingForm.querySelector('input[name="check_out"]');

  const stayDaysValue = document.getElementById('stayDaysValue');
  const stayRentValue = document.getElementById('stayRentValue');
  const estimatedTotalValue = document.getElementById('estimatedTotalValue');
  const dailyRentValue = document.getElementById('dailyRentValue');

  const parseNumber = (value) => {
    if (value === null || value === undefined) {
      return 0;
    }
    const parsed = Number(String(value));
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const dailyRent = parseNumber(bookingForm.dataset.dailyRent);
  const depositApplicable = String(bookingForm.dataset.depositApplicable) === 'true';
  const securityDeposit = depositApplicable ? parseNumber(bookingForm.dataset.securityDeposit) : 0;
  const lockInMonths = parseInt(bookingForm.dataset.lockInMonths || '0', 10) || 0;

  const formatCurrency = (amount) => {
    if (!Number.isFinite(amount)) {
      return '—';
    }
    // Keep it simple (no new UI): show as rounded rupees.
    return Math.round(amount).toLocaleString('en-IN');
  };

  const addMonths = (isoDate, months) => {
    // isoDate: YYYY-MM-DD
    const parts = (isoDate || '').split('-').map((p) => parseInt(p, 10));
    if (parts.length !== 3 || parts.some((n) => !Number.isFinite(n))) {
      return null;
    }
    const [year, month, day] = parts;
    const base = new Date(Date.UTC(year, month - 1, day));
    if (Number.isNaN(base.getTime())) {
      return null;
    }
    const targetMonthIndex = (month - 1) + months;
    const targetYear = year + Math.floor(targetMonthIndex / 12);
    const targetMonth = (targetMonthIndex % 12 + 12) % 12;

    // Clamp the day to last day of target month.
    const lastDay = new Date(Date.UTC(targetYear, targetMonth + 1, 0)).getUTCDate();
    const clampedDay = Math.min(day, lastDay);
    const out = new Date(Date.UTC(targetYear, targetMonth, clampedDay));
    return out.toISOString().slice(0, 10);
  };

  const recalc = () => {
    const checkIn = checkInInput?.value;
    const checkOut = checkOutInput?.value;
    if (!checkInInput || !checkOutInput || !checkIn || !checkOut) {
      return;
    }

    // Enforce lock-in minimum on the client (server still validates).
    if (lockInMonths > 0) {
      const minCheckout = addMonths(checkIn, lockInMonths);
      if (minCheckout) {
        checkOutInput.min = minCheckout;
        if (checkOut < minCheckout) {
          checkOutInput.value = minCheckout;
        }
      }
    }

    const inDate = new Date(`${checkIn}T00:00:00`);
    const outDate = new Date(`${checkOutInput.value}T00:00:00`);
    if (Number.isNaN(inDate.getTime()) || Number.isNaN(outDate.getTime())) {
      return;
    }

    const diffMs = outDate.getTime() - inDate.getTime();
    const days = Math.floor(diffMs / (24 * 60 * 60 * 1000));

    if (stayDaysValue) {
      stayDaysValue.textContent = days > 0 ? `${days} day${days === 1 ? '' : 's'}` : '—';
    }

    const stayRent = days > 0 ? dailyRent * days : NaN;
    if (stayRentValue) {
      stayRentValue.textContent = days > 0 ? formatCurrency(stayRent) : '—';
    }

    const estimatedTotal = days > 0 ? stayRent + securityDeposit : NaN;
    if (estimatedTotalValue) {
      estimatedTotalValue.textContent = days > 0 ? formatCurrency(estimatedTotal) : '—';
    }
  };

  // If server-rendered daily rent is present, keep it stable.
  if (dailyRentValue && dailyRent) {
    dailyRentValue.textContent = String(parseNumber(dailyRent)).toFixed(2);
  }

  if (checkInInput && checkOutInput) {
    checkInInput.addEventListener('change', recalc);
    checkOutInput.addEventListener('change', recalc);
    recalc();
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
