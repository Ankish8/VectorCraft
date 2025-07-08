"""
Authentication service layer for VectorCraft
Handles user authentication, session management, and security
"""

import logging
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from database_optimized import db_optimized
from .monitoring import system_logger

logger = logging.getLogger(__name__)


class AuthService:
    """Service layer for authentication operations"""
    
    def __init__(self, db=None):
        self.db = db or db_optimized
        self.logger = logger
        
        # Rate limiting settings
        self.max_login_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
        self.session_timeout = timedelta(hours=1)
    
    def create_user(self, username: str, email: str, password: str) -> Optional[int]:
        """Create a new user account"""
        try:
            # Validate input
            if not self._validate_user_input(username, email, password):
                return None
            
            # Check if user already exists
            if self.get_user_by_username(username):
                self.logger.warning(f"Attempted to create user with existing username: {username}")
                return None
            
            if self.get_user_by_email(email):
                self.logger.warning(f"Attempted to create user with existing email: {email}")
                return None
            
            # Create user
            user_id = self.db.create_user(username, email, password)
            
            if user_id:
                system_logger.info('auth', f'User created successfully: {username}',
                                  user_email=email,
                                  details={'user_id': user_id})
                return user_id
            
        except Exception as e:
            self.logger.error(f"Error creating user: {e}")
            system_logger.error('auth', f'User creation failed: {str(e)}',
                               details={'username': username, 'email': email})
        
        return None
    
    def authenticate_user(self, username: str, password: str, ip_address: str = None) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials"""
        try:
            # Get user
            user = self.get_user_by_username(username)
            if not user:
                self.logger.warning(f"Authentication failed: User not found: {username}")
                return None
            
            # Check if user is locked out
            if self._is_user_locked_out(user):
                self.logger.warning(f"Authentication failed: User locked out: {username}")
                system_logger.warning('auth', f'Login attempt for locked out user: {username}',
                                     details={'ip_address': ip_address})
                return None
            
            # Verify password
            if self.db.verify_password(password, user['password_hash']):
                # Successful authentication
                self._handle_successful_login(user, ip_address)
                
                system_logger.info('auth', f'User authenticated successfully: {username}',
                                  user_email=user['email'],
                                  details={'ip_address': ip_address})
                
                return user
            else:
                # Failed authentication
                self._handle_failed_login(user, ip_address)
                
                system_logger.warning('auth', f'Authentication failed for user: {username}',
                                     details={'ip_address': ip_address})
                
                return None
                
        except Exception as e:
            self.logger.error(f"Error authenticating user: {e}")
            system_logger.error('auth', f'Authentication error: {str(e)}',
                               details={'username': username, 'ip_address': ip_address})
        
        return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        try:
            return self.db.get_user_by_username(username)
        except Exception as e:
            self.logger.error(f"Error getting user by username: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            return self.db.get_user_by_email(email)
        except Exception as e:
            self.logger.error(f"Error getting user by email: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            return self.db.get_user_by_id(user_id)
        except Exception as e:
            self.logger.error(f"Error getting user by ID: {e}")
            return None
    
    def update_user_last_login(self, user_id: int) -> bool:
        """Update user's last login timestamp"""
        try:
            with self.db.pool.get_connection() as conn:
                conn.execute('''
                    UPDATE users 
                    SET last_login = CURRENT_TIMESTAMP, login_attempts = 0
                    WHERE id = ?
                ''', (user_id,))
            
            # Clear cache
            user = self.get_user_by_id(user_id)
            if user:
                self.db._clear_user_cache(user['username'], user['email'])
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating user last login: {e}")
            return False
    
    def generate_secure_password(self, length: int = 12) -> str:
        """Generate a secure random password"""
        characters = string.ascii_letters + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    def generate_username(self, base: str = None) -> str:
        """Generate a unique username"""
        if base:
            # Try to use base name
            if not self.get_user_by_username(base):
                return base
            
            # Try with numbers
            for i in range(1, 1000):
                username = f"{base}{i}"
                if not self.get_user_by_username(username):
                    return username
        
        # Generate random username
        import random
        return f"user_{random.randint(10000, 99999)}"
    
    def is_admin_user(self, user: Dict[str, Any]) -> bool:
        """Check if user has admin privileges"""
        if not user:
            return False
        
        return (user.get('username') == 'admin' or 
                'admin' in user.get('email', '').lower())
    
    def validate_session(self, user_id: int, session_id: str) -> bool:
        """Validate user session"""
        try:
            with self.db.pool.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM user_sessions 
                    WHERE user_id = ? AND session_id = ? AND is_active = 1
                    AND expires_at > CURRENT_TIMESTAMP
                ''', (user_id, session_id))
                
                session = cursor.fetchone()
                return session is not None
                
        except Exception as e:
            self.logger.error(f"Error validating session: {e}")
            return False
    
    def create_session(self, user_id: int, ip_address: str = None, user_agent: str = None) -> Optional[str]:
        """Create a new user session"""
        try:
            session_id = secrets.token_urlsafe(32)
            expires_at = datetime.now() + self.session_timeout
            
            with self.db.pool.get_connection() as conn:
                conn.execute('''
                    INSERT INTO user_sessions 
                    (user_id, session_id, ip_address, user_agent, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, session_id, ip_address, user_agent, expires_at))
            
            return session_id
            
        except Exception as e:
            self.logger.error(f"Error creating session: {e}")
            return None
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a user session"""
        try:
            with self.db.pool.get_connection() as conn:
                conn.execute('''
                    UPDATE user_sessions 
                    SET is_active = 0 
                    WHERE session_id = ?
                ''', (session_id,))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error invalidating session: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        try:
            with self.db.pool.get_connection() as conn:
                cursor = conn.execute('''
                    DELETE FROM user_sessions 
                    WHERE expires_at < CURRENT_TIMESTAMP OR is_active = 0
                ''')
                
                deleted_count = cursor.rowcount
                
                if deleted_count > 0:
                    self.logger.info(f"Cleaned up {deleted_count} expired sessions")
                
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Error cleaning up expired sessions: {e}")
            return 0
    
    def _validate_user_input(self, username: str, email: str, password: str) -> bool:
        """Validate user input"""
        if not username or len(username) < 3 or len(username) > 50:
            return False
        
        if not email or '@' not in email or len(email) > 100:
            return False
        
        if not password or len(password) < 6:
            return False
        
        return True
    
    def _is_user_locked_out(self, user: Dict[str, Any]) -> bool:
        """Check if user is locked out due to too many failed attempts"""
        attempts = user.get('login_attempts', 0)
        if attempts < self.max_login_attempts:
            return False
        
        last_attempt = user.get('last_attempt')
        if not last_attempt:
            return False
        
        try:
            last_attempt_dt = datetime.fromisoformat(last_attempt)
            return datetime.now() - last_attempt_dt < self.lockout_duration
        except:
            return False
    
    def _handle_successful_login(self, user: Dict[str, Any], ip_address: str = None):
        """Handle successful login"""
        try:
            with self.db.pool.get_connection() as conn:
                conn.execute('''
                    UPDATE users 
                    SET last_login = CURRENT_TIMESTAMP, login_attempts = 0
                    WHERE id = ?
                ''', (user['id'],))
            
            # Clear cache
            self.db._clear_user_cache(user['username'], user['email'])
            
        except Exception as e:
            self.logger.error(f"Error handling successful login: {e}")
    
    def _handle_failed_login(self, user: Dict[str, Any], ip_address: str = None):
        """Handle failed login attempt"""
        try:
            with self.db.pool.get_connection() as conn:
                conn.execute('''
                    UPDATE users 
                    SET login_attempts = login_attempts + 1, last_attempt = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (user['id'],))
            
            # Clear cache
            self.db._clear_user_cache(user['username'], user['email'])
            
        except Exception as e:
            self.logger.error(f"Error handling failed login: {e}")


# Global auth service instance
auth_service = AuthService()


if __name__ == '__main__':
    # Test the auth service
    logger.info("Testing VectorCraft Auth Service...")
    
    # Test user creation
    test_user_id = auth_service.create_user('testuser', 'test@example.com', 'testpass123')
    if test_user_id:
        logger.info(f"Test user created with ID: {test_user_id}")
    
    # Test authentication
    user = auth_service.authenticate_user('testuser', 'testpass123', '127.0.0.1')
    if user:
        logger.info(f"User authenticated successfully: {user['username']}")
    
    # Test session management
    session_id = auth_service.create_session(user['id'], '127.0.0.1', 'Test Agent')
    if session_id:
        logger.info(f"Session created: {session_id}")
    
    # Test session validation
    is_valid = auth_service.validate_session(user['id'], session_id)
    logger.info(f"Session validation: {is_valid}")
    
    logger.info("Auth service test completed!")