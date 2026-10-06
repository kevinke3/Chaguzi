from datetime import datetime
from extensions import db


class Position(db.Model):
    __tablename__ = 'positions'
    
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'),
                             nullable=False, index=True)
    
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    max_selections = db.Column(db.Integer, default=1)  # Reserved for future; enforced to 1
    order_index = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    candidates = db.relationship('Candidate', backref='position', lazy='dynamic',
                                  cascade='all, delete-orphan',
                                  order_by='Candidate.order_index')
    
    def to_dict(self, include_candidates=False):
        data = {
            'id': self.id,
            'election_id': self.election_id,
            'title': self.title,
            'description': self.description,
            'max_selections': self.max_selections,
            'order_index': self.order_index,
        }
        if include_candidates:
            data['candidates'] = [c.to_dict() for c in self.candidates]
        return data
    
    def __repr__(self):
        return f'<Position {self.title}>'