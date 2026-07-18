// js/ui.js — UI layer for the GOES-19 globe viewer.
//
// Pure chrome: owns the control bar, title block, toasts and busy indicator.
// It never imports data.js or globe.js and holds no imagery knowledge of its
// own — frames/resolutions arrive via setCatalog(), the current position via
// setFrame(), and user intent leaves through the initUI() callbacks.

const SPEED_PRESETS = [2, 5, 10, 20]; // fps — playback presets per spec
const DEFAULT_FPS = 5;
const TOAST_TTL = { info: 3500, error: 8000 }; // error toasts persist longer
const MAX_TOASTS = 4;
const THUMB_PX = 14; // must match the slider thumb size in css/style.css

export function initUI({ onScrub, onPlayToggle, onSpeedChange, onResChange, onLatest } = {}) {
  const $ = (id) => document.getElementById(id);
  const playBtn = $('play-btn');
  const speedSel = $('speed-select');
  const slider = $('time-slider');
  const tip = $('slider-tip');
  const utcEl = $('time-utc');
  const localEl = $('time-local');
  const resSel = $('res-select');
  const latestBtn = $('latest-btn');
  const sourceEl = $('source-label');
  const badgeEl = $('demo-badge');
  const busyEl = $('busy');
  const toastsEl = $('toasts');

  let frames = [];       // [{ stamp, date }] — only ever set by setCatalog()
  let currentIndex = -1; // last position from setFrame()/user scrubbing
  let playing = false;
  let dragging = false;  // true while the thumb is being pointer-dragged
  let tipTimer = 0;

  // ---------- formatting ----------

  const pad = (n) => String(n).padStart(2, '0');

  function fmtUTC(date) {
    return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ` +
           `${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())} UTC`;
  }

  function fmtLocal(date) {
    return `${date.toLocaleTimeString(undefined, { timeStyle: 'short' })} local`;
  }

  function renderReadout(index) {
    const f = frames[index];
    if (!f) return;
    utcEl.textContent = fmtUTC(f.date);
    localEl.textContent = fmtLocal(f.date);
    slider.setAttribute('aria-valuetext', fmtUTC(f.date));
  }

  // ---------- slider: fill, tooltip, scrub ----------

  function updateFill() {
    const max = Number(slider.max) || 0;
    const pct = max > 0 ? (Number(slider.value) / max) * 100 : 0;
    slider.style.setProperty('--fill', `${pct}%`);
  }

  function positionTip() {
    if (tip.hidden) return;
    const f = frames[Number(slider.value)];
    if (!f) return;
    tip.textContent = fmtUTC(f.date);
    const max = Number(slider.max) || 0;
    const frac = max > 0 ? Number(slider.value) / max : 0;
    const w = slider.getBoundingClientRect().width;
    // center over the thumb: the thumb's travel is (track width - thumb width)
    tip.style.left = `${slider.offsetLeft + frac * (w - THUMB_PX) + THUMB_PX / 2}px`;
  }

  function showTip() {
    tip.hidden = false;
    positionTip();
    clearTimeout(tipTimer);
    tipTimer = setTimeout(() => { if (!dragging) tip.hidden = true; }, 900);
  }

  function endDrag() {
    if (!dragging) return;
    dragging = false;
    clearTimeout(tipTimer);
    tipTimer = setTimeout(() => { tip.hidden = true; }, 250);
    // catch up with any setFrame() calls that arrived mid-drag
    if (currentIndex >= 0 && slider.value !== String(currentIndex)) {
      slider.value = String(currentIndex);
      updateFill();
      renderReadout(currentIndex);
    }
  }

  slider.addEventListener('pointerdown', () => { dragging = true; showTip(); });
  slider.addEventListener('pointerup', endDrag);
  slider.addEventListener('pointercancel', endDrag);
  window.addEventListener('pointerup', endDrag);

  // 'input' (not 'change') so the readout and tooltip track the thumb live
  slider.addEventListener('input', () => {
    const i = Number(slider.value);
    currentIndex = i;
    updateFill();
    renderReadout(i);
    showTip();
    onScrub?.(i);
  });

  window.addEventListener('resize', positionTip);

  // ---------- play / speed / resolution / latest ----------

  function reflectPlaying(p) {
    playing = !!p;
    playBtn.classList.toggle('playing', playing);
    playBtn.setAttribute('aria-label', playing ? 'Pause' : 'Play');
    playBtn.title = playing ? 'Pause (Space)' : 'Play (Space)';
  }

  function togglePlay() {
    if (playBtn.disabled) return;
    reflectPlaying(!playing);
    onPlayToggle?.(playing);
  }

  playBtn.addEventListener('click', togglePlay);

  for (const fps of SPEED_PRESETS) {
    const opt = document.createElement('option');
    opt.value = String(fps);
    opt.textContent = `${fps} fps`;
    if (fps === DEFAULT_FPS) opt.selected = true;
    speedSel.appendChild(opt);
  }
  speedSel.addEventListener('change', () => onSpeedChange?.(Number(speedSel.value)));

  resSel.addEventListener('change', () => onResChange?.(resSel.value));
  latestBtn.addEventListener('click', () => onLatest?.());

  // ---------- keyboard: Space = play/pause, arrows = step ----------

  function step(delta) {
    if (!frames.length) return;
    const max = frames.length - 1;
    const from = currentIndex < 0 ? max : currentIndex;
    const i = Math.min(max, Math.max(0, from + delta));
    if (i === from) return;
    currentIndex = i;
    slider.value = String(i);
    updateFill();
    renderReadout(i);
    onScrub?.(i);
  }

  window.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const t = e.target;
    if (t instanceof HTMLSelectElement) return; // selects keep native key handling
    if (e.code === 'Space') {
      if (e.repeat) return;
      e.preventDefault(); // also stops a focused button from double-firing
      togglePlay();
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      if (t === slider) return; // native range stepping already fires 'input'
      e.preventDefault();
      step(e.key === 'ArrowRight' ? 1 : -1);
    }
  });

  // ---------- public API ----------

  function setCatalog({ frames: nextFrames = [], sourceLabel = '', demo = false,
                        resolutions = [], resolution } = {}) {
    frames = Array.isArray(nextFrames) ? nextFrames : [];
    const max = Math.max(0, frames.length - 1);
    // A refreshed catalog appends newer frames, so an existing index still
    // points at the same frame — keep the user's position, clamp only if the
    // catalog shrank. First catalog parks at the newest frame.
    currentIndex = currentIndex < 0 ? max : Math.min(currentIndex, max);
    slider.max = String(max);
    if (!dragging) {
      slider.value = String(currentIndex);
      renderReadout(currentIndex);
    }
    updateFill();

    sourceEl.textContent = sourceLabel || '';
    badgeEl.hidden = !demo;

    const prevRes = resSel.value;
    resSel.replaceChildren();
    for (const res of resolutions) {
      const opt = document.createElement('option');
      opt.value = res;
      opt.textContent = res;
      resSel.appendChild(opt);
    }
    const want = resolution ?? prevRes;
    if (want && resolutions.includes(want)) resSel.value = want;

    const hasFrames = frames.length > 0;
    slider.disabled = frames.length < 2;
    playBtn.disabled = !hasFrames;
    latestBtn.disabled = !hasFrames;
    resSel.disabled = resolutions.length === 0;
  }

  function setFrame(index) {
    if (!frames.length || !Number.isFinite(index)) return;
    const i = Math.min(frames.length - 1, Math.max(0, Math.trunc(index)));
    currentIndex = i;
    if (dragging) return; // don't fight the user's thumb mid-drag
    slider.value = String(i);
    updateFill();
    renderReadout(i);
  }

  function setPlaying(p) {
    reflectPlaying(p);
  }

  function setBusy(busy) {
    busyEl.classList.toggle('on', !!busy);
  }

  function toast(msg, kind = 'info') {
    const el = document.createElement('div');
    el.className = `toast ${kind === 'error' ? 'error' : 'info'}`;
    el.setAttribute('role', kind === 'error' ? 'alert' : 'status');
    el.textContent = String(msg);
    toastsEl.appendChild(el);
    while (toastsEl.children.length > MAX_TOASTS) toastsEl.firstElementChild.remove();
    requestAnimationFrame(() => el.classList.add('show'));
    const dismiss = () => {
      if (!el.isConnected) return;
      el.classList.remove('show');
      el.addEventListener('transitionend', () => el.remove(), { once: true });
      setTimeout(() => el.remove(), 400); // fallback (reduced-motion kills the transition)
    };
    const timer = setTimeout(dismiss, TOAST_TTL[kind] ?? TOAST_TTL.info);
    el.addEventListener('click', () => { clearTimeout(timer); dismiss(); });
  }

  return { setCatalog, setFrame, setPlaying, setBusy, toast };
}
