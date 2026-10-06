from flask import Blueprint, jsonify, render_template
from datetime import datetime
from extensions import db
from models.election import Election
from models.organization import Organization

elections_bp = Blueprint('elections', __name__)


@elections_bp.route('/public/<int:election_id>')
def public_election(election_id):
    election = db.session.get(Election, election_id)
    if not election:
        return render_template('errors/404.html'), 404
    org = election.organization
    if not org.allow_public_results and election.status != 'announced':
        return render_template('public_results.html', election=election, org=org, allowed=False)
    return render_template('public_results.html', election=election, org=org, allowed=True)


@elections_bp.route('/api/organizations')
def list_orgs():
    orgs = Organization.query.filter_by(is_active=True).all()
    return jsonify([o.to_dict() for o in orgs])