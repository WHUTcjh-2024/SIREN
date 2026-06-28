<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useExperiment } from '../composables/useExperiment'

const { state } = useExperiment()
const answers = reactive({ s1: '', s2: '', s3: '', m1: [] as string[], t1: '' })
const summary = ref('')
const passed = ref(false)
function check() {
  passed.value = answers.s1 === 'B' && answers.s2 === 'A' && answers.s3 === 'B' && [...answers.m1].sort().join(',') === 'A,B,C' && answers.t1 === 'false'
  summary.value = passed.value ? '全部正确！已通过预习测验，可以进入正式实验。' : '仍有答案不正确，请结合实验原理检查后重新提交。'
  if (passed.value) { state.quizPassed = true; state.progress = Math.max(state.progress, 20) }
}
function reset() {
  answers.s1 = answers.s2 = answers.s3 = answers.t1 = ''
  answers.m1.splice(0)
  summary.value = ''
  passed.value = false
}
</script>

<template>
  <div class="app-body app-body--quiz"><div class="app-content">
    <nav class="quiz-page-breadcrumb"><RouterLink to="/"><i class="fa fa-home" /> 实验主页</RouterLink><i class="fa fa-angle-right" /><span>预习测验</span></nav>
    <div class="quiz-page-hero"><span class="home-section-tag">实验前</span><h2>预习测验</h2><p>完成下列 5 题并自检全部正确后，方可进入「图像采集」与「数据处理」。本页与实验主页、正式实验模块采用同一工作台主题。</p></div>
    <div v-if="!state.quizPassed" class="quiz-gate-banner is-visible"><i class="fa fa-exclamation-triangle" /> 请先完成测验并全部答对，再进入正式实验</div>
    <div class="preview-quiz-wrap"><div class="preview-quiz-card">
      <div class="preview-quiz-header"><div class="quiz-header-copy"><span class="quiz-book"><i class="fa fa-book" /></span><div><strong>预习测验答卷</strong><p>实验前测验 · 全部答对后进入正式实验</p></div></div><span class="preview-quiz-toggle"><i class="fa fa-chevron-down" /></span></div>
      <div class="preview-quiz-body"><form class="preview-quiz-form" @submit.prevent="check">
        <div class="preview-quiz-section"><div class="preview-quiz-section-title"><i class="fa fa-dot-circle-o" /> 单项选择题</div>
          <div class="preview-quiz-item"><p class="preview-quiz-q"><span class="preview-quiz-q-num">1.</span>同等实验环境下，99% 无水乙醇相比纯水，所需最佳振动频率（ ）</p><div class="preview-quiz-options"><label v-for="o in [['A','更低'],['B','更高'],['C','完全相同'],['D','无规律']]" :key="o[0]" class="preview-quiz-option"><input v-model="answers.s1" type="radio" :value="o[0]"> {{ o[0] }}. {{ o[1] }}</label></div></div>
          <div class="preview-quiz-item"><p class="preview-quiz-q"><span class="preview-quiz-q-num">2.</span>由光栅衍射公式可知，毛细波波长越小，衍射条纹间距（ ）</p><div class="preview-quiz-options"><label v-for="o in [['A','越大'],['B','越小'],['C','不变'],['D','先大后小']]" :key="o[0]" class="preview-quiz-option"><input v-model="answers.s2" type="radio" :value="o[0]"> {{ o[0] }}. {{ o[1] }}</label></div></div>
          <div class="preview-quiz-item"><p class="preview-quiz-q"><span class="preview-quiz-q-num">3.</span>频率过高时液面波纹过密，会出现什么现象（ ）</p><div class="preview-quiz-options"><label v-for="o in [['A','条纹清晰散开'],['B','条纹拥挤难以分辨'],['C','条纹消失'],['D','条纹反向排列']]" :key="o[0]" class="preview-quiz-option"><input v-model="answers.s3" type="radio" :value="o[0]"> {{ o[0] }}. {{ o[1] }}</label></div></div>
        </div>
        <div class="preview-quiz-section"><div class="preview-quiz-section-title"><i class="fa fa-check-square-o" /> 多项选择题</div><div class="preview-quiz-item"><p class="preview-quiz-q"><span class="preview-quiz-q-num">1.</span>下列关于衍射条纹说法正确的有（ ）</p><div class="preview-quiz-options"><label v-for="o in [['A','零级主极大亮度最高'],['B','衍射级次越高亮度越弱'],['C','条纹均匀分布代表波纹规整'],['D','条纹粘连说明频率合适']]" :key="o[0]" class="preview-quiz-option"><input v-model="answers.m1" type="checkbox" :value="o[0]"> {{ o[0] }}. {{ o[1] }}</label></div></div></div>
        <div class="preview-quiz-section"><div class="preview-quiz-section-title"><i class="fa fa-gavel" /> 判断题</div><div class="preview-quiz-item"><p class="preview-quiz-q"><span class="preview-quiz-q-num">1.</span>表面张力越大的液体，所需最佳工作振动频率普遍越高。</p><div class="preview-quiz-tf"><label><input v-model="answers.t1" type="radio" value="true"> 正确 √</label><label><input v-model="answers.t1" type="radio" value="false"> 错误 ×</label></div></div></div>
        <p class="preview-quiz-hint"><i class="fa fa-info-circle" />须独立完成作答并「提交自检」全部正确，方可进入实验系统。</p>
        <div class="preview-quiz-actions"><button type="submit" class="preview-quiz-btn preview-quiz-btn-primary"><i class="fa fa-check" /> 提交自检</button><button type="button" class="preview-quiz-btn preview-quiz-btn-secondary" @click="reset"><i class="fa fa-refresh" /> 重新作答</button></div>
        <div class="preview-quiz-summary" :class="{ 'is-visible': summary, 'is-pass': passed, 'is-fail': summary && !passed }">{{ summary }}</div>
      </form></div>
    </div></div>
    <div class="quiz-page-foot"><RouterLink to="/" class="app-btn-outline"><i class="fa fa-arrow-left" /> 返回实验主页</RouterLink><RouterLink to="/laser-diffraction" class="app-btn-primary"><i class="fa fa-arrow-right" /> 进入图像采集</RouterLink></div>
  </div></div>
</template>

<style scoped>
.quiz-page-breadcrumb{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text-muted);margin-bottom:16px}.quiz-page-breadcrumb a{color:var(--primary);font-weight:600}.quiz-page-hero{padding:22px 26px;margin-bottom:18px;background:linear-gradient(135deg,#fffbeb 0%,#fff 55%,#eff6ff 100%);border:1px solid #fde68a;border-radius:var(--radius);box-shadow:var(--shadow)}.quiz-page-hero h2{margin:8px 0 6px;font-size:20px;font-weight:800;color:#0f172a}.quiz-page-hero p{font-size:14px;color:var(--text-secondary);line-height:1.55;max-width:40em}.quiz-page-foot{display:flex;gap:10px;margin-top:18px}.quiz-header-copy{display:flex;align-items:center;gap:12px}.quiz-header-copy strong{font-size:16px}.quiz-header-copy p{font-size:12px;color:var(--text-muted);margin-top:3px}.quiz-book{width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,var(--primary),var(--accent));color:#fff;display:grid;place-items:center}
</style>
