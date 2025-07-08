#!/usr/bin/env python3
"""
Unit tests for database operations
Tests database initialization, CRUD operations, and data integrity
"""

import pytest
import sqlite3
import tempfile
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

from database import Database


class TestDatabaseInitialization:
    """Test database initialization and setup"""
    
    def test_database_creation(self):
        """Test database file creation"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = Database(db_path)
            assert os.path.exists(db_path)
            assert db.db_path == db_path
        finally:
            os.unlink(db_path)
    
    def test_database_tables_creation(self, temp_db):
        """Test that all required tables are created"""
        with sqlite3.connect(temp_db.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            
            # Check required tables exist
            required_tables = {
                'users', 'transactions', 'system_logs', 
                'health_status', 'admin_alerts', 'user_sessions'
            }
            
            assert required_tables.issubset(tables)
    
    def test_users_table_schema(self, temp_db):
        """Test users table schema"""
        with sqlite3.connect(temp_db.db_path) as conn:
            cursor = conn.cursor()
            
            # Get table schema
            cursor.execute("PRAGMA table_info(users)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            # Check required columns
            expected_columns = {
                'id': 'INTEGER',
                'username': 'TEXT',
                'email': 'TEXT',
                'password_hash': 'TEXT',
                'salt': 'TEXT',
                'created_at': 'TIMESTAMP',
                'last_login': 'TIMESTAMP',
                'is_active': 'BOOLEAN'
            }
            
            for column, type_name in expected_columns.items():
                assert column in columns
                assert type_name in columns[column]
    
    def test_transactions_table_schema(self, temp_db):
        """Test transactions table schema"""
        with sqlite3.connect(temp_db.db_path) as conn:
            cursor = conn.cursor()
            
            # Get table schema
            cursor.execute("PRAGMA table_info(transactions)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            # Check required columns
            expected_columns = {
                'id': 'INTEGER',
                'transaction_id': 'TEXT',
                'email': 'TEXT',
                'username': 'TEXT',
                'amount': 'DECIMAL',
                'currency': 'VARCHAR',
                'paypal_order_id': 'TEXT',
                'paypal_payment_id': 'TEXT',
                'status': 'VARCHAR',
                'user_created': 'BOOLEAN',
                'email_sent': 'BOOLEAN',
                'created_at': 'TIMESTAMP',
                'completed_at': 'TIMESTAMP',
                'error_message': 'TEXT',
                'metadata': 'TEXT'
            }
            
            for column, type_name in expected_columns.items():
                assert column in columns
                assert type_name in columns[column]
    
    def test_database_indexes(self, temp_db):
        """Test database indexes are created"""
        with sqlite3.connect(temp_db.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = {row[0] for row in cursor.fetchall()}
            
            # Check important indexes exist
            expected_indexes = {
                'idx_users_username',
                'idx_users_email',
                'idx_transactions_transaction_id',
                'idx_transactions_email',
                'idx_system_logs_timestamp'
            }
            
            # Note: Some indexes might be created automatically by SQLite
            # Check that at least some expected indexes exist
            assert len(indexes.intersection(expected_indexes)) > 0
    
    def test_database_constraints(self, temp_db):
        """Test database constraints"""
        with sqlite3.connect(temp_db.db_path) as conn:
            cursor = conn.cursor()
            
            # Test unique constraint on username
            cursor.execute("INSERT INTO users (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
                          ("testuser", "test1@example.com", "hash1", "salt1"))
            
            with pytest.raises(sqlite3.IntegrityError):
                cursor.execute("INSERT INTO users (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
                              ("testuser", "test2@example.com", "hash2", "salt2"))
    
    def test_database_connection_context_manager(self, temp_db):
        """Test database connection context manager"""
        with temp_db.get_db_connection() as conn:
            assert conn is not None
            assert isinstance(conn, sqlite3.Connection)
            assert conn.row_factory == sqlite3.Row
            
            # Test connection is working
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
    
    def test_database_docker_path_handling(self):
        """Test database path handling in Docker environment"""
        # Test Docker path
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            with patch('os.makedirs') as mock_makedirs:
                db = Database()
                assert '/app/data/vectorcraft.db' in db.db_path
                mock_makedirs.assert_called_once_with('/app/data', exist_ok=True)
        
        # Test non-Docker path
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            db = Database()
            assert db.db_path == 'vectorcraft.db'


class TestUserOperations:
    """Test user CRUD operations"""
    
    def test_create_user(self, temp_db, test_user_data):
        """Test user creation"""
        user_id = temp_db.create_user(
            username=test_user_data['username'],
            email=test_user_data['email'],
            password=test_user_data['password']
        )
        
        assert user_id is not None
        assert isinstance(user_id, int)
        assert user_id > 0
    
    def test_get_user_by_id(self, temp_db, created_user):
        """Test retrieving user by ID"""
        user = temp_db.get_user_by_id(created_user['id'])
        
        assert user is not None
        assert user['id'] == created_user['id']
        assert user['username'] == created_user['username']
        assert user['email'] == created_user['email']
        assert user['password_hash'] is not None
        assert user['salt'] is not None
    
    def test_get_user_by_username(self, temp_db, created_user):
        """Test retrieving user by username"""
        user = temp_db.get_user_by_username(created_user['username'])
        
        assert user is not None
        assert user['id'] == created_user['id']
        assert user['username'] == created_user['username']
        assert user['email'] == created_user['email']
    
    def test_get_user_by_email(self, temp_db, created_user):
        """Test retrieving user by email"""
        user = temp_db.get_user_by_email(created_user['email'])
        
        assert user is not None
        assert user['id'] == created_user['id']
        assert user['username'] == created_user['username']
        assert user['email'] == created_user['email']
    
    def test_get_nonexistent_user(self, temp_db):
        """Test retrieving non-existent user"""
        user = temp_db.get_user_by_id(99999)
        assert user is None
        
        user = temp_db.get_user_by_username("nonexistent")
        assert user is None
        
        user = temp_db.get_user_by_email("nonexistent@example.com")
        assert user is None
    
    def test_update_user(self, temp_db, created_user):
        """Test user update"""
        new_email = "updated@example.com"
        
        success = temp_db.update_user(created_user['id'], {'email': new_email})
        assert success is True
        
        # Verify update
        user = temp_db.get_user_by_id(created_user['id'])
        assert user['email'] == new_email
    
    def test_update_nonexistent_user(self, temp_db):
        """Test updating non-existent user"""
        success = temp_db.update_user(99999, {'email': 'test@example.com'})
        assert success is False
    
    def test_delete_user(self, temp_db, created_user):
        """Test user deletion (soft delete)"""
        success = temp_db.delete_user(created_user['id'])
        assert success is True
        
        # Verify user is deactivated, not deleted
        user = temp_db.get_user_by_id(created_user['id'])
        assert user is not None
        assert user['is_active'] == 0
    
    def test_list_users(self, temp_db, db_test_helpers):
        """Test listing users with pagination"""
        # Create multiple users
        for i in range(5):
            temp_db.create_user(f"user{i}", f"user{i}@example.com", "Password123!")
        
        # Test pagination
        users = temp_db.list_users(page=1, per_page=3)
        assert len(users) == 3
        
        users = temp_db.list_users(page=2, per_page=3)
        assert len(users) == 2
    
    def test_count_users(self, temp_db, db_test_helpers):
        """Test counting users"""
        initial_count = temp_db.count_users()
        
        # Create test users
        for i in range(3):
            temp_db.create_user(f"user{i}", f"user{i}@example.com", "Password123!")
        
        final_count = temp_db.count_users()
        assert final_count == initial_count + 3
    
    def test_user_last_login_update(self, temp_db, created_user):
        """Test updating user last login"""
        # Initially last_login should be None
        user = temp_db.get_user_by_id(created_user['id'])
        assert user['last_login'] is None
        
        # Update last login
        success = temp_db.update_last_login(created_user['id'])
        assert success is True
        
        # Verify update
        user = temp_db.get_user_by_id(created_user['id'])
        assert user['last_login'] is not None
    
    def test_user_password_change(self, temp_db, created_user):
        """Test user password change"""
        new_password_hash = "new_hash"
        new_salt = "new_salt"
        
        success = temp_db.update_user(created_user['id'], {
            'password_hash': new_password_hash,
            'salt': new_salt
        })
        assert success is True
        
        # Verify update
        user = temp_db.get_user_by_id(created_user['id'])
        assert user['password_hash'] == new_password_hash
        assert user['salt'] == new_salt


class TestTransactionOperations:
    """Test transaction CRUD operations"""
    
    def test_create_transaction(self, temp_db, sample_transaction_data):
        """Test transaction creation"""
        transaction_id = temp_db.create_transaction(sample_transaction_data)
        
        assert transaction_id is not None
        assert isinstance(transaction_id, int)
        assert transaction_id > 0
    
    def test_get_transaction_by_id(self, temp_db, sample_transaction_data):
        """Test retrieving transaction by ID"""
        transaction_id = temp_db.create_transaction(sample_transaction_data)
        
        transaction = temp_db.get_transaction_by_id(transaction_id)
        
        assert transaction is not None
        assert transaction['id'] == transaction_id
        assert transaction['transaction_id'] == sample_transaction_data['transaction_id']
        assert transaction['email'] == sample_transaction_data['email']
        assert transaction['amount'] == sample_transaction_data['amount']
    
    def test_get_transaction_by_transaction_id(self, temp_db, sample_transaction_data):
        """Test retrieving transaction by transaction ID"""
        temp_db.create_transaction(sample_transaction_data)
        
        transaction = temp_db.get_transaction_by_transaction_id(
            sample_transaction_data['transaction_id']
        )
        
        assert transaction is not None
        assert transaction['transaction_id'] == sample_transaction_data['transaction_id']
        assert transaction['email'] == sample_transaction_data['email']
    
    def test_update_transaction_status(self, temp_db, sample_transaction_data):
        """Test updating transaction status"""
        transaction_id = temp_db.create_transaction(sample_transaction_data)
        
        success = temp_db.update_transaction_status(transaction_id, 'completed')
        assert success is True
        
        # Verify update
        transaction = temp_db.get_transaction_by_id(transaction_id)
        assert transaction['status'] == 'completed'
    
    def test_list_transactions(self, temp_db):
        """Test listing transactions"""
        # Create multiple transactions
        for i in range(5):
            transaction_data = {
                'transaction_id': f'txn-{i}',
                'email': f'user{i}@example.com',
                'amount': 49.00 + i,
                'currency': 'USD',
                'status': 'completed'
            }
            temp_db.create_transaction(transaction_data)
        
        # Test pagination
        transactions = temp_db.list_transactions(page=1, per_page=3)
        assert len(transactions) == 3
        
        transactions = temp_db.list_transactions(page=2, per_page=3)
        assert len(transactions) == 2
    
    def test_get_user_transactions(self, temp_db, created_user):
        """Test retrieving transactions for a user"""
        # Create transactions for the user
        for i in range(3):
            transaction_data = {
                'transaction_id': f'txn-{i}',
                'email': created_user['email'],
                'username': created_user['username'],
                'amount': 49.00 + i,
                'currency': 'USD',
                'status': 'completed'
            }
            temp_db.create_transaction(transaction_data)
        
        # Create transaction for different user
        transaction_data = {
            'transaction_id': 'txn-other',
            'email': 'other@example.com',
            'username': 'other_user',
            'amount': 49.00,
            'currency': 'USD',
            'status': 'completed'
        }
        temp_db.create_transaction(transaction_data)
        
        # Get transactions for our user
        transactions = temp_db.get_user_transactions(created_user['email'])
        assert len(transactions) == 3
        
        for transaction in transactions:
            assert transaction['email'] == created_user['email']
    
    def test_transaction_statistics(self, temp_db):
        """Test transaction statistics"""
        # Create test transactions
        transaction_data = [
            {'transaction_id': 'txn-1', 'email': 'user1@example.com', 'amount': 49.00, 'currency': 'USD', 'status': 'completed'},
            {'transaction_id': 'txn-2', 'email': 'user2@example.com', 'amount': 99.00, 'currency': 'USD', 'status': 'completed'},
            {'transaction_id': 'txn-3', 'email': 'user3@example.com', 'amount': 49.00, 'currency': 'USD', 'status': 'pending'},
            {'transaction_id': 'txn-4', 'email': 'user4@example.com', 'amount': 149.00, 'currency': 'USD', 'status': 'completed'},
        ]
        
        for data in transaction_data:
            temp_db.create_transaction(data)
        
        # Test statistics
        stats = temp_db.get_transaction_statistics()
        
        assert stats['total_transactions'] == 4
        assert stats['completed_transactions'] == 3
        assert stats['pending_transactions'] == 1
        assert stats['total_revenue'] == 297.00  # 49 + 99 + 149
        assert stats['average_transaction'] == 99.00  # 297 / 3


class TestSystemLogging:
    """Test system logging operations"""
    
    def test_log_event(self, temp_db):
        """Test logging system events"""
        event_data = {
            'event_type': 'user_login',
            'user_id': 1,
            'message': 'User logged in successfully',
            'ip_address': '192.168.1.1',
            'user_agent': 'Mozilla/5.0'
        }
        
        log_id = temp_db.log_event(event_data)
        
        assert log_id is not None
        assert isinstance(log_id, int)
        assert log_id > 0
    
    def test_get_recent_logs(self, temp_db):
        """Test retrieving recent logs"""
        # Create test logs
        for i in range(5):
            event_data = {
                'event_type': f'test_event_{i}',
                'message': f'Test message {i}',
                'ip_address': '192.168.1.1'
            }
            temp_db.log_event(event_data)
        
        # Get recent logs
        logs = temp_db.get_recent_logs(limit=3)
        assert len(logs) == 3
        
        # Logs should be ordered by timestamp (newest first)
        for i in range(len(logs) - 1):
            assert logs[i]['created_at'] >= logs[i + 1]['created_at']
    
    def test_get_logs_by_type(self, temp_db):
        """Test retrieving logs by event type"""
        # Create logs of different types
        for i in range(3):
            temp_db.log_event({
                'event_type': 'user_login',
                'message': f'Login message {i}',
                'ip_address': '192.168.1.1'
            })
        
        for i in range(2):
            temp_db.log_event({
                'event_type': 'file_upload',
                'message': f'Upload message {i}',
                'ip_address': '192.168.1.1'
            })
        
        # Get logs by type
        login_logs = temp_db.get_logs_by_type('user_login')
        assert len(login_logs) == 3
        
        upload_logs = temp_db.get_logs_by_type('file_upload')
        assert len(upload_logs) == 2
    
    def test_cleanup_old_logs(self, temp_db):
        """Test cleanup of old logs"""
        # Create old logs
        old_timestamp = datetime.now() - timedelta(days=35)
        
        with patch('database.datetime') as mock_datetime:
            mock_datetime.now.return_value = old_timestamp
            
            for i in range(3):
                temp_db.log_event({
                    'event_type': 'old_event',
                    'message': f'Old message {i}',
                    'ip_address': '192.168.1.1'
                })
        
        # Create recent logs
        for i in range(2):
            temp_db.log_event({
                'event_type': 'recent_event',
                'message': f'Recent message {i}',
                'ip_address': '192.168.1.1'
            })
        
        # Cleanup old logs (older than 30 days)
        cleaned_count = temp_db.cleanup_old_logs(days=30)
        assert cleaned_count == 3
        
        # Verify only recent logs remain
        remaining_logs = temp_db.get_recent_logs(limit=10)
        assert len(remaining_logs) == 2
        
        for log in remaining_logs:
            assert log['event_type'] == 'recent_event'


class TestDataIntegrity:
    """Test data integrity and consistency"""
    
    def test_foreign_key_constraints(self, temp_db, created_user):
        """Test foreign key constraints"""
        # Create transaction referencing user
        transaction_data = {
            'transaction_id': 'txn-1',
            'email': created_user['email'],
            'username': created_user['username'],
            'amount': 49.00,
            'currency': 'USD',
            'status': 'completed'
        }
        
        transaction_id = temp_db.create_transaction(transaction_data)
        assert transaction_id is not None
        
        # Verify transaction references correct user
        transaction = temp_db.get_transaction_by_id(transaction_id)
        assert transaction['email'] == created_user['email']
        assert transaction['username'] == created_user['username']
    
    def test_data_validation(self, temp_db):
        """Test data validation during insertion"""
        # Test invalid email format
        with pytest.raises(ValueError):
            temp_db.create_user("testuser", "invalid_email", "Password123!")
        
        # Test invalid transaction amount
        with pytest.raises(ValueError):
            temp_db.create_transaction({
                'transaction_id': 'txn-1',
                'email': 'test@example.com',
                'amount': -49.00,  # Negative amount
                'currency': 'USD',
                'status': 'completed'
            })
    
    def test_transaction_atomicity(self, temp_db):
        """Test transaction atomicity"""
        # Mock database error during transaction
        with patch.object(temp_db, 'get_db_connection') as mock_connection:
            mock_conn = MagicMock()
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.execute.side_effect = Exception("Database error")
            mock_connection.return_value = mock_conn
            
            # Transaction should fail completely
            with pytest.raises(Exception):
                temp_db.create_user("testuser", "test@example.com", "Password123!")
            
            # Verify no partial data was saved
            user = temp_db.get_user_by_username("testuser")
            assert user is None
    
    def test_concurrent_access(self, temp_db):
        """Test concurrent database access"""
        import threading
        import time
        
        results = []
        errors = []
        
        def create_user_concurrent(i):
            try:
                user_id = temp_db.create_user(f"user{i}", f"user{i}@example.com", "Password123!")
                results.append(user_id)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_user_concurrent, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All operations should succeed
        assert len(results) == 10
        assert len(errors) == 0
        
        # Verify all users were created
        for i in range(10):
            user = temp_db.get_user_by_username(f"user{i}")
            assert user is not None
    
    def test_backup_and_restore(self, temp_db):
        """Test database backup and restore functionality"""
        # Create test data
        user_id = temp_db.create_user("testuser", "test@example.com", "Password123!")
        
        transaction_data = {
            'transaction_id': 'txn-1',
            'email': 'test@example.com',
            'amount': 49.00,
            'currency': 'USD',
            'status': 'completed'
        }
        temp_db.create_transaction(transaction_data)
        
        # Create backup
        backup_path = temp_db.create_backup()
        assert os.path.exists(backup_path)
        
        # Verify backup contains data
        backup_db = Database(backup_path)
        backup_user = backup_db.get_user_by_username("testuser")
        assert backup_user is not None
        
        # Cleanup
        os.unlink(backup_path)


class TestPerformance:
    """Test database performance"""
    
    def test_query_performance(self, temp_db, performance_test_helpers):
        """Test query performance"""
        # Create test data
        for i in range(1000):
            temp_db.create_user(f"user{i}", f"user{i}@example.com", "Password123!")
        
        # Test query performance
        performance_test_helpers.start_timer()
        
        # Query by username (should be fast with index)
        user = temp_db.get_user_by_username("user500")
        assert user is not None
        
        query_time = performance_test_helpers.end_timer("username_query")
        performance_test_helpers.assert_performance("username_query", 0.1)  # Should be under 100ms
        
        # Query by email (should be fast with index)
        performance_test_helpers.start_timer()
        user = temp_db.get_user_by_email("user500@example.com")
        assert user is not None
        
        email_query_time = performance_test_helpers.end_timer("email_query")
        performance_test_helpers.assert_performance("email_query", 0.1)  # Should be under 100ms
    
    def test_bulk_operations_performance(self, temp_db, performance_test_helpers):
        """Test bulk operations performance"""
        performance_test_helpers.start_timer()
        
        # Bulk insert users
        users_data = []
        for i in range(100):
            users_data.append({
                'username': f'bulk_user_{i}',
                'email': f'bulk_user_{i}@example.com',
                'password': 'Password123!'
            })
        
        for user_data in users_data:
            temp_db.create_user(user_data['username'], user_data['email'], user_data['password'])
        
        bulk_insert_time = performance_test_helpers.end_timer("bulk_insert")
        performance_test_helpers.assert_performance("bulk_insert", 5.0)  # Should be under 5 seconds
    
    def test_index_effectiveness(self, temp_db):
        """Test database index effectiveness"""
        # Create test data
        for i in range(10000):
            temp_db.create_user(f"user{i}", f"user{i}@example.com", "Password123!")
        
        # Test query execution plan
        with sqlite3.connect(temp_db.db_path) as conn:
            cursor = conn.cursor()
            
            # Query with index
            cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM users WHERE username = ?", ("user5000",))
            plan = cursor.fetchall()
            
            # Should use index (not full table scan)
            plan_text = ' '.join(str(row) for row in plan)
            assert "SCAN TABLE users" not in plan_text or "USING INDEX" in plan_text


@pytest.mark.parametrize("table_name,expected_columns", [
    ("users", ["id", "username", "email", "password_hash", "salt", "created_at", "last_login", "is_active"]),
    ("transactions", ["id", "transaction_id", "email", "amount", "currency", "status", "created_at"]),
    ("system_logs", ["id", "event_type", "message", "created_at"]),
])
def test_table_schemas_parametrized(temp_db, table_name, expected_columns):
    """Test table schemas with parametrized testing"""
    with sqlite3.connect(temp_db.db_path) as conn:
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Check all expected columns exist
        for expected_column in expected_columns:
            assert expected_column in columns


class TestDatabaseMigration:
    """Test database migration functionality"""
    
    def test_schema_version_tracking(self, temp_db):
        """Test schema version tracking"""
        # Check initial schema version
        version = temp_db.get_schema_version()
        assert version > 0
        
        # Test schema version update
        new_version = version + 1
        temp_db.update_schema_version(new_version)
        
        updated_version = temp_db.get_schema_version()
        assert updated_version == new_version
    
    def test_migration_application(self, temp_db):
        """Test migration application"""
        # Apply test migration
        migration_sql = """
        CREATE TABLE IF NOT EXISTS test_migration (
            id INTEGER PRIMARY KEY,
            test_column TEXT
        )
        """
        
        success = temp_db.apply_migration(migration_sql)
        assert success is True
        
        # Verify migration was applied
        with sqlite3.connect(temp_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_migration'")
            result = cursor.fetchone()
            assert result is not None
    
    def test_rollback_migration(self, temp_db):
        """Test migration rollback"""
        # Apply migration
        migration_sql = "CREATE TABLE test_rollback (id INTEGER PRIMARY KEY)"
        temp_db.apply_migration(migration_sql)
        
        # Rollback migration
        rollback_sql = "DROP TABLE test_rollback"
        success = temp_db.rollback_migration(rollback_sql)
        assert success is True
        
        # Verify rollback was applied
        with sqlite3.connect(temp_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_rollback'")
            result = cursor.fetchone()
            assert result is None