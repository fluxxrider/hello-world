// js/data.js — frame catalog for the NOAA GOES-19 Full Disk GEOCOLOR viewer.
// Owns: listing fetch/parse (proxy-first, then direct CDN), YYYYDDDHHMM <->
// UTC Date math, and the synthetic demo catalog whose frames are rendered
// through the real geostationary forward projection so the globe shader can
// be validated offline.

export const SAT = { id: 'GOES19', lonDeg: -75.2, name: 'GOES-East (GOES-19)' };
export const RESOLUTIONS = ['339x339', '678x678', '1808x1808', '5424x5424', '10848x10848'];
export const DEFAULT_RESOLUTION = '1808x1808';

const CDN_BASE = 'https://cdn.star.nesdis.noaa.gov/GOES19/ABI/FD/GEOCOLOR/';
const PROXY_BASE = 'noaa/';
const FILE_RE = /(\d{11})_GOES19-ABI-FD-GEOCOLOR-\d+x\d+\.jpg/g;
const STEP_MS = 10 * 60 * 1000;
const DAY_MS = 86400000;
const FRAME_COUNT = 145; // last 24 h at 10-min cadence, endpoints inclusive

// ---------------------------------------------------------------- date math

function daysInYear(year) {
  return (Date.UTC(year + 1, 0, 1) - Date.UTC(year, 0, 1)) / DAY_MS;
}

// 'YYYYDDDHHMM' -> UTC Date, or null when the stamp is not a real time.
function stampToDate(stamp) {
  if (!/^\d{11}$/.test(stamp)) return null;
  const year = +stamp.slice(0, 4);
  const doy = +stamp.slice(4, 7);
  const hh = +stamp.slice(7, 9);
  const mm = +stamp.slice(9, 11);
  if (doy < 1 || doy > daysInYear(year) || hh > 23 || mm > 59) return null;
  // Date.UTC rolls day-of-month overflow forward, which with month January
  // is exactly day-of-year arithmetic (leap years included).
  return new Date(Date.UTC(year, 0, doy, hh, mm));
}

function utcDayOfYear(date) {
  const y = date.getUTCFullYear();
  return (Date.UTC(y, date.getUTCMonth(), date.getUTCDate()) - Date.UTC(y, 0, 1)) / DAY_MS + 1;
}

// UTC Date -> 'YYYYDDDHHMM'
function dateToStamp(date) {
  const doy = String(utcDayOfYear(date)).padStart(3, '0');
  const hh = String(date.getUTCHours()).padStart(2, '0');
  const mm = String(date.getUTCMinutes()).padStart(2, '0');
  return `${date.getUTCFullYear()}${doy}${hh}${mm}`;
}

// ------------------------------------------------------------ live catalog

function parseListing(html) {
  const stamps = new Set();
  for (const m of html.matchAll(FILE_RE)) stamps.add(m[1]); // dedupe: one per res
  const frames = [];
  for (const stamp of stamps) {
    const date = stampToDate(stamp);
    if (date) frames.push({ stamp, date });
  }
  frames.sort((a, b) => a.date - b.date);
  return frames;
}

async function fetchFrames(base) {
  const res = await fetch(base, { cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return parseListing(await res.text());
}

function makeIndexNearest(frames) {
  return (date) => {
    if (!frames.length) return -1;
    const t = +date;
    let lo = 0;
    let hi = frames.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (+frames[mid].date < t) lo = mid + 1;
      else hi = mid;
    }
    if (lo > 0 && t - +frames[lo - 1].date <= +frames[lo].date - t) return lo - 1;
    return lo;
  };
}

function makeLiveCatalog(source, frames) {
  const known = new Set(frames.map((f) => f.stamp));
  return {
    frames,
    demo: false,
    sourceLabel: source.label,
    urlFor(stamp, res) {
      return `${source.base}${stamp}_GOES19-ABI-FD-GEOCOLOR-${res}.jpg`;
    },
    indexNearest: makeIndexNearest(frames),
    async refresh() {
      let fresh;
      try {
        fresh = await fetchFrames(source.base);
      } catch {
        return 0; // transient listing failure — keep the current catalog
      }
      let added = 0;
      for (const f of fresh) {
        if (known.has(f.stamp)) continue;
        known.add(f.stamp);
        frames.push(f);
        added++;
      }
      if (added) frames.sort((a, b) => a.date - b.date);
      return added;
    },
  };
}

export async function loadCatalog(opts = {}) {
  if (opts.demo) return makeDemoCatalog();
  const sources = [
    { base: PROXY_BASE, label: 'local proxy' },
    { base: CDN_BASE, label: 'NOAA STAR CDN (direct)' },
  ];
  const failures = [];
  for (const source of sources) {
    let frames;
    try {
      frames = await fetchFrames(source.base);
    } catch (err) {
      failures.push(`${source.label}: ${err && err.message ? err.message : err}`);
      continue;
    }
    if (frames.length) return makeLiveCatalog(source, frames);
    failures.push(`${source.label}: listing had no frames`);
  }
  throw new Error(
    `Could not reach the GOES-19 imagery listing (${failures.join('; ')}) — ` +
      'check your connection or reload with ?demo=1.'
  );
}

// ------------------------------------------------------------ demo catalog

function makeDemoCatalog() {
  const end = Math.floor(Date.now() / STEP_MS) * STEP_MS; // now, floored to 10 min
  const frames = [];
  for (let i = FRAME_COUNT - 1; i >= 0; i--) {
    const date = new Date(end - i * STEP_MS);
    frames.push({ stamp: dateToStamp(date), date });
  }
  const urlCache = new Map(); // `${stamp}|${res}` -> object URL
  const stampCache = new Map(); // renders are res-independent (always 1024²)
  return {
    frames,
    demo: true,
    sourceLabel: 'demo',
    urlFor(stamp, res) {
      const key = `${stamp}|${res}`;
      let url = urlCache.get(key);
      if (!url) {
        url = stampCache.get(stamp);
        if (!url) {
          url = renderDemoFrame(stamp); // lazy: first request for this stamp
          stampCache.set(stamp, url);
        }
        urlCache.set(key, url);
      }
      return url;
    },
    indexNearest: makeIndexNearest(frames),
    async refresh() {
      return 0;
    },
  };
}

// --- GOES-R fixed-grid geostationary projection (PUG L1b vol. 3, 5.1.2.8) ---

const DEG = Math.PI / 180;
const REQ = 6378137.0; // GRS80 semi-major axis, m
const RPOL = 6356752.31414; // GRS80 semi-minor axis, m
const SAT_HEIGHT = 42164160.0; // satellite distance from Earth center, m
const E2 = 0.0066943800229; // (req² − rpol²) / req²
const EXTENT = 0.151872; // half-width of the full-disk scan, rad
const LON0 = SAT.lonDeg * DEG;
const SIZE = 1024; // demo frames render at 1024x1024 regardless of res

// Forward projection: geodetic lat/lon (deg) -> demo-image pixel, or null
// when the point is on the far side of the Earth.
function geosToPixel(latDeg, lonDeg) {
  const lat = latDeg * DEG;
  const phiC = Math.atan(((RPOL * RPOL) / (REQ * REQ)) * Math.tan(lat)); // geocentric lat
  const cosP = Math.cos(phiC);
  const sinP = Math.sin(phiC);
  const rc = RPOL / Math.sqrt(1 - E2 * cosP * cosP);
  const dLon = lonDeg * DEG - LON0;
  const sx = SAT_HEIGHT - rc * cosP * Math.cos(dLon);
  const sy = -rc * cosP * Math.sin(dLon);
  const sz = rc * sinP;
  if (SAT_HEIGHT * (SAT_HEIGHT - sx) < sy * sy + ((REQ * REQ) / (RPOL * RPOL)) * sz * sz) {
    return null; // not visible from the satellite
  }
  const scanx = Math.asin(-sy / Math.sqrt(sx * sx + sy * sy + sz * sz));
  const scany = Math.atan(sz / sx);
  return {
    x: (scanx / EXTENT + 1) * 0.5 * SIZE, // east (+scanx) = right
    y: (1 - scany / EXTENT) * 0.5 * SIZE, // north (+scany) = top
  };
}

// Inverse projection sampled once per pixel; shared by every demo frame.
// mask=1 on the Earth disk; sin/cos(lat) and lon (rad) feed the terminator.
let geoLUT = null;
function getLUT() {
  if (geoLUT) return geoLUT;
  const n = SIZE * SIZE;
  const mask = new Uint8Array(n);
  const sinLat = new Float32Array(n);
  const cosLat = new Float32Array(n);
  const lon = new Float32Array(n);
  const c = SAT_HEIGHT * SAT_HEIGHT - REQ * REQ;
  const ratio2 = (REQ * REQ) / (RPOL * RPOL);
  for (let j = 0, p = 0; j < SIZE; j++) {
    const scany = (1 - (2 * (j + 0.5)) / SIZE) * EXTENT;
    const cosy = Math.cos(scany);
    const siny = Math.sin(scany);
    for (let i = 0; i < SIZE; i++, p++) {
      const scanx = ((2 * (i + 0.5)) / SIZE - 1) * EXTENT;
      const cosx = Math.cos(scanx);
      const sinx = Math.sin(scanx);
      const a = sinx * sinx + cosx * cosx * (cosy * cosy + ratio2 * siny * siny);
      const b = -2 * SAT_HEIGHT * cosx * cosy;
      const disc = b * b - 4 * a * c;
      if (disc < 0) continue; // ray misses the ellipsoid: space pixel
      const rs = (-b - Math.sqrt(disc)) / (2 * a);
      const sx = rs * cosx * cosy;
      const sy = -rs * sinx;
      const sz = rs * cosx * siny;
      const lat = Math.atan((ratio2 * sz) / Math.hypot(SAT_HEIGHT - sx, sy));
      mask[p] = 1;
      sinLat[p] = Math.sin(lat);
      cosLat[p] = Math.cos(lat);
      lon[p] = LON0 - Math.atan(sy / (SAT_HEIGHT - sx));
    }
  }
  geoLUT = { mask, sinLat, cosLat, lon };
  return geoLUT;
}

// ------------------------------------------------------- demo frame render

function mulberry32(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function smoothstep(e0, e1, x) {
  const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
}

// Fixed continent-ish blobs (lat/lon polygons); seeded so every frame matches.
let continents = null;
function getContinents() {
  if (continents) return continents;
  const rng = mulberry32(0xc0ffee);
  continents = [];
  for (let b = 0; b < 7; b++) {
    const clat = -42 + rng() * 92;
    const clon = SAT.lonDeg + (rng() * 100 - 50);
    const radius = 6 + rng() * 8;
    const verts = 8 + Math.floor(rng() * 7);
    const latScale = 0.7 + rng() * 0.6;
    const pts = [];
    for (let k = 0; k < verts; k++) {
      const ang = (k / verts) * 2 * Math.PI + (rng() - 0.5) * 0.5;
      const r = radius * (0.55 + rng() * 0.9);
      pts.push([
        clat + r * latScale * Math.sin(ang),
        clon + (r * Math.cos(ang)) / Math.max(0.5, Math.cos(clat * DEG)),
      ]);
    }
    continents.push(pts);
  }
  return continents;
}

// Closed path along the visible-Earth horizon (clip region + limb stroke).
function horizonPath() {
  // Spherical horizon sits acos(R/H) from the sub-satellite point; pull in
  // slightly so every sample survives the ellipsoid visibility test.
  const th = Math.acos(6371008.8 / SAT_HEIGHT) - 0.3 * DEG;
  const sinT = Math.sin(th);
  const cosT = Math.cos(th);
  const path = new Path2D();
  let first = true;
  for (let a = 0; a <= 360; a += 3) {
    const az = a * DEG;
    const lat = Math.asin(sinT * Math.cos(az)) / DEG;
    const lonDeg = SAT.lonDeg + Math.atan2(Math.sin(az) * sinT, cosT) / DEG;
    const pt = geosToPixel(lat, lonDeg);
    if (!pt) continue;
    if (first) {
      path.moveTo(pt.x, pt.y);
      first = false;
    } else {
      path.lineTo(pt.x, pt.y);
    }
  }
  path.closePath();
  return path;
}

function strokeGeoPolyline(ctx, points) {
  ctx.beginPath();
  let pen = false;
  for (const pt of points) {
    if (!pt) {
      pen = false; // far-side gap: lift the pen
      continue;
    }
    if (pen) ctx.lineTo(pt.x, pt.y);
    else {
      ctx.moveTo(pt.x, pt.y);
      pen = true;
    }
  }
  ctx.stroke();
}

function drawGraticule(ctx) {
  ctx.lineWidth = 1;
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.28)';
  for (let lon = -180; lon < 180; lon += 15) {
    const pts = [];
    for (let lat = -88; lat <= 88; lat += 2) pts.push(geosToPixel(lat, lon));
    strokeGeoPolyline(ctx, pts);
  }
  for (let lat = -75; lat <= 75; lat += 15) {
    if (lat === 0) continue;
    const pts = [];
    for (let lon = -170; lon <= 20; lon += 2) pts.push(geosToPixel(lat, lon));
    strokeGeoPolyline(ctx, pts);
  }
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)'; // brighter equator
  const eq = [];
  for (let lon = -170; lon <= 20; lon += 2) eq.push(geosToPixel(0, lon));
  strokeGeoPolyline(ctx, eq);
}

function drawContinents(ctx) {
  ctx.fillStyle = '#3c7a4a';
  for (const blob of getContinents()) {
    ctx.beginPath();
    let started = false;
    let count = 0;
    for (const [lat, lon] of blob) {
      const pt = geosToPixel(lat, lon);
      if (!pt) continue;
      if (started) ctx.lineTo(pt.x, pt.y);
      else {
        ctx.moveTo(pt.x, pt.y);
        started = true;
      }
      count++;
    }
    if (count >= 3) {
      ctx.closePath();
      ctx.fill();
    }
  }
}

function applyTerminator(ctx, date, lut) {
  const img = ctx.getImageData(0, 0, SIZE, SIZE);
  const d = img.data;
  const hours = date.getUTCHours() + date.getUTCMinutes() / 60;
  const sunLon = (180 - 15 * hours) * DEG; // subsolar lon drifts west 15°/h
  // Rough solar declination from day of year — enough for a plausible tilt.
  const decl = -23.44 * DEG * Math.cos((2 * Math.PI * (utcDayOfYear(date) + 10)) / 365.24);
  const sinD = Math.sin(decl);
  const cosD = Math.cos(decl);
  const { mask, sinLat, cosLat, lon } = lut;
  for (let p = 0, q = 0; p < SIZE * SIZE; p++, q += 4) {
    if (!mask[p]) continue;
    const cosZ = sinLat[p] * sinD + cosLat[p] * cosD * Math.cos(lon[p] - sunLon);
    const f = 0.22 + 0.78 * smoothstep(-0.07, 0.07, cosZ); // soft twilight band
    if (f > 0.995) continue;
    d[q] *= f;
    d[q + 1] *= f;
    d[q + 2] *= f;
  }
  ctx.putImageData(img, 0, 0);
}

function drawLimbMarkers(ctx) {
  ctx.font = 'bold 34px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const spots = [
    ['N', 62, SAT.lonDeg],
    ['S', -62, SAT.lonDeg],
    ['E', 0, SAT.lonDeg + 62],
    ['W', 0, SAT.lonDeg - 62],
  ];
  for (const [label, lat, lon] of spots) {
    const pt = geosToPixel(lat, lon);
    if (!pt) continue;
    ctx.lineWidth = 5;
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.75)';
    ctx.strokeText(label, pt.x, pt.y);
    ctx.fillStyle = '#ffffff';
    ctx.fillText(label, pt.x, pt.y);
  }
}

function canvasToObjectURL(canvas) {
  // toBlob is async but urlFor must return synchronously, so go through the
  // (synchronous) data URL and rewrap the bytes as a Blob.
  const dataUrl = canvas.toDataURL('image/png');
  const bin = atob(dataUrl.slice(dataUrl.indexOf(',') + 1));
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return URL.createObjectURL(new Blob([bytes], { type: 'image/png' }));
}

function renderDemoFrame(stamp) {
  const lut = getLUT();
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = SIZE;
  const ctx = canvas.getContext('2d');

  // Black frame + ocean disk from the per-pixel inverse-projection mask.
  const img = ctx.createImageData(SIZE, SIZE);
  const d = img.data;
  for (let p = 0, q = 0; p < SIZE * SIZE; p++, q += 4) {
    if (lut.mask[p]) {
      d[q] = 12;
      d[q + 1] = 52;
      d[q + 2] = 108;
    }
    d[q + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);

  const horizon = horizonPath();
  ctx.save();
  ctx.clip(horizon);
  drawGraticule(ctx);
  drawContinents(ctx);
  ctx.restore();
  ctx.lineWidth = 2;
  ctx.strokeStyle = 'rgba(90, 130, 180, 0.9)';
  ctx.stroke(horizon); // smooth limb over the aliased pixel mask

  applyTerminator(ctx, stampToDate(stamp), lut);
  drawLimbMarkers(ctx); // after the terminator: orientation aids stay bright

  ctx.font = '18px ui-monospace, Menlo, monospace';
  ctx.textAlign = 'left';
  ctx.textBaseline = 'alphabetic';
  ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
  ctx.fillText(stamp, 12, SIZE - 14); // corner, outside the disk

  return canvasToObjectURL(canvas);
}
