#!/usr/bin/env python3
from unittest.mock import Mock, patch

from api.api_orchestrator import APIOrchestrator
from api.circuit_breaker import CircuitBreaker


class TestAPIOrchestratorInit:
    def test_default_initialization(self):
        config = {}
        orch = APIOrchestrator(config)
        assert orch.available_apis == []
        assert orch.current_api_index == 0
        assert orch.max_threads_per_api == 3
        assert isinstance(orch.circuit_breaker, CircuitBreaker)

    def test_custom_max_threads(self):
        config = {"basic": {"max_threads_per_api": 5}}
        orch = APIOrchestrator(config)
        assert orch.max_threads_per_api == 5

    def test_circuit_breaker_config(self):
        config = {
            "advanced": {
                "circuit_breaker": {
                    "failure_threshold": 10,
                    "recovery_timeout": 120,
                }
            }
        }
        orch = APIOrchestrator(config)
        assert orch.circuit_breaker.failure_threshold == 10
        assert orch.circuit_breaker.recovery_timeout == 120


class TestBuildApiList:
    def test_empty_config(self):
        orch = APIOrchestrator({})
        result = orch.build_api_list()
        assert result == []

    def test_filters_disabled(self):
        config = {
            "apis": [
                {"name": "a", "enabled": True},
                {"name": "b", "enabled": False},
                {"name": "c"},
            ]
        }
        orch = APIOrchestrator(config)
        result = orch.build_api_list()
        assert len(result) == 2
        assert result[0]["name"] == "a"
        assert result[1]["name"] == "c"

    def test_default_enabled_true(self):
        config = {"apis": [{"name": "a"}]}
        orch = APIOrchestrator(config)
        result = orch.build_api_list()
        assert len(result) == 1


class TestGetNextApi:
    def test_no_available_apis(self):
        orch = APIOrchestrator({})
        assert orch.get_next_api() is None

    def test_returns_available_api(self):
        orch = APIOrchestrator({})
        api1 = {"name": "api1"}
        api2 = {"name": "api2"}
        orch.available_apis = [api1, api2]
        result = orch.get_next_api()
        assert result is not None
        assert result["name"] in ("api1", "api2")

    def test_round_robin(self):
        orch = APIOrchestrator({})
        api1 = {"name": "api1"}
        api2 = {"name": "api2"}
        orch.available_apis = [api1, api2]
        first = orch.get_next_api()
        second = orch.get_next_api()
        assert first["name"] != second["name"]

    def test_skips_open_circuit_breaker(self):
        orch = APIOrchestrator({})
        api1 = {"name": "api1"}
        api2 = {"name": "api2"}
        orch.available_apis = [api1, api2]

        for _ in range(5):
            orch.circuit_breaker.record_failure("api1")

        result = orch.get_next_api()
        assert result["name"] == "api2"

    def test_skips_max_threads(self):
        config = {"basic": {"max_threads_per_api": 1}}
        orch = APIOrchestrator(config)
        api1 = {"name": "api1"}
        api2 = {"name": "api2"}
        orch.available_apis = [api1, api2]
        orch.api_active_threads["api1"] = 1

        result = orch.get_next_api()
        assert result["name"] == "api2"

    def test_all_apis_unavailable(self):
        config = {"basic": {"max_threads_per_api": 1}}
        orch = APIOrchestrator(config)
        api1 = {"name": "api1"}
        orch.available_apis = [api1]
        orch.api_active_threads["api1"] = 1

        result = orch.get_next_api()
        assert result is None


class TestAcquireReleaseApiThread:
    def test_acquire_success(self):
        orch = APIOrchestrator({})
        api = {"name": "api1"}
        assert orch.acquire_api_thread(api) is True
        assert orch.api_active_threads["api1"] == 1

    def test_acquire_at_max(self):
        config = {"basic": {"max_threads_per_api": 1}}
        orch = APIOrchestrator(config)
        api = {"name": "api1"}
        orch.acquire_api_thread(api)
        assert orch.acquire_api_thread(api) is False

    def test_release_decrements(self):
        orch = APIOrchestrator({})
        api = {"name": "api1"}
        orch.acquire_api_thread(api)
        orch.acquire_api_thread(api)
        assert orch.api_active_threads["api1"] == 2
        orch.release_api_thread(api)
        assert orch.api_active_threads["api1"] == 1

    def test_release_does_not_go_below_zero(self):
        orch = APIOrchestrator({})
        api = {"name": "api1"}
        orch.release_api_thread(api)
        assert orch.api_active_threads.get("api1", 0) == 0


class TestRecordSuccessFailure:
    def test_record_success(self):
        orch = APIOrchestrator({})
        orch.circuit_breaker = Mock()
        orch.record_success("api1")
        orch.circuit_breaker.record_success.assert_called_once_with("api1")

    def test_record_failure(self):
        orch = APIOrchestrator({})
        orch.circuit_breaker = Mock()
        orch.record_failure("api1")
        orch.circuit_breaker.record_failure.assert_called_once_with("api1")


class TestGetAvailableApis:
    def test_returns_copy(self):
        orch = APIOrchestrator({})
        api = {"name": "api1"}
        orch.available_apis = [api]
        result = orch.get_available_apis()
        assert result == [api]
        result.append({"name": "api2"})
        assert len(orch.available_apis) == 1


class TestGetApiStats:
    def test_stats_structure(self):
        orch = APIOrchestrator({})
        api = {"name": "api1"}
        orch.available_apis = [api]
        orch.api_active_threads = {"api1": 2}

        stats = orch.get_api_stats()
        assert stats["total_apis"] == 1
        assert stats["active_threads"] == {"api1": 2}
        assert stats["max_threads_per_api"] == 3
        assert "circuit_breaker_status" in stats
        assert "api1" in stats["circuit_breaker_status"]


class TestDetectAvailableApis:
    def test_detect_sets_available_apis(self):
        with patch("api.api_detector.APIDetector") as mock_cls:
            mock_detector = Mock()
            mock_detector.detect_available.return_value = [{"name": "api1"}]
            mock_cls.return_value = mock_detector

            orch = APIOrchestrator({})
            result = orch.detect_available_apis()
            assert len(result) == 1
            assert result[0]["name"] == "api1"
            assert orch.current_api_index == 0
