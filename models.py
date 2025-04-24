from app import db
from datetime import datetime

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Admin {self.username}>'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fb_id = db.Column(db.String(100), unique=True, nullable=False)
    fb_email = db.Column(db.String(120), nullable=False)
    fb_password = db.Column(db.String(100), nullable=False)
    fb_token = db.Column(db.Text, nullable=False)
    guard_status = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Auto post fields
    auto_post_enabled = db.Column(db.Boolean, default=False)
    post_id = db.Column(db.String(100), nullable=True)
    last_update = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<User {self.fb_id}>'
