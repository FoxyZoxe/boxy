/* ══════════════════════════════════════════════════════
   BOXY — customizer.js
   Génère et télécharge un fichier .env personnalisé
   ══════════════════════════════════════════════════════ */

// Appelle updatePreview() dès le chargement de la page
document.addEventListener('DOMContentLoaded', () => {
  updatePreview();
});

// ── Lecture des valeurs du formulaire ─────────────────────────────
function getConfig() {
  const v = id => {
    const el = document.getElementById(id);
    return el ? el.value.trim() : '';
  };

  return {
    name:         v('cfg-name')         || 'Boxy',
    user:         v('cfg-user')         || 'Monsieur',
    provider:     _currentProvider      || 'groq',
    groqKey:      v('cfg-groq-key'),
    groqModel:    v('cfg-groq-model')   || 'llama-3.3-70b-versatile',
    ollamaUrl:    v('cfg-ollama-url')   || 'http://localhost:11434',
    ollamaModel:  v('cfg-ollama-model') || 'mistral:latest',
    openaiKey:    v('cfg-openai-key'),
    openaiModel:  v('cfg-openai-model') || 'gpt-4o-mini',
    voice:        v('cfg-voice')        || 'fr-FR-DeniseNeural',
    voiceMode:    v('cfg-voice-mode')   || 'wake_word',
    whisper:      v('cfg-whisper')      || 'small',
    sttLang:      v('cfg-stt-lang')     || 'fr',
    theme:        _currentTheme         || 'cyan',
    history:      v('cfg-history')      || '6',
    timeout:      v('cfg-timeout')      || '120',
    discord:      v('cfg-discord'),
  };
}

// ── Génère le contenu du fichier .env ─────────────────────────────
function buildEnv(cfg) {
  const lines = [];

  function section(title) { lines.push(`\n# ══ ${title} ══`); }
  function kv(key, val, comment) {
    if (comment) lines.push(`# ${comment}`);
    lines.push(`${key}=${val}`);
  }
  function blank() { lines.push(''); }

  section('IA');
  kv('AI_PROVIDER', cfg.provider, `Moteur IA : ${cfg.provider}`);
  blank();

  if (cfg.provider === 'groq' || true) {
    kv('GROQ_API_KEY',  cfg.groqKey  || 'VOTRE_CLE_GROQ_ICI');
    kv('GROQ_MODEL',    cfg.groqModel);
  }
  blank();

  kv('OPENAI_API_KEY', cfg.openaiKey  || 'VOTRE_CLE_OPENAI_ICI');
  kv('OPENAI_MODEL',   cfg.openaiModel);
  blank();

  kv('OLLAMA_BASE_URL', cfg.ollamaUrl);
  kv('OLLAMA_MODEL',    cfg.ollamaModel);

  section('PERSONNALITÉ');
  kv('ASSISTANT_NAME', cfg.name);
  kv('USER_NAME',      cfg.user);
  kv('MAX_HISTORY_LENGTH', cfg.history);
  kv('AI_TIMEOUT',     cfg.timeout);

  section('VOIX');
  kv('VOICE_ENABLED',  'true');
  kv('TTS_VOICE',      cfg.voice, 'Voix de synthèse (edge-tts)');
  kv('WHISPER_MODEL',  cfg.whisper, 'tiny | base | small | medium');
  kv('STT_LANGUAGE',   cfg.sttLang, 'Langue de transcription Whisper');
  kv('VOICE_MODE',     cfg.voiceMode, 'push_to_talk | wake_word');
  kv('PTT_KEY',        'space', 'Touche push-to-talk');
  kv('WAKE_WORD_MODEL','hey_jarvis', 'Modèle wake word');
  kv('GLOBAL_HOTKEY',  'ctrl+space', 'Raccourci global');
  kv('PICOVOICE_ACCESS_KEY', '', 'Clé Picovoice (wake word cloud, optionnel)');

  section('INTERFACE');
  kv('THEME', cfg.theme, 'Thème : cyan | red | green | purple | orange | pink');

  section('OPTIONS');
  kv('IMAGE_PROVIDER', 'pollinations', 'Génération d\'images : pollinations | openai');

  section('INTÉGRATIONS (optionnel)');
  kv('DISCORD_TOKEN',   cfg.discord || '');
  kv('DISCORD_CHANNEL', 'boxy');
  kv('OBS_HOST',        'localhost');
  kv('OBS_PORT',        '4455');
  kv('OBS_PASSWORD',    '');
  kv('HF_HUB_DISABLE_SYMLINKS_WARNING', '1');

  return lines.join('\n').trim() + '\n';
}

// ── Syntaxe colorée HTML pour la prévisualisation ─────────────────
function syntaxHighlight(text) {
  return text
    .split('\n')
    .map(line => {
      if (line.startsWith('#')) {
        return `<span class="comment">${escHtml(line)}</span>`;
      }
      const eq = line.indexOf('=');
      if (eq !== -1) {
        const key = line.slice(0, eq);
        const val = line.slice(eq + 1);
        return `<span class="key">${escHtml(key)}</span>=<span class="val">${escHtml(val)}</span>`;
      }
      return escHtml(line);
    })
    .join('\n');
}

function escHtml(s) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ── Mise à jour de la prévisualisation ────────────────────────────
function updatePreview() {
  const cfg = getConfig();
  const env = buildEnv(cfg);
  const pre = document.getElementById('env-preview');
  if (pre) {
    pre.innerHTML = syntaxHighlight(env);
  }
}

// ── Téléchargement du fichier .env ────────────────────────────────
function downloadEnv() {
  const cfg = getConfig();
  const env = buildEnv(cfg);

  const blob = new Blob([env], { type: 'text/plain;charset=utf-8' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = '.env';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  // Feedback visuel
  const btn = document.getElementById('btn-download');
  if (btn) {
    const orig = btn.innerHTML;
    btn.innerHTML = '✓ Téléchargé !';
    btn.style.background = '#00ff88';
    btn.style.color = '#000';
    setTimeout(() => {
      btn.innerHTML = orig;
      btn.style.background = '';
      btn.style.color = '';
    }, 2500);
  }

  // Affiche un message d'instructions
  showDownloadInstructions(cfg.name);
}

// ── Message post-téléchargement ────────────────────────────────────
function showDownloadInstructions(name) {
  // Crée un toast de confirmation
  const toast = document.createElement('div');
  toast.style.cssText = `
    position: fixed; bottom: 32px; right: 32px; z-index: 9999;
    background: #0d1117; border: 1px solid #00ff88;
    border-radius: 8px; padding: 20px 24px;
    font-family: 'Share Tech Mono', monospace; font-size: 13px;
    color: #c8d8e8; max-width: 340px;
    box-shadow: 0 0 30px rgba(0,255,136,.2);
    animation: slideIn .3s ease;
  `;
  toast.innerHTML = `
    <style>@keyframes slideIn { from { transform: translateY(20px); opacity:0; } to { transform: none; opacity:1; } }</style>
    <div style="color:#00ff88;margin-bottom:8px;font-size:14px;">✓ .env téléchargé !</div>
    <div style="color:#4a6070;line-height:1.6;">
      Placez ce fichier à la racine du dossier <strong style="color:#c8d8e8">${escHtml(name)}</strong> (là où se trouve <code style="color:#00d4ff">main.py</code>) et relancez.
    </div>
    <button onclick="this.parentElement.remove()" style="
      margin-top:12px; background:transparent; border:1px solid #1a2332;
      color:#4a6070; padding:5px 12px; border-radius:4px; cursor:pointer;
      font-size:11px; width:100%;
    ">Fermer</button>
  `;
  document.body.appendChild(toast);
  setTimeout(() => { if (toast.parentElement) toast.remove(); }, 8000);
}
