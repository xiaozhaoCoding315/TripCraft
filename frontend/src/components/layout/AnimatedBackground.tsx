import React, { useRef, useEffect, useCallback } from 'react';

interface Props {
  phase?: 'idle' | 'planning' | 'result';
}

// Simple Perlin-like noise implementation
function noise2D(x: number, y: number): number {
  const n = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453;
  return n - Math.floor(n);
}

function smoothNoise(x: number, y: number): number {
  const ix = Math.floor(x);
  const iy = Math.floor(y);
  const fx = x - ix;
  const fy = y - iy;

  // Smooth interpolation
  const sx = fx * fx * (3 - 2 * fx);
  const sy = fy * fy * (3 - 2 * fy);

  const n00 = noise2D(ix, iy);
  const n10 = noise2D(ix + 1, iy);
  const n01 = noise2D(ix, iy + 1);
  const n11 = noise2D(ix + 1, iy + 1);

  const nx0 = n00 + (n10 - n00) * sx;
  const nx1 = n01 + (n11 - n01) * sx;

  return nx0 + (nx1 - nx0) * sy;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
  color: string;
  life: number;
  maxLife: number;
}

const PARTICLE_COUNT = 200;
const CONNECTION_DIST = 80;
const MOUSE_REPEL_DIST = 120;
const MOUSE_REPEL_FORCE = 0.5;

const AnimatedBackground: React.FC<Props> = ({ phase = 'idle' }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const mouseRef = useRef({ x: -1000, y: -1000 });
  const frameRef = useRef<number>(0);
  const timeRef = useRef(0);

  const initParticles = useCallback((width: number, height: number) => {
    const particles: Particle[] = [];
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: 0,
        vy: 0,
        size: Math.random() * 2 + 0.5,
        alpha: Math.random() * 0.6 + 0.2,
        color: Math.random() > 0.3 ? '34, 211, 240' : '167, 139, 250', // cyan or purple
        life: Math.random() * 300,
        maxLife: 300 + Math.random() * 200,
      });
    }
    return particles;
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    resize();
    window.addEventListener('resize', resize);

    // Initialize particles
    if (particlesRef.current.length === 0) {
      particlesRef.current = initParticles(canvas.width, canvas.height);
    }

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };

    window.addEventListener('mousemove', handleMouseMove);

    // Speed multiplier based on phase
    const speedMultiplier = phase === 'planning' ? 3 : phase === 'result' ? 1.5 : 1;
    const connectionOpacity = phase === 'planning' ? 0.3 : 0.15;

    const animate = () => {
      const { width, height } = canvas;
      const mouse = mouseRef.current;
      const particles = particlesRef.current;
      const t = timeRef.current;

      ctx.clearRect(0, 0, width, height);

      // Update and draw particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // Flow field force
        const angle = smoothNoise(p.x * 0.005, p.y * 0.005 + t * 0.001) * Math.PI * 4;
        const flowForce = 0.03 * speedMultiplier;

        p.vx += Math.cos(angle) * flowForce;
        p.vy += Math.sin(angle) * flowForce;

        // Mouse repulsion
        const dx = p.x - mouse.x;
        const dy = p.y - mouse.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < MOUSE_REPEL_DIST && dist > 0) {
          const force = (MOUSE_REPEL_DIST - dist) / MOUSE_REPEL_DIST * MOUSE_REPEL_FORCE;
          p.vx += (dx / dist) * force;
          p.vy += (dy / dist) * force;
        }

        // Gentle attraction toward center during planning
        if (phase === 'planning') {
          const cx = width / 2;
          const cy = height / 2;
          const cdx = cx - p.x;
          const cdy = cy - p.y;
          const cdist = Math.sqrt(cdx * cdx + cdy * cdy);
          if (cdist > 100) {
            p.vx += (cdx / cdist) * 0.01;
            p.vy += (cdy / cdist) * 0.01;
          }
        }

        // Damping
        p.vx *= 0.98;
        p.vy *= 0.98;

        // Speed cap
        const speed = Math.sqrt(p.vx * p.vx + p.vy * p.vy);
        const maxSpeed = 2 * speedMultiplier;
        if (speed > maxSpeed) {
          p.vx = (p.vx / speed) * maxSpeed;
          p.vy = (p.vy / speed) * maxSpeed;
        }

        // Update position
        p.x += p.vx;
        p.y += p.vy;

        // Wrap around edges
        if (p.x < -10) p.x = width + 10;
        if (p.x > width + 10) p.x = -10;
        if (p.y < -10) p.y = height + 10;
        if (p.y > height + 10) p.y = -10;

        // Life cycle for twinkling
        p.life--;
        if (p.life <= 0) {
          p.life = p.maxLife;
          p.x = Math.random() * width;
          p.y = Math.random() * height;
        }

        const lifeFade = Math.sin((p.life / p.maxLife) * Math.PI);
        const alpha = p.alpha * (0.6 + 0.4 * lifeFade);

        // Draw particle
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${p.color}, ${alpha})`;
        ctx.fill();

        // Draw glow for larger particles
        if (p.size > 1.2) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size * 3, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${p.color}, ${alpha * 0.15})`;
          ctx.fill();
        }
      }

      // Draw connections between nearby particles
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < CONNECTION_DIST) {
            const alpha = (1 - dist / CONNECTION_DIST) * connectionOpacity;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(34, 211, 240, ${alpha})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }

      timeRef.current += 1;
      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [phase, initParticles]);

  return (
    <div className="layer-background" aria-hidden="true">
      {/* Canvas particle flow field */}
      <canvas
        ref={canvasRef}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />

      {/* Ambient light orbs */}
      <div
        style={{
          position: 'fixed',
          width: 500,
          height: 500,
          borderRadius: '50%',
          background: `radial-gradient(circle, rgba(34,211,240,0.06) 0%, transparent 70%)`,
          top: '10%',
          left: '60%',
          filter: 'blur(60px)',
          pointerEvents: 'none',
          zIndex: 0,
          transition: 'all 8s ease-in-out',
          animation: 'floatSlow 10s ease-in-out infinite',
        }}
      />
      <div
        style={{
          position: 'fixed',
          width: 400,
          height: 400,
          borderRadius: '50%',
          background: `radial-gradient(circle, rgba(167,139,250,0.05) 0%, transparent 70%)`,
          top: '60%',
          left: '20%',
          filter: 'blur(50px)',
          pointerEvents: 'none',
          zIndex: 0,
          transition: 'all 8s ease-in-out',
          animation: 'floatSlow 12s ease-in-out infinite reverse',
        }}
      />
      <div
        style={{
          position: 'fixed',
          width: 300,
          height: 300,
          borderRadius: '50%',
          background: `radial-gradient(circle, rgba(45,212,191,0.04) 0%, transparent 70%)`,
          top: '30%',
          left: '40%',
          filter: 'blur(40px)',
          pointerEvents: 'none',
          zIndex: 0,
          transition: 'all 8s ease-in-out',
          animation: 'floatSlow 14s ease-in-out infinite',
        }}
      />

      {/* Perspective grid floor */}
      <div className="grid-floor" />

      {/* Gradient mesh fallback */}
      <div className="gradient-mesh" style={{ opacity: 0.4 }} />
    </div>
  );
};

export default AnimatedBackground;
