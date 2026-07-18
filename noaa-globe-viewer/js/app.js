import { SAT, RESOLUTIONS, DEFAULT_RESOLUTION, loadCatalog } from './data.js';
import { GlobeViewer } from './globe.js';
import { initUI } from './ui.js';

const REFRESH_MS = 5 * 60 * 1000;

async function main() {
  const params = new URLSearchParams(location.search);
  const wantDemo = params.has('demo');

  const globe = new GlobeViewer(document.getElementById('globe'), { satLonDeg: SAT.lonDeg });

  let catalog;
  let resolution = RESOLUTIONS.includes(params.get('res')) ? params.get('res') : DEFAULT_RESOLUTION;
  let index = 0;
  let playing = false;
  let fps = 10;
  let playTimer = null;
  let frameBusy = false;

  const ui = initUI({
    onScrub: (i) => { stop(); show(i); },
    onPlayToggle: (p) => (p ? play() : stop()),
    onSpeedChange: (f) => { fps = f; if (playing) { stop(); play(); } },
    onResChange: (res) => { resolution = res; show(index); },
    onLatest: async () => {
      stop();
      try { await catalog.refresh(); } catch { /* keep existing frames */ }
      ui.setCatalog(catalogView());
      show(catalog.frames.length - 1);
    },
  });

  try {
    catalog = await loadCatalog({ demo: wantDemo });
  } catch (err) {
    ui.toast(`${err.message} — falling back to demo data.`, 'error');
    catalog = await loadCatalog({ demo: true });
  }

  function catalogView() {
    return {
      frames: catalog.frames,
      sourceLabel: catalog.sourceLabel,
      demo: catalog.demo,
      resolutions: RESOLUTIONS,
      resolution,
    };
  }

  async function show(i) {
    index = Math.max(0, Math.min(i, catalog.frames.length - 1));
    ui.setFrame(index);
    ui.setBusy(true);
    frameBusy = true;
    try {
      await globe.showFrame(catalog.urlFor(catalog.frames[index].stamp, resolution));
    } catch {
      ui.toast(`Frame ${catalog.frames[index].stamp} failed to load; keeping previous image.`, 'info');
    } finally {
      frameBusy = false;
      ui.setBusy(false);
    }
  }

  function play() {
    playing = true;
    ui.setPlaying(true);
    playTimer = setInterval(() => {
      if (frameBusy) return; // don't queue frames faster than they load
      show(index + 1 >= catalog.frames.length ? 0 : index + 1);
    }, 1000 / fps);
  }

  function stop() {
    playing = false;
    ui.setPlaying(false);
    if (playTimer) { clearInterval(playTimer); playTimer = null; }
  }

  // Periodically pick up newly published frames while sitting at the live edge.
  setInterval(async () => {
    if (catalog.demo) return;
    const atEdge = index >= catalog.frames.length - 1;
    try {
      const added = await catalog.refresh();
      if (added > 0) {
        ui.setCatalog(catalogView());
        if (atEdge && !playing) show(catalog.frames.length - 1);
      }
    } catch { /* transient; try again next tick */ }
  }, REFRESH_MS);

  ui.setCatalog(catalogView());
  if (catalog.demo && !wantDemo) {
    // already toasted the failure above
  } else if (catalog.demo) {
    ui.toast('Demo mode: synthetic imagery, no network used.', 'info');
  }
  await show(catalog.frames.length - 1);
}

main().catch((err) => {
  console.error(err);
  const el = document.createElement('pre');
  el.style.cssText = 'position:fixed;inset:auto 12px 12px 12px;color:#f88;z-index:99;';
  el.textContent = `Failed to start: ${err.message}`;
  document.body.appendChild(el);
});
