<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

type ClassKey = 'all' | 'class1' | 'class2'
type ExperimentKey = 'surface' | 'diffraction'
type Student = {
  id: string
  name: string
  className: string
  quiz: number
  wrong: number
  questions: number
  risk: 'high' | 'medium'
  issue: string
  lastActive: string
}

const selectedClass = ref<ClassKey>('all')
const selectedExperiment = ref<ExperimentKey>('surface')
const range = ref('近 7 天')
const toast = ref('')
const search = ref('')
const isLive = ref(true)
const now = ref(new Date())
const liveConversationDelta = ref(0)
const activeNow = ref(37)
const requestsPerMinute = ref(8.6)
const anomalyCount = ref(3)
const activitySeries = ref([28, 34, 31, 42, 39, 48, 53, 49, 58, 62, 57, 66])
const liveEvents = ref([
  { time: '刚刚', type: 'question', title: '新增概念疑惑', detail: '物理 2402 · 衍射角与条纹间距', tone: 'orange' },
  { time: '1 分钟前', type: 'quiz', title: '预习测验已提交', detail: '物理 2401 · 正确率 80%', tone: 'blue' },
  { time: '3 分钟前', type: 'risk', title: '学习风险变化', detail: '1 名学生由中风险转为低风险', tone: 'green' },
  { time: '5 分钟前', type: 'ai', title: '智慧星完成解答', detail: '有效数字与误差传递', tone: 'violet' },
])

const eventPool = [
  { type: 'question', title: '新增概念疑惑', detail: '物理 2402 · Kelvin 公式参数含义', tone: 'orange' },
  { type: 'quiz', title: '预习测验已提交', detail: '物理 2401 · 正确率 80%', tone: 'blue' },
  { type: 'ai', title: '智慧星完成解答', detail: '物理 2402 · SIREN 拟合判读', tone: 'violet' },
  { type: 'risk', title: '学习风险变化', detail: '1 名学生进入重点关注队列', tone: 'red' },
]

const classFactor = computed(() => selectedClass.value === 'class1' ? 1.04 : selectedClass.value === 'class2' ? 0.94 : 1)
const experimentFactor = computed(() => selectedExperiment.value === 'surface' ? 1 : 0.91)
const eligibleStudents = computed(() => selectedClass.value === 'all' ? 86 : 43)
const students = computed(() => Math.round((selectedClass.value === 'all' ? 86 : 43) * experimentFactor.value))
const completion = computed(() => Math.min(99, Math.round(88 * classFactor.value * experimentFactor.value)))
const accuracy = computed(() => Math.min(96, Math.round(76 * classFactor.value * experimentFactor.value)))
const conversations = computed(() => Math.round(students.value * 2.14 * (selectedExperiment.value === 'surface' ? 1 : 1.08)) + liveConversationDelta.value)
const helpNeeded = computed(() => Math.max(3, Math.round(students.value * (selectedClass.value === 'class2' ? .19 : .13))))
const readiness = computed(() => Math.round(completion.value * .48 + accuracy.value * .42 + Math.min(100, activeNow.value / Math.max(1, students.value) * 100) * .1))
const updatedAt = computed(() => now.value.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }))
const pulseMax = computed(() => Math.max(...activitySeries.value, 1))

const trend = computed(() => {
  const base = selectedExperiment.value === 'surface' ? [58, 63, 65, 69, 72, 74, 76] : [51, 56, 61, 60, 66, 68, 70]
  return base.map(value => Math.min(98, Math.round(value * classFactor.value)))
})
const linePoints = computed(() => trend.value.map((value, index) => `${28 + index * 72},${160 - (value - 45) * 3}`).join(' '))

const misconceptions = computed(() => selectedExperiment.value === 'surface' ? [
  { title: '衍射角与条纹间距的关系', count: 31, wrong: 42, tone: 'orange', note: '混淆角度增大与条纹疏密变化' },
  { title: 'Kelvin 公式参数含义', count: 24, wrong: 35, tone: 'blue', note: '对波长 λ 与波数 k 的换算不熟悉' },
  { title: '有效数字与误差传递', count: 18, wrong: 28, tone: 'violet', note: '计算结果保留位数不一致' },
  { title: 'SIREN 拟合结果判读', count: 13, wrong: 19, tone: 'green', note: '无法区分拟合误差与实验误差' },
] : [
  { title: '光栅方程适用条件', count: 28, wrong: 39, tone: 'orange', note: '将主极大条件用于单缝衍射' },
  { title: '级次与衍射角关系', count: 23, wrong: 34, tone: 'blue', note: '忽略可观察最高级次约束' },
  { title: '测量不确定度合成', count: 16, wrong: 26, tone: 'violet', note: 'A、B 类不确定度混淆' },
  { title: '数据线性化处理', count: 11, wrong: 17, tone: 'green', note: '斜率物理意义判断错误' },
])

const studentRows: Student[] = [
  { id: '20260127', name: '陈雨欣', className: '物理 2402', quiz: 48, wrong: 4, questions: 9, risk: 'high', issue: '衍射角定义、公式选择', lastActive: '10 分钟前' },
  { id: '20260053', name: '周子航', className: '物理 2401', quiz: 56, wrong: 3, questions: 7, risk: 'high', issue: '波数换算、单位处理', lastActive: '32 分钟前' },
  { id: '20260115', name: '宋嘉宁', className: '物理 2402', quiz: 64, wrong: 3, questions: 6, risk: 'medium', issue: '有效数字、误差传递', lastActive: '1 小时前' },
  { id: '20260031', name: '林浩然', className: '物理 2401', quiz: 68, wrong: 2, questions: 5, risk: 'medium', issue: '拟合曲线物理意义', lastActive: '2 小时前' },
]

const filteredStudents = computed(() => studentRows.filter(student => {
  const matchesClass = selectedClass.value === 'all' || (selectedClass.value === 'class1' ? student.className.endsWith('2401') : student.className.endsWith('2402'))
  const term = search.value.trim().toLowerCase()
  return matchesClass && (!term || `${student.name}${student.id}${student.issue}`.toLowerCase().includes(term))
}))

function notify(message: string) {
  toast.value = message
  window.setTimeout(() => { toast.value = '' }, 2400)
}

function refreshLiveData() {
  now.value = new Date()
  const next = Math.max(18, Math.min(78, activitySeries.value.at(-1)! + Math.round(Math.random() * 14 - 6)))
  activitySeries.value = [...activitySeries.value.slice(1), next]
  activeNow.value = Math.max(24, Math.min(students.value, activeNow.value + Math.round(Math.random() * 6 - 3)))
  requestsPerMinute.value = Math.max(4.2, Math.min(16, +(requestsPerMinute.value + Math.random() * 2.4 - 1.1).toFixed(1)))
  liveConversationDelta.value += Math.random() > .42 ? 1 : 0
  if (Math.random() > .48) {
    const event = eventPool[Math.floor(Math.random() * eventPool.length)]
    liveEvents.value = [{ ...event, time: '刚刚' }, ...liveEvents.value.slice(0, 3)]
  }
}

function toggleLive() {
  isLive.value = !isLive.value
  notify(isLive.value ? '实时数据流已恢复' : '实时数据流已暂停')
}

let liveTimer: number | undefined
onMounted(() => {
  liveTimer = window.setInterval(() => {
    if (isLive.value) refreshLiveData()
  }, 4000)
})
onBeforeUnmount(() => window.clearInterval(liveTimer))
</script>

<template>
  <div class="teacher-app">
    <aside class="teacher-sidebar">
      <div class="brand">
        <div class="brand-mark">S</div>
        <div><strong>SIREN 教学云</strong><span>大学物理实验</span></div>
      </div>
      <nav class="teacher-nav" aria-label="教师端导航">
        <p>教学管理</p>
        <a class="active" href="#overview"><span class="nav-icon">▦</span>数据驾驶舱</a>
        <a href="#students"><span class="nav-icon">♙</span>学生学情</a>
        <a href="#quiz"><span class="nav-icon">✓</span>测验分析</a>
        <a href="#questions"><span class="nav-icon">◌</span>疑惑洞察 <b>12</b></a>
        <p>智能教学</p>
        <a href="#brief"><span class="nav-icon">✦</span>AI 备课助手</a>
        <a href="#resources"><span class="nav-icon">▤</span>教学资源</a>
        <a href="#reports"><span class="nav-icon">↗</span>教学报告</a>
      </nav>
      <div class="privacy-note"><span>●</span><div><strong>数据已脱敏</strong><small>仅用于教学改进，不参与自动评分</small></div></div>
      <a class="back-student" href="/">← 返回学生端</a>
    </aside>

    <main class="teacher-main">
      <header class="teacher-topbar">
        <div><h1>教学数据驾驶舱</h1><p>早上好，王老师。这里是学生预习情况与疑惑摘要。</p></div>
        <div class="top-actions">
          <button class="icon-button" aria-label="通知">♢<span></span></button>
          <div class="teacher-profile"><div>王</div><p><strong>王老师</strong><span>课程负责人</span></p><i>⌄</i></div>
        </div>
      </header>

      <div class="teacher-content" id="overview">
        <section class="filters" aria-label="数据筛选">
          <label>班级<select v-model="selectedClass"><option value="all">全部班级（2）</option><option value="class1">物理 2401</option><option value="class2">物理 2402</option></select></label>
          <label>实验<select v-model="selectedExperiment"><option value="surface">液体表面张力系数测量</option><option value="diffraction">光栅衍射实验</option></select></label>
          <label>时间<select v-model="range"><option>近 7 天</option><option>本教学周</option><option>本学期</option></select></label>
          <span class="freshness"><i></i>数据更新于 09:42</span>
          <button class="export-button" @click="notify('教学数据报告已生成')">⇩ 导出报告</button>
        </section>

        <section class="hero-summary">
          <div class="hero-copy">
            <span class="eyebrow">✦ AI 学情速览</span>
            <h2>整体预习进展良好，<em>但有 2 个概念需要重点讲解</em></h2>
            <p>学生对“衍射角与条纹间距关系”的理解分歧最明显，相关题目错误率 42%，且在与智慧星的对话中被重复提问 31 次。</p>
            <div class="hero-actions"><button @click="notify('已生成 5 分钟课堂讲解提纲')">生成讲解方案</button><a href="#questions">查看完整分析 →</a></div>
          </div>
          <div class="hero-signal" aria-label="AI 综合判断">
            <div class="orb"><span>AI</span><i></i><i></i><i></i></div>
            <p><strong>建议课前干预</strong><span>可信度 92%</span></p>
          </div>
        </section>

        <section class="metric-grid">
          <article><div class="metric-head"><span class="metric-icon blue">♙</span><b class="good">较上周 +6.2%</b></div><strong>{{ students }}</strong><p>参与学生 <span>/ {{ eligibleStudents }} 人</span></p><small>覆盖本次实验的有效学习记录</small></article>
          <article><div class="metric-head"><span class="metric-icon green">✓</span><b class="good">↑ 4.1%</b></div><strong>{{ completion }}%</strong><p>预习完成率</p><div class="mini-progress"><i :style="{ width: `${completion}%` }"></i></div></article>
          <article><div class="metric-head"><span class="metric-icon violet">◎</span><b class="good">↑ 3.8%</b></div><strong>{{ accuracy }}%</strong><p>测验平均正确率</p><small>共完成 {{ students * 5 }} 道题</small></article>
          <article><div class="metric-head"><span class="metric-icon orange">✦</span><b>人均 2.1 次</b></div><strong>{{ conversations }}</strong><p>AI 有效对话</p><small>已排除问候与重复消息</small></article>
          <article class="risk-card"><div class="metric-head"><span class="metric-icon red">!</span><b>需要关注</b></div><strong>{{ helpNeeded }}</strong><p>需重点帮助学生</p><small>低正确率且高频求助</small></article>
        </section>

        <section class="dashboard-row">
          <article class="panel trend-panel" id="quiz">
            <header><div><span class="panel-kicker">学习趋势</span><h3>预习效果持续提升</h3></div><div class="legend"><span class="blue-dot"></span>平均正确率 <i></i>目标线 80%</div></header>
            <div class="chart-wrap">
              <div class="y-axis"><span>100%</span><span>80%</span><span>60%</span><span>40%</span></div>
              <svg viewBox="0 0 480 185" role="img" aria-label="近七日平均正确率折线图">
                <defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4578ff" stop-opacity=".24"/><stop offset="1" stop-color="#4578ff" stop-opacity="0"/></linearGradient></defs>
                <g class="grid"><line v-for="y in [25,73,121,169]" :key="y" x1="28" :y1="y" x2="460" :y2="y" /></g>
                <line class="target" x1="28" y1="55" x2="460" y2="55" />
                <polygon :points="`${linePoints} 460,169 28,169`" fill="url(#area)" />
                <polyline :points="linePoints" fill="none" stroke="#3567ef" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
                <circle v-for="(value, index) in trend" :key="index" :cx="28 + index * 72" :cy="160 - (value - 45) * 3" r="4" fill="white" stroke="#3567ef" stroke-width="3" />
              </svg>
              <div class="x-axis"><span>周二</span><span>周三</span><span>周四</span><span>周五</span><span>周六</span><span>周日</span><span>今天</span></div>
            </div>
            <footer><span>当前较课程目标低 <strong>{{ Math.max(0, 80 - accuracy) }} 个百分点</strong></span><span>预计实验课前可达 <strong>81%</strong></span></footer>
          </article>

          <article class="panel insight-panel" id="brief">
            <header><div><span class="panel-kicker purple">AI 教学建议</span><h3>下一节课建议这样安排</h3></div><button aria-label="更多">•••</button></header>
            <ol class="lesson-plan">
              <li><span>01</span><div><strong>5 分钟概念辨析</strong><p>用动态光路图对比“衍射角增大”与“条纹间距变化”。</p><em>覆盖 31 名学生的共同疑惑</em></div></li>
              <li><span>02</span><div><strong>3 分钟公式拆解</strong><p>回顾 Kelvin 公式中 λ、k、θ 的物理意义和单位。</p><em>关联错题 Q2、Q4</em></div></li>
              <li><span>03</span><div><strong>分组追问重点学生</strong><p>优先关注同时存在低正确率与高频求助的学生。</p><em>已识别 {{ helpNeeded }} 人</em></div></li>
            </ol>
            <button class="prepare-button" @click="notify('备课卡片已加入教学资源')">✦ 一键生成备课卡片</button>
          </article>
        </section>

        <section class="dashboard-row lower-row">
          <article class="panel misconception-panel" id="questions">
            <header><div><span class="panel-kicker orange-text">疑惑聚类</span><h3>学生最困惑的知识点</h3></div><a href="#students">查看全部 →</a></header>
            <div class="misconception-list">
              <div v-for="(item, index) in misconceptions" :key="item.title" class="misconception-item">
                <span class="rank" :class="item.tone">{{ index + 1 }}</span>
                <div class="misconception-copy"><strong>{{ item.title }}</strong><p>{{ item.note }}</p><div class="bar"><i :class="item.tone" :style="{ width: `${item.wrong * 1.8}%` }"></i></div></div>
                <div class="misconception-num"><strong>{{ item.count }}<small> 次</small></strong><span>{{ item.wrong }}% 错误率</span></div>
              </div>
            </div>
            <p class="method-note">✦ AI 基于 {{ conversations }} 条有效对话与 {{ students * 5 }} 次答题记录聚类，已自动合并相似表达。</p>
          </article>

          <article class="panel question-panel">
            <header><div><span class="panel-kicker green-text">真实声音</span><h3>学生最近在问什么</h3></div><span class="live"><i></i>实时更新</span></header>
            <div class="quote-list">
              <blockquote><p>“老师，为什么衍射角变大以后，屏幕上的条纹反而更疏了？”</p><footer><span>匿名学生 · 物理 2402</span><em>概念理解</em></footer></blockquote>
              <blockquote><p>“波数 k 是不是直接用 2π/λ？这里的单位需要换成米吗？”</p><footer><span>匿名学生 · 物理 2401</span><em>公式应用</em></footer></blockquote>
              <blockquote><p>“拟合出来的曲线很好看，是不是就说明实验结果一定准确？”</p><footer><span>匿名学生 · 物理 2402</span><em>结果判读</em></footer></blockquote>
            </div>
          </article>
        </section>

        <section class="panel student-panel" id="students">
          <header><div><span class="panel-kicker red-text">教学干预</span><h3>需要重点关注的学生</h3><p>综合预习正确率、错题分布和 AI 求助频次识别，仅作为教师参考。</p></div><label class="search">⌕<input v-model="search" placeholder="搜索学生或疑惑" /></label></header>
          <div class="table-scroll"><table><thead><tr><th>学生</th><th>班级</th><th>测验得分</th><th>错题</th><th>AI 提问</th><th>主要疑惑</th><th>风险</th><th>最近学习</th><th></th></tr></thead><tbody>
            <tr v-for="student in filteredStudents" :key="student.id"><td><span class="student-avatar">{{ student.name.slice(-1) }}</span><div><strong>{{ student.name }}</strong><small>{{ student.id }}</small></div></td><td>{{ student.className }}</td><td><strong :class="student.quiz < 60 ? 'score-low' : ''">{{ student.quiz }}</strong> / 100</td><td>{{ student.wrong }} 题</td><td>{{ student.questions }} 次</td><td><span class="issue-tag">{{ student.issue }}</span></td><td><span class="risk" :class="student.risk">{{ student.risk === 'high' ? '高' : '中' }}</span></td><td>{{ student.lastActive }}</td><td><button @click="notify(`已打开 ${student.name} 的学习档案`)">查看 →</button></td></tr>
            <tr v-if="!filteredStudents.length"><td colspan="9" class="empty">没有符合条件的学生</td></tr>
          </tbody></table></div>
        </section>

        <footer class="teacher-footer"><span>数据范围：{{ range }} · 演示数据 · 最后更新 2026-06-30 09:42</span><span>指标口径与隐私说明 · 所有 AI 结论需由教师复核</span></footer>
      </div>
    </main>
    <transition name="toast"><div v-if="toast" class="toast">✓ {{ toast }}</div></transition>
  </div>
</template>

<style scoped>
:global(*){box-sizing:border-box}:global(body){margin:0;background:#f5f7fb;color:#172033;font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif;overflow-x:hidden}.teacher-app{--blue:#3567ef;--ink:#172033;--muted:#778199;min-height:100vh;display:flex;max-width:100vw;overflow-x:hidden}.teacher-sidebar{position:fixed;inset:0 auto 0 0;width:232px;background:#101a32;color:#ced5e5;padding:26px 18px 18px;display:flex;flex-direction:column;z-index:20}.brand{display:flex;gap:12px;align-items:center;padding:0 8px 27px;border-bottom:1px solid #26314a}.brand-mark{width:38px;height:38px;border-radius:12px;background:linear-gradient(145deg,#628aff,#315bea);display:grid;place-items:center;color:white;font-size:20px;font-weight:800;box-shadow:0 8px 22px #142456}.brand strong,.brand span{display:block}.brand strong{font-size:15px;color:#fff}.brand span{font-size:11px;color:#8994ac;margin-top:3px;letter-spacing:.5px}.teacher-nav{margin-top:16px}.teacher-nav p{font-size:10px;color:#68748d;margin:20px 12px 8px;letter-spacing:1.4px}.teacher-nav a{position:relative;display:flex;align-items:center;gap:11px;height:42px;padding:0 12px;border-radius:9px;text-decoration:none;color:#9eabc3;font-size:13px;margin:3px 0}.teacher-nav a:hover{background:#192641;color:white}.teacher-nav a.active{background:linear-gradient(90deg,#315fe9,#3f73ff);color:white;box-shadow:0 8px 20px #09122a}.teacher-nav a b{margin-left:auto;background:#ff725e;color:#fff;border-radius:8px;min-width:20px;text-align:center;font-size:10px;padding:2px 5px}.nav-icon{width:18px;text-align:center;font-size:16px}.privacy-note{margin-top:auto;display:flex;gap:9px;background:#172440;border:1px solid #283650;border-radius:10px;padding:11px}.privacy-note>span{color:#49c89b;font-size:10px}.privacy-note strong,.privacy-note small{display:block}.privacy-note strong{font-size:11px;color:#d9e0ee}.privacy-note small{font-size:9px;color:#71809b;line-height:1.5;margin-top:3px}.back-student{color:#75839d;text-decoration:none;font-size:11px;margin:14px 8px 0}.teacher-main{width:calc(100% - 232px);margin-left:232px;min-width:0}.teacher-topbar{height:78px;background:white;border-bottom:1px solid #e7ebf2;display:flex;align-items:center;justify-content:space-between;padding:0 34px;position:sticky;top:0;z-index:12}.teacher-topbar h1{margin:0;font-size:19px}.teacher-topbar p{margin:5px 0 0;color:#929bae;font-size:11px}.top-actions,.teacher-profile{display:flex;align-items:center}.top-actions{gap:20px}.icon-button{width:34px;height:34px;border:1px solid #e7eaf1;background:white;border-radius:9px;position:relative;color:#58637a}.icon-button span{position:absolute;width:6px;height:6px;background:#ff5c58;border:1px solid white;border-radius:50%;top:7px;right:8px}.teacher-profile{gap:9px}.teacher-profile>div{width:35px;height:35px;border-radius:10px;background:#e6ecff;color:#315fe9;display:grid;place-items:center;font-weight:700}.teacher-profile p{margin:0}.teacher-profile strong,.teacher-profile span{display:block}.teacher-profile strong{font-size:12px}.teacher-profile span{font-size:9px;color:#97a0b3}.teacher-profile i{font-style:normal;color:#8d96a9;margin-left:5px}.teacher-content{padding:22px 28px 8px;max-width:1600px;margin:auto;min-width:0}.filters{display:flex;align-items:end;gap:12px;margin-bottom:18px;min-width:0}.filters label{font-size:10px;color:#8a94a8;min-width:0}.filters select{display:block;margin-top:6px;height:34px;border:1px solid #dfe4ed;border-radius:8px;background:#fff;color:#34405a;font-size:11px;padding:0 30px 0 11px;outline:none;max-width:100%;min-width:0}.freshness{font-size:10px;color:#98a1b3;margin-left:auto;align-self:center}.freshness i,.live i{display:inline-block;width:6px;height:6px;background:#3fc790;border-radius:50%;margin-right:6px}.export-button{height:34px;border:1px solid #dfe4ed;background:#fff;border-radius:8px;color:#46536e;padding:0 13px;font-size:11px}.hero-summary{min-height:190px;border-radius:16px;background:linear-gradient(115deg,#16264b 0%,#243a72 60%,#315bb0 100%);color:white;padding:27px 34px;display:flex;justify-content:space-between;align-items:center;overflow:hidden;position:relative;box-shadow:0 14px 30px #243c6d20}.hero-summary:after{content:"";position:absolute;width:260px;height:260px;border-radius:50%;border:1px solid #ffffff12;right:25px;top:-72px;box-shadow:0 0 0 35px #ffffff05,0 0 0 70px #ffffff04}.hero-copy{max-width:760px;min-width:0;position:relative;z-index:2}.eyebrow{display:inline-block;color:#9fb9ff;font-size:11px;background:#ffffff0e;border:1px solid #ffffff16;border-radius:12px;padding:5px 9px}.hero-copy h2{font-size:23px;line-height:1.4;margin:13px 0 8px}.hero-copy h2 em{font-style:normal;color:#ffd57c}.hero-copy p{font-size:12px;color:#c1cde3;line-height:1.8;margin:0;max-width:690px}.hero-actions{display:flex;align-items:center;gap:19px;margin-top:16px}.hero-actions button{border:0;border-radius:8px;background:#fff;color:#214ba6;height:34px;padding:0 15px;font-size:11px;font-weight:700}.hero-actions a{color:#c5d5ff;text-decoration:none;font-size:11px}.hero-signal{position:relative;z-index:2;width:170px;text-align:center}.orb{width:78px;height:78px;margin:auto;border-radius:50%;display:grid;place-items:center;background:radial-gradient(circle at 35% 30%,#9fc3ff,#477df1 45%,#284a9e);box-shadow:0 0 30px #68a0ff77;position:relative}.orb span{font-size:22px;font-weight:800}.orb i{position:absolute;inset:-10px;border:1px solid #a7c4ff45;border-radius:50%}.orb i:nth-child(2){inset:-20px}.orb i:nth-child(3){inset:-31px}.hero-signal p strong,.hero-signal p span{display:block}.hero-signal p strong{font-size:11px}.hero-signal p span{font-size:9px;color:#9db4e3;margin-top:4px}.metric-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:16px 0}.metric-grid article{background:#fff;border:1px solid #e8ebf2;border-radius:12px;padding:15px 16px;min-width:0;box-shadow:0 4px 14px #31446d08}.metric-head{display:flex;align-items:center;justify-content:space-between}.metric-head b{font-size:9px;color:#7f899d;font-weight:500}.metric-head b.good{color:#28a97a}.metric-icon{width:28px;height:28px;display:grid;place-items:center;border-radius:8px;font-weight:700}.metric-icon.blue{background:#e9efff;color:#3567ef}.metric-icon.green{background:#e4f8f0;color:#20a978}.metric-icon.violet{background:#f0eaff;color:#8057dd}.metric-icon.orange{background:#fff0df;color:#e98a2d}.metric-icon.red{background:#ffe9e7;color:#e65950}.metric-grid article>strong{display:block;font-size:25px;margin-top:11px}.metric-grid article>p{font-size:11px;margin:2px 0 0;color:#59657b}.metric-grid article>p span,.metric-grid article>small{color:#9ca5b6}.metric-grid article>small{display:block;font-size:9px;margin-top:7px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.mini-progress{height:4px;background:#edf0f5;border-radius:5px;margin-top:10px}.mini-progress i{display:block;height:100%;background:#31ba88;border-radius:5px}.risk-card{border-color:#f2d7d5!important}.dashboard-row{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(320px,.85fr);gap:14px;margin-bottom:14px}.panel{background:#fff;border:1px solid #e7ebf2;border-radius:13px;padding:20px 21px;box-shadow:0 4px 15px #34456908;min-width:0}.panel>header{display:flex;justify-content:space-between;align-items:flex-start}.panel h3{font-size:15px;margin:4px 0 0}.panel-kicker{font-size:9px;color:#3567ef;letter-spacing:.8px;font-weight:700}.panel-kicker.purple{color:#7a55d8}.orange-text{color:#e28229}.green-text{color:#20a678}.red-text{color:#db5a54}.legend{font-size:9px;color:#8993a6;display:flex;align-items:center;gap:6px}.blue-dot{width:7px;height:7px;border-radius:50%;background:#3567ef}.legend i{width:16px;border-top:1px dashed #b9c0ce;margin-left:8px}.chart-wrap{position:relative;padding-left:35px;margin-top:10px}.chart-wrap svg{display:block;width:100%;height:190px}.grid line{stroke:#edf0f5;stroke-width:1}.target{stroke:#b9c0ce;stroke-width:1;stroke-dasharray:4}.y-axis{position:absolute;left:0;top:9px;height:153px;display:flex;flex-direction:column;justify-content:space-between;font-size:8px;color:#a0a8b8}.x-axis{display:flex;justify-content:space-between;font-size:8px;color:#8993a6;padding:0 8px}.trend-panel>footer{border-top:1px solid #edf0f5;margin-top:11px;padding-top:11px;display:flex;justify-content:space-between;color:#8c96a9;font-size:9px}.trend-panel>footer strong{color:#42506a}.insight-panel header button{border:0;background:transparent;color:#8b95a8}.lesson-plan{padding:0;margin:13px 0 11px;list-style:none}.lesson-plan li{display:flex;gap:11px;padding:10px 0;border-bottom:1px solid #eff1f5}.lesson-plan li>span{font-size:10px;color:#6f50d0;background:#eeeaff;width:26px;height:26px;display:grid;place-items:center;border-radius:8px;font-weight:700}.lesson-plan li div{flex:1}.lesson-plan strong{font-size:11px}.lesson-plan p{font-size:9px;color:#747f94;line-height:1.55;margin:3px 0}.lesson-plan em{font-style:normal;font-size:8px;color:#8a63db;background:#f4f0ff;border-radius:8px;padding:3px 6px}.prepare-button{width:100%;height:34px;border:1px solid #ded6f5;color:#6743c7;background:#f7f4ff;border-radius:8px;font-size:10px;font-weight:700}.lower-row{grid-template-columns:minmax(0,1.35fr) minmax(330px,.75fr)}.panel header a{font-size:9px;color:#5273ce;text-decoration:none}.misconception-list{margin-top:9px}.misconception-item{display:flex;align-items:center;gap:11px;padding:10px 0;border-bottom:1px solid #eff1f5}.rank{width:25px;height:25px;border-radius:7px;display:grid;place-items:center;font-size:10px;font-weight:700}.rank.orange{background:#fff0df;color:#df8128}.rank.blue{background:#e8eeff;color:#3567ef}.rank.violet{background:#f0eaff;color:#7956d3}.rank.green{background:#e4f7ef;color:#20a678}.misconception-copy{flex:1}.misconception-copy strong{font-size:10px}.misconception-copy p{font-size:8px;color:#929bae;margin:3px 0 6px}.bar{height:3px;background:#f0f2f6;border-radius:4px}.bar i{display:block;height:100%;border-radius:4px}.bar i.orange{background:#ef9945}.bar i.blue{background:#527bf1}.bar i.violet{background:#8967dc}.bar i.green{background:#3eb48b}.misconception-num{text-align:right}.misconception-num strong,.misconception-num span{display:block}.misconception-num strong{font-size:13px}.misconception-num strong small{font-size:8px;color:#9099aa}.misconception-num span{font-size:8px;color:#ec796e;margin-top:3px}.method-note{font-size:8px;color:#8792a7;background:#f7f8fb;padding:8px 10px;border-radius:7px;margin:11px 0 0}.live{font-size:9px;color:#5d6a80}.quote-list{margin-top:11px}.quote-list blockquote{margin:0 0 9px;padding:11px 12px;border:1px solid #edf0f5;border-left:3px solid #6c8cf1;border-radius:8px;background:#fbfcfe}.quote-list blockquote:nth-child(2){border-left-color:#8c67df}.quote-list blockquote:nth-child(3){border-left-color:#44b68f}.quote-list p{font-size:10px;line-height:1.55;margin:0;color:#3f4b62}.quote-list footer{display:flex;justify-content:space-between;margin-top:8px}.quote-list footer span{font-size:8px;color:#929bad}.quote-list footer em{font-style:normal;font-size:8px;color:#5574c9;background:#edf2ff;padding:2px 6px;border-radius:7px}.student-panel{margin-bottom:14px;padding-bottom:10px}.student-panel>header{align-items:center}.student-panel header p{font-size:9px;color:#8e98aa;margin:4px 0 0}.search{height:32px;border:1px solid #e0e4ec;border-radius:8px;display:flex;align-items:center;padding:0 9px;color:#8b95a7}.search input{border:0;outline:0;font-size:9px;width:130px;margin-left:6px}.table-scroll{overflow:auto;margin-top:14px}table{width:100%;border-collapse:collapse;white-space:nowrap}th{text-align:left;background:#f7f8fa;color:#8b95a7;font-size:8px;font-weight:600;padding:9px 10px}td{border-bottom:1px solid #eef1f5;padding:10px;color:#536078;font-size:9px}td:first-child{display:flex;align-items:center;gap:8px}.student-avatar{width:27px;height:27px;border-radius:8px;background:#e8eeff;color:#3567ef;display:grid;place-items:center;font-weight:700}td strong,td small{display:block}td small{font-size:7px;color:#9da5b5;margin-top:2px}.score-low{color:#e65f57}.issue-tag{background:#f3f5f8;padding:4px 7px;border-radius:6px}.risk{display:inline-grid;place-items:center;width:23px;height:20px;border-radius:6px;font-weight:700}.risk.high{background:#ffe8e6;color:#e65d54}.risk.medium{background:#fff1dc;color:#d9882c}td button{border:0;background:transparent;color:#456ad0;font-size:8px}.empty{text-align:center!important;padding:24px!important}.teacher-footer{display:flex;justify-content:space-between;color:#9ba4b5;font-size:8px;padding:1px 4px 12px}.toast{position:fixed;right:26px;bottom:24px;background:#17233e;color:#fff;padding:12px 16px;border-radius:9px;font-size:11px;box-shadow:0 10px 30px #15213d44;z-index:50}.toast-enter-active,.toast-leave-active{transition:.2s}.toast-enter-from,.toast-leave-to{opacity:0;transform:translateY(8px)}
@media(max-width:1100px){.metric-grid{grid-template-columns:repeat(3,1fr)}.dashboard-row,.lower-row{grid-template-columns:1fr}.hero-signal{display:none}}@media(max-width:760px){.teacher-sidebar{display:none}.teacher-main{width:100%;max-width:100vw;margin-left:0;overflow:hidden}.teacher-topbar{padding:0 16px}.teacher-content{width:100%;padding:15px}.filters{width:100%;flex-wrap:wrap}.filters label{width:100%;flex:none}.filters select{width:calc(100vw - 30px)}.freshness{margin-left:0}.metric-grid{grid-template-columns:repeat(2,1fr)}.hero-summary{width:100%;padding:23px}.hero-copy{width:100%}.hero-copy h2,.hero-copy p{white-space:normal;overflow-wrap:anywhere;word-break:break-word}.hero-copy h2{font-size:19px}.teacher-profile p,.teacher-profile i{display:none}.student-panel{padding:15px}.student-panel>header{align-items:flex-start;gap:12px;flex-direction:column}.teacher-footer{display:block;line-height:2}}@media(max-width:480px){.metric-grid{grid-template-columns:1fr}.export-button{margin-left:0}.hero-copy h2{font-size:17px}.hero-actions{align-items:flex-start;flex-direction:column;gap:10px}.trend-panel>footer{display:block;line-height:2}}
</style>
