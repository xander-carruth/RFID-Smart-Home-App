from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import relationship

class User(db.Model, UserMixin):
    """
    User class is a model for a user in the database
    """
    __tablename__ = 'user'

    id = db.Column(
        db.Integer,
        primary_key=True
    )
    name = db.Column(
        db.String(100),
        nullable=False,
        unique=False
    )

    nfc_id = db.Column(
        db.String(100),
        nullable=True,
        unique=True
    )
    email = db.Column(
        db.String(40),
        unique=True,
        nullable=False
    )
    password = db.Column(
        db.String(200),
        primary_key=False,
        unique=False,
        nullable=False
    )

    preferences = relationship("Preferences", backref="user", uselist=False)

    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(
            password,
            method='sha256'
        )

    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password, password)

    def __repr__(self):
        return '<User {}>'.format(self.username)

class Preferences(db.Model):
    __tablename__ = 'preferences'
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    app1 = db.Column(
        db.String(6),
        nullable=True,
        unique=False
    )
    app2 = db.Column(
        db.String(6),
        nullable=True,
        unique=False
    )
    app3 = db.Column(
        db.String(6),
        nullable=True,
        unique=False
    )
    app4 = db.Column(
        db.String(6),
        nullable=True,
        unique=False
    )
    user_id = db.Column(
        Integer,
        ForeignKey('user.id')
    )
    _user = relationship("User", uselist=False, overlaps="preferences,user")
    def __repr__(self):
        # return '\{app1:"{}",app2:"{}",app3:"{}",app4:"{}"\}'.format(self.app1, self.app2, self.app3, self.app4)
        return '{{{{app1:\"{}\"}}, {{app2:\"{}\"}}, {{app3:\"{}\"}}, {{app4:\"{}\"}}}}'.format(self.app1, self.app2, self.app3, self.app4)