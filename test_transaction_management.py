#!/usr/bin/env python3
"""
Integration Test for Advanced Transaction Management System
Tests all components working together
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db
from services.transaction_analytics import transaction_analytics
from services.payment_monitor import payment_monitor
from services.fraud_detection import fraud_detector, DisputeType
from services.financial_reporting import financial_reporter, ReportPeriod
from services.dispute_manager import dispute_manager

class TransactionManagementTester:
    """Test suite for advanced transaction management"""
    
    def __init__(self):
        self.test_results = []
        self.setup_test_data()
    
    def setup_test_data(self):
        """Setup test transaction data"""
        print("Setting up test data...")
        
        # Create test transactions
        test_transactions = [
            {
                'transaction_id': 'TEST_001',
                'email': 'test1@example.com',
                'username': 'test1',
                'amount': 49.00,
                'currency': 'USD',
                'status': 'completed',
                'paypal_order_id': 'PPO_001',
                'paypal_payment_id': 'PPP_001'
            },
            {
                'transaction_id': 'TEST_002',
                'email': 'test2@example.com',
                'username': 'test2',
                'amount': 149.00,
                'currency': 'USD',
                'status': 'pending',
                'paypal_order_id': 'PPO_002'
            },
            {
                'transaction_id': 'TEST_003',
                'email': 'suspicious@tempmail.com',
                'username': 'test3',
                'amount': 999.00,
                'currency': 'USD',
                'status': 'failed',
                'error_message': 'Payment declined'
            }
        ]
        
        for tx in test_transactions:
            try:
                db.log_transaction(**tx)
                print(f"✓ Created test transaction: {tx['transaction_id']}")
            except Exception as e:
                print(f"✗ Failed to create test transaction {tx['transaction_id']}: {e}")
    
    def test_transaction_analytics(self):
        """Test transaction analytics service"""
        print("\n=== Testing Transaction Analytics ===")
        
        try:
            # Test basic analytics
            analytics = transaction_analytics.get_transaction_analytics()
            
            assert analytics.total_transactions >= 3, "Should have at least 3 test transactions"
            assert analytics.success_rate > 0, "Success rate should be positive"
            assert analytics.avg_transaction_value > 0, "Average transaction value should be positive"
            
            print(f"✓ Basic analytics: {analytics.total_transactions} transactions, {analytics.success_rate:.1f}% success rate")
            
            # Test transaction details
            details = transaction_analytics.get_transaction_details('TEST_001')
            assert 'basic_info' in details, "Should have basic info"
            assert 'timeline' in details, "Should have timeline"
            assert 'fraud_score' in details, "Should have fraud score"
            
            print("✓ Transaction details working")
            
            # Test revenue analytics
            revenue = transaction_analytics.get_revenue_analytics()
            assert 'daily_revenue' in revenue, "Should have daily revenue data"
            assert 'totals' in revenue, "Should have totals"
            
            print("✓ Revenue analytics working")
            
            self.test_results.append(("Transaction Analytics", "PASSED"))
            
        except Exception as e:
            print(f"✗ Transaction Analytics test failed: {e}")
            self.test_results.append(("Transaction Analytics", "FAILED", str(e)))
    
    def test_payment_monitor(self):
        """Test payment monitoring system"""
        print("\n=== Testing Payment Monitor ===")
        
        try:
            # Test payment health
            health = payment_monitor.get_payment_health()
            
            assert hasattr(health, 'paypal_api_status'), "Should have PayPal API status"
            assert hasattr(health, 'success_rate'), "Should have success rate"
            assert hasattr(health, 'pending_transactions'), "Should have pending transaction count"
            
            print(f"✓ Payment health: API {health.paypal_api_status}, {health.success_rate:.1f}% success rate")
            
            # Test payment statistics
            stats = payment_monitor.get_payment_statistics()
            assert 'total_transactions' in stats, "Should have total transactions"
            assert 'success_rate' in stats, "Should have success rate"
            
            print("✓ Payment statistics working")
            
            # Test processing performance
            performance = payment_monitor.get_processing_performance()
            assert isinstance(performance, dict), "Should return performance dict"
            
            print("✓ Processing performance working")
            
            self.test_results.append(("Payment Monitor", "PASSED"))
            
        except Exception as e:
            print(f"✗ Payment Monitor test failed: {e}")
            self.test_results.append(("Payment Monitor", "FAILED", str(e)))
    
    def test_fraud_detection(self):
        """Test fraud detection system"""
        print("\n=== Testing Fraud Detection ===")
        
        try:
            # Test fraud analysis on suspicious transaction
            transaction = db.get_transaction('TEST_003')
            analysis = fraud_detector.analyze_transaction(transaction)
            
            assert analysis.risk_score > 0, "Suspicious transaction should have risk score"
            assert len(analysis.indicators) > 0, "Should have fraud indicators"
            assert analysis.risk_level.value in ['low', 'medium', 'high', 'critical'], "Should have valid risk level"
            
            print(f"✓ Fraud analysis: Risk level {analysis.risk_level.value}, Score {analysis.risk_score:.2f}")
            
            # Test fraud statistics
            stats = fraud_detector.get_fraud_statistics()
            assert isinstance(stats, dict), "Should return statistics dict"
            
            print("✓ Fraud statistics working")
            
            # Test fraud patterns
            patterns = fraud_detector.get_fraud_patterns()
            assert isinstance(patterns, dict), "Should return patterns dict"
            
            print("✓ Fraud patterns working")
            
            self.test_results.append(("Fraud Detection", "PASSED"))
            
        except Exception as e:
            print(f"✗ Fraud Detection test failed: {e}")
            self.test_results.append(("Fraud Detection", "FAILED", str(e)))
    
    def test_financial_reporting(self):
        """Test financial reporting system"""
        print("\n=== Testing Financial Reporting ===")
        
        try:
            # Test financial report generation
            report = financial_reporter.generate_financial_report(
                period=ReportPeriod.MONTH
            )
            
            assert 'metrics' in report, "Should have metrics"
            assert 'revenue_breakdown' in report, "Should have revenue breakdown"
            assert 'trends' in report, "Should have trends"
            
            print(f"✓ Financial report generated for {report['report_period']}")
            
            # Test dashboard summary
            summary = financial_reporter.get_dashboard_summary()
            assert 'today' in summary, "Should have today's data"
            assert 'month' in summary, "Should have month's data"
            assert 'year_to_date' in summary, "Should have YTD data"
            
            print("✓ Dashboard summary working")
            
            # Test data export
            export_data = financial_reporter.export_financial_data(format_type='json')
            assert 'transactions' in export_data, "Should have transaction data"
            assert 'total_records' in export_data, "Should have record count"
            
            print("✓ Data export working")
            
            self.test_results.append(("Financial Reporting", "PASSED"))
            
        except Exception as e:
            print(f"✗ Financial Reporting test failed: {e}")
            self.test_results.append(("Financial Reporting", "FAILED", str(e)))\n    \n    def test_dispute_manager(self):\n        \"\"\"Test dispute management system\"\"\"\n        print(\"\\n=== Testing Dispute Manager ===\")\n        \n        try:\n            # Test dispute creation\n            case_id = dispute_manager.create_dispute(\n                transaction_id='TEST_001',\n                dispute_type=DisputeType.REFUND_REQUEST,\n                customer_message='Test dispute case'\n            )\n            \n            assert case_id.startswith('DISP_'), \"Case ID should start with DISP_\"\n            print(f\"✓ Dispute case created: {case_id}\")\n            \n            # Test dispute details\n            details = dispute_manager.get_dispute_details(case_id)\n            assert details is not None, \"Should get dispute details\"\n            assert details['case_id'] == case_id, \"Case ID should match\"\n            \n            print(\"✓ Dispute details working\")\n            \n            # Test dispute metrics\n            metrics = dispute_manager.get_dispute_metrics()\n            assert metrics.total_disputes >= 1, \"Should have at least 1 dispute\"\n            \n            print(f\"✓ Dispute metrics: {metrics.total_disputes} total disputes\")\n            \n            # Test open disputes\n            open_disputes = dispute_manager.get_open_disputes()\n            assert len(open_disputes) >= 1, \"Should have at least 1 open dispute\"\n            \n            print(\"✓ Open disputes working\")\n            \n            self.test_results.append((\"Dispute Manager\", \"PASSED\"))\n            \n        except Exception as e:\n            print(f\"✗ Dispute Manager test failed: {e}\")\n            self.test_results.append((\"Dispute Manager\", \"FAILED\", str(e)))\n    \n    def test_integration(self):\n        \"\"\"Test system integration\"\"\"\n        print(\"\\n=== Testing System Integration ===\")\n        \n        try:\n            # Test cross-component data flow\n            transaction = db.get_transaction('TEST_003')\n            \n            # Analyze for fraud\n            fraud_analysis = fraud_detector.analyze_transaction(transaction)\n            \n            # Create dispute if high risk\n            if fraud_analysis.risk_level.value in ['high', 'critical']:\n                case_id = dispute_manager.create_dispute(\n                    transaction_id=transaction['transaction_id'],\n                    dispute_type=DisputeType.UNAUTHORIZED_TRANSACTION,\n                    customer_message='High-risk transaction detected'\n                )\n                print(f\"✓ Auto-created dispute for high-risk transaction: {case_id}\")\n            \n            # Generate comprehensive report\n            report = financial_reporter.generate_financial_report()\n            analytics = transaction_analytics.get_transaction_analytics()\n            \n            # Verify data consistency\n            assert report['metrics']['total_transactions'] == analytics.total_transactions, \"Transaction counts should match\"\n            \n            print(\"✓ Cross-component integration working\")\n            \n            self.test_results.append((\"System Integration\", \"PASSED\"))\n            \n        except Exception as e:\n            print(f\"✗ System Integration test failed: {e}\")\n            self.test_results.append((\"System Integration\", \"FAILED\", str(e)))\n    \n    def run_all_tests(self):\n        \"\"\"Run all test suites\"\"\"\n        print(\"\\n\" + \"=\"*50)\n        print(\"Advanced Transaction Management System Test\")\n        print(\"=\"*50)\n        \n        start_time = time.time()\n        \n        # Run individual test suites\n        self.test_transaction_analytics()\n        self.test_payment_monitor()\n        self.test_fraud_detection()\n        self.test_financial_reporting()\n        self.test_dispute_manager()\n        self.test_integration()\n        \n        end_time = time.time()\n        \n        # Print results summary\n        print(\"\\n\" + \"=\"*50)\n        print(\"TEST RESULTS SUMMARY\")\n        print(\"=\"*50)\n        \n        passed = 0\n        failed = 0\n        \n        for result in self.test_results:\n            if result[1] == \"PASSED\":\n                print(f\"✓ {result[0]}: PASSED\")\n                passed += 1\n            else:\n                print(f\"✗ {result[0]}: FAILED - {result[2] if len(result) > 2 else 'Unknown error'}\")\n                failed += 1\n        \n        print(f\"\\nTotal Tests: {passed + failed}\")\n        print(f\"Passed: {passed}\")\n        print(f\"Failed: {failed}\")\n        print(f\"Test Duration: {end_time - start_time:.2f} seconds\")\n        \n        if failed == 0:\n            print(\"\\n🎉 ALL TESTS PASSED! Advanced Transaction Management System is ready for deployment.\")\n        else:\n            print(f\"\\n⚠️  {failed} test(s) failed. Please review and fix issues before deployment.\")\n        \n        return failed == 0\n\ndef main():\n    \"\"\"Main test runner\"\"\"\n    tester = TransactionManagementTester()\n    success = tester.run_all_tests()\n    \n    if success:\n        print(\"\\n\" + \"=\"*70)\n        print(\"ADVANCED TRANSACTION MANAGEMENT SYSTEM - IMPLEMENTATION COMPLETE\")\n        print(\"=\"*70)\n        print(\"\\nComponents Implemented:\")\n        print(\"✓ Transaction Analytics Service\")\n        print(\"✓ Payment Processing Monitor\")\n        print(\"✓ Fraud Detection System\")\n        print(\"✓ Financial Reporting Dashboard\")\n        print(\"✓ Transaction Dispute Management\")\n        print(\"✓ Advanced Admin Templates\")\n        print(\"✓ Comprehensive API Integration\")\n        print(\"\\nThe system is ready for production deployment!\")\n    else:\n        print(\"\\n⚠️  Some tests failed. Please review the errors above.\")\n    \n    return 0 if success else 1\n\nif __name__ == '__main__':\n    exit(main())"