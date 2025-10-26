function togglePasswordVisibility(button) {
  const targetSelector = button.getAttribute('data-target');
  if (!targetSelector) {
    return;
  }

  const input = document.querySelector(targetSelector);
  if (!input) {
    return;
  }

  const isPassword = input.type === 'password';
  input.type = isPassword ? 'text' : 'password';

  const icon = button.querySelector('i');
  if (icon) {
    icon.classList.toggle('bi-eye', isPassword);
    icon.classList.toggle('bi-eye-slash', !isPassword);
  }

  button.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
}

export function initPasswordToggles() {
  const buttons = document.querySelectorAll('.toggle-password');
  if (!buttons.length) {
    return;
  }

  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      togglePasswordVisibility(button);
    });
  });
}

export default initPasswordToggles;
