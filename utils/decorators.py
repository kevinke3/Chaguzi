from functools import wraps
from flask import abort, jsonify, request, redirect, url_for, flash
from flask_login import current_user


def admin_required(f):
    """Restrict route to organization administrators."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json or request.path.startswith('/api'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login'))
        if not current_user.is_admin:
            if request.is_json or request.path.startswith('/api'):
                return jsonify({'error': 'Administrator access required'}), 403
            abort(403)
        if not current_user.is_active or not current_user.is_approved:
            if request.is_json:
                return jsonify({'error': 'Account is not active'}), 403
            abort(403)
        return f(*args, **kwargs)
    return decorated


def voter_required(f):
    """Restrict route to voters."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json or request.path.startswith('/api'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login'))
        if not current_user.is_voter:
            if request.is_json or request.path.startswith('/api'):
                return jsonify({'error': 'Voter access required'}), 403
            abort(403)
        if not current_user.is_active or not current_user.is_approved:
            if request.is_json:
                return jsonify({'error': 'Account is not active'}), 403
            abort(403)
        return f(*args, **kwargs)
    return decorated


def org_required(f):
    """Ensure user has an organization."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.organization_id:
            abort(403)
        return f(*args, **kwargs)
    return decorated