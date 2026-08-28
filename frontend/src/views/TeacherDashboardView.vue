<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type {
  TeacherSection,
  TeachingAlert,
  TeacherWorkspace,
} from "../data/teacherWorkspace";
import { useTeacherWorkspace } from "../composables/useTeacherWorkspace";

const {
  workspace,
  source,
  transport,
  loading,
  error,
  accessRequired,
  accessCode,
  selectedClassId,
  selectedAlertId,
  savingAlertId,
  creatingDraft,
  updatingInterventionId,
  notice,
  scope,
  classOptions,
  actionableAlerts,
  activeAlert,
  displayKpis,
  peakActivity,
  refresh,
  submitAccessCode,
  saveAlert,
  createDraft,
  advanceIntervention,
} = useTeacherWorkspace();

const activeSection = ref<TeacherSection>("overview");

const navigation: Array<{ id: TeacherSection; label: string; icon: string }> = [
  { id: "overview", label: "教学工作台", icon: "▦" },
  { id: "classes", label: "班级学情", icon: "◫" },
  { id: "experiments", label: "实验过程", icon: "⌁" },
  { id: "alerts", label: "重点关注", icon: "!" },
  { id: "integrations", label: "接入中心", icon: "⊞" },
];

const sourceDescription = computed(() => {
  const profile = workspace.value?.dataProfile;
  const coverage = profile
    ? `${profile.studentCount} 名学习者、${profile.experimentRecordCount} 条实验记录、${profile.dialogueEventCount} 条学习对话`
    : "教学数据正在汇聚";
  return source.value === "live"
    ? `数据已同步 · ${coverage} · 最近更新 ${workspace.value?.updatedAt || "—"}`
    : `当前为示例教学工作区：已汇聚 ${coverage}，教师处理记录会独立持久化。`;
});
const selectedStudentCount = computed(() => {
  if (scope.value?.classItem) return scope.value.classItem.students;
  return (
    workspace.value?.classes.reduce(
      (total, item) => total + item.students,
      0,
    ) || 1
  );
});
const activeStudentRate = computed(() =>
  Math.round(
    ((displayKpis.value.activeStudents ?? 0) / selectedStudentCount.value) *
      100,
  ),
);
const highPriorityCount = computed(
  () =>
    scope.value?.alerts.filter(
      (item) => item.level === "high" && item.status !== "resolved",
    ).length || 0,
);
const teachingHealth = computed(() =>
  Math.round(
    (displayKpis.value.completionRate ?? 0) * 0.45 +
      (displayKpis.value.dataPassRate ?? 0) * 0.4 +
      activeStudentRate.value * 0.15,
  ),
);
const classAverages = computed(() => {
  const classes = workspace.value?.classes ?? [];
  const divisor = Math.max(classes.length, 1);
  return {
    completion: Math.round(
      classes.reduce((total, item) => total + item.completionRate, 0) / divisor,
    ),
    dataPass: Math.round(
      classes.reduce((total, item) => total + item.dataPassRate, 0) / divisor,
    ),
  };
});
const alertQueue = computed(() => {
  const alerts = scope.value?.alerts ?? [];
  return {
    inProgress: alerts.filter((item) => item.status === "in_progress").length,
    resolved: alerts.filter((item) => item.status === "resolved").length,
  };
});
const completedStageCount = computed(
  () =>
    workspace.value?.stages.filter((stage) => stage.state === "complete")
      .length ?? 0,
);
const activeStage = computed(() =>
  workspace.value?.stages.find((stage) => stage.state === "active"),
);
const processProgress = computed(() =>
  Math.round(
    (completedStageCount.value /
      Math.max(workspace.value?.stages.length ?? 1, 1)) *
      100,
  ),
);
const connectedIntegrationCount = computed(
  () =>
    workspace.value?.integrations.filter((item) => item.status === "connected")
      .length ?? 0,
);

function goTo(section: TeacherSection) {
  activeSection.value = section;
  notice.value = "";
}
function selectAlert(alert: TeachingAlert) {
  selectedAlertId.value = alert.id;
  activeSection.value = "alerts";
}
function createIntervention() {
  activeSection.value = "alerts";
  void createDraft();
}
function statusLabel(status: TeachingAlert["status"]) {
  return (
    { new: "待处理", in_progress: "处理中", resolved: "已归档" } as const
  )[status];
}
function integrationLabel(
  status: TeacherWorkspace["integrations"][number]["status"],
) {
  if (source.value === "demo") {
    return (
      { connected: "演示映射", ready: "待接入", pending: "待配置" } as const
    )[status];
  }
  return ({ connected: "运行中", ready: "可接入", pending: "待配置" } as const)[
    status
  ];
}
function typeLabel(type: TeachingAlert["type"]) {
  return (
    {
      concept: "概念理解",
      data: "数据质量",
      progress: "学习进度",
      device: "仪器采集",
    } as const
  )[type];
}

onMounted(() => {
  void refresh();
});
</script>

<template>
  <div class="teacher-workspace">
    <section v-if="loading" class="workspace-state" aria-live="polite">
      <i></i><strong>正在整理教学数据…</strong>
      <p>正在加载班级、实验记录与教师干预状态。</p>
    </section>
    <section v-else-if="error" class="workspace-state unavailable" role="alert">
      <span>!</span><strong>教学数据暂不可用</strong>
      <p>{{ error }}</p>
      <form
        v-if="accessRequired"
        class="teacher-access-form"
        @submit.prevent="submitAccessCode"
      >
        <label for="teacher-access-code">教师访问码</label>
        <input
          id="teacher-access-code"
          v-model="accessCode"
          type="password"
          autocomplete="current-password"
          required
        />
        <button class="button primary" type="submit">进入教师工作区</button>
      </form>
      <button v-else class="button primary" type="button" @click="refresh">
        重新连接
      </button>
    </section>
    <template v-else-if="workspace && scope">
      <aside class="workspace-sidebar" aria-label="教师端主导航">
        <div class="product-lockup">
          <div class="product-mark"><span>∿</span><i></i></div>
          <div><strong>SIREN Labs</strong><span>AI 实验教学工作台</span></div>
        </div>
        <div class="workspace-context">
          <span>当前工作区</span><strong>{{ workspace.organization }}</strong
          ><small>物理 / 光电实验教学</small>
        </div>
        <nav class="workspace-nav">
          <button
            v-for="item in navigation"
            :key="item.id"
            :class="{ active: activeSection === item.id }"
            type="button"
            @click="goTo(item.id)"
          >
            <i>{{ item.icon }}</i
            ><span>{{ item.label }}</span
            ><em v-if="item.id === 'alerts' && actionableAlerts.length">{{
              actionableAlerts.length
            }}</em>
          </button>
        </nav>
        <div class="sidebar-pilot-card">
          <span class="pilot-icon">✦</span><strong>虚实一体试点</strong>
          <p>把仿真、仪器和学习过程数据汇成一条可诊断的教学链路。</p>
          <button type="button" @click="goTo('integrations')">
            查看接入能力 →
          </button>
        </div>
        <div class="sidebar-profile">
          <div class="avatar">{{ workspace.teacherName.slice(0, 1) }}</div>
          <div>
            <strong>{{ workspace.teacherName }}</strong
            ><span>课程负责人</span>
          </div>
          <button type="button" aria-label="更多教师设置">···</button>
        </div>
      </aside>

      <main class="workspace-main">
        <header class="workspace-header">
          <div class="header-title">
            <p>{{ workspace.courseName }} <i>/</i> {{ scope.classLabel }}</p>
            <h1>
              {{ navigation.find((item) => item.id === activeSection)?.label }}
            </h1>
          </div>
          <div class="header-actions">
            <label class="class-filter"
              ><span>教学班</span
              ><select v-model="selectedClassId" aria-label="筛选教学班">
                <option
                  v-for="option in classOptions"
                  :key="option.id"
                  :value="option.id"
                >
                  {{ option.name }}
                </option>
              </select></label
            ><button
              class="button secondary"
              type="button"
              @click="goTo('integrations')"
            >
              接入数据</button
            ><button
              class="button primary"
              type="button"
              :disabled="creatingDraft"
              @click="createIntervention"
            >
              {{ creatingDraft ? "正在创建…" : "+ 创建干预草稿" }}
            </button>
          </div>
        </header>
        <section class="source-banner" :class="{ live: source === 'live' }">
          <span class="source-dot"></span
          ><strong>{{
            source === "live" ? "真实教学数据" : "演示数据工作区"
          }}</strong>
          <p>{{ sourceDescription }}</p>
          <small v-if="transport === 'fixture'"
            >离线模式：处理操作不会写入服务端。</small
          ><button
            v-if="source === 'demo'"
            type="button"
            @click="goTo('integrations')"
          >
            了解接入方案 →
          </button>
        </section>

        <section
          v-if="workspace.interventions.length"
          class="intervention-workflow"
          aria-label="教师干预任务"
        >
          <header>
            <strong>干预任务</strong
            ><span>草稿 → 已下发 → 已完成，全程留痕</span>
          </header>
          <article v-for="item in workspace.interventions" :key="item.id">
            <div>
              <strong>{{ item.title }}</strong
              ><small>{{ item.alertIds.length }} 项关注线索</small>
            </div>
            <span>{{
              { draft: "草稿", assigned: "已下发", completed: "已完成" }[
                item.status
              ]
            }}</span>
            <button
              v-if="item.status !== 'completed'"
              class="button secondary"
              type="button"
              :disabled="updatingInterventionId === item.id"
              @click="
                advanceIntervention(
                  item.id,
                  item.status === 'draft' ? 'assigned' : 'completed',
                )
              "
            >
              {{ item.status === "draft" ? "确认下发" : "确认完成" }}
            </button>
          </article>
        </section>

        <div class="workspace-content">
          <section
            v-if="activeSection === 'overview'"
            class="page-content overview-page"
          >
            <section class="welcome-row overview-hero">
              <div class="hero-copy">
                <span class="hero-kicker"><i></i> 今日教学指挥台</span>
                <h2>
                  把注意力放在 <em>{{ actionableAlerts.length }}</em> 个关键节点
                </h2>
                <p>聚合测验、采集与对话线索；先看趋势，再决定是否介入。</p>
                <div class="hero-signals" aria-label="教学工作重点">
                  <span
                    ><b>{{ highPriorityCount }}</b> 高优先级</span
                  >
                  <span
                    ><b>{{ displayKpis.dataPassRate }}%</b> 数据可用</span
                  >
                  <span
                    ><b>{{ workspace.experimentName }}</b> 当前实验</span
                  >
                </div>
              </div>
              <div class="hero-visual" aria-label="教学健康度">
                <div
                  class="health-ring"
                  :style="`--health-score: ${teachingHealth}%`"
                >
                  <div>
                    <strong>{{ teachingHealth }}</strong
                    ><span>/100</span><small>教学健康度</small>
                  </div>
                </div>
                <div class="health-summary">
                  <strong>{{
                    teachingHealth >= 90
                      ? "教学节奏总体稳定"
                      : "需要关注数据质量"
                  }}</strong>
                  <span
                    >完成率 {{ displayKpis.completionRate }}% · 数据合格
                    {{ displayKpis.dataPassRate }}%</span
                  >
                </div>
              </div>
            </section>
            <section class="metric-grid" aria-label="班级教学指标">
              <article class="metric-card blue">
                <div class="metric-card-top">
                  <span class="metric-symbol">◉</span
                  ><span class="metric-trend">{{ activeStudentRate }}%</span>
                </div>
                <div>
                  <p>活跃学生</p>
                  <strong
                    >{{ displayKpis.activeStudents }}<small> 人</small></strong
                  ><em>当前筛选：{{ scope.classLabel }}</em
                  ><span class="metric-progress"
                    ><i :style="{ width: `${activeStudentRate}%` }"></i
                  ></span>
                </div>
              </article>
              <article class="metric-card green">
                <div class="metric-card-top">
                  <span class="metric-symbol">✓</span
                  ><span class="metric-trend">已完成</span>
                </div>
                <div>
                  <p>实验完成率</p>
                  <strong
                    >{{ displayKpis.completionRate }}<small>%</small></strong
                  ><em>当前班级已完成实验任务</em
                  ><span class="metric-progress"
                    ><i :style="{ width: `${displayKpis.completionRate}%` }"></i
                  ></span>
                </div>
              </article>
              <article class="metric-card orange">
                <div class="metric-card-top">
                  <span class="metric-symbol">⌁</span
                  ><span class="metric-trend">双重校验</span>
                </div>
                <div>
                  <p>数据合格率</p>
                  <strong>{{ displayKpis.dataPassRate }}<small>%</small></strong
                  ><em>基于图像与计算双重校验</em
                  ><span class="metric-progress"
                    ><i :style="{ width: `${displayKpis.dataPassRate}%` }"></i
                  ></span>
                </div>
              </article>
              <article class="metric-card violet">
                <div class="metric-card-top">
                  <span class="metric-symbol">!</span
                  ><span class="metric-trend attention">需响应</span>
                </div>
                <div>
                  <p>待教师关注</p>
                  <strong
                    >{{ displayKpis.attentionCount }}<small> 项</small></strong
                  ><em
                    ><b>{{ highPriorityCount }} 项高优先级</b></em
                  ><span class="attention-dots" aria-hidden="true"
                    ><i
                      v-for="index in 5"
                      :key="index"
                      :class="{ active: index <= displayKpis.attentionCount }"
                    ></i
                  ></span>
                </div>
              </article>
            </section>
            <section class="overview-grid">
              <article class="panel priority-panel">
                <header class="panel-heading">
                  <div>
                    <span class="workspace-eyebrow">优先处理</span>
                    <h3>本节课教学关注项</h3>
                  </div>
                  <button type="button" @click="goTo('alerts')">
                    查看全部 →
                  </button>
                </header>
                <div class="priority-list">
                  <button
                    v-for="alert in actionableAlerts.slice(0, 3)"
                    :key="alert.id"
                    class="priority-item"
                    type="button"
                    @click="selectAlert(alert)"
                  >
                    <span class="priority-icon" :class="alert.type">{{
                      alert.type === "concept"
                        ? "⌘"
                        : alert.type === "data"
                          ? "⌁"
                          : alert.type === "device"
                            ? "◉"
                            : "↗"
                    }}</span
                    ><span class="priority-copy"
                      ><strong>{{ alert.title }}</strong
                      ><small
                        >{{ alert.student }} · {{ alert.className }}</small
                      ></span
                    ><em :class="alert.level">{{
                      alert.level === "high" ? "高优先级" : "建议跟进"
                    }}</em
                    ><i>›</i>
                  </button>
                </div>
                <footer>每项判断都附带来源证据，教师确认后再发起干预。</footer>
              </article>
              <article class="panel diagnosis-panel">
                <header class="panel-heading">
                  <div>
                    <span class="workspace-eyebrow">AI 教学诊断</span>
                    <h3>为什么需要介入？</h3>
                  </div>
                  <span class="evidence-count">{{
                    scope.diagnosis.confidenceLabel
                  }}</span>
                </header>
                <h4>{{ scope.diagnosis.title }}</h4>
                <p class="diagnosis-summary">{{ scope.diagnosis.summary }}</p>
                <div class="evidence-list">
                  <div
                    v-for="evidence in scope.diagnosis.evidence"
                    :key="evidence.source"
                    class="evidence-item"
                  >
                    <span>{{ evidence.source }}</span
                    ><strong>{{ evidence.label }}</strong
                    ><small>{{ evidence.detail }}</small>
                  </div>
                </div>
                <div class="recommendation">
                  <span>建议行动</span>
                  <p>{{ scope.diagnosis.recommendation }}</p>
                </div>
              </article>
              <article class="panel class-panel">
                <header class="panel-heading">
                  <div>
                    <span class="workspace-eyebrow">班级概览</span>
                    <h3>从总体看到班级差异</h3>
                  </div>
                  <button type="button" @click="goTo('classes')">
                    进入学情 →
                  </button>
                </header>
                <div class="class-list">
                  <button
                    v-for="item in workspace.classes"
                    :key="item.id"
                    type="button"
                    @click="
                      selectedClassId = item.id;
                      goTo('classes');
                    "
                  >
                    <span class="class-avatar">{{ item.name.slice(-2) }}</span
                    ><span class="class-copy"
                      ><strong>{{ item.name }}</strong
                      ><small
                        >{{ item.students }} 人 · {{ item.nextSession }}</small
                      ></span
                    ><span class="class-stat"
                      ><strong>{{ item.completionRate }}%</strong
                      ><small>完成率</small
                      ><span class="class-meter"
                        ><i
                          :style="{ width: `${item.dataPassRate}%` }"
                        ></i></span></span
                    ><i :class="item.trend">{{
                      item.trend === "up" ? "↗" : "→"
                    }}</i>
                  </button>
                </div>
              </article>
              <article class="panel activity-panel">
                <header class="panel-heading">
                  <div>
                    <span class="workspace-eyebrow">实验脉冲</span>
                    <h3>今日学习过程</h3>
                  </div>
                  <span class="updated"
                    >更新于 {{ workspace.updatedAt.slice(-5) }}</span
                  >
                </header>
                <div class="activity-chart">
                  <div
                    v-for="item in scope.activity"
                    :key="item.time"
                    class="activity-column"
                  >
                    <span>{{ item.value }}</span
                    ><i
                      :style="{
                        height: `${(item.value / peakActivity) * 100}%`,
                      }"
                    ></i
                    ><small>{{ item.time }}</small
                    ><em>{{ item.label }}</em>
                  </div>
                </div>
                <div class="activity-legend">
                  <span><i></i>有效学习事件</span
                  ><small
                    >峰值：{{
                      scope.activity.find((item) => item.value === peakActivity)
                        ?.label
                    }}</small
                  >
                </div>
              </article>
            </section>
          </section>

          <section
            v-else-if="activeSection === 'classes'"
            class="page-content classes-page"
          >
            <section class="workspace-page-intro class-page-intro">
              <div class="page-intro-copy">
                <span class="workspace-eyebrow">班级学情</span>
                <h2>把班级差异转成下一步教学动作</h2>
                <p>
                  用完成度、数据质量与待处理事项一起判断班级状态；点击任一班级即可进入对应关注项。
                </p>
              </div>
              <div class="class-comparison-visual" aria-label="班级完成率比较">
                <div class="comparison-score">
                  <strong>{{ classAverages.completion }}%</strong
                  ><span>平均完成率</span>
                </div>
                <div class="comparison-list">
                  <div v-for="item in workspace.classes" :key="item.id">
                    <span>{{ item.name }}</span
                    ><i><b :style="{ width: `${item.completionRate}%` }"></b></i
                    ><strong>{{ item.completionRate }}%</strong>
                  </div>
                </div>
              </div>
            </section>
            <article class="panel data-table-panel">
              <div class="table-header">
                <span>教学班</span><span>实验完成</span><span>数据合格</span
                ><span>平均误差</span><span>需关注</span><span></span>
              </div>
              <button
                v-for="item in workspace.classes"
                :key="item.id"
                type="button"
                class="table-row"
                :class="{ selected: selectedClassId === item.id }"
                @click="
                  selectedClassId = item.id;
                  goTo('alerts');
                "
              >
                <span
                  ><strong>{{ item.name }}</strong
                  ><small
                    >{{ item.students }} 人 · {{ item.nextSession }}</small
                  ></span
                ><span
                  ><strong>{{ item.completionRate }}%</strong
                  ><i
                    ><b
                      :style="{ width: `${item.completionRate}%` }"
                    ></b></i></span
                ><span
                  ><strong>{{ item.dataPassRate }}%</strong
                  ><i class="green"
                    ><b
                      :style="{ width: `${item.dataPassRate}%` }"
                    ></b></i></span
                ><span
                  ><strong>{{ item.averageError }}%</strong
                  ><small>相对误差</small></span
                ><span class="attention-number"
                  >{{ item.attentionCount }} <small>项</small></span
                ><span>查看关注项 ›</span>
              </button>
            </article>
            <article class="panel class-insight">
              <div>
                <span class="workspace-eyebrow">教学建议</span>
                <h3>不要只盯着完成率</h3>
                <p>
                  对完成率较高但数据质量偏低的班级，优先检查“采集条件—观测量—模型输入”的连续性；这比补一套习题更可能提升实验质量。
                </p>
              </div>
              <div class="insight-pill">
                <span>本次筛选</span><strong>{{ scope.classLabel }}</strong
                ><small>{{ actionableAlerts.length }} 项可行动线索</small>
              </div>
            </article>
          </section>

          <section
            v-else-if="activeSection === 'experiments'"
            class="page-content experiments-page"
          >
            <section class="workspace-page-intro process-page-intro">
              <div class="page-intro-copy">
                <span class="workspace-eyebrow">虚实一体实验过程</span>
                <h2>让一次实验留下可分析、可复盘的数据足迹</h2>
                <p>
                  课前推演、课中采集、课后诊断与教师反馈共用同一条记录链路。
                </p>
              </div>
              <div class="process-scorecard" aria-label="实验流程进度">
                <span>当前环节</span
                ><strong>{{ activeStage?.name ?? "流程已就绪" }}</strong>
                <i><b :style="{ width: `${processProgress}%` }"></b></i>
                <small
                  >{{ completedStageCount }} /
                  {{ workspace.stages.length }} 环节已完成</small
                >
              </div>
            </section>
            <article class="panel process-panel">
              <div
                v-for="(stage, index) in workspace.stages"
                :key="stage.name"
                class="process-stage"
                :class="stage.state"
              >
                <span class="stage-number">0{{ index + 1 }}</span
                ><i v-if="index < workspace.stages.length - 1"></i>
                <div>
                  <strong>{{ stage.name }}</strong
                  ><small>{{ stage.description }}</small
                  ><em>{{ stage.metric }}</em>
                </div>
              </div>
            </article>
            <section class="process-benefits">
              <article>
                <span>01</span>
                <h3>先在仿真中暴露理解问题</h3>
                <p>
                  把参数推演、概念测验的过程记录带到真实实验前，教师知道该讲什么。
                </p>
              </article>
              <article>
                <span>02</span>
                <h3>实物数据不止保存结果</h3>
                <p>
                  保留图像、设备条件、关键观测量与计算过程，支持数据质量追溯。
                </p>
              </article>
              <article>
                <span>03</span>
                <h3>AI 将过程转成干预线索</h3>
                <p>
                  不是替教师下结论，而是聚合证据、标记风险、提供可执行的追问与任务。
                </p>
              </article>
            </section>
          </section>

          <section
            v-else-if="activeSection === 'alerts'"
            class="page-content alerts-page"
          >
            <section class="workspace-page-intro alerts-page-intro">
              <div>
                <span class="workspace-eyebrow">重点学生与实验预警</span>
                <h2>每一个提醒，都必须能说明原因</h2>
                <p>
                  先看高优先级，再结合证据决定是否介入；系统不会替教师作出最终判断。
                </p>
              </div>
              <div class="alert-queue" aria-label="预警处理概览">
                <span
                  ><b>{{ highPriorityCount }}</b> 高优先级</span
                >
                <span
                  ><b>{{ alertQueue.inProgress }}</b> 处理中</span
                >
                <span
                  ><b>{{ alertQueue.resolved }}</b> 已归档</span
                >
              </div>
            </section>
            <section v-if="scope.alerts.length" class="alert-layout">
              <article class="panel alert-list-panel">
                <button
                  v-for="alert in scope.alerts"
                  :key="alert.id"
                  type="button"
                  class="alert-list-item"
                  :class="{
                    active: activeAlert?.id === alert.id,
                    resolved: alert.status === 'resolved',
                  }"
                  @click="selectedAlertId = alert.id"
                >
                  <span class="alert-level" :class="alert.level"></span>
                  <div>
                    <strong>{{ alert.title }}</strong
                    ><small
                      >{{ alert.student }} · {{ alert.className }} ·
                      {{ typeLabel(alert.type) }}</small
                    >
                  </div>
                  <em>{{ statusLabel(alert.status) }}</em>
                </button>
              </article>
              <article v-if="activeAlert" class="panel alert-detail-panel">
                <header>
                  <span class="detail-tag" :class="activeAlert.level">{{
                    activeAlert.level === "high"
                      ? "高优先级"
                      : activeAlert.level === "medium"
                        ? "建议本节课处理"
                        : "可自动跟进"
                  }}</span
                  ><span>{{ typeLabel(activeAlert.type) }}</span>
                </header>
                <h3>{{ activeAlert.title }}</h3>
                <p class="detail-description">{{ activeAlert.detail }}</p>
                <section class="detail-block">
                  <span>系统依据</span
                  ><strong>{{ activeAlert.evidence }}</strong
                  ><small>系统仅提供证据归纳；请结合课堂实际作出判断。</small>
                </section>
                <section class="detail-block recommendation-block">
                  <span>建议教师行动</span
                  ><strong>{{ activeAlert.recommendation }}</strong>
                </section>
                <div class="detail-actions">
                  <button
                    class="button secondary"
                    type="button"
                    :disabled="
                      activeAlert.status === 'resolved' ||
                      savingAlertId === activeAlert.id
                    "
                    @click="saveAlert('in_progress')"
                  >
                    {{
                      savingAlertId === activeAlert.id
                        ? "正在保存…"
                        : "加入干预清单"
                    }}</button
                  ><button
                    class="button primary"
                    type="button"
                    :disabled="
                      activeAlert.status === 'resolved' ||
                      savingAlertId === activeAlert.id
                    "
                    @click="saveAlert('resolved')"
                  >
                    确认已处理
                  </button>
                </div>
                <p v-if="notice" class="action-notice" aria-live="polite">
                  {{ notice }}
                </p>
              </article>
            </section>
            <section v-else class="empty-panel">
              <span>✓</span><strong>当前筛选范围没有待跟进事项</strong>
              <p>系统会在出现新的实验质量、概念理解或进度风险时提示教师。</p>
            </section>
          </section>

          <section v-else class="page-content integrations-page">
            <section class="workspace-page-intro integrations-page-intro">
              <div class="page-intro-copy">
                <span class="workspace-eyebrow">产品接入与试点能力</span>
                <h2>不替换已有平台，连接已有教学数据</h2>
                <p>
                  将实验室管理、虚拟仿真与仪器采集沉淀的数据汇入 AI
                  诊断层，减少学校重复建设。
                </p>
              </div>
              <div class="integration-map" aria-label="已接入能力概览">
                <span
                  v-for="item in workspace.integrations"
                  :key="item.id"
                  :class="item.status"
                  :title="item.title"
                  >{{ item.icon }}</span
                >
                <strong>AI<small>诊断层</small></strong>
                <em>{{ connectedIntegrationCount }} 项已映射</em>
              </div>
            </section>
            <section class="data-profile-grid" aria-label="当前数据覆盖范围">
              <article>
                <span>学习者</span
                ><strong>{{ workspace.dataProfile.studentCount }}</strong
                ><small>已纳入教学切片</small>
              </article>
              <article>
                <span>实验记录</span
                ><strong>{{
                  workspace.dataProfile.experimentRecordCount
                }}</strong
                ><small>含图像质量与误差字段</small>
              </article>
              <article>
                <span>测验提交</span
                ><strong>{{ workspace.dataProfile.quizAttemptCount }}</strong
                ><small>含概念与单位题结果</small>
              </article>
              <article>
                <span>学习对话</span
                ><strong>{{ workspace.dataProfile.dialogueEventCount }}</strong
                ><small>用于高频困惑聚类</small>
              </article>
            </section>
            <section class="integration-grid">
              <article
                v-for="item in workspace.integrations"
                :key="item.id"
                class="panel integration-card"
              >
                <header>
                  <span class="integration-icon">{{ item.icon }}</span
                  ><span class="integration-status" :class="item.status">{{
                    integrationLabel(item.status)
                  }}</span>
                </header>
                <span class="integration-category">{{ item.category }}</span>
                <h3>{{ item.title }}</h3>
                <p>{{ item.description }}</p>
                <footer>
                  <span>可交换数据</span><strong>{{ item.capability }}</strong>
                </footer>
              </article>
            </section>
            <article class="pilot-architecture">
              <div>
                <span class="workspace-eyebrow">建议试点路径</span>
                <h3>一项真实实验 · 一个教学班 · 一条完整数据链</h3>
                <p>
                  先验证数据接入、教学诊断和教师干预是否产生真实价值，再扩展至多仪器、多实验和校级平台。
                </p>
              </div>
              <ol>
                <li><span>1</span>同步班级与实验任务</li>
                <li><span>2</span>接入图像 / 仪器 / 仿真数据</li>
                <li><span>3</span>验证 AI 诊断与教师干预效果</li>
              </ol>
            </article>
          </section>
        </div>
      </main>
    </template>
  </div>
</template>

<style scoped src="../styles/teacher-workspace.css"></style>
