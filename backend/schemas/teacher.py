from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


AlertStatus = Literal["new", "in_progress", "resolved"]
TeacherDataSource = Literal["demo", "live"]
AlertType = Literal["concept", "data", "progress", "device"]
AlertLevel = Literal["high", "medium", "low"]
Trend = Literal["up", "steady", "down"]
IntegrationStatus = Literal["connected", "ready", "pending"]
StageStatus = Literal["complete", "active", "pending"]


class TeacherActor(BaseModel):
    """Temporary local actor contract; replace with SSO-backed identity in deployment."""

    id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=80)


class AlertStatusWrite(BaseModel):
    status: AlertStatus
    note: str | None = Field(default=None, max_length=500)
    expected_revision: int = Field(
        ge=0,
        validation_alias=AliasChoices("expectedRevision", "expected_revision"),
    )


class InterventionDraftWrite(BaseModel):
    class_id: str | None = Field(
        default=None,
        max_length=64,
        validation_alias=AliasChoices("classId", "class_id"),
    )
    title: str | None = Field(default=None, max_length=120)
    expected_revision: int = Field(
        ge=0,
        validation_alias=AliasChoices("expectedRevision", "expected_revision"),
    )


class AuditEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str
    timestamp: datetime
    actor_id: str = Field(alias="actorId")
    actor_name: str = Field(alias="actorName")
    action: Literal["alert_status_updated", "intervention_draft_created"]
    entity_id: str = Field(alias="entityId")
    previous_status: AlertStatus | None = Field(default=None, alias="previousStatus")
    next_status: AlertStatus | None = Field(default=None, alias="nextStatus")
    note: str | None = None


class ActivityPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    time: str
    label: str
    value: int = Field(ge=0)


class ClassSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str
    name: str
    course: str
    students: int = Field(ge=0)
    active_students: int = Field(alias="activeStudents", ge=0)
    completion_rate: int = Field(alias="completionRate", ge=0, le=100)
    data_pass_rate: int = Field(alias="dataPassRate", ge=0, le=100)
    average_error: float = Field(alias="averageError", ge=0)
    attention_count: int = Field(alias="attentionCount", ge=0)
    trend: Trend
    next_session: str = Field(alias="nextSession")
    activity: list[ActivityPoint]


class TeachingAlert(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str
    student: str
    class_name: str = Field(alias="className")
    type: AlertType
    level: AlertLevel
    title: str
    detail: str
    evidence: str
    recommendation: str
    status: AlertStatus


class DiagnosisEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["测验", "实验记录", "AI 对话"]
    label: str
    detail: str


class TeachingDiagnosis(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    title: str
    summary: str
    recommendation: str
    confidence_label: str = Field(alias="confidenceLabel")
    evidence: list[DiagnosisEvidence]


class ExperimentStage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    metric: str
    state: StageStatus


class IntegrationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    icon: str
    title: str
    category: str
    status: IntegrationStatus
    description: str
    capability: str


class InterventionDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str
    title: str
    class_id: str = Field(alias="classId")
    alert_ids: list[str] = Field(alias="alertIds")
    status: Literal["draft", "assigned", "completed"]
    created_at: str = Field(alias="createdAt")
    created_by: dict[str, str] = Field(alias="createdBy")


class TeacherKpis(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    active_students: int = Field(alias="activeStudents", ge=0)
    completion_rate: int = Field(alias="completionRate", ge=0, le=100)
    data_pass_rate: int = Field(alias="dataPassRate", ge=0, le=100)
    attention_count: int = Field(alias="attentionCount", ge=0)


class TeachingDataProfile(BaseModel):
    """Aggregate coverage metadata shown without exposing learner-level records."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    student_count: int = Field(alias="studentCount", ge=0)
    experiment_record_count: int = Field(alias="experimentRecordCount", ge=0)
    quiz_attempt_count: int = Field(alias="quizAttemptCount", ge=0)
    dialogue_event_count: int = Field(alias="dialogueEventCount", ge=0)
    measurement_window: str = Field(alias="measurementWindow", min_length=1)


class TeacherWorkspaceData(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    data_source: TeacherDataSource = Field(alias="dataSource")
    organization: str
    teacher_name: str = Field(alias="teacherName")
    course_name: str = Field(alias="courseName")
    experiment_name: str = Field(alias="experimentName")
    updated_at: str = Field(alias="updatedAt")
    revision: int = Field(ge=0)
    data_profile: TeachingDataProfile = Field(alias="dataProfile")
    kpis: TeacherKpis
    classes: list[ClassSummary]
    alerts: list[TeachingAlert]
    diagnoses: dict[str, TeachingDiagnosis]
    stages: list[ExperimentStage]
    integrations: list[IntegrationItem]
    activity: list[ActivityPoint]
    interventions: list[InterventionDraft]
    audit_trail: list[AuditEntry] = Field(alias="auditTrail")


class TeacherWorkspaceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True]
    data: TeacherWorkspaceData
    source: TeacherDataSource
    revision: int = Field(ge=0)


class AlertUpdateData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert: TeachingAlert
    audit: AuditEntry
    revision: int = Field(ge=0)


class AlertUpdateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True]
    data: AlertUpdateData


class InterventionDraftData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intervention: InterventionDraft
    audit: AuditEntry
    revision: int = Field(ge=0)


class InterventionDraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True]
    data: InterventionDraftData
