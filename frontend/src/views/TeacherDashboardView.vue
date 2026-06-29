<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

type ClassKey = 'all' | 'class1' | 'class2'
type ExperimentKey = 'surface' | 'diffraction'

const selectedClass = ref<ClassKey>('all')
const selectedExperiment = ref<ExperimentKey>('surface')
const isLive = ref(true)
const now = ref(new Date())
const activeStudents = ref(37)
const aiRate = ref(8.6)
const conversationDelta = ref(0)
const pulse = ref([26, 31, 28, 38, 44, 40, 52, 47, 58, 62, 55, 66, 61, 70])
const questionCursor = ref(0)
const eventCursor = ref(0)
const updateVersion = ref(0)

const classFactor = computed(() => selectedClass.value === 'class1' ? 1.04 : selectedClass.value === 'class2' ? .94 : 1)
const eligible = computed(() => selectedClass.value === 'all' ? 86 : 43)
const completion = computed(() => Math.min(97, Math.round(88 * classFactor.value)))
const accuracy = computed(() => Math.min(95, Math.round((selectedExperiment.value === 'surface' ? 76 : 71) * classFactor.value)))
const conversations = computed(() => Math.round(184 * eligible.value / 86) + conversationDelta.value)
const focusStudents = computed(() => selectedClass.value === 'all' ? 11 : selectedClass.value === 'class2' ? 7 : 4)
const readiness = computed(() => Math.round(completion.value * .48 + accuracy.value * .42 + activeStudents.value / eligible.value * 10))
const pulseMax = computed(() => Math.max(...pulse.value, 1))
const clock = computed(() => now.value.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }))

const misconceptions = computed(() => selectedExperiment.value === 'surface' ? [
  { name: '衍射角与条纹间距', questions: 31, wrong: 42, detail: '角度变化与条纹疏密关系混淆' },
  { name: 'Kelvin 公式参数含义', questions: 24, wrong: 35, detail: '波长 λ、波数 k 的换算不熟练' },
  { name: '有效数字与误差传递', questions: 18, wrong: 28, detail: '结果保留位数与不确定度不一致' },
] : [
  { name: '光栅方程适用条件', questions: 28, wrong: 39, detail: '主极大条件与单缝衍射混淆' },
  { name: '级次与衍射角关系', questions: 23, wrong: 34, detail: '忽略可观察最高级次约束' },
  { name: '测量不确定度合成', questions: 16, wrong: 26, detail: 'A、B 类不确定度混淆' },
])

const questionPool = [
  { text: '为什么衍射角变大以后，屏幕上的条纹反而更疏了？', tag: '概念理解', className: '物理 2402' },
  { text: '波数 k 是直接用 2π/λ 吗？单位需要换成米吗？', tag: '公式应用', className: '物理 2401' },
  { text: '拟合曲线很平滑，就能说明实验结果一定准确吗？', tag: '结果判读', className: '物理 2402' },
  { text: '相对误差和不确定度在实验报告里应该分别怎么写？', tag: '误差分析', className: '物理 2401' },
]
const liveQuestions = computed(() => Array.from({ length: 3 }, (_, index) => questionPool[(questionCursor.value + index) % questionPool.length]))
const eventPool = [
  '物理 2402 新增 1 次概念提问，AI 已归入“衍射角关系”疑惑簇',
  '物理 2401 提交预习测验，班级正确率更新为 76%',
  '智慧星完成一次追问式辅导，学生随后修正了错误答案',
  'AI 发现 2 条相似提问，已合并更新课堂讲解建议',
]
const latestEvent = computed(() => eventPool[eventCursor.value])

function toggleLive() {
  isLive.value = !isLive.value
}

function updateLiveData() {
  now.value = new Date()
  const next = Math.max(24, Math.min(78, pulse.value.at(-1)! + Math.round(Math.random() * 13 - 6)))
  pulse.value = [...pulse.value.slice(1), next]
  const direction = Math.random() > .48 ? 1 : -1
  activeStudents.value = Math.max(21, Math.min(eligible.value, activeStudents.value + direction))
  aiRate.value = Math.max(4.5, Math.min(15, +(aiRate.value + Math.random() * 2 - .9).toFixed(1)))
  conversationDelta.value += 1
  questionCursor.value = (questionCursor.value + 1) % questionPool.length
  eventCursor.value = (eventCursor.value + 1) % eventPool.length
  updateVersion.value += 1
}

let timer: number | undefined
onMounted(() => {
  timer = window.setInterval(() => {
    if (isLive.value) updateLiveData()
  }, 2800)
})
onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <div class="cockpit">
    <header class="cockpit-header">
      <div class="product-brand">
        <div class="brand-symbol"><span>S</span><i></i></div>
        <div><h1>AI 物理实验教学驾驶舱</h1><p>SIREN · 智慧星学情分析中心</p></div>
      </div>

      <div class="scope-controls">
        <label><span>教学班</span><select v-model="selectedClass"><option value="all">全部班级</option><option value="class1">物理 2401</option><option value="class2">物理 2402</option></select></label>
        <label class="experiment-select"><span>当前实验</span><select v-model="selectedExperiment"><option value="surface">液体表面张力系数测量</option><option value="diffraction">光栅衍射实验</option></select></label>
      </div>

      <div class="header-status">
        <button class="live-switch" :class="{ paused: !isLive }" @click="toggleLive"><i></i>{{ isLive ? '实时分析中' : '已暂停' }}</button>
        <div class="clock"><strong>{{ clock }}</strong><span>模拟实时数据</span></div>
        <div class="teacher-avatar">王</div>
      </div>
    </header>

    <main class="cockpit-main">
      <section class="live-event-bar" :class="{ paused: !isLive }">
        <strong><i></i>实时教学事件</strong>
        <transition name="ticker" mode="out-in"><p :key="eventCursor">{{ latestEvent }}</p></transition>
        <span>{{ clock }} · AI 诊断已同步</span>
      </section>

      <section class="kpi-strip" aria-label="核心教学指标">
        <article><span class="kpi-icon blue">◉</span><div><p>课堂准备度</p><strong :key="readiness" class="changing-value">{{ readiness }}<small>/100</small></strong></div><em class="up">较上周 +5</em></article>
        <article><span class="kpi-icon green">✓</span><div><p>预习完成率</p><strong>{{ completion }}<small>%</small></strong></div><em>{{ eligible }} 人应完成</em></article>
        <article><span class="kpi-icon violet">◇</span><div><p>测验正确率</p><strong>{{ accuracy }}<small>%</small></strong></div><em class="warn">低于目标 {{ Math.max(0, 80 - accuracy) }}%</em></article>
        <article><span class="kpi-icon orange">✦</span><div><p>AI 有效对话</p><strong :key="conversations" class="changing-value">{{ conversations }}<small>条</small></strong></div><em class="live-rate">● {{ aiRate.toFixed(1) }} 次/分钟</em></article>
        <article class="attention-kpi"><span class="kpi-icon red">!</span><div><p>需教师关注</p><strong>{{ focusStudents }}<small>人</small></strong></div><em>已形成干预建议</em></article>
      </section>

      <section class="cockpit-grid">
        <article class="cockpit-panel fusion-panel">
          <header class="panel-header"><div><span class="section-code">AI 综合研判</span><h2>测验 + 对话融合诊断</h2></div><span class="confidence">可信度 92%</span></header>

          <div class="ai-conclusion">
            <span class="ai-badge">AI</span>
            <div><p>本节课最需要解决的问题</p><h3>学生会计算，但没有真正理解<br><em>“衍射角—条纹间距—波数”</em>之间的物理联系</h3></div>
          </div>

          <div class="evidence-row">
            <div><span>测验行为证据</span><strong>{{ eligible * 5 }}</strong><small>次答题记录</small></div>
            <i>+</i>
            <div><span>对话语义证据</span><strong :key="conversations" class="changing-value">{{ conversations }}</strong><small>条有效问答</small></div>
            <i>→</i>
            <div class="result-evidence"><span>AI 归纳结果</span><strong>3</strong><small>个核心疑惑</small></div>
          </div>

          <div class="ranking-title"><h3>高频疑惑与测验错误交叉验证</h3><span>提问次数 / 相关题错误率</span></div>
          <div class="misconception-ranking">
            <div v-for="(item, index) in misconceptions" :key="item.name" class="rank-row">
              <b>{{ index + 1 }}</b>
              <div class="rank-copy"><strong>{{ item.name }}</strong><span>{{ item.detail }}</span><div class="rank-bar"><i :style="{ width: `${item.wrong * 2}%` }"></i></div></div>
              <div class="rank-values"><strong>{{ item.questions }}<small> 次提问</small></strong><span>{{ item.wrong }}% 错误率</span></div>
            </div>
          </div>

          <div class="pulse-block">
            <div class="pulse-heading"><div><h3>实时学习脉冲</h3><span>近 35 分钟有效学习事件</span></div><strong :key="activeStudents" class="changing-value"><i></i>{{ activeStudents }} 人在线</strong></div>
            <div class="pulse-chart"><span class="scan-line"></span><i v-for="(value, index) in pulse" :key="index === pulse.length - 1 ? `live-${updateVersion}` : `bar-${index}`" :class="{ latest: index === pulse.length - 1 }" :style="{ height: `${Math.max(15, value / pulseMax * 100)}%` }"></i></div>
            <div class="pulse-axis"><span>-35 分钟</span><span>-20 分钟</span><span>-10 分钟</span><span>现在</span></div>
          </div>
        </article>

        <article class="cockpit-panel matrix-panel">
          <header class="panel-header"><div><span class="section-code">班级知识画像</span><h2>核心概念掌握矩阵</h2></div><span class="matrix-note">班级 × 核心概念</span></header>
          <div class="readiness-summary">
            <div class="readiness-ring" :style="{ '--progress': `${readiness * 3.6}deg` }"><div><strong>{{ readiness }}</strong><span>课堂准备度</span></div></div>
            <div><strong>{{ readiness >= 80 ? '具备开课条件' : '建议先行干预' }}</strong><p>建议用 5 分钟概念辨析后进入实验操作。</p></div>
          </div>
          <div class="matrix">
            <div class="matrix-head"></div><div class="matrix-head">角度关系</div><div class="matrix-head">Kelvin</div><div class="matrix-head">误差</div><div class="matrix-head">拟合</div>
            <div class="matrix-label">2401<small>43人</small></div><div class="cell c2">68%</div><div class="cell c3">76%</div><div class="cell c3">79%</div><div class="cell c4">86%</div>
            <div class="matrix-label">2402<small>43人</small></div><div class="cell c1">57%<small>重点</small></div><div class="cell c2">69%</div><div class="cell c3">74%</div><div class="cell c4">81%</div>
          </div>
          <footer><span>低掌握</span><i class="c1"></i><i class="c2"></i><i class="c3"></i><i class="c4"></i><span>高掌握</span></footer>
        </article>

        <article class="cockpit-panel voice-panel">
          <header class="panel-header"><div><span class="section-code">实时语义聚合</span><h2>学生此刻在问</h2></div><span class="streaming"><i></i>持续更新</span></header>
          <transition-group name="question" tag="div" class="question-list">
            <div v-for="(question, index) in liveQuestions" :key="question.text" class="question-item">
              <span>{{ index + 1 }}</span><div><p>“{{ question.text }}”</p><small>{{ question.className }} · {{ question.tag }}</small></div>
            </div>
          </transition-group>
        </article>

        <article class="cockpit-panel action-panel">
          <header class="panel-header inverse"><div><span class="section-code">AI 教学智能体</span><h2>课堂行动方案</h2></div><span class="generated">随学情更新</span></header>

          <div class="action-focus"><span>本节课教学目标</span><h3>让学生从“会套公式”<br>走向“能解释物理图像”</h3><p>依据测验错误与智慧星对话的联合分析自动生成。</p></div>

          <ol class="action-steps">
            <li><span>01<small>5 min</small></span><div><strong>动态光路概念辨析</strong><p>对比衍射角变化前后的条纹位置，让学生先预测再观察。</p><em>覆盖 31 次重复疑惑</em></div></li>
            <li><span>02<small>3 min</small></span><div><strong>公式中的物理量连线</strong><p>将 λ、k、θ 与实验装置上的可测量量逐一对应。</p><em>关联错题 Q2、Q4</em></div></li>
            <li><span>03<small>8 min</small></span><div><strong>分层实验追问</strong><p>对 {{ focusStudents }} 名重点学生使用解释型追问，不直接给出答案。</p><em>AI 已生成追问脚本</em></div></li>
          </ol>

          <div class="teacher-prompt"><span>建议教师追问</span><p>“如果只改变激光波长，你预测条纹间距如何变化？为什么？”</p></div>
          <button class="generate-button">✦ 生成课堂讲解卡</button>
          <footer>AI 提供证据与建议，最终教学判断由教师完成</footer>
        </article>
      </section>
    </main>
  </div>
</template>

<style scoped>
:global(*){box-sizing:border-box}:global(html),:global(body),:global(#app){width:100%;height:100%;margin:0;overflow:hidden}:global(body){font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif;background:#07101f;color:#e8eefc}.cockpit{width:100vw;height:100vh;overflow:hidden;background:radial-gradient(circle at 50% -20%,#17305d 0,#0a1529 42%,#07101f 100%);display:flex;flex-direction:column}.cockpit-header{height:76px;flex:none;padding:0 28px;display:grid;grid-template-columns:minmax(300px,1fr) auto minmax(300px,1fr);align-items:center;border-bottom:1px solid #ffffff12;background:#081326dc;backdrop-filter:blur(16px)}.product-brand{display:flex;align-items:center;gap:13px}.brand-symbol{width:42px;height:42px;border-radius:13px;display:grid;place-items:center;background:linear-gradient(145deg,#4f87ff,#2553d5);font-size:20px;font-weight:800;position:relative;box-shadow:0 0 25px #3972ff44}.brand-symbol i{position:absolute;width:7px;height:7px;background:#4ce6b3;border:2px solid #17346c;border-radius:50%;right:-1px;top:-1px}.product-brand h1{font-size:21px;margin:0;letter-spacing:.3px}.product-brand p{font-size:11px;color:#7890b8;margin:4px 0 0}.scope-controls{display:flex;gap:10px}.scope-controls label{height:46px;min-width:130px;border:1px solid #ffffff14;background:#ffffff08;border-radius:10px;padding:6px 10px}.scope-controls label.experiment-select{min-width:230px}.scope-controls label>span{display:block;color:#6f86ad;font-size:9px}.scope-controls select{width:100%;border:0;background:transparent;color:#e5ecfa;font-size:12px;font-weight:600;outline:0;margin-top:3px}.scope-controls option{color:#172033}.header-status{display:flex;justify-content:flex-end;align-items:center;gap:14px}.live-switch{height:32px;border:1px solid #2b7e68;background:#0f392f;color:#62e1b7;border-radius:18px;padding:0 12px;font-size:11px}.live-switch i,.streaming i,.pulse-heading strong i{display:inline-block;width:6px;height:6px;background:#4ce6b3;border-radius:50%;margin-right:6px;animation:signal 1.5s infinite}.live-switch.paused{border-color:#526079;background:#202b3d;color:#9ba8bc}.live-switch.paused i{background:#8d98aa;animation:none}.clock{text-align:right}.clock strong,.clock span{display:block}.clock strong{font:600 14px ui-monospace,Consolas,monospace;letter-spacing:.5px}.clock span{color:#667a9d;font-size:9px;margin-top:2px}.teacher-avatar{width:34px;height:34px;border-radius:10px;background:#263a62;color:#8cb0ff;display:grid;place-items:center;font-weight:700}.cockpit-main{height:calc(100vh - 76px);padding:16px 20px 18px;display:flex;flex-direction:column;gap:13px;min-height:0}.kpi-strip{height:88px;flex:none;display:grid;grid-template-columns:repeat(5,1fr);gap:11px}.kpi-strip article{display:grid;grid-template-columns:40px 1fr auto;align-items:center;gap:11px;padding:12px 15px;border:1px solid #ffffff12;background:linear-gradient(135deg,#14223bda,#0e1b31da);border-radius:12px;box-shadow:inset 0 1px #ffffff08}.kpi-icon{width:38px;height:38px;border-radius:10px;display:grid;place-items:center;font-size:17px}.kpi-icon.blue{color:#71a0ff;background:#2f68e326}.kpi-icon.green{color:#5edfb3;background:#2aae8124}.kpi-icon.violet{color:#b291ff;background:#8057dd24}.kpi-icon.orange{color:#ffc072;background:#e98a2d22}.kpi-icon.red{color:#ff857d;background:#e6595026}.kpi-strip p{color:#8fa0bd;font-size:11px;margin:0 0 2px}.kpi-strip strong{font-size:26px;line-height:1}.kpi-strip strong small{font-size:11px;color:#7285a5;margin-left:2px}.kpi-strip em{font-style:normal;color:#7e90ad;font-size:9px;text-align:right}.kpi-strip em.up{color:#55d7ad}.kpi-strip em.warn{color:#ffb65f}.kpi-strip em.live-rate{color:#ffc16f}.kpi-strip .attention-kpi{border-color:#d65a553f;background:linear-gradient(135deg,#2c1b29,#111a2c)}.cockpit-grid{flex:1;min-height:0;display:grid;grid-template-columns:1.25fr .92fr .9fr;grid-template-rows:1.08fr .82fr;grid-template-areas:"fusion matrix action" "fusion voice action";gap:13px}.cockpit-panel{min-width:0;min-height:0;overflow:hidden;border:1px solid #ffffff12;background:linear-gradient(145deg,#111e35eb,#0b172beb);border-radius:14px;padding:17px 19px;box-shadow:inset 0 1px #ffffff08,0 12px 30px #00000018}.fusion-panel{grid-area:fusion;display:flex;flex-direction:column}.matrix-panel{grid-area:matrix}.voice-panel{grid-area:voice}.action-panel{grid-area:action;background:linear-gradient(155deg,#152d5b,#151d3d 58%,#221b42);border-color:#557cce55}.panel-header{display:flex;justify-content:space-between;align-items:flex-start;flex:none}.section-code{font-size:9px;color:#4f89ff;letter-spacing:1.2px;font-weight:700}.panel-header h2{font-size:17px;margin:3px 0 0}.confidence,.matrix-note,.generated{font-size:9px;border:1px solid #ffffff13;background:#ffffff08;border-radius:10px;color:#8ea2c3;padding:4px 8px}.confidence{color:#68dcb7;border-color:#39a68144}.ai-conclusion{display:flex;gap:13px;margin-top:13px;padding:13px 15px;border:1px solid #4374dd42;background:linear-gradient(90deg,#1c376b6e,#13284d45);border-radius:11px}.ai-badge{width:36px;height:36px;flex:none;display:grid;place-items:center;border-radius:10px;color:white;font-weight:800;background:linear-gradient(145deg,#568bff,#2859df);box-shadow:0 0 18px #3f77ef55}.ai-conclusion p{font-size:10px;color:#85a7e9;margin:0 0 5px}.ai-conclusion h3{font-size:15px;line-height:1.5;margin:0}.ai-conclusion em{font-style:normal;color:#ffd078}.evidence-row{display:grid;grid-template-columns:1fr 18px 1fr 18px 1fr;align-items:center;margin:12px 0}.evidence-row>div{text-align:center;background:#ffffff06;border:1px solid #ffffff0b;border-radius:9px;padding:8px}.evidence-row>i{text-align:center;color:#526889;font-style:normal}.evidence-row span,.evidence-row strong,.evidence-row small{display:block}.evidence-row span{font-size:9px;color:#7f91ad}.evidence-row strong{font-size:17px;margin:2px 0}.evidence-row small{font-size:8px;color:#607390}.evidence-row .result-evidence{border-color:#8167d53d;background:#6b50bf16}.ranking-title{display:flex;align-items:end;justify-content:space-between;border-top:1px solid #ffffff0c;padding-top:10px}.ranking-title h3{font-size:12px;margin:0}.ranking-title span{font-size:8px;color:#657895}.misconception-ranking{margin-top:3px}.rank-row{display:grid;grid-template-columns:26px 1fr 83px;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #ffffff0a}.rank-row>b{width:25px;height:25px;display:grid;place-items:center;border-radius:7px;background:#ffb55e20;color:#ffbd6f;font-size:10px}.rank-copy strong,.rank-copy span{display:block}.rank-copy strong{font-size:11px}.rank-copy span{color:#70829e;font-size:8px;margin:2px 0 5px}.rank-bar{height:3px;background:#ffffff0b;border-radius:4px}.rank-bar i{display:block;height:100%;background:linear-gradient(90deg,#4d79e9,#ffae5d);border-radius:4px}.rank-values{text-align:right}.rank-values strong,.rank-values span{display:block}.rank-values strong{font-size:12px;color:#ffc277}.rank-values strong small{font-size:8px}.rank-values span{font-size:8px;color:#ff817b;margin-top:3px}.pulse-block{margin-top:auto;padding-top:10px}.pulse-heading{display:flex;justify-content:space-between;align-items:center}.pulse-heading h3{font-size:12px;margin:0}.pulse-heading span{font-size:8px;color:#677a99}.pulse-heading strong{font-size:10px;color:#64dab5}.pulse-chart{height:54px;margin-top:7px;display:flex;align-items:end;gap:5px;border-bottom:1px solid #2b3b55;background:repeating-linear-gradient(to top,transparent 0,transparent 17px,#ffffff08 18px)}.pulse-chart>i{flex:1;min-height:6px;border-radius:3px 3px 0 0;background:#4168b873;transition:height .7s}.pulse-chart>i.latest{background:#5f8cff;box-shadow:0 0 10px #4778ed88}.pulse-axis{display:flex;justify-content:space-between;color:#5d7091;font-size:7px;margin-top:4px}.readiness-summary{display:flex;gap:14px;align-items:center;margin:13px 0}.readiness-ring{--progress:280deg;width:82px;height:82px;border-radius:50%;padding:8px;background:conic-gradient(#5b87ff 0 var(--progress),#25334c var(--progress));flex:none}.readiness-ring>div{width:100%;height:100%;border-radius:50%;background:#101d33;display:grid;place-content:center;text-align:center}.readiness-ring strong{font-size:23px}.readiness-ring span{font-size:7px;color:#7789a8}.readiness-summary>div:last-child>strong{font-size:12px;color:#66dcb6}.readiness-summary p{font-size:9px;line-height:1.5;color:#7486a3;margin:4px 0 0}.matrix{display:grid;grid-template-columns:54px repeat(4,1fr);gap:5px}.matrix-head{text-align:center;font-size:8px;color:#6e819f;padding:3px}.matrix-label{font-size:10px;font-weight:700;display:grid;place-content:center}.matrix-label small{display:block;color:#60728f;font-size:7px}.cell{min-height:43px;border-radius:7px;display:grid;place-content:center;text-align:center;font-size:11px;font-weight:700}.cell small{display:block;font-size:7px}.c1{background:#673237!important;color:#ff928b}.c2{background:#58452f!important;color:#ffc474}.c3{background:#263e70!important;color:#9cbdff}.c4{background:#315fc0!important;color:#fff}.matrix-panel footer{display:flex;align-items:center;justify-content:flex-end;gap:4px;color:#617492;font-size:7px;margin-top:8px}.matrix-panel footer i{width:15px;height:6px;border-radius:2px}.question-list{margin-top:8px}.question-item{display:grid;grid-template-columns:24px 1fr;gap:8px;padding:7px 0;border-bottom:1px solid #ffffff0b}.question-item>span{width:23px;height:23px;border-radius:7px;background:#375eaf45;color:#89adff;display:grid;place-items:center;font-size:9px}.question-item p{font-size:11px;line-height:1.45;margin:0;color:#d6dfef}.question-item small{font-size:8px;color:#6d7f9c}.streaming{font-size:9px;color:#5eddb3}.question-enter-active{transition:.4s}.question-enter-from{opacity:0;transform:translateY(-8px)}.panel-header.inverse .section-code{color:#a8c2ff}.generated{color:#76e4bd}.action-focus{margin:14px 0;padding:14px 15px;border-left:3px solid #f8bd68;background:#ffffff08;border-radius:0 10px 10px 0}.action-focus>span{font-size:9px;color:#f4bd6a}.action-focus h3{font-size:18px;line-height:1.45;margin:5px 0}.action-focus p{font-size:8px;color:#8396b7;margin:0}.action-steps{list-style:none;margin:0;padding:0}.action-steps li{display:grid;grid-template-columns:42px 1fr;gap:11px;padding:11px 0;border-bottom:1px solid #ffffff12}.action-steps li>span{height:39px;border-radius:9px;background:#ffffff0c;color:#8eb0ff;display:grid;place-content:center;text-align:center;font-size:11px;font-weight:700}.action-steps li>span small{display:block;font-size:7px;color:#657ba2}.action-steps strong{font-size:12px}.action-steps p{font-size:9px;line-height:1.45;color:#91a0b9;margin:3px 0}.action-steps em{font-style:normal;font-size:8px;color:#c8b0ff;background:#7558c72c;border-radius:6px;padding:3px 5px}.teacher-prompt{margin-top:12px;padding:10px 12px;background:#f5bd6814;border:1px solid #f5bd682c;border-radius:9px}.teacher-prompt span{font-size:8px;color:#f5c475}.teacher-prompt p{font-size:11px;line-height:1.5;margin:3px 0 0}.generate-button{width:100%;height:38px;margin-top:11px;border:1px solid #7098ec;background:linear-gradient(90deg,#3968d2,#6a55c9);color:#fff;border-radius:9px;font-size:11px;font-weight:700}.action-panel>footer{text-align:center;color:#657897;font-size:8px;margin-top:8px}@keyframes signal{0%,100%{box-shadow:0 0 0 0 #4ce6b355}50%{box-shadow:0 0 0 5px #4ce6b300}}
@media(max-width:1180px){.cockpit-header{grid-template-columns:1fr auto}.scope-controls{display:none}.kpi-strip article{grid-template-columns:34px 1fr}.kpi-strip em{display:none}.cockpit-grid{grid-template-columns:1.2fr .9fr .9fr}.cockpit-panel{padding:14px}.action-focus h3{font-size:16px}}
@media(max-height:780px){.cockpit-header{height:64px}.cockpit-main{height:calc(100vh - 64px);padding:10px 16px;gap:9px}.kpi-strip{height:74px;gap:8px}.kpi-strip article{padding:8px 11px}.kpi-strip strong{font-size:22px}.cockpit-grid{gap:9px}.cockpit-panel{padding:12px 15px}.ai-conclusion{margin-top:8px;padding:9px}.evidence-row{margin:7px 0}.rank-row{padding:5px 0}.pulse-block{padding-top:5px}.pulse-chart{height:42px}.readiness-summary{margin:8px 0}.cell{min-height:36px}.action-focus{margin:8px 0;padding:9px 12px}.action-focus h3{font-size:15px}.action-steps li{padding:7px 0}.teacher-prompt{margin-top:7px;padding:7px 10px}.generate-button{height:32px;margin-top:7px}}
@media(max-width:900px){.cockpit-header{padding:0 14px}.header-status .clock{display:none}.product-brand h1{font-size:17px}.cockpit-main{padding:10px}.kpi-strip{grid-template-columns:repeat(5,minmax(150px,1fr));overflow:hidden}.cockpit-grid{grid-template-columns:1fr 1fr;grid-template-areas:"fusion action" "fusion action"}.matrix-panel,.voice-panel{display:none}}
.cockpit h1,.cockpit h2,.cockpit h3,.cockpit strong{color:#eef4ff}.product-brand h1{font-size:22px;color:#f4f7ff}.panel-header h2{font-size:18px;color:#eef4ff}.kpi-strip p{font-size:12px}.kpi-strip strong{font-size:27px;color:#f3f7ff}.ai-conclusion p{font-size:11px}.ai-conclusion h3{font-size:16px;color:#f1f5ff}.evidence-row span{font-size:10px}.evidence-row strong{font-size:19px}.ranking-title h3,.pulse-heading h3{font-size:13px;color:#eaf1ff}.rank-copy strong{font-size:12px;color:#e8eef9}.rank-copy span{font-size:9px}.question-item p{font-size:12px}.question-item small{font-size:9px}.action-focus h3{font-size:19px;color:#fff}.action-steps strong{font-size:13px;color:#f2f5ff}.action-steps p{font-size:10px}.teacher-prompt p{font-size:12px;color:#f2f5ff}
.live-event-bar{height:38px;flex:none;display:grid;grid-template-columns:128px 1fr auto;align-items:center;gap:14px;padding:0 15px;border:1px solid #2c705f;background:linear-gradient(90deg,#10382f,#122c3d 60%,#14233b);border-radius:10px;overflow:hidden}.live-event-bar>strong{font-size:13px;color:#65e2b8}.live-event-bar>strong i{display:inline-block;width:7px;height:7px;border-radius:50%;background:#4ce6b3;margin-right:8px;animation:signal 1.5s infinite}.live-event-bar p{font-size:13px;color:#dce8f7;margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.live-event-bar>span{font-size:12px;color:#7f94b2}.live-event-bar.paused{filter:saturate(.25);opacity:.75}.ticker-enter-active,.ticker-leave-active{transition:.24s}.ticker-enter-from{opacity:0;transform:translateY(12px)}.ticker-leave-to{opacity:0;transform:translateY(-12px)}.changing-value{display:inline-block;animation:valuePop .48s ease}.pulse-chart{position:relative;overflow:hidden}.scan-line{position:absolute;z-index:3;top:0;bottom:0;width:2px;background:#80a7ff;box-shadow:0 0 12px #6e9aff;animation:scan 2.8s linear infinite}.pulse-chart>i.latest{animation:barPop .48s ease}.product-brand p,.scope-controls label>span,.live-switch,.clock span,.kpi-strip strong small,.kpi-strip em,.section-code,.confidence,.matrix-note,.generated,.ai-conclusion p,.evidence-row span,.evidence-row small,.ranking-title span,.rank-row>b,.rank-copy span,.rank-values strong small,.rank-values span,.pulse-heading span,.pulse-axis,.readiness-ring span,.readiness-summary p,.matrix-head,.matrix-label small,.cell small,.matrix-panel footer,.question-item>span,.question-item small,.streaming,.action-focus>span,.action-focus p,.action-steps li>span,.action-steps li>span small,.action-steps p,.action-steps em,.teacher-prompt span,.action-panel>footer{font-size:12px}.ai-conclusion p{font-size:13px}.evidence-row strong{font-size:20px}.rank-copy strong{font-size:13px}.rank-values strong{font-size:14px}.pulse-heading strong{font-size:13px}.readiness-ring{width:96px;height:96px}.readiness-summary>div:last-child>strong{font-size:14px}.matrix-label{font-size:13px}.cell{font-size:15px;min-height:48px}.question-item>span{width:28px;height:28px}.question-item p{font-size:14px}.action-focus p{font-size:12px}.action-steps li{grid-template-columns:48px 1fr}.action-steps li>span{height:46px}.action-steps strong{font-size:14px}.action-steps p{font-size:12px}.action-steps em{display:inline-block;font-size:12px}.teacher-prompt p{font-size:13px}.generate-button{font-size:13px}.action-panel>footer{font-size:12px}@keyframes valuePop{0%{opacity:.35;transform:translateY(6px) scale(.94)}60%{color:#74f0c2;transform:translateY(-1px) scale(1.05)}100%{opacity:1;transform:none}}@keyframes scan{from{left:-3%}to{left:103%}}@keyframes barPop{0%{transform:scaleY(.25);transform-origin:bottom}100%{transform:scaleY(1);transform-origin:bottom}}
</style>
