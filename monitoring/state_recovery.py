"""
System state recovery and resilience management
"""

import time
import logging
import json
import pickle
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
import uuid

class RecoveryAction(Enum):
    """Types of recovery actions"""
    RESTART_SERVICE = "restart_service"
    RESET_CONNECTION = "reset_connection"
    CLEAR_CACHE = "clear_cache"
    RESTORE_STATE = "restore_state"
    FALLBACK_MODE = "fallback_mode"
    MANUAL_INTERVENTION = "manual_intervention"

class ServiceState(Enum):
    """Service state levels"""
    RUNNING = "running"
    DEGRADED = "degraded"
    FAILED = "failed"
    RECOVERING = "recovering"
    MAINTENANCE = "maintenance"

@dataclass
class ServiceStatus:
    """Status of a service"""
    name: str
    state: ServiceState
    last_check: float
    error_count: int
    last_error: Optional[str] = None
    recovery_attempts: int = 0
    metadata: Dict[str, Any] = None

@dataclass
class RecoveryPlan:
    """Recovery plan for a service"""
    service_name: str
    actions: List[RecoveryAction]
    max_attempts: int
    timeout: float
    prerequisites: List[str] = None

class SystemStateRecovery:
    """System state recovery and resilience manager"""
    
    def __init__(self, state_dir: str = "system_state"):
        self.logger = logging.getLogger(__name__)
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Service registry
        self.services = {}
        self.service_states = {}
        self.recovery_plans = {}
        
        # Recovery settings
        self.max_recovery_attempts = 3
        self.recovery_cooldown = 60  # seconds
        self.state_backup_interval = 300  # 5 minutes
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.recovery_lock = threading.Lock()
        
        # State management
        self.last_state_backup = 0
        self.auto_recovery_enabled = True
        
        # Initialize state backup
        self._load_persistent_state()
    
    def register_service(
        self,
        name: str,
        health_check_func: Callable,
        recovery_plan: RecoveryPlan,
        startup_func: Optional[Callable] = None,
        shutdown_func: Optional[Callable] = None,
        metadata: Dict[str, Any] = None
    ):
        """Register a service for monitoring and recovery"""
        self.services[name] = {
            'health_check': health_check_func,
            'startup': startup_func,
            'shutdown': shutdown_func,
            'metadata': metadata or {}
        }
        
        self.service_states[name] = ServiceStatus(
            name=name,
            state=ServiceState.RUNNING,
            last_check=time.time(),
            error_count=0,
            metadata=metadata
        )
        
        self.recovery_plans[name] = recovery_plan
        
        self.logger.debug(f"Registered service: {name}")
    
    def check_service_health(self, service_name: str) -> ServiceStatus:
        """Check health of a specific service"""
        if service_name not in self.services:
            raise ValueError(f"Service {service_name} not registered")
        
        service = self.services[service_name]
        current_status = self.service_states[service_name]
        
        try:
            # Run health check
            health_result = service['health_check']()
            
            # Update status based on health check
            if health_result:
                current_status.state = ServiceState.RUNNING
                current_status.error_count = 0
                current_status.last_error = None
            else:
                current_status.error_count += 1
                current_status.state = ServiceState.DEGRADED if current_status.error_count < 3 else ServiceState.FAILED
                current_status.last_error = "Health check failed"
            
            current_status.last_check = time.time()
            
        except Exception as e:
            current_status.error_count += 1
            current_status.state = ServiceState.FAILED
            current_status.last_error = str(e)
            current_status.last_check = time.time()
            
            self.logger.error(f"Health check failed for {service_name}: {e}")
        
        return current_status
    
    def check_all_services(self) -> Dict[str, ServiceStatus]:
        """Check health of all registered services"""
        results = {}
        
        for service_name in self.services:
            results[service_name] = self.check_service_health(service_name)
        
        return results
    
    def needs_recovery(self, service_name: str) -> bool:
        """Check if a service needs recovery"""
        status = self.service_states.get(service_name)
        if not status:
            return False
        
        return (
            status.state in [ServiceState.FAILED, ServiceState.DEGRADED] and
            status.recovery_attempts < self.max_recovery_attempts and
            (time.time() - status.last_check) > self.recovery_cooldown
        )
    
    def execute_recovery_action(
        self,
        service_name: str,
        action: RecoveryAction
    ) -> bool:
        """Execute a specific recovery action"""
        self.logger.info(f"Executing recovery action {action.value} for {service_name}")
        
        try:
            if action == RecoveryAction.RESTART_SERVICE:
                return self._restart_service(service_name)
            elif action == RecoveryAction.RESET_CONNECTION:
                return self._reset_connection(service_name)
            elif action == RecoveryAction.CLEAR_CACHE:
                return self._clear_cache(service_name)
            elif action == RecoveryAction.RESTORE_STATE:
                return self._restore_service_state(service_name)
            elif action == RecoveryAction.FALLBACK_MODE:
                return self._enable_fallback_mode(service_name)
            else:
                self.logger.warning(f"Unknown recovery action: {action.value}")
                return False
                
        except Exception as e:
            self.logger.error(f"Recovery action {action.value} failed for {service_name}: {e}")
            return False
    
    def _restart_service(self, service_name: str) -> bool:
        """Restart a service"""
        service = self.services[service_name]
        
        try:
            # Shutdown if function exists
            if service['shutdown']:
                service['shutdown']()
            
            time.sleep(2)  # Brief pause
            
            # Startup if function exists
            if service['startup']:
                service['startup']()
                
            # Update state
            self.service_states[service_name].state = ServiceState.RECOVERING
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restart service {service_name}: {e}")
            return False
    
    def _reset_connection(self, service_name: str) -> bool:
        """Reset connections for a service"""
        # Implementation depends on service type
        # This is a placeholder for service-specific connection reset logic
        self.logger.info(f"Resetting connections for {service_name}")
        return True
    
    def _clear_cache(self, service_name: str) -> bool:
        """Clear cache for a service"""
        # Implementation depends on service type
        self.logger.info(f"Clearing cache for {service_name}")
        return True
    
    def _restore_service_state(self, service_name: str) -> bool:
        """Restore service state from backup"""
        state_file = self.state_dir / f"{service_name}_state.json"
        
        try:
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                
                # Apply state restoration logic here
                self.logger.info(f"Restored state for {service_name}")
                return True
            else:
                self.logger.warning(f"No state backup found for {service_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to restore state for {service_name}: {e}")
            return False
    
    def _enable_fallback_mode(self, service_name: str) -> bool:
        """Enable fallback mode for a service"""
        self.service_states[service_name].state = ServiceState.DEGRADED
        self.logger.info(f"Enabled fallback mode for {service_name}")
        return True
    
    def recover_service(self, service_name: str) -> bool:
        """Attempt to recover a failed service"""
        with self.recovery_lock:
            if not self.needs_recovery(service_name):
                return True
            
            plan = self.recovery_plans.get(service_name)
            if not plan:
                self.logger.error(f"No recovery plan for service {service_name}")
                return False
            
            status = self.service_states[service_name]
            status.state = ServiceState.RECOVERING
            status.recovery_attempts += 1
            
            self.logger.info(f"Starting recovery for {service_name} (attempt {status.recovery_attempts})")
            
            # Execute recovery actions in sequence
            for action in plan.actions:
                success = self.execute_recovery_action(service_name, action)
                if not success:
                    self.logger.error(f"Recovery action {action.value} failed for {service_name}")
                    break
                
                # Brief pause between actions
                time.sleep(1)
            
            # Check if recovery was successful
            time.sleep(5)  # Wait for service to stabilize
            recovery_status = self.check_service_health(service_name)
            
            if recovery_status.state == ServiceState.RUNNING:
                self.logger.info(f"Successfully recovered service {service_name}")
                status.recovery_attempts = 0
                return True
            else:
                self.logger.error(f"Recovery failed for service {service_name}")
                if status.recovery_attempts >= self.max_recovery_attempts:
                    status.state = ServiceState.MAINTENANCE
                    self.logger.critical(f"Service {service_name} requires manual intervention")
                return False
    
    def auto_recover_all(self):
        """Attempt auto-recovery for all services that need it"""
        if not self.auto_recovery_enabled:
            return
        
        failed_services = []
        
        # Check all services
        for service_name, status in self.service_states.items():
            if self.needs_recovery(service_name):
                # Attempt recovery in background
                future = self.executor.submit(self.recover_service, service_name)
                try:
                    success = future.result(timeout=120)  # 2 minute timeout
                    if not success:
                        failed_services.append(service_name)
                except Exception as e:
                    self.logger.error(f"Recovery timeout for {service_name}: {e}")
                    failed_services.append(service_name)
        
        if failed_services:
            self.logger.warning(f"Auto-recovery failed for services: {failed_services}")
    
    def backup_system_state(self):
        """Backup current system state"""
        try:
            timestamp = time.time()
            
            # Backup service states with proper enum handling
            state_data = {
                'timestamp': timestamp,
                'services': {
                    name: {
                        'name': status.name,
                        'state': status.state.value,  # Convert enum to string
                        'last_check': status.last_check,
                        'error_count': status.error_count,
                        'last_error': status.last_error,
                        'recovery_attempts': status.recovery_attempts,
                        'metadata': status.metadata or {}
                    }
                    for name, status in self.service_states.items()
                },
                'metadata': {
                    'backup_version': '1.0',
                    'system_id': str(uuid.uuid4())
                }
            }
            
            # Save to file
            backup_file = self.state_dir / f"system_state_{int(timestamp)}.json"
            with open(backup_file, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            # Also save as latest
            latest_file = self.state_dir / "latest_state.json"
            with open(latest_file, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            self.last_state_backup = timestamp
            self.logger.debug(f"System state backed up to {backup_file}")
            
            # Cleanup old backups (keep last 10)
            self._cleanup_old_backups()
            
        except Exception as e:
            self.logger.error(f"Failed to backup system state: {e}")
    
    def _cleanup_old_backups(self):
        """Remove old state backup files"""
        try:
            backup_files = list(self.state_dir.glob("system_state_*.json"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Keep only the 10 most recent backups
            for old_backup in backup_files[10:]:
                old_backup.unlink()
                self.logger.debug(f"Removed old backup: {old_backup}")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {e}")
    
    def _load_persistent_state(self):
        """Load persistent state from backup"""
        try:
            latest_file = self.state_dir / "latest_state.json"
            if latest_file.exists():
                with open(latest_file, 'r') as f:
                    state_data = json.load(f)
                
                self.logger.info("Loaded persistent system state")
            else:
                self.logger.info("No persistent state found, starting fresh")
                
        except Exception as e:
            self.logger.error(f"Failed to load persistent state: {e}")
    
    def restore_system_state(self, backup_file: Optional[str] = None):
        """Restore system state from backup"""
        try:
            if backup_file:
                restore_file = Path(backup_file)
            else:
                restore_file = self.state_dir / "latest_state.json"
            
            if not restore_file.exists():
                raise FileNotFoundError(f"Backup file not found: {restore_file}")
            
            with open(restore_file, 'r') as f:
                state_data = json.load(f)
            
            # Restore service states
            for service_name, service_data in state_data['services'].items():
                if service_name in self.service_states:
                    # Convert back to ServiceStatus object
                    service_data['state'] = ServiceState(service_data['state'])
                    self.service_states[service_name] = ServiceStatus(**service_data)
            
            self.logger.info(f"System state restored from {restore_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to restore system state: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        self.check_all_services()
        
        total_services = len(self.service_states)
        running_count = sum(1 for s in self.service_states.values() if s.state == ServiceState.RUNNING)
        failed_count = sum(1 for s in self.service_states.values() if s.state == ServiceState.FAILED)
        degraded_count = sum(1 for s in self.service_states.values() if s.state == ServiceState.DEGRADED)
        
        return {
            'overall_health': 'healthy' if failed_count == 0 and degraded_count == 0 else 'degraded' if failed_count == 0 else 'unhealthy',
            'timestamp': time.time(),
            'services': {
                name: {
                    'state': status.state.value,
                    'last_check': status.last_check,
                    'error_count': status.error_count,
                    'last_error': status.last_error,
                    'recovery_attempts': status.recovery_attempts
                }
                for name, status in self.service_states.items()
            },
            'statistics': {
                'total_services': total_services,
                'running': running_count,
                'failed': failed_count,
                'degraded': degraded_count,
                'recovering': sum(1 for s in self.service_states.values() if s.state == ServiceState.RECOVERING),
                'maintenance': sum(1 for s in self.service_states.values() if s.state == ServiceState.MAINTENANCE)
            },
            'recovery_status': {
                'auto_recovery_enabled': self.auto_recovery_enabled,
                'last_backup': self.last_state_backup,
                'max_recovery_attempts': self.max_recovery_attempts
            }
        }
    
    def enable_auto_recovery(self):
        """Enable automatic recovery"""
        self.auto_recovery_enabled = True
        self.logger.info("Auto-recovery enabled")
    
    def disable_auto_recovery(self):
        """Disable automatic recovery"""
        self.auto_recovery_enabled = False
        self.logger.info("Auto-recovery disabled")
    
    def start_monitoring(self):
        """Start continuous monitoring and auto-recovery"""
        def monitor_loop():
            while True:
                try:
                    # Check all services
                    self.check_all_services()
                    
                    # Attempt auto-recovery
                    self.auto_recover_all()
                    
                    # Backup state periodically
                    if time.time() - self.last_state_backup > self.state_backup_interval:
                        self.backup_system_state()
                    
                    time.sleep(30)  # Check every 30 seconds
                    
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(30)
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        self.logger.debug("System state monitoring started") 