from datetime import datetime
from extensions import db


class Candidate(db.Model):
    __tablename__ = 'candidates'
    
    id = db.Column(db.Integer, primary_key=True)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'),
                             nullable=False, index=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'),
                                 nullable=False, index=True)
    
    name = db.Column(db.String(150), nullable=False)
    photo = db.Column(db.String(300))
    description = db.Column(db.Text)
    manifesto = db.Column(db.Text)
    identifier = db.Column(db.String(100))
    extra_info = db.Column(db.Text)
    
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def vote_count(self):
        from models.vote import Vote
        return Vote.query.filter_by(candidate_id=self.id).count()
    
    def to_dict(self):
        return {
            'id': self.id,
            'position_id': self.position_id,
            'name': self.name,
            'photo': self.photo,
            'description': self.description,
            'manifesto': self.manifesto,
            'identifier': self.identifier,
            'extra_info': self.extra_info,
            'order_index': self.order_index,
            'is_active': self.is_active,
        }
    
    def __repr__(self):
        return f'<Candidate {self.name}>'