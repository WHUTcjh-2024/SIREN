import workspaceSeed from "../../../data/teacher_workspace_seed.json";
import { ApiError, api } from "../api/client";

export type TeacherSection =
  | "overview"
  | "classes"
  | "experiments"
  | "alerts"
  | "integrations";
export type AlertStatus = "new" | "in_progress" | "resolved";
export type TeacherDataSource = "demo" | "live";
export type InterventionStatus = "draft" | "assigned" | "completed";

export interface ActivityPoint {
  time: string;
  label: string;
  value: number;
}

export interface ClassSummary {
  id: string;
  name: string;
  course: string;
  students: number;
  activeStudents: number;
  completionRate: number;
  dataPassRate: number;
  averageError: number;
  attentionCount: number;
  trend: "up" | "steady" | "down";
  nextSession: string;
  activity: ActivityPoint[];
}

export interface TeachingAlert {
  id: string;
  student: string;
  className: string;
  type: "concept" | "data" | "progress" | "device";
  level: "high" | "medium" | "low";
  title: string;
  detail: string;
  evidence: string;
  recommendation: string;
  status: AlertStatus;
}

export interface TeachingDiagnosis {
  title: string;
  summary: string;
  recommendation: string;
  confidenceLabel: string;
  evidence: Array<{
    source: "测验" | "实验记录" | "AI 对话";
    label: string;
    detail: string;
  }>;
}

export interface ExperimentStage {
  name: string;
  description: string;
  metric: string;
  state: "complete" | "active" | "pending";
}

export interface IntegrationItem {
  id: string;
  icon: string;
  title: string;
  category: string;
  status: "connected" | "ready" | "pending";
  description: string;
  capability: string;
}

export interface TeacherWorkspace {
  dataSource: TeacherDataSource;
  organization: string;
  teacherName: string;
  courseName: string;
  experimentName: string;
  updatedAt: string;
  revision: number;
  dataProfile: {
    studentCount: number;
    experimentRecordCount: number;
    quizAttemptCount: number;
    dialogueEventCount: number;
    measurementWindow: string;
  };
  kpis: {
    activeStudents: number;
    completionRate: number;
    dataPassRate: number;
    attentionCount: number;
  };
  classes: ClassSummary[];
  alerts: TeachingAlert[];
  diagnoses: Record<string, TeachingDiagnosis>;
  stages: ExperimentStage[];
  integrations: IntegrationItem[];
  activity: ActivityPoint[];
  interventions: Array<{
    id: string;
    title: string;
    classId: string;
    alertIds: string[];
    status: InterventionStatus;
    createdAt: string;
    assignedAt?: string;
    completedAt?: string;
    completionNote?: string;
  }>;
  auditTrail: Array<{
    id: string;
    timestamp: string;
    actorId: string;
    actorName: string;
    action: string;
    entityId: string;
    previousStatus?: AlertStatus;
    nextStatus?: AlertStatus;
    note?: string;
  }>;
}

export interface TeacherScope {
  classItem?: ClassSummary;
  classLabel: string;
  kpis: TeacherWorkspace["kpis"];
  alerts: TeachingAlert[];
  diagnosis: TeachingDiagnosis;
  activity: ActivityPoint[];
}

export type TeacherWorkspaceLoad =
  | {
      status: "ready";
      workspace: TeacherWorkspace;
      source: TeacherDataSource;
      transport: "api" | "fixture";
    }
  | { status: "access_required"; message: string }
  | { status: "unavailable"; message: string };

export const teacherDemoWorkspace = workspaceSeed as TeacherWorkspace;
export async function createTeacherSession(accessCode: string): Promise<void> {
  await api("/api/teacher/session", {
    method: "POST",
    body: JSON.stringify({ accessCode: accessCode.trim() }),
  });
}

/**
 * API is the default even in development. Use VITE_TEACHER_DATA_SOURCE=fixture
 * only for an explicitly offline visual demo. Errors never silently become demo data.
 */
export async function loadTeacherWorkspace(): Promise<TeacherWorkspaceLoad> {
  if (import.meta.env.VITE_TEACHER_DATA_SOURCE === "fixture") {
    return {
      status: "ready",
      workspace: teacherDemoWorkspace,
      source: "demo",
      transport: "fixture",
    };
  }

  try {
    const response = await api<{
      data: TeacherWorkspace;
      source: TeacherDataSource;
    }>("/api/teacher/workspace");
    return {
      status: "ready",
      workspace: response.data,
      source: response.source,
      transport: "api",
    };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return { status: "access_required", message: error.message };
    }
    return {
      status: "unavailable",
      message:
        error instanceof Error ? error.message : "教师工作区服务暂不可用",
    };
  }
}

export async function updateTeacherAlert(
  alertId: string,
  status: AlertStatus,
  expectedRevision: number,
): Promise<{ alert: TeachingAlert; revision: number }> {
  const response = await api<{
    data: { alert: TeachingAlert; revision: number };
  }>(`/api/teacher/alerts/${encodeURIComponent(alertId)}`, {
    method: "PATCH",
    body: JSON.stringify({ status, expectedRevision }),
  });
  return response.data;
}

export async function createTeacherInterventionDraft(
  classId: string | undefined,
  expectedRevision: number,
): Promise<{
  id: string;
  title: string;
  alertIds: string[];
  revision: number;
}> {
  const response = await api<{
    data: {
      intervention: { id: string; title: string; alertIds: string[] };
      revision: number;
    };
  }>("/api/teacher/interventions/drafts", {
    method: "POST",
    body: JSON.stringify({
      classId: classId === "all" ? null : classId,
      expectedRevision,
    }),
  });
  return { ...response.data.intervention, revision: response.data.revision };
}

export async function updateTeacherIntervention(
  interventionId: string,
  status: Exclude<InterventionStatus, "draft">,
  expectedRevision: number,
): Promise<{ revision: number }> {
  const response = await api<{ data: { revision: number } }>(
    `/api/teacher/interventions/${encodeURIComponent(interventionId)}`,
    {
      method: "PATCH",
      body: JSON.stringify({ status, expectedRevision }),
    },
  );
  return response.data;
}

export function getTeacherScope(
  workspace: TeacherWorkspace,
  classId: string,
): TeacherScope {
  const classItem = workspace.classes.find((item) => item.id === classId);
  const alerts = classItem
    ? workspace.alerts.filter((item) => item.className === classItem.name)
    : workspace.alerts;
  const kpis = classItem
    ? {
        activeStudents: classItem.activeStudents,
        completionRate: classItem.completionRate,
        dataPassRate: classItem.dataPassRate,
        attentionCount: classItem.attentionCount,
      }
    : workspace.kpis;

  return {
    classItem,
    classLabel: classItem?.name || "全部教学班",
    kpis,
    alerts,
    diagnosis: workspace.diagnoses[classId] || workspace.diagnoses.all,
    activity: classItem?.activity || workspace.activity,
  };
}
