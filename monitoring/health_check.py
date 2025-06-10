"""
Health check and system monitoring
"""

import time
import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor
import psutil
import requests
from pathlib import Path

class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component: str
    status: HealthStatus
    message: str
    timestamp: float
    response_time: float
    details: Dict[str, Any] = None

class HealthChecker:
    """Comprehensive health checking system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.health_checks = {}
        self.health_history = {}
        self.last_status = {}  # Track last status to only log changes
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_usage_percent': 90.0,
            'response_time_seconds': 5.0
        }
        self.check_interval = 60  # seconds - increased to reduce noise
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def register_check(
        self,
        name: str,
        check_func: Callable,
        critical: bool = True,
        timeout: float = 10.0
    ):
        """Register a health check function"""
        self.health_checks[name] = {
            'func': check_func,
            'critical': critical,
            'timeout': timeout,
            'last_result': None
        }
        self.health_history[name] = []
    
    def check_system_resources(self) -> HealthCheckResult:
        """Check system resource usage"""
        start_time = time.time()
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Determine status
            status = HealthStatus.HEALTHY
            issues = []
            
            if cpu_percent > self.thresholds['cpu_percent']:
                status = HealthStatus.DEGRADED
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if memory_percent > self.thresholds['memory_percent']:
                status = HealthStatus.DEGRADED
                issues.append(f"High memory usage: {memory_percent:.1f}%")
            
            if disk_percent > self.thresholds['disk_usage_percent']:
                status = HealthStatus.UNHEALTHY
                issues.append(f"High disk usage: {disk_percent:.1f}%")
            
            message = "System resources normal" if not issues else f"Issues: {'; '.join(issues)}"
            
            return HealthCheckResult(
                component="system_resources",
                status=status,
                message=message,
                timestamp=time.time(),
                response_time=time.time() - start_time,
                details={
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'disk_percent': disk_percent,
                    'memory_available_gb': memory.available / (1024**3),
                    'disk_free_gb': disk.free / (1024**3)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                component="system_resources",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check system resources: {str(e)}",
                timestamp=time.time(),
                response_time=time.time() - start_time
            )
    
    def check_database_connection(self, db_driver) -> HealthCheckResult:
        """Check database connectivity"""
        start_time = time.time()
        
        try:
            # Try to execute a simple query
            with db_driver.session() as session:
                result = session.run("RETURN 1 as test")
                test_value = result.single()["test"]
                
                if test_value == 1:
                    return HealthCheckResult(
                        component="neo4j_database",
                        status=HealthStatus.HEALTHY,
                        message="Database connection successful",
                        timestamp=time.time(),
                        response_time=time.time() - start_time
                    )
                else:
                    return HealthCheckResult(
                        component="neo4j_database",
                        status=HealthStatus.UNHEALTHY,
                        message="Database query returned unexpected result",
                        timestamp=time.time(),
                        response_time=time.time() - start_time
                    )
                    
        except Exception as e:
            return HealthCheckResult(
                component="neo4j_database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                timestamp=time.time(),
                response_time=time.time() - start_time
            )
    
    def check_vector_database(self, qdrant_client) -> HealthCheckResult:
        """Check Qdrant vector database"""
        start_time = time.time()
        
        try:
            # Check if Qdrant is responsive
            collections = qdrant_client.get_collections()
            
            return HealthCheckResult(
                component="qdrant_database",
                status=HealthStatus.HEALTHY,
                message="Vector database connection successful",
                timestamp=time.time(),
                response_time=time.time() - start_time,
                details={
                    'collections_count': len(collections.collections),
                    'collections': [col.name for col in collections.collections]
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                component="qdrant_database",
                status=HealthStatus.UNHEALTHY,
                message=f"Vector database connection failed: {str(e)}",
                timestamp=time.time(),
                response_time=time.time() - start_time
            )
    
    def check_external_api(self, url: str, timeout: float = 5.0) -> HealthCheckResult:
        """Check external API availability"""
        start_time = time.time()
        
        try:
            response = requests.get(url, timeout=timeout)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                status = HealthStatus.HEALTHY
                message = "API endpoint accessible"
            elif response.status_code < 500:
                status = HealthStatus.DEGRADED
                message = f"API returned status {response.status_code}"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"API error: status {response.status_code}"
            
            return HealthCheckResult(
                component=f"external_api_{url}",
                status=status,
                message=message,
                timestamp=time.time(),
                response_time=response_time,
                details={
                    'status_code': response.status_code,
                    'url': url
                }
            )
            
        except requests.exceptions.Timeout:
            return HealthCheckResult(
                component=f"external_api_{url}",
                status=HealthStatus.UNHEALTHY,
                message="API request timed out",
                timestamp=time.time(),
                response_time=time.time() - start_time
            )
        except Exception as e:
            return HealthCheckResult(
                component=f"external_api_{url}",
                status=HealthStatus.UNHEALTHY,
                message=f"API check failed: {str(e)}",
                timestamp=time.time(),
                response_time=time.time() - start_time
            )
    
    def check_log_files(self, log_dir: str = "logs") -> HealthCheckResult:
        """Check log file accessibility and disk usage"""
        start_time = time.time()
        
        try:
            log_path = Path(log_dir)
            
            if not log_path.exists():
                return HealthCheckResult(
                    component="log_files",
                    status=HealthStatus.DEGRADED,
                    message="Log directory does not exist",
                    timestamp=time.time(),
                    response_time=time.time() - start_time
                )
            
            # Check if we can write to log directory
            test_file = log_path / "health_check_test.tmp"
            try:
                test_file.write_text("test")
                test_file.unlink()
                write_access = True
            except:
                write_access = False
            
            # Calculate log directory size
            total_size = 0
            file_count = 0
            for file_path in log_path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
            
            size_mb = total_size / (1024 * 1024)
            
            # Determine status
            if not write_access:
                status = HealthStatus.UNHEALTHY
                message = "Cannot write to log directory"
            elif size_mb > 1000:  # 1GB
                status = HealthStatus.DEGRADED
                message = f"Log directory large: {size_mb:.1f} MB"
            else:
                status = HealthStatus.HEALTHY
                message = "Log files accessible"
            
            return HealthCheckResult(
                component="log_files",
                status=status,
                message=message,
                timestamp=time.time(),
                response_time=time.time() - start_time,
                details={
                    'log_dir': str(log_path),
                    'write_access': write_access,
                    'total_size_mb': size_mb,
                    'file_count': file_count
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                component="log_files",
                status=HealthStatus.UNHEALTHY,
                message=f"Log file check failed: {str(e)}",
                timestamp=time.time(),
                response_time=time.time() - start_time
            )
    
    def run_single_check(self, name: str) -> HealthCheckResult:
        """Run a single health check"""
        if name not in self.health_checks:
            return HealthCheckResult(
                component=name,
                status=HealthStatus.UNKNOWN,
                message="Health check not registered",
                timestamp=time.time(),
                response_time=0.0
            )
        
        check_config = self.health_checks[name]
        start_time = time.time()
        
        try:
            # Run check with timeout
            future = self.executor.submit(check_config['func'])
            result = future.result(timeout=check_config['timeout'])
            
            # Store result
            self.health_checks[name]['last_result'] = result
            self.health_history[name].append(result)
            
            # Keep only recent history (last 100 checks)
            if len(self.health_history[name]) > 100:
                self.health_history[name] = self.health_history[name][-100:]
            
            return result
            
        except Exception as e:
            result = HealthCheckResult(
                component=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                timestamp=time.time(),
                response_time=time.time() - start_time
            )
            
            self.health_checks[name]['last_result'] = result
            self.health_history[name].append(result)
            
            return result
    
    def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks"""
        results = {}
        
        # Run system resource check by default
        results['system_resources'] = self.check_system_resources()
        
        # Run registered checks
        for name in self.health_checks:
            results[name] = self.run_single_check(name)
        
        return results
    
    def get_overall_status(self) -> tuple[HealthStatus, str]:
        """Get overall system health status"""
        all_results = self.run_all_checks()
        
        critical_unhealthy = []
        critical_degraded = []
        non_critical_issues = []
        
        for name, result in all_results.items():
            is_critical = self.health_checks.get(name, {}).get('critical', True)
            
            if result.status == HealthStatus.UNHEALTHY:
                if is_critical:
                    critical_unhealthy.append(name)
                else:
                    non_critical_issues.append(f"{name} unhealthy")
            elif result.status == HealthStatus.DEGRADED:
                if is_critical:
                    critical_degraded.append(name)
                else:
                    non_critical_issues.append(f"{name} degraded")
        
        # Determine overall status
        if critical_unhealthy:
            status = HealthStatus.UNHEALTHY
            message = f"Critical components unhealthy: {', '.join(critical_unhealthy)}"
        elif critical_degraded:
            status = HealthStatus.DEGRADED
            message = f"Critical components degraded: {', '.join(critical_degraded)}"
        elif non_critical_issues:
            status = HealthStatus.DEGRADED
            message = f"Non-critical issues: {', '.join(non_critical_issues)}"
        else:
            status = HealthStatus.HEALTHY
            message = "All systems operational"
        
        return status, message
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary"""
        all_results = self.run_all_checks()
        overall_status, overall_message = self.get_overall_status()
        
        return {
            'overall_status': overall_status.value,
            'overall_message': overall_message,
            'timestamp': time.time(),
            'components': {
                name: {
                    'status': result.status.value,
                    'message': result.message,
                    'response_time': result.response_time,
                    'timestamp': result.timestamp,
                    'details': result.details
                }
                for name, result in all_results.items()
            },
            'statistics': {
                'total_components': len(all_results),
                'healthy_count': sum(1 for r in all_results.values() if r.status == HealthStatus.HEALTHY),
                'degraded_count': sum(1 for r in all_results.values() if r.status == HealthStatus.DEGRADED),
                'unhealthy_count': sum(1 for r in all_results.values() if r.status == HealthStatus.UNHEALTHY)
            }
        }
    
    def start_monitoring(self):
        """Start continuous health monitoring"""
        self.running = True
        
        def monitor_loop():
            while self.running:
                try:
                    results = self.run_all_checks()
                    
                    # Only log status changes or errors
                    for name, result in results.items():
                        last_status = self.last_status.get(name)
                        current_status = result.status.value
                        
                        # Log if status changed or if there's an issue
                        if (last_status != current_status or 
                            result.status in [HealthStatus.UNHEALTHY, HealthStatus.DEGRADED]):
                            
                            if result.status == HealthStatus.UNHEALTHY:
                                self.logger.error(f"Health check FAILED - {name}: {result.message}")
                            elif result.status == HealthStatus.DEGRADED:
                                self.logger.warning(f"Health check DEGRADED - {name}: {result.message}")
                            elif last_status and last_status != current_status:
                                self.logger.info(f"Health check RECOVERED - {name}: {result.message}")
                        
                        self.last_status[name] = current_status
                    
                    time.sleep(self.check_interval)
                except Exception as e:
                    self.logger.error(f"Error in health monitoring loop: {e}")
                    time.sleep(self.check_interval)
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        self.logger.debug("Health monitoring started")
    
    def stop_monitoring(self):
        """Stop continuous health monitoring"""
        self.running = False
        self.logger.info("Health monitoring stopped")
    
    def get_component_history(self, component: str, limit: int = 50) -> List[HealthCheckResult]:
        """Get health check history for a specific component"""
        if component not in self.health_history:
            return []
        
        return self.health_history[component][-limit:] 