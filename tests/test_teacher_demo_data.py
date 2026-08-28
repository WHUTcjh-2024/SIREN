import json
from pathlib import Path

from backend.schemas.teacher import TeacherWorkspaceData
from scripts.generate_teacher_demo_data import RECORDS_FILE, WORKSPACE_FILE, build_teacher_demo


def test_generated_demo_workspace_is_backed_by_learner_level_records():
    records, workspace = build_teacher_demo()
    parsed = TeacherWorkspaceData.model_validate(workspace)

    assert parsed.data_profile.student_count == len(records["students"])
    assert parsed.data_profile.experiment_record_count == len(records["experimentRecords"])
    assert parsed.data_profile.quiz_attempt_count == len(records["quizAttempts"])
    assert parsed.data_profile.dialogue_event_count == len(records["dialogueEvents"])
    assert len(parsed.classes) == 2
    assert any(alert["id"] == "alert-2" for alert in workspace["alerts"])


def test_committed_data_files_match_the_generated_workspace_profile():
    records = json.loads(Path(RECORDS_FILE).read_text(encoding="utf-8"))
    workspace = json.loads(Path(WORKSPACE_FILE).read_text(encoding="utf-8"))
    parsed = TeacherWorkspaceData.model_validate(workspace)

    assert parsed.data_profile.student_count == len(records["students"])
    assert parsed.data_profile.experiment_record_count == len(records["experimentRecords"])
    assert parsed.data_profile.quiz_attempt_count == len(records["quizAttempts"])
    assert parsed.data_profile.dialogue_event_count == len(records["dialogueEvents"])
