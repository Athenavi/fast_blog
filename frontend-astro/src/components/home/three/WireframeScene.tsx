'use client';

/**
 * WireframeScene - 首页 Hero 的 three.js 线框背景
 *
 * 设计意图（taste-skill 克制科技感）：
 * - 旋转线框二十面体 + 双层线框环，低透明度、低饱和蓝
 * - 鼠标视差：物体组平滑跟随指针微偏移
 * - 不抢内容：线框透明度 ≤ 0.4，与衬线标题共存
 * - 通过 React.lazy 懒加载，仅在首页加载 three 相关 chunk
 */
import React, {useRef} from 'react';
import {Canvas, useFrame} from '@react-three/fiber';
import * as THREE from 'three';

interface CoreProps {
  reducedMotion: boolean;
}

function WireframeCore({reducedMotion}: CoreProps) {
  const group = useRef<THREE.Group>(null);
  const ringA = useRef<THREE.Mesh>(null);
  const ringB = useRef<THREE.Mesh>(null);
  const pointerTarget = useRef({x: 0, y: 0});

  useFrame((state, delta) => {
    const g = group.current;
    if (!g) return;
    const t = state.clock.elapsedTime;

    if (reducedMotion) {
      // 静止：仅保留鼠标视差（轻）
      pointerTarget.current.x += (state.pointer.x * 0.15 - pointerTarget.current.x) * 0.03;
      pointerTarget.current.y += (state.pointer.y * 0.1 - pointerTarget.current.y) * 0.03;
      g.rotation.y = pointerTarget.current.x;
      g.rotation.x = pointerTarget.current.y;
      return;
    }

    // 自转 + 呼吸
    g.rotation.y += delta * 0.12;
    g.rotation.x = Math.sin(t * 0.12) * 0.18;

    // 鼠标视差（与自转叠加）
    pointerTarget.current.x += (state.pointer.x * 0.35 - pointerTarget.current.x) * 0.02;
    pointerTarget.current.y += (state.pointer.y * 0.25 - pointerTarget.current.y) * 0.02;
    g.rotation.y += pointerTarget.current.x * delta * 0.6;
    g.rotation.x += pointerTarget.current.y * delta * 0.4;

    // 环反向旋转
    if (ringA.current) ringA.current.rotation.z -= delta * 0.08;
    if (ringB.current) ringB.current.rotation.z += delta * 0.05;
  });

  return (
    <group ref={group}>
      {/* 主体：线框二十面体 */}
      <mesh>
        <icosahedronGeometry args={[1.5, 1]}/>
        <meshBasicMaterial wireframe color="#3b82f6" transparent opacity={0.32}/>
      </mesh>
      {/* 内层小二十面体（反向感） */}
      <mesh scale={0.55} rotation={[0.4, 0.6, 0]}>
        <icosahedronGeometry args={[1.5, 0]}/>
        <meshBasicMaterial wireframe color="#60a5fa" transparent opacity={0.22}/>
      </mesh>
      {/* 双层线框环 */}
      <mesh ref={ringA} rotation={[Math.PI / 2.3, 0.4, 0]}>
        <torusGeometry args={[2.7, 0.012, 12, 140]}/>
        <meshBasicMaterial wireframe color="#60a5fa" transparent opacity={0.18}/>
      </mesh>
      <mesh ref={ringB} rotation={[-Math.PI / 2.7, -0.5, 0.3]} scale={1.15}>
        <torusGeometry args={[2.4, 0.008, 12, 140]}/>
        <meshBasicMaterial wireframe color="#38bdf8" transparent opacity={0.12}/>
      </mesh>
      {/* 星点：少量散布粒子强化“深夜编辑部”氛围 */}
      <points>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[generateStarPositions(180), 3]}
          />
        </bufferGeometry>
        <pointsMaterial size={0.02} color="#94a3b8" transparent opacity={0.5} sizeAttenuation/>
      </points>
    </group>
  );
}

function generateStarPositions(count: number): Float32Array {
  const arr = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    // 球壳分布，半径 4-9，避开中心
    const r = 4 + Math.random() * 5;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    arr[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    arr[i * 3 + 2] = r * Math.cos(phi);
  }
  return arr;
}

export default function WireframeScene({reducedMotion = false}: { reducedMotion?: boolean }) {
  return (
    <Canvas
      camera={{position: [0, 0, 7], fov: 45}}
      dpr={[1, 1.5]}
      gl={{antialias: true, alpha: true}}
      style={{position: 'absolute', inset: 0}}
    >
      <WireframeCore reducedMotion={reducedMotion}/>
    </Canvas>
  );
}
