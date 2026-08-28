import { computed, ref, watch } from "vue";
import {
  createTeacherInterventionDraft,
  getTeacherScope,
  loadTeacherWorkspace,
  createTeacherSession,
  updateTeacherAlert,
  updateTeacherIntervention,
  type AlertStatus,
  type TeacherWorkspace,
} from "../data/teacherWorkspace";

export function useTeacherWorkspace() {
  const workspace = ref<TeacherWorkspace | null>(null);
  const source = ref<"demo" | "live">("demo");
  const transport = ref<"api" | "fixture">("api");
  const loading = ref(true);
  const error = ref("");
  const accessRequired = ref(false);
  const accessCode = ref("");
  const selectedClassId = ref("all");
  const selectedAlertId = ref("");
  const savingAlertId = ref("");
  const creatingDraft = ref(false);
  const updatingInterventionId = ref("");
  const notice = ref("");

  const scope = computed(() =>
    workspace.value
      ? getTeacherScope(workspace.value, selectedClassId.value)
      : null,
  );
  const classOptions = computed(() =>
    workspace.value
      ? [
          { id: "all", name: "全部教学班" },
          ...workspace.value.classes.map((item) => ({
            id: item.id,
            name: item.name,
          })),
        ]
      : [],
  );
  const actionableAlerts = computed(
    () =>
      scope.value?.alerts.filter((item) => item.status !== "resolved") || [],
  );
  const activeAlert = computed(
    () =>
      scope.value?.alerts.find((item) => item.id === selectedAlertId.value) ||
      scope.value?.alerts[0] ||
      null,
  );
  const displayKpis = computed(() => ({
    ...scope.value?.kpis,
    attentionCount: actionableAlerts.value.length,
  }));
  const peakActivity = computed(() =>
    Math.max(...(scope.value?.activity.map((item) => item.value) || [1])),
  );

  watch(
    scope,
    (nextScope) => {
      if (
        !nextScope?.alerts.some((item) => item.id === selectedAlertId.value)
      ) {
        selectedAlertId.value = nextScope?.alerts[0]?.id || "";
      }
    },
    { immediate: true },
  );

  async function refresh() {
    loading.value = true;
    error.value = "";
    accessRequired.value = false;
    const result = await loadTeacherWorkspace();
    loading.value = false;
    if (result.status === "access_required") {
      workspace.value = null;
      error.value = result.message;
      accessRequired.value = true;
      return false;
    }
    if (result.status === "unavailable") {
      workspace.value = null;
      error.value = result.message;
      return false;
    }
    workspace.value = result.workspace;
    source.value = result.source;
    transport.value = result.transport;
    return true;
  }

  async function submitAccessCode() {
    error.value = "";
    try {
      await createTeacherSession(accessCode.value);
      accessCode.value = "";
      return refresh();
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : "教师登录失败";
      return false;
    }
  }

  async function saveAlert(status: AlertStatus) {
    const alert = activeAlert.value;
    const currentWorkspace = workspace.value;
    if (!alert || !currentWorkspace || transport.value !== "api") {
      notice.value =
        "离线演示模式不会修改教学记录。请连接教师服务后再执行该操作。";
      return;
    }
    savingAlertId.value = alert.id;
    notice.value = "";
    try {
      await updateTeacherAlert(alert.id, status, currentWorkspace.revision);
      const refreshed = await refresh();
      if (!refreshed) return;
      notice.value =
        status === "resolved"
          ? "已保存为“已处理”，并记录操作时间与教师身份。"
          : "已保存到教师干预清单，可创建任务后确认下发。";
    } catch (cause) {
      if (cause instanceof Error && "status" in cause && cause.status === 409) {
        await refresh();
        notice.value =
          "有其他教师刚更新了该工作区，已刷新到最新状态，请确认后重试。";
        return;
      }
      notice.value =
        cause instanceof Error ? cause.message : "保存教师干预失败，请重试。";
    } finally {
      savingAlertId.value = "";
    }
  }

  async function createDraft() {
    const currentWorkspace = workspace.value;
    if (!currentWorkspace || transport.value !== "api") {
      notice.value =
        "离线演示模式不会创建教学任务。请连接教师服务后再执行该操作。";
      return;
    }
    creatingDraft.value = true;
    notice.value = "";
    try {
      const draft = await createTeacherInterventionDraft(
        selectedClassId.value,
        currentWorkspace.revision,
      );
      const refreshed = await refresh();
      if (!refreshed) return;
      notice.value = `已创建“${draft.title}”，覆盖 ${draft.alertIds.length} 项关注线索。`;
    } catch (cause) {
      if (cause instanceof Error && "status" in cause && cause.status === 409) {
        await refresh();
        notice.value =
          "有其他教师刚更新了该工作区，已刷新到最新状态，请确认后重试。";
        return;
      }
      notice.value =
        cause instanceof Error ? cause.message : "创建干预任务失败，请重试。";
    } finally {
      creatingDraft.value = false;
    }
  }

  async function advanceIntervention(
    interventionId: string,
    status: "assigned" | "completed",
  ) {
    const currentWorkspace = workspace.value;
    if (!currentWorkspace || transport.value !== "api") return;
    updatingInterventionId.value = interventionId;
    notice.value = "";
    try {
      await updateTeacherIntervention(
        interventionId,
        status,
        currentWorkspace.revision,
      );
      if (!(await refresh())) return;
      notice.value =
        status === "assigned"
          ? "干预任务已下发并记录操作人和时间。"
          : "干预任务已完成并写入审计记录。";
    } catch (cause) {
      if (cause instanceof Error && "status" in cause && cause.status === 409) {
        await refresh();
      }
      notice.value =
        cause instanceof Error ? cause.message : "更新干预任务失败";
    } finally {
      updatingInterventionId.value = "";
    }
  }

  return {
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
  };
}
