#!/usr/bin/env python3
"""
Demonstration of RAG Search Monitoring and Error Handling System
Phase 6: Error Handling and Monitoring
"""

import time
import asyncio
import json
from pathlib import Path
import random

# Import monitoring components
from monitoring import (
    setup_logging, get_logger, get_performance_logger,
    ErrorHandler, handle_errors, RetryConfig, FallbackConfig,
    HealthChecker, SystemStateRecovery, RecoveryPlan, RecoveryAction,
    MetricsCollector, set_log_context, log_api_request, log_error_with_context
)

def setup_demo_environment():
    """Setup the demonstration environment"""
    print("🔧 Setting up monitoring demonstration environment...")
    
    # Initialize logging
    setup_logging(
        log_level="INFO",
        log_dir="demo_logs",
        enable_console=True,
        enable_file=True,
        enable_json=False  # Use human-readable format for demo
    )
    
    # Create demo directories
    Path("demo_logs").mkdir(exist_ok=True)
    Path("demo_state").mkdir(exist_ok=True)
    
    print("✅ Monitoring environment initialized!")


def demo_error_handling():
    """Demonstrate error handling capabilities"""
    print("\n📋 DEMO: Error Handling and Recovery")
    print("=" * 50)
    
    logger = get_logger(__name__)
    
    # Example 1: Retry with exponential backoff
    print("1. Testing retry mechanism with exponential backoff...")
    
    attempt_count = 0
    
    @handle_errors(
        retry_config=RetryConfig(max_attempts=3, delay=1.0, backoff_factor=2.0),
        record_error=True
    )
    def flaky_service():
        nonlocal attempt_count
        attempt_count += 1
        print(f"   Attempt {attempt_count}")
        if attempt_count < 3:
            raise ConnectionError("Service temporarily unavailable")
        return "Service restored!"
    
    try:
        result = flaky_service()
        print(f"   ✅ Success: {result}")
    except Exception as e:
        print(f"   ❌ Failed after retries: {e}")
    
    # Example 2: Fallback mechanism
    print("\n2. Testing fallback mechanism...")
    
    @handle_errors(
        fallback_config=FallbackConfig(
            default_value="Fallback response: Service unavailable",
            fallback_message="Using fallback"
        ),
        suppress_exceptions=True
    )
    def unreliable_service():
        raise TimeoutError("Service timeout")
    
    result = unreliable_service()
    print(f"   ✅ Fallback result: {result}")
    
    # Example 3: Error classification
    print("\n3. Testing error classification...")
    
    from monitoring.error_handler import error_handler
    
    test_errors = [
        ValueError("Invalid input data"),
        ConnectionError("Database connection failed"),
        TimeoutError("Request timed out"),
        PermissionError("Unauthorized access")
    ]
    
    for error in test_errors:
        error_details = error_handler.record_error(error, context={'demo': True})
        print(f"   {error.__class__.__name__}: {error_details.category.value} severity: {error_details.severity.value}")


def demo_health_monitoring():
    """Demonstrate health monitoring capabilities"""
    print("\n🏥 DEMO: Health Monitoring")
    print("=" * 50)
    
    health_checker = HealthChecker()
    
    # Register mock health checks
    print("1. Registering health checks...")
    
    def mock_database_check():
        # Simulate database health check
        return random.choice([True, True, False])  # 2/3 chance of success
    
    def mock_cache_check():
        return True  # Always healthy
    
    def mock_external_api_check():
        return random.choice([True, False])  # 50/50 chance
    
    health_checker.register_check("database", mock_database_check, critical=True)
    health_checker.register_check("cache", mock_cache_check, critical=False)
    health_checker.register_check("external_api", mock_external_api_check, critical=False)
    
    print("   ✅ Health checks registered")
    
    # Run health checks
    print("\n2. Running health checks...")
    
    results = health_checker.run_all_checks()
    for name, result in results.items():
        if hasattr(result, 'status'):
            status_emoji = "✅" if result.status.value == "healthy" else "⚠️" if result.status.value == "degraded" else "❌"
            print(f"   {status_emoji} {name}: {result.status.value} - {result.message}")
        else:
            # Handle boolean result
            status_emoji = "✅" if result else "❌"
            print(f"   {status_emoji} {name}: {'healthy' if result else 'unhealthy'}")
    
    # Get overall status
    try:
        overall_status, message = health_checker.get_overall_status()
        if hasattr(overall_status, 'value'):
            status_emoji = "✅" if overall_status.value == "healthy" else "⚠️" if overall_status.value == "degraded" else "❌"
            print(f"\n   {status_emoji} Overall System Status: {overall_status.value}")
        else:
            status_emoji = "✅" if overall_status else "❌"
            print(f"\n   {status_emoji} Overall System Status: {'healthy' if overall_status else 'unhealthy'}")
        print(f"   Message: {message}")
    except Exception as e:
        print(f"\n   ❌ Unable to get overall status: {e}")


def demo_metrics_collection():
    """Demonstrate metrics collection and analysis"""
    print("\n📊 DEMO: Metrics Collection")
    print("=" * 50)
    
    metrics = MetricsCollector()
    
    # Simulate various operations
    print("1. Simulating application metrics...")
    
    # Simulate HTTP requests
    for i in range(10):
        method = random.choice(['GET', 'POST'])
        path = random.choice(['/search', '/health', '/metrics'])
        status = random.choice([200, 200, 200, 404, 500])  # Mostly successful
        duration = random.uniform(0.1, 2.0)
        
        metrics.record_request(method, path, status, duration)
    
    # Simulate search operations
    for i in range(5):
        query = f"test query {i}"
        results_count = random.randint(0, 10)
        duration = random.uniform(0.5, 3.0)
        
        metrics.record_search_metrics(query, results_count, duration, 'advanced')
    
    # Simulate database operations
    for i in range(8):
        operation = random.choice(['SELECT', 'INSERT', 'UPDATE'])
        table = random.choice(['documents', 'users', 'sessions'])
        duration = random.uniform(0.01, 0.5)
        success = random.choice([True, True, True, False])  # Mostly successful
        
        metrics.record_database_metrics(operation, table, duration, success)
    
    print("   ✅ Simulated 23 operations")
    
    # Display metrics summary
    print("\n2. Metrics Summary:")
    
    health_metrics = metrics.get_system_health_metrics()
    print(f"   📈 Total Requests: {health_metrics['requests']['total']}")
    print(f"   ❌ Failed Requests: {health_metrics['requests']['failed']}")
    print(f"   ⚡ Avg Response Time: {health_metrics['requests']['avg_response_time_ms']}ms")
    
    # Show recent metric summaries
    summaries = metrics.get_all_metrics_summary(time_window=60)
    if summaries:
        print("\n3. Recent Metric Summaries:")
        for name, summary in list(summaries.items())[:3]:  # Show first 3
            print(f"   📊 {name}:")
            print(f"      Count: {summary.count}, Avg: {summary.avg:.3f}, 95th%: {summary.percentile_95:.3f}")


def demo_system_recovery():
    """Demonstrate system state recovery"""
    print("\n🔄 DEMO: System State Recovery")
    print("=" * 50)
    
    recovery = SystemStateRecovery(state_dir="demo_state")
    
    # Register mock services
    print("1. Registering services for recovery...")
    
    service_health = {"database": True, "cache": True, "search": True}
    
    def create_health_check(service_name):
        def health_check():
            return service_health.get(service_name, False)
        return health_check
    
    # Register services with recovery plans
    for service_name in ["database", "cache", "search"]:
        plan = RecoveryPlan(
            service_name=service_name,
            actions=[RecoveryAction.RESET_CONNECTION, RecoveryAction.RESTART_SERVICE],
            max_attempts=2,
            timeout=10.0
        )
        
        recovery.register_service(
            service_name,
            create_health_check(service_name),
            plan
        )
    
    print("   ✅ Services registered for recovery")
    
    # Simulate service failure and recovery
    print("\n2. Simulating service failure...")
    
    # Make database service unhealthy
    service_health["database"] = False
    
    # Check system status
    status = recovery.get_system_status()
    print(f"   System Health: {status['overall_health']}")
    
    # Attempt recovery
    print("\n3. Attempting service recovery...")
    
    # Simulate recovery success
    service_health["database"] = True
    
    success = recovery.recover_service("database")
    print(f"   Recovery {'successful' if success else 'failed'}")
    
    # Check final status
    final_status = recovery.get_system_status()
    print(f"   Final System Health: {final_status['overall_health']}")


def demo_performance_monitoring():
    """Demonstrate performance monitoring with context"""
    print("\n⚡ DEMO: Performance Monitoring")
    print("=" * 50)
    
    logger = get_logger(__name__)
    perf_logger = get_performance_logger()
    
    # Simulate a complex operation with nested timing
    print("1. Monitoring complex operation performance...")
    
    with perf_logger.log_operation("complex_search", component="search", user_id="demo_user"):
        print("   Starting complex search operation...")
        
        # Set logging context
        set_log_context(
            request_id="demo-req-123",
            user_id="demo_user",
            component="search"
        )
        
        # Simulate sub-operations
        with perf_logger.log_operation("query_parsing", component="nlp"):
            time.sleep(0.1)  # Simulate query parsing
            logger.info("Query parsed successfully")
        
        with perf_logger.log_operation("vector_search", component="qdrant"):
            time.sleep(0.3)  # Simulate vector search
            logger.info("Vector search completed")
        
        with perf_logger.log_operation("graph_traversal", component="neo4j"):
            time.sleep(0.2)  # Simulate graph traversal
            logger.info("Graph traversal completed")
        
        with perf_logger.log_operation("response_generation", component="openai"):
            time.sleep(0.4)  # Simulate AI response generation
            logger.info("Response generated")
    
    print("   ✅ Complex operation completed with full monitoring")
    
    # Simulate error in monitored operation
    print("\n2. Monitoring operation with error...")
    
    try:
        with perf_logger.log_operation("failing_operation", component="test"):
            time.sleep(0.1)
            raise ValueError("Simulated error for demonstration")
    except ValueError as e:
        log_error_with_context(logger, e, "failing_operation")
        print(f"   ❌ Error logged: {e}")


def demo_input_validation():
    """Demonstrate input validation"""
    print("\n🛡️ DEMO: Input Validation")
    print("=" * 50)
    
    from monitoring.input_validation import InputValidator
    
    validator = InputValidator()
    
    # Test search request validation
    print("1. Testing search request validation...")
    
    valid_requests = [
        {
            'query': 'find revenue documents',
            'session_id': '550e8400-e29b-41d4-a716-446655440000',
            'limit': 5
        }
    ]
    
    invalid_requests = [
        {'query': ''},  # Empty query
        {'query': 'x' * 1001},  # Too long
        {'query': 'test', 'session_id': 'invalid-id'},  # Invalid session ID
        {'query': 'test', 'limit': 100}  # Invalid limit
    ]
    
    for req in valid_requests:
        try:
            result = validator.validate_search_request(req)
            print(f"   ✅ Valid request processed: query='{result['query'][:20]}...'")
        except ValueError as e:
            print(f"   ❌ Unexpected validation error: {e}")
    
    for req in invalid_requests:
        try:
            validator.validate_search_request(req)
            print(f"   ❌ Invalid request incorrectly accepted: {req}")
        except ValueError as e:
            print(f"   ✅ Invalid request rejected: {str(e)[:50]}...")
    
    # Test string sanitization
    print("\n2. Testing string sanitization...")
    
    dangerous_inputs = [
        "<script>alert('xss')</script>Normal text",
        "Text with\x00null\x01bytes",
        "Text    with     excessive     whitespace"
    ]
    
    for dangerous_input in dangerous_inputs:
        sanitized = validator._sanitize_string(dangerous_input)
        print(f"   🧼 Sanitized: '{dangerous_input[:30]}...' -> '{sanitized[:30]}...'")


def create_summary_report():
    """Create a comprehensive summary report"""
    print("\n📋 MONITORING SYSTEM SUMMARY")
    print("=" * 60)
    
    # Error statistics
    from monitoring.error_handler import error_handler
    error_stats = error_handler.get_error_stats()
    
    print(f"📊 Error Statistics:")
    print(f"   Total Errors: {error_stats['total_errors']}")
    print(f"   By Category: {dict(error_stats['errors_by_category'])}")
    print(f"   By Severity: {dict(error_stats['errors_by_severity'])}")
    
    # Logs created
    log_dir = Path("demo_logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        print(f"\n📁 Log Files Created: {len(log_files)}")
        for log_file in log_files:
            size_kb = log_file.stat().st_size / 1024
            print(f"   {log_file.name}: {size_kb:.1f} KB")
    
    # State backup
    state_dir = Path("demo_state")
    if state_dir.exists():
        state_files = list(state_dir.glob("*.json"))
        print(f"\n💾 State Backup Files: {len(state_files)}")
    
    print(f"\n✅ Monitoring System Features Demonstrated:")
    features = [
        "Comprehensive error handling with retry and fallback",
        "Health monitoring with critical/non-critical classification",
        "Metrics collection and performance analysis",
        "System state recovery and service management",
        "Structured logging with context tracking",
        "Input validation and sanitization",
        "Performance monitoring with nested operations",
        "Automatic error classification and recording"
    ]
    
    for i, feature in enumerate(features, 1):
        print(f"   {i}. {feature}")


def main():
    """Run the complete monitoring system demonstration"""
    print("🚀 RAG Search Monitoring System Demonstration")
    print("Phase 6: Error Handling and Monitoring")
    print("=" * 60)
    
    try:
        # Setup
        setup_demo_environment()
        
        # Run demonstrations
        demo_error_handling()
        demo_health_monitoring()
        demo_metrics_collection()
        demo_system_recovery()
        demo_performance_monitoring()
        demo_input_validation()
        
        # Summary
        create_summary_report()
        
        print(f"\n🎉 Monitoring system demonstration completed successfully!")
        print(f"💡 Check the 'demo_logs' directory for generated log files")
        print(f"💡 Check the 'demo_state' directory for state backup files")
        
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 