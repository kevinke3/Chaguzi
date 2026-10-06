from datetime import datetime
from sqlalchemy.exc import IntegrityError
from extensions import db
from models.election import Election
from models.position import Position
from models.candidate import Candidate
from models.vote import Vote
from models.user import User
from services.audit_service import log_action
from utils.helpers import generate_vote_receipt, get_client_ip


class VoteError(Exception):
    pass


def cast_votes(election_id, voter, selections, ip=None, user_agent=None):
    """
    Cast votes for a voter.
    selections: dict {position_id: candidate_id}
    
    Enforces:
      - election belongs to voter's organization
      - election is open
      - one vote per position (DB unique constraint + explicit check)
      - candidate belongs to position & org
    """
    election = db.session.get(Election, election_id)
    if not election:
        raise VoteError('Election not found.')
    
    # Cross-organization isolation
    if election.organization_id != voter.organization_id:
        raise VoteError('You cannot vote in this election.')
    
    if voter.role != 'voter':
        raise VoteError('Only voters can cast votes.')
    
    # Election state
    if election.is_finalized or election.status in ('closed', 'announced'):
        raise VoteError('This election is closed.')
    
    now = datetime.utcnow()
    if election.status != 'active':
        raise VoteError('This election is not currently open.')
    if now < election.start_date:
        raise VoteError('Voting has not started yet.')
    if now > election.end_date:
        raise VoteError('Voting period has ended.')
    
    # Check for existing votes
    existing = {v.position_id for v in Vote.query.filter_by(
        election_id=election.id, voter_id=voter.id).all()}
    
    if existing and not election.allow_vote_correction:
        raise VoteError('You have already submitted your vote for this election.')
    
    # Validate selections
    positions = election.positions.all()
    position_map = {p.id: p for p in positions}
    
    if not selections:
        raise VoteError('No selections provided.')
    
    # Ensure every selected position is valid
    for pid_str, cid_str in selections.items():
        try:
            pid = int(pid_str)
            cid = int(cid_str)
        except (TypeError, ValueError):
            raise VoteError('Invalid selection format.')
        
        if pid not in position_map:
            raise VoteError('Invalid position selection.')
        
        if pid in existing:
            continue  # already voted for this position
        
        candidate = db.session.get(Candidate, cid)
        if not candidate or candidate.position_id != pid:
            raise VoteError('Invalid candidate selection.')
        if candidate.organization_id != voter.organization_id:
            raise VoteError('Candidate does not belong to your organization.')
        if not candidate.is_active:
            raise VoteError('This candidate is no longer available.')
    
    # Insert votes
    created = 0
    try:
        for pid_str, cid_str in selections.items():
            pid = int(pid_str)
            cid = int(cid_str)
            if pid in existing:
                continue  # skip already-voted positions
            # Double-check no race (DB unique constraint will also catch)
            dup = Vote.query.filter_by(
                election_id=election.id,
                position_id=pid,
                voter_id=voter.id,
            ).first()
            if dup:
                continue
            
            receipt = generate_vote_receipt(voter.id, election.id, pid)
            vote = Vote(
                organization_id=voter.organization_id,
                election_id=election.id,
                position_id=pid,
                candidate_id=cid,
                voter_id=voter.id,
                receipt_hash=receipt,
                ip_address=ip or get_client_ip(),
                user_agent=(user_agent or '')[:300],
            )
            db.session.add(vote)
            db.session.flush()
            created += 1
        
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        raise VoteError('Duplicate vote detected. Your vote was not recorded.')
    
    if created == 0:
        raise VoteError('No new votes were recorded.')
    
    log_action(voter.organization_id, voter.id, 'vote.cast',
               'election', election.id,
               f'Voter cast {created} vote(s) in election #{election.id}')
    
    return created


def has_voted_in_election(voter_id, election_id):
    return db.session.query(
        Vote.query.filter_by(voter_id=voter_id, election_id=election_id).exists()
    ).scalar()


def get_voter_positions_status(voter_id, election_id):
    """Return dict {position_id: bool voted}."""
    votes = Vote.query.filter_by(voter_id=voter_id, election_id=election_id).all()
    voted_positions = {v.position_id for v in votes}
    election = db.session.get(Election, election_id)
    if not election:
        return {}
    return {p.id: (p.id in voted_positions) for p in election.positions}