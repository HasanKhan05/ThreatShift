/**
 * Cyberattack Detection ML — Interactive Demo JavaScript
 * Handles smooth client-side switching between Attack-like and Benign replay states.
 */

let demoData = null;
let currentState = 'attack';

async function initDemo() {
  try {
    const response = await fetch('./data/site-data.json');
    if (!response.ok) throw new Error(`HTTP error ${response.status}`);
    const data = await response.json();
    demoData = data.demonstration.states;
    renderDemoState('attack');
  } catch (err) {
    console.error('Failed to load demo data:', err);
  }

  const toggleBtns = document.querySelectorAll('.toggle-btn');
  toggleBtns.forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const state = btn.getAttribute('data-state');
      if (state && state !== currentState) {
        toggleBtns.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        currentState = state;
        renderDemoState(state);
      }
    });
  });
}

function renderDemoState(stateKey) {
  if (!demoData || !demoData[stateKey]) return;
  const state = demoData[stateKey];

  // Tag Badge
  const tagEl = document.getElementById('demo-tag');
  if (tagEl) {
    tagEl.textContent = state.tag;
    tagEl.className = 'badge-pill ' + (stateKey === 'attack' ? 'orange' : 'teal');
  }

  // Description
  const descEl = document.getElementById('demo-desc');
  if (descEl) {
    descEl.textContent = state.description;
  }

  // Disclaimer
  const discEl = document.getElementById('demo-disclaimer-text');
  if (discEl) {
    discEl.textContent = state.disclaimer;
  }

  // Feature Chips
  const chipsContainer = document.getElementById('demo-chips');
  if (chipsContainer && state.chips) {
    chipsContainer.innerHTML = state.chips
      .map((chip) => `<div class="feature-chip">${chip}</div>`)
      .join('');
  }

  // Flow Rail Visual
  const railEl = document.getElementById('demo-packet-rail');
  if (railEl) {
    if (stateKey === 'attack') {
      railEl.innerHTML = `
        <div class="flow-packet dot-orange" style="left: 12%;"></div>
        <div class="flow-packet dot-orange" style="left: 22%;"></div>
        <div class="flow-packet triangle" style="left: 32%;"></div>
        <div class="flow-packet dot-orange" style="left: 44%;"></div>
        <div class="flow-packet dot-lime" style="left: 68%;"></div>
        <div class="flow-packet triangle" style="left: 82%;"></div>
        <div class="flow-packet dot-orange" style="left: 92%;"></div>
      `;
    } else {
      railEl.innerHTML = `
        <div class="flow-packet dot-cyan" style="left: 15%;"></div>
        <div class="flow-packet dot-cyan" style="left: 38%;"></div>
        <div class="flow-packet dot-cyan" style="left: 62%;"></div>
        <div class="flow-packet dot-cyan" style="left: 85%;"></div>
      `;
    }
  }

  // Model Decisions Panel
  const modelsContainer = document.getElementById('demo-models-list');
  if (modelsContainer && state.models) {
    modelsContainer.innerHTML = state.models
      .map((m) => {
        let badgeClass = 'badge-baseline';
        if (m.badge_type === 'attack') badgeClass = 'badge-attack';
        else if (m.badge_type === 'benign') badgeClass = 'badge-benign';

        let barColor = 'fill-gray';
        if (m.id.includes('logistic')) barColor = 'fill-cyan';
        else if (m.id.includes('random')) barColor = 'fill-teal';
        else if (m.id.includes('mlp')) barColor = 'fill-purple';

        const highlightClass = m.is_highlighted ? 'highlighted' : '';

        return `
          <div class="decision-card ${highlightClass}">
            <div class="decision-card-top">
              <span class="decision-model-name">${m.name}</span>
              <span class="status-badge ${badgeClass}">${m.badge}</span>
            </div>
            <div class="decision-score-track">
              <div class="decision-score-fill ${barColor}" style="width: ${m.score_display};"></div>
            </div>
            <div class="decision-caption">
              <span>saved replay score</span>
              <span>${m.score_display}</span>
            </div>
          </div>
        `;
      })
      .join('');
  }
}

document.addEventListener('DOMContentLoaded', initDemo);
