// Chaguzi - main.js

const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]')?.content || '';

// ---------- Toast ----------
function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.transition = 'opacity .3s, transform .3s';
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}
window.showToast = showToast;

// ---------- Fetch helper ----------
async function apiFetch(url, options = {}) {
    const opts = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': CSRF_TOKEN,
            ...(options.headers || {}),
        },
        credentials: 'same-origin',
        ...options,
    };
    if (opts.body && typeof opts.body !== 'string' && !(opts.body instanceof FormData)) {
        opts.body = JSON.stringify(opts.body);
    }
    const res = await fetch(url, opts);
    const contentType = res.headers.get('content-type') || '';
    let data;
    if (contentType.includes('application/json')) {
        data = await res.json();
    } else {
        data = { error: await res.text() };
    }
    if (!res.ok) {
        throw new Error(data.error || `Request failed (${res.status})`);
    }
    return data;
}
window.apiFetch = apiFetch;

// ---------- Confirm dialog ----------
function confirmAction(message) {
    return window.confirm(message);
}
window.confirmAction = confirmAction;

// ---------- Sidebar toggle (mobile) ----------
document.addEventListener('DOMContentLoaded', () => {
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // ---------- Notifications ----------
    const bell = document.getElementById('notifBell');
    const panel = document.getElementById('notifPanel');
    const notifBody = document.getElementById('notifBody');
    const markReadBtn = document.getElementById('markReadBtn');

    if (bell && panel) {
        bell.addEventListener('click', async (e) => {
            e.stopPropagation();
            panel.classList.toggle('open');
            if (panel.classList.contains('open')) {
                await loadNotifications();
            }
        });
        document.addEventListener('click', (e) => {
            if (!panel.contains(e.target) && e.target !== bell) {
                panel.classList.remove('open');
            }
        });
    }

    async function loadNotifications() {
        if (!notifBody) return;
        try {
            const url = window.location.pathname.startsWith('/admin')
                ? '/admin/api/notifications'
                : '/voter/api/notifications';
            const items = await apiFetch(url);
            if (!items.length) {
                notifBody.innerHTML = '<p class="empty">No notifications.</p>';
                return;
            }
            notifBody.innerHTML = items.map(n => `
                <div class="notif-item">
                    <strong>${escapeHtml(n.title)}</strong>
                    <p>${escapeHtml(n.message)}</p>
                    <small>${new Date(n.created_at).toLocaleString()}</small>
                </div>
            `).join('');
        } catch (err) {
            notifBody.innerHTML = '<p class="empty">Could not load notifications.</p>';
        }
    }

    if (markReadBtn) {
        markReadBtn.addEventListener('click', async () => {
            try {
                const url = window.location.pathname.startsWith('/admin')
                    ? '/admin/api/notifications/mark-read'
                    : '/voter/api/notifications/mark-read';
                await apiFetch(url, { method: 'POST' });
                await loadNotifications();
                const badge = document.querySelector('.notif-bell .badge');
                if (badge) badge.remove();
            } catch (err) {
                showToast(err.message, 'error');
            }
        });
    }

    // Auto-load notifications count every 30s
    if (bell) {
        setInterval(async () => {
            try {
                const url = window.location.pathname.startsWith('/admin')
                    ? '/admin/api/notifications'
                    : '/voter/api/notifications';
                const items = await apiFetch(url);
                const unread = items.filter(n => !n.is_read).length;
                let badge = document.querySelector('.notif-bell .badge');
                if (unread > 0) {
                    if (!badge) {
                        badge = document.createElement('span');
                        badge.className = 'badge';
                        bell.appendChild(badge);
                    }
                    badge.textContent = unread;
                } else if (badge) {
                    badge.remove();
                }
            } catch (e) {}
        }, 30000);
    }
});

// ---------- Helpers ----------
function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
window.escapeHtml = escapeHtml;