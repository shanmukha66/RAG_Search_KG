"""
Comprehensive logging system for RAG Search
"""

import logging
import logging.handlers
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import threading
from contextlib import contextmanager
import uuid

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread_id': threading.current_thread().ident,
            'process_id': record.process
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'session_id'):
            log_entry['session_id'] = record.session_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        if hasattr(record, 'duration'):
            log_entry['duration'] = record.duration
        if hasattr(record, 'status'):
            log_entry['status'] = record.status
        if hasattr(record, 'error_code'):
            log_entry['error_code'] = record.error_code
        if hasattr(record, 'component'):
            log_entry['component'] = record.component
        
        return json.dumps(log_entry)

class ContextFilter(logging.Filter):
    """Filter to add context information to log records"""
    
    def __init__(self):
        super().__init__()
        self.context = threading.local()
    
    def filter(self, record):
        # Add context from thread-local storage
        if hasattr(self.context, 'request_id'):
            record.request_id = self.context.request_id
        if hasattr(self.context, 'user_id'):
            record.user_id = self.context.user_id
        if hasattr(self.context, 'session_id'):
            record.session_id = self.context.session_id
        if hasattr(self.context, 'component'):
            record.component = self.context.component
        
        return True
    
    def set_context(self, **kwargs):
        """Set context for current thread"""
        for key, value in kwargs.items():
            setattr(self.context, key, value)
    
    def clear_context(self):
        """Clear context for current thread"""
        self.context = threading.local()

# Global context filter instance
context_filter = ContextFilter()

class PerformanceLogger:
    """Logger for performance metrics and timing"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    @contextmanager
    def log_operation(self, operation: str, **kwargs):
        """Context manager to log operation timing"""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Set operation context
        context_filter.set_context(
            request_id=request_id,
            operation=operation,
            **kwargs
        )
        
        self.logger.info(
            f"Starting operation: {operation}",
            extra={'operation': operation, 'status': 'started', 'request_id': request_id}
        )
        
        try:
            yield request_id
            duration = time.time() - start_time
            self.logger.info(
                f"Operation completed: {operation}",
                extra={
                    'operation': operation,
                    'status': 'completed',
                    'duration': duration,
                    'request_id': request_id
                }
            )
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                f"Operation failed: {operation}",
                extra={
                    'operation': operation,
                    'status': 'failed',
                    'duration': duration,
                    'error': str(e),
                    'request_id': request_id
                },
                exc_info=True
            )
            raise
        finally:
            context_filter.clear_context()

def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    enable_console: bool = True,
    enable_file: bool = True,
    enable_json: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """
    Setup comprehensive logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        enable_console: Enable console logging
        enable_file: Enable file logging
        enable_json: Use JSON formatting
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
    """
    
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Add context filter to root logger
    root_logger.addFilter(context_filter)
    
    # Setup formatters
    if enable_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        root_logger.addHandler(console_handler)
    
    # File handlers
    if enable_file:
        # Main application log
        file_handler = logging.handlers.RotatingFileHandler(
            log_path / "rag_search.log",
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        
        # Error log (only errors and above)
        error_handler = logging.handlers.RotatingFileHandler(
            log_path / "error.log",
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)
        
        # Performance log
        perf_handler = logging.handlers.RotatingFileHandler(
            log_path / "performance.log",
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        perf_handler.setFormatter(formatter)
        
        # Create performance logger
        perf_logger = logging.getLogger('performance')
        perf_logger.addHandler(perf_handler)
        perf_logger.setLevel(logging.INFO)
        perf_logger.propagate = False  # Don't propagate to root logger
    
    # Security/audit log
    security_handler = logging.handlers.RotatingFileHandler(
        log_path / "security.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    security_handler.setFormatter(formatter)
    
    security_logger = logging.getLogger('security')
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.INFO)
    security_logger.propagate = False
    
    logging.info("Logging system initialized")

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

def get_performance_logger() -> PerformanceLogger:
    """Get performance logger instance"""
    logger = logging.getLogger('performance')
    return PerformanceLogger(logger)

def get_security_logger() -> logging.Logger:
    """Get security logger instance"""
    return logging.getLogger('security')

def set_log_context(**kwargs):
    """Set logging context for current thread"""
    context_filter.set_context(**kwargs)

def clear_log_context():
    """Clear logging context for current thread"""
    context_filter.clear_context()

# Convenience functions for common logging patterns
def log_api_request(logger: logging.Logger, method: str, path: str, user_id: str = None, **kwargs):
    """Log API request"""
    logger.info(
        f"API Request: {method} {path}",
        extra={
            'component': 'api',
            'http_method': method,
            'path': path,
            'user_id': user_id,
            **kwargs
        }
    )

def log_database_operation(logger: logging.Logger, operation: str, table: str, duration: float = None, **kwargs):
    """Log database operation"""
    logger.info(
        f"Database {operation}: {table}",
        extra={
            'component': 'database',
            'db_operation': operation,
            'table': table,
            'duration': duration,
            **kwargs
        }
    )

def log_search_operation(logger: logging.Logger, query: str, results_count: int, duration: float = None, **kwargs):
    """Log search operation"""
    logger.info(
        f"Search executed: {results_count} results",
        extra={
            'component': 'search',
            'query': query,
            'results_count': results_count,
            'duration': duration,
            **kwargs
        }
    )

def log_error_with_context(logger: logging.Logger, error: Exception, operation: str = None, **kwargs):
    """Log error with full context"""
    logger.error(
        f"Error in {operation or 'operation'}: {str(error)}",
        extra={
            'error_type': type(error).__name__,
            'error_message': str(error),
            'operation': operation,
            **kwargs
        },
        exc_info=True
    ) 