function setCustomMessage(field, message) {
  if (!field) {
    return;
  }

  field.setCustomValidity(message);
  const feedback = field.closest('.mb-3')?.querySelector('.invalid-feedback');
  if (feedback) {
    feedback.textContent = message || feedback.dataset.defaultMessage || feedback.textContent;
  }
}

function resetMessage(field) {
  if (!field) {
    return;
  }

  field.setCustomValidity('');
  const feedback = field.closest('.mb-3')?.querySelector('.invalid-feedback');
  if (feedback && feedback.dataset.defaultMessage) {
    feedback.textContent = feedback.dataset.defaultMessage;
  }
}

export function initRegisterPage() {
  const occupationFieldWrapper = document.getElementById('occupation-field');
  if (!occupationFieldWrapper) {
    return;
  }

  const userTypeInputs = document.querySelectorAll('input[name="user_type"]');
  const occupationSelect = document.getElementById('occupation');
  const registerForm = document.getElementById('registerForm');
  const password1 = document.getElementById('password1');
  const password2 = document.getElementById('password2');
  const contactNumber = document.getElementById('contact_number');

  userTypeInputs.forEach((input) => {
    input.addEventListener('change', () => {
      const checked = document.querySelector('input[name="user_type"]:checked');
      const shouldShow = checked && checked.value === 'student';
      occupationFieldWrapper.style.display = shouldShow ? 'block' : 'none';
      if (!shouldShow && occupationSelect) {
        occupationSelect.value = '';
        resetMessage(occupationSelect);
      }
    });
  });

  const initialChecked = document.querySelector('input[name="user_type"]:checked');
  occupationFieldWrapper.style.display = initialChecked && initialChecked.value === 'student' ? 'block' : 'none';

  if (password1) {
    const feedback = password1.closest('.mb-3')?.querySelector('.invalid-feedback');
    if (feedback) {
      feedback.dataset.defaultMessage = feedback.textContent;
    }
    password1.addEventListener('input', () => {
      resetMessage(password1);
      if (password1.value.trim().length < 8) {
        setCustomMessage(password1, 'Password must contain at least 8 characters.');
      }
    });
  }

  if (password2) {
    const feedback = password2.closest('.mb-3')?.querySelector('.invalid-feedback');
    if (feedback) {
      feedback.dataset.defaultMessage = feedback.textContent;
    }
    password2.addEventListener('input', () => {
      resetMessage(password2);
      if (password1 && password2.value !== password1.value) {
        setCustomMessage(password2, 'Passwords must match.');
      }
    });
  }

  if (occupationSelect) {
    const feedback = occupationSelect.closest('.mb-3')?.querySelector('.invalid-feedback');
    if (feedback) {
      feedback.dataset.defaultMessage = feedback.textContent;
    }
    occupationSelect.addEventListener('change', () => {
      resetMessage(occupationSelect);
    });
  }

  if (contactNumber) {
    const feedback = contactNumber.closest('.mb-3')?.querySelector('.invalid-feedback');
    if (feedback) {
      feedback.dataset.defaultMessage = feedback.textContent;
    }

    const enforceDigits = () => {
      const digitsOnly = contactNumber.value.replace(/\D/g, '').slice(0, 10);
      if (contactNumber.value !== digitsOnly) {
        contactNumber.value = digitsOnly;
        const cursorPos = Math.min(digitsOnly.length, 10);
        window.requestAnimationFrame(() => {
          contactNumber.setSelectionRange(cursorPos, cursorPos);
        });
      }

      resetMessage(contactNumber);
      if (contactNumber.value && contactNumber.value.length !== 10) {
        setCustomMessage(contactNumber, 'Enter a valid 10-digit contact number.');
      }
    };

    contactNumber.addEventListener('input', enforceDigits);
    contactNumber.addEventListener('blur', () => {
      enforceDigits();
      if (contactNumber.value.length !== 10) {
        setCustomMessage(contactNumber, 'Enter a valid 10-digit contact number.');
      }
    });
  }

  if (registerForm) {
    const feedbackElements = registerForm.querySelectorAll('.invalid-feedback');
    feedbackElements.forEach((feedback) => {
      if (!feedback.dataset.defaultMessage) {
        feedback.dataset.defaultMessage = feedback.textContent;
      }
    });

    registerForm.addEventListener('submit', (event) => {
      let valid = true;

      if (password1 && password1.value.trim().length < 8) {
        setCustomMessage(password1, 'Password must contain at least 8 characters.');
        valid = false;
      }

      if (password1 && password2 && password1.value !== password2.value) {
        setCustomMessage(password2, 'Passwords must match.');
        valid = false;
      }

      const checked = document.querySelector('input[name="user_type"]:checked');
      const requiresOccupation = checked && checked.value === 'student';
      if (requiresOccupation && occupationSelect && !occupationSelect.value) {
        setCustomMessage(occupationSelect, 'Select your occupation.');
        valid = false;
      }

      if (contactNumber && contactNumber.value.length !== 10) {
        setCustomMessage(contactNumber, 'Enter a valid 10-digit contact number.');
        valid = false;
      }

      if (!valid) {
        event.preventDefault();
        event.stopPropagation();
        registerForm.classList.add('was-validated');
      }
    });
  }
}

export default initRegisterPage;
