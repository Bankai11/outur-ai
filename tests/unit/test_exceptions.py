"""
Unit tests for core/utils/exceptions.py

Tests cover:
- Each exception type's status_code and error_code
- to_dict() output format
- Constructor parameter handling
- Exception hierarchy (all inherit from OUTURAIError)
"""

from __future__ import annotations

import pytest

from core.utils.exceptions import (
    ConfigurationError,
    ConflictError,
    DatabaseError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    OUTURAIError,
    RateLimitError,
    UnauthorizedError,
    ValidationError,
)


@pytest.mark.unit
class TestExceptionHierarchy:
    """All custom exceptions must inherit from OUTURAIError."""

    @pytest.mark.parametrize("exc_class", [
        ValidationError,
        NotFoundError,
        ConflictError,
        UnauthorizedError,
        ForbiddenError,
        RateLimitError,
        DatabaseError,
        ExternalServiceError,
        ConfigurationError,
    ])
    def test_inherits_from_base(self, exc_class: type) -> None:
        assert issubclass(exc_class, OUTURAIError)


@pytest.mark.unit
class TestNotFoundError:
    def test_default_message(self) -> None:
        exc = NotFoundError()
        assert "not found" in exc.detail.lower()

    def test_with_resource_and_id(self) -> None:
        exc = NotFoundError(resource="Company", identifier="abc-123")
        assert "Company" in exc.detail
        assert "abc-123" in exc.detail

    def test_status_code(self) -> None:
        assert NotFoundError.status_code == 404

    def test_error_code(self) -> None:
        assert NotFoundError.error_code == "not_found"

    def test_to_dict(self) -> None:
        exc = NotFoundError(resource="Lead", identifier=42)
        result = exc.to_dict()
        assert result["error"] == "not_found"
        assert "Lead" in result["detail"]


@pytest.mark.unit
class TestValidationError:
    def test_status_code(self) -> None:
        assert ValidationError.status_code == 422

    def test_with_field(self) -> None:
        exc = ValidationError(detail="Email is invalid.", field="email")
        assert exc.field == "email"
        assert exc.context["field"] == "email"

    def test_without_field(self) -> None:
        exc = ValidationError(detail="Bad input.")
        assert exc.field is None


@pytest.mark.unit
class TestExternalServiceError:
    def test_status_code(self) -> None:
        assert ExternalServiceError.status_code == 502

    def test_service_in_context(self) -> None:
        exc = ExternalServiceError(service="Apollo")
        assert exc.context["service"] == "Apollo"


@pytest.mark.unit
class TestUnauthorizedError:
    def test_status_code(self) -> None:
        assert UnauthorizedError.status_code == 401


@pytest.mark.unit
class TestForbiddenError:
    def test_status_code(self) -> None:
        assert ForbiddenError.status_code == 403


@pytest.mark.unit
class TestRateLimitError:
    def test_status_code(self) -> None:
        assert RateLimitError.status_code == 429


@pytest.mark.unit
class TestBaseToDictFormat:
    """to_dict() must always return error and detail keys."""

    @pytest.mark.parametrize("exc", [
        NotFoundError(),
        ValidationError(),
        ConflictError(),
        UnauthorizedError(),
        ForbiddenError(),
        DatabaseError(),
    ])
    def test_to_dict_keys(self, exc: OUTURAIError) -> None:
        result = exc.to_dict()
        assert "error" in result
        assert "detail" in result
