<script setup lang="ts">
defineProps<{ title: string; subtitle: string }>()
</script>
<template><div class="page narrow-page"><section class="card placeholder"><i>⌁</i><span class="eyebrow">Dynamic Experiment</span><h2>{{ title }}</h2><p>{{ subtitle }}</p><b>模块接口与导航已预留</b></section></div></template>
