"""Build a deterministic, privacy-preserving teaching data slice for the local pilot.

The generated workspace is intentionally derived from learner-level records rather
than hand-authored dashboard totals. This makes the teacher demo repeatable while
keeping individual identifiers pseudonymous.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from random import Random
from statistics import fmean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RECORDS_FILE = ROOT / "data" / "teacher_demo_records.json"
WORKSPACE_FILE = ROOT / "data" / "teacher_workspace_seed.json"
RUNTIME_WORKSPACE_FILE = ROOT / "data" / "teacher_workspace.json"
RANDOM_SEED = 20260825
BASE_TIME = datetime(2026, 8, 25, 8, 30)
ACTIVITY_BUCKETS = (
    ("09:00", "预习测验", 54),
    ("10:30", "虚拟推演", 76),
    ("13:30", "图像采集", 108),
    ("15:00", "数据处理", 91),
    ("16:30", "复盘反馈", 48),
)


@dataclass(frozen=True)
class ClassSpec:
    id: str
    name: str
    students: int
    active_students: int
    completed_students: int
    target_passed_records: int
    next_session: str
    trend: str
    concept_error_rate: float


CLASS_SPECS = (
    ClassSpec(
        id="telecom2401",
        name="电信科 2401",
        students=42,
        active_students=41,
        completed_students=40,
        target_passed_records=111,
        next_session="周四 14:00 · 复盘课",
        trend="up",
        concept_error_rate=0.26,
    ),
    ClassSpec(
        id="telecom2402",
        name="电信科 2402",
        students=41,
        active_students=40,
        completed_students=38,
        target_passed_records=103,
        next_session="周五 09:50 · 实验课",
        trend="steady",
        concept_error_rate=0.42,
    ),
)


def _timestamp(offset_minutes: int) -> str:
    return (BASE_TIME + timedelta(minutes=offset_minutes)).strftime("%Y-%m-%d %H:%M:%S")


def _round_percent(numerator: int, denominator: int) -> int:
    return round(numerator / max(denominator, 1) * 100)


def _student_name(student_id: str) -> str:
    """Use a stable pseudonym, avoiding real names in the demo data."""

    class_suffix, number = student_id.split("-s", maxsplit=1)
    return f"学生 {class_suffix[-4:]}-{number}"


def _build_records() -> dict[str, Any]:
    random = Random(RANDOM_SEED)
    students: list[dict[str, Any]] = []
    quiz_attempts: list[dict[str, Any]] = []
    experiment_records: list[dict[str, Any]] = []
    dialogue_events: list[dict[str, Any]] = []
    activity_events: list[dict[str, Any]] = []
    class_student_ids: dict[str, list[str]] = defaultdict(list)

    for class_index, spec in enumerate(CLASS_SPECS):
        passed_records_remaining = spec.target_passed_records
        for position in range(1, spec.students + 1):
            student_id = f"{spec.id}-s{position:02d}"
            active = position <= spec.active_students
            completed = position <= spec.completed_students
            students.append(
                {
                    "id": student_id,
                    "displayName": _student_name(student_id),
                    "classId": spec.id,
                    "enrolledAt": _timestamp(class_index * 11 + position),
                    "active": active,
                    "completed": completed,
                }
            )
            class_student_ids[spec.id].append(student_id)

            concept_correct = random.random() > spec.concept_error_rate
            unit_correct = random.random() > 0.19
            if student_id == "telecom2402-s07":
                concept_correct = False
            if student_id == "telecom2402-s23":
                unit_correct = False
            quiz_attempts.append(
                {
                    "id": f"quiz-{student_id}",
                    "studentId": student_id,
                    "classId": spec.id,
                    "submittedAt": _timestamp(30 + class_index * 17 + position),
                    "score": round(68 + random.random() * 28 - (0 if concept_correct else 13)),
                    "fringeToAngleCorrect": concept_correct,
                    "unitConversionCorrect": unit_correct,
                    "safetyCheckPassed": active,
                }
            )

            if not active:
                continue

            dialogue_count = 1 + int(random.random() > 0.56)
            if not concept_correct:
                dialogue_count += 1
            for dialogue_index in range(dialogue_count):
                cluster = "general_guidance"
                if not concept_correct:
                    cluster = "fringe_to_angle"
                elif not unit_correct:
                    cluster = "unit_conversion"
                dialogue_events.append(
                    {
                        "id": f"dialogue-{student_id}-{dialogue_index + 1}",
                        "studentId": student_id,
                        "classId": spec.id,
                        "occurredAt": _timestamp(90 + class_index * 23 + position + dialogue_index),
                        "cluster": cluster,
                        "resolved": completed and cluster == "general_guidance",
                    }
                )

            for replicate in range(1, 4):
                passed = passed_records_remaining > 0
                passed_records_remaining -= int(passed)
                image_quality = round(
                    (83 if passed else 64) + random.uniform(-7, 7),
                    1,
                )
                relative_error = round(
                    (3.7 if passed else 8.8) + random.uniform(-1.0, 1.5),
                    2,
                )
                if student_id == "telecom2401-s12":
                    image_quality = 72.0
                    relative_error = (8.92, 9.37, 8.61)[replicate - 1]
                    passed = False
                if student_id in {"telecom2401-s28", "telecom2401-s29"}:
                    image_quality = min(image_quality, 61.0 + replicate)
                    passed = False
                experiment_records.append(
                    {
                        "id": f"record-{student_id}-{replicate}",
                        "studentId": student_id,
                        "classId": spec.id,
                        "replicate": replicate,
                        "capturedAt": _timestamp(210 + class_index * 41 + position * 3 + replicate),
                        "imageQuality": image_quality,
                        "fringeContrast": round(image_quality * random.uniform(0.68, 0.86), 1),
                        "screenDistanceMm": round(825 + random.uniform(-9, 9), 1),
                        "stripeSpacingMm": round(1.46 + random.uniform(-0.16, 0.16), 3),
                        "surfaceTensionNPerM": round(0.072 + random.uniform(-0.006, 0.006), 4),
                        "relativeErrorPercent": relative_error,
                        "fitResidual": round(relative_error * random.uniform(0.11, 0.21), 3),
                        "dataPassed": passed,
                    }
                )

    all_student_ids = [student["id"] for student in students if student["active"]]
    for bucket_index, (time, stage, event_count) in enumerate(ACTIVITY_BUCKETS):
        for event_index in range(event_count):
            student_id = all_student_ids[(event_index * 7 + bucket_index * 11) % len(all_student_ids)]
            class_id = student_id.split("-s", maxsplit=1)[0]
            activity_events.append(
                {
                    "id": f"event-{bucket_index + 1}-{event_index + 1}",
                    "studentId": student_id,
                    "classId": class_id,
                    "time": time,
                    "stage": stage,
                    "occurredAt": _timestamp(480 + bucket_index * 70 + event_index),
                }
            )

    return {
        "scenario": {
            "course": "大学物理实验",
            "experiment": "液体表面张力系数测量",
            "measurementWindow": "2026-08-25 08:30–17:20",
        },
        "students": students,
        "quizAttempts": quiz_attempts,
        "experimentRecords": experiment_records,
        "dialogueEvents": dialogue_events,
        "activityEvents": activity_events,
    }


def _activity_summary(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter((event["time"], event["stage"]) for event in events)
    return [
        {"time": time, "label": stage, "value": counts[(time, stage)]}
        for time, stage, _ in ACTIVITY_BUCKETS
    ]


def _build_alerts() -> list[dict[str, Any]]:
    return [
        {
            "id": "alert-1",
            "student": "学生 2402-07",
            "className": "电信科 2402",
            "type": "concept",
            "level": "high",
            "title": "测量链路理解断点",
            "detail": "连续两次将条纹间距 Δx 与衍射角差 δ 混用，尚未建立观测量与模型项的对应关系。",
            "evidence": "测验第 3 题错误 + 4 条“条纹到角度”相似对话 + 复测未通过",
            "recommendation": "课前用装置图追问 Δx、L 与 δ 的关系，再安排一次定向复测。",
            "status": "new",
        },
        {
            "id": "alert-2",
            "student": "学生 2401-12",
            "className": "电信科 2401",
            "type": "data",
            "level": "high",
            "title": "测量误差持续偏高",
            "detail": "连续三组数据的相对误差均高于 8%，需要先排除屏距与标尺基准的系统偏差。",
            "evidence": "3 条采集记录相对误差 8.61%–9.37% + 拟合残差连续偏高",
            "recommendation": "核验屏距 L 与标尺基准，复测一组正负一级条纹并对照残差变化。",
            "status": "new",
        },
        {
            "id": "alert-3",
            "student": "学生 2402-18",
            "className": "电信科 2402",
            "type": "progress",
            "level": "medium",
            "title": "实验流程停留在数据处理",
            "detail": "已完成三组采集，但尚未提交拟合与误差分析，流程停留超过 28 分钟。",
            "evidence": "任务状态停留 + 最近一次有效操作距今 28 分钟",
            "recommendation": "先发送一步式拟合提示；若仍未提交，课后安排同伴互助。",
            "status": "in_progress",
        },
        {
            "id": "alert-4",
            "student": "第 2 采集小组",
            "className": "电信科 2401",
            "type": "device",
            "level": "medium",
            "title": "采集条件需要复核",
            "detail": "同一时段两名学习者的亮纹对比度低于班级中位数，存在环境光或准直条件扰动。",
            "evidence": "图像质量评分 61–63 / 100 + 条纹对比度低于同班 P25",
            "recommendation": "检查激光准直与环境光，保留本组原始图像并复测一组。",
            "status": "new",
        },
        {
            "id": "alert-5",
            "student": "学生 2402-23",
            "className": "电信科 2402",
            "type": "concept",
            "level": "low",
            "title": "单位换算仍需巩固",
            "detail": "主公式代入正确，但频率量纲换算仍有遗漏，建议在下次实验前完成微练习。",
            "evidence": "预习测验 1 处单位题错误 + 2 条单位换算对话",
            "recommendation": "推送 3 题微练习，在下次实验前自动校验。",
            "status": "in_progress",
        },
    ]


def _diagnosis(
    records: dict[str, Any], class_id: str | None, class_name: str | None
) -> dict[str, Any]:
    quiz_attempts = [
        item
        for item in records["quizAttempts"]
        if class_id is None or item["classId"] == class_id
    ]
    experiment_records = [
        item
        for item in records["experimentRecords"]
        if class_id is None or item["classId"] == class_id
    ]
    dialogues = [
        item
        for item in records["dialogueEvents"]
        if class_id is None or item["classId"] == class_id
    ]
    concept_errors = sum(not item["fringeToAngleCorrect"] for item in quiz_attempts)
    readout_risks = sum(item["relativeErrorPercent"] >= 7 for item in experiment_records)
    related_dialogues = sum(item["cluster"] == "fringe_to_angle" for item in dialogues)
    error_rate = _round_percent(concept_errors, len(quiz_attempts))
    scope_label = class_name or "两个教学班"
    return {
        "title": "条纹读取的关键，不是公式代入，而是“观测量如何进入物理模型”",
        "summary": (
            f"{scope_label}在条纹读取、衍射角换算与 Kelvin 公式之间出现连续性理解断点；"
            "优先通过装置图追问而非重复讲解公式。"
        ),
        "recommendation": "在下一次课前插入 6 分钟“装置图—观测量—公式项”连线活动，并对高风险学习者发起定向复测。",
        "confidenceLabel": "测验、采集、对话三源交叉验证",
        "evidence": [
            {
                "source": "测验",
                "label": f"第 3 题错误率 {error_rate}%",
                "detail": "衍射角差 δ 的几何含义仍是高频理解断点",
            },
            {
                "source": "实验记录",
                "label": f"{readout_risks} 条记录出现读数风险",
                "detail": "异常集中在条纹间距与屏距换算环节",
            },
            {
                "source": "AI 对话",
                "label": f"{related_dialogues} 条相关追问",
                "detail": "高频询问如何将 Δx 代入模型计算",
            },
        ],
    }


def build_teacher_demo() -> tuple[dict[str, Any], dict[str, Any]]:
    """Return source records and a workspace summary derived from those records."""

    records = _build_records()
    records_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records["experimentRecords"]:
        records_by_class[record["classId"]].append(record)
    alerts = _build_alerts()

    classes: list[dict[str, Any]] = []
    for spec in CLASS_SPECS:
        students = [student for student in records["students"] if student["classId"] == spec.id]
        class_records = records_by_class[spec.id]
        active_students = sum(student["active"] for student in students)
        completed_students = sum(student["completed"] for student in students)
        classes.append(
            {
                "id": spec.id,
                "name": spec.name,
                "course": "大学物理实验",
                "students": len(students),
                "activeStudents": active_students,
                "completionRate": _round_percent(completed_students, len(students)),
                "dataPassRate": _round_percent(
                    sum(record["dataPassed"] for record in class_records),
                    len(class_records),
                ),
                "averageError": round(
                    fmean(record["relativeErrorPercent"] for record in class_records), 1
                ),
                "attentionCount": sum(
                    alert["className"] == spec.name and alert["status"] != "resolved"
                    for alert in alerts
                ),
                "trend": spec.trend,
                "nextSession": spec.next_session,
                "activity": _activity_summary(
                    [event for event in records["activityEvents"] if event["classId"] == spec.id]
                ),
            }
        )

    total_students = len(records["students"])
    active_students = sum(student["active"] for student in records["students"])
    completed_students = sum(student["completed"] for student in records["students"])
    passed_records = sum(record["dataPassed"] for record in records["experimentRecords"])
    workspace = {
        "dataSource": "demo",
        "organization": "高校物理实验教学试点工作区",
        "teacherName": "王老师",
        "courseName": "大学物理实验",
        "experimentName": "液体表面张力系数测量",
        "updatedAt": "2026-08-25 17:20",
        "revision": 1,
        "dataProfile": {
            "studentCount": total_students,
            "experimentRecordCount": len(records["experimentRecords"]),
            "quizAttemptCount": len(records["quizAttempts"]),
            "dialogueEventCount": len(records["dialogueEvents"]),
            "measurementWindow": records["scenario"]["measurementWindow"],
        },
        "kpis": {
            "activeStudents": active_students,
            "completionRate": _round_percent(completed_students, total_students),
            "dataPassRate": _round_percent(passed_records, len(records["experimentRecords"])),
            "attentionCount": sum(alert["status"] != "resolved" for alert in alerts),
        },
        "classes": classes,
        "alerts": alerts,
        "diagnoses": {
            "all": _diagnosis(records, None, None),
            **{
                spec.id: _diagnosis(records, spec.id, spec.name)
                for spec in CLASS_SPECS
            },
        },
        "stages": [
            {
                "name": "预习校准",
                "description": "概念测验与安全检查",
                "metric": f"{sum(item['safetyCheckPassed'] for item in records['quizAttempts'])} / {total_students} 已通过",
                "state": "complete",
            },
            {
                "name": "虚拟推演",
                "description": "参数影响与测量预演",
                "metric": f"{sum(item['score'] >= 75 for item in records['quizAttempts'])} 人已完成",
                "state": "complete",
            },
            {
                "name": "实物采集",
                "description": "图像、仪器与观测量",
                "metric": f"{len(records['experimentRecords'])} 条采集记录",
                "state": "active",
            },
            {
                "name": "AI 分析",
                "description": "图像质检、计算与误差溯源",
                "metric": f"{_round_percent(passed_records, len(records['experimentRecords']))}% 数据合格",
                "state": "active",
            },
            {
                "name": "反馈复盘",
                "description": "分层任务与学习闭环",
                "metric": f"{sum(alert['status'] != 'resolved' for alert in alerts)} 项待处理",
                "state": "pending",
            },
        ],
        "integrations": [
            {
                "id": "instrument",
                "icon": "⌁",
                "title": "仪器与采集数据",
                "category": "实物实验",
                "status": "ready",
                "description": "接入实验图像、设备参数与采集时间，形成可追溯原始记录。",
                "capability": "相机 / 传感器 / 导入文件",
            },
            {
                "id": "simulation",
                "icon": "◌",
                "title": "虚拟仿真平台",
                "category": "课前与复盘",
                "status": "ready",
                "description": "把虚拟推演结果与实物实验结果放入同一学习链路。",
                "capability": "任务状态 / 参数 / 成绩回传",
            },
            {
                "id": "lms",
                "icon": "▣",
                "title": "教务与实验管理系统",
                "category": "教学管理",
                "status": "pending",
                "description": "同步班级、学习者与实验任务，避免教师重复建班与导出。",
                "capability": "班级名册 / 任务 / 成绩单",
            },
            {
                "id": "ai",
                "icon": "✦",
                "title": "AI 助教与知识库",
                "category": "教学诊断",
                "status": "connected",
                "description": "归纳高频困惑、生成追问建议，并保留判断的来源证据。",
                "capability": "对话聚类 / 证据链 / 干预建议",
            },
        ],
        "activity": _activity_summary(records["activityEvents"]),
        "interventions": [],
        "auditTrail": [],
    }
    return records, workspace


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _preserve_teacher_actions(workspace: dict[str, Any]) -> dict[str, Any]:
    """Carry local teacher decisions into a regenerated teaching data slice."""

    if not RUNTIME_WORKSPACE_FILE.is_file():
        return workspace
    try:
        previous = json.loads(RUNTIME_WORKSPACE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return workspace
    statuses = {
        item.get("id"): item.get("status")
        for item in previous.get("alerts", [])
        if item.get("status") in {"new", "in_progress", "resolved"}
    }
    for alert in workspace["alerts"]:
        if alert["id"] in statuses:
            alert["status"] = statuses[alert["id"]]
    unresolved_alerts = [
        alert for alert in workspace["alerts"] if alert["status"] != "resolved"
    ]
    workspace["kpis"]["attentionCount"] = len(unresolved_alerts)
    for class_item in workspace["classes"]:
        class_item["attentionCount"] = sum(
            alert["className"] == class_item["name"] for alert in unresolved_alerts
        )
    workspace["interventions"] = previous.get("interventions", [])
    workspace["auditTrail"] = previous.get("auditTrail", [])[-200:]
    workspace["revision"] = max(int(workspace["revision"]), int(previous.get("revision", 0)))
    return workspace


def main() -> None:
    records, workspace = build_teacher_demo()
    _write_json(RECORDS_FILE, records)
    _write_json(WORKSPACE_FILE, workspace)
    _write_json(RUNTIME_WORKSPACE_FILE, _preserve_teacher_actions(workspace))
    print(
        "Generated "
        f"{len(records['students'])} learners, "
        f"{len(records['experimentRecords'])} experiment records, "
        f"{len(records['dialogueEvents'])} dialogue events."
    )


if __name__ == "__main__":
    main()
