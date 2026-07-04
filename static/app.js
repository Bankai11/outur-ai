const API_BASE = '/api/v1';

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardMetrics();
    loadCampaigns();

    document.getElementById('new-campaign-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('campaign-name').value;
        
        try {
            // Very simplified: creating a campaign with dummy target lists to pass validation
            // In a real app, this would involve selecting companies and contacts from the discovery page.
            const res = await fetch(`${API_BASE}/campaigns`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    selected_companies: [], // Would be populated from discovery
                    selected_contacts: []
                })
            });
            if (res.ok) {
                closeModals();
                loadCampaigns();
            } else {
                const data = await res.json();
                alert('Error creating campaign: ' + JSON.stringify(data));
            }
        } catch (error) {
            console.error('Failed to create campaign', error);
            alert('Failed to create campaign');
        }
    });
});

async function loadDashboardMetrics() {
    try {
        const res = await fetch(`${API_BASE}/dashboard/metrics`);
        const data = await res.json();
        
        document.getElementById('metric-prospects').textContent = data.prospects_today || 0;
        document.getElementById('metric-qualified').textContent = data.qualified || 0;
        document.getElementById('metric-verified').textContent = data.verified_emails || 0;
        document.getElementById('metric-high-opp').textContent = data.high_opportunity || 0;
        document.getElementById('metric-sent').textContent = data.emails_sent || 0;
        document.getElementById('metric-replies').textContent = data.replies || 0;
        document.getElementById('metric-positive').textContent = data.positive_replies || 0;
    } catch (error) {
        console.error('Failed to load metrics', error);
    }
}

async function loadCampaigns() {
    try {
        const res = await fetch(`${API_BASE}/campaigns?limit=50`);
        const data = await res.json();
        
        const tbody = document.getElementById('campaigns-tbody');
        tbody.innerHTML = '';
        
        if (data.items && data.items.length > 0) {
            data.items.forEach(c => {
                const tr = document.createElement('tr');
                const targetCount = c.selected_companies.length + c.selected_contacts.length;
                tr.innerHTML = `
                    <td><strong>${c.name}</strong></td>
                    <td><span class="status-badge status-${c.status}">${c.status}</span></td>
                    <td>${targetCount} targets</td>
                    <td>${new Date().toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-secondary" onclick="openCampaignDetails('${c.id}', '${c.name}')">Intelligence View</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="5">No campaigns found. Create one to get started.</td></tr>';
        }
    } catch (error) {
        console.error('Failed to load campaigns', error);
    }
}

let currentCampaignId = null;

async function openCampaignDetails(id, name) {
    currentCampaignId = id;
    document.getElementById('detail-campaign-name').textContent = name + " - Intelligence";
    
    document.getElementById('modal-overlay').style.display = 'flex';
    document.getElementById('campaign-details-modal').style.display = 'flex';
    
    await loadDrafts(id);
}

async function loadDrafts(campaignId) {
    const container = document.getElementById('drafts-container');
    container.innerHTML = '<p style="color: var(--text-muted)">Loading intelligence data...</p>';
    
    try {
        const res = await fetch(`${API_BASE}/campaigns/${campaignId}/drafts`);
        const data = await res.json();
        
        if (data.success && data.data.length > 0) {
            renderDrafts(data.data);
        } else {
            container.innerHTML = '<p style="color: var(--text-muted)">Click "Generate Outreach Drafts" to run the Research Engine and create emails.</p>';
        }
    } catch (error) {
        console.error('Failed to load drafts', error);
        container.innerHTML = '<p style="color: red">Failed to load drafts.</p>';
    }
}

async function generateDrafts() {
    if (!currentCampaignId) return;
    
    const container = document.getElementById('drafts-container');
    container.innerHTML = '<p style="color: var(--text-muted)">Running Research Intelligence Engine & drafting emails... (this may take a moment)</p>';
    
    try {
        const res = await fetch(`${API_BASE}/campaigns/${currentCampaignId}/generate`, {
            method: 'POST'
        });
        const data = await res.json();
        
        if (data.success) {
            await loadDrafts(currentCampaignId);
            loadCampaigns(); // Refresh status in background
            loadDashboardMetrics(); // Refresh metrics
        } else {
            container.innerHTML = `<p style="color: red">No drafts generated. Error: ${JSON.stringify(data.errors)}</p>`;
        }
    } catch (error) {
        console.error('Failed to generate drafts', error);
        container.innerHTML = '<p style="color: red">Failed to generate drafts.</p>';
    }
}

async function sendCampaign() {
    if (!currentCampaignId) return;
    
    if (!confirm('Are you sure you want to send all drafts for this campaign?')) return;
    
    try {
        const res = await fetch(`${API_BASE}/campaigns/${currentCampaignId}/send`, {
            method: 'POST'
        });
        const data = await res.json();
        
        if (data.success) {
            alert(data.message);
            closeModals();
            loadCampaigns();
            loadDashboardMetrics();
        } else {
            alert('Error: ' + JSON.stringify(data));
        }
    } catch (error) {
        console.error('Failed to send campaign', error);
        alert('Failed to send campaign');
    }
}

function renderDrafts(drafts) {
    const container = document.getElementById('drafts-container');
    container.innerHTML = '';
    
    drafts.forEach(item => {
        const d = item.draft;
        const div = document.createElement('div');
        div.className = 'intelligence-card';
        
        const oppClass = item.opportunity_score > 70 ? 'high' : '';
        const signalsHtml = item.hiring_signals.map(s => `<li>${s}</li>`).join('') + 
                            item.recent_news.map(n => `<li>${n}</li>`).join('');
                            
        div.innerHTML = `
            <div class="intelligence-header">
                <div>
                    <h4 class="intelligence-title">${item.company_name}</h4>
                    <div class="intelligence-subtitle">
                        Best Contact: <strong>${item.contact_name}</strong> (${item.contact_title}) &mdash; Confidence: ${item.contact_confidence}%
                    </div>
                </div>
                <div class="score-badge ${oppClass}" title="Opportunity Score">
                    ${item.opportunity_score}
                </div>
            </div>
            <div class="intelligence-body">
                <div class="intelligence-section">
                    <h5>Why Contact? (Score: ${item.why_now_score})</h5>
                    <ul class="signals-list">
                        ${signalsHtml || '<li style="color:var(--text-muted); list-style:none;">No clear signals</li>'}
                    </ul>
                </div>
                <div class="intelligence-section">
                    <h5>Generated Outreach &mdash; <span class="status-badge status-${d.status}">${d.status}</span></h5>
                    <div class="draft-preview">
                        <pre><strong>Subj:</strong> ${d.subject}\n\n${d.body}</pre>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(div);
    });
}

function openNewCampaignModal() {
    document.getElementById('modal-overlay').style.display = 'flex';
    document.getElementById('new-campaign-modal').style.display = 'block';
}

function closeModals() {
    document.getElementById('modal-overlay').style.display = 'none';
    document.querySelectorAll('.modal').forEach(m => m.style.display = 'none');
    document.getElementById('new-campaign-form').reset();
    currentCampaignId = null;
}
