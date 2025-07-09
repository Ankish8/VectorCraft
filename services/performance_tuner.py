#!/usr/bin/env python3
"""
Advanced Performance Tuner & System Optimizer
Real-time performance optimization and system tuning capabilities
"""

import os
import time
import threading
import psutil
import statistics
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Try to import Flask
try:
    from flask import current_app
except ImportError:
    current_app = None

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    timestamp: datetime
    metric_type: str
    value: float
    unit: str
    endpoint: Optional[str] = None
    status: str = 'normal'
    metadata: Dict[str, Any] = None

@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation"""
    category: str
    title: str
    description: str
    impact: str  # low, medium, high, critical
    confidence: float  # 0.0 to 1.0
    action: str
    parameters: Dict[str, Any]
    estimated_improvement: str

@dataclass
class SystemThreshold:
    """System performance threshold configuration"""
    metric: str
    warning_threshold: float
    critical_threshold: float
    unit: str
    description: str

class PerformanceTuner:
    """Advanced performance tuning and optimization system"""
    
    def __init__(self, db_path: str = "vectorcraft.db"):
        self.db_path = db_path
        self.metrics_history = deque(maxlen=10000)
        self.optimization_queue = deque()
        self.active_optimizations = {}
        self.tuning_parameters = self._load_tuning_parameters()
        self.thresholds = self._initialize_thresholds()
        
        # Performance monitoring
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        
        # Optimization engine
        self.optimization_active = True
        self.optimization_thread = threading.Thread(target=self._optimization_loop)
        self.optimization_thread.daemon = True
        
        # Initialize database
        self._init_database()
        
        # Start monitoring threads
        self.monitoring_thread.start()
        self.optimization_thread.start()
        
        logger.info("Performance Tuner initialized with real-time optimization")
    
    def _initialize_thresholds(self) -> Dict[str, SystemThreshold]:
        """Initialize performance thresholds"""
        return {
            'response_time_avg': SystemThreshold(
                metric='response_time_avg',
                warning_threshold=100.0,
                critical_threshold=500.0,
                unit='ms',
                description='Average response time across all endpoints'
            ),
            'response_time_95th': SystemThreshold(
                metric='response_time_95th',
                warning_threshold=200.0,
                critical_threshold=1000.0,
                unit='ms',
                description='95th percentile response time'
            ),
            'memory_usage': SystemThreshold(
                metric='memory_usage',
                warning_threshold=80.0,
                critical_threshold=90.0,
                unit='%',
                description='System memory usage percentage'
            ),
            'cpu_usage': SystemThreshold(
                metric='cpu_usage',
                warning_threshold=70.0,
                critical_threshold=85.0,
                unit='%',
                description='System CPU usage percentage'
            ),
            'disk_usage': SystemThreshold(
                metric='disk_usage',
                warning_threshold=80.0,
                critical_threshold=90.0,
                unit='%',
                description='System disk usage percentage'
            ),
            'error_rate': SystemThreshold(
                metric='error_rate',
                warning_threshold=2.0,
                critical_threshold=5.0,
                unit='%',
                description='Application error rate percentage'
            ),
            'database_query_time': SystemThreshold(
                metric='database_query_time',
                warning_threshold=50.0,
                critical_threshold=200.0,
                unit='ms',
                description='Database query response time'
            )
        }
    
    def _load_tuning_parameters(self) -> Dict[str, Any]:
        """Load tuning parameters from configuration"""
        return {
            'memory_optimization': {
                'cache_size_mb': 256,
                'gc_threshold': 0.8,
                'connection_pool_size': 10,
                'max_workers': 4
            },
            'database_optimization': {
                'query_cache_size': 100,
                'connection_timeout': 30,
                'slow_query_threshold': 50,
                'index_optimization': True
            },
            'network_optimization': {
                'request_timeout': 30,
                'max_connections': 100,
                'keepalive_timeout': 60,
                'compression_enabled': True
            },
            'application_optimization': {
                'auto_scaling': True,
                'load_balancing': False,
                'caching_enabled': True,
                'async_processing': True
            }
        }
    
    def _init_database(self):
        """Initialize performance database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    metric_type VARCHAR(50) NOT NULL,
                    value REAL NOT NULL,
                    unit VARCHAR(10),
                    endpoint VARCHAR(100),
                    status VARCHAR(20) DEFAULT 'normal',
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Optimization history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS optimization_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    action VARCHAR(100) NOT NULL,
                    parameters TEXT,
                    result VARCHAR(20),
                    impact_score REAL,
                    duration_ms INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tuning parameters table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tuning_parameters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category VARCHAR(50) NOT NULL,
                    parameter_name VARCHAR(100) NOT NULL,
                    parameter_value TEXT NOT NULL,
                    description TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, parameter_name)
                )
            ''')
            
            # Performance thresholds table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_thresholds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric VARCHAR(50) PRIMARY KEY,
                    warning_threshold REAL NOT NULL,
                    critical_threshold REAL NOT NULL,
                    unit VARCHAR(10),
                    description TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric"""
        try:
            # Add to in-memory history
            self.metrics_history.append(metric)
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_metrics 
                (timestamp, metric_type, value, unit, endpoint, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric.timestamp,
                metric.metric_type,
                metric.value,
                metric.unit,
                metric.endpoint,
                metric.status,
                json.dumps(metric.metadata) if metric.metadata else None
            ))
            
            conn.commit()
            conn.close()
            
            # Check if optimization is needed
            self._check_optimization_triggers(metric)
            
        except Exception as e:
            logger.error(f"Error recording metric: {e}")
    
    def _monitoring_loop(self):
        """Main monitoring loop for collecting system metrics"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                timestamp = datetime.now()
                
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_freq = psutil.cpu_freq()
                cpu_count = psutil.cpu_count()
                
                # Memory metrics
                memory = psutil.virtual_memory()
                swap = psutil.swap_memory()
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                disk_io = psutil.disk_io_counters()
                
                # Network metrics
                network = psutil.net_io_counters()
                
                # Process metrics
                process = psutil.Process()
                process_memory = process.memory_info()
                process_cpu = process.cpu_percent()
                
                # Record metrics
                metrics = [
                    PerformanceMetric(timestamp, 'cpu_usage', cpu_percent, '%'),
                    PerformanceMetric(timestamp, 'cpu_frequency', cpu_freq.current if cpu_freq else 0, 'MHz'),
                    PerformanceMetric(timestamp, 'memory_usage', memory.percent, '%'),
                    PerformanceMetric(timestamp, 'memory_available', memory.available, 'bytes'),
                    PerformanceMetric(timestamp, 'swap_usage', swap.percent, '%'),
                    PerformanceMetric(timestamp, 'disk_usage', disk.percent, '%'),
                    PerformanceMetric(timestamp, 'disk_read_bytes', disk_io.read_bytes if disk_io else 0, 'bytes'),
                    PerformanceMetric(timestamp, 'disk_write_bytes', disk_io.write_bytes if disk_io else 0, 'bytes'),
                    PerformanceMetric(timestamp, 'network_bytes_sent', network.bytes_sent, 'bytes'),
                    PerformanceMetric(timestamp, 'network_bytes_recv', network.bytes_recv, 'bytes'),
                    PerformanceMetric(timestamp, 'process_memory', process_memory.rss, 'bytes'),
                    PerformanceMetric(timestamp, 'process_cpu', process_cpu, '%'),
                ]
                
                for metric in metrics:
                    self.record_metric(metric)
                
                # Sleep for monitoring interval
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(60)
    
    def _optimization_loop(self):
        """Main optimization loop for applying performance improvements"""
        while self.optimization_active:
            try:
                if self.optimization_queue:
                    recommendation = self.optimization_queue.popleft()
                    self._apply_optimization(recommendation)
                
                # Run periodic optimization checks
                self._run_periodic_optimization()
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Optimization loop error: {e}")
                time.sleep(120)
    
    def _check_optimization_triggers(self, metric: PerformanceMetric):
        """Check if metric triggers optimization"""
        if metric.metric_type not in self.thresholds:
            return
        
        threshold = self.thresholds[metric.metric_type]
        
        # Check if threshold is exceeded
        if metric.value > threshold.critical_threshold:
            self._trigger_optimization(metric, 'critical')
        elif metric.value > threshold.warning_threshold:
            self._trigger_optimization(metric, 'warning')
    
    def _trigger_optimization(self, metric: PerformanceMetric, severity: str):
        """Trigger optimization based on metric threshold"""
        recommendations = self._generate_optimization_recommendations(metric, severity)
        
        for recommendation in recommendations:
            self.optimization_queue.append(recommendation)
    
    def _generate_optimization_recommendations(self, metric: PerformanceMetric, severity: str) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations based on metric"""
        recommendations = []
        
        if metric.metric_type == 'memory_usage':
            if metric.value > 80:
                recommendations.append(OptimizationRecommendation(
                    category='memory',
                    title='Reduce Memory Usage',
                    description='High memory usage detected. Optimize memory allocation and cleanup.',
                    impact='high',
                    confidence=0.8,
                    action='optimize_memory',
                    parameters={'threshold': metric.value},
                    estimated_improvement='10-20% memory reduction'
                ))
        
        elif metric.metric_type == 'cpu_usage':
            if metric.value > 70:
                recommendations.append(OptimizationRecommendation(
                    category='cpu',
                    title='Optimize CPU Usage',
                    description='High CPU usage detected. Optimize processing algorithms.',
                    impact='high',
                    confidence=0.7,
                    action='optimize_cpu',
                    parameters={'threshold': metric.value},
                    estimated_improvement='15-30% CPU reduction'
                ))
        
        elif metric.metric_type == 'response_time_avg':
            if metric.value > 100:
                recommendations.append(OptimizationRecommendation(
                    category='performance',
                    title='Improve Response Time',
                    description='Slow response times detected. Optimize caching and database queries.',
                    impact='medium',
                    confidence=0.9,
                    action='optimize_response_time',
                    parameters={'current_time': metric.value},
                    estimated_improvement='20-40% response time improvement'
                ))
        
        return recommendations
    
    def _apply_optimization(self, recommendation: OptimizationRecommendation):
        """Apply optimization recommendation"""
        start_time = time.time()
        result = 'failed'
        
        try:
            if recommendation.action == 'optimize_memory':
                result = self._optimize_memory(recommendation.parameters)
            elif recommendation.action == 'optimize_cpu':
                result = self._optimize_cpu(recommendation.parameters)
            elif recommendation.action == 'optimize_response_time':
                result = self._optimize_response_time(recommendation.parameters)
            elif recommendation.action == 'optimize_database':
                result = self._optimize_database(recommendation.parameters)
            
            duration = int((time.time() - start_time) * 1000)
            
            # Record optimization result
            self._record_optimization_result(recommendation, result, duration)
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            duration = int((time.time() - start_time) * 1000)
            self._record_optimization_result(recommendation, 'error', duration)
    
    def _optimize_memory(self, parameters: Dict[str, Any]) -> str:
        """Optimize memory usage"""
        try:
            import gc
            
            # Force garbage collection
            gc.collect()
            
            # Optimize tuning parameters
            if parameters.get('threshold', 0) > 85:
                self.tuning_parameters['memory_optimization']['cache_size_mb'] = max(
                    128, self.tuning_parameters['memory_optimization']['cache_size_mb'] - 64
                )
                self.tuning_parameters['memory_optimization']['connection_pool_size'] = max(
                    5, self.tuning_parameters['memory_optimization']['connection_pool_size'] - 2
                )
            
            return 'success'
            
        except Exception as e:
            logger.error(f"Memory optimization error: {e}")
            return 'failed'
    
    def _optimize_cpu(self, parameters: Dict[str, Any]) -> str:
        """Optimize CPU usage"""
        try:
            # Reduce worker threads if CPU usage is high
            if parameters.get('threshold', 0) > 80:
                self.tuning_parameters['memory_optimization']['max_workers'] = max(
                    2, self.tuning_parameters['memory_optimization']['max_workers'] - 1
                )
            
            return 'success'
            
        except Exception as e:
            logger.error(f"CPU optimization error: {e}")
            return 'failed'
    
    def _optimize_response_time(self, parameters: Dict[str, Any]) -> str:
        """Optimize response time"""
        try:
            # Enable compression if response time is slow
            if parameters.get('current_time', 0) > 200:
                self.tuning_parameters['network_optimization']['compression_enabled'] = True
                self.tuning_parameters['application_optimization']['caching_enabled'] = True
            
            return 'success'
            
        except Exception as e:
            logger.error(f"Response time optimization error: {e}")
            return 'failed'
    
    def _optimize_database(self, parameters: Dict[str, Any]) -> str:
        """Optimize database performance"""
        try:
            # Increase connection pool if needed
            if parameters.get('slow_queries', 0) > 5:
                self.tuning_parameters['database_optimization']['connection_timeout'] = min(
                    60, self.tuning_parameters['database_optimization']['connection_timeout'] + 10
                )
            
            return 'success'
            
        except Exception as e:
            logger.error(f"Database optimization error: {e}")
            return 'failed'
    
    def _record_optimization_result(self, recommendation: OptimizationRecommendation, result: str, duration: int):
        """Record optimization result in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO optimization_history 
                (timestamp, category, action, parameters, result, impact_score, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now(),
                recommendation.category,
                recommendation.action,
                json.dumps(recommendation.parameters),
                result,
                recommendation.confidence,
                duration
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error recording optimization result: {e}")
    
    def _run_periodic_optimization(self):
        """Run periodic optimization checks"""
        try:
            # Check for optimization opportunities
            recent_metrics = self._get_recent_metrics(minutes=5)
            
            # Analyze patterns and suggest optimizations
            patterns = self._analyze_performance_patterns(recent_metrics)
            
            for pattern in patterns:
                if pattern['confidence'] > 0.7:
                    recommendation = self._pattern_to_recommendation(pattern)
                    if recommendation:
                        self.optimization_queue.append(recommendation)
            
        except Exception as e:
            logger.error(f"Periodic optimization error: {e}")
    
    def _get_recent_metrics(self, minutes: int = 5) -> List[PerformanceMetric]:
        """Get recent metrics from specified time period"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [m for m in self.metrics_history if m.timestamp > cutoff_time]
    
    def _analyze_performance_patterns(self, metrics: List[PerformanceMetric]) -> List[Dict[str, Any]]:
        """Analyze performance patterns in metrics"""
        patterns = []
        
        try:
            # Group metrics by type
            metric_groups = defaultdict(list)
            for metric in metrics:
                metric_groups[metric.metric_type].append(metric.value)
            
            # Analyze each metric type
            for metric_type, values in metric_groups.items():
                if len(values) >= 5:  # Need minimum data points
                    # Calculate trend
                    trend = self._calculate_trend(values)
                    variance = statistics.variance(values) if len(values) > 1 else 0
                    
                    # Identify patterns
                    if trend > 0.1 and metric_type in ['memory_usage', 'cpu_usage']:
                        patterns.append({
                            'type': 'increasing_resource_usage',
                            'metric': metric_type,
                            'trend': trend,
                            'confidence': min(0.9, abs(trend) * 2),
                            'severity': 'medium' if trend < 0.2 else 'high'
                        })
                    
                    if variance > 100 and metric_type == 'response_time_avg':
                        patterns.append({
                            'type': 'response_time_instability',
                            'metric': metric_type,
                            'variance': variance,
                            'confidence': min(0.8, variance / 500),
                            'severity': 'medium'
                        })
            
        except Exception as e:
            logger.error(f"Pattern analysis error: {e}")
        
        return patterns
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend in values (positive = increasing, negative = decreasing)"""
        if len(values) < 2:
            return 0.0
        
        # Simple linear regression slope
        n = len(values)
        x = list(range(n))
        
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope
    
    def _pattern_to_recommendation(self, pattern: Dict[str, Any]) -> Optional[OptimizationRecommendation]:
        """Convert pattern to optimization recommendation"""
        if pattern['type'] == 'increasing_resource_usage':
            return OptimizationRecommendation(
                category='resource',
                title=f'Optimize {pattern["metric"]}',
                description=f'Increasing trend detected in {pattern["metric"]}',
                impact=pattern['severity'],
                confidence=pattern['confidence'],
                action=f'optimize_{pattern["metric"]}',
                parameters=pattern,
                estimated_improvement=f'Stabilize {pattern["metric"]} growth'
            )
        
        elif pattern['type'] == 'response_time_instability':
            return OptimizationRecommendation(
                category='stability',
                title='Stabilize Response Times',
                description='Response time variance detected',
                impact='medium',
                confidence=pattern['confidence'],
                action='optimize_response_stability',
                parameters=pattern,
                estimated_improvement='Reduce response time variance by 30%'
            )
        
        return None
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time performance metrics"""
        try:
            recent_metrics = self._get_recent_metrics(minutes=1)
            
            # Group by metric type
            metric_data = defaultdict(list)
            for metric in recent_metrics:
                metric_data[metric.metric_type].append(metric.value)
            
            # Calculate current values
            current_metrics = {}
            for metric_type, values in metric_data.items():
                if values:
                    current_metrics[metric_type] = {
                        'current': values[-1],
                        'average': statistics.mean(values),
                        'max': max(values),
                        'min': min(values),
                        'trend': self._calculate_trend(values),
                        'status': self._get_metric_status(metric_type, values[-1])
                    }
            
            return {
                'timestamp': datetime.now().isoformat(),
                'metrics': current_metrics,
                'active_optimizations': len(self.active_optimizations),
                'optimization_queue_size': len(self.optimization_queue),
                'system_health': self._calculate_system_health(current_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error getting real-time metrics: {e}")
            return {'error': str(e)}
    
    def _get_metric_status(self, metric_type: str, value: float) -> str:
        """Get status of metric based on thresholds"""
        if metric_type not in self.thresholds:
            return 'unknown'
        
        threshold = self.thresholds[metric_type]
        
        if value > threshold.critical_threshold:
            return 'critical'
        elif value > threshold.warning_threshold:
            return 'warning'
        else:
            return 'normal'
    
    def _calculate_system_health(self, metrics: Dict[str, Any]) -> str:
        """Calculate overall system health"""
        critical_count = 0
        warning_count = 0
        total_count = 0
        
        for metric_type, data in metrics.items():
            status = data.get('status', 'unknown')
            if status == 'critical':
                critical_count += 1
            elif status == 'warning':
                warning_count += 1
            total_count += 1
        
        if total_count == 0:
            return 'unknown'
        
        if critical_count > 0:
            return 'critical'
        elif warning_count > total_count * 0.3:  # More than 30% warnings
            return 'warning'
        else:
            return 'healthy'
    
    def get_optimization_recommendations(self) -> List[OptimizationRecommendation]:
        """Get current optimization recommendations"""
        recommendations = []
        
        # Generate recommendations based on current metrics
        recent_metrics = self._get_recent_metrics(minutes=5)
        
        for metric in recent_metrics:
            if metric.metric_type in self.thresholds:
                threshold = self.thresholds[metric.metric_type]
                
                if metric.value > threshold.warning_threshold:
                    severity = 'critical' if metric.value > threshold.critical_threshold else 'warning'
                    recs = self._generate_optimization_recommendations(metric, severity)
                    recommendations.extend(recs)
        
        # Remove duplicates
        unique_recommendations = []
        seen_actions = set()
        
        for rec in recommendations:
            if rec.action not in seen_actions:
                unique_recommendations.append(rec)
                seen_actions.add(rec.action)
        
        return unique_recommendations
    
    def apply_tuning_parameter(self, category: str, parameter: str, value: Any) -> bool:
        """Apply tuning parameter change"""
        try:
            if category in self.tuning_parameters:
                if parameter in self.tuning_parameters[category]:
                    old_value = self.tuning_parameters[category][parameter]
                    self.tuning_parameters[category][parameter] = value
                    
                    # Save to database
                    self._save_tuning_parameter(category, parameter, value)
                    
                    logger.info(f"Tuning parameter updated: {category}.{parameter} = {value} (was {old_value})")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error applying tuning parameter: {e}")
            return False
    
    def _save_tuning_parameter(self, category: str, parameter: str, value: Any):
        """Save tuning parameter to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO tuning_parameters 
                (category, parameter_name, parameter_value, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (category, parameter, json.dumps(value), datetime.now()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving tuning parameter: {e}")
    
    def get_tuning_parameters(self) -> Dict[str, Any]:
        """Get current tuning parameters"""
        return self.tuning_parameters
    
    def get_performance_history(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance history for specified hours"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            cursor.execute('''
                SELECT metric_type, value, timestamp
                FROM performance_metrics
                WHERE timestamp > ?
                ORDER BY timestamp
            ''', (cutoff_time,))
            
            results = cursor.fetchall()
            conn.close()
            
            # Group by metric type
            history = defaultdict(list)
            for metric_type, value, timestamp in results:
                history[metric_type].append({
                    'value': value,
                    'timestamp': timestamp
                })
            
            return dict(history)
            
        except Exception as e:
            logger.error(f"Error getting performance history: {e}")
            return {}
    
    def get_optimization_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get optimization history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            cursor.execute('''
                SELECT category, action, parameters, result, impact_score, duration_ms, timestamp
                FROM optimization_history
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            ''', (cutoff_time,))
            
            results = cursor.fetchall()
            conn.close()
            
            history = []
            for row in results:
                history.append({
                    'category': row[0],
                    'action': row[1],
                    'parameters': json.loads(row[2]) if row[2] else {},
                    'result': row[3],
                    'impact_score': row[4],
                    'duration_ms': row[5],
                    'timestamp': row[6]
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting optimization history: {e}")
            return []
    
    def stop(self):
        """Stop performance tuner"""
        self.monitoring_active = False
        self.optimization_active = False
        
        if self.monitoring_thread.is_alive():
            self.monitoring_thread.join()
        if self.optimization_thread.is_alive():
            self.optimization_thread.join()
        
        logger.info("Performance Tuner stopped")

# Global performance tuner instance
performance_tuner = PerformanceTuner()

if __name__ == '__main__':
    # Test performance tuner
    print("🚀 Testing VectorCraft Performance Tuner...")
    
    # Simulate some metrics
    import random
    
    for i in range(10):
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            metric_type='cpu_usage',
            value=random.uniform(30, 90),
            unit='%'
        )
        performance_tuner.record_metric(metric)
        time.sleep(0.1)
    
    # Get recommendations
    recommendations = performance_tuner.get_optimization_recommendations()
    print(f"\n💡 Optimization Recommendations: {len(recommendations)}")
    
    for rec in recommendations:
        print(f"  - {rec.title}: {rec.description}")
    
    # Get real-time metrics
    real_time = performance_tuner.get_real_time_metrics()
    print(f"\n📊 Real-time Metrics: {json.dumps(real_time, indent=2, default=str)}")
    
    # Stop tuner
    performance_tuner.stop()