'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';

const INK = '#1A1815';
const ACCENT = '#B3400A';
const FAINT = '#C9C4B8';

export function HeroPoster() {
  return (
    <div className="hero-scene-poster" aria-hidden="true">
      <div className="hero-poster-core" />
      <div className="hero-poster-ring hero-poster-ring-a" />
      <div className="hero-poster-ring hero-poster-ring-b" />
      <span className="mono hero-poster-tag">face → web → chain</span>
    </div>
  );
}

function Rig({ children }) {
  const ref = useRef();
  const { pointer } = useThree();
  useFrame((state, dt) => {
    if (!ref.current) return;
    const t = Math.min(dt, 0.05);
    ref.current.rotation.y += t * 0.12;
    ref.current.rotation.x += (((pointer.y || 0) * -0.25) - ref.current.rotation.x) * t * 2;
    ref.current.rotation.z += (((pointer.x || 0) * 0.12) - ref.current.rotation.z) * t * 2;
  });
  return <group ref={ref}>{children}</group>;
}

function Rings() {
  const a = useRef();
  const b = useRef();
  useFrame((state, dt) => {
    const t = Math.min(dt, 0.05);
    if (a.current) a.current.rotation.z += t * 0.25;
    if (b.current) b.current.rotation.z -= t * 0.18;
  });
  return (
    <>
      <mesh ref={a} rotation={[Math.PI / 2.4, 0.2, 0]}>
        <torusGeometry args={[2.05, 0.012, 12, 128]} />
        <meshBasicMaterial color={ACCENT} transparent opacity={0.85} />
      </mesh>
      <mesh ref={b} rotation={[Math.PI / 1.8, -0.3, 0.4]}>
        <torusGeometry args={[2.5, 0.008, 12, 128]} />
        <meshBasicMaterial color={FAINT} transparent opacity={0.9} />
      </mesh>
    </>
  );
}

function Nodes() {
  const g = useRef();
  useFrame((state) => {
    if (!g.current) return;
    const t = state.clock.elapsedTime * 0.25;
    g.current.children.forEach((m, i) => {
      const a = t + (i * Math.PI * 2) / 3;
      m.position.set(Math.cos(a) * 2.05, Math.sin(a) * 2.05 * 0.42, Math.sin(a) * 0.6);
    });
  });
  return (
    <group ref={g} rotation={[Math.PI / 2.4, 0.2, 0]}>
      {[0, 1, 2].map((i) => (
        <mesh key={i}>
          <sphereGeometry args={[i === 0 ? 0.09 : 0.06, 24, 24]} />
          <meshBasicMaterial color={i === 0 ? ACCENT : INK} />
        </mesh>
      ))}
    </group>
  );
}

function Lattice() {
  const ref = useRef();
  useFrame((state, dt) => {
    if (ref.current) ref.current.rotation.y += Math.min(dt, 0.05) * -0.08;
  });
  return (
    <group>
      <mesh ref={ref}>
        <icosahedronGeometry args={[1.15, 1]} />
        <meshBasicMaterial color={INK} wireframe transparent opacity={0.9} />
      </mesh>
      <mesh scale={0.55}>
        <icosahedronGeometry args={[1.15, 0]} />
        <meshBasicMaterial color={ACCENT} wireframe transparent opacity={0.55} />
      </mesh>
    </group>
  );
}

export default function HeroScene() {
  const [wrap, setWrap] = useState(null);
  const [visible, setVisible] = useState(true);
  const [reduced, setReduced] = useState(false);
  const [webgl, setWebgl] = useState(true);

  useEffect(() => {
    setReduced(window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    try {
      const c = document.createElement('canvas');
      setWebgl(!!(c.getContext('webgl') || c.getContext('experimental-webgl')));
    } catch {
      setWebgl(false);
    }
  }, []);

  useEffect(() => {
    if (!wrap) return;
    const io = new IntersectionObserver(([e]) => setVisible(e.isIntersecting), { threshold: 0.05 });
    io.observe(wrap);
    return () => io.disconnect();
  }, [wrap]);

  if (reduced || !webgl) return <HeroPoster />;

  return (
    <div ref={setWrap} className="hero-scene" role="img" aria-label="Abstract 3D lattice of a verification record orbited by three stages">
      <Canvas
        dpr={[1, 1.75]}
        camera={{ position: [0, 0.4, 6.2], fov: 42 }}
        gl={{ antialias: true, alpha: true }}
        frameloop={visible ? 'always' : 'never'}
      >
        <Suspense fallback={null}>
          <Rig>
            <Lattice />
            <Rings />
            <Nodes />
          </Rig>
        </Suspense>
      </Canvas>
    </div>
  );
}
