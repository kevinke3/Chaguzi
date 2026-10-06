from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user, login_required
from sqlalchemy import desc

from extensions import db
from models.election import Election
from models.vote import Vote
from models.notification import Notification
from services.vote_service import (
    cast_votes, VoteError, has_voted_in_election, get_voter_positions_status
)
from utils.decorators import voter_required

voter_bp = Blueprint('voter', __name__)


@voter_bp.before_request
@login_required
@voter_required
def before_voter():
    pass


# ---------------------------------------------------------------------------
# Dashboard — overview only
# ---------------------------------------------------------------------------
@voter_bp.route('/dashboard')
def dashboard():
    org = current_user.organization
    now = datetime.utcnow()

    # Counters for stat cards
    active_count = Election.query.filter(
        Election.organization_id == org.id,
        Election.status.notin_(['draft', 'closed', 'announced']),
        Election.start_date <= now,
        Election.end_date >= now,
    ).count()

    completed_count = Election.query.filter(
        Election.organization_id == org.id,
        Election.status.in_(['closed', 'announced']),
    ).count()

    # Upcoming list (small preview)
    upcoming = Election.query.filter(
        Election.organization_id == org.id,
        Election.status.notin_(['closed', 'announced']),
        Election.start_date > now,
    ).order_by(Election.start_date).limit(5).all()

    # Short preview of currently-open elections on the dashboard
    active_preview = Election.query.filter(
        Election.organization_id == org.id,
        Election.status.notin_(['draft', 'closed', 'announced']),
        Election.start_date <= now,
        Election.end_date >= now,
    ).order_by(desc(Election.start_date)).limit(3).all()

    voted_map = {e.id: has_voted_in_election(current_user.id, e.id) for e in active_preview}

    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(desc(Notification.created_at)).limit(5).all()

    return render_template('voter/dashboard.html',
                           org=org,
                           active_count=active_count,
                           completed_count=completed_count,
                           upcoming=upcoming,
                           active_preview=active_preview,
                           voted_map=voted_map,
                           notifications=notifications)


# ---------------------------------------------------------------------------
# Active & Completed list pages
# ---------------------------------------------------------------------------
@voter_bp.route('/elections/active')
def active_elections():
    org = current_user.organization
    now = datetime.utcnow()

    elections = Election.query.filter(
        Election.organization_id == org.id,
        Election.status.notin_(['draft', 'closed', 'announced']),
        Election.start_date <= now,
        Election.end_date >= now,
    ).order_by(desc(Election.start_date)).all()

    voted_map = {e.id: has_voted_in_election(current_user.id, e.id) for e in elections}

    return render_template('voter/elections_list.html',
                           title='Active Elections',
                           subtitle='Elections currently open for voting.',
                           elections=elections,
                           voted_map=voted_map,
                           section='active')


@voter_bp.route('/elections/completed')
def completed_elections():
    org = current_user.organization

    elections = Election.query.filter(
        Election.organization_id == org.id,
        Election.status.in_(['closed', 'announced']),
    ).order_by(desc(Election.end_date)).all()

    return render_template('voter/elections_list.html',
                           title='Completed Elections',
                           subtitle='Elections that have closed. Results may be available.',
                           elections=elections,
                           voted_map={},
                           section='completed')


# ---------------------------------------------------------------------------
# Single election detail
# ---------------------------------------------------------------------------
@voter_bp.route('/elections/<int:election_id>')
def election_view(election_id):
    election = Election.query.filter_by(
        id=election_id, organization_id=current_user.organization_id).first_or_404()

    voted_positions = get_voter_positions_status(current_user.id, election.id)
    has_any_vote = any(voted_positions.values())

    return render_template('voter/election.html',
                           election=election,
                           voted_positions=voted_positions,
                           has_any_vote=has_any_vote)


# ---------------------------------------------------------------------------
# Ballot page
# ---------------------------------------------------------------------------
@voter_bp.route('/elections/<int:election_id>/vote')
def vote_page(election_id):
    election = Election.query.filter_by(
        id=election_id, organization_id=current_user.organization_id).first_or_404()

    now = datetime.utcnow()
    if election.status != 'active' or not (election.start_date <= now <= election.end_date):
        flash('This election is not currently open for voting.', 'warning')
        return redirect(url_for('voter.election_view', election_id=election.id))

    voted_positions = get_voter_positions_status(current_user.id, election.id)

    positions = []
    for pos in election.positions.all():
        if voted_positions.get(pos.id):
            continue
        positions.append({
            'id': pos.id,
            'title': pos.title,
            'description': pos.description,
            'candidates': [c.to_dict() for c in pos.candidates.filter_by(is_active=True).all()]
        })

    if not positions:
        flash('You have already voted for all positions in this election.', 'info')
        return redirect(url_for('voter.election_view', election_id=election.id))

    return render_template('voter/vote.html',
                           election=election,
                           positions=positions,
                           voted_positions=voted_positions)


# ---------------------------------------------------------------------------
# API — positions for the voting app
# ---------------------------------------------------------------------------
@voter_bp.route('/elections/<int:election_id>/api/positions')
def api_positions(election_id):
    election = Election.query.filter_by(
        id=election_id, organization_id=current_user.organization_id).first_or_404()
    voted = get_voter_positions_status(current_user.id, election.id)
    result = []
    for pos in election.positions.all():
        if voted.get(pos.id):
            continue
        result.append({
            'id': pos.id,
            'title': pos.title,
            'description': pos.description,
            'voted': False,
            'candidates': [c.to_dict() for c in pos.candidates.filter_by(is_active=True).all()]
        })
    return jsonify(result)


# ---------------------------------------------------------------------------
# Vote submission
# ---------------------------------------------------------------------------
@voter_bp.route('/elections/<int:election_id>/submit', methods=['POST'])
def submit_vote(election_id):
    data = request.get_json(silent=True) or request.form.to_dict()
    selections = data.get('selections') or {}

    if not isinstance(selections, dict):
        return jsonify({'error': 'Invalid submission.'}), 400

    try:
        count = cast_votes(
            election_id,
            current_user,
            selections,
            ip=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
        )
    except VoteError as e:
        return jsonify({'error': str(e)}), 400
    except Exception:
        return jsonify({'error': 'An unexpected error occurred. Your vote was not recorded.'}), 500

    election = db.session.get(Election, election_id)
    db.session.add(Notification(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        title='Vote Recorded',
        message=f'Your vote in "{election.name}" was successfully recorded.',
        category='success',
        link=url_for('voter.election_view', election_id=election.id),
    ))
    db.session.commit()

    return jsonify({
        'ok': True,
        'message': 'Your vote has been recorded successfully.',
        'count': count,
    })


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
@voter_bp.route('/elections/<int:election_id>/results')
def election_results(election_id):
    election = Election.query.filter_by(
        id=election_id, organization_id=current_user.organization_id).first_or_404()

    visible = False
    if election.status == 'announced':
        visible = True
    elif election.result_visibility == 'live' and election.status == 'active':
        visible = True
    elif election.result_visibility == 'after_close' and election.status in ('closed', 'announced'):
        visible = True

    return render_template('voter/results.html',
                           election=election,
                           visible=visible)


# ---------------------------------------------------------------------------
# Notifications API
# ---------------------------------------------------------------------------
@voter_bp.route('/api/notifications')
def notifications():
    items = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(desc(Notification.created_at)).limit(20).all()
    return jsonify([n.to_dict() for n in items])


@voter_bp.route('/api/notifications/mark-read', methods=['POST'])
def mark_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    return jsonify({'ok': True})