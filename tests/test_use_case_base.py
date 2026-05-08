#!/usr/bin/env python3
from unittest.mock import Mock

import pytest

from core.use_cases.base import BaseUseCase, UseCaseResult


class ConcreteUseCase(BaseUseCase):
    def __init__(self, name=None, impl_fn=None):
        super().__init__(name=name)
        self._impl_fn = impl_fn

    def _execute_impl(self, progress_callback, log_callback, **kwargs):
        if self._impl_fn:
            return self._impl_fn(progress_callback, log_callback, **kwargs)
        return {"message": "done", "data": {"key": "value"}}


class FailingUseCase(BaseUseCase):
    def _execute_impl(self, progress_callback, log_callback, **kwargs):
        raise ValueError("implementation error")


class TestUseCaseResult:
    def test_default_values(self):
        result = UseCaseResult(success=True)
        assert result.success is True
        assert result.message == ""
        assert result.data == {}
        assert result.error == ""
        assert result.duration_ms == 0.0

    def test_to_dict(self):
        result = UseCaseResult(
            success=True,
            message="ok",
            data={"count": 5},
            duration_ms=100.0,
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["message"] == "ok"
        assert d["data"] == {"count": 5}
        assert d["duration_ms"] == 100.0


class TestBaseUseCase:
    def test_default_name(self):
        uc = ConcreteUseCase()
        assert uc.name == "ConcreteUseCase"

    def test_custom_name(self):
        uc = ConcreteUseCase(name="custom")
        assert uc.name == "custom"

    def test_execute_success(self):
        uc = ConcreteUseCase()
        result = uc.execute()
        assert result.success is True
        assert result.message == "done"
        assert result.data == {"key": "value"}
        assert result.duration_ms > 0

    def test_execute_failure(self):
        uc = FailingUseCase()
        result = uc.execute()
        assert result.success is False
        assert "implementation error" in result.error
        assert result.duration_ms > 0

    def test_execute_with_callbacks(self):
        progress_cb = Mock()
        log_cb = Mock()

        def impl(progress, log, **kwargs):
            if progress:
                progress(0.5, 10, 5)
            if log:
                log("starting")
            return {"message": "ok", "data": {}}

        uc = ConcreteUseCase(impl_fn=impl)
        result = uc.execute(progress_callback=progress_cb, log_callback=log_cb)
        assert result.success is True
        progress_cb.assert_called()
        log_cb.assert_called()

    def test_execution_count(self):
        uc = ConcreteUseCase()
        assert uc._execution_count == 0
        uc.execute()
        assert uc._execution_count == 1
        uc.execute()
        assert uc._execution_count == 2

    def test_get_execution_stats(self):
        uc = ConcreteUseCase(name="test_uc")
        uc.execute()
        stats = uc.get_execution_stats()
        assert stats["name"] == "test_uc"
        assert stats["execution_count"] == 1


class TestWrapProgress:
    def test_clamps_below_zero(self):
        uc = ConcreteUseCase()
        cb = Mock()
        wrapped = uc._wrap_progress(cb)
        wrapped(-0.5, 0, 0)
        cb.assert_called_with(0.0, 0, 0)

    def test_clamps_above_one(self):
        uc = ConcreteUseCase()
        cb = Mock()
        wrapped = uc._wrap_progress(cb)
        wrapped(1.5, 0, 0)
        cb.assert_called_with(1.0, 0, 0)

    def test_passes_valid_value(self):
        uc = ConcreteUseCase()
        cb = Mock()
        wrapped = uc._wrap_progress(cb)
        wrapped(0.5, 10, 5)
        cb.assert_called_with(0.5, 10, 5)

    def test_none_callback(self):
        uc = ConcreteUseCase()
        wrapped = uc._wrap_progress(None)
        assert wrapped is None


class TestWrapLog:
    def test_none_callback_returns_noop(self):
        uc = ConcreteUseCase()
        wrapped = uc._wrap_log(None)
        wrapped("test")

    def test_passes_callback_through(self):
        uc = ConcreteUseCase()
        cb = Mock()
        wrapped = uc._wrap_log(cb)
        wrapped("test message")
        cb.assert_called_once_with("test message")


class TestCreateProgressMapper:
    def test_maps_zero_to_start(self):
        uc = ConcreteUseCase()
        mapper = uc._create_progress_mapper(0.2, 0.8)
        result = mapper(0.0)
        assert result == pytest.approx(0.2)

    def test_maps_one_to_end(self):
        uc = ConcreteUseCase()
        mapper = uc._create_progress_mapper(0.2, 0.8)
        result = mapper(1.0)
        assert result == pytest.approx(0.8)

    def test_maps_midpoint(self):
        uc = ConcreteUseCase()
        mapper = uc._create_progress_mapper(0.0, 1.0)
        result = mapper(0.5)
        assert result == pytest.approx(0.5)

    def test_clamps_to_range(self):
        uc = ConcreteUseCase()
        mapper = uc._create_progress_mapper(0.2, 0.8)
        assert mapper(-0.5) == pytest.approx(0.2)
        assert mapper(1.5) == pytest.approx(0.8)
