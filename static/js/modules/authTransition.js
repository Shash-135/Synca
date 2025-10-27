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

  const navLinks = document.querySelectorAll('[data-auth-nav]');
  if (!navLinks.length) {
    return;
  }

  navLinks.forEach((link) => {
    link.addEventListener('click', (event) => {
      if (link.classList.contains('active')) {
        event.preventDefault();
        return;
      }

      const href = link.getAttribute('href');
      if (!href) {
        return;
      }

      event.preventDefault();

      if (card.classList.contains('is-exiting')) {
        return;
      }

      card.classList.remove('is-ready');
      card.classList.add('is-exiting');

      window.setTimeout(() => {
        window.location.href = href;
      }, 280);
    });
  });
}

export default initAuthTransition;
