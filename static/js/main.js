import { initAlertBridge } from './modules/alerts.js';

const moduleRegistry = [
  {
    condition: () => document.querySelector('form.needs-validation'),
    loader: () =>
      import('./modules/formValidation.js').then((module) => {
        const init = module.initFormValidation || module.default;
        if (typeof init === 'function') {
          init();
        }
      }),
  },
  {
    condition: () => document.querySelector('.auth-card'),
    loader: () =>
      import('./modules/authTransition.js').then((module) => {
        const init = module.initAuthTransition || module.default;
        if (typeof init === 'function') {
          init();
        }
      }),
  },
  {
    condition: () => document.querySelector('.toggle-password'),
    loader: () =>
      import('./modules/passwordToggle.js').then((module) => {
        const init = module.initPasswordToggles || module.default;
        if (typeof init === 'function') {
          init();
        }
      }),
  },
  {
    condition: () => document.getElementById('loginForm'),
    loader: () =>
      import('./modules/login.js').then((module) => {
        const init = module.initLoginFormValidation || module.default;
        if (typeof init === 'function') {
          init();
        }
      }),
  },
  {
    condition: () => document.getElementById('occupation-field'),
    loader: () =>
      import('./modules/register.js').then((module) => {
        const init = module.initRegisterPage || module.default;
        if (typeof init === 'function') {
          init();
        }
      }),
  },
  {
    condition: () => document.getElementById('bookingForm'),
    loader: () =>
      import('./modules/booking.js').then((module) => {
        const init = module.initBookingForm || module.default;
        if (typeof init === 'function') {
          init();
        }
      }),
  },
  {
    condition: () => document.querySelector('.bed-toggle'),
    loader: () =>
      import('./modules/ownerBeds.js').then((module) => {
        const init = module.initOwnerBedToggle || module.default;
        if (typeof init === 'function') {
          init();
        }
      }),
  },
  {
    condition: () => document.getElementById('pgDetail'),
    loader: () =>
      import('./modules/pgDetail.js').then((module) => {
        const init = module.initPgDetailBeds || module.default;
        if (typeof init === 'function') {
          init();
        }
      }),
  },
  {
    condition: () => document.getElementById('splashContainer'),
    loader: () =>
      import('./modules/splash.js').then((module) => {
        const init = module.initSplashScreen || module.default;
        if (typeof init === 'function') {
          init();
        }
      }),
  },
];

function initializeModules() {
  initAlertBridge();

  moduleRegistry.forEach(({ condition, loader }) => {
    if (condition()) {
      loader().catch((error) => {
        console.error('Failed to initialize module', error);
      });
    }
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeModules);
} else {
  initializeModules();
}
