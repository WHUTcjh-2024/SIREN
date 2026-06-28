<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useExperiment } from '../composables/useExperiment'

const { state } = useExperiment()
const completed = computed(() => [state.quizPassed, !!state.measurement, state.calculations.length > 0, state.calculations.length > 1, state.progress >= 100].filter(Boolean).length)
const percent = computed(() => Math.max(state.progress, completed.value * 20))
const status = (done: boolean) => done ? '已完成' : '待完成'
const exportReport = () => window.print()
</script>

<template>
  <div class="app-body app-body--home app-body--home-fit">
    <div class="app-content">
      <div class="companion-home-strip" role="note">
        <i class="fa fa-star" aria-hidden="true" />
        <div><strong>智慧星 · 学习激励与情感陪伴</strong><span> 完成预习与实验各阶段后，将自动收到鼓励与学习建议；遇到困难或久未登录时也会主动关心你。点击右下角智慧星可查看消息。</span></div>
      </div>
      <div class="home-center">
        <section class="home-hero home-hero--fit">
          <div class="home-hero-main">
            <span class="competition-hero-tag home-hero-track-tag">AI + 物理实验 · 2026</span>
            <h2 class="home-hero-title">基于SIREN与PINNs的液体表面张力系数AI高精度测量系统</h2>
            <p class="home-hero-sub">SIREN 神经隐式场 · PINNs 物理约束 · 亚像素条纹分析</p>
            <ul class="home-hero-points competition-innovation-list">
              <li>SIREN 连续光强场亚像素寻峰</li>
              <li>PINNs 物理约束保证表面张力 σ 一致性</li>
              <li>人机协同：预习—采集—计算全流程可追溯</li>
            </ul>
            <p v-if="!state.quizPassed" class="home-hero-gate"><i class="fa fa-exclamation-circle" /> 须先完成 <RouterLink to="/preview-quiz">预习测验</RouterLink> 并全部答对</p>
            <div class="home-hero-actions">
              <RouterLink to="/laser-diffraction" class="app-btn-primary"><i class="fa fa-play" /> 开始实验</RouterLink>
              <RouterLink to="/preview-quiz" class="app-btn-outline"><i class="fa fa-edit" /> 预习测验</RouterLink>
              <RouterLink to="/data-processing" class="app-btn-outline"><i class="fa fa-calculator" /> 数据处理</RouterLink>
              <button type="button" class="app-btn-outline" @click="exportReport"><i class="fa fa-download" /> 导出</button>
            </div>
          </div>
          <div class="home-hero-aside">
            <div class="home-scene-frame">
              <img :src="'/static/img/experiment-scene.png'" alt="激光衍射实验场景" width="480" height="270" />
              <span class="home-scene-badge"><i class="fa fa-camera" /> 实验实拍</span>
            </div>
            <div class="home-hero-metrics">
              <div class="home-metric"><span class="home-metric-val">{{ completed }}/5</span><span class="home-metric-label">已完成步骤</span></div>
              <div class="home-metric"><span class="home-metric-val">{{ percent }}%</span><span class="home-metric-label">总进度</span></div>
            </div>
          </div>
        </section>

        <section class="home-workflow-full" aria-labelledby="workflow-heading">
          <header class="home-workflow-head">
            <div class="home-workflow-head-main"><div class="home-workflow-head-title-row"><span class="home-section-tag home-section-tag--flow">实验流程</span><h2 id="workflow-heading" class="home-workflow-full-title">精密工作流与核心方程</h2></div></div>
            <RouterLink to="/laser-diffraction" class="home-workflow-cta"><i class="fa fa-play" /> 进入采集</RouterLink>
          </header>
          <div class="workflow-pipeline" role="list">
            <article class="workflow-pipeline-card" role="listitem"><div class="workflow-pipeline-top"><span class="workflow-pipeline-icon is-blue"><i class="fa fa-camera" /></span><span class="workflow-pipeline-num">01</span></div><h3>图像采集</h3><p>衍射图 + 标尺，SIREN / EasyOCR</p></article>
            <div class="workflow-pipeline-link"><span class="workflow-pipeline-link-core"><i class="fa fa-long-arrow-right" /></span></div>
            <article class="workflow-pipeline-card" role="listitem"><div class="workflow-pipeline-top"><span class="workflow-pipeline-icon is-indigo"><i class="fa fa-area-chart" /></span><span class="workflow-pipeline-num">02</span></div><h3>SIREN 拟合</h3><p>连续光强场 · 亚像素寻峰</p></article>
            <div class="workflow-pipeline-link"><span class="workflow-pipeline-link-core"><i class="fa fa-long-arrow-right" /></span></div>
            <article class="workflow-pipeline-card" role="listitem"><div class="workflow-pipeline-top"><span class="workflow-pipeline-icon is-violet"><i class="fa fa-shield" /></span><span class="workflow-pipeline-num">03</span></div><h3>PINNs 约束</h3><p>色散关系与对称性</p></article>
            <div class="workflow-pipeline-link"><span class="workflow-pipeline-link-core"><i class="fa fa-long-arrow-right" /></span></div>
            <article class="workflow-pipeline-card" role="listitem"><div class="workflow-pipeline-top"><span class="workflow-pipeline-icon is-emerald"><i class="fa fa-calculator" /></span><span class="workflow-pipeline-num">04</span></div><h3>σ 计算拟合</h3><p>Kelvin 公式 · 多组验证</p></article>
          </div>
          <div class="workflow-core-equations">
            <h3 class="workflow-core-title">核心方程</h3>
            <div class="workflow-equations-grid">
              <div class="workflow-eq-item is-kelvin"><span class="workflow-eq-label">Kelvin</span><div class="formula-katex-display">σ = ρω² / k³</div></div>
              <div class="workflow-eq-item is-delta"><span class="workflow-eq-label">衍射角差</span><div class="formula-katex-display">δ = β − α</div></div>
              <div class="workflow-eq-item is-k"><span class="workflow-eq-label">波数 k</span><div class="formula-katex-display formula-katex-display--sm">k ∝ sin(δ/2) sin α</div></div>
              <div class="workflow-eq-item is-error"><span class="workflow-eq-label">相对误差</span><div class="formula-katex-display formula-katex-display--sm">E = |σ−σ₀|/σ₀ × 100%</div></div>
            </div>
          </div>
        </section>
      </div>
    </div>

    <aside class="app-rail app-rail--home">
      <div class="app-card rail-exp-card">
        <div class="app-card-head"><span>我的实验</span></div>
        <div class="rail-progress-block"><div class="rail-progress-top"><span class="rail-progress-label">实验总进度</span><strong class="rail-progress-pct">{{ percent }}%</strong></div><div class="app-progress rail-progress-bar-wrap"><div class="app-progress-bar" :style="{ width: `${percent}%` }" /></div></div>
        <div class="rail-exp-list">
          <RouterLink to="/preview-quiz" class="rail-exp-item"><div class="rail-exp-thumb is-blue"><i class="fa fa-book" /></div><div class="rail-exp-body"><h4>预习测验</h4><p>实验前 · 5 题（单选 / 多选 / 判断）</p></div><span class="app-badge" :class="state.quizPassed ? 'app-badge-green' : 'app-badge-amber'">{{ status(state.quizPassed) }}</span></RouterLink>
          <RouterLink to="/laser-diffraction" class="rail-exp-item"><div class="rail-exp-thumb is-blue"><i class="fa fa-video-camera" /></div><div class="rail-exp-body"><h4>激光衍射图像采集</h4><p>SIREN 条纹定位 · 输出 H₀、Δx</p></div><span class="app-badge" :class="state.measurement ? 'app-badge-green' : 'app-badge-amber'">{{ status(!!state.measurement) }}</span></RouterLink>
          <RouterLink to="/data-processing" class="rail-exp-item"><div class="rail-exp-thumb is-violet"><i class="fa fa-calculator" /></div><div class="rail-exp-body"><h4>表面张力计算</h4><p>σ = ρω²/k³ · 可导入采集结果</p></div><span class="app-badge" :class="state.calculations.length ? 'app-badge-green' : 'app-badge-amber'">{{ status(state.calculations.length > 0) }}</span></RouterLink>
          <RouterLink to="/data-processing" class="rail-exp-item"><div class="rail-exp-thumb is-green"><i class="fa fa-line-chart" /></div><div class="rail-exp-body"><h4>多组数据拟合</h4><p>ω = a · k³⁄² · 验证 σ</p></div><span class="app-badge" :class="state.calculations.length > 1 ? 'app-badge-green' : 'app-badge-amber'">{{ status(state.calculations.length > 1) }}</span></RouterLink>
        </div>
        <div class="rail-exp-footer"><RouterLink to="/laser-diffraction" class="app-btn-primary rail-cta-btn"><i class="fa fa-arrow-right" /> 继续实验</RouterLink></div>
      </div>
      <div class="rail-bottom-row">
        <div class="app-card"><div class="app-card-head">实验记录</div><div class="app-card-body rail-log-body"><ul class="app-rail-list"><li v-if="!completed"><span>暂无记录</span></li><li v-if="state.quizPassed"><span>预习测验已通过</span><span class="app-status-ok">完成</span></li><li v-if="state.measurement"><span>图像分析已完成</span><span class="app-status-ok">完成</span></li></ul></div></div>
        <div class="app-card"><div class="app-card-head">系统状态</div><div class="app-card-body"><ul class="app-rail-list"><li><span>分析引擎</span><span class="app-status-ok">正常</span></li><li><span>预习测验</span><span :class="state.quizPassed ? 'app-status-ok' : 'app-status-warn'">{{ state.quizPassed ? '已通过' : '未完成' }}</span></li><li><span>智慧星</span><span class="app-status-ok">激励 · 陪伴 · RAG</span></li></ul></div></div>
      </div>
    </aside>
  </div>
</template>
