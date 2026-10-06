from datetime import datetime
from extensions import db


class Election(db.Model):
    __tablename__ = 'elections'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'),
                                 nullable=False, index=True)
    
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    election_type = db.Column(db.String(50), default='general')
    # general, student_council, board, committee, leadership, class, custom
    
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    
    # Result visibility: 'hidden', 'live', 'after_close'
    result_visibility = db.Column(db.String(20), default='after_close')
    
    # Status: 'draft', 'scheduled', 'active', 'closed', 'announced'
    status = db.Column(db.String(20), default='draft', index=True)
    
    allow_vote_correction = db.Column(db.Boolean, default=False)
    eligible_group = db.Column(db.String(150), default='all')
    
    # Announcement
    announced_at = db.Column(db.DateTime)
    announced_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    is_finalized = db.Column(db.Boolean, default=False)
    
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    positions = db.relationship('Position', backref='election', lazy='dynamic',
                                 cascade='all, delete-orphan',
                                 order_by='Position.order_index')
    votes = db.relationship('Vote', backref='election', lazy='dynamic',
                            cascade='all, delete-orphan')
    
    # --- Status helpers ---
    @property
    def is_open(self):
        if self.status != 'active':
            return False
        now = datetime.utcnow()
        return self.start_date <= now <= self.end_date
    
    @property
    def has_started(self):
        return datetime.utcnow() >= self.start_date
    
    @property
    def has_ended(self):
        return datetime.utcnow() > self.end_date
    
    @property
    def effective_status(self):
        """Compute effective status considering dates."""
        now = datetime.utcnow()
        if self.status == 'announced':
            return 'announced'
        if self.status == 'closed':
            return 'closed'
        if self.status == 'draft':
            return 'draft'
        if now < self.start_date:
            return 'scheduled'
        if now > self.end_date:
            return 'closed'
        return 'active'
    
    def total_voters_who_voted(self):
        from models.vote import Vote
        return db.session.query(Vote.voter_id).filter_by(
            election_id=self.id
        ).distinct().count()
    
    def total_eligible_voters(self):
        from models.user import User
        return User.query.filter_by(
            organization_id=self.organization_id,
            role='voter',
            is_active=True,
            is_approved=True
        ).count()
    
    def to_dict(self, include_positions=False):
        data = {
            'id': self.id,
            'organization_id': self.organization_id,
            'name': self.name,
            'description': self.description,
            'election_type': self.election_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'result_visibility': self.result_visibility,
            'status': self.status,
            'effective_status': self.effective_status,
            'eligible_group': self.eligible_group,
            'is_finalized': self.is_finalized,
            'total_voters_who_voted': self.total_voters_who_voted(),
            'total_eligible_voters': self.total_eligible_voters(),
        }
        if include_positions:
            data['positions'] = [p.to_dict(include_candidates=True)
                                 for p in self.positions]
        return data
    
    def __repr__(self):
        return f'<Election {self.name} ({self.status})>'