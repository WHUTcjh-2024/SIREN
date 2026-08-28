from dataclasses import replace

import pytest

from backend.core.config import get_settings


def test_external_binding_requires_a_long_teacher_access_code():
    settings = replace(
        get_settings(),
        siren_env="development",
        siren_host="0.0.0.0",
        teacher_access_code="",
    )
    with pytest.raises(RuntimeError, match="TEACHER_ACCESS_CODE"):
        settings.validate()


def test_cors_wildcard_is_rejected():
    settings = replace(get_settings(), siren_cors_origins=("*",))
    with pytest.raises(RuntimeError, match="通配符"):
        settings.validate()
