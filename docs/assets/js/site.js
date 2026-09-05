/**
 * Cyberattack Detection ML — Site JavaScript
 * Handles dynamic data population, active navigation, and chart animations.
 */

async function loadSiteData() {
  try {
    const response = await fetch('./data/site-data.json');
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error('Failed to load site-data.json:', error);
    return null;
  }
}

// Animate horizontal bars when visible
function initBarObserver() {
  const bars = document.querySelectorAll('.chart-fill');
  if (!bars.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const targetWidth = entry.target.getAttribute('data-width');
        if (targetWidth) {
          entry.target.style.width = targetWidth;
        }
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.2 });

  bars.forEach((bar) => observer.observe(bar));
}

// Highlight active navigation link
function initActiveNav() {
  const currentPath = window.location.pathname.split('/').pop() || 'index.html';
  const links = document.querySelectorAll('.nav-links a');
  links.forEach((link) => {
    const href = link.getAttribute('href');
    if (href === currentPath || (currentPath === '' && href === 'index.html')) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  initActiveNav();
  initBarObserver();
});
