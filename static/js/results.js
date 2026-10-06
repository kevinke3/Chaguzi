// Chaguzi - results.js

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('resultsContainer');
    if (!container) return;

    const electionId = window.ELECTION_ID;
    const pollMs = window.RESULTS_POLL_MS || 0;
    const lastUpdatedEl = document.getElementById('lastUpdated');

    let chartInstances = {};

    async function loadResults() {
        try {
            const data = await apiFetch(`/results/api/election/${electionId}`);
            renderResults(data);
            if (lastUpdatedEl) {
                lastUpdatedEl.textContent = 'Updated: ' + new Date().toLocaleTimeString();
            }
        } catch (err) {
            container.innerHTML = `<div class="panel"><p class="empty">${escapeHtml(err.message)}</p></div>`;
        }
    }

    function renderResults(data) {
        const stats = data.stats || {};
        const positionsHtml = data.positions.map(pos => renderPosition(pos)).join('');

        container.innerHTML = `
            <div class="stats-grid">
                <div class="stat-card"><div class="stat-label">Eligible</div><div class="stat-value">${stats.total_eligible || 0}</div></div>
                <div class="stat-card"><div class="stat-label">Voted</div><div class="stat-value">${stats.total_voted || 0}</div></div>
                <div class="stat-card"><div class="stat-label">Not Voted</div><div class="stat-value">${stats.total_not_voted || 0}</div></div>
                <div class="stat-card"><div class="stat-label">Turnout</div><div class="stat-value">${stats.turnout_percentage || 0}%</div></div>
            </div>
            ${positionsHtml}
        `;

        // Attach chart renders
        data.positions.forEach(pos => {
            const canvas = document.getElementById(`chart-${pos.id}`);
            if (!canvas) return;
            if (chartInstances[pos.id]) chartInstances[pos.id].destroy();
            const ctx = canvas.getContext('2d');
            chartInstances[pos.id] = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: pos.candidates.map(c => c.name),
                    datasets: [{
                        data: pos.candidates.map(c => c.votes),
                        backgroundColor: ['#1f4fd8', '#3a6df0', '#93b3ff', '#c7d7ff', '#e0e8ff', '#f0f4ff'],
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { position: 'right' } }
                }
            });
        });
    }

    function renderPosition(pos) {
        const total = pos.total_votes || 0;
        const rows = pos.candidates.map((c, i) => {
            const isWinner = pos.winner && pos.winner === c.name && c.votes > 0;
            return `
                <div class="result-row ${isWinner ? 'winner' : ''}">
                    <div class="result-rank">#${i + 1}</div>
                    <div class="result-photo">
                        ${c.photo ? `<img src="/static/${c.photo}" alt="">` : escapeHtml(c.name[0] || '?')}
                    </div>
                    <div class="result-info">
                        <strong>${escapeHtml(c.name)}</strong>
                        ${isWinner ? '<span class="winner-tag">Winner</span>' : ''}
                        <div class="result-bar"><div style="width: ${c.percentage || 0}%"></div></div>
                    </div>
                    <div class="result-votes">
                        <strong>${c.votes}</strong>
                        <small>${c.percentage || 0}%</small>
                    </div>
                </div>
            `;
        }).join('');

        const tie = pos.is_tie ? '<p class="muted small">⚠ Tie detected</p>' : '';

        return `
            <div class="panel results-position">
                <div class="row-space">
                    <h3>${escapeHtml(pos.title)}</h3>
                    <span class="muted small">${total} total vote(s)</span>
                </div>
                ${tie}
                ${rows}
                <div class="chart-wrap"><canvas id="chart-${pos.id}" height="120"></canvas></div>
            </div>
        `;
    }

    loadResults();
    if (pollMs > 0) {
        setInterval(loadResults, pollMs);
    }
});