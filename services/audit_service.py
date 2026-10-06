from extensions import db
from models.audit_log import AuditLog
from utils.helpers import get_client_ip
from flask import request


def log_action(organization_id, actor_id, action,
               entity_type=None, entity_id=None, description=None):
    """Record an audit log entry."""
    try:
        ip = get_client_ip()
        ua = (request.headers.get('User-Agent') or '')[:300] if request else ''
    except Exception:
        ip, ua = None, None
    
    entry = AuditLog(
        organization_id=organization_id,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        ip_address=ip,
        user_agent=ua,
    )
    db.session.add(entry)
    db.session.commit()
    return entry