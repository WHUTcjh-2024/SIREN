<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { readNdjson } from '../api/client'
import { useExperiment, type Measurement } from '../composables/useExperiment'

const router = useRouter()
const { state } = useExperiment()
const file = ref<File>()
const preview = ref('')
const analysing = ref(false)
const error = ref('')
const steps = ref(Array.from({ length: 6 }, (_, index) => ({ label: ['图像预处理', '刻度 OCR', '光强剖面', 'SIREN 拟合', '亚像素定位', '输出结果'][index], status: 'pending' })))
const result = computed(() => state.measurement)

function choose(event: Event) {
  const chosen = (event.target as HTMLInputElement).files?.[0]
  if (!chosen) return
  file.value = chosen
  if (preview.value) URL.revokeObjectURL(preview.value)
  preview.value = URL.createObjectURL(chosen)
  error.value = ''
}

async function analyse() {
  if (!file.value || analysing.value) return
  analysing.value = true
  error.value = ''
  steps.value.forEach(item => item.status = 'pending')
  const body = new FormData()
  body.append('images', file.value)
  try {
    const response = await fetch('/api/laser-diffraction-stream', { method: 'POST', body })
    for await (const event of readNdjson(response)) {
      if (event.event === 'step') {
        const index = Number(event.data.step)
        if (steps.value[index]) steps.value[index].status = event.data.status
      } else if (event.event === 'result') {
        state.measurement = event.data.data as Measurement
        state.progress = Math.max(state.progress, 60)
        steps.value.forEach(item => item.status = 'done')
      } else if (event.event === 'error') throw new Error(event.data.message)
    }
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '分析失败'
  } finally { analysing.value = false }
}
</script>

<template>
  <div class="page capture-page">
    <!-- Page Header -->
    <section class="page-intro">
      <div>
        <span class="eyebrow">Diffraction Analysis</span>
        <h2>激光衍射测量</h2>
        <p>SIREN 神经隐式场 · PINNs 物理约束 · 亚像素级高精度测量</p>
      </div>
      <button v-if="result" class="primary" @click="router.push('/data-processing')">
        导入数据处理 →
      </button>
    </section>

    <!-- Upload & Results Grid -->
    <div class="capture-grid">
      <!-- Upload Panel -->
      <section class="card upload-panel">
        <div class="section-title">
          <div>
            <span class="eyebrow">输入</span>
            <h3>实验图像</h3>
          </div>
          <span class="status-dot">PNG · JPG · TIFF</span>
        </div>
        <label class="drop-zone" :class="{ filled: preview }">
          <input type="file" accept="image/png,image/jpeg,image/bmp,image/tiff" @change="choose" />
          <img v-if="preview" :src="preview" alt="待分析实验图像" />
          <template v-else>
            <i>＋</i>
            <b>点击选择衍射图像</b>
            <p>单张图片最大 16 MB</p>
          </template>
        </label>
        <button class="primary full" :disabled="!file || analysing" @click="analyse">
          {{ analysing ? '正在分析…' : '开始智能分析' }}
        </button>
        <p v-if="error" class="error">{{ error }}</p>
      </section>

      <!-- Quick Results Panel -->
      <section class="card pipeline-panel quick-results">
        <div class="panel-heading">
          <span class="panel-icon"><i class="fa fa-crosshairs" /></span>
          <div>
            <h3>快速测量结果</h3>
            <p>AI 自动识别并计算</p>
          </div>
        </div>
        <div class="quick-result">
          <span>中央峰高度 H₀</span>
          <b>{{ result?.H0 ?? '—' }} <small>cm</small></b>
        </div>
        <div class="quick-pair">
          <div>
            <span>Δx₁ (+1级)</span>
            <b>{{ result?.deltaX1 ?? '—' }}</b>
          </div>
          <div>
            <span>Δx₂ (-1级)</span>
            <b>{{ result?.deltaX2 ?? '—' }}</b>
          </div>
        </div>
        <div class="quick-result average">
          <span>平均间距 Δx</span>
          <b>{{ result?.avgDeltaX ?? '—' }} <small>cm</small></b>
        </div>
      </section>
    </div>

    <!-- Analysis Progress -->
    <section v-if="analysing || result" class="card original-panel analysis-progress">
      <div class="panel-heading">
        <span class="panel-icon"><i class="fa fa-microchip" /></span>
        <div>
          <h3>AI 赋能物理实验流程</h3>
          <p>SIREN · PINNs · EasyOCR</p>
        </div>
      </div>
      <ol class="pipeline horizontal">
        <li v-for="(step, index) in steps" :key="step.label" :class="step.status">
          <i>{{ step.status === 'done' ? '✓' : index + 1 }}</i>
          <span>
            <b>{{ step.label }}</b>
            <small>{{ step.status === 'start' ? '处理中' : step.status === 'done' ? '已完成' : '等待执行' }}</small>
          </span>
        </li>
      </ol>
    </section>

    <!-- Detailed Results -->
    <section v-if="result" class="results">
      <div class="measurement-grid">
        <article class="card">
          <span>中央峰高度 H₀</span>
          <b>{{ result.H0 ?? '—' }}</b>
          <small>cm</small>
        </article>
        <article class="card">
          <span>正一级间距 Δx₁</span>
          <b>{{ result.deltaX1 ?? '—' }}</b>
          <small>cm</small>
        </article>
        <article class="card">
          <span>负一级间距 Δx₂</span>
          <b>{{ result.deltaX2 ?? '—' }}</b>
          <small>cm</small>
        </article>
        <article class="card">
          <span>平均间距</span>
          <b>{{ result.avgDeltaX ?? '—' }}</b>
          <small>cm</small>
        </article>
      </div>
      <div class="visual-grid">
        <article v-if="result.annotatedImage" class="card visual">
          <h3>峰值与刻度标注</h3>
          <img :src="result.annotatedImage" alt="分析标注图" />
        </article>
        <article v-if="result.intensityProfile" class="card visual">
          <h3>连续光强剖面</h3>
          <img :src="result.intensityProfile" alt="光强剖面" />
        </article>
      </div>
    </section>
  </div>
</template>
