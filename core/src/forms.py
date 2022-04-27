"""
This package provides the login, signup, and preference forms for the website
"""
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, PasswordField, SubmitField
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length
)


class SignupForm(FlaskForm):
    """User Sign-up Form."""
    name = StringField(
        'Name',
        validators=[DataRequired()]
    )
    email = StringField(
        'Email',
        validators=[
            Length(min=6),
            Email(message='Enter a valid email.'),
            DataRequired()
        ]
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(),
            Length(min=6, message='Select a stronger password.')
        ]
    )
    confirm = PasswordField(
        'Confirm Your Password',
        validators=[
            DataRequired(),
            EqualTo('password', message='Passwords must match.')
        ]
    )
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    """User Log-in Form."""
    email = StringField(
        'Email',
        validators=[
            DataRequired(),
            Email(message='Enter a valid email.')
        ]
    )
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')

class PreferencesForm(FlaskForm):
    """User Preferences Form."""
    app1 = SelectField(
        'Application 1',
        choices=[('Yes', 'Yes'), ('No', 'No')],
        validators=[
            DataRequired()
        ]
    )
    app2 = SelectField(
        'Application 2',
        choices=[('Yes', 'Yes'), ('No', 'No')],
        validators=[
            DataRequired()
        ]
    )
    app3 = SelectField(
        'Application 3',
        choices=[('Yes', 'Yes'), ('No', 'No')],
        validators=[
            DataRequired()
        ]
    )
    app4 = SelectField(
        'Application 4',
        choices=[('Yes', 'Yes'), ('No', 'No')],
        validators=[
            DataRequired()
        ]
    )
    submit = SubmitField('Save')