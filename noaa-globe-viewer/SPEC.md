# NOAA GOES-19 Globe Viewer — Build Spec

A static, no-build-step web app that renders NOAA GOES-19 ABI Full Disk GEOCOLOR
imagery (https://cdn.star.nesdis.noaa.gov/GOES19/ABI/FD/GEOCOLOR/) onto an
interactive 3D globe, with a timeline to scrub through time (10-minute cadence,
rolling multi-day window), playback animation, and resolution switching.

Everything is vanilla ES modules loaded straight from `index.html` — no bundler,
no framework, no TypeScript. Must work when served by any static file server.

## File layout (each module is owned by exactly one author — do not edit files you don't own)

```
noaa-globe-viewer/
  index.html                  (owner: UI agent)
  css/style.css               (owner: UI agent)
  js/ui.js                    (owner: UI agent)
  js/data.js                  (owner: data agent)
  js/globe.js                 (owner: globe agent)
  js/app.js                   (owner: integrator — DO NOT create/edit)
  vendor/three.module.min.js  (already present)
  vendor/addons/controls/OrbitControls.js  (already present)
  serve.py, README.md         (owner: integrator)
```

`index.html` must declare this import map before the module scripts:

```html
<script type="importmap">
{ "imports": {
    "three": "./vendor/three.module.min.js",
    "three/addons/": "./vendor/addons/"
} }
</script>
<script type="module" src="./js/app.js"></script>
```

## Imagery facts (assume these; the sandbox cannot reach the CDN)

- Base URL: `https://cdn.star.nesdis.noaa.gov/GOES19/ABI/FD/GEOCOLOR/`
- Timestamped files: `YYYYDDDHHMM_GOES19-ABI-FD-GEOCOLOR-<RES>.jpg`
  where `DDD` = UTC day-of-year (001-366), `HHMM` UTC, minutes in 10-min steps.
  Example: `20261990000_GOES19-ABI-FD-GEOCOLOR-1808x1808.jpg`
- Resolutions: `339x339`, `678x678`, `1808x1808`, `5424x5424`, `10848x10848`.
  Default `1808x1808`.
- `latest.jpg` also exists (full res alias of newest frame) — not used.
- Directory listing is a standard Apache-style HTML index; the CDN serves
  `Access-Control-Allow-Origin: *` (browser fetch + WebGL textures OK).
- The image is square; the Earth disk is the GOES-R ABI fixed-grid full-disk
  view: north up, east on the right, sub-satellite longitude **-75.2°**
  (GOES-East). Agency logos sit in the image corners, outside the disk.

## Module contracts

### js/data.js  (data agent)

```js
export const SAT = { id: 'GOES19', lonDeg: -75.2, name: 'GOES-East (GOES-19)' };
export const RESOLUTIONS = ['339x339', '678x678', '1808x1808', '5424x5424', '10848x10848'];
export const DEFAULT_RESOLUTION = '1808x1808';

// Load the frame catalog. opts.demo === true -> synthetic offline catalog.
// Returns a catalog object (below). Throws Error with a human-readable
// message (suitable for a toast) if no source is reachable.
export async function loadCatalog(opts = {}) -> {
  frames,        // Array<{ stamp: string /* YYYYDDDHHMM */, date: Date /* UTC */ }>,
                 // sorted ascending by date; deduped
  demo,          // boolean
  sourceLabel,   // e.g. 'NOAA STAR CDN (direct)', 'local proxy', 'demo'
  urlFor(stamp, res),   // -> string URL for that frame at that resolution
  indexNearest(date),   // -> index into frames closest to a Date
  refresh(),     // async; re-fetches listing, appends any new frames in place,
                 //  returns count of new frames (0 in demo mode)
}
```

Source resolution order for the real catalog (probe in this order, use first
that yields a parseable listing):
1. Same-origin proxy: `fetch('noaa/')` — provided when the app is served by
   `serve.py`, which forwards `noaa/<path>` to the CDN. If it works,
   `urlFor` must also use the `noaa/` prefix.
2. Direct CDN: `fetch('https://cdn.star.nesdis.noaa.gov/GOES19/ABI/FD/GEOCOLOR/')`.

Parse listings with a regex over the HTML for
`(\d{11})_GOES19-ABI-FD-GEOCOLOR-\d+x\d+\.jpg`; dedupe stamps (each appears
once per resolution). Convert `YYYYDDDHHMM` -> UTC Date via day-of-year math
(no date libraries).

**Demo mode** (`demo: true`, used when the CDN is unreachable and always via
`?demo=1`): generate 145 synthetic frames covering the last 24 h at 10-min
steps ending at the current UTC time rounded down to 10 min. `urlFor` returns a
blob/object URL of a canvas-rendered synthetic full-disk image (square, black
background, Earth disk filling the frame like the real product):
- ocean-blue disk with a lat/lon graticule every 15°, rendered by actually
  projecting graticule points through the geostationary forward projection
  (same math as in globe.js below) so the demo validates the shader mapping;
- a few green continent-ish blobs (fixed pseudo-random polygons, seeded so
  every frame matches);
- orientation markers ON the disk near the limb: white "N" (top), "S"
  (bottom), "E" (right), "W" (left);
- a day/night terminator: darken the night side consistent with the frame's
  UTC time (sun longitude ≈ 180° - 15°*(UTC decimal hours) deg, moving west as
  time advances) so scrubbing the slider visibly moves the terminator;
- the frame's `stamp` drawn small in a corner (outside the disk).
Cache generated object URLs per (stamp, res); render at 1024x1024 regardless
of requested res. Generation must be lazy (on first urlFor call for a stamp),
not all 145 upfront.

No DOM assumptions other than `document.createElement('canvas')`. No imports
from three.js.

### js/globe.js  (globe agent)

```js
import * as THREE from 'three';  // via the import map

export class GlobeViewer {
  constructor(containerEl, { satLonDeg = -75.2 } = {})
  // Load (or fetch from LRU cache) the image URL as a texture, then display
  // it. Serialize: if called again while a load is in flight, the latest call
  // wins and stale loads are dropped. Resolves when displayed (or dropped).
  // Rejects on image load failure; the previous texture MUST stay on screen.
  async showFrame(url)
  onReady(cb)      // cb() once the first frame is visible
  resize()         // also wire window resize internally
  dispose()
}
```

Scene: unit sphere (SphereGeometry, >=128 segments), custom ShaderMaterial;
OrbitControls (`three/addons/controls/OrbitControls.js`) for drag-rotate +
wheel-zoom, damping on, zoom clamped [1.15, 6], pan disabled; camera starts
looking at the sub-satellite point. Background: near-black with a subtle
procedural starfield (Points). A soft atmosphere rim (backside sphere with
additive fresnel shader) is welcome but keep it tasteful. No texture flip
tricks in JS — handle all orientation inside the fragment shader.

**Fragment shader — geostationary projection (GOES-R fixed grid, PUG L1b vol 3):**

For each fragment, from the interpolated unit-sphere model position `p`
(y = north pole axis): `lat = asin(p.y)` (geodetic, treat sphere as ellipsoid
via the formulas below), `lon = atan(p.x, p.z) + uLonOffset` — choose the
lon convention + offset such that the sub-satellite longitude uSatLon lands at
the disk center and east appears to the right when viewing the globe from the
satellite direction (VERIFY with the demo texture's E/W markers — a
mirrored globe is the classic bug here).

Constants: `req = 6378137.0`, `rpol = 6356752.31414`, `H = 42164160.0`,
`e2 = (req²−rpol²)/req² = 0.0066943800229`, `lon0 = radians(uSatLonDeg)`.

```
phi_c = atan((rpol²/req²) * tan(lat))          // geocentric latitude
rc    = rpol / sqrt(1 − e2*cos(phi_c)²)
sx = H − rc*cos(phi_c)*cos(lon − lon0)
sy = −rc*cos(phi_c)*sin(lon − lon0)
sz = rc*sin(phi_c)
visible when  H*(H − sx) ≥ sy² + (req²/rpol²)*sz²    // else far side
scanx = asin(−sy / length(vec3(sx,sy,sz)))
scany = atan(sz / sx)
u = (scanx/EXTENT + 1.0) * 0.5
v = (1.0 − scany/EXTENT) * 0.5                 // +scany = north = image top
EXTENT = 0.151872                              // half-width of FD scan, rad
```

Sample the texture when visible and u,v ∈ [0,1]; otherwise render the "no
data" side: very dark blue-gray base + faint graticule lines (15° grid,
thin, computed from lat/lon with fwidth anti-aliasing) + slight fresnel edge
lighting so the sphere still reads as 3D. Blend a soft edge (smoothstep over
~0.3° of arc) at the visibility boundary instead of a hard cut.

Texture cache: LRU keyed by URL, capacity 24, dispose() evicted textures.
Use `THREE.TextureLoader` with `crossOrigin='anonymous'`; set
`colorSpace = THREE.SRGBColorSpace`, anisotropy = renderer max.

Self-verify before finishing: build a tiny throwaway HTML harness (delete it
after) or run via node --experimental if needed — at minimum reason through
the E/W orientation carefully and leave a `uFlipX`-style uniform OUT of the
final code (fix the math, don't add knobs).

### js/ui.js  (UI agent)

```js
// All wiring is callback-based; ui.js never imports data.js or globe.js.
export function initUI({
  onScrub,        // (index) user moved the slider to frame index
  onPlayToggle,   // (playing: boolean)
  onSpeedChange,  // (fps: number)  playback speed presets [2, 5, 10, 20]
  onResChange,    // (res: string)
  onLatest,       // () jump to newest frame + refresh catalog
}) -> {
  setCatalog({ frames, sourceLabel, demo, resolutions, resolution }),
                        // (re)build slider range + labels, show demo badge
  setFrame(index),      // reflect current frame: slider pos + UTC/local readout
  setPlaying(playing),  // reflect play/pause state
  setBusy(busy),        // subtle loading indicator (frame is being fetched)
  toast(msg, kind),     // kind: 'info' | 'error'; error toasts persist longer
}
```

index.html: full-viewport dark UI. A `#globe` container fills the screen;
controls float over it in a bottom bar: play/pause button, speed select, the
time slider (flex-grow), UTC + local time readout (monospace), resolution
select, "Latest" button. Top-left: small title "GOES-19 · Full Disk ·
GEOCOLOR" + source label; show an amber "DEMO DATA" badge when demo. Keyboard:
Space = play/pause, ←/→ = step one frame. Mobile-friendly (controls wrap;
touch works — OrbitControls handles the canvas itself). No CSS frameworks;
system font stack; keep it genuinely polished — this floats over a beautiful
Earth image, so restrained glassy dark chrome (blur backdrop, 1px hairlines),
not gray developer boxes.

The UI must not hardcode frame counts, resolutions, or timestamps — everything
arrives via `setCatalog`/`setFrame`.

### js/app.js (integrator — pre-written, agents must match it)

app.js will:
1. `const demo = new URLSearchParams(location.search).has('demo')`
2. `loadCatalog({ demo })` — on error: try `loadCatalog({ demo: true })`,
   toast the error, continue with demo data.
3. `new GlobeViewer(document.getElementById('globe'), { satLonDeg: SAT.lonDeg })`
4. wire ui callbacks -> globe.showFrame(catalog.urlFor(...)), playback timer
   (setInterval by fps; skip ticks while a frame is still loading), periodic
   catalog.refresh() every 5 min when playing at the newest frame.

## Constraints for all agents

- Vanilla JS (ES2022), ES modules, no dependencies beyond the vendored three.js.
- No top-level await outside app.js. No globals on `window`.
- Handle failure paths (bad image, missing listing) without throwing to console
  uncaught.
- Comment only non-obvious math/constraints (e.g. projection constants source:
  GOES-R PUG). Keep files focused; ~200-400 lines each is the expected size.
- The sandbox you run in CANNOT reach the NOAA CDN — do not try to verify
  against it; demo mode is the offline test path.
