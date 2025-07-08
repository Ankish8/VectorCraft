"""
Authentication forms for VectorCraft
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError
from database import db


class LoginForm(FlaskForm):
    """User login form"""
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(min=3, max=50)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=6, max=100)
    ])
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    """User registration form (for manual registration)"""
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(min=3, max=50)
    ])
    email = StringField('Email', validators=[
        DataRequired(), 
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=6, max=100)
    ])
    submit = SubmitField('Register')

    def validate_username(self, username):
        """Validate username uniqueness"""
        user = db.get_user_by_username(username.data)
        if user:
            raise ValidationError('Username already exists')

    def validate_email(self, email):
        """Validate email uniqueness"""
        user = db.get_user_by_email(email.data)
        if user:
            raise ValidationError('Email already registered')


class PasswordResetRequestForm(FlaskForm):
    """Password reset request form"""
    email = StringField('Email', validators=[
        DataRequired(), 
        Email()
    ])
    submit = SubmitField('Request Password Reset')


class PasswordResetForm(FlaskForm):
    """Password reset form"""
    password = PasswordField('New Password', validators=[
        DataRequired(), 
        Length(min=6, max=100)
    ])
    password_confirm = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        Length(min=6, max=100)
    ])
    submit = SubmitField('Reset Password')

    def validate_password_confirm(self, password_confirm):
        """Validate password confirmation"""
        if password_confirm.data != self.password.data:
            raise ValidationError('Passwords do not match')