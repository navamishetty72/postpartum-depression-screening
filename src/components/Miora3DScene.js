import {
  AmbientLight,
  Color,
  DirectionalLight,
  Group,
  Mesh,
  MeshBasicMaterial,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
  PerspectiveCamera,
  PointLight,
  Scene,
  SphereGeometry,
  TorusGeometry,
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
    color: new Color(0xe66d93),
    emissive: new Color(0x6d1936),
    shellColor: new Color(0xffe1e8),
    ringColor: new Color(0xebb0bf),
    breatheSpeed: 1.35,
    breatheAmp: 0.045,
    ringSpeed: 0.35,
  },
  understand: {
    color: new Color(0xc73566),
    emissive: new Color(0x5c102b),
    shellColor: new Color(0xffccd8),
    ringColor: new Color(0xe07b9b),
    breatheSpeed: 2.1,
    breatheAmp: 0.065,
    ringSpeed: 0.72,
  },
  support: {
    color: new Color(0xe27e7a),
    emissive: new Color(0x742530),
    shellColor: new Color(0xffe5dc),
    ringColor: new Color(0xf0beaf),
    breatheSpeed: 1.55,
    breatheAmp: 0.055,
    ringSpeed: 0.48,
  },
};

/**
 * Mounts an interactive, silk-smooth 3D Empathy Core centerpiece with layered
 * glass spheres and ring-locked orbiting pearls.
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
  const camera = new PerspectiveCamera(34, 1, 0.1, 50);
  camera.position.set(0, 0, 6.4);

  const root = new Group();
  scene.add(root);

  scene.add(new AmbientLight(0xfff5f3, 1.45));
  const keyLight = new DirectionalLight(0xfff0ec, 2.1);
  keyLight.position.set(-3.5, 4.5, 5.5);
  scene.add(keyLight);

  const roseRim = new PointLight(0xd93c75, 2.5, 18);
  roseRim.position.set(3.5, -2.5, 2.5);
  scene.add(roseRim);

  const peachFill = new PointLight(0xffd4c2, 2.0, 18);
  peachFill.position.set(-3, -2, 3);
  scene.add(peachFill);

  // Smooth indexed high-resolution core & layered glass shell (zero low-poly facets)
  const coreGroup = new Group();
  root.add(coreGroup);

  const orbMat = new MeshPhysicalMaterial({
    color: ORB_MODES.share.color.clone(),
    emissive: ORB_MODES.share.emissive.clone(),
    emissiveIntensity: 0.25,
    roughness: 0.18,
    metalness: 0.04,
    clearcoat: 0.95,
    clearcoatRoughness: 0.1,
  });
  const orbMesh = new Mesh(new SphereGeometry(0.84, 64, 64), orbMat);
  coreGroup.add(orbMesh);

  // Soft frosted translucent outer glass shell
  const shellMat = new MeshPhysicalMaterial({
    color: ORB_MODES.share.shellColor.clone(),
    roughness: 0.12,
    metalness: 0.02,
    clearcoat: 1.0,
    clearcoatRoughness: 0.08,
    transparent: true,
    opacity: 0.34,
  });
  const shellMesh = new Mesh(new SphereGeometry(0.98, 64, 64), shellMat);
  coreGroup.add(shellMesh);

  // Soft glowing inner heart core
  const innerCore = new Mesh(
    new SphereGeometry(0.52, 48, 48),
    new MeshBasicMaterial({
      color: 0xffe8ec,
      transparent: true,
      opacity: 0.45,
    })
  );
  coreGroup.add(innerCore);

  // Helper to build a smooth 3D ring with a pearl locked directly onto its local track
  const ringMat1 = new MeshStandardMaterial({
    color: ORB_MODES.share.ringColor.clone(),
    roughness: 0.25,
    metalness: 0.18,
    transparent: true,
    opacity: 0.7,
  });
  const ringMat2 = new MeshStandardMaterial({
    color: 0xf7cbbd,
    roughness: 0.28,
    metalness: 0.15,
    transparent: true,
    opacity: 0.55,
  });

  const R1 = 1.38;
  const ring1Pivot = new Group();
  ring1Pivot.rotation.set(1.12, 0.36, 0.15);
  const halo1 = new Mesh(new TorusGeometry(R1, 0.02, 24, 128), ringMat1);
  ring1Pivot.add(halo1);
  const pearl1 = new Mesh(
    new SphereGeometry(0.085, 28, 28),
    new MeshPhysicalMaterial({ color: 0xf7b8c7, roughness: 0.14, clearcoat: 1.0 })
  );
  ring1Pivot.add(pearl1);
  root.add(ring1Pivot);

  const R2 = 1.58;
  const ring2Pivot = new Group();
  ring2Pivot.rotation.set(-0.98, 0.52, -0.25);
  const halo2 = new Mesh(new TorusGeometry(R2, 0.015, 24, 128), ringMat2);
  ring2Pivot.add(halo2);
  const pearl2 = new Mesh(
    new SphereGeometry(0.075, 28, 28),
    new MeshPhysicalMaterial({ color: 0xc73566, roughness: 0.16, clearcoat: 1.0 })
  );
  ring2Pivot.add(pearl2);
  const pearl3 = new Mesh(
    new SphereGeometry(0.068, 28, 28),
    new MeshPhysicalMaterial({ color: 0xfad2c0, roughness: 0.14, clearcoat: 1.0 })
  );
  ring2Pivot.add(pearl3);
  root.add(ring2Pivot);

  let activeMode = ORB_MODES.share;
  let currentBreatheSpeed = activeMode.breatheSpeed;
  let currentBreatheAmp = activeMode.breatheAmp;
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
    const width = canvas.clientWidth || container.clientWidth || 320;
    const height = canvas.clientHeight || 250;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };
  resize();

  const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(resize) : null;
  ro?.observe(canvas);

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let rafId = 0;
  let phase = 0;
  let ringPhase = 0;
  let lastTime = Date.now();

  const renderFrame = (dt) => {
    currentBreatheSpeed += (activeMode.breatheSpeed - currentBreatheSpeed) * 0.06;
    currentBreatheAmp += (activeMode.breatheAmp - currentBreatheAmp) * 0.06;
    currentRingSpeed += (activeMode.ringSpeed - currentRingSpeed) * 0.06;

    orbMat.color.lerp(activeMode.color, 0.06);
    orbMat.emissive.lerp(activeMode.emissive, 0.06);
    shellMat.color.lerp(activeMode.shellColor, 0.06);
    ringMat1.color.lerp(activeMode.ringColor, 0.06);

    phase += dt * currentBreatheSpeed;
    ringPhase += dt * currentRingSpeed;

    // Gentle symmetric breathing & floating levitation
    const coreScale = 1 + Math.sin(phase) * currentBreatheAmp;
    const shellScale = 1 + Math.sin(phase - 0.45) * (currentBreatheAmp * 1.15);
    orbMesh.scale.setScalar(coreScale);
    shellMesh.scale.setScalar(shellScale);
    root.position.y = Math.sin(phase * 0.7) * 0.055;

    // Smooth interactive cursor tilt
    root.rotation.y += (pointerX * 0.5 - root.rotation.y) * 0.05;
    root.rotation.x += (pointerY * 0.35 - root.rotation.x) * 0.05;

    // Precess rings smoothly and keep every pearl locked on its ring perimeter
    ring1Pivot.rotation.y = 0.36 + Math.sin(ringPhase * 0.5) * 0.18;
    ring1Pivot.rotation.x = 1.12 + Math.cos(ringPhase * 0.4) * 0.14;
    const a1 = ringPhase * 1.4;
    pearl1.position.set(Math.cos(a1) * R1, Math.sin(a1) * R1, 0);

    ring2Pivot.rotation.y = 0.52 - Math.cos(ringPhase * 0.45) * 0.18;
    ring2Pivot.rotation.x = -0.98 + Math.sin(ringPhase * 0.38) * 0.14;
    const a2 = -ringPhase * 1.15 + 1.2;
    pearl2.position.set(Math.cos(a2) * R2, Math.sin(a2) * R2, 0);
    const a3 = a2 + Math.PI;
    pearl3.position.set(Math.cos(a3) * R2, Math.sin(a3) * R2, 0);

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
          shellMat.color.copy(activeMode.shellColor);
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
