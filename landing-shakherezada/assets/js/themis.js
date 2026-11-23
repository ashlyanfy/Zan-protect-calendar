/* ============================================================
   ФЕМИДА — постоянный 3D-фон лендинга (Three.js r169, локально)

   Канвас зафиксирован на весь экран позади контента.
   Камера летит по «якорным ракурсам», привязанным к секциям:
   hero — статуя в полный рост без текста, затем наезд на лицо,
   дальше в каждой секции свой ракурс (весы, профиль, меч, отъезд).
   Прокрутка плавно интерполирует камеру между якорями и
   подкручивает статую; поверх — лёгкое «дыхание» и параллакс мыши.
   ============================================================ */
import * as THREE from '../vendor/three.module.min.js';
import { GLTFLoader } from '../vendor/GLTFLoader.js';
import { MeshoptDecoder } from '../vendor/meshopt_decoder.module.js';

const MODEL_URL = 'assets/models/themis.glb';
const MODEL_HEIGHT = 3.0;

const COL = {
  body: 0x16445f,
  bodyDark: 0x0a2435,
  metal: 0x3f93b8,
  accent: 0x0af0ff,
  glow: 0x00b4dc,
};

/* ── якорные ракурсы: секция, точка внутри неё (0..1) и камера ──
   x — горизонтальный сдвиг кадра (минус = статуя уходит вправо),
   spin — поворот статуи (убывает ⇒ при прокрутке она вращается). */
const ANCHORS = [
  // первый экран: полный рост, по центру, без текста
  { sel: '#hero',       at: 0.00, dist: 7.6, camY: 1.75, lookY: 1.42, x: 0,     spin: -0.15 },
  // текст въехал — статуя правее, лицом к зрителю
  { sel: '#hero',       at: 0.85, dist: 4.2, camY: 2.1,  lookY: 1.95, x: -1.55, spin: 0 },
  // «Обо мне»: крупный план слева (фото юриста — справа)
  { sel: '#about',      at: 0.45, dist: 2.4, camY: 2.45, lookY: 2.4,  x: 0.9,   spin: 0.25 },
  // «Услуги»: весы крупным планом
  { sel: '#services',   at: 0.4,  dist: 2.9, camY: 2.05, lookY: 2.05, x: 0.9,   spin: -2.35 },
  // фотолента: широкий переходный план
  { sel: '#imgband',    at: 0.5,  dist: 5.8, camY: 1.9,  lookY: 1.55, x: 0,     spin: -3.3 },
  // «Преимущества»: сторона с мечом
  { sel: '#advantages', at: 0.45, dist: 2.8, camY: 1.45, lookY: 1.5,  x: -0.55, spin: -4.6 },
  // CTA: отъезд, статуя в полный рост, камера сверху
  { sel: '#cta',        at: 0.5,  dist: 8.4, camY: 3.2,  lookY: 1.5,  x: 0,     spin: -6.0 },
  // контакты: финал — снова лицом к зрителю
  { sel: '#contacts',   at: 0.95, dist: 9.4, camY: 1.35, lookY: 1.7,  x: 0,     spin: -6.43 },
];

const canvas = document.getElementById('themis-canvas');
if (canvas) boot();

function boot() {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const mobile = innerWidth < 768;

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: !mobile, alpha: true, powerPreference: 'high-performance' });
  } catch (err) {
    document.body.classList.add('no-3d');
    return;
  }
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, mobile ? 1.5 : 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.08;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
  const lookAt = new THREE.Vector3(0, 1.5, 0);

  scene.environment = buildEnvironment(renderer);

  /* ── свет ── */
  scene.add(new THREE.HemisphereLight(0x7fe6ff, 0x030c14, 0.55));
  const key = new THREE.DirectionalLight(0xd8f6ff, 2.4);
  key.position.set(3.2, 5.4, 4.2);
  scene.add(key);
  const rim = new THREE.DirectionalLight(COL.glow, 3.2);
  rim.position.set(-4.4, 2.4, -3.2);
  scene.add(rim);
  const fill = new THREE.PointLight(COL.accent, 14, 9, 2);
  fill.position.set(1.8, 1.2, 2.6);
  scene.add(fill);
  const under = new THREE.PointLight(COL.glow, 8, 6, 2);
  under.position.set(0, 0.1, 1.4);
  scene.add(under);

  /* ── центральный свет интро: прожектор сверху + видимый конус.
        Гаснет по мере прокрутки первого экрана (см. frame) ── */
  const spot = new THREE.SpotLight(0xcdeeff, 0, 30, 0.4, 0.55, 1);
  spot.position.set(0, 8.5, 1.4);
  spot.target.position.set(0, 1.3, 0);
  scene.add(spot);
  scene.add(spot.target);

  const cone = buildLightCone();
  scene.add(cone);

  /* ── статуя ── */
  const pivot = new THREE.Group();
  scene.add(pivot);
  pivot.add(buildPedestal());

  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  loader.load(
    MODEL_URL,
    gltf => pivot.add(fitModel(gltf.scene)),
    undefined,
    () => pivot.add(buildThemis({ mobile }))   // запасная процедурная фигура
  );

  scene.add(glowPlane(7.5, 0x0af0ff, 0.17, new THREE.Vector3(0, 1.6, -2.2)));
  const floorGlow = glowPlane(5.2, 0x00b4dc, 0.3, new THREE.Vector3(0, -0.23, 0));
  floorGlow.rotation.x = -Math.PI / 2;
  scene.add(floorGlow);

  /* ── размер: канвас всегда во весь экран ── */
  let aspectFit = 1;
  function resize() {
    const w = innerWidth, h = innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    aspectFit = THREE.MathUtils.clamp(1 / camera.aspect, 1, 1.9);
    rebuildTrack();
  }

  /* ── трек камеры из якорей ── */
  let track = [];
  function rebuildTrack() {
    const vh = innerHeight;
    const maxScroll = Math.max(1, document.documentElement.scrollHeight - vh);
    track = [];
    for (const a of ANCHORS) {
      const sec = document.querySelector(a.sel);
      if (!sec) continue;
      const r = sec.getBoundingClientRect();
      const top = r.top + scrollY;
      const y = THREE.MathUtils.clamp(top + a.at * r.height - vh * 0.5, 0, maxScroll);
      track.push({ y, a });
    }
    track.sort((p, q) => p.y - q.y);
  }

  function sampleTrack(s) {
    if (!track.length) return ANCHORS[0];
    if (s <= track[0].y) return track[0].a;
    const last = track[track.length - 1];
    if (s >= last.y) return last.a;
    for (let i = 0; i < track.length - 1; i++) {
      const p = track[i], q = track[i + 1];
      if (s >= p.y && s <= q.y) {
        const t = smooth((s - p.y) / Math.max(1, q.y - p.y));
        return {
          dist: THREE.MathUtils.lerp(p.a.dist, q.a.dist, t),
          camY: THREE.MathUtils.lerp(p.a.camY, q.a.camY, t),
          lookY: THREE.MathUtils.lerp(p.a.lookY, q.a.lookY, t),
          x: THREE.MathUtils.lerp(p.a.x, q.a.x, t),
          spin: THREE.MathUtils.lerp(p.a.spin, q.a.spin, t),
        };
      }
    }
    return last.a;
  }

  window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(resize, 150); });
  let rt;
  resize();
  // высоты секций зависят от шрифтов/картинок — пересчитать после полной загрузки
  window.addEventListener('load', rebuildTrack);

  /* ── лёгкая инерция от прокрутки ── */
  let lastScroll = scrollY, spinKick = 0;
  addEventListener('scroll', () => {
    spinKick += (scrollY - lastScroll) * 0.0009;
    spinKick = THREE.MathUtils.clamp(spinKick, -0.3, 0.3);
    lastScroll = scrollY;
  }, { passive: true });

  const pointer = { x: 0, y: 0, cx: 0, cy: 0 };
  addEventListener('mousemove', e => {
    pointer.x = (e.clientX / innerWidth) * 2 - 1;
    pointer.y = (e.clientY / innerHeight) * 2 - 1;
  }, { passive: true });

  // служебная настройка ракурсов из консоли: __setCam({dist,camY,lookY,x,spin}) / __setCam(null)
  window.__setCam = v => { camOverride = v; };
  let camOverride = null;

  /* ── цикл ── */
  const clock = new THREE.Clock();
  const cur = { ...sampleTrack(0) };
  let raf = null;

  function frame() {
    const dt = Math.min(clock.getDelta(), 0.05);
    const t = clock.elapsedTime;

    // свет интро: полный на первом экране, гаснет при прокрутке
    const heroT = smooth(THREE.MathUtils.clamp(1 - scrollY / (innerHeight * 0.85), 0, 1));
    spot.intensity = 95 * heroT;
    cone.material.opacity = 0.13 * heroT;
    cone.visible = heroT > 0.01;
    key.intensity = 2.4 - 1.1 * heroT;      // остальной свет чуть приглушён,
    rim.intensity = 3.2 - 1.2 * heroT;      // пока работает прожектор

    const target = camOverride || sampleTrack(scrollY);
    const k = 1 - Math.exp(-dt * 3.2);           // кинематографичная плавность
    cur.dist += (target.dist - cur.dist) * k;
    cur.camY += (target.camY - cur.camY) * k;
    cur.lookY += (target.lookY - cur.lookY) * k;
    cur.x += (target.x - cur.x) * k;
    cur.spin += (target.spin - cur.spin) * k;

    spinKick *= Math.pow(0.9, dt * 60);
    const sway = reduce ? 0 : Math.sin(t * 0.35) * 0.035;
    pivot.rotation.y = cur.spin + spinKick + sway;
    pivot.rotation.z = reduce ? 0 : Math.sin(t * 0.4) * 0.008;

    pointer.cx += (pointer.x - pointer.cx) * 0.05;
    pointer.cy += (pointer.y - pointer.cy) * 0.05;

    const xOff = cur.x * (mobile ? 0.25 : 1);
    camera.position.set(
      xOff + pointer.cx * 0.35,
      cur.camY + pointer.cy * -0.2,
      cur.dist * aspectFit
    );
    lookAt.set(xOff, cur.lookY, 0);
    camera.lookAt(lookAt);

    renderer.render(scene, camera);
    raf = requestAnimationFrame(frame);
  }

  function start() { if (!raf) { clock.getDelta(); raf = requestAnimationFrame(frame); } }
  function stop() { if (raf) { cancelAnimationFrame(raf); raf = null; } }
  document.addEventListener('visibilitychange', () => { document.hidden ? stop() : start(); });
  start();
}

/* ============================================================
   Подгонка загруженной модели: высота, центровка, синий металл
   ============================================================ */
function fitModel(root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = box.getSize(new THREE.Vector3());
  root.scale.setScalar(MODEL_HEIGHT / (size.y || 1));
  root.rotation.y = -Math.PI / 2;        // лицом к зрителю при spin = 0

  box.setFromObject(root);               // после масштаба и поворота
  const c = box.getCenter(new THREE.Vector3());
  root.position.x -= c.x;
  root.position.z -= c.z;
  root.position.y -= box.min.y;          // ставим на пьедестал

  root.traverse(o => {
    if (!o.isMesh) return;
    const src = o.material || {};
    const m = new THREE.MeshPhysicalMaterial({
      color: 0x2a7fab, metalness: 0.9, roughness: 0.3,
      clearcoat: 0.25, clearcoatRoughness: 0.35, envMapIntensity: 1.5,
      sheen: 0.35, sheenColor: new THREE.Color(0x8df2ff),
    });
    if (src.normalMap) { m.normalMap = src.normalMap; m.normalScale = src.normalScale; }
    o.material = m;
    o.frustumCulled = false;
  });
  return root;
}

/* Пьедестал со светящимися кольцами */
function buildPedestal() {
  const g = new THREE.Group();
  const dark = new THREE.MeshPhysicalMaterial({
    color: COL.bodyDark, metalness: 0.5, roughness: 0.45, envMapIntensity: 1.1,
  });
  const accent = new THREE.MeshStandardMaterial({
    color: COL.accent, emissive: COL.accent, emissiveIntensity: 1.25,
    metalness: 0.3, roughness: 0.25,
  });

  const d1 = new THREE.Mesh(new THREE.CylinderGeometry(0.84, 0.88, 0.1, 64), dark);
  d1.position.y = -0.05;
  g.add(d1);
  const d2 = new THREE.Mesh(new THREE.CylinderGeometry(0.97, 1.02, 0.13, 64), dark);
  d2.position.y = -0.165;
  g.add(d2);

  const ring1 = new THREE.Mesh(new THREE.TorusGeometry(0.88, 0.008, 8, 96), accent);
  ring1.position.y = -0.002;
  ring1.rotation.x = Math.PI / 2;
  g.add(ring1);
  const ring2 = new THREE.Mesh(new THREE.TorusGeometry(1.03, 0.006, 8, 96), accent);
  ring2.position.y = -0.1;
  ring2.rotation.x = Math.PI / 2;
  g.add(ring2);
  return g;
}

/* ============================================================
   Запасная процедурная фигура (если GLB недоступен)
   ============================================================ */
function buildThemis({ mobile }) {
  const SEG = mobile ? 48 : 96;
  const g = new THREE.Group();

  const body = new THREE.MeshPhysicalMaterial({
    color: COL.body, metalness: 0.88, roughness: 0.34,
    clearcoat: 0.22, clearcoatRoughness: 0.4,
    envMapIntensity: 1.35,
    sheen: 0.5, sheenColor: new THREE.Color(0x8df2ff), sheenRoughness: 0.55,
  });
  const metal = new THREE.MeshPhysicalMaterial({
    color: COL.metal, metalness: 0.95, roughness: 0.18, envMapIntensity: 1.9,
  });
  const dark = new THREE.MeshPhysicalMaterial({
    color: COL.bodyDark, metalness: 0.5, roughness: 0.45, envMapIntensity: 1.1,
  });
  const accent = new THREE.MeshStandardMaterial({
    color: COL.accent, emissive: COL.accent, emissiveIntensity: 1.25,
    metalness: 0.3, roughness: 0.25,
  });

  const profile = smoothProfile([
    [0.001, 0.00], [0.52, 0.00], [0.60, 0.05], [0.565, 0.24], [0.505, 0.52],
    [0.445, 0.82], [0.385, 1.12], [0.335, 1.36], [0.292, 1.56], [0.282, 1.66],
    [0.305, 1.8], [0.325, 1.94], [0.335, 2.06], [0.325, 2.16], [0.255, 2.235],
    [0.13, 2.28], [0.09, 2.35], [0.088, 2.46],
  ], 160);
  const figure = new THREE.LatheGeometry(profile, SEG);
  addFolds(figure, { freq: 18, amp: 0.036, freq2: 7, amp2: 0.018, top: 1.6 });
  g.add(new THREE.Mesh(figure, body));

  const beltGeo = new THREE.LatheGeometry(smoothProfile([
    [0.283, 1.6], [0.293, 1.635], [0.293, 1.695], [0.283, 1.73],
  ], 20), SEG);
  addFolds(beltGeo, { freq: 18, amp: 0.036, freq2: 7, amp2: 0.018, top: 1.6 });
  const belt = new THREE.Mesh(beltGeo, accent);
  belt.material.side = THREE.DoubleSide;
  belt.scale.set(1.035, 1, 1.035);
  g.add(belt);

  const head = new THREE.Mesh(new THREE.SphereGeometry(0.16, 48, 40), body);
  head.scale.set(1, 1.2, 1.06);
  head.position.set(0, 2.6, 0.005);
  g.add(head);

  const band = new THREE.Mesh(new THREE.TorusGeometry(0.163, 0.024, 14, 56), accent);
  band.position.set(0, 2.615, 0.005);
  band.rotation.x = Math.PI / 2;
  band.scale.set(1, 1, 1.12);
  g.add(band);

  const hood = new THREE.Mesh(
    new THREE.LatheGeometry(
      smoothProfile([
        [0.03, 2.82], [0.12, 2.76], [0.19, 2.64], [0.215, 2.5], [0.26, 2.34], [0.345, 2.2], [0.40, 2.1],
      ], 48),
      Math.round(SEG * 0.7), Math.PI * 0.28, Math.PI * 1.44
    ),
    body
  );
  hood.material.side = THREE.DoubleSide;
  g.add(hood);

  g.add(new THREE.Mesh(tapered(new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.3, 2.14, 0.02),
    new THREE.Vector3(0.52, 2.08, 0.09),
    new THREE.Vector3(0.7, 2.19, 0.08),
    new THREE.Vector3(0.79, 2.39, 0.05),
    new THREE.Vector3(0.8, 2.47, 0.04),
  ]), 44, 0.078, 16, t => 1 - 0.4 * t), body));
  addJoint(g, body, 0.3, 2.14, 0.02, 0.1);
  addJoint(g, body, 0.8, 2.47, 0.04, 0.055);

  g.add(new THREE.Mesh(tapered(new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.3, 2.13, 0.01),
    new THREE.Vector3(-0.47, 1.88, 0.08),
    new THREE.Vector3(-0.53, 1.64, 0.15),
    new THREE.Vector3(-0.5, 1.45, 0.19),
    new THREE.Vector3(-0.49, 1.38, 0.2),
  ]), 44, 0.078, 16, t => 1 - 0.38 * t), body));
  addJoint(g, body, -0.3, 2.13, 0.01, 0.1);
  addJoint(g, body, -0.49, 1.39, 0.2, 0.055);

  const sword = new THREE.Group();
  const outline = new THREE.Shape();
  outline.moveTo(0.042, 0.02);
  outline.lineTo(0.042, -0.9);
  outline.lineTo(0, -1.04);
  outline.lineTo(-0.042, -0.9);
  outline.lineTo(-0.042, 0.02);
  outline.lineTo(0.042, 0.02);
  const bladeGeo = new THREE.ExtrudeGeometry(outline, {
    depth: 0.022, bevelEnabled: true, bevelThickness: 0.006,
    bevelSize: 0.006, bevelSegments: 2, curveSegments: 4,
  });
  bladeGeo.translate(0, 0, -0.011);
  sword.add(new THREE.Mesh(bladeGeo, metal));
  const guard = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.034, 0.05), metal);
  guard.position.y = 0.035;
  sword.add(guard);
  const grip = new THREE.Mesh(new THREE.CylinderGeometry(0.026, 0.03, 0.17, 16), dark);
  grip.position.y = 0.135;
  sword.add(grip);
  const pommel = new THREE.Mesh(new THREE.SphereGeometry(0.036, 20, 16), accent);
  pommel.position.y = 0.232;
  sword.add(pommel);
  sword.position.set(-0.52, 1.42, 0.25);
  sword.rotation.set(-0.12, 0.26, -0.1);
  g.add(sword);

  const scales = new THREE.Group();
  scales.position.set(0.8, 2.44, 0.04);
  scales.rotation.y = -0.55;
  const hook = new THREE.Mesh(new THREE.TorusGeometry(0.032, 0.009, 10, 28), metal);
  hook.rotation.y = Math.PI / 2;
  scales.add(hook);
  scales.add(rod(new THREE.Vector3(0, -0.02, 0), new THREE.Vector3(0, -0.26, 0), 0.011, metal));
  const ARM = 0.36;
  const beam = new THREE.Group();
  beam.position.y = -0.27;
  const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.014, ARM * 2, 12), metal);
  bar.rotation.z = Math.PI / 2;
  beam.add(bar);
  [-1, 1].forEach(s => {
    const cap = new THREE.Mesh(new THREE.SphereGeometry(0.026, 16, 12), accent);
    cap.position.x = s * ARM;
    beam.add(cap);
  });
  beam.add(new THREE.Mesh(new THREE.SphereGeometry(0.042, 20, 16), metal));
  scales.add(beam);
  const panProf = smoothProfile([
    [0.001, -0.004], [0.055, -0.022], [0.105, -0.042], [0.142, -0.024], [0.148, 0.0],
  ], 40);
  const panY = -0.27 - 0.34;
  [-1, 1].forEach(s => {
    const pan = new THREE.Group();
    pan.position.set(s * ARM, panY, 0);
    const bowl = new THREE.Mesh(new THREE.LatheGeometry(panProf, 48), metal);
    bowl.material.side = THREE.DoubleSide;
    pan.add(bowl);
    pan.add(new THREE.Mesh(new THREE.TorusGeometry(0.149, 0.006, 8, 48), accent));
    for (let k = 0; k < 3; k++) {
      const a = (k / 3) * Math.PI * 2;
      pan.add(rod(
        new THREE.Vector3(Math.cos(a) * 0.14, 0, Math.sin(a) * 0.14),
        new THREE.Vector3(0, 0.34, 0), 0.0045, metal, 6
      ));
    }
    scales.add(pan);
  });
  g.add(scales);
  return g;
}

/* ============================================================
   ХЕЛПЕРЫ
   ============================================================ */
function smoothProfile(pts, count) {
  const curve = new THREE.CatmullRomCurve3(pts.map(([x, y]) => new THREE.Vector3(x, y, 0)));
  return curve.getPoints(count).map(p => new THREE.Vector2(Math.max(p.x, 0.0008), p.y));
}

function addFolds(geo, { freq, amp, freq2, amp2, top }) {
  const p = geo.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
    const r = Math.hypot(x, z);
    if (r < 1e-4) continue;
    const th = Math.atan2(z, x);
    const fade = y > top ? Math.max(0, 1 - (y - top) / 0.45) : 1;
    const d = (Math.sin(th * freq) * amp + Math.sin(th * freq2 + 1.1) * amp2) * fade * Math.min(1, r / 0.25);
    const nr = r + d;
    p.setX(i, (x / r) * nr);
    p.setZ(i, (z / r) * nr);
  }
  p.needsUpdate = true;
  geo.computeVertexNormals();
}

function tapered(curve, tubularSeg, radius, radialSeg, scaleAt) {
  const g = new THREE.TubeGeometry(curve, tubularSeg, radius, radialSeg, false);
  const p = g.attributes.position;
  for (let i = 0; i <= tubularSeg; i++) {
    const c = curve.getPointAt(i / tubularSeg);
    const s = scaleAt(i / tubularSeg);
    for (let j = 0; j <= radialSeg; j++) {
      const idx = i * (radialSeg + 1) + j;
      p.setXYZ(idx,
        c.x + (p.getX(idx) - c.x) * s,
        c.y + (p.getY(idx) - c.y) * s,
        c.z + (p.getZ(idx) - c.z) * s);
    }
  }
  p.needsUpdate = true;
  g.computeVertexNormals();
  return g;
}

function addJoint(parent, mat, x, y, z, r) {
  const m = new THREE.Mesh(new THREE.SphereGeometry(r, 20, 14), mat);
  m.position.set(x, y, z);
  parent.add(m);
}

function rod(a, b, r, mat, seg = 10) {
  const d = new THREE.Vector3().subVectors(b, a);
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, d.length(), seg, 1), mat);
  m.position.copy(a).addScaledVector(d, 0.5);
  m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.clone().normalize());
  return m;
}

function glowPlane(size, color, opacity, pos) {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const ctx = c.getContext('2d');
  const col = new THREE.Color(color);
  const rgb = Math.round(col.r * 255) + ',' + Math.round(col.g * 255) + ',' + Math.round(col.b * 255);
  const grad = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
  grad.addColorStop(0, 'rgba(' + rgb + ',1)');
  grad.addColorStop(0.45, 'rgba(' + rgb + ',.28)');
  grad.addColorStop(1, 'rgba(' + rgb + ',0)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 256, 256);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(size, size),
    new THREE.MeshBasicMaterial({
      map: tex, transparent: true, opacity,
      blending: THREE.AdditiveBlending, depthWrite: false,
    })
  );
  mesh.position.copy(pos);
  return mesh;
}

/* видимый конус света: цилиндр с вертикальным градиентом, additive */
function buildLightCone() {
  const c = document.createElement('canvas');
  c.width = 4; c.height = 256;
  const ctx = c.getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 0, 256);
  grad.addColorStop(0, 'rgba(205,238,255,.9)');
  grad.addColorStop(0.5, 'rgba(160,220,250,.35)');
  grad.addColorStop(1, 'rgba(120,200,245,0)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 4, 256);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;

  const geo = new THREE.CylinderGeometry(0.32, 2.35, 7.8, 48, 1, true);
  const mat = new THREE.MeshBasicMaterial({
    map: tex, transparent: true, opacity: 0.13,
    blending: THREE.AdditiveBlending, depthWrite: false,
    side: THREE.DoubleSide,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(0, 8.5 - 3.9, 0.35);   // от прожектора вниз к статуе
  mesh.renderOrder = 2;
  return mesh;
}

function buildEnvironment(renderer) {
  const scene = new THREE.Scene();
  const mat = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    uniforms: {
      top: { value: new THREE.Color(0x1c7fa6) },
      mid: { value: new THREE.Color(0x07283c) },
      bottom: { value: new THREE.Color(0x02070c) },
      hot: { value: new THREE.Color(0xbdf3ff) },
    },
    vertexShader: [
      'varying vec3 vP;',
      'void main(){ vP = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
    ].join('\n'),
    fragmentShader: [
      'uniform vec3 top, mid, bottom, hot;',
      'varying vec3 vP;',
      'void main(){',
      '  vec3 n = normalize(vP);',
      '  float h = n.y * 0.5 + 0.5;',
      '  vec3 c = mix(bottom, mid, smoothstep(0.0, 0.5, h));',
      '  c = mix(c, top, smoothstep(0.5, 1.0, h));',
      '  float s = smoothstep(0.78, 1.0, dot(n, normalize(vec3(0.45, 0.8, 0.4))));',
      '  c += hot * s * 1.5;',
      '  gl_FragColor = vec4(c, 1.0);',
      '}',
    ].join('\n'),
  });
  scene.add(new THREE.Mesh(new THREE.SphereGeometry(12, 32, 24), mat));
  const pmrem = new THREE.PMREMGenerator(renderer);
  const tex = pmrem.fromScene(scene, 0.03).texture;
  pmrem.dispose();
  return tex;
}

function smooth(t) { return t * t * (3 - 2 * t); }
