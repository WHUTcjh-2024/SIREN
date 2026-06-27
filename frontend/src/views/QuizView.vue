<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useExperiment } from '../composables/useExperiment'

const router = useRouter()
const { state } = useExperiment()
const questions = [
  { q: '衍射条纹间距增大时，其他条件不变，波数 k 如何变化？', options: ['增大', '减小', '不变'], answer: 1 },
  { q: 'SIREN 使用哪一种激活函数表示连续光强场？', options: ['ReLU', 'Sigmoid', '正弦函数'], answer: 2 },
  { q: '为了降低随机误差，实验数据应如何处理？', options: ['只取一次结果', '多次测量并拟合', '删除所有偏差点'], answer: 1 },
  { q: '左右一级条纹间距差异较大时，应首先做什么？', options: ['直接取最大值', '检查光路与峰值识别', '修改理论值'], answer: 1 }
]
const current = ref(0)
const selected = ref<number[]>(Array(questions.length).fill(-1))
const submitted = ref(false)
const score = computed(() => selected.value.reduce((sum, item, index) => sum + Number(item === questions[index].answer), 0))
function finish() {
  submitted.value = true
  if (score.value === questions.length) {
    state.quizPassed = true
    state.progress = Math.max(state.progress, 20)
  }
}
</script>

<template>
  <div class="page narrow-page">
    <section class="quiz-header card"><span class="eyebrow">实验前置任务</span><h2>预习测验</h2><p>全部答对后进入正式实验。第 {{ current + 1 }} / {{ questions.length }} 题</p><div class="progress"><i :style="{ width: `${(current + 1) / questions.length * 100}%` }" /></div></section>
    <section class="quiz-card card">
      <span class="question-index">问题 {{ String(current + 1).padStart(2, '0') }}</span>
      <h3>{{ questions[current].q }}</h3>
      <label v-for="(option, index) in questions[current].options" :key="option" class="answer" :class="{ selected: selected[current] === index }">
        <input v-model="selected[current]" type="radio" :value="index" /> <i>{{ String.fromCharCode(65 + index) }}</i><span>{{ option }}</span>
      </label>
      <div class="quiz-actions"><button class="secondary" :disabled="current === 0" @click="current--">上一题</button><button v-if="current < questions.length - 1" class="primary" :disabled="selected[current] < 0" @click="current++">下一题</button><button v-else class="primary" @click="finish">提交测验</button></div>
      <div v-if="submitted" class="result-banner" :class="{ success: score === questions.length }">
        <b>{{ score === questions.length ? '全部答对，预习完成' : `答对 ${score} / ${questions.length} 题` }}</b>
        <p>{{ score === questions.length ? '实验模块已解锁。' : '请检查答案后重新提交。' }}</p>
        <button v-if="score === questions.length" class="primary" @click="router.push('/laser-diffraction')">进入图像采集 →</button>
      </div>
    </section>
  </div>
</template>
