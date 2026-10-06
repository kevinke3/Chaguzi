from datetime import datetime
from extensions import db


class Organization(db.Model):
    __tablename__ = 'organizations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True, index=True)
    slug = db.Column(db.String(220), nullable=False, unique=True, index=True)
    org_type = db.Column(db.String(50), nullable=False, default='school')
    # school, university, college, company, church, sacco, association, institution, other
    logo = db.Column(db.String(300))
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50))
    location = db.Column(db.String(200))
    registration_number = db.Column(db.String(100))
    description = db.Column(db.Text)
    
    # Settings
    voter_id_required = db.Column(db.Boolean, default=True)
    voter_id_label = db.Column(db.String(50), default='Membership ID')
    allow_public_results = db.Column(db.Boolean, default=False)
    default_result_visibility = db.Column(db.String(20), default='after_close')
    # 'hidden', 'live', 'after_close'
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='organization', lazy='dynamic',
                            cascade='all, delete-orphan')
    elections = db.relationship('Election', backref='organization', lazy='dynamic',
                                cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'org_type': self.org_type,
            'logo': self.logo,
            'email': self.email,
            'phone': self.phone,
            'location': self.location,
            'description': self.description,
            'voter_id_required': self.voter_id_required,
            'voter_id_label': self.voter_id_label,
        }
    
    def __repr__(self):
        return f'<Organization {self.name}>'