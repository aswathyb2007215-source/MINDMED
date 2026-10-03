/**
 * MINDMED Main Client Scripts
 */

document.addEventListener('DOMContentLoaded', () => {
  // Mobile Navigation Toggle
  const mobileToggle = document.getElementById('mobileToggle');
  const navMenu = document.getElementById('navMenu');

  if (mobileToggle && navMenu) {
    mobileToggle.addEventListener('click', () => {
      navMenu.classList.toggle('show');
    });
  }

  // Dismiss flash alerts
  const alertCloseButtons = document.querySelectorAll('.alert-close');
  alertCloseButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      const alert = e.target.closest('.alert');
      if (alert) {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 200);
      }
    });
  });

  // Demo Credentials Auto-Fill Helper for Judges
  const fillDemoBtn = document.getElementById('fillDemoBtn');
  if (fillDemoBtn) {
    fillDemoBtn.addEventListener('click', () => {
      const emailInput = document.getElementById('email');
      const passwordInput = document.getElementById('password');
      if (emailInput && passwordInput) {
        emailInput.value = 'demo@mindmed.health';
        passwordInput.value = 'mindmed123';
        // highlight briefly
        emailInput.style.backgroundColor = '#ccfbf1';
        passwordInput.style.backgroundColor = '#ccfbf1';
        setTimeout(() => {
          emailInput.style.backgroundColor = '';
          passwordInput.style.backgroundColor = '';
        }, 600);
      }
    });
  }
});
