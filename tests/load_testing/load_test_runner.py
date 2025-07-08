#!/usr/bin/env python3
"""
Load Testing Framework for VectorCraft
Comprehensive load testing using Locust with custom scenarios
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging
import gevent

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

logger = logging.getLogger(__name__)

class VectorCraftUser(HttpUser):
    """Simulated VectorCraft user behavior"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Setup for each user"""
        self.client.verify = False  # Disable SSL verification for testing
        self.login()
    
    def login(self):
        """Login to VectorCraft"""
        response = self.client.post("/login", data={
            "username": "testuser",
            "password": "testpass"
        })
        
        if response.status_code != 200:
            logger.warning(f"Login failed with status {response.status_code}")
    
    @task(10)
    def view_dashboard(self):
        """View user dashboard"""
        self.client.get("/dashboard")
    
    @task(5)
    def upload_image(self):
        """Upload image for vectorization"""
        # Simulate image upload
        files = {
            'file': ('test_image.png', b'fake_image_data', 'image/png')
        }
        
        response = self.client.post("/upload", files=files)
        
        if response.status_code == 200:
            try:
                result = response.json()
                if 'task_id' in result:
                    # Check task status
                    task_id = result['task_id']
                    self.check_task_status(task_id)
            except:
                pass
    
    def check_task_status(self, task_id):
        """Check vectorization task status"""
        for _ in range(10):  # Check up to 10 times
            response = self.client.get(f"/task/{task_id}")
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('status') == 'completed':
                        break
                except:
                    pass
            time.sleep(1)
    
    @task(3)
    def view_results(self):
        """View vectorization results"""
        self.client.get("/results")
    
    @task(2)
    def download_result(self):
        """Download vectorization result"""
        # Simulate downloading a result
        self.client.get("/download/test_result.svg")
    
    @task(1)
    def view_admin_health(self):
        """View system health (admin endpoint)"""
        self.client.get("/health")


class VectorCraftAdminUser(HttpUser):
    """Simulated admin user behavior"""
    
    wait_time = between(2, 5)  # Admin users are less frequent
    
    def on_start(self):
        """Setup for admin user"""
        self.client.verify = False
        self.admin_login()
    
    def admin_login(self):
        """Admin login"""
        response = self.client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        })
        
        if response.status_code != 200:
            logger.warning(f"Admin login failed with status {response.status_code}")
    
    @task(5)
    def view_admin_dashboard(self):
        """View admin dashboard"""
        self.client.get("/admin")
    
    @task(3)
    def view_performance_metrics(self):
        """View performance metrics"""
        self.client.get("/admin/performance")
    
    @task(2)
    def view_system_health(self):
        """View system health"""
        self.client.get("/admin/system")
    
    @task(2)
    def view_transactions(self):
        """View transactions"""
        self.client.get("/admin/transactions")
    
    @task(1)
    def view_logs(self):
        """View system logs"""
        self.client.get("/admin/logs")
    
    @task(1)
    def api_real_time_metrics(self):
        """Get real-time metrics via API"""
        self.client.get("/admin/api/performance/real-time")


class LoadTestRunner:
    """Load test runner with custom scenarios"""
    
    def __init__(self):
        self.results = {}
        self.logger = logging.getLogger(__name__)
        
    def run_basic_load_test(self, host="http://localhost:8080", users=10, spawn_rate=2, run_time=60):
        """Run basic load test"""
        self.logger.info(f"Starting basic load test: {users} users, {spawn_rate} spawn rate, {run_time}s duration")
        
        # Setup logging
        setup_logging("INFO", None)
        
        # Create environment
        env = Environment(user_classes=[VectorCraftUser])
        env.create_local_runner()
        
        # Setup event handlers
        self._setup_event_handlers()
        
        # Start test
        env.runner.start(users, spawn_rate=spawn_rate)
        
        # Run for specified time
        gevent.spawn_later(run_time, lambda: env.runner.quit())
        
        # Start web UI (optional)
        # env.create_web_ui("127.0.0.1", 8089)
        
        # Wait for test completion
        env.runner.greenlet.join()
        
        # Collect results
        stats = env.runner.stats
        self.results['basic_load_test'] = {
            'total_requests': stats.total.num_requests,
            'total_failures': stats.total.num_failures,
            'average_response_time': stats.total.avg_response_time,
            'min_response_time': stats.total.min_response_time,
            'max_response_time': stats.total.max_response_time,
            'requests_per_second': stats.total.current_rps,
            'failure_rate': stats.total.fail_ratio
        }
        
        return self.results['basic_load_test']
    
    def run_stress_test(self, host="http://localhost:8080", max_users=100, spawn_rate=5, run_time=300):
        """Run stress test with increasing load"""
        self.logger.info(f"Starting stress test: up to {max_users} users, {spawn_rate} spawn rate, {run_time}s duration")
        
        # Setup logging
        setup_logging("INFO", None)
        
        # Create environment
        env = Environment(user_classes=[VectorCraftUser])
        env.create_local_runner()
        
        # Setup event handlers
        self._setup_event_handlers()
        
        # Gradual load increase
        current_users = 10
        step_duration = run_time // 5  # 5 steps
        
        for step in range(5):
            self.logger.info(f"Step {step + 1}: {current_users} users")
            
            env.runner.start(current_users, spawn_rate=spawn_rate)
            time.sleep(step_duration)
            
            current_users = min(current_users + 20, max_users)
        
        # Final stats
        env.runner.quit()
        env.runner.greenlet.join()
        
        stats = env.runner.stats
        self.results['stress_test'] = {
            'max_users': max_users,
            'total_requests': stats.total.num_requests,
            'total_failures': stats.total.num_failures,
            'average_response_time': stats.total.avg_response_time,
            'max_response_time': stats.total.max_response_time,
            'requests_per_second': stats.total.current_rps,
            'failure_rate': stats.total.fail_ratio
        }
        
        return self.results['stress_test']
    
    def run_spike_test(self, host="http://localhost:8080", spike_users=200, normal_users=10, run_time=180):
        """Run spike test with sudden load increase"""
        self.logger.info(f"Starting spike test: spike to {spike_users} users, normal {normal_users} users")
        
        # Setup logging
        setup_logging("INFO", None)
        
        # Create environment
        env = Environment(user_classes=[VectorCraftUser])
        env.create_local_runner()
        
        # Setup event handlers
        self._setup_event_handlers()
        
        # Phase 1: Normal load
        self.logger.info("Phase 1: Normal load")
        env.runner.start(normal_users, spawn_rate=5)
        time.sleep(60)
        
        # Phase 2: Spike
        self.logger.info("Phase 2: Spike load")
        env.runner.start(spike_users, spawn_rate=20)
        time.sleep(60)
        
        # Phase 3: Back to normal
        self.logger.info("Phase 3: Back to normal")
        env.runner.start(normal_users, spawn_rate=10)
        time.sleep(60)
        
        # Final stats
        env.runner.quit()
        env.runner.greenlet.join()
        
        stats = env.runner.stats
        self.results['spike_test'] = {
            'spike_users': spike_users,
            'normal_users': normal_users,
            'total_requests': stats.total.num_requests,
            'total_failures': stats.total.num_failures,
            'average_response_time': stats.total.avg_response_time,
            'max_response_time': stats.total.max_response_time,
            'requests_per_second': stats.total.current_rps,
            'failure_rate': stats.total.fail_ratio
        }
        
        return self.results['spike_test']
    
    def run_mixed_user_test(self, host="http://localhost:8080", regular_users=20, admin_users=5, run_time=120):
        """Run mixed user test (regular + admin users)"""
        self.logger.info(f"Starting mixed user test: {regular_users} regular users, {admin_users} admin users")
        
        # Setup logging
        setup_logging("INFO", None)
        
        # Create environment with mixed user types
        env = Environment(user_classes=[VectorCraftUser, VectorCraftAdminUser])
        env.create_local_runner()
        
        # Setup event handlers
        self._setup_event_handlers()
        
        # Start mixed load
        total_users = regular_users + admin_users
        env.runner.start(total_users, spawn_rate=3)
        
        # Run for specified time
        gevent.spawn_later(run_time, lambda: env.runner.quit())
        
        # Wait for completion
        env.runner.greenlet.join()
        
        stats = env.runner.stats
        self.results['mixed_user_test'] = {
            'regular_users': regular_users,
            'admin_users': admin_users,
            'total_requests': stats.total.num_requests,
            'total_failures': stats.total.num_failures,
            'average_response_time': stats.total.avg_response_time,
            'max_response_time': stats.total.max_response_time,
            'requests_per_second': stats.total.current_rps,
            'failure_rate': stats.total.fail_ratio
        }
        
        return self.results['mixed_user_test']
    
    def _setup_event_handlers(self):
        """Setup event handlers for collecting metrics"""
        
        @events.request_success.add_listener
        def on_request_success(request_type, name, response_time, response_length, **kwargs):
            pass
        
        @events.request_failure.add_listener
        def on_request_failure(request_type, name, response_time, response_length, exception, **kwargs):
            self.logger.warning(f"Request failed: {name} - {exception}")
        
        @events.user_error.add_listener
        def on_user_error(user_instance, exception, tb, **kwargs):
            self.logger.error(f"User error: {exception}")
    
    def run_all_tests(self, host="http://localhost:8080"):
        """Run all load test scenarios"""
        self.logger.info("Starting comprehensive load test suite")
        
        test_results = {}
        
        # Test 1: Basic load test
        try:
            self.logger.info("Running basic load test...")
            test_results['basic_load'] = self.run_basic_load_test(host, users=10, run_time=60)
        except Exception as e:
            self.logger.error(f"Basic load test failed: {e}")
            test_results['basic_load'] = {'error': str(e)}
        
        # Test 2: Stress test
        try:
            self.logger.info("Running stress test...")
            test_results['stress_test'] = self.run_stress_test(host, max_users=50, run_time=180)
        except Exception as e:
            self.logger.error(f"Stress test failed: {e}")
            test_results['stress_test'] = {'error': str(e)}
        
        # Test 3: Spike test
        try:
            self.logger.info("Running spike test...")
            test_results['spike_test'] = self.run_spike_test(host, spike_users=100, run_time=180)
        except Exception as e:
            self.logger.error(f"Spike test failed: {e}")
            test_results['spike_test'] = {'error': str(e)}
        
        # Test 4: Mixed user test
        try:
            self.logger.info("Running mixed user test...")
            test_results['mixed_user'] = self.run_mixed_user_test(host, regular_users=15, admin_users=5, run_time=120)
        except Exception as e:
            self.logger.error(f"Mixed user test failed: {e}")
            test_results['mixed_user'] = {'error': str(e)}
        
        # Save results
        self.save_results(test_results)
        
        return test_results
    
    def save_results(self, results):
        """Save test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"load_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Test results saved to {filename}")
    
    def generate_report(self, results):
        """Generate performance test report"""
        report = []
        report.append("VectorCraft Load Test Report")
        report.append("=" * 50)
        report.append(f"Generated: {datetime.now()}")
        report.append("")
        
        for test_name, result in results.items():
            if 'error' in result:
                report.append(f"❌ {test_name.upper()}: FAILED - {result['error']}")
                continue
            
            report.append(f"✅ {test_name.upper()}")
            report.append(f"   Total Requests: {result.get('total_requests', 0)}")
            report.append(f"   Total Failures: {result.get('total_failures', 0)}")
            report.append(f"   Average Response Time: {result.get('average_response_time', 0):.1f}ms")
            report.append(f"   Max Response Time: {result.get('max_response_time', 0):.1f}ms")
            report.append(f"   Requests/Second: {result.get('requests_per_second', 0):.1f}")
            report.append(f"   Failure Rate: {result.get('failure_rate', 0):.2%}")
            report.append("")
        
        return "\n".join(report)


def main():
    """Main entry point for load testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="VectorCraft Load Testing")
    parser.add_argument("--host", default="http://localhost:8080", help="Target host")
    parser.add_argument("--test", choices=['basic', 'stress', 'spike', 'mixed', 'all'], 
                       default='all', help="Test type to run")
    parser.add_argument("--users", type=int, default=10, help="Number of users")
    parser.add_argument("--time", type=int, default=60, help="Test duration in seconds")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create test runner
    runner = LoadTestRunner()
    
    # Run specified test
    if args.test == 'basic':
        results = runner.run_basic_load_test(args.host, args.users, run_time=args.time)
    elif args.test == 'stress':
        results = runner.run_stress_test(args.host, max_users=args.users, run_time=args.time)
    elif args.test == 'spike':
        results = runner.run_spike_test(args.host, spike_users=args.users, run_time=args.time)
    elif args.test == 'mixed':
        results = runner.run_mixed_user_test(args.host, regular_users=args.users, run_time=args.time)
    else:
        results = runner.run_all_tests(args.host)
    
    # Generate and display report
    report = runner.generate_report(results if isinstance(results, dict) else {args.test: results})
    print("\n" + report)
    
    return results


if __name__ == "__main__":
    main()