"""
Input validation and sanitization for API requests
"""

import re
import html
import json
from typing import Dict, Any, Optional, List, Union
from flask import request
import logging
from .error_handler import validate_input

logger = logging.getLogger(__name__)

class InputValidator:
    """Comprehensive input validation for API requests"""
    
    def __init__(self):
        self.max_query_length = 1000
        self.max_session_id_length = 50
        self.allowed_file_extensions = {'.txt', '.pdf', '.doc', '.docx', '.md'}
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        
        # Regex patterns for validation
        self.patterns = {
            'session_id': re.compile(r'^[a-fA-F0-9-]{8,50}$'),
            'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            'alphanumeric': re.compile(r'^[a-zA-Z0-9\s\-_.,!?]+$'),
            'safe_string': re.compile(r'^[a-zA-Z0-9\s\-_.,!?\'"()]+$'),
            'uuid': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'),
        }
    
    def validate_search_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate search request data"""
        validated_data = {}
        
        # Validate query
        query = data.get('query', '').strip()
        if not query:
            raise ValueError("Search query is required")
        
        if len(query) > self.max_query_length:
            raise ValueError(f"Query too long. Maximum {self.max_query_length} characters allowed")
        
        # Sanitize query
        validated_data['query'] = self._sanitize_string(query)
        
        # Validate session ID (optional)
        session_id = data.get('session_id', '').strip()
        if session_id:
            if not self.patterns['uuid'].match(session_id):
                raise ValueError("Invalid session ID format")
            validated_data['session_id'] = session_id
        
        # Validate limit (optional)
        limit = data.get('limit', 5)
        try:
            limit = int(limit)
            if not (1 <= limit <= 50):
                raise ValueError("Limit must be between 1 and 50")
            validated_data['limit'] = limit
        except (ValueError, TypeError):
            raise ValueError("Invalid limit value")
        
        return validated_data
    
    def validate_feedback_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate feedback request data"""
        validated_data = {}
        
        # Validate session ID
        session_id = data.get('session_id', '').strip()
        if not session_id:
            raise ValueError("Session ID is required")
        
        if not self.patterns['uuid'].match(session_id):
            raise ValueError("Invalid session ID format")
        validated_data['session_id'] = session_id
        
        # Validate query
        query = data.get('query', '').strip()
        if not query:
            raise ValueError("Query is required")
        
        validated_data['query'] = self._sanitize_string(query)
        
        # Validate clicked results
        clicked_results = data.get('clicked_results', [])
        if not isinstance(clicked_results, list):
            raise ValueError("Clicked results must be a list")
        
        # Validate each clicked result index
        validated_clicked = []
        for index in clicked_results:
            try:
                index = int(index)
                if 0 <= index <= 100:  # Reasonable upper bound
                    validated_clicked.append(index)
            except (ValueError, TypeError):
                logger.warning(f"Invalid clicked result index: {index}")
        
        validated_data['clicked_results'] = validated_clicked
        
        # Validate satisfaction rating (optional)
        satisfaction = data.get('satisfaction')
        if satisfaction is not None:
            try:
                satisfaction = int(satisfaction)
                if not (1 <= satisfaction <= 5):
                    raise ValueError("Satisfaction rating must be between 1 and 5")
                validated_data['satisfaction'] = satisfaction
            except (ValueError, TypeError):
                raise ValueError("Invalid satisfaction rating")
        
        return validated_data
    
    def validate_file_upload(self, file) -> Dict[str, Any]:
        """Validate file upload"""
        if not file or not file.filename:
            raise ValueError("No file provided")
        
        # Check file extension
        file_ext = '.' + file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_ext not in self.allowed_file_extensions:
            raise ValueError(f"File type not allowed. Allowed types: {', '.join(self.allowed_file_extensions)}")
        
        # Check file size (if possible)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > self.max_file_size:
            raise ValueError(f"File too large. Maximum size: {self.max_file_size // (1024*1024)}MB")
        
        return {
            'filename': self._sanitize_filename(file.filename),
            'size': file_size,
            'extension': file_ext
        }
    
    def validate_recovery_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate system recovery request"""
        validated_data = {}
        
        # Validate service name
        service_name = data.get('service_name', '').strip()
        if not service_name:
            raise ValueError("Service name is required")
        
        # Only allow known service names
        allowed_services = {'qdrant', 'neo4j', 'openai', 'advanced_search'}
        if service_name not in allowed_services:
            raise ValueError(f"Unknown service name. Allowed: {', '.join(allowed_services)}")
        
        validated_data['service_name'] = service_name
        
        return validated_data
    
    def validate_metrics_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metrics request parameters"""
        validated_data = {}
        
        # Validate time window
        time_window = data.get('window', 300)
        try:
            time_window = int(time_window)
            if not (60 <= time_window <= 86400):  # 1 minute to 1 day
                raise ValueError("Time window must be between 60 and 86400 seconds")
            validated_data['window'] = time_window
        except (ValueError, TypeError):
            raise ValueError("Invalid time window value")
        
        # Validate metric names (optional)
        metric_names = data.get('metrics', [])
        if metric_names:
            if not isinstance(metric_names, list):
                raise ValueError("Metrics must be a list")
            
            validated_metrics = []
            for name in metric_names:
                if isinstance(name, str) and self.patterns['alphanumeric'].match(name):
                    validated_metrics.append(name)
            
            validated_data['metrics'] = validated_metrics
        
        return validated_data
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize string input"""
        # Remove HTML tags and entities
        text = html.escape(text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        return text
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename"""
        # Remove path components
        filename = filename.split('/')[-1].split('\\')[-1]
        
        # Remove or replace dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250] + ('.' + ext if ext else '')
        
        return filename
    
    def validate_request_headers(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Validate request headers"""
        validated_headers = {}
        
        # Validate Content-Type for POST requests
        content_type = headers.get('Content-Type', '')
        if request.method == 'POST':
            allowed_content_types = [
                'application/json',
                'application/x-www-form-urlencoded',
                'multipart/form-data'
            ]
            
            if not any(ct in content_type for ct in allowed_content_types):
                logger.warning(f"Unexpected content type: {content_type}")
        
        # Validate User-Agent (optional security check)
        user_agent = headers.get('User-Agent', '')
        if user_agent:
            # Check for common bot/scanner patterns
            suspicious_patterns = ['sqlmap', 'nikto', 'nmap', 'dirb', 'gobuster']
            if any(pattern in user_agent.lower() for pattern in suspicious_patterns):
                logger.warning(f"Suspicious User-Agent: {user_agent}")
                validated_headers['suspicious_request'] = True
        
        # Validate custom headers
        user_id = headers.get('X-User-ID', '')
        if user_id:
            if len(user_id) > 50 or not self.patterns['alphanumeric'].match(user_id):
                logger.warning(f"Invalid User-ID header: {user_id}")
            else:
                validated_headers['user_id'] = user_id
        
        return validated_headers

# Global validator instance
input_validator = InputValidator()

def validate_request(validation_type: str):
    """Decorator for request validation"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                # Get request data
                if request.method == 'POST':
                    if request.is_json:
                        data = request.get_json() or {}
                    else:
                        data = request.form.to_dict()
                else:
                    data = request.args.to_dict()
                
                # Validate headers
                header_validation = input_validator.validate_request_headers(dict(request.headers))
                
                # Check for suspicious requests
                if header_validation.get('suspicious_request'):
                    logger.warning(f"Blocking suspicious request from {request.remote_addr}")
                    from flask import jsonify
                    return jsonify({'error': 'Request blocked'}), 403
                
                # Perform specific validation
                if validation_type == 'search':
                    validated_data = input_validator.validate_search_request(data)
                elif validation_type == 'feedback':
                    validated_data = input_validator.validate_feedback_request(data)
                elif validation_type == 'recovery':
                    validated_data = input_validator.validate_recovery_request(data)
                elif validation_type == 'metrics':
                    validated_data = input_validator.validate_metrics_request(data)
                else:
                    validated_data = data
                
                # Add validated data to request context
                request.validated_data = validated_data
                request.validated_headers = header_validation
                
                return func(*args, **kwargs)
                
            except ValueError as e:
                logger.warning(f"Validation error: {e}")
                from flask import jsonify
                return jsonify({'error': f'Validation error: {str(e)}'}), 400
            except Exception as e:
                logger.error(f"Unexpected validation error: {e}")
                from flask import jsonify
                return jsonify({'error': 'Invalid request'}), 400
        
        return wrapper
    return decorator 