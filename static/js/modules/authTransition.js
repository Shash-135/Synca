export function initAuthTransition() {
  const card = document.querySelector('.auth-card');
  if (!card) {
    return;
  }

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (prefersReducedMotion) {
    card.classList.add('is-ready');
    return;
  }

  window.requestAnimationFrame(() => {
    card.classList.add('is-ready');
  });
}

export default initAuthTransition;
