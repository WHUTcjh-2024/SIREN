<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useExperiment } from '../composables/useExperiment'
import AiAssistant from './AiAssistant.vue'

const route = useRoute()
const sidebarOpen = ref(false)
const { state, hydrate } = useExperiment()
const pageTitle = computed(() => String(route.meta.title || '实验主页'))
const pageSubtitle = computed(() => String(route.meta.subtitle || 'AI + 物理实验 · 预习测验 → 静态实验 → 动态实验'))
const active = (name: string) => route.name === name
const openAssistant = () => window.dispatchEvent(new CustomEvent('siren:open-assistant'))
onMounted(() => void hydrate().catch(() => undefined))
</script>

<template>
  <button type="button" class="app-sidebar-toggle" aria-label="打开菜单" @click="sidebarOpen = !sidebarOpen"><i class="fa fa-bars" /></button>
  <div class="app-layout">
    <aside class="app-sidebar" :class="{ 'is-open': sidebarOpen }" aria-label="主导航">
      <RouterLink to="/" class="app-sidebar-brand" title="基于SIREN与PINNs的液体表面张力系数AI高精度测量系统" @click="sidebarOpen = false">
        <div class="app-sidebar-brand-icon"><i class="fa fa-tint" /></div>
        <div class="app-sidebar-brand-copy">
          <h1 class="app-sidebar-title">SIREN-PINNs智能系统</h1>
          <p class="app-sidebar-meta">AI + 物理实验 · SIREN · PINNs · 衍射</p>
        </div>
      </RouterLink>

      <nav class="app-nav" aria-label="实验导航">
        <RouterLink to="/" class="app-nav-link app-nav-link--hub" :class="{ 'is-active': active('home') }" @click="sidebarOpen = false">
          <span class="app-nav-link-icon app-nav-link-icon--hub"><i class="fa fa-home" /></span>
          <span class="app-nav-link-text"><strong>实验主页</strong><small>总览 · 进度 · 实验记录</small></span>
        </RouterLink>

        <p class="app-nav-group-label"><span>实验前</span></p>
        <RouterLink to="/preview-quiz" class="app-nav-link app-nav-link--gate" :class="{ 'is-active': active('quiz') }" @click="sidebarOpen = false">
          <span class="app-nav-step app-nav-step--gate">测</span>
          <span class="app-nav-link-text"><strong>预习测验</strong><small>进入正式实验前须完成</small></span>
          <span v-if="!state.quizPassed" class="app-nav-pill">待完成</span>
        </RouterLink>

        <p class="app-nav-group-label"><span>正式实验</span></p>
        <div class="app-nav-experiment">
          <p class="app-nav-subgroup-label"><span>静态实验</span></p>
          <div class="app-nav-flow app-nav-flow--static">
            <RouterLink to="/laser-diffraction" class="app-nav-link app-nav-link--flow" :class="{ 'is-active': active('capture') }" @click="sidebarOpen = false">
              <span class="app-nav-step">1</span><span class="app-nav-link-text"><strong>静态图像采集</strong><small>衍射图 · SIREN 读条纹</small></span>
            </RouterLink>
            <RouterLink to="/data-processing" class="app-nav-link app-nav-link--flow" :class="{ 'is-active': active('processing') }" @click="sidebarOpen = false">
              <span class="app-nav-step">2</span><span class="app-nav-link-text"><strong>静态实验数据处理</strong><small>σ 计算 · 多组拟合</small></span>
            </RouterLink>
          </div>
          <p class="app-nav-subgroup-label app-nav-subgroup-label--dynamic"><span>动态实验</span></p>
          <div class="app-nav-flow app-nav-flow--dynamic">
            <RouterLink to="/dynamic-video-capture" class="app-nav-link app-nav-link--flow app-nav-link--dynamic" :class="{ 'is-active': active('dynamic-capture') }" @click="sidebarOpen = false">
              <span class="app-nav-step app-nav-step--dynamic">3</span><span class="app-nav-link-text"><strong>动态图像采集</strong><small>表面张力 σ · 变温衍射图</small></span>
            </RouterLink>
            <RouterLink to="/dynamic-data-processing" class="app-nav-link app-nav-link--flow app-nav-link--dynamic" :class="{ 'is-active': active('dynamic-processing') }" @click="sidebarOpen = false">
              <span class="app-nav-step app-nav-step--dynamic">4</span><span class="app-nav-link-text"><strong>动态数据处理</strong><small>σ–T 关系 · 拟合与对比</small></span>
            </RouterLink>
          </div>
        </div>
        <div class="app-nav-divider" />
        <a href="#" class="app-nav-link app-nav-link--assistant" @click.prevent="openAssistant">
          <span class="app-nav-link-icon"><i class="fa fa-comments" /></span><span class="app-nav-link-text"><strong>智慧星</strong><small>激励 · 陪伴 · 答疑</small></span>
        </a>
      </nav>

      <div class="app-sidebar-route" aria-hidden="true">
        <span :class="{ 'is-on': active('home') }">主页</span><i class="fa fa-angle-right" />
        <span :class="{ 'is-on': active('quiz') }">测验</span><i class="fa fa-angle-right" />
        <span :class="{ 'is-on': active('capture') }">静采</span><i class="fa fa-angle-right" />
        <span :class="{ 'is-on': active('processing') }">静处</span><i class="fa fa-angle-right" />
        <span :class="{ 'is-on': active('dynamic-capture') }">动采</span><i class="fa fa-angle-right" />
        <span :class="{ 'is-on': active('dynamic-processing') }">动处</span>
      </div>
      <div class="app-sidebar-deco"><div class="app-sidebar-deco-inner">
        <div class="app-sidebar-tech-chips"><span>SIREN</span><span>PINNs</span><span>智慧星</span></div>
        <p class="app-sidebar-deco-note">AI 读图辅助 · 人工复核留痕</p>
      </div></div>
    </aside>

    <div class="app-main" :class="{ 'app-main--home': active('home') }">
      <header class="app-topbar">
        <div class="app-topbar-greeting"><b>{{ pageTitle }}</b><span>{{ pageSubtitle }}</span></div>
        <div class="app-topbar-actions">
          <button type="button" class="app-btn-assistant" aria-label="打开智慧星" @click="openAssistant"><i class="fa fa-comments" /><span class="u-show-from-sm">智慧星</span></button>
          <div class="app-user-pill app-user-pill--workbench"><div class="app-user-avatar app-user-avatar--ai">AI</div><span class="app-user-name">AI 实验工作台</span></div>
        </div>
      </header>
      <slot />
      <footer class="app-footer">
        <span>© 2026 SIREN-PINNs智能系统</span>
        <div><RouterLink to="/">实验主页</RouterLink><RouterLink to="/preview-quiz">预习测验</RouterLink><RouterLink to="/laser-diffraction">静态采集</RouterLink><RouterLink to="/data-processing">静态处理</RouterLink><RouterLink to="/dynamic-video-capture">动态图采</RouterLink><RouterLink to="/dynamic-data-processing">动态处理</RouterLink></div>
      </footer>
    </div>
  </div>
  <AiAssistant />
</template>
