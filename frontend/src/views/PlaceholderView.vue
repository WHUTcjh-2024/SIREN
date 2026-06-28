<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
const route = useRoute()
const icon = computed(() => String(route.meta.icon || 'fa-cogs'))
</script>
<template><div class="app-body"><div class="app-content"><div class="app-card app-module-placeholder"><div class="app-module-placeholder-icon"><i class="fa" :class="icon" /></div><h2 class="app-module-placeholder-title">{{ route.meta.title }}</h2><p class="app-module-placeholder-desc">{{ route.meta.subtitle }}</p><p class="app-module-placeholder-note">该实验模块已纳入统一工作台，正在等待实验设备接入。</p><div class="app-module-placeholder-actions"><RouterLink to="/" class="app-btn-outline"><i class="fa fa-home" /> 返回实验主页</RouterLink><RouterLink to="/laser-diffraction" class="app-btn-primary"><i class="fa fa-camera" /> 进入静态实验</RouterLink></div></div></div></div></template>
