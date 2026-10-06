from datetime import datetime
from extensions import db


class Vote(db.Model):
    __tablename__ = 'votes'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'),
                                 nullable=False, index=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'),
                             nullable=False, index=True)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'),
                             nullable=False, index=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'),
                              nullable=False, index=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                          nullable=False, index=True)
    
    # Vote receipt hash for audit (does not reveal choice)
    receipt_hash = db.Column(db.String(64), index=True)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(300))
    
    cast_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # CRITICAL: Enforce one vote per voter per position per election
    __table_args__ = (
        db.UniqueConstraint('election_id', 'position_id', 'voter_id',
                            name='uq_one_vote_per_position_per_voter'),
    )
    
    candidate = db.relationship('Candidate', backref='votes')
    position = db.relationship('Position', backref='votes')
    
    def __repr__(self):
        return f'<Vote e={self.election_id} p={self.position_id} v={self.voter_id}>'