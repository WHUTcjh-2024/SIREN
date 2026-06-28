<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api/client'
import { useRoute } from 'vue-router'

interface Message { role: 'user' | 'assistant'; content: string }
const route = useRoute()
const open = ref(false)
const input = ref('')
const sending = ref(false)
const list = ref<HTMLElement>()
const messages = ref<Message[]>([{ role: 'assistant', content: '你好，我是智慧星。可以向我询问衍射原理、实验操作或误差分析。' }])
const show = () => { open.value = true }
onMounted(() => window.addEventListener('siren:open-assistant', show))
onBeforeUnmount(() => window.removeEventListener('siren:open-assistant', show))

async function send() {
  const question = input.value.trim()
  if (!question || sending.value) return
  messages.value.push({ role: 'user', content: question })
  input.value = ''
  sending.value = true
  try {
    const result = await api<{ answer: string }>('/api/ask', { method: 'POST', body: JSON.stringify({ question, history: messages.value.slice(-12, -1) }) })
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
  <div id="ai-assistant-root">
    <div id="ai-chat-backdrop" :class="{ 'is-open': open }" @click="open = false" />
    <button v-if="route.name !== 'capture'" type="button" id="ai-mascot-btn" aria-label="打开智慧星" title="点击与智慧星交流" @click="open = true">
      <span class="ai-mascot-shadow" />
      <div class="ai-mascot-character"><img class="ai-mascot-base" :src="'/static/img/ai-mascot-graduate-transparent.png'" alt="" width="200" height="450" draggable="false" /></div>
      <img class="ai-mascot-img ai-mascot-img-fallback" :src="'/static/img/ai-mascot-graduate-transparent.png'" alt="智慧星" width="200" height="450" draggable="false" />
      <span class="ai-mascot-badge">AI</span><span class="ai-mascot-hint">点我提问</span>
    </button>
    <div id="ai-chat-panel" :class="{ 'is-open': open }" role="dialog" aria-labelledby="ai-chat-title">
      <header class="ai-chat-header">
        <img class="ai-header-mascot" :src="'/static/img/ai-mascot-graduate-transparent.png'" alt="" width="56" height="56" />
        <div class="ai-header-title"><h3 id="ai-chat-title">智慧星</h3><p><span class="ai-status-dot" />学习激励 · 情感陪伴 · 物理辅导</p></div>
        <button type="button" id="ai-close-btn" aria-label="关闭" @click="open = false"><i class="fa fa-times" /></button>
      </header>
      <div class="ai-ethics-modal">AI 用于答疑与读图辅助，不替代原始数据与公式推导；报告须注明人工复核项。</div>
      <div id="ai-chat-messages" ref="list">
        <div v-for="(message,index) in messages" :key="index" class="ai-msg" :class="message.role === 'user' ? 'ai-msg--user' : 'ai-msg--bot'">
          <span class="ai-msg-avatar"><i :class="message.role === 'user' ? 'fa fa-user' : 'fa fa-star'" /></span><div class="ai-msg-bubble">{{ message.content }}</div>
        </div>
        <div v-if="sending" class="ai-msg ai-msg--bot"><span class="ai-msg-avatar"><i class="fa fa-star" /></span><div class="ai-msg-bubble">正在思考…</div></div>
      </div>
      <footer id="ai-chat-footer"><form class="ai-input-row" @submit.prevent="send"><textarea v-model="input" rows="1" placeholder="输入实验相关问题…（Enter 发送）" @keydown.enter.exact.prevent="send" /><button type="submit" id="ai-send-btn" aria-label="发送" :disabled="sending"><i class="fa fa-paper-plane" /></button></form></footer>
    </div>
  </div>
</template>
