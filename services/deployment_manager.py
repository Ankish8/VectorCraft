#!/usr/bin/env python3
"""
Deployment and Release Management System
Blue-green deployments, canary releases, and rollback capabilities
"""

import json
import os
import subprocess
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
import hashlib
import shutil
from pathlib import Path
from database import db
from services.monitoring.system_logger import system_logger
from services.monitoring.alert_manager import alert_manager
from services.system_controller import system_controller

class DeploymentStatus(Enum):
    """Deployment status options"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"

class DeploymentStrategy(Enum):
    """Deployment strategy options"""
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    IMMEDIATE = "immediate"

class ReleaseStage(Enum):
    """Release stage options"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class DeploymentManager:
    """
    Manages deployments, releases, and rollbacks with safety mechanisms
    """
    
    def __init__(self):
        self.logger = system_logger
        self.alert_manager = alert_manager
        self._deployments = {}
        self._releases = {}
        self._lock = threading.RLock()
        self._active_deployment = None
        self._rollback_points = {}
        self._init_database()
        self._load_deployments()
        
    def _init_database(self):
        """Initialize deployment database tables"""
        try:
            with db.get_db_connection() as conn:
                # Deployments table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS deployments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        deployment_id TEXT UNIQUE NOT NULL,
                        version TEXT NOT NULL,
                        strategy TEXT NOT NULL,
                        stage TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        progress INTEGER DEFAULT 0,
                        started_by TEXT,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP,
                        rollback_point TEXT,
                        config TEXT,
                        logs TEXT,
                        metadata TEXT
                    )
                ''')
                
                # Releases table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS releases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        release_id TEXT UNIQUE NOT NULL,
                        version TEXT NOT NULL,
                        name TEXT,
                        description TEXT,
                        changelog TEXT,
                        stage TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'draft',
                        created_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        deployed_at TIMESTAMP,
                        rollback_version TEXT,
                        metadata TEXT
                    )
                ''')
                
                # Rollback points table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS rollback_points (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        point_id TEXT UNIQUE NOT NULL,
                        version TEXT NOT NULL,
                        stage TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        database_backup TEXT,
                        file_backup TEXT,
                        config_backup TEXT,
                        metadata TEXT
                    )
                ''')
                
                # Deployment logs table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS deployment_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        deployment_id TEXT NOT NULL,
                        log_level TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        component TEXT,
                        metadata TEXT
                    )
                ''')
                
                conn.commit()
                self.logger.info("Deployment database initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize deployment database: {e}")
    
    def _load_deployments(self):
        """Load active deployments from database"""
        try:
            with db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT deployment_id, version, strategy, stage, status, progress,
                           started_by, started_at, config, metadata
                    FROM deployments
                    WHERE status IN ('pending', 'running')
                    ORDER BY started_at DESC
                ''')
                
                for row in cursor.fetchall():
                    deployment_data = {
                        'deployment_id': row['deployment_id'],
                        'version': row['version'],
                        'strategy': DeploymentStrategy(row['strategy']),
                        'stage': ReleaseStage(row['stage']),
                        'status': DeploymentStatus(row['status']),
                        'progress': row['progress'],
                        'started_by': row['started_by'],
                        'started_at': row['started_at'],
                        'config': json.loads(row['config']) if row['config'] else {},
                        'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                    }
                    
                    self._deployments[row['deployment_id']] = deployment_data
                
                self.logger.info(f"Loaded {len(self._deployments)} active deployments")
        except Exception as e:
            self.logger.error(f"Failed to load deployments: {e}")
    
    def _save_deployment(self, deployment_id: str, deployment_data: Dict[str, Any]):
        """Save deployment to database"""
        try:
            with db.get_db_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO deployments
                    (deployment_id, version, strategy, stage, status, progress,
                     started_by, started_at, completed_at, config, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    deployment_id,
                    deployment_data['version'],
                    deployment_data['strategy'].value,
                    deployment_data['stage'].value,
                    deployment_data['status'].value,
                    deployment_data['progress'],
                    deployment_data['started_by'],
                    deployment_data['started_at'],
                    deployment_data.get('completed_at'),
                    json.dumps(deployment_data['config']),
                    json.dumps(deployment_data['metadata'])
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to save deployment {deployment_id}: {e}")
    
    def _log_deployment(self, deployment_id: str, level: str, message: str, component: str = None):
        """Log deployment event"""
        try:
            with db.get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO deployment_logs
                    (deployment_id, log_level, message, component)
                    VALUES (?, ?, ?, ?)
                ''', (deployment_id, level, message, component))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to log deployment event: {e}")
    
    def create_release(self, version: str, name: str = None, description: str = None,
                      changelog: str = None, stage: ReleaseStage = ReleaseStage.DEVELOPMENT,
                      user: str = None) -> Dict[str, Any]:
        """Create a new release"""
        
        release_id = f"release-{version}-{int(time.time())}"
        
        with self._lock:
            if release_id in self._releases:
                return {
                    'success': False,
                    'error': f'Release {release_id} already exists'
                }
            
            release_data = {
                'release_id': release_id,
                'version': version,
                'name': name or f'Release {version}',
                'description': description or '',
                'changelog': changelog or '',
                'stage': stage,
                'status': 'draft',
                'created_by': user,
                'created_at': datetime.now().isoformat(),
                'metadata': {}
            }
            
            self._releases[release_id] = release_data
            
            # Save to database
            try:
                with db.get_db_connection() as conn:
                    conn.execute('''
                        INSERT INTO releases
                        (release_id, version, name, description, changelog, stage, status, created_by, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        release_id,
                        version,
                        name,
                        description,
                        changelog,
                        stage.value,
                        'draft',
                        user,
                        json.dumps(release_data['metadata'])
                    ))
                    conn.commit()
            except Exception as e:
                self.logger.error(f"Failed to save release {release_id}: {e}")
                return {
                    'success': False,
                    'error': f'Failed to save release: {e}'
                }
            
            self.logger.info(f"Release {release_id} created by {user}")
            
            return {
                'success': True,
                'release': release_data,
                'created_by': user,
                'timestamp': datetime.now().isoformat()
            }
    
    def start_deployment(self, version: str, strategy: DeploymentStrategy = DeploymentStrategy.BLUE_GREEN,
                        stage: ReleaseStage = ReleaseStage.STAGING,
                        config: Dict[str, Any] = None, user: str = None) -> Dict[str, Any]:
        """Start a new deployment"""
        
        if config is None:
            config = {}
        
        deployment_id = f"deploy-{version}-{int(time.time())}"
        
        with self._lock:
            # Check if there's an active deployment
            if self._active_deployment:
                active_deploy = self._deployments.get(self._active_deployment)
                if active_deploy and active_deploy['status'] in [DeploymentStatus.PENDING, DeploymentStatus.RUNNING]:
                    return {
                        'success': False,
                        'error': f'Deployment {self._active_deployment} is already active'
                    }
            
            # Create rollback point before deployment
            rollback_point = self._create_rollback_point(version, stage, user)
            
            deployment_data = {
                'deployment_id': deployment_id,
                'version': version,
                'strategy': strategy,
                'stage': stage,
                'status': DeploymentStatus.PENDING,
                'progress': 0,
                'started_by': user,
                'started_at': datetime.now().isoformat(),
                'rollback_point': rollback_point['point_id'] if rollback_point['success'] else None,
                'config': config,
                'metadata': {
                    'estimated_duration': self._estimate_deployment_duration(strategy),
                    'safety_checks': True
                }
            }
            
            self._deployments[deployment_id] = deployment_data
            self._active_deployment = deployment_id
            
            # Save to database
            self._save_deployment(deployment_id, deployment_data)
            self._log_deployment(deployment_id, 'info', f'Deployment started by {user}')
            
            # Start deployment in background
            deployment_thread = threading.Thread(
                target=self._execute_deployment,
                args=(deployment_id,),
                daemon=True
            )
            deployment_thread.start()
            
            self.logger.info(f"Deployment {deployment_id} started by {user}")
            
            return {
                'success': True,
                'deployment_id': deployment_id,
                'deployment': deployment_data,
                'started_by': user,
                'timestamp': datetime.now().isoformat()
            }
    
    def _execute_deployment(self, deployment_id: str):
        """Execute deployment process"""
        try:
            with self._lock:
                deployment = self._deployments[deployment_id]
                deployment['status'] = DeploymentStatus.RUNNING
                self._save_deployment(deployment_id, deployment)
            
            strategy = deployment['strategy']
            
            if strategy == DeploymentStrategy.BLUE_GREEN:
                self._execute_blue_green_deployment(deployment_id)
            elif strategy == DeploymentStrategy.CANARY:
                self._execute_canary_deployment(deployment_id)
            elif strategy == DeploymentStrategy.ROLLING:
                self._execute_rolling_deployment(deployment_id)
            elif strategy == DeploymentStrategy.IMMEDIATE:
                self._execute_immediate_deployment(deployment_id)
            
            # Mark as completed
            with self._lock:
                deployment['status'] = DeploymentStatus.SUCCESS
                deployment['completed_at'] = datetime.now().isoformat()
                deployment['progress'] = 100
                self._save_deployment(deployment_id, deployment)
            
            self._log_deployment(deployment_id, 'info', 'Deployment completed successfully')
            self.logger.info(f"Deployment {deployment_id} completed successfully")
            
        except Exception as e:
            with self._lock:
                deployment['status'] = DeploymentStatus.FAILED
                deployment['completed_at'] = datetime.now().isoformat()
                deployment['error'] = str(e)
                self._save_deployment(deployment_id, deployment)
            
            self._log_deployment(deployment_id, 'error', f'Deployment failed: {e}')
            self.logger.error(f"Deployment {deployment_id} failed: {e}")
            
            # Send alert
            self.alert_manager.send_alert(
                level='critical',
                message=f'Deployment {deployment_id} failed: {e}',
                component='deployment_manager'
            )
        finally:
            with self._lock:
                if self._active_deployment == deployment_id:
                    self._active_deployment = None
    
    def _execute_blue_green_deployment(self, deployment_id: str):
        """Execute blue-green deployment"""
        deployment = self._deployments[deployment_id]
        
        # Phase 1: Prepare green environment
        self._log_deployment(deployment_id, 'info', 'Preparing green environment')
        deployment['progress'] = 10
        self._save_deployment(deployment_id, deployment)
        
        # Simulate green environment setup
        time.sleep(2)
        
        # Phase 2: Deploy to green
        self._log_deployment(deployment_id, 'info', 'Deploying to green environment')
        deployment['progress'] = 30
        self._save_deployment(deployment_id, deployment)
        
        # Simulate deployment
        time.sleep(3)
        
        # Phase 3: Health checks
        self._log_deployment(deployment_id, 'info', 'Running health checks')
        deployment['progress'] = 60
        self._save_deployment(deployment_id, deployment)
        
        # Simulate health checks
        time.sleep(2)
        
        # Phase 4: Switch traffic
        self._log_deployment(deployment_id, 'info', 'Switching traffic to green')
        deployment['progress'] = 80
        self._save_deployment(deployment_id, deployment)
        
        # Simulate traffic switch
        time.sleep(1)
        
        # Phase 5: Cleanup blue environment
        self._log_deployment(deployment_id, 'info', 'Cleaning up blue environment')
        deployment['progress'] = 95
        self._save_deployment(deployment_id, deployment)
        
        # Simulate cleanup
        time.sleep(1)
    
    def _execute_canary_deployment(self, deployment_id: str):
        """Execute canary deployment"""
        deployment = self._deployments[deployment_id]
        
        # Phase 1: Deploy to canary servers
        self._log_deployment(deployment_id, 'info', 'Deploying to canary servers')
        deployment['progress'] = 20
        self._save_deployment(deployment_id, deployment)
        
        time.sleep(2)
        
        # Phase 2: Route small percentage of traffic
        self._log_deployment(deployment_id, 'info', 'Routing 10% traffic to canary')
        deployment['progress'] = 40
        self._save_deployment(deployment_id, deployment)
        
        time.sleep(3)
        
        # Phase 3: Monitor metrics
        self._log_deployment(deployment_id, 'info', 'Monitoring canary metrics')
        deployment['progress'] = 60
        self._save_deployment(deployment_id, deployment)
        
        time.sleep(2)
        
        # Phase 4: Gradually increase traffic
        self._log_deployment(deployment_id, 'info', 'Increasing traffic to 50%')
        deployment['progress'] = 80
        self._save_deployment(deployment_id, deployment)
        
        time.sleep(2)
        
        # Phase 5: Complete rollout
        self._log_deployment(deployment_id, 'info', 'Completing rollout to all servers')
        deployment['progress'] = 95
        self._save_deployment(deployment_id, deployment)
        
        time.sleep(1)
    
    def _execute_rolling_deployment(self, deployment_id: str):
        """Execute rolling deployment"""
        deployment = self._deployments[deployment_id]
        
        # Simulate rolling deployment across multiple servers
        servers = ['server-1', 'server-2', 'server-3', 'server-4']
        
        for i, server in enumerate(servers):
            self._log_deployment(deployment_id, 'info', f'Deploying to {server}')
            deployment['progress'] = int((i + 1) / len(servers) * 90)
            self._save_deployment(deployment_id, deployment)
            
            time.sleep(1)
    
    def _execute_immediate_deployment(self, deployment_id: str):
        """Execute immediate deployment"""
        deployment = self._deployments[deployment_id]
        
        # Phase 1: Deploy immediately
        self._log_deployment(deployment_id, 'info', 'Deploying immediately')
        deployment['progress'] = 50
        self._save_deployment(deployment_id, deployment)
        
        time.sleep(2)
        
        # Phase 2: Restart services
        self._log_deployment(deployment_id, 'info', 'Restarting services')
        deployment['progress'] = 90
        self._save_deployment(deployment_id, deployment)
        
        time.sleep(1)
    
    def _create_rollback_point(self, version: str, stage: ReleaseStage, user: str = None) -> Dict[str, Any]:
        """Create a rollback point"""
        point_id = f"rollback-{version}-{int(time.time())}"
        
        try:
            # Create rollback point data
            rollback_data = {
                'point_id': point_id,
                'version': version,
                'stage': stage,
                'created_at': datetime.now().isoformat(),
                'created_by': user,
                'database_backup': self._backup_database(),
                'file_backup': self._backup_files(),
                'config_backup': self._backup_config()
            }
            
            self._rollback_points[point_id] = rollback_data
            
            # Save to database
            with db.get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO rollback_points
                    (point_id, version, stage, database_backup, file_backup, config_backup, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    point_id,
                    version,
                    stage.value,
                    rollback_data['database_backup'],
                    rollback_data['file_backup'],
                    rollback_data['config_backup'],
                    json.dumps({'created_by': user})
                ))
                conn.commit()
            
            self.logger.info(f"Rollback point {point_id} created")
            
            return {
                'success': True,
                'point_id': point_id,
                'rollback_point': rollback_data
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create rollback point: {e}")
            return {
                'success': False,
                'error': f'Failed to create rollback point: {e}'
            }
    
    def _backup_database(self) -> str:
        """Create database backup"""
        try:
            # Create database backup
            backup_path = f"/tmp/db_backup_{int(time.time())}.db"
            shutil.copy2(db.db_path, backup_path)
            return backup_path
        except Exception as e:
            self.logger.error(f"Failed to backup database: {e}")
            return ""
    
    def _backup_files(self) -> str:
        """Create file backup"""
        try:
            # Create file backup (simplified)
            backup_path = f"/tmp/files_backup_{int(time.time())}.tar.gz"
            # In a real implementation, this would create a tar.gz of important files
            return backup_path
        except Exception as e:
            self.logger.error(f"Failed to backup files: {e}")
            return ""
    
    def _backup_config(self) -> str:
        """Create configuration backup"""
        try:
            # Backup current configuration
            config_backup = {
                'system_config': system_controller.get_system_config(),
                'timestamp': datetime.now().isoformat()
            }
            
            backup_path = f"/tmp/config_backup_{int(time.time())}.json"
            with open(backup_path, 'w') as f:
                json.dump(config_backup, f, indent=2)
            
            return backup_path
        except Exception as e:
            self.logger.error(f"Failed to backup configuration: {e}")
            return ""
    
    def rollback_deployment(self, deployment_id: str = None, rollback_point_id: str = None,
                           user: str = None) -> Dict[str, Any]:
        """Rollback a deployment"""
        
        with self._lock:
            if deployment_id:
                if deployment_id not in self._deployments:
                    return {
                        'success': False,
                        'error': f'Deployment {deployment_id} not found'
                    }
                
                deployment = self._deployments[deployment_id]
                rollback_point_id = deployment.get('rollback_point')
                
                if not rollback_point_id:
                    return {
                        'success': False,
                        'error': f'No rollback point available for deployment {deployment_id}'
                    }
            
            if not rollback_point_id:
                return {
                    'success': False,
                    'error': 'No rollback point specified'
                }
            
            if rollback_point_id not in self._rollback_points:
                # Load from database
                try:
                    with db.get_db_connection() as conn:
                        cursor = conn.execute('''
                            SELECT * FROM rollback_points WHERE point_id = ?
                        ''', (rollback_point_id,))
                        
                        row = cursor.fetchone()
                        if not row:
                            return {
                                'success': False,
                                'error': f'Rollback point {rollback_point_id} not found'
                            }
                        
                        rollback_data = {
                            'point_id': row['point_id'],
                            'version': row['version'],
                            'stage': ReleaseStage(row['stage']),
                            'created_at': row['created_at'],
                            'database_backup': row['database_backup'],
                            'file_backup': row['file_backup'],
                            'config_backup': row['config_backup']
                        }
                        
                        self._rollback_points[rollback_point_id] = rollback_data
                        
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Failed to load rollback point: {e}'
                    }
            
            rollback_data = self._rollback_points[rollback_point_id]
            
            # Execute rollback
            try:
                # Set maintenance mode
                system_controller.set_maintenance_mode(True, "System rollback in progress", user)
                
                # Restore database
                if rollback_data['database_backup'] and os.path.exists(rollback_data['database_backup']):
                    shutil.copy2(rollback_data['database_backup'], db.db_path)
                
                # Restore configuration
                if rollback_data['config_backup'] and os.path.exists(rollback_data['config_backup']):
                    with open(rollback_data['config_backup'], 'r') as f:
                        config_backup = json.load(f)
                        system_controller.update_system_config(config_backup['system_config'], user)
                
                # Update deployment status
                if deployment_id:
                    deployment['status'] = DeploymentStatus.ROLLED_BACK
                    deployment['completed_at'] = datetime.now().isoformat()
                    self._save_deployment(deployment_id, deployment)
                
                # Clear maintenance mode
                system_controller.set_maintenance_mode(False, admin_user=user)
                
                self.logger.info(f"Rollback to {rollback_point_id} completed by {user}")
                
                return {
                    'success': True,
                    'rollback_point': rollback_data,
                    'rolled_back_by': user,
                    'timestamp': datetime.now().isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"Rollback failed: {e}")
                return {
                    'success': False,
                    'error': f'Rollback failed: {e}'
                }
    
    def _estimate_deployment_duration(self, strategy: DeploymentStrategy) -> int:
        """Estimate deployment duration in seconds"""
        durations = {
            DeploymentStrategy.IMMEDIATE: 30,
            DeploymentStrategy.ROLLING: 120,
            DeploymentStrategy.BLUE_GREEN: 180,
            DeploymentStrategy.CANARY: 300
        }
        return durations.get(strategy, 120)
    
    def get_deployment_status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment status"""
        with self._lock:
            return self._deployments.get(deployment_id)
    
    def get_active_deployments(self) -> List[Dict[str, Any]]:
        """Get all active deployments"""
        with self._lock:
            return [
                deploy for deploy in self._deployments.values()
                if deploy['status'] in [DeploymentStatus.PENDING, DeploymentStatus.RUNNING]
            ]
    
    def get_deployment_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get deployment history"""
        try:
            with db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM deployments
                    ORDER BY started_at DESC
                    LIMIT ?
                ''', (limit,))
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        'deployment_id': row['deployment_id'],
                        'version': row['version'],
                        'strategy': row['strategy'],
                        'stage': row['stage'],
                        'status': row['status'],
                        'progress': row['progress'],
                        'started_by': row['started_by'],
                        'started_at': row['started_at'],
                        'completed_at': row['completed_at']
                    })
                
                return history
        except Exception as e:
            self.logger.error(f"Failed to get deployment history: {e}")
            return []
    
    def get_deployment_logs(self, deployment_id: str) -> List[Dict[str, Any]]:
        """Get deployment logs"""
        try:
            with db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM deployment_logs
                    WHERE deployment_id = ?
                    ORDER BY timestamp ASC
                ''', (deployment_id,))
                
                logs = []
                for row in cursor.fetchall():
                    logs.append({
                        'deployment_id': row['deployment_id'],
                        'log_level': row['log_level'],
                        'message': row['message'],
                        'timestamp': row['timestamp'],
                        'component': row['component']
                    })
                
                return logs
        except Exception as e:
            self.logger.error(f"Failed to get deployment logs: {e}")
            return []
    
    def cancel_deployment(self, deployment_id: str, user: str = None) -> Dict[str, Any]:
        """Cancel an active deployment"""
        with self._lock:
            if deployment_id not in self._deployments:
                return {
                    'success': False,
                    'error': f'Deployment {deployment_id} not found'
                }
            
            deployment = self._deployments[deployment_id]
            
            if deployment['status'] not in [DeploymentStatus.PENDING, DeploymentStatus.RUNNING]:
                return {
                    'success': False,
                    'error': f'Deployment {deployment_id} cannot be cancelled (status: {deployment["status"]})'
                }
            
            deployment['status'] = DeploymentStatus.CANCELLED
            deployment['completed_at'] = datetime.now().isoformat()
            self._save_deployment(deployment_id, deployment)
            
            self._log_deployment(deployment_id, 'warning', f'Deployment cancelled by {user}')
            
            if self._active_deployment == deployment_id:
                self._active_deployment = None
            
            self.logger.info(f"Deployment {deployment_id} cancelled by {user}")
            
            return {
                'success': True,
                'deployment_id': deployment_id,
                'cancelled_by': user,
                'timestamp': datetime.now().isoformat()
            }


# Global deployment manager instance
deployment_manager = DeploymentManager()

if __name__ == '__main__':
    # Test deployment manager
    print("🚀 Testing VectorCraft Deployment Manager...")
    
    # Create a test release
    print("\n📦 Creating Test Release:")
    release_result = deployment_manager.create_release(
        version="2.1.0",
        name="Feature Update",
        description="New features and improvements",
        changelog="- Added system control center\n- Improved performance\n- Bug fixes",
        user="test-admin"
    )
    print(f"  Created release: {release_result['success']}")
    
    # Start a deployment
    print("\n🚀 Starting Test Deployment:")
    deploy_result = deployment_manager.start_deployment(
        version="2.1.0",
        strategy=DeploymentStrategy.BLUE_GREEN,
        stage=ReleaseStage.STAGING,
        user="test-admin"
    )
    print(f"  Started deployment: {deploy_result['success']}")
    
    if deploy_result['success']:
        deployment_id = deploy_result['deployment_id']
        print(f"  Deployment ID: {deployment_id}")
        
        # Monitor deployment progress
        print("\n📊 Monitoring Deployment Progress:")
        for i in range(10):
            time.sleep(1)
            status = deployment_manager.get_deployment_status(deployment_id)
            if status:
                print(f"  Progress: {status['progress']}% - Status: {status['status'].value}")
                if status['status'] in [DeploymentStatus.SUCCESS, DeploymentStatus.FAILED]:
                    break
        
        # Get deployment logs
        print("\n📋 Deployment Logs:")
        logs = deployment_manager.get_deployment_logs(deployment_id)
        for log in logs[-5:]:  # Show last 5 logs
            print(f"  [{log['timestamp']}] {log['log_level']}: {log['message']}")
    
    # Get deployment history
    print("\n📚 Deployment History:")
    history = deployment_manager.get_deployment_history(limit=3)
    for deployment in history:
        print(f"  {deployment['deployment_id']}: {deployment['version']} - {deployment['status']}")
    
    print("\n✅ Deployment Manager Test Complete")