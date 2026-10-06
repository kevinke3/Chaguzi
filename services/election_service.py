from datetime import datetime
from extensions import db
from models.election import Election
from models.position import Position
from models.candidate import Candidate
from services.audit_service import log_action


def create_election(org_id, admin_id, data):
    """Create a new election."""
    name = (data.get('name') or '').strip()
    if not name:
        return None, 'Election name is required.'
    
    try:
        start = datetime.fromisoformat(data['start_date'])
        end = datetime.fromisoformat(data['end_date'])
    except (KeyError, ValueError):
        return None, 'Valid start and end dates are required.'
    
    if end <= start:
        return None, 'End date must be after start date.'
    
    visibility = data.get('result_visibility', 'after_close')
    if visibility not in ('hidden', 'live', 'after_close'):
        visibility = 'after_close'
    
    election = Election(
        organization_id=org_id,
        name=name,
        description=data.get('description'),
        election_type=data.get('election_type', 'general'),
        start_date=start,
        end_date=end,
        result_visibility=visibility,
        eligible_group=data.get('eligible_group', 'all'),
        status=data.get('status', 'draft'),
        allow_vote_correction=bool(data.get('allow_vote_correction', False)),
        created_by=admin_id,
    )
    db.session.add(election)
    db.session.commit()
    
    log_action(org_id, admin_id, 'election.create',
               'election', election.id, f'Created election "{name}"')
    return election, None


def update_election(election, admin_id, data):
    """Update an election (only safe changes if not finalized)."""
    if election.is_finalized:
        return False, 'This election has been finalized and cannot be modified.'
    
    if 'name' in data and data['name']:
        election.name = data['name'].strip()
    if 'description' in data:
        election.description = data.get('description')
    if 'election_type' in data:
        election.election_type = data['election_type']
    if 'eligible_group' in data:
        election.eligible_group = data['eligible_group']
    if 'result_visibility' in data:
        v = data['result_visibility']
        if v in ('hidden', 'live', 'after_close'):
            election.result_visibility = v
    
    # Date changes only allowed if election hasn't started
    if election.status in ('draft', 'scheduled'):
        try:
            if data.get('start_date'):
                election.start_date = datetime.fromisoformat(data['start_date'])
            if data.get('end_date'):
                election.end_date = datetime.fromisoformat(data['end_date'])
        except ValueError:
            return False, 'Invalid date format.'
    
    if election.end_date <= election.start_date:
        return False, 'End date must be after start date.'
    
    db.session.commit()
    log_action(election.organization_id, admin_id, 'election.update',
               'election', election.id, f'Updated election "{election.name}"')
    return True, 'Election updated.'


def change_election_status(election, admin_id, new_status):
    """Open, close, or finalize an election."""
    valid = {'draft', 'scheduled', 'active', 'closed', 'announced'}
    if new_status not in valid:
        return False, 'Invalid status.'
    
    if election.is_finalized and new_status != 'announced':
        return False, 'Finalized elections cannot change status.'
    
    old = election.status
    election.status = new_status
    
    if new_status == 'announced':
        election.announced_at = datetime.utcnow()
        election.announced_by = admin_id
        election.is_finalized = True
    if new_status == 'closed':
        # Mark finalized when closed? Keep mutable for admin review but block votes
        pass
    
    db.session.commit()
    log_action(election.organization_id, admin_id, f'election.{new_status}',
               'election', election.id, f'Status changed {old} -> {new_status}')
    return True, f'Election {new_status}.'


def add_position(election, admin_id, data):
    if election.is_finalized:
        return None, 'Cannot add positions to a finalized election.'
    title = (data.get('title') or '').strip()
    if not title:
        return None, 'Position title is required.'
    # Determine next order index
    count = election.positions.count()
    pos = Position(
        election_id=election.id,
        title=title,
        description=data.get('description'),
        max_selections=1,
        order_index=count,
    )
    db.session.add(pos)
    db.session.commit()
    log_action(election.organization_id, admin_id, 'position.create',
               'position', pos.id, f'Added position "{title}"')
    return pos, None


def add_candidate(position, org_id, admin_id, data):
    election = position.election
    if election.is_finalized or election.status == 'active':
        return None, 'Cannot add candidates once voting has started.'
    name = (data.get('name') or '').strip()
    if not name:
        return None, 'Candidate name is required.'
    count = position.candidates.count()
    cand = Candidate(
        position_id=position.id,
        organization_id=org_id,
        name=name,
        description=data.get('description'),
        manifesto=data.get('manifesto'),
        identifier=data.get('identifier'),
        extra_info=data.get('extra_info'),
        photo=data.get('photo'),
        order_index=count,
    )
    db.session.add(cand)
    db.session.commit()
    log_action(org_id, admin_id, 'candidate.create',
               'candidate', cand.id, f'Added candidate "{name}"')
    return cand, None