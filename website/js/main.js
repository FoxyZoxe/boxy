/* ══════════════════════════════════════════════════════
   BOXY — main.js
   Animations, canvas grid, démo HUD, tabs showcase
   ══════════════════════════════════════════════════════ */

// ── Canvas grille en arrière-plan du hero ──────────────────────────
const BOXY_SETUP_URL = 'https://raw.githubusercontent.com/FoxyZoxe/Boxy-Setup1/refs/heads/main/Boxy-Setup.bat';

async function downloadSetup(event) {
  if (event) event.preventDefault();

  try {
    const response = await fetch(BOXY_SETUP_URL, { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'Boxy-Setup.bat';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    showSetupSecurityHint();
  } catch (error) {
    window.location.href = BOXY_SETUP_URL;
  }
}

function showSetupSecurityHint() {
  const note = document.getElementById('security-note');
  if (!note) return;

  note.scrollIntoView({ behavior: 'smooth', block: 'center' });
  note.classList.add('flash');
  window.setTimeout(() => note.classList.remove('flash'), 2500);
}

(function initGridCanvas() {
  const canvas = document.getElementById('grid-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let W, H, cols, rows;

  function resize() {
    W = canvas.width  = canvas.offsetWidth;
    H = canvas.height = canvas.offsetHeight;
    cols = Math.floor(W / 40);
    rows = Math.floor(H / 40);
    draw();
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    ctx.strokeStyle = 'rgba(0,212,255,0.12)';
    ctx.lineWidth = 0.5;

    // Lignes verticales
    for (let c = 0; c <= cols; c++) {
      const x = c * 40;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, H);
      ctx.stroke();
    }
    // Lignes horizontales
    for (let r = 0; r <= rows; r++) {
      const y = r * 40;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }

    // Points aux intersections
    ctx.fillStyle = 'rgba(0,212,255,0.3)';
    for (let c = 0; c <= cols; c++) {
      for (let r = 0; r <= rows; r++) {
        ctx.beginPath();
        ctx.arc(c * 40, r * 40, 1.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Dégradé radial pour fondu vers le centre
    const grad = ctx.createRadialGradient(W/2, H/2, 0, W/2, H/2, Math.max(W, H) * 0.6);
    grad.addColorStop(0,   'rgba(7,9,14,0.9)');
    grad.addColorStop(0.6, 'rgba(7,9,14,0.3)');
    grad.addColorStop(1,   'rgba(7,9,14,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);
  }

  window.addEventListener('resize', () => { resize(); });
  resize();
})();


// ── Animation HUD démo dans le hero ──────────────────────────────────
(function initHudDemo() {
  const bars = document.querySelectorAll('.wave-bars span');
  const statusDemo = document.getElementById('status-demo');
  const waveLbl    = document.getElementById('wave-label');
  const msgUser    = document.getElementById('msg-user');
  const msgBoxy    = document.getElementById('msg-boxy');
  const msgBoxyTxt = document.getElementById('msg-boxy-text');
  const cpuDemo    = document.getElementById('cpu-demo');
  const ramDemo    = document.getElementById('ram-demo');

  if (!bars.length) return;

  // Animation des barres de la waveform
  function animBars(active) {
    bars.forEach(b => {
      const h = active ? Math.random() * 20 + 4 : 3;
      b.style.height = h + 'px';
    });
  }

  // Fausse animation CPU/RAM
  setInterval(() => {
    if (cpuDemo) cpuDemo.textContent = (Math.random() * 40 + 10).toFixed(0) + '%';
    if (ramDemo) ramDemo.textContent = (Math.random() * 30 + 35).toFixed(0) + '%';
  }, 4000);

  // Séquence de démo : idle → écoute → réflexion → réponse → idle
  const BOXY_REPLY  = 'Spotify lancé et volume à 70%.';
  let seq = null;

  function runSequence() {
    // État idle
    animBars(false);
    if (statusDemo) { statusDemo.textContent = 'INACTIF'; statusDemo.style.color = '#4a6070'; }
    if (waveLbl)    { waveLbl.textContent = 'INACTIF'; waveLbl.style.color = '#4a6070'; }
    if (msgUser)  msgUser.style.opacity  = '0';
    if (msgBoxy)  msgBoxy.style.opacity  = '0';
    if (msgBoxyTxt) msgBoxyTxt.textContent = '';

    // Étape 1 : écoute
    seq = setTimeout(() => {
      if (statusDemo) { statusDemo.textContent = 'ÉCOUTE'; statusDemo.style.color = '#00d4ff'; }
      if (waveLbl)    { waveLbl.textContent = 'ÉCOUTE'; waveLbl.style.color = '#00d4ff'; }
      const barsInterval = setInterval(() => animBars(true), 100);

      // Étape 2 : message utilisateur visible
      setTimeout(() => {
        if (msgUser) msgUser.style.opacity = '1';
        clearInterval(barsInterval);
        animBars(false);

        // Étape 3 : réflexion
        if (statusDemo) { statusDemo.textContent = 'RÉFLEXION'; statusDemo.style.color = '#ffaa00'; }
        if (waveLbl)    { waveLbl.textContent = 'RÉFLEXION'; waveLbl.style.color = '#ffaa00'; }
        const thinkBars = setInterval(() => animBars(true), 150);

        // Étape 4 : réponse (typing)
        setTimeout(() => {
          clearInterval(thinkBars);
          if (msgBoxy)  msgBoxy.style.opacity  = '1';
          if (statusDemo) { statusDemo.textContent = 'PAROLE'; statusDemo.style.color = '#00ff88'; }
          if (waveLbl)    { waveLbl.textContent = 'PAROLE';  waveLbl.style.color = '#00ff88'; }
          const speakBars = setInterval(() => animBars(true), 80);

          let i = 0;
          const typeInterval = setInterval(() => {
            if (i < BOXY_REPLY.length) {
              if (msgBoxyTxt) msgBoxyTxt.textContent = BOXY_REPLY.slice(0, ++i);
            } else {
              clearInterval(typeInterval);
              clearInterval(speakBars);
              animBars(false);
              // Retour idle puis relance
              setTimeout(runSequence, 4000);
            }
          }, 45);

        }, 1200);
      }, 1000);
    }, 2500);
  }

  // Démarre après un délai pour laisser la page se charger
  setTimeout(runSequence, 1500);
})();


// ── Intersection Observer pour l'animation des cartes ─────────────
(function initScrollAnimations() {
  const cards = document.querySelectorAll('.feat-card');
  if (!cards.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const delay = entry.target.dataset.delay || 0;
        setTimeout(() => entry.target.classList.add('visible'), parseInt(delay));
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  cards.forEach(card => observer.observe(card));
})();


// ── Tabs showcase ─────────────────────────────────────────────────
(function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = document.getElementById('tab-' + tab);
      if (panel) panel.classList.add('active');
    });
  });

  // Animation des barres de la section showcase
  const mockBars = document.querySelectorAll('.mock-bars span');
  function animMockBars() {
    mockBars.forEach(b => { b.style.height = (Math.random() * 14 + 2) + 'px'; });
  }
  setInterval(animMockBars, 200);
})();


// ── Navbar : scroll → fond opaque ─────────────────────────────────
(function initNavbar() {
  const nav = document.getElementById('navbar');
  if (!nav) return;
  window.addEventListener('scroll', () => {
    nav.style.background = window.scrollY > 40
      ? 'rgba(7,9,14,0.98)'
      : 'rgba(7,9,14,0.85)';
  }, { passive: true });
})();


// ── Utilitaire : copier du code ────────────────────────────────────
function copyCode(btn, text) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.textContent;
    btn.textContent = '✓';
    setTimeout(() => { btn.textContent = orig; }, 1500);
  });
}

// ── Copie du .env prévisualisé ─────────────────────────────────────
function copyEnv() {
  const pre = document.getElementById('env-preview');
  if (!pre) return;
  navigator.clipboard.writeText(pre.textContent).then(() => {
    const orig = event.target.textContent;
    event.target.textContent = '✓ Copié';
    setTimeout(() => { event.target.textContent = orig; }, 1500);
  });
}

// ── Toggle visibilité mot de passe ─────────────────────────────────
function toggleEye(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = '🙈';
  } else {
    input.type = 'password';
    btn.textContent = '👁';
  }
}

// ── Sélection du provider IA ───────────────────────────────────────
let _currentProvider = 'groq';
function selectProvider(p) {
  _currentProvider = p;
  document.querySelectorAll('.ptab').forEach(b => {
    b.classList.toggle('active', b.dataset.p === p);
  });
  document.querySelectorAll('.provider-panel').forEach(panel => {
    panel.classList.add('hidden');
  });
  const target = document.getElementById('panel-' + p);
  if (target) target.classList.remove('hidden');
  if (typeof updatePreview === 'function') updatePreview();
}

// ── Sélection du thème ─────────────────────────────────────────────
let _currentTheme = 'cyan';
function selectTheme(theme) {
  _currentTheme = theme;
  document.querySelectorAll('.theme-swatch').forEach(s => {
    s.classList.toggle('active', s.dataset.theme === theme);
  });
  if (typeof updatePreview === 'function') updatePreview();
}
