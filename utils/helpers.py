import os
import re
import secrets
import hashlib
from werkzeug.utils import secure_filename
from flask import current_app


def slugify_text(text):
    """Simple slug generator (no external dependency)."""
    text = (text or '').lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-') or secrets.token_hex(4)


def make_unique_slug(model, base, field='slug'):
    """Generate a unique slug given a SQLAlchemy model."""
    from extensions import db
    base = slugify_text(base)
    slug = base
    i = 1
    while db.session.query(model.id).filter(getattr(model, field) == slug).first():
        i += 1
        slug = f'{base}-{i}'
    return slug


def save_upload(file, subfolder='misc', prefix=''):
    """Save an uploaded file, returning the relative path (under static/)."""
    if not file or not file.filename:
        return None
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'bin'
    token = secrets.token_hex(8)
    new_name = f'{prefix}{token}.{ext}' if prefix else f'{token}.{ext}'
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(folder, exist_ok=True)
    full_path = os.path.join(folder, new_name)
    file.save(full_path)
    return f'uploads/{subfolder}/{new_name}'


def generate_vote_receipt(voter_id, election_id, position_id):
    """Generate a non-reversible receipt hash for audit purposes."""
    raw = f'{voter_id}:{election_id}:{position_id}:{secrets.token_hex(8)}'
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def get_client_ip():
    """Get the client IP, honoring X-Forwarded-For behind proxies."""
    from flask import request
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or 'unknown'