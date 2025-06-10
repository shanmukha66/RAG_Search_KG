"""
Metrics collection and monitoring system
"""

import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
from pathlib import Path
import statistics
import logging
from datetime import datetime, timedelta

@dataclass
class MetricPoint:
    """Single metric data point"""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass  
class MetricSummary:
    """Aggregated metric summary"""
    name: str
    count: int
    sum: float
    avg: float
    min: float
    max: float
    percentile_95: float
    timestamp: float

class MetricsCollector:
    """Comprehensive metrics collection system"""
    
    def __init__(self, retention_period: int = 3600):  # 1 hour default
        self.logger = logging.getLogger(__name__)
        self.retention_period = retention_period
        self.metrics = defaultdict(lambda: deque(maxlen=10000))  # Store up to 10k points per metric
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self.lock = threading.RLock()
        
        # System metrics
        self.system_metrics = {
            'requests_total': 0,
            'requests_failed': 0,
            'response_time_sum': 0.0,
            'errors_by_type': defaultdict(int),
            'active_sessions': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Performance tracking
        self.operation_times = defaultdict(list)
        self.error_rates = defaultdict(list)
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def record_metric(
        self,
        name: str,
        value: float,
        tags: Dict[str, str] = None,
        timestamp: float = None
    ):
        """Record a metric data point"""
        if timestamp is None:
            timestamp = time.time()
        
        metric_point = MetricPoint(
            name=name,
            value=value,
            timestamp=timestamp,
            tags=tags or {}
        )
        
        with self.lock:
            self.metrics[name].append(metric_point)
    
    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """Increment a counter metric"""
        with self.lock:
            self.counters[name] += value
            self.record_metric(f"{name}_total", self.counters[name], tags)
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric value"""
        with self.lock:
            self.gauges[name] = value
            self.record_metric(name, value, tags)
    
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a value for histogram metrics"""
        with self.lock:
            self.histograms[name].append(value)
            # Keep only recent values for histogram
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]
            self.record_metric(name, value, tags)
    
    def time_operation(self, operation_name: str, tags: Dict[str, str] = None):
        """Context manager for timing operations"""
        return OperationTimer(self, operation_name, tags)
    
    def record_request(self, method: str, path: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        tags = {
            'method': method,
            'path': path,
            'status': str(status_code)
        }
        
        with self.lock:
            self.system_metrics['requests_total'] += 1
            self.system_metrics['response_time_sum'] += duration
            
            if status_code >= 400:
                self.system_metrics['requests_failed'] += 1
        
        self.increment_counter('http_requests', tags=tags)
        self.record_histogram('http_request_duration', duration, tags)
        self.record_metric('http_response_size', 0, tags)  # Placeholder
    
    def record_error(self, error_type: str, error_message: str, component: str = None):
        """Record error metrics"""
        tags = {
            'error_type': error_type,
            'component': component or 'unknown'
        }
        
        with self.lock:
            self.system_metrics['errors_by_type'][error_type] += 1
        
        self.increment_counter('errors', tags=tags)
        self.record_metric('error_occurrence', 1, tags)
    
    def record_search_metrics(
        self,
        query: str,
        results_count: int,
        duration: float,
        search_type: str = 'standard'
    ):
        """Record search operation metrics"""
        tags = {
            'search_type': search_type,
            'results_bucket': self._bucket_results_count(results_count)
        }
        
        self.increment_counter('searches', tags=tags)
        self.record_histogram('search_duration', duration, tags)
        self.record_histogram('search_results_count', results_count, tags)
        self.record_metric('search_query_length', len(query), tags)
    
    def record_database_metrics(self, operation: str, table: str, duration: float, success: bool):
        """Record database operation metrics"""
        tags = {
            'operation': operation,
            'table': table,
            'status': 'success' if success else 'error'
        }
        
        self.increment_counter('db_operations', tags=tags)
        self.record_histogram('db_operation_duration', duration, tags)
    
    def record_cache_metrics(self, operation: str, hit: bool, key_prefix: str = None):
        """Record cache operation metrics"""
        tags = {
            'operation': operation,
            'key_prefix': key_prefix or 'unknown'
        }
        
        with self.lock:
            if hit:
                self.system_metrics['cache_hits'] += 1
            else:
                self.system_metrics['cache_misses'] += 1
        
        status = 'hit' if hit else 'miss'
        self.increment_counter(f'cache_{status}', tags=tags)
    
    def record_user_session(self, session_id: str, action: str):
        """Record user session metrics"""
        tags = {
            'action': action,
            'session_id': session_id[:8]  # Truncated for privacy
        }
        
        if action == 'start':
            with self.lock:
                self.system_metrics['active_sessions'] += 1
        elif action == 'end':
            with self.lock:
                self.system_metrics['active_sessions'] = max(0, self.system_metrics['active_sessions'] - 1)
        
        self.increment_counter('user_sessions', tags=tags)
    
    def _bucket_results_count(self, count: int) -> str:
        """Bucket results count for better aggregation"""
        if count == 0:
            return '0'
        elif count <= 5:
            return '1-5'
        elif count <= 10:
            return '6-10'
        elif count <= 50:
            return '11-50'
        else:
            return '50+'
    
    def get_metric_summary(self, name: str, time_window: int = 300) -> Optional[MetricSummary]:
        """Get summary statistics for a metric over time window"""
        if name not in self.metrics:
            return None
        
        current_time = time.time()
        cutoff_time = current_time - time_window
        
        with self.lock:
            recent_points = [
                point for point in self.metrics[name] 
                if point.timestamp >= cutoff_time
            ]
        
        if not recent_points:
            return None
        
        values = [point.value for point in recent_points]
        
        return MetricSummary(
            name=name,
            count=len(values),
            sum=sum(values),
            avg=statistics.mean(values),
            min=min(values),
            max=max(values),
            percentile_95=self._percentile(values, 95),
            timestamp=current_time
        )
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def get_all_metrics_summary(self, time_window: int = 300) -> Dict[str, MetricSummary]:
        """Get summary for all metrics"""
        summaries = {}
        
        for metric_name in self.metrics.keys():
            summary = self.get_metric_summary(metric_name, time_window)
            if summary:
                summaries[metric_name] = summary
        
        return summaries
    
    def get_system_health_metrics(self) -> Dict[str, Any]:
        """Get overall system health metrics"""
        with self.lock:
            total_requests = self.system_metrics['requests_total']
            failed_requests = self.system_metrics['requests_failed']
            response_time_sum = self.system_metrics['response_time_sum']
            
            error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
            avg_response_time = (response_time_sum / total_requests) if total_requests > 0 else 0
            cache_hit_rate = (
                self.system_metrics['cache_hits'] / 
                (self.system_metrics['cache_hits'] + self.system_metrics['cache_misses']) * 100
            ) if (self.system_metrics['cache_hits'] + self.system_metrics['cache_misses']) > 0 else 0
        
        return {
            'requests': {
                'total': total_requests,
                'failed': failed_requests,
                'error_rate_percent': round(error_rate, 2),
                'avg_response_time_ms': round(avg_response_time * 1000, 2)
            },
            'cache': {
                'hits': self.system_metrics['cache_hits'],
                'misses': self.system_metrics['cache_misses'],
                'hit_rate_percent': round(cache_hit_rate, 2)
            },
            'sessions': {
                'active': self.system_metrics['active_sessions']
            },
            'errors': dict(self.system_metrics['errors_by_type']),
            'timestamp': time.time()
        }
    
    def get_performance_report(self, time_window: int = 3600) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        current_time = time.time()
        
        # Get summaries for key metrics
        request_duration = self.get_metric_summary('http_request_duration', time_window)
        search_duration = self.get_metric_summary('search_duration', time_window)
        db_duration = self.get_metric_summary('db_operation_duration', time_window)
        
        # Calculate trends
        trends = self._calculate_trends(time_window)
        
        return {
            'report_period': {
                'start_time': current_time - time_window,
                'end_time': current_time,
                'duration_minutes': time_window / 60
            },
            'performance': {
                'http_requests': request_duration.__dict__ if request_duration else None,
                'search_operations': search_duration.__dict__ if search_duration else None,
                'database_operations': db_duration.__dict__ if db_duration else None
            },
            'trends': trends,
            'system_health': self.get_system_health_metrics(),
            'generated_at': current_time
        }
    
    def _calculate_trends(self, time_window: int) -> Dict[str, str]:
        """Calculate trends for key metrics"""
        current_time = time.time()
        half_window = time_window // 2
        
        trends = {}
        
        for metric_name in ['http_request_duration', 'search_duration', 'errors_total']:
            if metric_name in self.metrics:
                # Compare first half vs second half of time window
                first_half = [
                    p.value for p in self.metrics[metric_name]
                    if current_time - time_window <= p.timestamp < current_time - half_window
                ]
                second_half = [
                    p.value for p in self.metrics[metric_name]
                    if current_time - half_window <= p.timestamp <= current_time
                ]
                
                if first_half and second_half:
                    first_avg = statistics.mean(first_half)
                    second_avg = statistics.mean(second_half)
                    
                    if second_avg > first_avg * 1.1:
                        trends[metric_name] = 'increasing'
                    elif second_avg < first_avg * 0.9:
                        trends[metric_name] = 'decreasing'
                    else:
                        trends[metric_name] = 'stable'
                else:
                    trends[metric_name] = 'insufficient_data'
        
        return trends
    
    def export_metrics(self, filepath: str, format: str = 'json'):
        """Export metrics to file"""
        export_data = {
            'export_timestamp': time.time(),
            'system_health': self.get_system_health_metrics(),
            'metric_summaries': {},
            'raw_metrics': {}
        }
        
        # Add summaries
        for name, summary in self.get_all_metrics_summary().items():
            export_data['metric_summaries'][name] = summary.__dict__
        
        # Add recent raw data (last 1000 points per metric)
        with self.lock:
            for name, points in self.metrics.items():
                export_data['raw_metrics'][name] = [
                    {
                        'value': p.value,
                        'timestamp': p.timestamp,
                        'tags': p.tags
                    }
                    for p in list(points)[-1000:]  # Last 1000 points
                ]
        
        # Write to file
        with open(filepath, 'w') as f:
            if format.lower() == 'json':
                json.dump(export_data, f, indent=2)
            else:
                raise ValueError(f"Unsupported export format: {format}")
        
        self.logger.info(f"Metrics exported to {filepath}")
    
    def _cleanup_old_metrics(self):
        """Remove old metric data points"""
        current_time = time.time()
        cutoff_time = current_time - self.retention_period
        
        with self.lock:
            for name, points in self.metrics.items():
                # Remove old points
                while points and points[0].timestamp < cutoff_time:
                    points.popleft()
    
    def _start_cleanup_thread(self):
        """Start background thread for metric cleanup"""
        def cleanup_loop():
            while True:
                try:
                    self._cleanup_old_metrics()
                    time.sleep(300)  # Clean up every 5 minutes
                except Exception as e:
                    self.logger.error(f"Error in metrics cleanup: {e}")
                    time.sleep(300)
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
        self.logger.debug("Metrics cleanup thread started")
    
    def reset_metrics(self, metric_names: List[str] = None):
        """Reset specific metrics or all metrics"""
        with self.lock:
            if metric_names:
                for name in metric_names:
                    if name in self.metrics:
                        self.metrics[name].clear()
                    if name in self.counters:
                        self.counters[name] = 0
                    if name in self.gauges:
                        del self.gauges[name]
                    if name in self.histograms:
                        self.histograms[name].clear()
            else:
                # Reset all metrics
                self.metrics.clear()
                self.counters.clear()
                self.gauges.clear()
                self.histograms.clear()
                self.system_metrics = {
                    'requests_total': 0,
                    'requests_failed': 0,
                    'response_time_sum': 0.0,
                    'errors_by_type': defaultdict(int),
                    'active_sessions': 0,
                    'cache_hits': 0,
                    'cache_misses': 0
                }
        
        self.logger.info(f"Reset metrics: {metric_names or 'all'}")

class OperationTimer:
    """Context manager for timing operations"""
    
    def __init__(self, collector: MetricsCollector, operation_name: str, tags: Dict[str, str] = None):
        self.collector = collector
        self.operation_name = operation_name
        self.tags = tags or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.collector.record_histogram(f"{self.operation_name}_duration", duration, self.tags)
            
            # Record success/failure
            if exc_type is None:
                self.collector.increment_counter(f"{self.operation_name}_success", tags=self.tags)
            else:
                error_tags = {**self.tags, 'error_type': exc_type.__name__}
                self.collector.increment_counter(f"{self.operation_name}_error", tags=error_tags) 