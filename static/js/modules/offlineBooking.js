const NAME_MIN_LENGTH = 2;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CONTACT_PATTERN = /^[0-9+\-\s()]{7,15}$/;
const MAX_AGE = 120;

function sanitizeTrim(value) {
  return typeof value === 'string' ? value.trim() : value;
}

function configureField(form, input, validator, { sanitizeOnBlur = null } = {}) {
  if (!form || !input) {
    return () => {};
  }

  const feedback = form.querySelector(
    `.invalid-feedback[data-feedback-for="${input.name}"]`
  );
  const defaultMessage = feedback?.dataset?.default?.trim() || feedback?.textContent?.trim() || '';

  const runValidation = (shouldSanitize = false) => {
    if (shouldSanitize && typeof sanitizeOnBlur === 'function') {
      const sanitized = sanitizeOnBlur(input.value);
      if (typeof sanitized === 'string') {
        input.value = sanitized;
      }
    }

    const message = typeof validator === 'function' ? validator(input) : '';
    input.setCustomValidity(message || '');

    if (feedback) {
      feedback.textContent = message || defaultMessage;
    }
  };

  input.addEventListener('input', () => runValidation(false));
  input.addEventListener('blur', () => runValidation(true));

  runValidation(false);
  return () => runValidation(true);
}

function validateName(label) {
  return (input) => {
    const value = sanitizeTrim(input.value);
    if (!value) {
      return `Please enter the ${label}.`;
    }
    if (value.length < NAME_MIN_LENGTH) {
      return `${label.charAt(0).toUpperCase() + label.slice(1)} must be at least ${NAME_MIN_LENGTH} characters.`;
    }
    return '';
  };
}

function validateEmail(input) {
  const value = sanitizeTrim(input.value);
  if (!value) {
    return 'Please enter the email address.';
  }
  if (!EMAIL_PATTERN.test(value)) {
    return 'Enter a valid email address (e.g., tenant@example.com).';
  }
  return '';
}

function validateAge(input) {
  const rawValue = sanitizeTrim(input.value);
  if (!rawValue) {
    return '';
  }
  const age = Number(rawValue);
  if (!Number.isFinite(age)) {
    return 'Enter a valid age.';
  }
  if (age < 0) {
    return 'Age cannot be negative.';
  }
  if (age > MAX_AGE) {
    return `Age must be ${MAX_AGE} or less.`;
  }
  return '';
}

function validateContact(input) {
  const value = sanitizeTrim(input.value);
  if (!value) {
    return '';
  }
  if (!CONTACT_PATTERN.test(value)) {
    return 'Enter 7-15 digits; you may include +, -, spaces, or parentheses.';
  }
  const digits = value.replace(/\D/g, '');
  if (digits.length < 7) {
    return 'Enter at least 7 numerical digits.';
  }
  return '';
}

function validateSelect(label) {
  return (input) => {
    const value = sanitizeTrim(input.value);
    if (!value) {
      return `Please select the ${label}.`;
    }
    return '';
  };
}

export function initOfflineBookingValidation() {
  const form = document.getElementById('offlineBookingForm');
  if (!form) {
    return;
  }

  const validators = [];

  validators.push(
    configureField(form, form.querySelector('[name="bed"]'), validateSelect('bed'))
  );

  validators.push(
    configureField(form, form.querySelector('[name="first_name"]'), validateName('first name'), {
      sanitizeOnBlur: sanitizeTrim,
    })
  );

  validators.push(
    configureField(form, form.querySelector('[name="last_name"]'), validateName('last name'), {
      sanitizeOnBlur: sanitizeTrim,
    })
  );

  validators.push(
    configureField(form, form.querySelector('[name="email"]'), validateEmail, {
      sanitizeOnBlur: sanitizeTrim,
    })
  );

  validators.push(
    configureField(form, form.querySelector('[name="age"]'), validateAge)
  );

  validators.push(
    configureField(form, form.querySelector('[name="contact_number"]'), validateContact, {
      sanitizeOnBlur: sanitizeTrim,
    })
  );

  form.addEventListener('submit', () => {
    validators.forEach((run) => run());
  });
}

export default initOfflineBookingValidation;
