from datetime import datetime, timedelta
from extensions import db
from models.user import User
from models.organization import Organization
from utils.validators import validate_password, validate_email


LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 15


def authenticate(email, password, organization_id=None):
    """Authenticate a user. Returns (user, error_message)."""
    if not email or not password:
        return None, 'Email and password are required.'
    
    query = User.query.filter(User.email == email.lower().strip())
    if organization_id:
        query = query.filter(User.organization_id == organization_id)
    
    user = query.first()
    
    if not user:
        return None, 'Invalid credentials.'
    
    # Check lockout
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = (user.locked_until - datetime.utcnow()).seconds // 60
        return None, f'Account locked. Try again in {remaining + 1} minute(s).'
    
    if not user.is_active:
        return None, 'Your account has been deactivated. Contact your administrator.'
    
    if not user.is_approved:
        return None, 'Your account is pending approval.'
    
    if not user.check_password(password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= LOCKOUT_THRESHOLD:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
        db.session.commit()
        return None, 'Invalid credentials.'
    
    # Success
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    db.session.commit()
    return user, None


def register_admin(data, org_data, logo_path=None):
    """Register a new organization and its administrator."""
    from utils.helpers import make_unique_slug, slugify_text
    
    # Validate
    ok, msg = validate_password(data.get('password', ''))
    if not ok:
        return None, msg
    
    if not validate_email(data.get('email')):
        return None, 'Invalid email address.'
    
    if not org_data.get('name'):
        return None, 'Organization name is required.'
    
    # Check org name uniqueness
    if Organization.query.filter_by(name=org_data['name']).first():
        return None, 'An organization with this name already exists.'
    
    # Check email uniqueness within new org (trivially true, but check globally for admins)
    slug = make_unique_slug(Organization, org_data['name'], field='slug')
    
    org = Organization(
        name=org_data['name'],
        slug=slug,
        org_type=org_data.get('org_type', 'school'),
        email=org_data.get('email') or data['email'],
        phone=org_data.get('phone'),
        location=org_data.get('location'),
        registration_number=org_data.get('registration_number'),
        description=org_data.get('description'),
        logo=logo_path,
        voter_id_required=bool(org_data.get('voter_id_required', True)),
        voter_id_label=org_data.get('voter_id_label') or 'Membership ID',
    )
    db.session.add(org)
    db.session.flush()
    
    admin = User(
        organization_id=org.id,
        role='admin',
        full_name=data['full_name'].strip(),
        email=data['email'].lower().strip(),
        phone=data.get('phone'),
        is_active=True,
        is_approved=True,
    )
    admin.set_password(data['password'])
    db.session.add(admin)
    db.session.commit()
    return admin, None


def register_voter(data):
    """Register a new voter."""
    ok, msg = validate_password(data.get('password', ''))
    if not ok:
        return None, msg
    
    if not validate_email(data.get('email')):
        return None, 'Invalid email address.'
    
    org_id = data.get('organization_id')
    if not org_id:
        return None, 'Please select your organization.'
    
    org = db.session.get(Organization, int(org_id))
    if not org or not org.is_active:
        return None, 'Selected organization is invalid or inactive.'
    
    email = data['email'].lower().strip()
    
    # Uniqueness within organization
    if User.query.filter_by(organization_id=org.id, email=email).first():
        return None, 'An account with this email already exists for this organization.'
    
    voter_id = (data.get('voter_id') or '').strip() or None
    if org.voter_id_required and not voter_id:
        return None, f'{org.voter_id_label} is required.'
    if voter_id:
        if User.query.filter_by(organization_id=org.id, voter_id=voter_id).first():
            return None, f'This {org.voter_id_label} is already registered.'
    
    voter = User(
        organization_id=org.id,
        role='voter',
        full_name=data['full_name'].strip(),
        email=email,
        phone=data.get('phone'),
        voter_id=voter_id,
        is_active=True,
        is_approved=True,
    )
    voter.set_password(data['password'])
    db.session.add(voter)
    db.session.commit()
    return voter, None


def change_password(user, old_password, new_password):
    if not user.check_password(old_password):
        return False, 'Current password is incorrect.'
    ok, msg = validate_password(new_password)
    if not ok:
        return False, msg
    user.set_password(new_password)
    db.session.commit()
    return True, 'Password changed successfully.'