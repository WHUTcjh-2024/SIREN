<script setup lang="ts">
import { computed } from 'vue'
import { RouterView } from 'vue-router'
import { useRoute } from 'vue-router'
import AppShell from './components/AppShell.vue'

const route = useRoute()
const isTeacherLayout = computed(() => route.meta.layout === 'teacher')
</script>

<template>
  <RouterView v-if="isTeacherLayout" />
  <AppShell v-else>
    <RouterView />
  </AppShell>
</template>
