// Chaguzi - admin.js

// ---------- Dashboard Chart ----------
function initChart() {
    const canvas = document.getElementById('participationChart');
    if (!canvas || !window.CHART_DATA) return;
    const ctx = canvas.getContext('2d');
    const data = window.CHART_DATA;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Votes Cast',
                    data: data.votes,
                    backgroundColor: '#1f4fd8',
                    borderRadius: 6,
                },
                {
                    label: 'Eligible Voters',
                    data: data.eligible,
                    backgroundColor: '#cbd5e1',
                    borderRadius: 6,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            },
            scales: {
                y: { beginAtZero: true, ticks: { precision: 0 } }
            }
        }
    });
}

// ---------- Election Detail: Candidate Modal ----------
function openAddCandidate(positionId, positionTitle) {
    const modal = document.getElementById('addCandidateModal');
    const form = document.getElementById('addCandidateForm');
    if (!modal || !form) return;
    document.getElementById('candPosTitle').textContent = positionTitle;
    form.action = `/admin/positions/${positionId}/candidates`;
    modal.classList.add('open');
}
window.openAddCandidate = openAddCandidate;

async function deleteCandidate(candidateId) {
    if (!confirmAction('Delete this candidate? This cannot be undone.')) return;
    try {
        await apiFetch(`/admin/candidates/${candidateId}/delete`, { method: 'POST' });
        showToast('Candidate deleted.', 'success');
        setTimeout(() => location.reload(), 500);
    } catch (err) {
        showToast(err.message, 'error');
    }
}
window.deleteCandidate = deleteCandidate;

async function toggleVoter(userId) {
    try {
        const data = await apiFetch(`/admin/voters/${userId}/toggle-active`, { method: 'POST' });
        showToast(`Voter is now ${data.is_active ? 'active' : 'inactive'}.`, 'success');
        setTimeout(() => location.reload(), 400);
    } catch (err) {
        showToast(err.message, 'error');
    }
}
window.toggleVoter = toggleVoter;

document.addEventListener('DOMContentLoaded', () => {
    initChart();

    // Close modals when clicking outside
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.classList.remove('open');
        });
    });
});