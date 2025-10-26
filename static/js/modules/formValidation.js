export function initFormValidation() {
  const forms = document.querySelectorAll('form.needs-validation');
  if (!forms.length) {
    return;
  }

  forms.forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }

      form.classList.add('was-validated');
    });
  });
}

export default initFormValidation;
