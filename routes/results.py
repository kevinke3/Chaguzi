from flask import Blueprint, jsonify
from flask_login import current_user, login_required
from sqlalchemy import func
from extensions import db
from models.election import Election
from models.position import Position
from models.candidate import Candidate
from models.vote import Vote
from models.user import User

results_bp = Blueprint('results', __name__)


def _compute_results(election, include_turnout=True):
    """Compute results for an election. Returns dict."""
    data = {
        'election': {
            'id': election.id,
            'name': election.name,
            'status': election.status,
            'effective_status': election.effective_status,
            'start_date': election.start_date.isoformat(),
            'end_date': election.end_date.isoformat(),
            'result_visibility': election.result_visibility,
            'is_finalized': election.is_finalized,
        },
        'positions': [],
    }
    
    total_eligible = election.total_eligible_voters()
    total_voted = election.total_voters_who_voted()
    
    for pos in election.positions.order_by(Position.order_index).all():
        # Total votes cast for this position
        total_pos_votes = db.session.query(func.count(Vote.id)).filter_by(
            position_id=pos.id, election_id=election.id).scalar() or 0
        
        candidates = []
        for cand in pos.candidates.order_by(Candidate.order_index).all():
            votes = db.session.query(func.count(Vote.id)).filter_by(
                candidate_id=cand.id, election_id=election.id,
                position_id=pos.id).scalar() or 0
            pct = round((votes / total_pos_votes) * 100, 2) if total_pos_votes else 0
            candidates.append({
                'id': cand.id,
                'name': cand.name,
                'photo': cand.photo,
                'description': cand.description,
                'manifesto': cand.manifesto,
                'votes': votes,
                'percentage': pct,
            })
        
        # Sort candidates by votes desc
        candidates.sort(key=lambda c: c['votes'], reverse=True)
        
        winner = candidates[0] if candidates and total_pos_votes > 0 else None
        
        data['positions'].append({
            'id': pos.id,
            'title': pos.title,
            'description': pos.description,
            'total_votes': total_pos_votes,
            'candidates': candidates,
            'winner': winner['name'] if winner and winner['votes'] > 0 else None,
            'is_tie': (len(candidates) > 1 and
                       candidates[0]['votes'] == candidates[1]['votes'] and
                       candidates[0]['votes'] > 0),
        })
    
    if include_turnout:
        data['stats'] = {
            'total_eligible': total_eligible,
            'total_voted': total_voted,
            'total_not_voted': max(0, total_eligible - total_voted),
            'turnout_percentage': round((total_voted / total_eligible) * 100, 2) if total_eligible else 0,
        }
    
    return data


@results_bp.route('/api/election/<int:election_id>')
def api_election_results(election_id):
    """Live results endpoint. Access rules: admin of org, or voter in org when visible."""
    election = db.session.get(Election, election_id)
    if not election:
        return jsonify({'error': 'Not found'}), 404
    
    # Visibility check
    visible = False
    if current_user.is_authenticated:
        if current_user.organization_id != election.organization_id and not current_user.is_admin:
            return jsonify({'error': 'Access denied'}), 403
        if current_user.is_admin:
            visible = True
    
    if not visible:
        if election.status == 'announced':
            visible = True
        elif election.result_visibility == 'live' and election.status == 'active':
            visible = True
        elif election.result_visibility == 'after_close' and election.status in ('closed', 'announced'):
            visible = True
        # Public orgs
        if not visible and election.organization.allow_public_results and election.status in ('closed', 'announced'):
            visible = True
    
    if not visible:
        return jsonify({'error': 'Results are not currently visible.'}), 403
    
    data = _compute_results(election)
    return jsonify(data)


@results_bp.route('/api/election/<int:election_id>/turnout')
def api_turnout(election_id):
    election = db.session.get(Election, election_id)
    if not election:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'total_eligible': election.total_eligible_voters(),
        'total_voted': election.total_voters_who_voted(),
        'turnout_percentage': round(
            (election.total_voters_who_voted() / election.total_eligible_voters()) * 100, 2
        ) if election.total_eligible_voters() else 0,
    })


@results_bp.route('/api/election/<int:election_id>/history')
@login_required
def api_history(election_id):
    """Historical results for announced elections in the same org."""
    election = db.session.get(Election, election_id)
    if not election or election.organization_id != current_user.organization_id:
        return jsonify({'error': 'Access denied'}), 403
    history = Election.query.filter_by(
        organization_id=current_user.organization_id, status='announced'
    ).order_by(Election.end_date.desc()).limit(10).all()
    return jsonify([e.to_dict() for e in history])