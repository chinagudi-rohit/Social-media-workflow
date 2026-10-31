// Shared helpers for motion3d scenes: renderer + bloom, seeded randomness, easing,
// timeline maths and HTML overlay helpers. Everything is a pure function of t.
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

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

export const easeInOutExpo = (x) =>
  x <= 0 ? 0 : x >= 1 ? 1 : x < 0.5 ? Math.pow(2, 20 * x - 10) / 2 : (2 - Math.pow(2, -20 * x + 10)) / 2;

// `tone`: "aces" (dark, contrasty scenes) or "neutral" (light studio scenes keep their pastels).
// `msaa`: samples on a half-float HDR target, so bloom and tone mapping see real highlights.
// `finish`: a last pass after tone mapping with film grain, vignette and chromatic aberration.
// `shadows`: "vsm" for soft studio shadows.
export function makeRenderer({ bloom = { strength: 0.9, radius: 0.55, threshold: 0.72 }, tone = "aces", msaa = 0,
  finish = null, shadows = null, fov = 32 } = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(W, H);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = tone === "neutral" ? THREE.NeutralToneMapping : THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  if (shadows) {
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = shadows === "vsm" ? THREE.VSMShadowMap : THREE.PCFSoftShadowMap;
  }
  document.getElementById("stage").appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(fov, W / H, 0.05, 200);
  let composer = null, finishPass = null;
  if (bloom || msaa || finish) {
    const target = new THREE.WebGLRenderTarget(W, H, { type: THREE.HalfFloatType, samples: msaa });
    composer = new EffectComposer(renderer, target);
    composer.addPass(new RenderPass(scene, camera));
    // Bloom at half resolution: the glow is soft anyway and the software GPU is slow.
    if (bloom) composer.addPass(new UnrealBloomPass(new THREE.Vector2(W / 2, H / 2), bloom.strength, bloom.radius, bloom.threshold));
    composer.addPass(new OutputPass());
    if (finish) composer.addPass((finishPass = new ShaderPass(FinishShader)));
  }
  if (finishPass) {
    const u = finishPass.uniforms;
    u.uGrain.value = finish.grain ?? 0.035;
    u.uVignette.value = finish.vignette ?? 0.25;
    u.uAberration.value = finish.aberration ?? 0.0015;
    u.uAspect.value = W / H;
  }
  // Grain changes every frame but stays a function of t (seeded by the frame time).
  const draw = (t = 0) => {
    if (finishPass) finishPass.uniforms.uSeed.value = (t * 60.0) % 1000.0;
    composer ? composer.render() : renderer.render(scene, camera);
  };
  return { renderer, scene, camera, draw };
}

const FinishShader = {
  uniforms: { tDiffuse: { value: null }, uSeed: { value: 0 }, uGrain: { value: 0.035 }, uVignette: { value: 0.25 },
    uAberration: { value: 0.0015 }, uAspect: { value: 1 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);} `,
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uSeed, uGrain, uVignette, uAberration, uAspect; varying vec2 vUv;
    float hash(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233)) + uSeed) * 43758.5453); }
    void main(){
      vec2 d = vUv - 0.5;
      vec2 off = d * uAberration * 2.0;
      vec3 c = vec3(texture2D(tDiffuse, vUv + off).r, texture2D(tDiffuse, vUv).g, texture2D(tDiffuse, vUv - off).b);
      float r = length(vec2(d.x * uAspect, d.y)) / length(vec2(0.5 * uAspect, 0.5));
      c *= 1.0 - uVignette * smoothstep(0.45, 1.05, r);
      c += (hash(vUv * 1024.0) - 0.5) * uGrain;
      gl_FragColor = vec4(c, 1.0);
    }`,
};

// Image-based reflections from a neutral studio room (clay sheen, metal, glass).
export function studioEnvironment(renderer, scene, intensity = 0.6) {
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = intensity;
}

// Camera keyframes [{t, pos:[x,y,z], look:[x,y,z]}]: an expo ease between keys (slow drift
// in a scene, a quick whip between scenes) plus a small seeded drift so no frame is static.
export function cameraRig(keys, { drift = 0.06, ease = easeInOutExpo, seed = 3 } = {}) {
  const r = rng(seed), ph = [r() * 6.28, r() * 6.28, r() * 6.28];
  const a = new THREE.Vector3(), b = new THREE.Vector3(), la = new THREE.Vector3(), lb = new THREE.Vector3();
  return (camera, t) => {
    let i = 0;
    while (i < keys.length - 2 && t >= keys[i + 1].t) i++;
    const k0 = keys[i], k1 = keys[Math.min(i + 1, keys.length - 1)];
    const k = k1.t > k0.t ? ease(clamp((t - k0.t) / (k1.t - k0.t))) : 1;
    a.fromArray(k0.pos).lerp(b.fromArray(k1.pos), k);
    la.fromArray(k0.look).lerp(lb.fromArray(k1.look), k);
    a.x += Math.sin(t * 0.7 + ph[0]) * drift;
    a.y += Math.sin(t * 0.53 + ph[1]) * drift * 0.6;
    a.z += Math.sin(t * 0.61 + ph[2]) * drift;
    camera.position.copy(a);
    camera.lookAt(la);
  };
}

// Soft "premium clay": physical material with sheen, plus a fresnel rim light injected into
// the shader so silhouettes read against a light backdrop.
export function clay(color, { rim = 0xffffff, rimStrength = 0.35, roughness = 0.62 } = {}) {
  const m = new THREE.MeshPhysicalMaterial({ color, roughness, metalness: 0, sheen: 1, sheenRoughness: 0.55,
    sheenColor: new THREE.Color(0xffffff), clearcoat: 0.08, clearcoatRoughness: 0.6 });
  m.onBeforeCompile = (shader) => {
    shader.uniforms.uRim = { value: new THREE.Color(rim).multiplyScalar(rimStrength) };
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nuniform vec3 uRim;")
      .replace("#include <opaque_fragment>",
        "outgoingLight += uRim * pow(1.0 - saturate(dot(normal, normalize(vViewPosition))), 3.0);\n#include <opaque_fragment>");
  };
  return m;
}

// Light studio: a gradient backdrop dome and a floor that only shows shadows plus a dotted
// grid fading out with distance.
export function studio(scene, { top = 0xf4f1fb, bottom = 0xfbfaf7, dots = 0xc9c3dc, radius = 60 } = {}) {
  const dome = new THREE.Mesh(new THREE.SphereGeometry(radius, 48, 24), new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false,
    uniforms: { uTop: { value: new THREE.Color(top) }, uBottom: { value: new THREE.Color(bottom) } },
    vertexShader: `varying vec3 vP; void main(){ vP = position; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);} `,
    fragmentShader: `uniform vec3 uTop, uBottom; varying vec3 vP;
      void main(){ float h = clamp(normalize(vP).y * 1.6 + 0.25, 0.0, 1.0); gl_FragColor = vec4(mix(uBottom, uTop, h), 1.0);} `,
  }));
  scene.add(dome);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(radius, radius), new THREE.ShadowMaterial({ opacity: 0.16 }));
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);
  const grid = new THREE.Mesh(new THREE.PlaneGeometry(radius, radius), new THREE.ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: { uColor: { value: new THREE.Color(dots) } },
    vertexShader: `varying vec2 vW; void main(){ vec4 w = modelMatrix*vec4(position,1.0); vW = w.xz; gl_Position = projectionMatrix*viewMatrix*w;} `,
    fragmentShader: `uniform vec3 uColor; varying vec2 vW;
      void main(){ vec2 g = fract(vW * 2.0) - 0.5; float d = length(g); float a = smoothstep(0.07, 0.03, d);
        a *= smoothstep(14.0, 3.0, length(vW)); gl_FragColor = vec4(uColor, a * 0.55);} `,
  }));
  grid.rotation.x = -Math.PI / 2;
  grid.position.y = 0.002;
  scene.add(grid);
  return { dome, floor, grid };
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
