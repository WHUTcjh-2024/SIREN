<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useExperiment } from '../composables/useExperiment'

const { state } = useExperiment()
const nextRoute = computed(() => !state.measurement ? '/laser-diffraction' : '/data-processing')
</script>

<template>
  <div class="page">
    <!-- Breadcrumb -->
    <div class="breadcrumb">
      <span>实验主页</span>
      <i class="fa fa-chevron-right" />
      <span>静态实验 · 图像采集</span>
      <i class="fa fa-chevron-right" />
      <span>静态实验 · 数据处理</span>
      <i class="fa fa-chevron-right" />
      <span>知识库</span>
    </div>

    <!-- Warning Banner -->
    <div class="warning-banner">
      <i class="fa fa-exclamation-triangle" />
      <span>实验前请确保激光器已预热至少15分钟，衍射图样清晰稳定。如有异常，请联系实验室管理员。</span>
    </div>

    <!-- Main Content Grid -->
    <div class="home-grid">
      <!-- Left Column - Main Content -->
      <div class="home-main">
        <!-- Title Card -->
        <div class="card title-card">
          <h2>基于SIREN与PINNs的液体表面张力高精度测量系统</h2>
          <ul class="feature-list">
            <li><i class="fa fa-check-circle" /> SIREN神经网络：连续可微的光场表示</li>
            <li><i class="fa fa-check-circle" /> PINNs物理约束：波动方程深度约束</li>
            <li><i class="fa fa-check-circle" /> AI实验助手：实验原理和误差分析问答</li>
          </ul>
          <div class="module-selector">
            <span class="active">1/4</span>
            <span>25%</span>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="action-buttons">
          <RouterLink :to="nextRoute" class="primary">
            <i class="fa fa-play" /> 开始实验
          </RouterLink>
          <RouterLink to="/laser-diffraction" class="secondary">
            <i class="fa fa-camera" /> 图像采集
          </RouterLink>
          <RouterLink to="/data-processing" class="secondary">
            <i class="fa fa-calculator" /> 数据处理
          </RouterLink>
          <button class="secondary">
            <i class="fa fa-book" /> 知识库
          </button>
        </div>

        <!-- Workflow Section -->
        <div class="card workflow-card">
          <div class="card-header">
            <i class="fa fa-cogs" />
            <span>精密工作流与核心方法</span>
            <RouterLink to="/laser-diffraction" class="start-btn">
              <i class="fa fa-play" /> 从头开始
            </RouterLink>
          </div>
          <div class="workflow-steps">
            <div class="step">
              <i class="fa fa-camera step-icon" />
              <span>图像采集</span>
            </div>
            <div class="step">
              <i class="fa fa-brain step-icon" />
              <span>SIREN 拟合</span>
            </div>
            <div class="step">
              <i class="fa fa-search step-icon" />
              <span>PINNs 约束</span>
            </div>
            <div class="step">
              <i class="fa fa-chart-line step-icon" />
              <span>数据分析</span>
            </div>
          </div>
          <div class="workflow-formulas">
            <div class="formula">
              <span>Kelvin 公式</span>
              <div>σ = ρ ω² / k³</div>
            </div>
            <div class="formula">
              <span>衍射角差</span>
              <div>δ = β − α</div>
            </div>
            <div class="formula">
              <span>波数计算</span>
              <div>k = (2π/λ₀)·sin(δ/2)·[...]</div>
            </div>
            <div class="formula">
              <span>相对误差</span>
              <div>E = |σ−σ₀|/σ₀ × 100%</div>
            </div>
          </div>
        </div>

        <!-- Core Knowledge -->
        <div class="card knowledge-card">
          <div class="card-header">
            <i class="fa fa-lightbulb" />
            <span>核心知识</span>
          </div>
          <div class="knowledge-grid">
            <div class="knowledge-item">
              <h4>SIREN 神经网络</h4>
              <p>使用周期激活函数的神经网络，可精确拟合连续光场分布。</p>
            </div>
            <div class="knowledge-item">
              <h4>PINNs 物理约束</h4>
              <p>将物理方程作为损失函数约束，确保结果符合波动理论。</p>
            </div>
            <div class="knowledge-item">
              <h4>亚像素定位</h4>
              <p>通过神经网络拟合实现0.01像素级别的峰值定位精度。</p>
            </div>
            <div class="knowledge-item">
              <h4>色散关系</h4>
              <p>ω = a·k^(3/2)，拟合得到表面张力系数σ。</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column - Sidebar -->
      <div class="home-sidebar">
        <!-- Experiment Progress -->
        <div class="card progress-card">
          <div class="card-header">
            <i class="fa fa-tasks" />
            <span>操作进度</span>
          </div>
          <div class="progress-list">
            <div class="progress-item" :class="{ done: state.measurement }">
              <i :class="state.measurement ? 'fa fa-check-circle' : 'fa fa-circle-o'" />
              <span>图像采集</span>
              <small>{{ state.measurement ? '已完成' : '待完成' }}</small>
            </div>
            <div class="progress-item" :class="{ done: state.calculations.length > 0 }">
              <i :class="state.calculations.length > 0 ? 'fa fa-check-circle' : 'fa fa-circle-o'" />
              <span>数据处理</span>
              <small>{{ state.calculations.length > 0 ? '已完成' : '待完成' }}</small>
            </div>
            <div class="progress-item" :class="{ done: state.progress >= 100 }">
              <i :class="state.progress >= 100 ? 'fa fa-check-circle' : 'fa fa-circle-o'" />
              <span>实验完成</span>
              <small>{{ state.progress >= 100 ? '已完成' : '待完成' }}</small>
            </div>
          </div>
          <div class="progress-bar">
            <div :style="{ width: `${state.progress}%` }" />
          </div>
        </div>

        <!-- Recent Results -->
        <div class="card results-card">
          <div class="card-header">
            <i class="fa fa-history" />
            <span>最近结果</span>
          </div>
          <div v-if="state.measurement" class="result-item">
            <span>中央峰高度 H₀</span>
            <b>{{ state.measurement.H0?.toFixed(4) ?? '—' }} cm</b>
          </div>
          <div v-if="state.measurement" class="result-item">
            <span>平均间距 Δx</span>
            <b>{{ state.measurement.avgDeltaX?.toFixed(4) ?? '—' }} cm</b>
          </div>
          <div v-if="!state.measurement" class="empty-state">
            <p>暂无测量结果</p>
          </div>
        </div>

        <!-- Quick Actions -->
        <div class="card actions-card">
          <div class="card-header">
            <i class="fa fa-bolt" />
            <span>快速操作</span>
          </div>
          <RouterLink to="/laser-diffraction" class="action-item">
            <i class="fa fa-camera" />
            <span>开始图像采集</span>
          </RouterLink>
          <RouterLink to="/data-processing" class="action-item">
            <i class="fa fa-calculator" />
            <span>数据处理计算</span>
          </RouterLink>
        </div>
      </div>
    </div>

    <!-- Mascot -->
    <div class="mascot">
      <div class="mascot-character">
        <i class="fa fa-user-graduate" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #718096;
  margin-bottom: 16px;
}
.breadcrumb i { font-size: 8px; color: #cbd5e0; }
.breadcrumb span:last-child { color: #5b5ce2; font-weight: 600; }

.warning-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #fffbeb;
  border: 1px solid #fcd34d;
  border-radius: 8px;
  font-size: 12px;
  color: #92400e;
  margin-bottom: 20px;
}
.warning-banner i { color: #f59e0b; }

.home-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 20px;
}

.home-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.home-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.title-card {
  padding: 24px;
}
.title-card h2 {
  font-size: 18px;
  font-weight: 700;
  color: #172033;
  margin: 0 0 16px;
  line-height: 1.4;
}
.feature-list {
  list-style: none;
  padding: 0;
  margin: 0 0 16px;
}
.feature-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #4a5568;
  margin-bottom: 8px;
}
.feature-list li i {
  color: #10b981;
  font-size: 14px;
}
.module-selector {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #718096;
}
.module-selector .active {
  color: #5b5ce2;
  font-weight: 700;
}

.action-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.workflow-card, .knowledge-card, .progress-card, .results-card, .actions-card {
  padding: 20px;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 14px;
  font-weight: 600;
  color: #172033;
}
.card-header i { color: #5b5ce2; }
.start-btn {
  margin-left: auto;
  font-size: 12px;
  color: #5b5ce2;
  text-decoration: none;
  font-weight: 600;
}

.workflow-steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 8px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 12px;
  color: #4a5568;
}
.step-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #5b5ce2, #7c3aed);
  color: white;
  border-radius: 10px;
  font-size: 16px;
}

.workflow-formulas {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.formula {
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 12px;
}
.formula span {
  display: block;
  color: #718096;
  margin-bottom: 6px;
  font-weight: 600;
}
.formula div {
  font-family: 'JetBrains Mono', monospace;
  color: #172033;
  font-size: 13px;
}

.knowledge-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.knowledge-item {
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
}
.knowledge-item h4 {
  font-size: 13px;
  font-weight: 700;
  color: #172033;
  margin: 0 0 8px;
}
.knowledge-item p {
  font-size: 12px;
  color: #718096;
  margin: 0;
  line-height: 1.5;
}

.progress-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}
.progress-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #4a5568;
}
.progress-item i { font-size: 16px; color: #cbd5e0; }
.progress-item.done i { color: #10b981; }
.progress-item small {
  margin-left: auto;
  font-size: 11px;
  color: #718096;
}

.progress-bar {
  height: 6px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}
.progress-bar div {
  height: 100%;
  background: linear-gradient(90deg, #5b5ce2, #18a9b8);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.result-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #e2e8f0;
  font-size: 12px;
}
.result-item span { color: #718096; }
.result-item b { color: #172033; font-weight: 600; }

.empty-state {
  text-align: center;
  padding: 20px;
  color: #a0aec0;
  font-size: 13px;
}

.action-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  text-decoration: none;
  color: #4a5568;
  font-size: 13px;
  margin-bottom: 8px;
  transition: all 0.2s;
}
.action-item:hover {
  background: #edf2f7;
  color: #5b5ce2;
}
.action-item i { color: #5b5ce2; }

.mascot {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 100;
}
.mascot-character {
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #5b5ce2, #7c3aed);
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: white;
  font-size: 24px;
  box-shadow: 0 4px 20px rgba(91, 92, 226, 0.3);
}
</style>
