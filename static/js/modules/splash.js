export function initSplashScreen() {
  const splashContainer = document.getElementById('splashContainer');
  if (!splashContainer) {
    return;
  }

  const redirectUrl = splashContainer.dataset.redirectUrl || '/home/';

  window.setTimeout(() => {
    splashContainer.classList.add('fade-out');
    window.setTimeout(() => {
      window.location.href = redirectUrl;
    }, 500);
  }, 3000);
}

export default initSplashScreen;
