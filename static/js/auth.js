// Chaguzi - auth.js

document.addEventListener('DOMContentLoaded', () => {
    const roleSwitch = document.getElementById('roleSwitch');
    const roleInput = document.getElementById('roleInput');
    const voterFields = document.querySelector('.role-fields[data-role="voter"]');
    const adminFields = document.querySelector('.role-fields[data-role="admin"]');
    const orgSelect = document.getElementById('v_org');
    const voterIdLabel = document.getElementById('voterIdLabel');
    const voterIdInput = document.getElementById('v_voter_id');
    const registerForm = document.getElementById('registerForm');

    if (!roleSwitch) return;

    roleSwitch.addEventListener('click', (e) => {
        const btn = e.target.closest('.role-btn');
        if (!btn) return;
        const role = btn.dataset.role;
        document.querySelectorAll('.role-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        roleInput.value = role;

        if (role === 'admin') {
            voterFields.classList.add('hidden');
            adminFields.classList.remove('hidden');
            orgSelect.required = false;
            voterIdInput.required = false;
            document.getElementById('a_org_name').required = true;
        } else {
            adminFields.classList.add('hidden');
            voterFields.classList.remove('hidden');
            orgSelect.required = true;
            document.getElementById('a_org_name').required = false;
        }
    });

    // Load voter ID label when org is selected
    if (orgSelect) {
        orgSelect.addEventListener('change', async () => {
            const orgId = orgSelect.value;
            if (!orgId) return;
            try {
                const res = await fetch(`/auth/api/org/${orgId}/config`);
                const data = await res.json();
                if (data.voter_id_label) {
                    voterIdLabel.textContent = data.voter_id_label + (data.voter_id_required ? ' *' : '');
                    voterIdInput.placeholder = data.voter_id_label;
                    voterIdInput.required = !!data.voter_id_required;
                }
            } catch (e) {}
        });
    }

    // Simple password confirmation
    if (registerForm) {
        registerForm.addEventListener('submit', (e) => {
            const pwd = document.getElementById('password').value;
            const confirm = document.getElementById('confirm_password').value;
            if (pwd !== confirm) {
                e.preventDefault();
                showToast('Passwords do not match.', 'error');
            }
        });
    }
});