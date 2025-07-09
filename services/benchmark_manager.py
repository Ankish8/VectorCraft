#!/usr/bin/env python3
"""
Benchmark Manager for Performance Testing & Comparison
Comprehensive benchmarking tools for VectorCraft performance analysis
"""

import os
import time
import json
import logging
import threading
import statistics
import subprocess
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import sqlite3
import uuid
import psutil

# Load testing imports
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class BenchmarkTest:
    """Benchmark test configuration"""
    id: str
    name: str
    description: str
    test_type: str  # load, stress, endurance, spike
    duration_seconds: int
    concurrent_users: int
    ramp_up_time: int
    target_endpoint: str
    payload: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    success_criteria: Optional[Dict[str, Any]] = None
    tags: List[str] = None

@dataclass
class BenchmarkResult:
    """Benchmark test result"""
    test_id: str
    timestamp: datetime
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput: float
    error_rate: float
    errors: List[str]
    system_metrics: Dict[str, Any]
    success: bool
    score: float

@dataclass
class BenchmarkComparison:
    """Comparison between benchmark results"""
    baseline_result: BenchmarkResult
    current_result: BenchmarkResult
    improvement_percentage: float
    regression_detected: bool
    significant_changes: List[str]
    recommendation: str

class BenchmarkManager:
    """Comprehensive benchmark management system"""
    
    def __init__(self, db_path: str = "vectorcraft.db", base_url: str = "http://localhost:8080"):
        self.db_path = db_path
        self.base_url = base_url
        self.test_results = deque(maxlen=1000)
        self.active_tests = {}
        self.benchmark_templates = self._load_benchmark_templates()
        
        # Performance thresholds
        self.performance_thresholds = {
            'response_time_ms': 500,
            'throughput_rps': 10,
            'error_rate_percent': 2.0,
            'cpu_usage_percent': 80,
            'memory_usage_percent': 85
        }
        
        # Initialize database
        self._init_database()
        
        logger.info("Benchmark Manager initialized")
    
    def _load_benchmark_templates(self) -> Dict[str, BenchmarkTest]:
        """Load predefined benchmark test templates"""
        templates = {}
        
        # Load test - Basic endpoint performance
        templates['load_basic'] = BenchmarkTest(
            id='load_basic',
            name='Basic Load Test',
            description='Basic load test for main endpoints',
            test_type='load',
            duration_seconds=60,
            concurrent_users=10,
            ramp_up_time=10,
            target_endpoint='/health',
            success_criteria={
                'avg_response_time': 200,
                'error_rate': 0.01,
                'throughput': 50
            },
            tags=['basic', 'health-check']
        )
        
        # Load test - Vectorization
        templates['load_vectorization'] = BenchmarkTest(
            id='load_vectorization',
            name='Vectorization Load Test',
            description='Load test for vectorization endpoints',
            test_type='load',
            duration_seconds=300,
            concurrent_users=5,
            ramp_up_time=30,
            target_endpoint='/api/vectorize',
            payload={
                'algorithm': 'vtracer_high_fidelity',
                'test_mode': True
            },
            headers={'Content-Type': 'application/json'},
            success_criteria={
                'avg_response_time': 5000,
                'error_rate': 0.05,
                'throughput': 2
            },
            tags=['vectorization', 'core-functionality']
        )
        
        # Stress test - High load
        templates['stress_high_load'] = BenchmarkTest(
            id='stress_high_load',
            name='High Load Stress Test',
            description='Stress test with high concurrent load',
            test_type='stress',
            duration_seconds=180,
            concurrent_users=50,
            ramp_up_time=30,
            target_endpoint='/dashboard',
            success_criteria={
                'avg_response_time': 1000,
                'error_rate': 0.1,
                'throughput': 40
            },
            tags=['stress', 'dashboard']
        )
        
        # Endurance test - Long duration
        templates['endurance_long'] = BenchmarkTest(
            id='endurance_long',
            name='Long Duration Endurance Test',
            description='Test system stability over extended period',
            test_type='endurance',
            duration_seconds=1800,  # 30 minutes
            concurrent_users=15,
            ramp_up_time=60,
            target_endpoint='/api/health',
            success_criteria={
                'avg_response_time': 300,
                'error_rate': 0.02,
                'throughput': 30
            },
            tags=['endurance', 'stability']
        )
        
        # Spike test - Sudden load increase
        templates['spike_sudden'] = BenchmarkTest(
            id='spike_sudden',
            name='Sudden Spike Test',
            description='Test response to sudden traffic spikes',
            test_type='spike',
            duration_seconds=120,
            concurrent_users=100,
            ramp_up_time=5,  # Very fast ramp-up
            target_endpoint='/login',
            success_criteria={
                'avg_response_time': 800,
                'error_rate': 0.15,
                'throughput': 20
            },
            tags=['spike', 'authentication']
        )
        
        return templates
    
    def _init_database(self):
        """Initialize benchmark database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Benchmark tests table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS benchmark_tests (
                    id TEXT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    test_type VARCHAR(50),
                    duration_seconds INTEGER,
                    concurrent_users INTEGER,
                    ramp_up_time INTEGER,
                    target_endpoint VARCHAR(200),
                    payload TEXT,
                    headers TEXT,
                    success_criteria TEXT,
                    tags TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Benchmark results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS benchmark_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    duration_seconds REAL,
                    total_requests INTEGER,
                    successful_requests INTEGER,
                    failed_requests INTEGER,
                    avg_response_time REAL,
                    min_response_time REAL,
                    max_response_time REAL,
                    p95_response_time REAL,
                    p99_response_time REAL,
                    throughput REAL,
                    error_rate REAL,
                    errors TEXT,
                    system_metrics TEXT,
                    success BOOLEAN,
                    score REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Benchmark comparisons table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS benchmark_comparisons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    baseline_result_id INTEGER,
                    current_result_id INTEGER,
                    improvement_percentage REAL,
                    regression_detected BOOLEAN,
                    significant_changes TEXT,
                    recommendation TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Performance baselines table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_baselines (
                    test_id TEXT PRIMARY KEY,
                    baseline_result_id INTEGER,
                    avg_response_time REAL,
                    throughput REAL,
                    error_rate REAL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    def run_benchmark(self, test_id: str, custom_params: Optional[Dict[str, Any]] = None) -> BenchmarkResult:
        """Run a benchmark test"""
        if test_id not in self.benchmark_templates:
            raise ValueError(f"Unknown benchmark test: {test_id}")
        
        test = self.benchmark_templates[test_id]
        
        # Apply custom parameters if provided
        if custom_params:
            test = self._apply_custom_params(test, custom_params)
        
        logger.info(f"Starting benchmark test: {test.name}")
        
        # Check if requests is available
        if not REQUESTS_AVAILABLE:
            logger.error("Requests library not available. Cannot run HTTP benchmarks.")
            return self._create_error_result(test, "Requests library not available")
        
        # Mark test as active
        self.active_tests[test_id] = {
            'test': test,
            'start_time': datetime.now(),
            'status': 'running'
        }
        
        try:
            # Run the actual benchmark
            result = self._execute_benchmark(test)
            
            # Save result
            self._save_benchmark_result(result)
            self.test_results.append(result)
            
            # Update active tests
            self.active_tests[test_id]['status'] = 'completed'
            self.active_tests[test_id]['result'] = result
            
            logger.info(f"Benchmark completed: {test.name} - Score: {result.score:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Benchmark error: {e}")
            error_result = self._create_error_result(test, str(e))
            self.active_tests[test_id]['status'] = 'failed'
            self.active_tests[test_id]['result'] = error_result
            return error_result
        
        finally:
            # Clean up active test after some time
            threading.Timer(300, lambda: self.active_tests.pop(test_id, None)).start()
    
    def _apply_custom_params(self, test: BenchmarkTest, custom_params: Dict[str, Any]) -> BenchmarkTest:
        """Apply custom parameters to benchmark test"""
        # Create a copy of the test with custom parameters
        test_dict = asdict(test)
        test_dict.update(custom_params)
        return BenchmarkTest(**test_dict)
    
    def _execute_benchmark(self, test: BenchmarkTest) -> BenchmarkResult:
        """Execute the actual benchmark test"""
        start_time = time.time()
        
        # Initialize metrics
        response_times = []
        errors = []
        successful_requests = 0
        failed_requests = 0
        
        # System metrics collection
        system_metrics_before = self._collect_system_metrics()
        
        # Create URL
        url = f"{self.base_url}{test.target_endpoint}"
        
        # Prepare request parameters
        request_params = {
            'timeout': 30,
            'headers': test.headers or {}
        }
        
        if test.payload:
            request_params['json'] = test.payload
        
        # Calculate requests per second for ramp-up
        total_requests = test.concurrent_users * test.duration_seconds
        requests_per_second = total_requests / test.duration_seconds
        
        # Execute benchmark with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=test.concurrent_users) as executor:
            # Submit initial requests
            futures = []
            
            # Ramp-up phase
            ramp_up_interval = test.ramp_up_time / test.concurrent_users if test.ramp_up_time > 0 else 0
            
            for i in range(test.concurrent_users):
                # Stagger request starts during ramp-up
                if ramp_up_interval > 0:
                    time.sleep(ramp_up_interval)
                
                future = executor.submit(self._execute_request_series, url, request_params, test.duration_seconds)
                futures.append(future)
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                try:
                    thread_results = future.result()
                    response_times.extend(thread_results['response_times'])
                    errors.extend(thread_results['errors'])
                    successful_requests += thread_results['successful_requests']
                    failed_requests += thread_results['failed_requests']
                except Exception as e:
                    errors.append(f"Thread execution error: {str(e)}")
        
        # Calculate duration
        actual_duration = time.time() - start_time
        
        # Collect system metrics after test
        system_metrics_after = self._collect_system_metrics()
        
        # Calculate statistics
        total_requests = successful_requests + failed_requests
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            # Calculate percentiles
            sorted_times = sorted(response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p99_index = int(len(sorted_times) * 0.99)
            
            p95_response_time = sorted_times[p95_index] if p95_index < len(sorted_times) else max_response_time
            p99_response_time = sorted_times[p99_index] if p99_index < len(sorted_times) else max_response_time
        else:
            avg_response_time = 0
            min_response_time = 0
            max_response_time = 0
            p95_response_time = 0
            p99_response_time = 0
        
        # Calculate throughput and error rate
        throughput = successful_requests / actual_duration if actual_duration > 0 else 0
        error_rate = failed_requests / total_requests if total_requests > 0 else 0
        
        # Calculate system metrics delta
        system_metrics_delta = self._calculate_system_metrics_delta(system_metrics_before, system_metrics_after)
        
        # Determine success based on criteria
        success = self._evaluate_success_criteria(test, {
            'avg_response_time': avg_response_time,
            'throughput': throughput,
            'error_rate': error_rate
        })
        
        # Calculate performance score
        score = self._calculate_performance_score(test, {
            'avg_response_time': avg_response_time,
            'throughput': throughput,
            'error_rate': error_rate,
            'system_metrics': system_metrics_delta
        })
        
        # Create result
        result = BenchmarkResult(
            test_id=test.id,
            timestamp=datetime.now(),
            duration_seconds=actual_duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            throughput=throughput,
            error_rate=error_rate,
            errors=errors[:100],  # Limit errors stored
            system_metrics=system_metrics_delta,
            success=success,
            score=score
        )
        
        return result
    
    def _execute_request_series(self, url: str, request_params: Dict[str, Any], duration: int) -> Dict[str, Any]:
        """Execute a series of requests for a single thread"""
        response_times = []
        errors = []
        successful_requests = 0
        failed_requests = 0
        
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                request_start = time.time()
                
                # Make request
                if 'json' in request_params:
                    response = requests.post(url, **request_params)
                else:
                    response = requests.get(url, **request_params)
                
                request_duration = (time.time() - request_start) * 1000  # Convert to ms
                
                # Check response
                if response.status_code < 400:
                    successful_requests += 1
                    response_times.append(request_duration)
                else:
                    failed_requests += 1
                    errors.append(f"HTTP {response.status_code}: {response.text[:100]}")
                
            except requests.exceptions.RequestException as e:
                failed_requests += 1
                errors.append(f"Request error: {str(e)}")
            
            except Exception as e:
                failed_requests += 1
                errors.append(f"Unexpected error: {str(e)}")
            
            # Small delay to prevent overwhelming the server
            time.sleep(0.01)
        
        return {
            'response_times': response_times,
            'errors': errors,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests
        }
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system metrics for benchmark"""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            disk = psutil.disk_usage('/')
            
            return {
                'timestamp': datetime.now().isoformat(),
                'memory_percent': memory.percent,
                'memory_used': memory.used,
                'memory_total': memory.total,
                'cpu_percent': cpu_percent,
                'disk_percent': disk.percent,
                'disk_used': disk.used,
                'disk_total': disk.total
            }
        except Exception as e:
            logger.error(f"System metrics collection error: {e}")
            return {}
    
    def _calculate_system_metrics_delta(self, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate system metrics delta"""
        if not before or not after:
            return {}
        
        delta = {}
        
        for key in ['memory_percent', 'cpu_percent', 'disk_percent']:
            if key in before and key in after:
                delta[f"{key}_delta"] = after[key] - before[key]
        
        for key in ['memory_used', 'disk_used']:
            if key in before and key in after:
                delta[f"{key}_delta"] = after[key] - before[key]
        
        return delta
    
    def _evaluate_success_criteria(self, test: BenchmarkTest, metrics: Dict[str, Any]) -> bool:
        """Evaluate if benchmark meets success criteria"""
        if not test.success_criteria:
            return True
        
        criteria = test.success_criteria
        
        # Check average response time
        if 'avg_response_time' in criteria:
            if metrics['avg_response_time'] > criteria['avg_response_time']:
                return False
        
        # Check throughput
        if 'throughput' in criteria:
            if metrics['throughput'] < criteria['throughput']:
                return False
        
        # Check error rate
        if 'error_rate' in criteria:
            if metrics['error_rate'] > criteria['error_rate']:
                return False
        
        return True
    
    def _calculate_performance_score(self, test: BenchmarkTest, metrics: Dict[str, Any]) -> float:
        """Calculate performance score (0-100)"""
        score = 100.0
        
        # Response time score (lower is better)
        if metrics['avg_response_time'] > 0:
            response_time_penalty = min(50, metrics['avg_response_time'] / 20)
            score -= response_time_penalty
        
        # Throughput score (higher is better)
        if metrics['throughput'] > 0:
            throughput_bonus = min(20, metrics['throughput'] / 5)
            score += throughput_bonus - 20  # Normalize
        
        # Error rate penalty
        error_rate_penalty = min(30, metrics['error_rate'] * 1000)
        score -= error_rate_penalty
        
        # System resource penalty
        system_metrics = metrics.get('system_metrics', {})
        if 'cpu_percent_delta' in system_metrics:
            cpu_penalty = min(10, max(0, system_metrics['cpu_percent_delta'] / 5))
            score -= cpu_penalty
        
        if 'memory_percent_delta' in system_metrics:
            memory_penalty = min(10, max(0, system_metrics['memory_percent_delta'] / 5))
            score -= memory_penalty
        
        return max(0, min(100, score))
    
    def _create_error_result(self, test: BenchmarkTest, error_message: str) -> BenchmarkResult:
        """Create error result for failed benchmark"""
        return BenchmarkResult(
            test_id=test.id,
            timestamp=datetime.now(),
            duration_seconds=0,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            avg_response_time=0,
            min_response_time=0,
            max_response_time=0,
            p95_response_time=0,
            p99_response_time=0,
            throughput=0,
            error_rate=1.0,
            errors=[error_message],
            system_metrics={},
            success=False,
            score=0
        )
    
    def _save_benchmark_result(self, result: BenchmarkResult):
        """Save benchmark result to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO benchmark_results 
                (test_id, timestamp, duration_seconds, total_requests, successful_requests, 
                 failed_requests, avg_response_time, min_response_time, max_response_time, 
                 p95_response_time, p99_response_time, throughput, error_rate, errors, 
                 system_metrics, success, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.test_id,
                result.timestamp,
                result.duration_seconds,
                result.total_requests,
                result.successful_requests,
                result.failed_requests,
                result.avg_response_time,
                result.min_response_time,
                result.max_response_time,
                result.p95_response_time,
                result.p99_response_time,
                result.throughput,
                result.error_rate,
                json.dumps(result.errors),
                json.dumps(result.system_metrics),
                result.success,
                result.score
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving benchmark result: {e}")
    
    def compare_results(self, baseline_test_id: str, current_test_id: str) -> BenchmarkComparison:
        """Compare two benchmark results"""
        baseline_result = self._get_latest_result(baseline_test_id)
        current_result = self._get_latest_result(current_test_id)
        
        if not baseline_result or not current_result:
            raise ValueError("Cannot find results for comparison")
        
        # Calculate improvement percentage
        improvement = ((current_result.score - baseline_result.score) / baseline_result.score) * 100
        
        # Detect regression
        regression_detected = current_result.score < baseline_result.score * 0.95  # 5% threshold
        
        # Identify significant changes
        significant_changes = []
        
        # Response time change
        response_time_change = ((current_result.avg_response_time - baseline_result.avg_response_time) / baseline_result.avg_response_time) * 100
        if abs(response_time_change) > 10:  # 10% threshold
            direction = "increased" if response_time_change > 0 else "decreased"
            significant_changes.append(f"Response time {direction} by {abs(response_time_change):.1f}%")
        
        # Throughput change
        throughput_change = ((current_result.throughput - baseline_result.throughput) / baseline_result.throughput) * 100
        if abs(throughput_change) > 15:  # 15% threshold
            direction = "increased" if throughput_change > 0 else "decreased"
            significant_changes.append(f"Throughput {direction} by {abs(throughput_change):.1f}%")
        
        # Error rate change
        error_rate_change = current_result.error_rate - baseline_result.error_rate
        if abs(error_rate_change) > 0.01:  # 1% threshold
            direction = "increased" if error_rate_change > 0 else "decreased"
            significant_changes.append(f"Error rate {direction} by {abs(error_rate_change * 100):.1f}%")
        
        # Generate recommendation
        recommendation = self._generate_comparison_recommendation(
            baseline_result, current_result, improvement, regression_detected, significant_changes
        )
        
        comparison = BenchmarkComparison(
            baseline_result=baseline_result,
            current_result=current_result,
            improvement_percentage=improvement,
            regression_detected=regression_detected,
            significant_changes=significant_changes,
            recommendation=recommendation
        )
        
        # Save comparison
        self._save_comparison(comparison)
        
        return comparison
    
    def _get_latest_result(self, test_id: str) -> Optional[BenchmarkResult]:
        """Get latest result for test"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM benchmark_results 
                WHERE test_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (test_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return BenchmarkResult(
                    test_id=row[1],
                    timestamp=datetime.fromisoformat(row[2]),
                    duration_seconds=row[3],
                    total_requests=row[4],
                    successful_requests=row[5],
                    failed_requests=row[6],
                    avg_response_time=row[7],
                    min_response_time=row[8],
                    max_response_time=row[9],
                    p95_response_time=row[10],
                    p99_response_time=row[11],
                    throughput=row[12],
                    error_rate=row[13],
                    errors=json.loads(row[14]) if row[14] else [],
                    system_metrics=json.loads(row[15]) if row[15] else {},
                    success=bool(row[16]),
                    score=row[17]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest result: {e}")
            return None
    
    def _generate_comparison_recommendation(self, baseline: BenchmarkResult, current: BenchmarkResult, 
                                         improvement: float, regression: bool, changes: List[str]) -> str:
        """Generate recommendation based on comparison"""
        if regression:
            return f"Performance regression detected ({improvement:.1f}% decrease). Consider investigating: {', '.join(changes)}"
        
        if improvement > 10:
            return f"Significant performance improvement detected ({improvement:.1f}% increase). Changes: {', '.join(changes) if changes else 'No significant changes'}"
        
        if improvement > 5:
            return f"Moderate performance improvement ({improvement:.1f}% increase). Continue monitoring."
        
        if improvement < -5:
            return f"Performance degradation detected ({improvement:.1f}% decrease). Consider optimization."
        
        return "Performance is stable with no significant changes."
    
    def _save_comparison(self, comparison: BenchmarkComparison):
        """Save comparison to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Note: This is a simplified version - in practice, you'd need to store result IDs
            cursor.execute('''
                INSERT INTO benchmark_comparisons 
                (baseline_result_id, current_result_id, improvement_percentage, 
                 regression_detected, significant_changes, recommendation)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                0,  # Would be actual result ID
                0,  # Would be actual result ID
                comparison.improvement_percentage,
                comparison.regression_detected,
                json.dumps(comparison.significant_changes),
                comparison.recommendation
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving comparison: {e}")
    
    def get_benchmark_history(self, test_id: str, days: int = 7) -> List[BenchmarkResult]:
        """Get benchmark history for a test"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT * FROM benchmark_results 
                WHERE test_id = ? AND timestamp > ?
                ORDER BY timestamp DESC
            ''', (test_id, cutoff_date))
            
            results = []
            for row in cursor.fetchall():
                result = BenchmarkResult(
                    test_id=row[1],
                    timestamp=datetime.fromisoformat(row[2]),
                    duration_seconds=row[3],
                    total_requests=row[4],
                    successful_requests=row[5],
                    failed_requests=row[6],
                    avg_response_time=row[7],
                    min_response_time=row[8],
                    max_response_time=row[9],
                    p95_response_time=row[10],
                    p99_response_time=row[11],
                    throughput=row[12],
                    error_rate=row[13],
                    errors=json.loads(row[14]) if row[14] else [],
                    system_metrics=json.loads(row[15]) if row[15] else {},
                    success=bool(row[16]),
                    score=row[17]
                )
                results.append(result)
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Error getting benchmark history: {e}")
            return []
    
    def get_available_tests(self) -> List[Dict[str, Any]]:
        """Get list of available benchmark tests"""
        return [
            {
                'id': test.id,
                'name': test.name,
                'description': test.description,
                'test_type': test.test_type,
                'duration_seconds': test.duration_seconds,
                'concurrent_users': test.concurrent_users,
                'tags': test.tags or []
            }
            for test in self.benchmark_templates.values()
        ]
    
    def get_active_tests(self) -> Dict[str, Any]:
        """Get currently active benchmark tests"""
        return {
            test_id: {
                'name': data['test'].name,
                'start_time': data['start_time'].isoformat(),
                'status': data['status'],
                'duration': (datetime.now() - data['start_time']).total_seconds()
            }
            for test_id, data in self.active_tests.items()
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary across all tests"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get recent results
            cutoff_date = datetime.now() - timedelta(days=7)
            cursor.execute('''
                SELECT test_id, AVG(score), AVG(avg_response_time), AVG(throughput), 
                       AVG(error_rate), COUNT(*) as test_count
                FROM benchmark_results 
                WHERE timestamp > ?
                GROUP BY test_id
            ''', (cutoff_date,))
            
            results = cursor.fetchall()
            conn.close()
            
            summary = {
                'total_tests_run': len(results),
                'avg_performance_score': 0,
                'avg_response_time': 0,
                'avg_throughput': 0,
                'avg_error_rate': 0,
                'test_details': []
            }
            
            if results:
                summary['avg_performance_score'] = sum(row[1] for row in results) / len(results)
                summary['avg_response_time'] = sum(row[2] for row in results) / len(results)
                summary['avg_throughput'] = sum(row[3] for row in results) / len(results)
                summary['avg_error_rate'] = sum(row[4] for row in results) / len(results)
                
                summary['test_details'] = [
                    {
                        'test_id': row[0],
                        'avg_score': row[1],
                        'avg_response_time': row[2],
                        'avg_throughput': row[3],
                        'avg_error_rate': row[4],
                        'test_count': row[5]
                    }
                    for row in results
                ]
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {'error': str(e)}

# Global benchmark manager instance
benchmark_manager = BenchmarkManager()

if __name__ == '__main__':
    # Test benchmark manager
    print("🏁 Testing VectorCraft Benchmark Manager...")
    
    # Get available tests
    tests = benchmark_manager.get_available_tests()
    print(f"\n📋 Available Tests: {len(tests)}")
    
    for test in tests:
        print(f"  - {test['name']}: {test['description']}")
    
    # Run a simple benchmark (if requests is available)
    if REQUESTS_AVAILABLE:
        try:
            print("\n🏃 Running basic load test...")
            result = benchmark_manager.run_benchmark('load_basic')
            print(f"✅ Test completed - Score: {result.score:.2f}")
            print(f"   Response time: {result.avg_response_time:.2f}ms")
            print(f"   Throughput: {result.throughput:.2f} req/s")
            print(f"   Error rate: {result.error_rate:.2%}")
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    # Get performance summary
    summary = benchmark_manager.get_performance_summary()
    print(f"\n📊 Performance Summary: {json.dumps(summary, indent=2)}")