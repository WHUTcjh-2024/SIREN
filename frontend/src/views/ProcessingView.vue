<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { api } from '../api/client'
import { useExperiment } from '../composables/useExperiment'

const { state } = useExperiment()
const form = reactive({ f: 50, delta_X_cm: state.measurement?.avgDeltaX || 1, H0: state.measurement?.H0 || 20, h: 5, L: 100, rho: 1000, sigma0: 0.072 })
const result = ref<Record<string, number | null>>()
const fit = ref<Record<string, any>>()
const error = ref('')
const rows = computed(() => state.calculations)

async function calculate() {
  error.value = ''
  try {
    const response = await api<{ data: Record<string, number> }>('/api/calculate', { method: 'POST', body: JSON.stringify(form) })
    result.value = response.data
    state.calculations.push({ f: form.f, k: response.data.k, sigma: response.data.sigma })
    state.progress = Math.max(state.progress, 80)
  } catch (reason) { error.value = reason instanceof Error ? reason.message : '计算失败' }
}
async function runFit() {
  error.value = ''
  try {
    const response = await api<{ data: Record<string, any> }>('/api/fit', {
      method: 'POST', body: JSON.stringify({ experiment_data: rows.value.map(({ f, k }) => ({ f, k })), rho: form.rho, sigma0: form.sigma0 })
    })
    fit.value = response.data
    state.progress = 100
  } catch (reason) { error.value = reason instanceof Error ? reason.message : '拟合失败' }
}
function remove(index: number) { state.calculations.splice(index, 1) }
</script>

<template>
  <div class="app-body app-body--process"><div class="app-content"><div class="page processing-page vue-migrated-page">
    <!-- Page Header -->
    <section class="page-intro">
      <div>
        <span class="eyebrow">Data Processing</span>
        <h2>数据处理与计算</h2>
        <p>表面张力系数计算 · 多组实验数据拟合分析</p>
      </div>
    </section>

    <!-- Formula Showcase -->
    <section class="card original-panel formula-showcase">
      <div class="panel-heading">
        <span class="panel-icon"><i class="fa fa-superscript" /></span>
        <div>
          <h3>核心计算公式</h3>
          <p>以下公式为表面张力计算的理论基础</p>
        </div>
      </div>
      <div class="formula-grid">
        <article>
          <b><i>1</i> Kelvin 公式</b>
          <div>σ = ρ ω² / k³</div>
          <p>ρ 液体密度，ω = 2πf 角频率，k 波数</p>
        </article>
        <article>
          <b><i>2</i> 衍射角度</b>
          <div>α = arctan(H/L)，β = arctan((Δx+H)/L)</div>
          <p>H = H₀-h，δ = β-α</p>
        </article>
        <article>
          <b><i>3</i> 波数计算</b>
          <div>k = 2π/λ₀ · sin(δ/2) · [sin(α+δ/2)+sin(α-δ/2)]</div>
          <p>λ₀ = 632.8 nm 氦氖激光波长</p>
        </article>
        <article>
          <b><i>4</i> 相对误差</b>
          <div>E = |σ-σ₀| / σ₀ × 100%</div>
          <p>σ 实验值，σ₀ 标准值</p>
        </article>
      </div>
    </section>

    <!-- Surface Tension Calculation -->
    <section class="card original-panel form-card">
      <div class="panel-heading">
        <span class="panel-icon"><i class="fa fa-calculator" /></span>
        <div>
          <h3>表面张力系数计算</h3>
          <p>填入单组实验测量参数，计算表面张力系数 σ</p>
        </div>
        <span v-if="state.measurement" class="status-dot">已导入采集结果</span>
      </div>
      <div class="form-grid">
        <label>激励频率 f <span><input v-model.number="form.f" type="number" min="0" /> Hz</span></label>
        <label>条纹间距 Δx <span><input v-model.number="form.delta_X_cm" type="number" min="0" step="0.0001" /> cm</span></label>
        <label>中央峰位置 H₀ <span><input v-model.number="form.H0" type="number" step="0.0001" /> cm</span></label>
        <label>液面基准 h <span><input v-model.number="form.h" type="number" step="0.01" /> cm</span></label>
        <label>屏距 L <span><input v-model.number="form.L" type="number" min="0" /> cm</span></label>
        <label>密度 ρ <span><input v-model.number="form.rho" type="number" min="0" /> kg/m³</span></label>
        <label>参考表面张力 σ₀ <span><input v-model.number="form.sigma0" type="number" min="0" step="0.001" /> N/m</span></label>
      </div>
      <div class="center-action">
        <button class="primary" @click="calculate">
          <i class="fa fa-calculator" /> 计算表面张力
        </button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <div v-if="result" class="measurement-grid calculation-results">
        <article class="card">
          <span>角度 δ</span>
          <b>{{ result.delta }}</b>
        </article>
        <article class="card">
          <span>波数 k</span>
          <b>{{ result.k }}</b>
          <small>m⁻¹</small>
        </article>
        <article class="card">
          <span>表面张力 σ</span>
          <b>{{ result.sigma }}</b>
          <small>N/m</small>
        </article>
        <article class="card">
          <span>相对误差</span>
          <b>{{ result.relative_error ?? '—' }}</b>
          <small>%</small>
        </article>
      </div>
    </section>

    <!-- Data Fitting -->
    <section class="card original-panel data-card">
      <div class="panel-heading">
        <span class="panel-icon amber-bg"><i class="fa fa-line-chart" /></span>
        <div>
          <h3>实验数据拟合</h3>
          <p>输入多组 (k, f) 数据，拟合得到表面张力系数 σ</p>
        </div>
        <button class="primary panel-button" :disabled="rows.length < 2" @click="runFit">
          拟合数据
        </button>
      </div>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>频率 f</th>
            <th>波数 k</th>
            <th>表面张力 σ</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in rows" :key="index">
            <td>{{ index + 1 }}</td>
            <td>{{ row.f }}</td>
            <td>{{ row.k }}</td>
            <td>{{ row.sigma }}</td>
            <td>
              <button class="text-button" @click="remove(index)">删除</button>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td colspan="5" class="empty">完成至少两组计算后可进行拟合</td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- Fit Results -->
    <section v-if="fit" class="fit-grid">
      <article class="card visual">
        <h3>色散关系拟合</h3>
        <img :src="`data:image/png;base64,${fit.img_base64}`" alt="拟合图" />
      </article>
      <article class="card fit-summary">
        <span class="eyebrow">Fit Result</span>
        <h3>拟合结果</h3>
        <div>
          <span>指数</span>
          <b>{{ fit.slope }}</b>
        </div>
        <div>
          <span>R²</span>
          <b>{{ fit.r_squared }}</b>
        </div>
        <div>
          <span>拟合 σ</span>
          <b>{{ fit.sigma_fit }} N/m</b>
        </div>
      </article>
    </section>
  </div></div></div>
</template>
