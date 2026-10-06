// Chaguzi - voting.js

document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('votingApp');
    if (!app) return;

    const electionId = app.dataset.electionId;
    const positions = JSON.parse(app.dataset.positions || '[]');
    const selections = {}; // { positionId: candidateId }
    let currentIndex = 0;
    let reviewing = false;

    if (!positions.length) {
        app.innerHTML = '<div class="panel empty-state"><h3>No positions to vote for</h3><p>You may have already voted or there are no positions.</p></div>';
        return;
    }

    function render() {
        if (reviewing) return renderReview();

        const pos = positions[currentIndex];
        const total = positions.length;

        app.innerHTML = `
            <div class="vote-header">
                <div class="row-space">
                    <strong>Position ${currentIndex + 1} of ${total}</strong>
                    <span class="muted small">${Object.keys(selections).length} selected</span>
                </div>
                <div class="vote-progress">
                    ${positions.map((_, i) => `
                        <div class="vote-progress-dot ${i < currentIndex ? 'done' : ''} ${i === currentIndex ? 'active' : ''}"></div>
                    `).join('')}
                </div>
            </div>

            <div class="vote-position">
                <h3>${escapeHtml(pos.title)}</h3>
                ${pos.description ? `<p class="desc">${escapeHtml(pos.description)}</p>` : ''}
                <div class="vote-candidates">
                    ${pos.candidates.map(c => `
                        <div class="vote-candidate ${selections[pos.id] == c.id ? 'selected' : ''}"
                             data-pos="${pos.id}" data-cand="${c.id}">
                            <div class="vote-candidate-photo">
                                ${c.photo ? `<img src="/static/${c.photo}" alt="">` : escapeHtml(c.name[0] || '?')}
                            </div>
                            <div class="vote-candidate-name">${escapeHtml(c.name)}</div>
                            ${c.description ? `<div class="vote-candidate-desc">${escapeHtml(c.description)}</div>` : ''}
                            ${c.manifesto ? `<div class="vote-candidate-manifesto">${escapeHtml(c.manifesto)}</div>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>

            <div class="vote-footer">
                <button class="btn btn-ghost" id="prevBtn" ${currentIndex === 0 ? 'disabled' : ''}>← Previous</button>
                <div>
                    ${currentIndex < total - 1
                        ? `<button class="btn btn-primary" id="nextBtn">Next →</button>`
                        : `<button class="btn btn-primary" id="reviewBtn">Review & Submit</button>`}
                </div>
            </div>
        `;

        // Attach candidate click handlers
        app.querySelectorAll('.vote-candidate').forEach(el => {
            el.addEventListener('click', () => {
                const pid = el.dataset.pos;
                const cid = el.dataset.cand;
                selections[pid] = cid;
                // Re-render just the candidate state for smoothness
                app.querySelectorAll(`.vote-candidate[data-pos="${pid}"]`).forEach(x => x.classList.remove('selected'));
                el.classList.add('selected');
            });
        });

        document.getElementById('prevBtn')?.addEventListener('click', () => {
            if (currentIndex > 0) { currentIndex--; render(); }
        });

        document.getElementById('nextBtn')?.addEventListener('click', () => {
            if (!selections[pos.id]) {
                showToast('Please select a candidate before continuing.', 'warning');
                return;
            }
            currentIndex++;
            render();
        });

        document.getElementById('reviewBtn')?.addEventListener('click', () => {
            // Check all positions have selections
            const missing = positions.filter(p => !selections[p.id]);
            if (missing.length) {
                showToast(`Please make a selection for: ${missing[0].title}`, 'warning');
                currentIndex = positions.indexOf(missing[0]);
                render();
                return;
            }
            reviewing = true;
            render();
        });
    }

    function renderReview() {
        const rows = positions.map(p => {
            const selId = selections[p.id];
            const cand = p.candidates.find(c => c.id == selId);
            return `
                <li>
                    <span><strong>${escapeHtml(p.title)}</strong></span>
                    <span>${cand ? escapeHtml(cand.name) : '<em>Not selected</em>'}</span>
                </li>
            `;
        }).join('');

        app.innerHTML = `
            <div class="vote-header">
                <strong>Review your selections</strong>
                <p class="muted small">Make sure everything is correct. Once submitted, your vote is final.</p>
            </div>
            <div class="vote-position">
                <ul class="review-list">${rows}</ul>
            </div>
            <div class="vote-footer">
                <button class="btn btn-ghost" id="backBtn">← Back to Voting</button>
                <button class="btn btn-primary btn-lg" id="submitBtn">✓ Submit My Vote</button>
            </div>
        `;

        document.getElementById('backBtn').addEventListener('click', () => {
            reviewing = false;
            currentIndex = 0;
            render();
        });

        document.getElementById('submitBtn').addEventListener('click', submitVotes);
    }

    async function submitVotes() {
        const btn = document.getElementById('submitBtn');
        btn.disabled = true;
        btn.textContent = 'Submitting...';

        try {
            const data = await apiFetch(`/voter/elections/${electionId}/submit`, {
                method: 'POST',
                body: { selections },
            });
            app.innerHTML = `
                <div class="panel empty-state">
                    <h2 style="color: var(--success);">✓ Vote Recorded</h2>
                    <p>${escapeHtml(data.message || 'Your vote has been recorded successfully.')}</p>
                    <a href="/voter/dashboard" class="btn btn-primary">Back to Dashboard</a>
                </div>
            `;
        } catch (err) {
            showToast(err.message, 'error', 6000);
            btn.disabled = false;
            btn.textContent = '✓ Submit My Vote';
        }
    }

    render();
});