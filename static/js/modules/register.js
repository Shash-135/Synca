export function initRegisterPage() {
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
    occupationField.style.display = checked && checked.value === 'student' ? 'block' : 'none';
  }

  toggleOccupationField();
  userTypeInputs.forEach((input) => {
    input.addEventListener('change', toggleOccupationField);
  });
}

export default initRegisterPage;
