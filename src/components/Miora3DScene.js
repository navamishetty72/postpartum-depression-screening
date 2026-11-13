import {
  AmbientLight,
  BufferAttribute,
  BufferGeometry,
  Color,
  DirectionalLight,
  Group,
  IcosahedronGeometry,
  Mesh,
  MeshBasicMaterial,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
  PerspectiveCamera,
  PointLight,
  Points,
  PointsMaterial,
  Scene,
  SphereGeometry,
  TorusGeometry,
  Vector3,
  WebGLRenderer,
} from 'three';

const hasWebGL = () => {
  if (typeof window === 'undefined' || !('WebGLRenderingContext' in window)) {
    return false;
  }
  try {
    const testCanvas = document.createElement('canvas');
    return Boolean(
      testCanvas.getContext('webgl2') || testCanvas.getContext('webgl')
    );
  } catch {
    return false;
  }
};

const ORB_MODES = {
  share: {
    color: new Color(0xe77498),
    emissive: new Color(0x7a1c3c),
    ringColor: new Color(0xf4b6c4),
    speed: 1.05,
    amp: 0.085,
    freq: 2.1,
    ringSpeed: 0.35,
  },
  understand: {
    color: new Color(0xc73566),
    emissive: new Color(0x691433),
    ringColor: new Color(0xe98ea7),
    speed: 1.75,
    amp: 0.135,
    freq: 3.1,
    ringSpeed: 0.72,
  },
  support: {
    color: new Color(0xe58682),
    emissive: new Color(0x882c3a),
    ringColor: new Color(0xf6cbbd),
    speed: 1.25,
    amp: 0.105,
    freq: 2.4,
    ringSpeed: 0.45,
  },
};

/**
 * Mounts subtle 3D orbiting pearlescent spheres, glass rings, and luminous particles
 * around the Hero portrait.
 */
export const initHero3D = (canvas, container) => {
  if (!canvas || !container || !hasWebGL()) return () => {};

  let renderer;
  try {
    renderer = new WebGLRenderer({
      canvas,
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance',
    });
  } catch {
    return () => {};
  }

  const scene = new Scene();
  const camera = new PerspectiveCamera(36, 1, 0.1, 50);
  camera.position.set(0, 0, 8.2);

  const root = new Group();
  scene.add(root);

  scene.add(new AmbientLight(0xfff4f2, 1.45));
  const keyLight = new DirectionalLight(0xffe8e2, 2.1);
  keyLight.position.set(-4, 5, 6);
  scene.add(keyLight);

  const rimLight = new PointLight(0xd93c75, 2.2, 24);
  rimLight.position.set(4, -3, 3);
  scene.add(rimLight);

  const warmFill = new PointLight(0xffd5c2, 1.8, 22);
  warmFill.position.set(-3, -3, 4);
  scene.add(warmFill);

  // Outer 3D tilted translucent rings framing the portrait
  const ring1 = new Mesh(
    new TorusGeometry(2.38, 0.018, 16, 120),
    new MeshStandardMaterial({
      color: 0xe688a6,
      roughness: 0.3,
      metalness: 0.15,
      transparent: true,
      opacity: 0.48,
    })
  );
  ring1.rotation.set(0.45, -0.35, 0.25);
  root.add(ring1);

  const ring2 = new Mesh(
    new TorusGeometry(2.55, 0.013, 16, 120),
    new MeshStandardMaterial({
      color: 0xf2b5a8,
      roughness: 0.35,
      metalness: 0.1,
      transparent: true,
      opacity: 0.36,
    })
  );
  ring2.rotation.set(-0.52, 0.42, -0.2);
  root.add(ring2);

  // Orbiting 3D pearlescent glass spheres
  const sphereSpecs = [
    { r: 0.2, radius: 2.38, speed: 0.22, phase: 0.2, tiltX: 0.45, tiltZ: 0.25, color: 0xf7b8c7 },
    { r: 0.14, radius: 2.55, speed: -0.18, phase: 2.1, tiltX: -0.52, tiltZ: -0.2, color: 0xe76d94 },
    { r: 0.16, radius: 2.42, speed: 0.16, phase: 3.9, tiltX: 0.35, tiltZ: -0.45, color: 0xfad3c4 },
    { r: 0.11, radius: 2.6, speed: -0.25, phase: 5.0, tiltX: -0.35, tiltZ: 0.4, color: 0xf5a2b8 },
    { r: 0.13, radius: 2.34, speed: 0.19, phase: 1.1, tiltX: 0.65, tiltZ: 0.1, color: 0xffe4e6 },
  ];

  const satellites = sphereSpecs.map((spec) => {
    const pivot = new Group();
    pivot.rotation.set(spec.tiltX, 0, spec.tiltZ);
    const mesh = new Mesh(
      new SphereGeometry(spec.r, 24, 24),
      new MeshPhysicalMaterial({
        color: spec.color,
        roughness: 0.16,
        metalness: 0.06,
        clearcoat: 1.0,
        clearcoatRoughness: 0.12,
      })
    );
    pivot.add(mesh);
    root.add(pivot);
    return { ...spec, mesh };
  });

  // Soft floating particle dust
  const particleCount = 32;
  const positions = new Float32Array(particleCount * 3);
  const particleSeeds = [];
  for (let i = 0; i < particleCount; i++) {
    const angle = (i / particleCount) * Math.PI * 2;
    const dist = 2.0 + (i % 5) * 0.24;
    positions[i * 3] = Math.cos(angle) * dist;
    positions[i * 3 + 1] = Math.sin(angle) * dist;
    positions[i * 3 + 2] = ((i % 7) - 3) * 0.25;
    particleSeeds.push({ angle, dist, speed: 0.12 + (i % 4) * 0.04, bob: i * 0.7 });
  }
  const particleGeo = new BufferGeometry();
  particleGeo.setAttribute('position', new BufferAttribute(positions, 3));
  const particles = new Points(
    particleGeo,
    new PointsMaterial({
      color: 0xd93c75,
      size: 0.055,
      transparent: true,
      opacity: 0.42,
    })
  );
  root.add(particles);

  let targetRotX = 0;
  let targetRotY = 0;
  const onPointerMove = (e) => {
    const rect = container.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const nx = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
    const ny = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
    targetRotY = nx * 0.22;
    targetRotX = -ny * 0.18;
  };
  const onPointerLeave = () => {
    targetRotX = 0;
    targetRotY = 0;
  };

  window.addEventListener('pointermove', onPointerMove, { passive: true });
  container.addEventListener('pointerleave', onPointerLeave);

  const resize = () => {
    const width = container.clientWidth || 465;
    const height = container.clientHeight || 465;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };
  resize();

  const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(resize) : null;
  ro?.observe(container);

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let rafId = 0;
  const start = Date.now();

  const renderFrame = (elapsedSec) => {
    root.rotation.x += (targetRotX - root.rotation.x) * 0.05;
    root.rotation.y += (targetRotY - root.rotation.y) * 0.05;

    ring1.rotation.z = 0.25 + elapsedSec * 0.08;
    ring1.rotation.x = 0.45 + Math.sin(elapsedSec * 0.4) * 0.08;
    ring2.rotation.z = -0.2 - elapsedSec * 0.06;
    ring2.rotation.y = 0.42 + Math.cos(elapsedSec * 0.35) * 0.08;

    satellites.forEach((sat) => {
      const a = sat.phase + elapsedSec * sat.speed;
      sat.mesh.position.set(
        Math.cos(a) * sat.radius,
        Math.sin(a) * sat.radius,
        Math.sin(a * 2) * 0.18
      );
    });

    const posAttr = particleGeo.getAttribute('position');
    for (let i = 0; i < particleCount; i++) {
      const seed = particleSeeds[i];
      const a = seed.angle + elapsedSec * seed.speed * 0.25;
      posAttr.setXYZ(
        i,
        Math.cos(a) * seed.dist,
        Math.sin(a) * seed.dist + Math.sin(elapsedSec * 0.8 + seed.bob) * 0.08,
        Math.cos(elapsedSec * 0.5 + seed.bob) * 0.35
      );
    }
    posAttr.needsUpdate = true;

    renderer.render(scene, camera);
  };

  renderFrame(0);

  if (!reducedMotion) {
    const tick = () => {
      const elapsedSec = (Date.now() - start) / 1000;
      renderFrame(elapsedSec);
      rafId = window.requestAnimationFrame(tick);
    };
    rafId = window.requestAnimationFrame(tick);
  }

  return () => {
    window.cancelAnimationFrame(rafId);
    ro?.disconnect();
    window.removeEventListener('pointermove', onPointerMove);
    container.removeEventListener('pointerleave', onPointerLeave);
    renderer.dispose();
  };
};

/**
 * Mounts an interactive 3D vertex-morphed "Empathy Orb" centerpiece in the Approach section
 * with Share / Understand / Support state transitions.
 */
export const initEmpathyOrb3D = (canvas, container) => {
  if (!canvas || !container || !hasWebGL()) {
    return { setMode: () => {}, destroy: () => {} };
  }

  let renderer;
  try {
    renderer = new WebGLRenderer({
      canvas,
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance',
    });
  } catch {
    return { setMode: () => {}, destroy: () => {} };
  }

  const scene = new Scene();
  const camera = new PerspectiveCamera(38, 1, 0.1, 50);
  camera.position.set(0, 0, 5.4);

  const root = new Group();
  scene.add(root);

  scene.add(new AmbientLight(0xfff4f2, 1.35));
  const keyLight = new DirectionalLight(0xffe9e4, 2.2);
  keyLight.position.set(-3, 4, 5);
  scene.add(keyLight);

  const roseRim = new PointLight(0xd93c75, 2.8, 18);
  roseRim.position.set(3.5, -2.5, 2.5);
  scene.add(roseRim);

  const peachFill = new PointLight(0xffcfb8, 2.0, 18);
  peachFill.position.set(-3, -2, 3);
  scene.add(peachFill);

  // Morphable organic sphere
  const orbGeo = new IcosahedronGeometry(1.12, 24);
  const posAttr = orbGeo.getAttribute('position');
  const basePos = new Float32Array(posAttr.array.length);
  basePos.set(posAttr.array);

  const orbMat = new MeshPhysicalMaterial({
    color: ORB_MODES.share.color.clone(),
    emissive: ORB_MODES.share.emissive.clone(),
    emissiveIntensity: 0.28,
    roughness: 0.22,
    metalness: 0.05,
    clearcoat: 0.9,
    clearcoatRoughness: 0.14,
  });
  const orbMesh = new Mesh(orbGeo, orbMat);
  root.add(orbMesh);

  // Warm inner core glow
  const innerCore = new Mesh(
    new SphereGeometry(0.68, 24, 24),
    new MeshBasicMaterial({
      color: 0xffe4e8,
      transparent: true,
      opacity: 0.45,
    })
  );
  root.add(innerCore);

  // Sculpted 3D orbital halo rings
  const ringMat1 = new MeshStandardMaterial({
    color: ORB_MODES.share.ringColor.clone(),
    roughness: 0.25,
    metalness: 0.2,
    transparent: true,
    opacity: 0.65,
  });
  const halo1 = new Mesh(new TorusGeometry(1.56, 0.022, 16, 100), ringMat1);
  halo1.rotation.set(1.15, 0.35, 0);
  root.add(halo1);

  const halo2 = new Mesh(
    new TorusGeometry(1.78, 0.015, 16, 100),
    new MeshStandardMaterial({
      color: 0xf7cbbd,
      roughness: 0.3,
      metalness: 0.15,
      transparent: true,
      opacity: 0.48,
    })
  );
  halo2.rotation.set(-0.95, 0.55, 0.3);
  root.add(halo2);

  // 3 cue satellites orbiting the Empathy Core
  const cueColors = [0xf8b9c8, 0xc73566, 0xfad2c0];
  const cueOrbs = cueColors.map((c, idx) => {
    const m = new Mesh(
      new SphereGeometry(0.095, 20, 20),
      new MeshPhysicalMaterial({
        color: c,
        roughness: 0.18,
        clearcoat: 1,
      })
    );
    root.add(m);
    return { mesh: m, offset: (idx * Math.PI * 2) / 3, radius: 1.56 + idx * 0.11 };
  });

  let activeMode = ORB_MODES.share;
  let currentSpeed = activeMode.speed;
  let currentAmp = activeMode.amp;
  let currentFreq = activeMode.freq;
  let currentRingSpeed = activeMode.ringSpeed;

  let pointerX = 0;
  let pointerY = 0;
  const onPointerMove = (e) => {
    const rect = container.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    pointerX = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
    pointerY = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
  };
  const onPointerLeave = () => {
    pointerX = 0;
    pointerY = 0;
  };
  container.addEventListener('pointermove', onPointerMove, { passive: true });
  container.addEventListener('pointerleave', onPointerLeave);

  const resize = () => {
    const width = container.clientWidth || 280;
    const height = container.clientHeight || 260;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };
  resize();

  const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(resize) : null;
  ro?.observe(container);

  const tempVec = new Vector3();
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let rafId = 0;
  let phase = 0;
  let lastTime = Date.now();

  const renderFrame = (dt) => {
    currentSpeed += (activeMode.speed - currentSpeed) * 0.06;
    currentAmp += (activeMode.amp - currentAmp) * 0.06;
    currentFreq += (activeMode.freq - currentFreq) * 0.06;
    currentRingSpeed += (activeMode.ringSpeed - currentRingSpeed) * 0.06;

    orbMat.color.lerp(activeMode.color, 0.06);
    orbMat.emissive.lerp(activeMode.emissive, 0.06);
    ringMat1.color.lerp(activeMode.ringColor, 0.06);

    phase += dt * currentSpeed;

    // Organic vertex breathing displacement
    for (let i = 0; i < posAttr.count; i++) {
      const bx = basePos[i * 3];
      const by = basePos[i * 3 + 1];
      const bz = basePos[i * 3 + 2];
      tempVec.set(bx, by, bz).normalize();

      const wave =
        Math.sin(tempVec.x * currentFreq + phase) *
          Math.cos(tempVec.y * currentFreq + phase * 0.85) +
        Math.sin(tempVec.z * (currentFreq * 1.3) - phase * 0.7) * 0.55;
      const breathe = Math.sin(phase * 1.1) * 0.035;
      const offset = 1 + breathe + wave * currentAmp;

      posAttr.setXYZ(i, bx * offset, by * offset, bz * offset);
    }
    posAttr.needsUpdate = true;
    orbGeo.computeVertexNormals();

    root.rotation.y += (pointerX * 0.55 - root.rotation.y) * 0.05;
    root.rotation.x += (pointerY * 0.4 - root.rotation.x) * 0.05;
    orbMesh.rotation.y = phase * 0.25;

    halo1.rotation.z = phase * currentRingSpeed;
    halo1.rotation.x = 1.15 + Math.sin(phase * 0.45) * 0.15;
    halo2.rotation.z = -phase * currentRingSpeed * 0.8;
    halo2.rotation.y = 0.55 + Math.cos(phase * 0.4) * 0.16;

    cueOrbs.forEach((cue, idx) => {
      const angle = cue.offset + phase * (0.55 + idx * 0.14);
      cue.mesh.position.set(
        Math.cos(angle) * cue.radius,
        Math.sin(angle * 1.2) * 0.55,
        Math.sin(angle) * cue.radius
      );
    });

    renderer.render(scene, camera);
  };

  renderFrame(0);
  container.classList.add('has-webgl');

  if (!reducedMotion) {
    const tick = () => {
      const now = Date.now();
      const dt = Math.min((now - lastTime) / 1000, 0.05);
      lastTime = now;
      renderFrame(dt);
      rafId = window.requestAnimationFrame(tick);
    };
    rafId = window.requestAnimationFrame(tick);
  }

  return {
    setMode: (modeName) => {
      if (ORB_MODES[modeName]) {
        activeMode = ORB_MODES[modeName];
        if (reducedMotion) {
          orbMat.color.copy(activeMode.color);
          orbMat.emissive.copy(activeMode.emissive);
          ringMat1.color.copy(activeMode.ringColor);
          renderer.render(scene, camera);
        }
      }
    },
    destroy: () => {
      window.cancelAnimationFrame(rafId);
      ro?.disconnect();
      container.removeEventListener('pointermove', onPointerMove);
      container.removeEventListener('pointerleave', onPointerLeave);
      renderer.dispose();
    },
  };
};

