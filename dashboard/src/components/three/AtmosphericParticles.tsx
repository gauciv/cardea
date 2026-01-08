import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

// ============================================
// ATMOSPHERIC PARTICLES
// Floating dust and energy particles for enhanced space atmosphere
// ============================================

const particleVertexShader = `
  uniform float uTime;
  uniform float uOpacity;
  attribute float aScale;
  attribute float aSpeed;
  attribute vec3 aVelocity;
  
  varying float vAlpha;
  varying vec3 vColor;
  
  void main() {
    vec3 pos = position;
    
    // Floating motion
    float timeOffset = uTime * aSpeed;
    pos += aVelocity * timeOffset;
    
    // Wrap particles in space
    pos.x = mod(pos.x + 50.0, 100.0) - 50.0;
    pos.y = mod(pos.y + 30.0, 60.0) - 30.0;
    pos.z = mod(pos.z + 40.0, 80.0) - 40.0;
    
    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
    gl_Position = projectionMatrix * mvPosition;
    
    // Size based on distance and scale
    float distance = length(mvPosition.xyz);
    gl_PointSize = (aScale * 80.0) / distance;
    gl_PointSize = max(gl_PointSize, 0.3);
    
    // Soft alpha based on distance
    float fade = 1.0 - smoothstep(30.0, 60.0, distance);
    vAlpha = fade * uOpacity * aScale;
    
    // Color variation based on scale
    vec3 lightBlue = vec3(0.4, 0.6, 0.9);
    vec3 deepBlue = vec3(0.2, 0.3, 0.6);
    vColor = mix(deepBlue, lightBlue, aScale);
  }
`;

const particleFragmentShader = `
  varying float vAlpha;
  varying vec3 vColor;
  
  void main() {
    vec2 center = gl_PointCoord - 0.5;
    float dist = length(center);
    
    // Soft circular particle
    float circle = 1.0 - smoothstep(0.0, 0.5, dist);
    circle = pow(circle, 2.0);
    
    if (circle < 0.1) discard;
    
    float alpha = circle * vAlpha;
    gl_FragColor = vec4(vColor, alpha);
  }
`;

interface AtmosphericParticlesProps {
  density?: number;
  opacity?: number;
}

export default function AtmosphericParticles({ 
  density = 1.0, 
  opacity = 0.3 
}: AtmosphericParticlesProps) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const count = Math.floor(500 * density);
  
  const { positions, scales, speeds, velocities } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const scales = new Float32Array(count);
    const speeds = new Float32Array(count);
    const velocities = new Float32Array(count * 3);
    
    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      
      // Distribute in 3D space
      positions[i3] = (Math.random() - 0.5) * 100;
      positions[i3 + 1] = (Math.random() - 0.5) * 60;
      positions[i3 + 2] = (Math.random() - 0.5) * 80;
      
      scales[i] = 0.3 + Math.random() * 0.7;
      speeds[i] = 0.1 + Math.random() * 0.2;
      
      // Slow drifting velocities
      velocities[i3] = (Math.random() - 0.5) * 2;
      velocities[i3 + 1] = (Math.random() - 0.5) * 1.5;
      velocities[i3 + 2] = (Math.random() - 0.5) * 2;
    }
    
    return { positions, scales, speeds, velocities };
  }, [count]);
  
  useFrame((_, delta) => {
    if (!materialRef.current) return;
    
    materialRef.current.uniforms.uTime.value += delta;
    materialRef.current.uniforms.uOpacity.value = THREE.MathUtils.lerp(
      materialRef.current.uniforms.uOpacity.value,
      opacity,
      delta * 2.0
    );
  });
  
  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-aScale" args={[scales, 1]} />
        <bufferAttribute attach="attributes-aSpeed" args={[speeds, 1]} />
        <bufferAttribute attach="attributes-aVelocity" args={[velocities, 3]} />
      </bufferGeometry>
      <shaderMaterial
        ref={materialRef}
        vertexShader={particleVertexShader}
        fragmentShader={particleFragmentShader}
        uniforms={{
          uTime: { value: 0 },
          uOpacity: { value: opacity },
        }}
        transparent
        blending={THREE.NormalBlending} // Changed from Additive
        depthWrite={false}
      />
    </points>
  );
}