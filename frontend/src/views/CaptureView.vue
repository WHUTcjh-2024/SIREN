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
const stream = ref<MediaStream>()
const devices = ref<MediaDeviceInfo[]>([])
const selectedDevice = ref('')
const cameraActive = ref(false)
const file = ref<File>()
const preview = ref('')
const sourceLabel = ref('')
const frameSize = ref('— × —')
const capturedAt = ref('—')
const analysing = ref(false)
const elapsed = ref(0)
const error = ref('')
const steps = ref(Array.from({ length: 6 }, (_, index) => ({
  label: ['图像预处理', '刻度 OCR', '光强剖面', 'SIREN 拟合', '亚像素定位', '输出结果'][index],
  status: 'pending' as StepStatus
})))
const result = computed(() => state.measurement)
const statusText = computed(() => analysing.value ? 'AI 分析中' : file.value ? '已采集' : cameraActive.value ? '摄像头工作中' : '待机')

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
  image.onload = () => { frameSize.value = `${image.naturalWidth} × ${image.naturalHeight}` }
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
  sourceLabel.value = cameraActive.value ? '摄像头' : ''
  capturedAt.value = '—'
  steps.value.forEach(step => { step.status = 'pending' })
}

async function analyse() {
  if (!file.value || analysing.value) return
  analysing.value = true
  error.value = ''
  elapsed.value = 0
  steps.value.forEach(step => { step.status = 'pending' })
  steps.value[0].status = 'start'
  const started = performance.now()
  const clock = window.setInterval(() => { elapsed.value = (performance.now() - started) / 1000 }, 100)
  const animation = window.setInterval(() => {
    const active = steps.value.findIndex(step => step.status === 'start')
    if (active >= 0 && active < steps.value.length - 2) {
      steps.value[active].status = 'done'
      steps.value[active + 1].status = 'start'
    }
  }, 1300)
  const body = new FormData()
  body.append('images', file.value)
  try {
    const response = await fetch('/api/laser-diffraction-stream', { method: 'POST', body })
    for await (const event of readNdjson(response)) {
      if (event.event === 'step') {
        const index = Number(event.data.step)
        if (steps.value[index]) steps.value[index].status = event.data.status === 'done' ? 'done' : 'start'
      } else if (event.event === 'result') {
        state.measurement = event.data.data as Measurement
        state.progress = Math.max(state.progress, 60)
        steps.value.forEach(step => { step.status = 'done' })
      } else if (event.event === 'error') throw new Error(event.data.message)
    }
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '分析失败'
    const current = steps.value.find(step => step.status === 'start')
    if (current) current.status = 'pending'
  } finally {
    window.clearInterval(clock)
    window.clearInterval(animation)
    analysing.value = false
  }
}

onBeforeUnmount(() => { stopCamera(); releasePreview() })
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

    <section v-if="file || analysing || result" class="card original-panel analysis-progress">
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
