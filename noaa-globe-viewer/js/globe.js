import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const CACHE_CAPACITY = 24;

const GLOBE_VERT = /* glsl */ `
varying vec3 vModelPos;
varying vec3 vWorldNormal;
varying vec3 vWorldPos;
void main() {
  vModelPos = position;
  vec4 wp = modelMatrix * vec4(position, 1.0);
  vWorldPos = wp.xyz;
  vWorldNormal = normalize(mat3(modelMatrix) * normal);
  gl_Position = projectionMatrix * viewMatrix * wp;
}
`;

// Geostationary forward projection onto the GOES-R ABI fixed grid
// (GOES-R PUG L1b vol. 3, GRS80 ellipsoid). Model space: y = north pole
// axis, +z = sub-satellite meridian, east toward +x — so the default
// camera on +z sees the sub-satellite point centered with east on the
// right, and lonRel = atan(p.x, p.z) equals (lon - lon0) directly.
const GLOBE_FRAG = /* glsl */ `
uniform sampler2D uTex;
uniform float uHasTex;
uniform float uSatLon; // sub-satellite longitude, radians

varying vec3 vModelPos;
varying vec3 vWorldNormal;
varying vec3 vWorldPos;

const float REQ     = 6378137.0;
const float RPOL    = 6356752.31414;
const float SAT_H   = 42164160.0;     // satellite distance from Earth center
const float E2      = 0.0066943800229;
const float EXTENT  = 0.151872;       // half-width of the FD scan, rad
const float POL2    = 0.9933056200;   // rpol^2/req^2
const float INV_POL2 = 1.0067394968;  // req^2/rpol^2
// |d(vis)/d(arc)| near the limb ~= 2.78e14 m^2/rad, so 0.3 deg of arc
// corresponds to ~1.45e12 m^2 of the visibility metric.
const float LIMB_FEATHER = 1.45e12;

float gridLine(float deg, float aa) {
  float d = abs(fract(deg / 15.0 + 0.5) - 0.5) * 15.0; // deg to nearest 15-deg line
  return 1.0 - smoothstep(0.0, aa * 1.6, d);
}

void main() {
  vec3 p = normalize(vModelPos);
  float lat = asin(clamp(p.y, -1.0, 1.0));
  // atan(0,0) is undefined in GLSL; only reachable at the exact poles,
  // where longitude is arbitrary anyway.
  float lonRel = (p.x == 0.0 && p.z == 0.0) ? 0.0 : atan(p.x, p.z); // lon - lon0
  float lon = lonRel + uSatLon;

  // Geocentric latitude: atan(POL2 * tan(lat)) in two-arg form so it
  // stays finite at lat = +/-90 where tan() blows up.
  float phic = atan(POL2 * sin(lat), cos(lat));
  float cosc = cos(phic);
  float rc = RPOL / sqrt(1.0 - E2 * cosc * cosc);
  float sx = SAT_H - rc * cosc * cos(lonRel);
  float sy = -rc * cosc * sin(lonRel);
  float sz = rc * sin(phic);

  // Visible from the satellite when vis >= 0 (else the far side, where
  // the scan angles alias back inside the frame — this test, not the uv
  // range check, is what rejects the mirrored back hemisphere).
  float vis = SAT_H * (SAT_H - sx) - (sy * sy + INV_POL2 * sz * sz);
  float scanx = asin(clamp(-sy / length(vec3(sx, sy, sz)), -1.0, 1.0));
  float scany = atan(sz, sx);         // sx > 0 wherever vis >= 0
  vec2 uv = vec2((scanx / EXTENT + 1.0) * 0.5,
                 (1.0 - scany / EXTENT) * 0.5); // +scany = north = image top

  float inFrame = step(abs(uv.x - 0.5), 0.5) * step(abs(uv.y - 0.5), 0.5);
  float dayMask = smoothstep(0.0, LIMB_FEATHER, vis) * inFrame * uHasTex;
  vec3 dayColor = texture2D(uTex, clamp(uv, 0.0, 1.0)).rgb;

  // "No data" side: dark blue-gray + faint 15-deg graticule + fresnel rim.
  float latDeg = degrees(lat);
  float lonDeg = degrees(lon); // 360 is a multiple of 15: wrap-safe grid
  float aaLat = fwidth(latDeg);
  float aaLon = fwidth(lonDeg);
  float grat = gridLine(latDeg, aaLat);
  // Fade lon lines where their screen derivative explodes (poles, atan seam).
  grat = max(grat, gridLine(lonDeg, aaLon) * (1.0 - smoothstep(4.0, 9.0, aaLon)));
  vec3 night = vec3(0.0045, 0.0065, 0.010);
  night += grat * vec3(0.010, 0.016, 0.026);
  vec3 viewDir = normalize(cameraPosition - vWorldPos);
  float fres = pow(1.0 - max(dot(normalize(vWorldNormal), viewDir), 0.0), 3.0);
  night += fres * vec3(0.010, 0.018, 0.032);

  gl_FragColor = vec4(mix(night, dayColor, dayMask), 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

const ATMO_VERT = /* glsl */ `
varying vec3 vViewNormal;
void main() {
  vViewNormal = normalize(normalMatrix * normal);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

// BackSide shell: visible fragments have view-space normal z in (-1, 0];
// glow peaks at the globe limb and fades outward across the shell ring.
const ATMO_FRAG = /* glsl */ `
varying vec3 vViewNormal;
void main() {
  float glow = pow(clamp(0.55 - normalize(vViewNormal).z, 0.0, 1.0), 8.0);
  gl_FragColor = vec4(vec3(0.10, 0.22, 0.45) * glow, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export class GlobeViewer {
  constructor(containerEl, { satLonDeg = -75.2 } = {}) {
    this._container = containerEl;
    this._disposed = false;
    this._seq = 0;
    this._cache = new Map(); // url -> THREE.Texture, insertion order = LRU order
    this._pending = new Map(); // url -> Promise<THREE.Texture>
    this._displayedUrl = null;
    this._readyFired = false;
    this._readyPending = false;
    this._readyCbs = [];

    const w = Math.max(1, containerEl.clientWidth);
    const h = Math.max(1, containerEl.clientHeight);

    this._renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    this._renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this._renderer.setSize(w, h);
    this._renderer.domElement.style.display = 'block';
    containerEl.appendChild(this._renderer.domElement);
    this._maxAniso = this._renderer.capabilities.getMaxAnisotropy();

    this._scene = new THREE.Scene();
    this._scene.background = new THREE.Color(0x010208);

    this._camera = new THREE.PerspectiveCamera(36, w / h, 0.02, 150);
    // The shader pins the sub-satellite meridian to +z, so starting on +z
    // means starting over the sub-satellite point for any satLonDeg.
    this._camera.position.set(0, 0, 2.8);

    this._controls = new OrbitControls(this._camera, this._renderer.domElement);
    this._controls.enableDamping = true;
    this._controls.dampingFactor = 0.07;
    this._controls.enablePan = false;
    this._controls.minDistance = 1.15;
    this._controls.maxDistance = 6;
    this._controls.rotateSpeed = 0.8;
    this._controls.zoomSpeed = 0.7;

    // 1x1 black placeholder so uTex is always a valid sampler before the
    // first frame arrives (uHasTex gates it out of the output).
    this._placeholder = new THREE.DataTexture(new Uint8Array([0, 0, 0, 255]), 1, 1);
    this._placeholder.needsUpdate = true;

    this._material = new THREE.ShaderMaterial({
      uniforms: {
        uTex: { value: this._placeholder },
        uHasTex: { value: 0 },
        uSatLon: { value: THREE.MathUtils.degToRad(satLonDeg) },
      },
      vertexShader: GLOBE_VERT,
      fragmentShader: GLOBE_FRAG,
    });
    this._globeGeom = new THREE.SphereGeometry(1, 256, 128);
    this._scene.add(new THREE.Mesh(this._globeGeom, this._material));

    this._atmoGeom = new THREE.SphereGeometry(1.035, 96, 48);
    this._atmoMaterial = new THREE.ShaderMaterial({
      vertexShader: ATMO_VERT,
      fragmentShader: ATMO_FRAG,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      transparent: true,
      depthWrite: false,
    });
    this._scene.add(new THREE.Mesh(this._atmoGeom, this._atmoMaterial));

    this._buildStarfield();

    this._loader = new THREE.TextureLoader();
    this._loader.setCrossOrigin('anonymous');

    this._onWindowResize = () => this.resize();
    window.addEventListener('resize', this._onWindowResize);
    if (typeof ResizeObserver !== 'undefined') {
      this._resizeObserver = new ResizeObserver(() => this.resize());
      this._resizeObserver.observe(containerEl);
    }

    this._renderer.setAnimationLoop(() => {
      this._controls.update();
      this._renderer.render(this._scene, this._camera);
      if (this._readyPending) {
        this._readyPending = false;
        this._readyFired = true;
        for (const cb of this._readyCbs.splice(0)) {
          try { cb(); } catch (err) { console.error(err); }
        }
      }
    });
  }

  _buildStarfield() {
    const rand = mulberry32(0x9e0e5); // seeded: same sky every load
    const count = 1500;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const z = rand() * 2 - 1;
      const t = rand() * Math.PI * 2;
      const r = Math.sqrt(Math.max(0, 1 - z * z));
      positions[i * 3] = 60 * r * Math.cos(t);
      positions[i * 3 + 1] = 60 * z;
      positions[i * 3 + 2] = 60 * r * Math.sin(t);
      const b = 0.25 + 0.75 * rand() * rand(); // mostly faint stars
      const warm = rand();
      colors[i * 3] = b * (0.85 + 0.15 * warm);
      colors[i * 3 + 1] = b * (0.88 + 0.08 * warm);
      colors[i * 3 + 2] = b;
    }
    this._starGeom = new THREE.BufferGeometry();
    this._starGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    this._starGeom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    this._starMaterial = new THREE.PointsMaterial({
      size: 1.6,
      sizeAttenuation: false,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
      depthWrite: false,
    });
    this._scene.add(new THREE.Points(this._starGeom, this._starMaterial));
  }

  // Latest-wins: every call bumps _seq; only the call whose seq is still
  // current when its texture is ready gets displayed. Superseded calls
  // resolve quietly ("dropped"); a failed load of the *current* call
  // rejects and leaves the previous texture on screen untouched.
  async showFrame(url) {
    const seq = ++this._seq;
    if (this._disposed) return;
    let tex = this._cacheGet(url);
    if (!tex) {
      try {
        tex = await this._load(url);
      } catch (err) {
        if (this._disposed || seq !== this._seq) return; // dropped
        throw err instanceof Error ? err : new Error(String(err));
      }
    }
    if (this._disposed || seq !== this._seq) return; // dropped
    this._displayedUrl = url;
    this._material.uniforms.uTex.value = tex;
    this._material.uniforms.uHasTex.value = 1;
    if (!this._readyFired) this._readyPending = true;
  }

  onReady(cb) {
    if (this._readyFired) queueMicrotask(() => cb());
    else this._readyCbs.push(cb);
  }

  resize() {
    if (this._disposed) return;
    const w = Math.max(1, this._container.clientWidth);
    const h = Math.max(1, this._container.clientHeight);
    this._camera.aspect = w / h;
    this._camera.updateProjectionMatrix();
    this._renderer.setSize(w, h);
  }

  dispose() {
    if (this._disposed) return;
    this._disposed = true;
    this._seq++; // strand any in-flight loads
    this._renderer.setAnimationLoop(null);
    window.removeEventListener('resize', this._onWindowResize);
    if (this._resizeObserver) this._resizeObserver.disconnect();
    this._controls.dispose();
    for (const tex of this._cache.values()) tex.dispose();
    this._cache.clear();
    this._pending.clear();
    this._placeholder.dispose();
    this._globeGeom.dispose();
    this._material.dispose();
    this._atmoGeom.dispose();
    this._atmoMaterial.dispose();
    this._starGeom.dispose();
    this._starMaterial.dispose();
    this._renderer.dispose();
    const canvas = this._renderer.domElement;
    if (canvas.parentNode) canvas.parentNode.removeChild(canvas);
  }

  _cacheGet(url) {
    const tex = this._cache.get(url);
    if (!tex) return null;
    this._cache.delete(url); // refresh recency
    this._cache.set(url, tex);
    return tex;
  }

  _cacheInsert(url, tex) {
    const existing = this._cache.get(url);
    if (existing) {
      if (existing !== tex) tex.dispose(); // lost a same-url race; keep first
      this._cache.delete(url);
      this._cache.set(url, existing);
      return existing;
    }
    this._cache.set(url, tex);
    while (this._cache.size > CACHE_CAPACITY) {
      const oldest = this._cache.keys().next().value;
      const evicted = this._cache.get(oldest);
      this._cache.delete(oldest);
      if (oldest === this._displayedUrl) {
        this._cache.set(oldest, evicted); // never dispose the visible texture
        continue;
      }
      evicted.dispose();
    }
    return tex;
  }

  _load(url) {
    let promise = this._pending.get(url);
    if (promise) return promise;
    promise = new Promise((resolve, reject) => {
      this._loader.load(
        url,
        (tex) => {
          this._pending.delete(url);
          if (this._disposed) {
            tex.dispose();
            reject(new Error('GlobeViewer disposed'));
            return;
          }
          tex.colorSpace = THREE.SRGBColorSpace;
          tex.anisotropy = this._maxAniso;
          // The fixed-grid v formula assumes v=0 is the image's top row,
          // so upload unflipped; orientation lives entirely in the shader.
          tex.flipY = false;
          tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
          resolve(this._cacheInsert(url, tex));
        },
        undefined,
        () => {
          this._pending.delete(url);
          reject(new Error(`Failed to load frame image: ${url}`));
        }
      );
    });
    this._pending.set(url, promise);
    return promise;
  }
}
