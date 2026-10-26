// Shared helpers for motion3d scenes: renderer + bloom, seeded randomness, easing,
// timeline maths and HTML overlay helpers. Everything is a pure function of t.
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

export const params = new URLSearchParams(location.search);
export const W = Number(params.get("w") || 1080);
export const H = Number(params.get("h") || 1920);

export function rng(seed = 1) {
  return () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, k) => a + (b - a) * k;
// 0 before t0, 1 after t1, eased in between.
export const span = (t, t0, t1, ease = easeInOutCubic) => ease(clamp((t - t0) / (t1 - t0)));
export const easeInOutCubic = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
export const easeOutCubic = (x) => 1 - Math.pow(1 - x, 3);
export const easeOutBack = (x) => 1 + 2.2 * Math.pow(x - 1, 3) + 1.2 * Math.pow(x - 1, 2);
// Visible between t0 and t1 with fades of `f` seconds: 0..1.
export const window01 = (t, t0, t1, f = 0.35) => Math.min(span(t, t0, t0 + f, easeOutCubic), 1 - span(t, t1 - f, t1));

export function makeRenderer({ bloom = { strength: 0.9, radius: 0.55, threshold: 0.72 } } = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(W, H);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  document.getElementById("stage").appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, W / H, 0.05, 200);
  let composer = null;
  if (bloom) {
    composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));
    // Bloom at half resolution: the glow is soft anyway and the software GPU is slow.
    composer.addPass(new UnrealBloomPass(new THREE.Vector2(W / 2, H / 2), bloom.strength, bloom.radius, bloom.threshold));
    composer.addPass(new OutputPass());
  }
  const draw = () => (composer ? composer.render() : renderer.render(scene, camera));
  return { renderer, scene, camera, draw };
}

// Screen position (px) of a world point, for HTML labels that track 3D objects.
export function toScreen(camera, v) {
  const p = v.clone().project(camera);
  return { x: (p.x * 0.5 + 0.5) * W, y: (-p.y * 0.5 + 0.5) * H, behind: p.z > 1 };
}

export function style(el, props) {
  for (const [k, v] of Object.entries(props)) el.style[k] = v;
}

// A starfield that twinkles as a function of uTime.
export function stars(count = 2500, radius = 60, seed = 7) {
  const r = rng(seed);
  const pos = new Float32Array(count * 3), size = new Float32Array(count), phase = new Float32Array(count);
  for (let i = 0; i < count; i++) {
    const u = r() * 2 - 1, a = r() * Math.PI * 2, s = Math.sqrt(1 - u * u);
    pos.set([s * Math.cos(a) * radius, u * radius, s * Math.sin(a) * radius], i * 3);
    size[i] = 0.6 + Math.pow(r(), 6) * 3.2;
    phase[i] = r() * 6.283;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("size", new THREE.BufferAttribute(size, 1));
  g.setAttribute("phase", new THREE.BufferAttribute(phase, 1));
  const m = new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uScale: { value: H / 1920 } },
    vertexShader: `attribute float size; attribute float phase; uniform float uTime; uniform float uScale; varying float vA;
      void main(){ vA = 0.55 + 0.45*sin(uTime*1.7 + phase); gl_PointSize = size*uScale*2.0; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);} `,
    fragmentShader: `varying float vA; void main(){ float d = length(gl_PointCoord-0.5); float a = smoothstep(0.5,0.0,d); gl_FragColor = vec4(vec3(0.85,0.9,1.0)*a*vA, a*vA);} `,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  });
  return new THREE.Points(g, m);
}

// A soft additive glow sprite (for cores, balls, highlights).
export function glow(color = 0xffd27a, size = 1) {
  const m = new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color(color) }, uOpacity: { value: 1 } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);} `,
    fragmentShader: `uniform vec3 uColor; uniform float uOpacity; varying vec2 vUv;
      void main(){ float d = length(vUv-0.5)*2.0; float a = pow(clamp(1.0-d,0.0,1.0), 2.4); gl_FragColor = vec4(uColor*a*uOpacity, a*uOpacity);} `,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  });
  const s = new THREE.Mesh(new THREE.PlaneGeometry(size, size), m);
  return s;
}

export function ready(scene) {
  window.SCENE = scene;
  document.fonts.ready.then(() => { window.SCENE_READY = true; });
}
