export function initSplashScreen() {
  const splashContainer = document.getElementById('splashContainer');
  if (!splashContainer) {
    return;
  }

  const redirectUrl = splashContainer.dataset.redirectUrl || '/home/';

  const triggerTransition = () => {
    if (window.__splashHandled) {
      return;
    }

    window.__splashHandled = true;
    splashContainer.classList.add('fade-out');
    window.setTimeout(() => {
      window.location.href = redirectUrl;
    }, 500);
  };

  window.setTimeout(triggerTransition, 3000);
  window.addEventListener('keydown', triggerTransition, { once: true });
  window.addEventListener('click', triggerTransition, { once: true });
}

export default initSplashScreen;
