from datetime import datetime
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, jsonify, current_app)
from flask_login import current_user, login_required
from sqlalchemy import func, desc, or_

from extensions import db
from models.organization import Organization
from models.user import User
from models.election import Election
from models.position import Position
from models.candidate import Candidate
from models.vote import Vote
from models.notification import Notification
from models.audit_log import AuditLog
from services.election_service import (
    create_election, update_election, change_election_status,
    add_position, add_candidate
)
from services.audit_service import log_action
from utils.decorators import admin_required
from utils.helpers import save_upload
from utils.validators import validate_email

admin_bp = Blueprint('admin', __name__)


@admin_bp.before_request
@login_required
@admin_required
def before_admin():
    pass


# ---------------- Dashboard ----------------
@admin_bp.route('/dashboard')
def dashboard():
    org = current_user.organization
    org_id = org.id
    
    total_voters = User.query.filter_by(
        organization_id=org_id, role='voter', is_active=True).count()
    total_candidates = Candidate.query.filter_by(organization_id=org_id).count()
    
    active_elections = Election.query.filter_by(
        organization_id=org_id, status='active').order_by(desc(Election.start_date)).all()
    upcoming = Election.query.filter_by(
        organization_id=org_id, status='scheduled').order_by(Election.start_date).limit(5).all()
    completed = Election.query.filter_by(
        organization_id=org_id).filter(
        Election.status.in_(['closed', 'announced'])
    ).order_by(desc(Election.end_date)).limit(5).all()
    
    # Turnout for active elections
    turnout = 0
    if active_elections:
        e = active_elections[0]
        voted = db.session.query(Vote.voter_id).filter_by(election_id=e.id).distinct().count()
        turnout = round((voted / total_voters) * 100, 1) if total_voters else 0
    
    # Recent activity
    recent = AuditLog.query.filter_by(organization_id=org_id)\
        .order_by(desc(AuditLog.created_at)).limit(10).all()
    
    # Chart data: elections over time (last 6)
    elections_all = Election.query.filter_by(organization_id=org_id)\
        .order_by(desc(Election.created_at)).limit(6).all()
    chart_labels = [e.name[:15] for e in reversed(elections_all)]
    chart_votes = [e.total_voters_who_voted() for e in reversed(elections_all)]
    chart_eligible = [e.total_eligible_voters() for e in reversed(elections_all)]
    
    return render_template('admin/dashboard.html',
                           org=org,
                           total_voters=total_voters,
                           total_candidates=total_candidates,
                           active_elections=active_elections,
                           upcoming=upcoming,
                           completed=completed,
                           turnout=turnout,
                           recent=recent,
                           chart_labels=chart_labels,
                           chart_votes=chart_votes,
                           chart_eligible=chart_eligible)


# ---------------- Elections ----------------
@admin_bp.route('/elections')
def elections():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    q = request.args.get('q', '').strip()
    
    query = Election.query.filter_by(organization_id=current_user.organization_id)
    if status:
        query = query.filter_by(status=status)
    if q:
        query = query.filter(Election.name.ilike(f'%{q}%'))
    query = query.order_by(desc(Election.created_at))
    
    pagination = query.paginate(page=page,
                                per_page=current_app.config['ELECTIONS_PER_PAGE'],
                                error_out=False)
    return render_template('admin/elections.html',
                           elections=pagination.items,
                           pagination=pagination,
                           status=status, q=q)


@admin_bp.route('/elections/new', methods=['GET', 'POST'])
def election_new():
    if request.method == 'POST':
        data = {
            'name': request.form.get('name', '').strip(),
            'description': request.form.get('description', '').strip(),
            'election_type': request.form.get('election_type', 'general'),
            'start_date': request.form.get('start_date'),
            'end_date': request.form.get('end_date'),
            'result_visibility': request.form.get('result_visibility', 'after_close'),
            'eligible_group': request.form.get('eligible_group', 'all'),
            'status': request.form.get('status', 'draft'),
            'allow_vote_correction': request.form.get('allow_vote_correction') == 'on',
        }
        election, err = create_election(current_user.organization_id, current_user.id, data)
        if err:
            flash(err, 'danger')
        else:
            flash('Election created successfully.', 'success')
            return redirect(url_for('admin.election_detail', election_id=election.id))
    return render_template('admin/election_form.html', election=None)


@admin_bp.route('/elections/<int:election_id>')
def election_detail(election_id):
    election = Election.query.filter_by(
        id=election_id, organization_id=current_user.organization_id).first_or_404()
    
    # Counts
    total_voted = election.total_voters_who_voted()
    total_eligible = election.total_eligible_voters()
    turnout = round((total_voted / total_eligible) * 100, 1) if total_eligible else 0
    
    return render_template('admin/election_detail.html',
                           election=election,
                           total_voted=total_voted,
                           total_eligible=total_eligible,
                           turnout=turnout)


@admin_bp.route('/elections/<int:election_id>/edit', methods=['GET', 'POST'])
def election_edit(election_id):
    election = Election.query.filter_by(
        id=election_id, organization_id=current_user.organization_id).first_or_404()
    
    if request.method == 'POST':
        data = request.form.to_dict()
        ok, msg = update_election(election, current_user.id, data)
        flash(msg, 'success' if ok else 'danger')
        if ok:
            return redirect(url_for('admin.election_detail', election_id=election.id))
    return render_template('admin/election_form.html', election=election)


@admin_bp.route('/elections/<int:election_id>/status', methods=['POST'])
def election_status(election_id):
    election = Election.query.filter_by(
        id=election_id, organization_id=current_user.organization_id).first_or_404()
    new_status = request.form.get('status') or (request.json or {}).get('status')
    ok, msg = change_election_status(election, current_user.id, new_status)
    if request.is_json:
        return jsonify({'ok': ok, 'message': msg}), (200 if ok else 400)
    flash(msg, 'success' if ok else 'danger')
    return redirect(url_for('admin.election_detail', election_id=election.id))


# ---------------- Positions & Candidates ----------------
@admin_bp.route('/elections/<int:election_id>/positions', methods=['POST'])
def add_position_route(election_id):
    election = Election.query.filter_by(
        id=election_id, organization_id=current_user.organization_id).first_or_404()
    data = request.form.to_dict()
    pos, err = add_position(election, current_user.id, data)
    if err:
        if request.is_json:
            return jsonify({'error': err}), 400
        flash(err, 'danger')
        return redirect(url_for('admin.election_detail', election_id=election.id))
    if request.is_json:
        return jsonify({'position': pos.to_dict()})
    flash('Position added.', 'success')
    return redirect(url_for('admin.election_detail', election_id=election.id))


@admin_bp.route('/positions/<int:position_id>/candidates', methods=['POST'])
def add_candidate_route(position_id):
    position = Position.query.join(Election).filter(
        Position.id == position_id,
        Election.organization_id == current_user.organization_id
    ).first_or_404()
    
    data = {
        'name': request.form.get('name', '').strip(),
        'description': request.form.get('description', '').strip(),
        'manifesto': request.form.get('manifesto', '').strip(),
        'identifier': request.form.get('identifier', '').strip(),
        'extra_info': request.form.get('extra_info', '').strip(),
    }
    photo_path = None
    if 'photo' in request.files and request.files['photo'].filename:
        photo_path = save_upload(request.files['photo'], 'candidates', 'cand_')
        data['photo'] = photo_path
    
    cand, err = add_candidate(position, current_user.organization_id, current_user.id, data)
    if err:
        if request.is_json:
            return jsonify({'error': err}), 400
        flash(err, 'danger')
    else:
        if request.is_json:
            return jsonify({'candidate': cand.to_dict()})
        flash('Candidate added.', 'success')
    return redirect(url_for('admin.election_detail', election_id=position.election_id))


@admin_bp.route('/candidates/<int:candidate_id>/edit', methods=['POST'])
def edit_candidate(candidate_id):
    cand = Candidate.query.filter_by(
        id=candidate_id, organization_id=current_user.organization_id).first_or_404()
    if cand.position.election.status in ('active', 'closed', 'announced'):
        return jsonify({'error': 'Cannot edit candidates after voting has started.'}), 400
    
    data = request.get_json() or request.form.to_dict()
    if data.get('name'):
        cand.name = data['name'].strip()
    for field in ('description', 'manifesto', 'identifier', 'extra_info'):
        if field in data:
            setattr(cand, field, data[field])
    db.session.commit()
    log_action(current_user.organization_id, current_user.id, 'candidate.update',
               'candidate', cand.id, f'Updated candidate "{cand.name}"')
    return jsonify({'candidate': cand.to_dict()})


@admin_bp.route('/candidates/<int:candidate_id>/delete', methods=['POST'])
def delete_candidate(candidate_id):
    cand = Candidate.query.filter_by(
        id=candidate_id, organization_id=current_user.organization_id).first_or_404()
    if cand.position.election.status in ('active', 'closed', 'announced'):
        return jsonify({'error': 'Cannot delete candidates after voting has started.'}), 400
    name = cand.name
    db.session.delete(cand)
    db.session.commit()
    log_action(current_user.organization_id, current_user.id, 'candidate.delete',
               'candidate', candidate_id, f'Deleted candidate "{name}"')
    return jsonify({'ok': True})


# ---------------- Voters ----------------
@admin_bp.route('/voters')
def voters():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '')
    
    query = User.query.filter_by(
        organization_id=current_user.organization_id, role='voter')
    if q:
        query = query.filter(or_(
            User.full_name.ilike(f'%{q}%'),
            User.email.ilike(f'%{q}%'),
            User.voter_id.ilike(f'%{q}%'),
        ))
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)
    elif status == 'pending':
        query = query.filter_by(is_approved=False)
    
    query = query.order_by(desc(User.created_at))
    pagination = query.paginate(page=page,
                                per_page=current_app.config['VOTERS_PER_PAGE'],
                                error_out=False)
    return render_template('admin/voters.html',
                           voters=pagination.items,
                           pagination=pagination, q=q, status=status)


@admin_bp.route('/voters/<int:user_id>/toggle-active', methods=['POST'])
def toggle_voter_active(user_id):
    user = User.query.filter_by(
        id=user_id, organization_id=current_user.organization_id, role='voter').first_or_404()
    user.is_active = not user.is_active
    db.session.commit()
    log_action(current_user.organization_id, current_user.id,
               'voter.toggle_active', 'user', user.id,
               f'Voter {user.email} -> {"active" if user.is_active else "inactive"}')
    return jsonify({'is_active': user.is_active})


@admin_bp.route('/voters/<int:user_id>/approve', methods=['POST'])
def approve_voter(user_id):
    user = User.query.filter_by(
        id=user_id, organization_id=current_user.organization_id, role='voter').first_or_404()
    user.is_approved = True
    db.session.commit()
    log_action(current_user.organization_id, current_user.id,
               'voter.approve', 'user', user.id, f'Approved voter {user.email}')
    return jsonify({'is_approved': True})


# ---------------- Results ----------------
@admin_bp.route('/elections/<int:election_id>/results')
def election_results(election_id):
    election = Election.query.filter_by(
        id=election_id, organization_id=current_user.organization_id).first_or_404()
    return render_template('admin/results.html', election=election)


@admin_bp.route('/elections/<int:election_id>/announce', methods=['POST'])
def announce_results(election_id):
    election = Election.query.filter_by(
        id=election_id, organization_id=current_user.organization_id).first_or_404()
    
    if election.status == 'active':
        return jsonify({'error': 'Close the election before announcing results.'}), 400
    
    ok, msg = change_election_status(election, current_user.id, 'announced')
    if ok:
        # Notify all voters
        voters = User.query.filter_by(
            organization_id=current_user.organization_id, role='voter', is_active=True).all()
        for v in voters:
            db.session.add(Notification(
                user_id=v.id,
                organization_id=current_user.organization_id,
                title='Results Announced',
                message=f'Results for "{election.name}" have been announced.',
                category='success',
                link=url_for('voter.election_results', election_id=election.id),
            ))
        db.session.commit()
    return jsonify({'ok': ok, 'message': msg}), (200 if ok else 400)


# ---------------- Settings ----------------
@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    org = current_user.organization
    if request.method == 'POST':
        org.name = request.form.get('name', org.name).strip()
        org.org_type = request.form.get('org_type', org.org_type)
        org.email = request.form.get('email', org.email).strip()
        org.phone = request.form.get('phone', org.phone)
        org.location = request.form.get('location', org.location)
        org.registration_number = request.form.get('registration_number', org.registration_number)
        org.description = request.form.get('description', org.description)
        org.voter_id_required = request.form.get('voter_id_required') == 'on'
        org.voter_id_label = request.form.get('voter_id_label', org.voter_id_label)
        org.allow_public_results = request.form.get('allow_public_results') == 'on'
        
        if 'logo' in request.files and request.files['logo'].filename:
            path = save_upload(request.files['logo'], 'logos', 'org_')
            if path:
                org.logo = path
        
        db.session.commit()
        log_action(org.id, current_user.id, 'org.update',
                   'organization', org.id, 'Organization settings updated')
        flash('Settings updated.', 'success')
        return redirect(url_for('admin.settings'))
    return render_template('admin/settings.html', org=org)


# ---------------- Audit Logs ----------------
@admin_bp.route('/audit-logs')
def audit_logs():
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.filter_by(organization_id=current_user.organization_id)\
        .order_by(desc(AuditLog.created_at))\
        .paginate(page=page, per_page=current_app.config['AUDIT_PER_PAGE'], error_out=False)
    return render_template('admin/audit_logs.html', pagination=logs)


# ---------------- API: notifications ----------------
@admin_bp.route('/api/notifications')
def notifications():
    items = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(desc(Notification.created_at)).limit(20).all()
    return jsonify([n.to_dict() for n in items])


@admin_bp.route('/api/notifications/mark-read', methods=['POST'])
def mark_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    return jsonify({'ok': True})


# ---------------- API: dashboard stats ----------------
@admin_bp.route('/api/stats')
def api_stats():
    org_id = current_user.organization_id
    total_voters = User.query.filter_by(
        organization_id=org_id, role='voter', is_active=True).count()
    total_elections = Election.query.filter_by(organization_id=org_id).count()
    active = Election.query.filter_by(organization_id=org_id, status='active').count()
    return jsonify({
        'total_voters': total_voters,
        'total_elections': total_elections,
        'active_elections': active,
    })