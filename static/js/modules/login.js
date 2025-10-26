export function initLoginFormValidation() {
  const form = document.getElementById('loginForm');
  if (!form) {
    return;
  }

  const usernameInput = form.querySelector('#username');
  const passwordInput = form.querySelector('#password');

  const trimInput = (input) => {
    if (!input) {
      return;
    }
    input.value = input.value.trimStart();
  };

  if (usernameInput) {
    usernameInput.addEventListener('blur', () => {
      usernameInput.value = usernameInput.value.trim();
    });
  }

  if (passwordInput) {
    passwordInput.addEventListener('input', () => {
      passwordInput.setCustomValidity('');
    });
  }

  form.addEventListener('submit', () => {
    trimInput(usernameInput);
  });
}

export default initLoginFormValidation;
