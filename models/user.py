from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'),
                                 nullable=False, index=True)
    
    # Role: 'admin' or 'voter'
    role = db.Column(db.String(20), nullable=False, default='voter', index=True)
    
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False, index=True)
    phone = db.Column(db.String(50))
    voter_id = db.Column(db.String(100), index=True)  # membership/student/employee ID
    password_hash = db.Column(db.String(255), nullable=False)
    
    is_active = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=True)
    
    # Security
    last_login = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(50))
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    votes = db.relationship('Vote', backref='voter', lazy='dynamic',
                            foreign_keys='Vote.voter_id')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic',
                                     cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='actor', lazy='dynamic',
                                  foreign_keys='AuditLog.actor_id')
    
    __table_args__ = (
        db.UniqueConstraint('organization_id', 'email', name='uq_org_email'),
        db.UniqueConstraint('organization_id', 'voter_id', name='uq_org_voter_id'),
    )
    
    # --- Password handling ---
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256:600000')
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    # --- Role helpers ---
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_voter(self):
        return self.role == 'voter'
    
    def has_voted_in(self, election_id):
        from models.vote import Vote
        return db.session.query(
            Vote.query.filter_by(voter_id=self.id, election_id=election_id).exists()
        ).scalar()
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'role': self.role,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'voter_id': self.voter_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<User {self.email} ({self.role})>'