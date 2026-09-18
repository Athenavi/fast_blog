<script lang="ts" setup>
import {onBeforeUnmount, onMounted, ref} from 'vue'

/**
 * 首页 Hero 的 three.js 线框背景
 *
 * 对应原 astro 的 `home/three/WireframeScene.tsx`（React Three Fiber 版）。
 * 这里不改技术栈、也不新增依赖：直接用已在依赖里的 `three` 原生 API，
 * 并通过动态 `import('three')` 让 three（约 600 KB）只在组件真正挂载时才加载。
 *
 * 视觉与原实现一一对应：线框二十面体 + 内层反向小二十面体 + 双层线框环 + 星点；
 * 动画为自转 + 呼吸 + 鼠标视差叠加；`reducedMotion` 时只保留鼠标视差（轻量、不抢内容）。
 */
const props = withDefaults(defineProps<{ reducedMotion?: boolean }>(), {reducedMotion: false})

const canvasRef = ref<HTMLCanvasElement | null>(null)

let cleanup: (() => void) | null = null

/** 球壳分布、半径 4~9，避开中心 */
function generateStarPositions(count: number): Float32Array {
  const positions = new Float32Array(count * 3)
  for (let i = 0; i < count; i += 1) {
    const radius = 4 + Math.random() * 5
    const theta = Math.random() * Math.PI * 2
    const phi = Math.acos(2 * Math.random() - 1)
    positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
    positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
    positions[i * 3 + 2] = radius * Math.cos(phi)
  }
  return positions
}

onMounted(async () => {
  const canvas = canvasRef.value
  if (!canvas) return

  const THREE = await import('three')

  const renderer = new THREE.WebGLRenderer({canvas, antialias: true, alpha: true})
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5))

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100)
  camera.position.set(0, 0, 7)

  const group = new THREE.Group()
  scene.add(group)

  // 主体：线框二十面体
  group.add(
    new THREE.Mesh(
      new THREE.IcosahedronGeometry(1.5, 1),
      new THREE.MeshBasicMaterial({
        wireframe: true,
        color: 0x3b82f6,
        transparent: true,
        opacity: 0.32,
      }),
    ),
  )

  // 内层小二十面体（尺度更小、朝向偏移，制造反面感）
  const inner = new THREE.Mesh(
    new THREE.IcosahedronGeometry(1.5, 0),
    new THREE.MeshBasicMaterial({wireframe: true, color: 0x60a5fa, transparent: true, opacity: 0.22}),
  )
  inner.scale.setScalar(0.55)
  inner.rotation.set(0.4, 0.6, 0)
  group.add(inner)

  // 双层线框环
  const ringA = new THREE.Mesh(
    new THREE.TorusGeometry(2.7, 0.012, 12, 140),
    new THREE.MeshBasicMaterial({wireframe: true, color: 0x60a5fa, transparent: true, opacity: 0.18}),
  )
  ringA.rotation.set(Math.PI / 2.3, 0.4, 0)
  group.add(ringA)

  const ringB = new THREE.Mesh(
    new THREE.TorusGeometry(2.4, 0.008, 12, 140),
    new THREE.MeshBasicMaterial({wireframe: true, color: 0x38bdf8, transparent: true, opacity: 0.12}),
  )
  ringB.rotation.set(-Math.PI / 2.7, -0.5, 0.3)
  ringB.scale.setScalar(1.15)
  group.add(ringB)

  // 星点：少量散布粒子，强化「深夜边缘」氛围
  const starGeometry = new THREE.BufferGeometry()
  starGeometry.setAttribute('position', new THREE.BufferAttribute(generateStarPositions(180), 3))
  group.add(
    new THREE.Points(
      starGeometry,
      new THREE.PointsMaterial({
        size: 0.02,
        color: 0x94a3b8,
        transparent: true,
        opacity: 0.5,
        sizeAttenuation: true,
      }),
    ),
  )

  const host: HTMLCanvasElement = canvas

  function resize(): void {
    const parent = host.parentElement
    const width = parent?.clientWidth || window.innerWidth
    const height = parent?.clientHeight || window.innerHeight
    renderer.setSize(width, height, false)
    camera.aspect = width / Math.max(height, 1)
    camera.updateProjectionMatrix()
  }

  resize()

  // 鼠标视差
  const pointer = {x: 0, y: 0}
  const target = {x: 0, y: 0}

  function onPointerMove(event: PointerEvent): void {
    pointer.x = (event.clientX / window.innerWidth) * 2 - 1
    pointer.y = -((event.clientY / window.innerHeight) * 2 - 1)
  }

  const clock = new THREE.Clock()
  let frameId = 0

  function animate(): void {
    frameId = window.requestAnimationFrame(animate)
    const delta = Math.min(clock.getDelta(), 0.05)
    const time = clock.elapsedTime

    if (props.reducedMotion) {
      // 静止：仅保留鼠标视差（更轻，不与内容争注意力）
      target.x += (pointer.x * 0.15 - target.x) * 0.03
      target.y += (pointer.y * 0.1 - target.y) * 0.03
      group.rotation.y = target.x
      group.rotation.x = target.y
    } else {
      // 自转 + 呼吸
      group.rotation.y += delta * 0.12
      group.rotation.x = Math.sin(time * 0.12) * 0.18

      // 鼠标视差（与自转叠加）
      target.x += (pointer.x * 0.35 - target.x) * 0.02
      target.y += (pointer.y * 0.25 - target.y) * 0.02
      group.rotation.y += target.x * delta * 0.6
      group.rotation.x += target.y * delta * 0.4

      // 环反向旋转
      ringA.rotation.z -= delta * 0.08
      ringB.rotation.z += delta * 0.05
    }

    renderer.render(scene, camera)
  }

  window.addEventListener('resize', resize)
  window.addEventListener('pointermove', onPointerMove)
  animate()

  cleanup = () => {
    window.cancelAnimationFrame(frameId)
    window.removeEventListener('resize', resize)
    window.removeEventListener('pointermove', onPointerMove)

    scene.traverse((object) => {
      const mesh = object as { geometry?: { dispose?: () => void }; material?: unknown }
      mesh.geometry?.dispose?.()
      const material = mesh.material
      if (Array.isArray(material)) material.forEach((item) => (item as { dispose?: () => void }).dispose?.())
      else (material as { dispose?: () => void } | undefined)?.dispose?.()
    })

    renderer.dispose()
  }
})

onBeforeUnmount(() => {
  cleanup?.()
  cleanup = null
})
</script>

<template>
  <canvas ref="canvasRef" aria-hidden="true" class="wireframe-scene"/>
</template>

<style scoped>
.wireframe-scene {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
</style>
