<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api/client'

interface Message { role: 'user' | 'assistant'; content: string }
const open = ref(false)
const input = ref('')
const sending = ref(false)
const messages = ref<Message[]>([
  { role: 'assistant', content: '你好，我是智实验星。可以向我询问衍射原理、实验操作或误差分析。' }
])
const list = ref<HTMLElement>()
const show = () => { open.value = true }
onMounted(() => window.addEventListener('siren:open-assistant', show))
onBeforeUnmount(() => window.removeEventListener('siren:open-assistant', show))

async function send() {
  const question = input.value.trim()
  if (!question || sending.value) return
  messages.value.push({ role: 'user', content: question })
  input.value = ''
  sending.value = true
  const history = messages.value.slice(-12, -1)
  try {
    const result = await api<{ answer: string }>('/api/ask', {
      method: 'POST', body: JSON.stringify({ question, history })
    })
    messages.value.push({ role: 'assistant', content: result.answer })
  } catch (error) {
    messages.value.push({ role: 'assistant', content: error instanceof Error ? error.message : '助手暂时不可用' })
  } finally {
    sending.value = false
    await nextTick()
    list.value?.scrollTo({ top: list.value.scrollHeight })
  }
}
</script>

<template>
  <button class="assistant-fab" aria-label="打开 AI 实验助手" @click="open = !open">
    <span>✦</span><b>AI 助手</b>
  </button>
  <section v-if="open" class="assistant-panel">
    <header><div><b>智实验星</b><small>RAG 实验助手</small></div><button @click="open = false">×</button></header>
    <div ref="list" class="assistant-messages">
      <p v-for="(message, index) in messages" :key="index" :class="message.role">{{ message.content }}</p>
      <p v-if="sending" class="assistant">正在思考…</p>
    </div>
    <form @submit.prevent="send"><textarea v-model="input" placeholder="输入实验问题…" @keydown.enter.exact.prevent="send" /><button :disabled="sending">发送</button></form>
  </section>
</template>
