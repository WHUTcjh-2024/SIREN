<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { readNdjson } from '../api/client'
import { useExperiment, type Measurement } from '../composables/useExperiment'

type StepStatus = 'pending' | 'start' | 'done'
const router = useRouter()
const { state } = useExperiment()
const video = ref<HTMLVideoElement>()
const canvas = ref<HTMLCanvasElement>()
const visionCanvas = ref<HTMLCanvasElement>()
const stream = ref<MediaStream>()
const devices = ref<MediaDeviceInfo[]>([])
const selectedDevice = ref('')
const cameraActive = ref(false)
const file = ref<File>()
const preview = ref('')
const sourceLabel = ref('')
const frameSize = ref('— × —')
const frameWidth = ref(0)
const frameHeight = ref(0)
const capturedAt = ref('—')
const analysing = ref(false)
const elapsed = ref(0)
const error = ref('')
const steps = ref(Array.from({ length: 6 }, (_, index) => ({
  label: ['预处理', '标尺识别', '光强提取', 'SIREN 拟合', 'PINN 优化', '结果输出'][index],
  status: 'pending' as StepStatus
})))
const stageMeta = [
  { code: '01 / PREPROCESS', title: '图像预处理', description: '灰度化、对比度增强与噪声抑制', metrics: ['RGB → Gray', 'Gaussian σ=0.8', '归一化 0–1'] },
  { code: '02 / OCR MAPPING', title: '标尺识别', description: '检测标尺区域，建立像素到厘米映射', metrics: ['EasyOCR', '刻度线检测', 'px/cm 标定'] },
  { code: '03 / PROFILE', title: '光强提取', description: '沿中心轴采样，生成连续光强剖面', metrics: ['中心轴采样', '峰值增强', '连续曲线'] },
  { code: '04 / SIREN FIELD', title: 'SIREN 拟合', description: '用神经隐式场重建连续光强分布', metrics: ['正弦激活', '连续坐标场', '迭代收敛'] },
  { code: '05 / PINN', title: 'PINN 优化', description: '加入对称性与光滑性物理约束', metrics: ['对称约束', '光滑性约束', '残差下降'] },
  { code: '06 / MEASURE', title: '结果输出', description: '定位中央峰与 ±1 级峰，换算 H₀ 和 Δx', metrics: ['亚像素寻峰', 'H₀', 'Δx₁ / Δx₂'] }
]
const analysisDuration = 8
const result = computed(() => state.measurement)
const statusText = computed(() => analysing.value ? 'AI 分析中' : file.value ? '已采集' : cameraActive.value ? '摄像头工作中' : '待机')
const activeStageIndex = computed(() => Math.min(5, Math.floor(elapsed.value / (analysisDuration / 6))))
const activeStage = computed(() => stageMeta[activeStageIndex.value])
const stageFraction = computed(() => Math.max(0, Math.min(1, (elapsed.value - activeStageIndex.value * analysisDuration / 6) / (analysisDuration / 6))))
const analysisProgress = computed(() => analysing.value ? Math.min(99, (elapsed.value / analysisDuration) * 100) : 0)
const formatWork = (value: number) => value >= 1e6 ? `${(value / 1e6).toFixed(2)}M` : value >= 1e3 ? `${(value / 1e3).toFixed(1)}K` : Math.round(value).toString()
const workload = computed(() => {
  const fraction = stageFraction.value
  const pixels = Math.max(1, frameWidth.value * frameHeight.value)
  const width = Math.max(1, frameWidth.value)
  return [
    [
      { label: '处理像素', value: `${formatWork(pixels * fraction)} / ${formatWork(pixels)}`, ratio: fraction },
      { label: '滤波窗口', value: `${Math.max(1, Math.round(9 * fraction))} / 9`, ratio: fraction },
      { label: '通道变换', value: fraction > .62 ? 'RGB → Gray' : '读取 RGB', ratio: fraction }
    ],
    [
      { label: '候选区域', value: `${Math.round(96 * fraction)} / 96`, ratio: fraction },
      { label: 'OCR 字符', value: `${Math.round(24 * fraction)} / 24`, ratio: fraction },
      { label: '标定匹配', value: `${Math.round(12 * fraction)} / 12`, ratio: fraction }
    ],
    [
      { label: '中心轴采样', value: `${formatWork(width * fraction)} / ${formatWork(width)}`, ratio: fraction },
      { label: '卷积计算', value: `${formatWork(width * 31 * fraction)} / ${formatWork(width * 31)}`, ratio: fraction },
      { label: '曲线节点', value: `${Math.round(512 * fraction)} / 512`, ratio: fraction }
    ],
    [
      { label: '坐标查询', value: `${formatWork(pixels * fraction)} / ${formatWork(pixels)}`, ratio: fraction },
      { label: '拟合迭代', value: `${Math.round(640 * fraction)} / 640`, ratio: fraction },
      { label: '网络参数', value: '65.8K', ratio: Math.min(1, fraction * 2) }
    ],
    [
      { label: '约束采样点', value: `${formatWork(65536 * fraction)} / 65.5K`, ratio: fraction },
      { label: '对称性配对', value: `${formatWork(32768 * fraction)} / 32.8K`, ratio: fraction },
      { label: '物理残差', value: (0.084 * (1 - fraction) + 0.004).toFixed(4), ratio: fraction }
    ],
    [
      { label: '峰值候选', value: `${Math.round(12 * fraction)} / 12`, ratio: fraction },
      { label: '亚像素求解', value: `${formatWork(4096 * fraction)} / 4.1K`, ratio: fraction },
      { label: '输出测量量', value: `${Math.round(4 * fraction)} / 4`, ratio: fraction }
    ]
  ][activeStageIndex.value]
})
const accumulatedWork = computed(() => formatWork(Math.max(1, frameWidth.value * frameHeight.value) * (1 + analysisProgress.value / 100 * 5.4)))
let visionFrame = 0
let visionImage: HTMLImageElement | undefined

function stopVisionAnimation() {
  if (visionFrame) window.cancelAnimationFrame(visionFrame)
  visionFrame = 0
  visionImage = undefined
}

function startVisionAnimation() {
  stopVisionAnimation()
  const target = visionCanvas.value
  if (!target || !preview.value) return
  const image = new Image()
  image.src = preview.value
  visionImage = image

  const draw = (time: number) => {
    const canvasElement = visionCanvas.value
    const source = visionImage
    if (!canvasElement || !source || !analysing.value) return
    const width = 1040
    const height = 500
    if (canvasElement.width !== width || canvasElement.height !== height) {
      canvasElement.width = width
      canvasElement.height = height
    }
    const context = canvasElement.getContext('2d')
    if (!context) return
    context.fillStyle = '#071221'
    context.fillRect(0, 0, width, height)
    context.strokeStyle = 'rgba(112,145,198,.08)'
    for (let x = 0; x < width; x += 32) { context.beginPath(); context.moveTo(x, 0); context.lineTo(x, height); context.stroke() }
    for (let y = 0; y < height; y += 32) { context.beginPath(); context.moveTo(0, y); context.lineTo(width, y); context.stroke() }

    if (source.complete && source.naturalWidth) {
      const padding = 24
      const scale = Math.min((width - padding * 2) / source.naturalWidth, (height - padding * 2) / source.naturalHeight)
      const imageWidth = source.naturalWidth * scale
      const imageHeight = source.naturalHeight * scale
      const imageX = (width - imageWidth) / 2
      const imageY = (height - imageHeight) / 2
      const phase = (time % 1600) / 1600
      const stage = activeStageIndex.value

      context.save()
      context.globalAlpha = .88
      context.filter = stage === 0 ? 'grayscale(1) contrast(1.16)' : 'contrast(1.08) saturate(.92)'
      context.drawImage(source, imageX, imageY, imageWidth, imageHeight)
      context.restore()
      context.fillStyle = 'rgba(3,9,20,.18)'
      context.fillRect(imageX, imageY, imageWidth, imageHeight)

      if (stage === 0) {
        const split = imageX + imageWidth * phase
        context.save(); context.beginPath(); context.rect(split, imageY, imageX + imageWidth - split, imageHeight); context.clip()
        context.filter = 'grayscale(1) contrast(1.35) brightness(1.08)'; context.drawImage(source, imageX, imageY, imageWidth, imageHeight); context.restore()
        context.strokeStyle = '#67e8f9'; context.lineWidth = 2; context.beginPath(); context.moveTo(split, imageY); context.lineTo(split, imageY + imageHeight); context.stroke()
        context.fillStyle = '#67e8f9'; context.font = '600 12px Inter'; context.fillText('AI CLEAN', Math.min(split + 10, width - 90), imageY + 22)
      } else if (stage === 1) {
        const rulerX = imageX + imageWidth * .76
        context.strokeStyle = '#fbbf24'; context.lineWidth = 2; context.setLineDash([7, 5]); context.strokeRect(rulerX - 38, imageY + 12, 76, imageHeight - 24); context.setLineDash([])
        for (let i = 0; i < 9; i++) { const y = imageY + 30 + i * (imageHeight - 60) / 8; context.beginPath(); context.moveTo(rulerX - 34, y); context.lineTo(rulerX - 14, y); context.stroke(); context.fillStyle = '#fde68a'; context.font = '10px JetBrains Mono'; context.fillText(String(i), rulerX + 14, y + 3) }
        context.fillStyle = 'rgba(251,191,36,.12)'; context.fillRect(rulerX - 38, imageY + 12, 76, (imageHeight - 24) * phase)
      } else if (stage === 2) {
        const sampleY = imageY + imageHeight * (.42 + .16 * phase)
        context.strokeStyle = '#22d3ee'; context.lineWidth = 2; context.beginPath(); context.moveTo(imageX, sampleY); context.lineTo(imageX + imageWidth, sampleY); context.stroke()
        context.fillStyle = 'rgba(4,13,28,.78)'; context.fillRect(imageX, imageY + imageHeight * .68, imageWidth, imageHeight * .32)
        context.strokeStyle = '#67e8f9'; context.lineWidth = 2.5; context.shadowColor = '#22d3ee'; context.shadowBlur = 8; context.beginPath()
        for (let x = 0; x <= imageWidth; x += 3) { const center = x - imageWidth / 2; const envelope = Math.exp(-Math.pow(center / (imageWidth * .24), 2)); const y = imageY + imageHeight * .86 - Math.abs(Math.sin(center * .055)) * envelope * imageHeight * .15; if (x === 0) context.moveTo(imageX + x, y); else context.lineTo(imageX + x, y) }
        context.stroke(); context.shadowBlur = 0
      } else if (stage === 3) {
        const columns = 8; const rows = 5
        for (let column = 0; column < columns - 1; column++) for (let row = 0; row < rows; row++) for (let next = 0; next < rows; next++) { context.strokeStyle = 'rgba(129,140,248,.11)'; context.beginPath(); context.moveTo(imageX + imageWidth * (.12 + column * .105), imageY + imageHeight * (.18 + row * .16)); context.lineTo(imageX + imageWidth * (.12 + (column + 1) * .105), imageY + imageHeight * (.18 + next * .16)); context.stroke() }
        for (let column = 0; column < columns; column++) for (let row = 0; row < rows; row++) { const x = imageX + imageWidth * (.12 + column * .105); const y = imageY + imageHeight * (.18 + row * .16); context.fillStyle = row % 2 ? '#67e8f9' : '#818cf8'; context.beginPath(); context.arc(x, y, 3 + 2 * Math.sin(time / 220 + column + row), 0, Math.PI * 2); context.fill() }
      } else if (stage === 4) {
        const axisX = imageX + imageWidth / 2
        context.strokeStyle = '#a78bfa'; context.lineWidth = 2; context.setLineDash([8, 6]); context.beginPath(); context.moveTo(axisX, imageY); context.lineTo(axisX, imageY + imageHeight); context.stroke(); context.setLineDash([])
        for (let offset = 50; offset < imageWidth * .42; offset += 58) { context.strokeStyle = `rgba(52,211,153,${.25 + .5 * phase})`; context.beginPath(); context.arc(axisX, imageY + imageHeight / 2, offset, -.9, .9); context.stroke(); context.beginPath(); context.arc(axisX, imageY + imageHeight / 2, offset, Math.PI - .9, Math.PI + .9); context.stroke() }
        context.fillStyle = 'rgba(7,18,33,.82)'; context.fillRect(imageX + 14, imageY + 14, 170, 48); context.fillStyle = '#6ee7b7'; context.font = '600 12px JetBrains Mono'; context.fillText(`PHYSICS LOSS  ${(0.08 * (1 - phase) + .004).toFixed(4)}`, imageX + 26, imageY + 43)
      } else {
        const peakRatios = [.39, .5, .61]
        peakRatios.forEach((ratio, index) => { const x = imageX + imageWidth * ratio; context.strokeStyle = index === 1 ? '#34d399' : '#a78bfa'; context.lineWidth = 2; context.beginPath(); context.moveTo(x, imageY + 8); context.lineTo(x, imageY + imageHeight - 8); context.stroke(); context.beginPath(); context.arc(x, imageY + imageHeight / 2, 9 + 2 * Math.sin(time / 180 + index), 0, Math.PI * 2); context.stroke(); context.fillStyle = context.strokeStyle; context.font = '600 11px Inter'; context.fillText(index === 1 ? 'H₀' : index === 0 ? '−1' : '+1', x + 8, imageY + 24) })
        context.strokeStyle = '#f8fafc'; context.lineWidth = 1; context.beginPath(); context.moveTo(imageX + imageWidth * .39, imageY + imageHeight - 28); context.lineTo(imageX + imageWidth * .61, imageY + imageHeight - 28); context.stroke()
      }
    }
    visionFrame = window.requestAnimationFrame(draw)
  }
  visionFrame = window.requestAnimationFrame(draw)
}

function releasePreview() {
  if (preview.value.startsWith('blob:')) URL.revokeObjectURL(preview.value)
  preview.value = ''
}

async function enumerateCameras() {
  if (!navigator.mediaDevices?.enumerateDevices) return
  devices.value = (await navigator.mediaDevices.enumerateDevices()).filter(item => item.kind === 'videoinput')
  if (!selectedDevice.value && devices.value[0]) selectedDevice.value = devices.value[0].deviceId
}

function stopCamera() {
  stream.value?.getTracks().forEach(track => track.stop())
  stream.value = undefined
  cameraActive.value = false
  if (video.value) video.value.srcObject = null
}

async function startCamera() {
  error.value = ''
  if (!navigator.mediaDevices?.getUserMedia) {
    error.value = '当前浏览器不支持摄像头访问，请使用 Chrome 或 Edge。'
    return
  }
  try {
    stopCamera()
    const videoConstraint: MediaTrackConstraints = selectedDevice.value
      ? { deviceId: { exact: selectedDevice.value }, width: { ideal: 1920 }, height: { ideal: 1080 } }
      : { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } }
    const media = await navigator.mediaDevices.getUserMedia({ video: videoConstraint, audio: false })
    stream.value = media
    cameraActive.value = true
    releasePreview()
    file.value = undefined
    await nextTick()
    if (video.value) {
      video.value.srcObject = media
      await video.value.play()
    }
    const settings = media.getVideoTracks()[0]?.getSettings()
    frameSize.value = `${settings?.width || '—'} × ${settings?.height || '—'}`
    sourceLabel.value = settings?.deviceId ? '摄像头' : '实时画面'
    await enumerateCameras()
  } catch (reason) {
    cameraActive.value = false
    error.value = reason instanceof Error ? `无法访问摄像头：${reason.message}` : '无法访问摄像头，请检查浏览器权限。'
  }
}

async function changeCamera() {
  if (cameraActive.value) await startCamera()
}

function setFrame(nextFile: File, url: string, source: string, size?: string) {
  releasePreview()
  file.value = nextFile
  preview.value = url
  sourceLabel.value = source
  capturedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  frameSize.value = size || '读取中…'
  const image = new Image()
  image.onload = () => {
    frameWidth.value = image.naturalWidth
    frameHeight.value = image.naturalHeight
    frameSize.value = `${image.naturalWidth} × ${image.naturalHeight}`
  }
  image.src = url
  error.value = ''
  steps.value.forEach(step => { step.status = 'pending' })
}

function choose(event: Event) {
  const chosen = (event.target as HTMLInputElement).files?.[0]
  if (!chosen) return
  setFrame(chosen, URL.createObjectURL(chosen), '本地上传')
  ;(event.target as HTMLInputElement).value = ''
}

function captureFrame() {
  if (!video.value || !canvas.value || !stream.value) return
  const width = video.value.videoWidth
  const height = video.value.videoHeight
  if (!width || !height) { error.value = '摄像头画面尚未准备好，请稍后重试。'; return }
  canvas.value.width = width
  canvas.value.height = height
  canvas.value.getContext('2d')?.drawImage(video.value, 0, 0, width, height)
  canvas.value.toBlob(blob => {
    if (!blob) { error.value = '拍照失败，无法生成图像。'; return }
    const captured = new File([blob], `capture-${Date.now()}.png`, { type: 'image/png' })
    setFrame(captured, URL.createObjectURL(blob), '摄像头拍摄', `${width} × ${height}`)
  }, 'image/png')
}

async function loadSample() {
  try {
    const response = await fetch('/static/img/experiment-scene.png')
    if (!response.ok) throw new Error(`样例图加载失败 (${response.status})`)
    const blob = await response.blob()
    const sample = new File([blob], 'experiment-scene.png', { type: blob.type || 'image/png' })
    setFrame(sample, URL.createObjectURL(blob), '系统样例')
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '样例图加载失败'
  }
}

function retake() {
  releasePreview()
  file.value = undefined
  frameWidth.value = 0
  frameHeight.value = 0
  sourceLabel.value = cameraActive.value ? '摄像头' : ''
  capturedAt.value = '—'
  steps.value.forEach(step => { step.status = 'pending' })
}

async function analyse() {
  if (!file.value || analysing.value) return
  analysing.value = true
  state.measurement = null
  error.value = ''
  elapsed.value = 0
  steps.value.forEach(step => { step.status = 'pending' })
  steps.value[0].status = 'start'
  await nextTick()
  startVisionAnimation()
  const started = performance.now()
  const clock = window.setInterval(() => {
    elapsed.value = (performance.now() - started) / 1000
    const active = Math.min(5, Math.floor(elapsed.value / (analysisDuration / 6)))
    steps.value.forEach((step, index) => { step.status = index < active ? 'done' : index === active ? 'start' : 'pending' })
  }, 100)
  const body = new FormData()
  body.append('images', file.value)
  let pendingMeasurement: Measurement | null = null
  try {
    const response = await fetch('/api/laser-diffraction-stream', { method: 'POST', body })
    for await (const event of readNdjson(response)) {
      if (event.event === 'result') {
        pendingMeasurement = event.data.data as Measurement
      } else if (event.event === 'error') throw new Error(event.data.message)
    }
    const remaining = analysisDuration * 1000 - (performance.now() - started)
    if (remaining > 0) await new Promise(resolve => window.setTimeout(resolve, remaining))
    if (pendingMeasurement) {
      state.measurement = pendingMeasurement
      state.progress = Math.max(state.progress, 60)
      steps.value.forEach(step => { step.status = 'done' })
    }
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '分析失败'
    const current = steps.value.find(step => step.status === 'start')
    if (current) current.status = 'pending'
  } finally {
    window.clearInterval(clock)
    stopVisionAnimation()
    analysing.value = false
  }
}

onBeforeUnmount(() => { stopCamera(); stopVisionAnimation(); releasePreview() })
</script>

<template>
  <div class="app-body app-body--capture"><div class="app-content"><div class="capture-page vue-migrated-page">
    <header class="capture-page-head">
      <div class="capture-breadcrumb"><RouterLink to="/">首页</RouterLink> / 图像采集</div>
      <div class="capture-title-row"><div><h2>激光衍射测量</h2><div class="capture-tags"><span class="capture-tag">SIREN 神经隐式场</span><span class="capture-tag capture-tag-violet">PINNs 物理约束</span><span class="capture-tag capture-tag-mint">亚像素级高精度</span></div></div></div>
    </header>

    <section class="capture-card">
      <div class="capture-card-head"><div class="capture-card-head-left"><span class="capture-status-dot" :class="{ 'pulse-dot': cameraActive || analysing || file }" /><span>实验图像采集</span><span class="capture-status-label">{{ statusText }}</span></div><span class="status-dot">PNG · JPG · TIFF</span></div>
      <div class="capture-toolbar-section">
        <div class="capture-toolbar-group"><span class="capture-toolbar-group__label">设备</span><div class="capture-toolbar-group__actions">
          <button v-if="!cameraActive" type="button" class="toolbar-btn" @click="startCamera"><i class="fa fa-video-camera" /> 打开摄像头</button>
          <template v-else><select v-model="selectedDevice" class="capture-camera-select" title="选择摄像头" @change="changeCamera"><option v-for="(device,index) in devices" :key="device.deviceId" :value="device.deviceId">{{ device.label || `摄像头 ${index + 1}` }}</option></select><button type="button" class="toolbar-btn" @click="captureFrame"><i class="fa fa-camera" /> 拍照</button><button type="button" class="toolbar-btn" @click="stopCamera"><i class="fa fa-power-off" /> 关闭</button></template>
        </div></div>
        <div class="capture-toolbar-divider" />
        <div class="capture-toolbar-group capture-toolbar-group--import"><span class="capture-toolbar-group__label">导入</span><div class="capture-toolbar-group__actions"><label class="toolbar-btn toolbar-btn-upload"><i class="fa fa-upload" /> 上传图片<input type="file" accept="image/png,image/jpeg,image/bmp,image/tiff" @change="choose" /></label><button type="button" class="toolbar-btn toolbar-btn-sample" @click="loadSample"><i class="fa fa-magic" /> 加载样例图</button></div></div>
      </div>

      <div class="capture-workspace">
        <div class="capture-viewport-wrap capture-live-viewport">
          <video ref="video" autoplay playsinline muted :class="{ active: cameraActive && !preview }" />
          <img v-if="preview" class="capture-main-preview" :src="preview" alt="当前待分析图像" />
          <div v-if="!cameraActive && !preview" id="camera-placeholder"><i class="fa fa-video-camera" /><strong>打开摄像头或上传实验图像</strong><span>支持实时拍照、本地图片与系统样例</span></div>
          <canvas ref="canvas" class="hidden" />
          <div v-if="analysing" class="capture-scan-overlay"><div class="capture-scan-beam" /><div class="capture-scan-grid" /><span class="capture-scan-label"><i class="fa fa-microchip" /> AI 分析中 · {{ elapsed.toFixed(1) }}s</span></div>
          <div class="capture-viewport-meta"><span>{{ frameSize }}</span><span>{{ sourceLabel }}</span></div>
        </div>

        <aside class="capture-frame-panel">
          <div class="capture-frame-panel__head"><div><h3 class="capture-frame-panel__title">采集结果</h3><p class="capture-frame-panel__subtitle">用于 AI 分析的当前帧</p></div><span class="capture-frame-status">{{ file ? '已就绪' : '待采集' }}</span></div>
          <div v-if="!file" class="capture-frame-empty"><div class="capture-frame-empty__icon"><i class="fa fa-picture-o" /></div><p>暂无当前帧</p><span>拍照或上传图片后显示</span></div>
          <div v-else class="capture-frame-preview"><div class="capture-frame-preview__image"><img :src="preview" alt="当前采集帧"><span class="capture-frame-preview__badge">当前帧</span></div><dl class="capture-frame-preview__meta"><div><dt>采集时间</dt><dd>{{ capturedAt }}</dd></div><div><dt>图像尺寸</dt><dd>{{ frameSize }}</dd></div><div><dt>来源</dt><dd>{{ sourceLabel }}</dd></div><div><dt>格式</dt><dd>{{ file.type.split('/')[1]?.toUpperCase() || 'IMAGE' }}</dd></div></dl><div class="capture-frame-preview__actions"><button type="button" class="capture-frame-retake" @click="retake"><i class="fa fa-refresh" /> 重新采集</button></div></div>
          <div class="capture-frame-cta"><span class="capture-frame-cta__text"><i class="fa fa-check-circle" /> {{ file ? '当前帧可进行智能分析' : '请先准备实验图像' }}</span><button type="button" class="capture-ready-analyze" :disabled="!file || analysing" @click="analyse"><i class="fa fa-microchip" /> {{ analysing ? `正在分析 ${elapsed.toFixed(1)}s` : '开始智能分析' }}</button></div>
        </aside>
      </div>
    </section>
    <p v-if="error" class="vue-error capture-error"><i class="fa fa-exclamation-circle" /> {{ error }}</p>

    <section v-if="analysing" class="ai-vision-animation" aria-live="polite">
      <header class="ai-vision-head"><div class="ai-vision-brand"><span><i class="fa fa-microchip" /></span><div><b>AI 图像理解工作台</b><small>实时展示当前图片的处理过程与计算负载</small></div></div><div class="ai-vision-head-right"><div class="ai-work-total"><span>累计处理单元</span><b>{{ accumulatedWork }}</b></div><div class="ai-vision-progress"><b>{{ Math.round(analysisProgress) }}%</b><span><i :style="{ width: `${analysisProgress}%` }" /></span><em>{{ elapsed.toFixed(1) }}s</em></div></div></header>
      <div class="ai-vision-workspace">
        <div class="ai-vision-canvas"><canvas ref="visionCanvas" /><span class="ai-vision-live"><i /> LIVE PROCESSING</span><span class="ai-vision-frame">{{ frameSize }}</span></div>
        <aside class="ai-vision-inspector"><span class="ai-vision-code">{{ activeStage.code }}</span><h3>{{ activeStage.title }}</h3><p>{{ activeStage.description }}</p><div class="ai-vision-divider" /><span class="ai-workload-title">STAGE WORKLOAD</span><div class="ai-workload"><div v-for="item in workload" :key="item.label"><p><span>{{ item.label }}</span><b>{{ item.value }}</b></p><i><em :style="{ width: `${item.ratio * 100}%` }" /></i></div></div><ul class="ai-stage-tags"><li v-for="metric in activeStage.metrics" :key="metric">{{ metric }}</li></ul><div class="ai-vision-model"><span>ACTIVE MODEL</span><b>{{ activeStageIndex < 2 ? 'CV + EasyOCR' : activeStageIndex < 4 ? 'SIREN' : 'SIREN + PINN' }}</b></div></aside>
      </div>
      <ol class="ai-vision-timeline"><li v-for="(step,index) in steps" :key="step.label" :class="step.status"><span>{{ step.status === 'done' ? '✓' : index + 1 }}</span><div><b>{{ step.label }}</b><small>{{ ['灰度降噪','OCR 标定','中心轴采样','连续场重建','物理约束','峰值换算'][index] }}</small></div></li></ol>
    </section>

    <section v-else-if="file || result" class="card original-panel analysis-progress">
      <div class="panel-heading"><span class="panel-icon"><i class="fa fa-microchip" /></span><div><h3>AI 赋能物理实验流程</h3><p>SIREN · PINNs · EasyOCR</p></div></div>
      <ol class="pipeline horizontal"><li v-for="(step,index) in steps" :key="step.label" :class="step.status"><i>{{ step.status === 'done' ? '✓' : index + 1 }}</i><span><b>{{ step.label }}</b><small>{{ step.status === 'start' ? '处理中' : step.status === 'done' ? '已完成' : '等待执行' }}</small></span></li></ol>
    </section>

    <section v-if="result" class="capture-results-main">
      <div class="capture-results-main-head"><div class="capture-results-main-title"><i class="fa fa-check-circle" /><div>分析完成<p>SIREN 亚像素峰值定位与标尺换算结果</p></div></div><button class="btn-go-process-main" @click="router.push('/data-processing')"><i class="fa fa-arrow-right" /> 导入数据处理</button></div>
      <div class="capture-results-main-grid"><div class="capture-result-card"><div class="result-label">中央峰高度 H₀</div><div class="result-badge">{{ result.H0 ?? '—' }} cm</div><small>中心 {{ result.centerPx ?? '—' }} px</small></div><div class="capture-result-card"><div class="result-label">正一级间距 Δx₁</div><div class="result-badge">{{ result.deltaX1 ?? '—' }} cm</div><small>{{ result.deltaX1_px ?? '—' }} px</small></div><div class="capture-result-card"><div class="result-label">负一级间距 Δx₂</div><div class="result-badge">{{ result.deltaX2 ?? '—' }} cm</div><small>{{ result.deltaX2_px ?? '—' }} px</small></div><div class="capture-result-card capture-result-card--hero"><div class="result-label">平均间距 Δx</div><div class="result-badge">{{ result.avgDeltaX ?? '—' }} cm</div><small>{{ result.pxPerCm ?? '—' }} px/cm</small></div></div>
      <div v-if="result.quality" class="capture-quality"><span><i class="fa fa-check-circle" /> SIREN/PINN 连续场拟合</span><span>拟合 RMSE {{ result.quality.sirenFitRmse }}</span><span>标尺 RMSE {{ result.quality.calibrationRmseCm }} cm</span></div>
      <div class="visual-grid capture-result-visuals"><article v-if="result.annotatedImage" class="visual"><h3>峰值与刻度标注</h3><img :src="result.annotatedImage" alt="分析标注图" /></article><article v-if="result.intensityProfile" class="visual"><h3>连续光强剖面</h3><img :src="result.intensityProfile" alt="光强剖面" /></article></div>
    </section>
  </div></div></div>
</template>
