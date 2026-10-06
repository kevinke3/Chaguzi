from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models.organization import Organization
from models.user import User
from services.auth_service import (
    authenticate, register_admin, register_voter, change_password
)
from services.audit_service import log_action
from utils.helpers import save_upload
from utils.validators import validate_email

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard_redirect'))
    
    if request.method == 'POST':
        data = request.form
        email = data.get('email', '').strip()
        password = data.get('password', '')
        remember = bool(data.get('remember'))
        org_id = data.get('organization_id')
        
        user, err = authenticate(email, password, org_id)
        if err:
            flash(err, 'danger')
            return render_template('auth/login.html',
                                   organizations=Organization.query.filter_by(is_active=True).all())
        
        login_user(user, remember=remember)
        user.last_login_ip = request.remote_addr
        db.session.commit()
        log_action(user.organization_id, user.id, 'auth.login',
                   'user', user.id, 'User logged in')
        
        next_url = request.args.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect(url_for('auth.dashboard_redirect'))
    
    return render_template('auth/login.html',
                           organizations=Organization.query.filter_by(is_active=True).all())


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard_redirect'))
    
    organizations = Organization.query.filter_by(is_active=True).order_by(Organization.name).all()
    
    if request.method == 'POST':
        role = request.form.get('role', 'voter')
        
        if role == 'admin':
            # Admin registration creates organization
            org_data = {
                'name': request.form.get('org_name', '').strip(),
                'org_type': request.form.get('org_type', 'school'),
                'email': request.form.get('org_email', '').strip(),
                'phone': request.form.get('org_phone', '').strip(),
                'location': request.form.get('org_location', '').strip(),
                'registration_number': request.form.get('org_reg_number', '').strip(),
                'description': request.form.get('org_description', '').strip(),
                'voter_id_required': request.form.get('voter_id_required') == 'on',
                'voter_id_label': request.form.get('voter_id_label', 'Membership ID'),
            }
            admin_data = {
                'full_name': request.form.get('full_name', '').strip(),
                'email': request.form.get('email', '').strip(),
                'phone': request.form.get('phone', '').strip(),
                'password': request.form.get('password', ''),
            }
            if request.form.get('password') != request.form.get('confirm_password'):
                flash('Passwords do not match.', 'danger')
                return render_template('auth/register.html', organizations=organizations, role=role)
            
            logo_path = None
            if 'logo' in request.files and request.files['logo'].filename:
                logo_path = save_upload(request.files['logo'], 'logos', 'org_')
            
            user, err = register_admin(admin_data, org_data, logo_path)
            if err:
                flash(err, 'danger')
                return render_template('auth/register.html', organizations=organizations, role=role)
            
            log_action(user.organization_id, user.id, 'org.register',
                       'organization', user.organization_id,
                       f'Registered organization "{org_data["name"]}"')
            flash('Organization registered successfully. You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        
        else:
            # Voter registration
            voter_data = {
                'full_name': request.form.get('full_name', '').strip(),
                'email': request.form.get('email', '').strip(),
                'phone': request.form.get('phone', '').strip(),
                'voter_id': request.form.get('voter_id', '').strip(),
                'password': request.form.get('password', ''),
                'organization_id': request.form.get('organization_id'),
            }
            if request.form.get('password') != request.form.get('confirm_password'):
                flash('Passwords do not match.', 'danger')
                return render_template('auth/register.html', organizations=organizations, role=role)
            
            user, err = register_voter(voter_data)
            if err:
                flash(err, 'danger')
                return render_template('auth/register.html', organizations=organizations, role=role)
            
            log_action(user.organization_id, user.id, 'voter.register',
                       'user', user.id, 'New voter registered')
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', organizations=organizations, role='voter')


@auth_bp.route('/logout')
@login_required
def logout():
    log_action(current_user.organization_id, current_user.id, 'auth.logout',
               'user', current_user.id, 'User logged out')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/dashboard')
@login_required
def dashboard_redirect():
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('voter.dashboard'))


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password_route():
    old = request.form.get('old_password', '')
    new = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')
    
    if new != confirm:
        return jsonify({'error': 'New passwords do not match.'}), 400
    
    ok, msg = change_password(current_user, old, new)
    if not ok:
        return jsonify({'error': msg}), 400
    
    log_action(current_user.organization_id, current_user.id, 'auth.password_change',
               'user', current_user.id, 'Password changed')
    return jsonify({'message': msg})


@auth_bp.route('/api/organizations')
def api_organizations():
    """Public endpoint: list active organizations (for registration)."""
    orgs = Organization.query.filter_by(is_active=True).order_by(Organization.name).all()
    return jsonify([o.to_dict() for o in orgs])


@auth_bp.route('/api/org/<int:org_id>/config')
def api_org_config(org_id):
    """Public: get org config (e.g. voter ID label)."""
    org = db.session.get(Organization, org_id)
    if not org or not org.is_active:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'id': org.id,
        'name': org.name,
        'voter_id_required': org.voter_id_required,
        'voter_id_label': org.voter_id_label,
    })