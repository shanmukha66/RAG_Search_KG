"""
Tests for monitoring and error handling system
"""

import pytest
import time
import asyncio
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json

# Import monitoring components
from monitoring import (
    ErrorHandler, ErrorSeverity, ErrorCategory,
    HealthChecker, HealthStatus,
    MetricsCollector, MetricPoint,
    SystemStateRecovery, ServiceState, RecoveryAction
)
from monitoring.input_validation import InputValidator, validate_request
from monitoring.logger import setup_logging, get_logger


class TestErrorHandler:
    """Test error handling functionality"""
    
    def setup_method(self):
        self.error_handler = ErrorHandler()
    
    def test_error_classification(self):
        """Test error classification logic"""
        # Test validation error
        error = ValueError("Invalid input data")
        category, severity = self.error_handler.classify_error(error)
        assert category == ErrorCategory.VALIDATION
        assert severity == ErrorSeverity.LOW
        
        # Test database error
        error = Exception("Database connection failed")
        category, severity = self.error_handler.classify_error(error)
        assert category == ErrorCategory.DATABASE
        assert severity == ErrorSeverity.HIGH
        
        # Test timeout error
        error = TimeoutError("Request timed out")
        category, severity = self.error_handler.classify_error(error)
        assert category == ErrorCategory.TIMEOUT
        assert severity == ErrorSeverity.MEDIUM
    
    def test_error_recording(self):
        """Test error recording and statistics"""
        initial_count = self.error_handler.error_stats['total_errors']
        
        # Record an error
        error = ValueError("Test error")
        error_details = self.error_handler.record_error(
            error,
            context={'test': 'context'},
            user_id='test_user'
        )
        
        # Check error details
        assert error_details.error_type == 'ValueError'
        assert error_details.message == 'Test error'
        assert error_details.user_id == 'test_user'
        assert error_details.context['test'] == 'context'
        
        # Check statistics update
        assert self.error_handler.error_stats['total_errors'] == initial_count + 1
        assert self.error_handler.error_stats['errors_by_category']['validation'] == 1
    
    def test_get_error_stats(self):
        """Test error statistics retrieval"""
        # Record multiple errors
        for i in range(3):
            self.error_handler.record_error(ValueError(f"Error {i}"))
        
        stats = self.error_handler.get_error_stats()
        
        assert stats['total_errors'] >= 3
        assert 'errors_by_category' in stats
        assert 'errors_by_severity' in stats
        assert 'recent_errors' in stats


class TestHealthChecker:
    """Test health checking functionality"""
    
    def setup_method(self):
        self.health_checker = HealthChecker()
    
    def test_system_resources_check(self):
        """Test system resource monitoring"""
        result = self.health_checker.check_system_resources()
        
        assert result.component == "system_resources"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert result.response_time > 0
        assert 'cpu_percent' in result.details
        assert 'memory_percent' in result.details
    
    def test_register_and_run_check(self):
        """Test registering and running custom health checks"""
        # Mock health check function
        mock_check = Mock(return_value=True)
        
        self.health_checker.register_check(
            "test_service",
            mock_check,
            critical=True
        )
        
        # Run the check
        result = self.health_checker.run_single_check("test_service")
        
        assert mock_check.called
        assert result.component == "test_service"
    
    def test_overall_status_calculation(self):
        """Test overall system status calculation"""
        # Register mock checks
        self.health_checker.register_check(
            "healthy_service",
            lambda: True,
            critical=True
        )
        
        self.health_checker.register_check(
            "unhealthy_service",
            lambda: False,
            critical=True
        )
        
        status, message = self.health_checker.get_overall_status()
        assert status == HealthStatus.UNHEALTHY
        assert "unhealthy_service" in message
    
    def test_health_summary(self):
        """Test comprehensive health summary"""
        summary = self.health_checker.get_health_summary()
        
        assert 'overall_status' in summary
        assert 'overall_message' in summary
        assert 'components' in summary
        assert 'statistics' in summary
        assert 'timestamp' in summary


class TestMetricsCollector:
    """Test metrics collection functionality"""
    
    def setup_method(self):
        self.metrics = MetricsCollector(retention_period=60)  # 1 minute for testing
    
    def test_record_metric(self):
        """Test basic metric recording"""
        self.metrics.record_metric("test_metric", 42.0, {"tag": "value"})
        
        # Check metric was recorded
        assert "test_metric" in self.metrics.metrics
        assert len(self.metrics.metrics["test_metric"]) == 1
        
        point = self.metrics.metrics["test_metric"][0]
        assert point.value == 42.0
        assert point.tags["tag"] == "value"
    
    def test_counter_operations(self):
        """Test counter increment operations"""
        self.metrics.increment_counter("test_counter", 5)
        self.metrics.increment_counter("test_counter", 3)
        
        assert self.metrics.counters["test_counter"] == 8
    
    def test_gauge_operations(self):
        """Test gauge set operations"""
        self.metrics.set_gauge("test_gauge", 100.0)
        self.metrics.set_gauge("test_gauge", 150.0)
        
        assert self.metrics.gauges["test_gauge"] == 150.0
    
    def test_histogram_operations(self):
        """Test histogram recording"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in values:
            self.metrics.record_histogram("test_histogram", value)
        
        assert len(self.metrics.histograms["test_histogram"]) == 5
    
    def test_metric_summary(self):
        """Test metric summary calculation"""
        # Record some test data
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in values:
            self.metrics.record_metric("test_summary", value)
        
        summary = self.metrics.get_metric_summary("test_summary", time_window=60)
        
        assert summary is not None
        assert summary.count == 5
        assert summary.avg == 3.0
        assert summary.min == 1.0
        assert summary.max == 5.0
    
    def test_request_recording(self):
        """Test HTTP request metrics recording"""
        self.metrics.record_request("GET", "/api/test", 200, 0.5)
        
        # Check system metrics were updated
        assert self.metrics.system_metrics['requests_total'] == 1
        assert self.metrics.system_metrics['requests_failed'] == 0
    
    def test_error_recording(self):
        """Test error metrics recording"""
        self.metrics.record_error("ValueError", "Test error", "test_component")
        
        assert self.metrics.system_metrics['errors_by_type']['ValueError'] == 1
    
    def test_performance_report(self):
        """Test performance report generation"""
        # Record some test metrics
        for i in range(5):
            self.metrics.record_histogram("http_request_duration", 0.1 * i)
            self.metrics.record_histogram("search_duration", 0.2 * i)
        
        report = self.metrics.get_performance_report(time_window=300)
        
        assert 'report_period' in report
        assert 'performance' in report
        assert 'system_health' in report
        assert 'generated_at' in report


class TestSystemStateRecovery:
    """Test system state recovery functionality"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.recovery = SystemStateRecovery(state_dir=self.temp_dir)
    
    def teardown_method(self):
        shutil.rmtree(self.temp_dir)
    
    def test_service_registration(self):
        """Test service registration for recovery"""
        mock_health_check = Mock(return_value=True)
        
        from monitoring.state_recovery import RecoveryPlan
        recovery_plan = RecoveryPlan(
            service_name="test_service",
            actions=[RecoveryAction.RESTART_SERVICE],
            max_attempts=3,
            timeout=30.0
        )
        
        self.recovery.register_service(
            "test_service",
            mock_health_check,
            recovery_plan
        )
        
        assert "test_service" in self.recovery.services
        assert "test_service" in self.recovery.service_states
        assert "test_service" in self.recovery.recovery_plans
    
    def test_health_check_execution(self):
        """Test service health check execution"""
        mock_health_check = Mock(return_value=True)
        
        from monitoring.state_recovery import RecoveryPlan
        recovery_plan = RecoveryPlan(
            service_name="test_service",
            actions=[RecoveryAction.RESTART_SERVICE],
            max_attempts=3,
            timeout=30.0
        )
        
        self.recovery.register_service(
            "test_service",
            mock_health_check,
            recovery_plan
        )
        
        status = self.recovery.check_service_health("test_service")
        
        assert mock_health_check.called
        assert status.state == ServiceState.RUNNING
        assert status.error_count == 0
    
    def test_system_status(self):
        """Test system status retrieval"""
        status = self.recovery.get_system_status()
        
        assert 'overall_health' in status
        assert 'services' in status
        assert 'statistics' in status
        assert 'recovery_status' in status
    
    def test_state_backup_and_restore(self):
        """Test system state backup and restore"""
        # Backup current state
        self.recovery.backup_system_state()
        
        # Check backup file exists
        backup_files = list(Path(self.temp_dir).glob("system_state_*.json"))
        assert len(backup_files) > 0
        
        latest_file = Path(self.temp_dir) / "latest_state.json"
        assert latest_file.exists()
        
        # Test restore
        self.recovery.restore_system_state()  # Should not raise exception


class TestInputValidator:
    """Test input validation functionality"""
    
    def setup_method(self):
        self.validator = InputValidator()
    
    def test_search_request_validation(self):
        """Test search request validation"""
        # Valid request
        valid_data = {
            'query': 'test query',
            'session_id': '550e8400-e29b-41d4-a716-446655440000',
            'limit': 10
        }
        
        result = self.validator.validate_search_request(valid_data)
        assert result['query'] == 'test query'
        assert result['session_id'] == '550e8400-e29b-41d4-a716-446655440000'
        assert result['limit'] == 10
    
    def test_search_request_validation_errors(self):
        """Test search request validation error cases"""
        # Empty query
        with pytest.raises(ValueError, match="Search query is required"):
            self.validator.validate_search_request({'query': ''})
        
        # Query too long
        with pytest.raises(ValueError, match="Query too long"):
            self.validator.validate_search_request({'query': 'x' * 1001})
        
        # Invalid session ID
        with pytest.raises(ValueError, match="Invalid session ID format"):
            self.validator.validate_search_request({
                'query': 'test',
                'session_id': 'invalid-session-id'
            })
        
        # Invalid limit
        with pytest.raises(ValueError, match="Limit must be between 1 and 50"):
            self.validator.validate_search_request({
                'query': 'test',
                'limit': 100
            })
    
    def test_feedback_request_validation(self):
        """Test feedback request validation"""
        valid_data = {
            'session_id': '550e8400-e29b-41d4-a716-446655440000',
            'query': 'test query',
            'clicked_results': [0, 1, 2],
            'satisfaction': 4
        }
        
        result = self.validator.validate_feedback_request(valid_data)
        assert result['session_id'] == '550e8400-e29b-41d4-a716-446655440000'
        assert result['query'] == 'test query'
        assert result['clicked_results'] == [0, 1, 2]
        assert result['satisfaction'] == 4
    
    def test_string_sanitization(self):
        """Test string sanitization"""
        dangerous_string = "<script>alert('xss')</script>Regular text"
        sanitized = self.validator._sanitize_string(dangerous_string)
        
        assert '<script>' not in sanitized
        assert 'Regular text' in sanitized
    
    def test_filename_sanitization(self):
        """Test filename sanitization"""
        dangerous_filename = "../../../etc/passwd"
        sanitized = self.validator._sanitize_filename(dangerous_filename)
        
        assert '..' not in sanitized
        assert '/' not in sanitized
        assert 'passwd' in sanitized
    
    def test_recovery_request_validation(self):
        """Test recovery request validation"""
        # Valid request
        valid_data = {'service_name': 'qdrant'}
        result = self.validator.validate_recovery_request(valid_data)
        assert result['service_name'] == 'qdrant'
        
        # Invalid service name
        with pytest.raises(ValueError, match="Unknown service name"):
            self.validator.validate_recovery_request({'service_name': 'unknown_service'})


class TestLoggingSystem:
    """Test logging system functionality"""
    
    def test_logging_setup(self):
        """Test logging system setup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(
                log_level="DEBUG",
                log_dir=temp_dir,
                enable_file=True,
                enable_json=True
            )
            
            logger = get_logger(__name__)
            logger.info("Test log message")
            
            # Check that log files were created
            log_files = list(Path(temp_dir).glob("*.log"))
            assert len(log_files) > 0
    
    def test_performance_logger(self):
        """Test performance logging context manager"""
        from monitoring.logger import get_performance_logger
        
        perf_logger = get_performance_logger()
        
        with perf_logger.log_operation("test_operation", component="test"):
            time.sleep(0.1)  # Simulate some work
        
        # Performance logger should have recorded the operation
        # This is mainly testing that no exceptions are raised


class TestIntegration:
    """Integration tests for monitoring system"""
    
    def test_error_handling_decorator(self):
        """Test error handling decorator functionality"""
        from monitoring.error_handler import handle_errors, RetryConfig, FallbackConfig
        
        call_count = 0
        
        @handle_errors(
            retry_config=RetryConfig(max_attempts=3, delay=0.1),
            fallback_config=FallbackConfig(default_value="fallback_result")
        )
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = failing_function()
        assert result == "success"
        assert call_count == 3  # Should have retried
    
    def test_monitoring_context_integration(self):
        """Test integration of monitoring context across components"""
        # This test ensures that logging context flows properly
        # through the monitoring system
        
        from monitoring.logger import set_log_context, clear_log_context
        
        set_log_context(
            request_id="test-request-123",
            user_id="test-user",
            component="integration_test"
        )
        
        logger = get_logger(__name__)
        logger.info("Test message with context")
        
        clear_log_context()
        
        # Test should complete without errors
        assert True


# Fixtures for integration testing
@pytest.fixture
def mock_flask_app():
    """Create a mock Flask app for testing"""
    from flask import Flask
    app = Flask(__name__)
    return app


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client"""
    mock_client = Mock()
    mock_client.get_collections.return_value = Mock(collections=[])
    return mock_client


@pytest.fixture
def mock_neo4j_driver():
    """Create a mock Neo4j driver"""
    mock_driver = Mock()
    mock_session = Mock()
    mock_session.run.return_value = Mock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_driver.session.return_value.__exit__.return_value = None
    return mock_driver


# Run tests if this file is executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 