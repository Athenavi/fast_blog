<script lang="ts" setup>
import {onBeforeUnmount, onMounted, ref} from 'vue'

/**
 * 首页 Hero 的线框背景（Canvas 2D 版）
 *
 * **为什么不再是 three.js**：原实现用 `import('three')` 画一个装饰性线框，
 * 代价是**每次访问首页都下载 184 KB（gzip）**——构建产物里 `three` 是单独一个
 * 736 KB 的 chunk，而且它还会常驻一个 `requestAnimationFrame` + WebGL 渲染循环，
 * 与 LCP/INP 争主线程和 GPU。实测首页总下载量因此从 ~220 KB 抬到 ~460 KB（gzip），
 * 比同类内容型站点高出一个数量级。
 *
 * 现在改为**手写等价几何 + Canvas 2D 透视投影**：视觉一一对应，体积不到 1 KB，
 * 无 WebGL 上下文、无第三方依赖（`three` / `@types/three` 已从 package.json 移除）。
 *
 * 还原的三要素（数值与原 three 实现逐项对齐，便于视觉回归比对）：
 *  - 相机：PerspectiveCamera(45°, aspect, 0.1, 100)，位于 (0, 0, 7)，看向原点；
 *  - 几何：detail=1 线框二十面体（#3b82f6 / 0.32）+ 内层 detail=0 小二十面体
 *    （#60a5fa / 0.22，scale 0.55，欧拉角 0.4/0.6/0）+ 双层线框环
 *    （R=2.7 #60a5fa 0.18 / R=2.4 #38bdf8 0.12 scale 1.15）+ 180 个半径 4~9 的星点（#94a3b8 / 0.5）；
 *  - 动画：自转 0.12 rad/s + 呼吸 sin(t·0.12)·0.18 + 鼠标视差叠加，环反向自转；
 *    `reducedMotion` 时只保留鼠标视差（与原实现一致）。
 *
 * 性能取舍：
 *  - 每帧只做 ~600 次线段/点绘制（20×4 面二十面体的 120 条边 + 2 条 140 段环 + 180 个点），
 *    Canvas 2D 在这个量级上远未饱和，且不再需要 GPU 上下文；
 *  - 页面不可见时（`document.visibilityState === 'hidden'`）停帧，后台标签页不再耗电；
 *  - `reducedMotion` 下没有持续动画，仅在指针移动时按需重绘。
 */

const props = withDefaults(defineProps<{ reducedMotion?: boolean }>(), {reducedMotion: false})

const canvasRef = ref<HTMLCanvasElement | null>(null)

/** 与原 three 相机一致的视场角（度）与相机距离 */
const FOV_DEG = 45
const CAMERA_Z = 7

type Vec3 = [number, number, number]

/** 欧拉角 XYZ 顺序的旋转矩阵（three 默认顺序），返回 3×3 行主序 */
function rotationMatrix(rx: number, ry: number, rz: number): number[] {
  const cx = Math.cos(rx), sx = Math.sin(rx)
  const cy = Math.cos(ry), sy = Math.sin(ry)
  const cz = Math.cos(rz), sz = Math.sin(rz)

  // R = Rx · Ry · Rz
  return [
    cy * cz, -cy * sz, sy,
    sx * sy * cz + cx * sz, -sx * sy * sz + cx * cz, -sx * cy,
    -cx * sy * cz + sx * sz, cx * sy * sz + sx * cz, cx * cy,
  ]
}

function applyMatrix(m: number[], v: Vec3): Vec3 {
  return [
    m[0] * v[0] + m[1] * v[1] + m[2] * v[2],
    m[3] * v[0] + m[4] * v[1] + m[5] * v[2],
    m[6] * v[0] + m[7] * v[1] + m[8] * v[2],
  ]
}

/** 单位二十面体的 12 个顶点（与 three 的 PolyhedronGeometry 同一组） */
function icosahedronVertices(): Vec3[] {
  const t = (1 + Math.sqrt(5)) / 2
  const raw: Vec3[] = [
    [-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0],
    [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
    [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1],
  ]
  return raw.map((v): Vec3 => {
    const len = Math.hypot(v[0], v[1], v[2])
    return [v[0] / len, v[1] / len, v[2] / len]
  })
}

/** 与 three 相同的 20 个面（顶点索引） */
const ICOSAHEDRON_FACES: Vec3[] = [
  [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
  [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
  [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
  [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
] as unknown as Vec3[]

/** 顶点去重键（球面细分后同一中点由不同面算出，浮点略有差异） */
function keyOf(v: Vec3): string {
  return `${v[0].toFixed(5)},${v[1].toFixed(5)},${v[2].toFixed(5)}`
}

function normalize(v: Vec3, radius: number): Vec3 {
  const len = Math.hypot(v[0], v[1], v[2]) || 1
  return [(v[0] / len) * radius, (v[1] / len) * radius, (v[2] / len) * radius]
}

/**
 * 生成 `IcosahedronGeometry(radius, detail)` 的**唯一边**列表。
 *
 * detail=0 → 30 条边；detail=1 → 每个面细分成 4 个（中点投到球面）→ 80 面 / 120 条边。
 * 这与 three 的 `WireframeGeometry` 结果一致（共享边只画一次），
 * 因此这里的线段数与原来 WebGL 版本画出的线框是同一份。
 */
function icosahedronEdges(radius: number, detail: number): Array<[Vec3, Vec3]> {
  const base = icosahedronVertices()
  let faces: Array<[Vec3, Vec3, Vec3]> = ICOSAHEDRON_FACES.map(
    (f) => [base[f[0]], base[f[1]], base[f[2]]] as [Vec3, Vec3, Vec3],
  )

  for (let level = 0; level < detail; level += 1) {
    const next: Array<[Vec3, Vec3, Vec3]> = []
    for (const [a, b, c] of faces) {
      const ab = normalize([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2], 1)
      const bc = normalize([(b[0] + c[0]) / 2, (b[1] + c[1]) / 2, (b[2] + c[2]) / 2], 1)
      const ca = normalize([(c[0] + a[0]) / 2, (c[1] + a[1]) / 2, (c[2] + a[2]) / 2], 1)
      next.push([a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca])
    }
    faces = next
  }

  // 边去重（无向）
  const seen = new Set<string>()
  const edges: Array<[Vec3, Vec3]> = []
  for (const [a, b, c] of faces) {
    for (const [p, q] of [[a, b], [b, c], [c, a]] as Array<[Vec3, Vec3]>) {
      const ka = keyOf(p), kb = keyOf(q)
      const id = ka < kb ? `${ka}|${kb}` : `${kb}|${ka}`
      if (seen.has(id)) continue
      seen.add(id)
      edges.push([
        [p[0] * radius, p[1] * radius, p[2] * radius],
        [q[0] * radius, q[1] * radius, q[2] * radius],
      ])
    }
  }
  return edges
}

/** 圆环在局部 XY 平面上的采样点（对应 TorusGeometry 的主半径圆） */
function circlePoints(radius: number, segments: number): Vec3[] {
  const points: Vec3[] = []
  for (let i = 0; i < segments; i += 1) {
    const angle = (i / segments) * Math.PI * 2
    points.push([Math.cos(angle) * radius, Math.sin(angle) * radius, 0])
  }
  return points
}

/** 球壳内散布的星点位置（与原实现的 generateStarPositions 同一分布） */
function starPositions(count: number): Vec3[] {
  const positions: Vec3[] = []
  for (let i = 0; i < count; i += 1) {
    const radius = 4 + Math.random() * 5
    const theta = Math.random() * Math.PI * 2
    const phi = Math.acos(2 * Math.random() - 1)
    positions.push([
      radius * Math.sin(phi) * Math.cos(theta),
      radius * Math.sin(phi) * Math.sin(theta),
      radius * Math.cos(phi),
    ])
  }
  return positions
}

onMounted(() => {
  const canvas = canvasRef.value
  const context = canvas?.getContext('2d')
  if (!canvas || !context) return

  const ctx = context

  // ---- 几何（模块外只算一次） --------------------------------------------
  const outerEdges = icosahedronEdges(1.5, 1)
  const innerEdges = icosahedronEdges(1.5 * 0.55, 0)
  const ringA = circlePoints(2.7, 140)
  const ringB = circlePoints(2.4, 140)
  const stars = starPositions(180)

  // 内层小二十面体的固定局部旋转（对应 inner.rotation.set(0.4, 0.6, 0) + scale 0.55）
  const INNER_MATRIX = rotationMatrix(0.4, 0.6, 0)
  const RING_A_ROT: [number, number, number] = [Math.PI / 2.3, 0.4, 0]
  const RING_B_ROT: [number, number, number] = [-Math.PI / 2.7, -0.5, 0.3]
  const RING_B_SCALE = 1.15

  // ---- 状态 ---------------------------------------------------------------
  let width = 0
  let height = 0
  let dpr = 1
  let frameId = 0
  let lastTime = 0
  let elapsed = 0

  // group.rotation（自转累积 + 视差）；ringA/ringB 的 z 也在转动
  let groupRotX = 0
  let groupRotY = 0
  let ringASpin = 0
  let ringBSpin = 0

  const pointer = {x: 0, y: 0}
  const target = {x: 0, y: 0}

  /** 视锥半角正切，等价于 three 的 `1 / tan(fov/2)`（在投影里为倒数使用） */
  const tanHalfFov = Math.tan((FOV_DEG * Math.PI) / 180 / 2)

  function resize(): void {
    const parent = canvas!.parentElement
    const nextWidth = parent?.clientWidth || window.innerWidth
    const nextHeight = parent?.clientHeight || window.innerHeight
    // 与原 renderer.setPixelRatio(min(dpr, 1.5)) 一致
    dpr = Math.min(window.devicePixelRatio || 1, 1.5)
    width = nextWidth
    height = nextHeight
    canvas!.width = Math.max(1, Math.round(nextWidth * dpr))
    canvas!.height = Math.max(1, Math.round(nextHeight * dpr))
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  }

  /** 世界坐标 → 屏幕坐标（透视投影，等价于 three 的 PerspectiveCamera(45) 位于 z=7） */
  function project(p: Vec3): { x: number; y: number; scale: number } {
    const depth = CAMERA_Z - p[2]
    const scale = 1 / (tanHalfFov * Math.max(depth, 0.001))
    const nx = (p[0] * scale) / Math.max(width / Math.max(height, 1), 0.001)
    const ny = p[1] * scale
    return {
      x: (nx * 0.5 + 0.5) * width,
      y: (0.5 - ny * 0.5) * height,
      // 供 sizeAttenuation 使用：越远越小
      scale: scale / tanHalfFov,
    }
  }

  function strokeEdges(edges: Array<[Vec3, Vec3]>, color: string, alpha: number, group: number[], extra?: number[]): void {
    ctx.strokeStyle = color
    ctx.globalAlpha = alpha
    ctx.beginPath()
    for (const [rawA, rawB] of edges) {
      let a = rawA
      let b = rawB
      if (extra) {
        a = applyMatrix(extra, a)
        b = applyMatrix(extra, b)
      }
      const pa = project(applyMatrix(group, a))
      const pb = project(applyMatrix(group, b))
      ctx.moveTo(pa.x, pa.y)
      ctx.lineTo(pb.x, pb.y)
    }
    ctx.stroke()
  }

  function drawRing(points: Vec3[], rot: [number, number, number], spin: number, scale: number, color: string, alpha: number, group: number[]): void {
    const local = rotationMatrix(rot[0], rot[1], rot[2] + spin)
    ctx.strokeStyle = color
    ctx.globalAlpha = alpha
    ctx.beginPath()
    for (let i = 0; i < points.length; i += 1) {
      const p = points[i]
      const scaled: Vec3 = [p[0] * scale, p[1] * scale, p[2] * scale]
      const projected = project(applyMatrix(group, applyMatrix(local, scaled)))
      if (i === 0) ctx.moveTo(projected.x, projected.y)
      else ctx.lineTo(projected.x, projected.y)
    }
    ctx.closePath()
    ctx.stroke()
  }

  function drawStars(group: number[]): void {
    ctx.fillStyle = '#94a3b8'
    ctx.globalAlpha = 0.5
    for (const star of stars) {
      const projected = project(applyMatrix(group, star))
      // PointsMaterial(size: 0.02, sizeAttenuation: true)：屏幕尺寸随距离衰减
      const radius = Math.max(0.6, 0.02 * projected.scale * height * 0.5)
      ctx.beginPath()
      ctx.arc(projected.x, projected.y, radius, 0, Math.PI * 2)
      ctx.fill()
    }
  }

  function render(): void {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, width, height)
    ctx.lineWidth = 1
    ctx.lineJoin = 'round'

    const group = rotationMatrix(groupRotX, groupRotY, 0)

    strokeEdges(outerEdges, '#3b82f6', 0.32, group)
    strokeEdges(innerEdges, '#60a5fa', 0.22, group, INNER_MATRIX)
    drawRing(ringA, RING_A_ROT, ringASpin, 1, '#60a5fa', 0.18, group)
    drawRing(ringB, RING_B_ROT, ringBSpin, RING_B_SCALE, '#38bdf8', 0.12, group)
    drawStars(group)

    ctx.globalAlpha = 1
  }

  /** 与原实现同一套动画数学（含 reducedMotion 分支） */
  function step(time: number): void {
    const delta = Math.min(Math.max(time - lastTime, 0) / 1000, 0.05)
    lastTime = time
    elapsed += delta

    if (props.reducedMotion) {
      target.x += (pointer.x * 0.15 - target.x) * 0.03
      target.y += (pointer.y * 0.1 - target.y) * 0.03
      groupRotY = target.x
      groupRotX = target.y
      // 静止态：仅在视差仍在收敛时重绘，省掉空转帧
      const settled = Math.abs(pointer.x * 0.15 - target.x) < 0.0005
        && Math.abs(pointer.y * 0.1 - target.y) < 0.0005
      render()
      if (settled) {
        frameId = 0
        return
      }
    } else {
      groupRotY += delta * 0.12
      groupRotX = Math.sin(elapsed * 0.12) * 0.18

      target.x += (pointer.x * 0.35 - target.x) * 0.02
      target.y += (pointer.y * 0.25 - target.y) * 0.02
      groupRotY += target.x * delta * 0.6
      groupRotX += target.y * delta * 0.4

      ringASpin -= delta * 0.08
      ringBSpin += delta * 0.05

      render()
    }

    frameId = window.requestAnimationFrame(step)
  }

  function start(): void {
    if (frameId) return
    lastTime = performance.now()
    frameId = window.requestAnimationFrame(step)
  }

  function stop(): void {
    if (!frameId) return
    window.cancelAnimationFrame(frameId)
    frameId = 0
  }

  function onPointerMove(event: PointerEvent): void {
    pointer.x = (event.clientX / window.innerWidth) * 2 - 1
    pointer.y = -((event.clientY / window.innerHeight) * 2 - 1)
    // reducedMotion 下帧循环已停；指针一动按需恢复几帧做视差
    if (props.reducedMotion) start()
  }

  function onVisibilityChange(): void {
    // 后台标签页停帧：原 three 版本在隐藏时仍持续渲染，白耗电量
    if (document.visibilityState === 'hidden') stop()
    else start()
  }

  resize()
  render()

  window.addEventListener('resize', resize)
  window.addEventListener('pointermove', onPointerMove)
  document.addEventListener('visibilitychange', onVisibilityChange)

  if (props.reducedMotion) {
    // 静止态不自动起帧：首次进入只画一帧，等指针移动再做视差
    render()
  } else {
    start()
  }

  onBeforeUnmount(() => {
    stop()
    window.removeEventListener('resize', resize)
    window.removeEventListener('pointermove', onPointerMove)
    document.removeEventListener('visibilitychange', onVisibilityChange)
  })
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
