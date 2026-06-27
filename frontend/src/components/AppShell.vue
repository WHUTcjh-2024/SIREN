<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useExperiment } from '../composables/useExperiment'

const route = useRoute()
const { state, hydrate, reset } = useExperiment()
onMounted(() => void hydrate().catch(() => undefined))
const openAssistant = () => window.dispatchEvent(new CustomEvent('siren:open-assistant'))
</script>

<template>
  <div class="app-layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <RouterLink to="/" class="brand">
        <span class="brand-mark">S</span>
        <span>
          <strong>SIREN-PINNs</strong>
          <small>高精度激光衍射测量系统</small>
        </span>
      </RouterLink>

      <nav>
        <p>实验模块</p>
        <RouterLink to="/" :class="{ 'router-link-exact-active': route.path === '/' }">
          <i class="fa fa-home" /><span>实验主页</span>
        </RouterLink>
        <RouterLink to="/laser-diffraction">
          <i class="fa fa-camera" /><span>静态图像采集</span>
        </RouterLink>
        <RouterLink to="/data-processing">
          <i class="fa fa-calculator" /><span>静态数据处理</span>
        </RouterLink>
      </nav>

      <div class="sidebar-progress">
        <div>
          <span>实验进度</span>
          <span>{{ state.progress }}%</span>
        </div>
        <div class="progress">
          <i :style="{ width: `${state.progress}%` }" />
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="workspace">
      <!-- Top Bar -->
      <header class="topbar">
        <div>
          <h1>SIREN-PINNs 智能实验系统</h1>
          <p>基于SIREN与PINNs的液体表面张力高精度测量系统</p>
        </div>
        <div class="user-chip">
          <i class="fa fa-user" />
        </div>
      </header>

      <!-- Main -->
      <main>
        <slot />
      </main>

      <!-- Footer -->
      <footer>AI 赋能物理实验 · 测量结果需结合不确定度评估</footer>
    </div>

    <!-- AI Assistant -->
    <AiAssistant />
  </div>
</template>

<script lang="ts">
import AiAssistant from './AiAssistant.vue'
export default { components: { AiAssistant } }
</script>
