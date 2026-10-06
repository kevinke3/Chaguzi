import re


def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email or ''))


def validate_phone(phone):
    if not phone:
        return True  # optional
    pattern = r'^\+?[0-9\s\-()]{7,20}$'
    return bool(re.match(pattern, phone))


def validate_password(password):
    """Return (ok, message)."""
    if not password or len(password) < 8:
        return False, 'Password must be at least 8 characters long.'
    if not re.search(r'[A-Za-z]', password):
        return False, 'Password must contain at least one letter.'
    if not re.search(r'\d', password):
        return False, 'Password must contain at least one number.'
    return True, ''


def sanitize_string(value, max_len=500):
    if value is None:
        return ''
    value = str(value).strip()
    return value[:max_len]


def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in allowed_extensions