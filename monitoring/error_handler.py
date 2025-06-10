"""
Comprehensive error handling and recovery system
"""

import functools
import time
import traceback
from typing import Dict, Any, Optional, Callable, Union, List
from enum import Enum
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import asyncio
from threading import Lock

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for classification"""
    VALIDATION = "validation"
    DATABASE = "database"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"

@dataclass
class ErrorDetails:
    """Detailed error information"""
    error_type: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    context: Dict[str, Any]
    timestamp: float
    stack_trace: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None

class RetryConfig:
    """Configuration for retry mechanisms"""
    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        exceptions: tuple = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.exceptions = exceptions

class FallbackConfig:
    """Configuration for fallback mechanisms"""
    def __init__(
        self,
        fallback_func: Optional[Callable] = None,
        default_value: Any = None,
        fallback_message: str = "Operation failed, using fallback"
    ):
        self.fallback_func = fallback_func
        self.default_value = default_value
        self.fallback_message = fallback_message

class ErrorHandler:
    """Centralized error handling system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_stats = {
            'total_errors': 0,
            'errors_by_category': {},
            'errors_by_severity': {},
            'recent_errors': []
        }
        self.circuit_breakers = {}
        self.lock = Lock()
        
        # Initialize error counters
        for category in ErrorCategory:
            self.error_stats['errors_by_category'][category.value] = 0
        for severity in ErrorSeverity:
            self.error_stats['errors_by_severity'][severity.value] = 0
    
    def classify_error(self, error: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify error by category and severity"""
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # Classification logic
        if 'validation' in error_msg or 'invalid' in error_msg:
            return ErrorCategory.VALIDATION, ErrorSeverity.LOW
        elif 'database' in error_msg or 'connection' in error_msg:
            return ErrorCategory.DATABASE, ErrorSeverity.HIGH
        elif 'network' in error_msg or 'timeout' in error_msg:
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
        elif 'permission' in error_msg or 'unauthorized' in error_msg:
            return ErrorCategory.AUTHORIZATION, ErrorSeverity.MEDIUM
        elif 'rate limit' in error_msg:
            return ErrorCategory.RATE_LIMIT, ErrorSeverity.MEDIUM
        elif isinstance(error, TimeoutError):
            return ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM
        elif 'memory' in error_msg or 'resource' in error_msg:
            return ErrorCategory.RESOURCE, ErrorSeverity.HIGH
        elif 'openai' in error_msg or 'api' in error_msg:
            return ErrorCategory.EXTERNAL_SERVICE, ErrorSeverity.MEDIUM
        else:
            return ErrorCategory.SYSTEM, ErrorSeverity.HIGH
    
    def record_error(
        self,
        error: Exception,
        context: Dict[str, Any] = None,
        user_id: str = None,
        session_id: str = None,
        request_id: str = None
    ) -> ErrorDetails:
        """Record and classify an error"""
        category, severity = self.classify_error(error)
        
        error_details = ErrorDetails(
            error_type=type(error).__name__,
            message=str(error),
            category=category,
            severity=severity,
            context=context or {},
            timestamp=time.time(),
            stack_trace=traceback.format_exc(),
            user_id=user_id,
            session_id=session_id,
            request_id=request_id
        )
        
        # Update statistics
        with self.lock:
            self.error_stats['total_errors'] += 1
            self.error_stats['errors_by_category'][category.value] += 1
            self.error_stats['errors_by_severity'][severity.value] += 1
            self.error_stats['recent_errors'].append(error_details)
            
            # Keep only recent errors (last 100)
            if len(self.error_stats['recent_errors']) > 100:
                self.error_stats['recent_errors'] = self.error_stats['recent_errors'][-100:]
        
        # Log error with appropriate level
        log_level = {
            ErrorSeverity.LOW: logging.WARNING,
            ErrorSeverity.MEDIUM: logging.ERROR,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }[severity]
        
        self.logger.log(
            log_level,
            f"Error recorded: {category.value} - {error_details.message}",
            extra={
                'error_category': category.value,
                'error_severity': severity.value,
                'error_type': error_details.error_type,
                'user_id': user_id,
                'session_id': session_id,
                'request_id': request_id,
                'context': context
            },
            exc_info=True
        )
        
        return error_details
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get current error statistics"""
        with self.lock:
            return self.error_stats.copy()

class CircuitBreaker:
    """Circuit breaker for external service calls"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        recovery_timeout: float = 30.0
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self.lock = Lock()
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        with self.lock:
            if self.state == 'OPEN':
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = 'HALF_OPEN'
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                if self.state == 'HALF_OPEN':
                    self.state = 'CLOSED'
                    self.failure_count = 0
                return result
                
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = 'OPEN'
                
                raise e

# Global error handler instance
error_handler = ErrorHandler()

def handle_errors(
    fallback_config: FallbackConfig = None,
    retry_config: RetryConfig = None,
    record_error: bool = True,
    suppress_exceptions: bool = False
):
    """
    Decorator for comprehensive error handling
    
    Args:
        fallback_config: Configuration for fallback behavior
        retry_config: Configuration for retry behavior
        record_error: Whether to record the error
        suppress_exceptions: Whether to suppress exceptions and return fallback
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            attempt = 0
            max_attempts = retry_config.max_attempts if retry_config else 1
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    attempt += 1
                    
                    # Record error if enabled
                    if record_error:
                        context = {
                            'function': func.__name__,
                            'attempt': attempt,
                            'max_attempts': max_attempts,
                            'args': str(args),
                            'kwargs': str(kwargs)
                        }
                        error_handler.record_error(e, context=context)
                    
                    # Check if we should retry
                    if (retry_config and 
                        attempt < max_attempts and 
                        isinstance(e, retry_config.exceptions)):
                        
                        delay = min(
                            retry_config.delay * (retry_config.backoff_factor ** (attempt - 1)),
                            retry_config.max_delay
                        )
                        time.sleep(delay)
                        continue
                    
                    # No more retries, handle fallback
                    if fallback_config:
                        if fallback_config.fallback_func:
                            try:
                                return fallback_config.fallback_func(*args, **kwargs)
                            except Exception as fallback_error:
                                if record_error:
                                    error_handler.record_error(
                                        fallback_error,
                                        context={'fallback_for': func.__name__}
                                    )
                        else:
                            return fallback_config.default_value
                    
                    # Suppress or raise exception
                    if suppress_exceptions:
                        return None
                    else:
                        raise last_exception
            
            # All retries exhausted
            if suppress_exceptions:
                return fallback_config.default_value if fallback_config else None
            else:
                raise last_exception
        
        return wrapper
    
    return decorator

async def handle_errors_async(
    fallback_config: FallbackConfig = None,
    retry_config: RetryConfig = None,
    record_error: bool = True,
    suppress_exceptions: bool = False
):
    """Async version of error handling decorator"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            attempt = 0
            max_attempts = retry_config.max_attempts if retry_config else 1
            
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    attempt += 1
                    
                    # Record error if enabled
                    if record_error:
                        context = {
                            'function': func.__name__,
                            'attempt': attempt,
                            'max_attempts': max_attempts,
                            'args': str(args),
                            'kwargs': str(kwargs)
                        }
                        error_handler.record_error(e, context=context)
                    
                    # Check if we should retry
                    if (retry_config and 
                        attempt < max_attempts and 
                        isinstance(e, retry_config.exceptions)):
                        
                        delay = min(
                            retry_config.delay * (retry_config.backoff_factor ** (attempt - 1)),
                            retry_config.max_delay
                        )
                        await asyncio.sleep(delay)
                        continue
                    
                    # No more retries, handle fallback
                    if fallback_config:
                        if fallback_config.fallback_func:
                            try:
                                if asyncio.iscoroutinefunction(fallback_config.fallback_func):
                                    return await fallback_config.fallback_func(*args, **kwargs)
                                else:
                                    return fallback_config.fallback_func(*args, **kwargs)
                            except Exception as fallback_error:
                                if record_error:
                                    error_handler.record_error(
                                        fallback_error,
                                        context={'fallback_for': func.__name__}
                                    )
                        else:
                            return fallback_config.default_value
                    
                    # Suppress or raise exception
                    if suppress_exceptions:
                        return None
                    else:
                        raise last_exception
            
            # All retries exhausted
            if suppress_exceptions:
                return fallback_config.default_value if fallback_config else None
            else:
                raise last_exception
        
        return wrapper
    
    return decorator

# Convenience functions for common error handling patterns

def safe_execute(
    func: Callable,
    default_value: Any = None,
    log_errors: bool = True,
    **kwargs
) -> Any:
    """Safely execute a function with error handling"""
    try:
        return func(**kwargs)
    except Exception as e:
        if log_errors:
            error_handler.record_error(e, context={'function': func.__name__})
        return default_value

def validate_input(
    data: Dict[str, Any],
    required_fields: List[str],
    field_types: Dict[str, type] = None
) -> Dict[str, Any]:
    """Validate input data with comprehensive error reporting"""
    errors = []
    
    # Check required fields
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # Check field types
    if field_types:
        for field, expected_type in field_types.items():
            if field in data and not isinstance(data[field], expected_type):
                errors.append(
                    f"Invalid type for field {field}: expected {expected_type.__name__}, "
                    f"got {type(data[field]).__name__}"
                )
    
    if errors:
        raise ValueError(f"Validation errors: {'; '.join(errors)}")
    
    return data

def safe_json_response(data: Any, default: Dict = None) -> Dict[str, Any]:
    """Safely create JSON response with error handling"""
    try:
        if data is None:
            return default or {'error': 'No data available'}
        
        # Ensure data is serializable
        import json
        json.dumps(data)  # Test serialization
        return data
        
    except (TypeError, ValueError) as e:
        error_handler.record_error(e, context={'data_type': type(data).__name__})
        return default or {'error': 'Data serialization failed'} 