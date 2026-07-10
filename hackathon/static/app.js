// ═══════════════════════════════════════════════
//  HR AI Agent v2.0 — Dashboard Application Logic
// ═══════════════════════════════════════════════

const API = '';

// ---------- State ----------
let state = {
  currentJD: '',
  currentRole: '',
  jdStyle: 'standard',
  selectedFiles: [],
  screened: [],
  shortlisted: [],
  drafts: {},
  calYear: new Date().getFullYear(),
  calMonth: new Date().getMonth(),
  calEvents: [],
};

// ---------- Navigation ----------
const pagesMeta = {
  pipeline: { title: 'Pipeline', sub: 'End-to-end recruitment stage tracker (restart-safe)' },
  jd: { title: 'JD Generator', sub: 'Create diverse, high-quality job descriptions via AI' },
  status: { title: 'Job Status', sub: 'Monitor posting activity and auto-relaxation' },
  resumes: { title: 'Resume Screening', sub: 'BERT-powered semantic resume ranking' },
  offers: { title: 'Offers & Tracking', sub: 'Send offers, track responses, negotiate, and read replies' },
  emails: { title: 'Email Center', sub: 'Draft and send interview invitations' },
  calendar: { title: 'Interview Calendar', sub: 'Schedule and manage interview events' },
  helpdesk: { title: 'HR Helpdesk', sub: 'Company-grade RAG chatbot for employee queries' },
  onboarding: { title: 'Onboarding', sub: 'Send welcome packages, track documents, schedule intro' },
};

function showPage(pageId, navEl) {
  document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const page = document.getElementById('page-' + pageId);
  if (page) page.style.display = 'block';
  if (navEl) navEl.classList.add('active');
  document.getElementById('topbar-title').textContent = pagesMeta[pageId]?.title || '';
  document.getElementById('topbar-sub').textContent = pagesMeta[pageId]?.sub || '';

  if (pageId === 'status') loadJobStatus();
  if (pageId === 'pipeline') loadPipeline();
  if (pageId === 'offers') loadOffers();
  if (pageId === 'onboarding') { populateOnboardingList(); populateOnboardingChecklistCandidates(); }
  if (pageId === 'emails') syncInterviewTimeMin();
  if (pageId === 'calendar') loadCalendar();
  if (pageId === 'analytics') loadAnalytics();
}

function syncInterviewTimeMin() {
  const el = document.getElementById('interview-time');
  if (!el) return;
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  el.min = now.toISOString().slice(0, 16);
}

// ---------- Utilities ----------
function setLoading(btnId, loading, text) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  if (loading) {
    btn.dataset.origText = btn.innerHTML;
    btn.innerHTML = `<span class="spinner"></span> ${text || 'Loading…'}`;
    btn.disabled = true;
    btn.classList.add('btn-loading');
  } else {
    btn.innerHTML = btn.dataset.origText || text || 'Done';
    btn.disabled = false;
    btn.classList.remove('btn-loading');
  }
}

function showAlert(id, type, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = `alert alert-${type} visible`;
  el.textContent = msg;
  setTimeout(() => el.classList.remove('visible'), 8000);
}

async function apiCall(endpoint, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API + endpoint, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

function avatarLetters(name) {
  return (name || '?').split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
}

function renderMarkdown(text) {
  if (!text) return '';
  let html = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
    .replace(/\n$/gim, '<br />');

  html = html.replace(/^\s*[-•]\s+(.*)$/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

  return html.replace(/\n/g, '<br />');
}


function updateSessionPills() {
  document.getElementById('pill-role').textContent = state.currentRole || '—';
  document.getElementById('pill-resumes').textContent = state.screened.length || state.selectedFiles.length || 0;
  document.getElementById('pill-shortlisted').textContent = state.shortlisted.length || 0;
}

// ═══════════════════════════════
//  FIX 1: JD GENERATOR WIZARD
// ═══════════════════════════════

// Wizard State
let jdWizardStep = 1;
const totalJdSteps = 5;

function navWizard(dir) {
  // Validate step 1 Title before proceeding
  if (jdWizardStep === 1 && dir === 1) {
    if (!document.getElementById('jd-w-title').value.trim()) {
      alert("Please enter a Job Title.");
      return;
    }
  }

  jdWizardStep += dir;
  if (jdWizardStep < 1) jdWizardStep = 1;
  if (jdWizardStep > totalJdSteps) jdWizardStep = totalJdSteps;

  // Update UI
  document.querySelectorAll('.jd-wizard-step').forEach(el => el.style.display = 'none');
  document.getElementById('jd-step-' + jdWizardStep).style.display = 'block';

  document.getElementById('jd-wizard-counter').textContent = `Step ${jdWizardStep} of ${totalJdSteps}`;
  document.getElementById('jd-wizard-progress').style.width = `${(jdWizardStep / totalJdSteps) * 100}%`;

  // Buttons
  document.getElementById('jd-btn-back').style.visibility = jdWizardStep > 1 ? 'visible' : 'hidden';

  if (jdWizardStep === totalJdSteps) {
    document.getElementById('jd-btn-next').style.display = 'none';
    document.getElementById('jd-btn-generate').style.display = 'block';
    updateWizardSummary();
  } else {
    document.getElementById('jd-btn-next').style.display = 'block';
    document.getElementById('jd-btn-generate').style.display = 'none';
  }
}

// Chip Interactions
function selectChipSingle(el, containerId) {
  document.querySelectorAll(`#${containerId} .style-chip`).forEach(c => c.classList.remove('active'));
  el.classList.add('active');
}

function toggleChipMulti(el) {
  el.classList.toggle('active');
}

function getActiveChips(containerId) {
  const chips = document.querySelectorAll(`#${containerId} .style-chip.active`);
  return Array.from(chips).map(c => c.textContent.trim().replace(/^[^a-zA-Z0-9]+/, '').trim());
}

function getActiveChipSingle(containerId) {
  const active = document.querySelector(`#${containerId} .style-chip.active`);
  return active ? active.textContent.trim().replace(/^[^a-zA-Z0-9]+/, '').trim() : '';
}

function updateWizardSummary() {
  const title = document.getElementById('jd-w-title').value.trim();
  const dept = document.getElementById('jd-w-dept').value.trim();
  const exp = getActiveChipSingle('jd-w-exp-chips');
  const type = getActiveChips('jd-w-type-chips').join(', ');
  const mode = getActiveChips('jd-w-work-chips').join(', ');
  const notice = getActiveChips('jd-w-notice-chips').join(', ');
  const style = getActiveChipSingle('jd-w-style-chips');

  const html = `
    <strong>Role:</strong> ${title} ${dept ? '(' + dept + ')' : ''} [${exp}]<br/>
    <strong>Candidate Profile:</strong> ${type || 'Any'}<br/>
    <strong>Work Details:</strong> ${mode || 'Flexible'}, Notice: ${notice || 'Flexible'}<br/>
    <strong>Style:</strong> ${style}
  `;
  document.getElementById('jd-summary-content').innerHTML = html;
}

async function generateWizardJD() {
  const payload = {
    title: document.getElementById('jd-w-title').value.trim(),
    department: document.getElementById('jd-w-dept').value.trim(),
    experience_level: getActiveChipSingle('jd-w-exp-chips'),

    preferred_skills: document.getElementById('jd-w-skills-pref').value.trim(),
    required_vs_nice: document.getElementById('jd-w-skills-req').value.trim(),
    excluded_skills: document.getElementById('jd-w-skills-exclude').value.trim(),

    candidate_types: getActiveChips('jd-w-type-chips'),
    work_modes: getActiveChips('jd-w-work-chips'),
    notice_periods: getActiveChips('jd-w-notice-chips'),

    project_preferences: document.getElementById('jd-w-projects').value.trim(),
    domain_preferences: document.getElementById('jd-w-domain').value.trim(),

    style: getActiveChipSingle('jd-w-style-chips')
  };

  setLoading('jd-btn-generate', true, 'Generating with AI…');
  try {
    const data = await apiCall('/api/generate-jd', 'POST', payload);
    state.currentJD = data.jd;
    state.currentRole = payload.title;

    document.getElementById('jd-output').innerHTML = renderMarkdown(data.jd);
    document.getElementById('jd-edit-area').value = data.jd;
    document.getElementById('jd-preview-card').style.display = 'block';
    document.getElementById('alert-posted').classList.remove('visible');
    updateSessionPills();
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    setLoading('jd-btn-generate', false, '✨ Generate JD');
  }
}

function regenerateJD() {
  generateWizardJD();
}

function editJD() {
  const out = document.getElementById('jd-output');
  const edit = document.getElementById('jd-editable');
  const isEditing = edit.style.display !== 'none';
  out.style.display = isEditing ? 'block' : 'none';
  edit.style.display = isEditing ? 'none' : 'block';
}

function saveJDEdit() {
  const text = document.getElementById('jd-edit-area').value;
  state.currentJD = text;
  document.getElementById('jd-output').innerHTML = renderMarkdown(text);
  editJD();
}

// ═══════════════════════════════
//  FIX 2: TELEGRAM DM
// ═══════════════════════════════

async function testTelegram() {
  const chatId = document.getElementById('telegram-chat-id').value.trim();
  if (!chatId) { showAlert('alert-telegram', 'warning', 'Enter your chat ID first.'); return; }
  setLoading('btn-test-tg', true, 'Testing…');
  try {
    await apiCall('/api/test-telegram', 'POST', { chat_id: chatId });
    showAlert('alert-telegram', 'success', '✅ Bot connected! Check your Telegram.');
  } catch (e) {
    showAlert('alert-telegram', 'error', '❌ ' + e.message);
  } finally {
    setLoading('btn-test-tg', false, '📡 Test');
  }
}

async function approveJD() {
  if (!state.currentJD) return;
  const chatId = document.getElementById('telegram-chat-id').value.trim();
  setLoading('btn-approve-jd', true, 'Posting…');
  try {
    await apiCall('/api/post-jd', 'POST', {
      jd: state.currentJD,
      role: state.currentRole,
      chat_id: chatId
    });
    document.getElementById('alert-posted').classList.add('visible');
    document.getElementById('badge-status').textContent = '1';
    document.getElementById('badge-status').classList.add('visible');
  } catch (e) {
    alert('Post failed: ' + e.message);
  } finally {
    setLoading('btn-approve-jd', false, '✅ Approve & Send via Telegram');
  }
}

// ---------- JOB STATUS ----------
async function loadJobStatus() {
  try {
    const data = await apiCall('/api/job-status');
    const job = data.current_job;
    if (!job) {
      document.getElementById('job-timeline').innerHTML =
        '<div style="color:var(--text-muted);font-size:0.85rem">No active job posted yet. Generate and post a JD first.</div>';
      return;
    }
    document.getElementById('stat-version').textContent = job.version || '—';
    document.getElementById('stat-apps').textContent = job.application_count ?? '—';
    document.getElementById('stat-threshold').textContent = 5;

    const timeline = document.getElementById('job-timeline');
    let html = `
      <div class="timeline-item">
        <div class="tl-dot">1</div>
        <div class="tl-content">
          <div class="tl-title">JD v1 Sent via Telegram DM</div>
          <div class="tl-sub">${new Date(job.posted_at).toLocaleString()} · Role: ${job.role}</div>
        </div>
      </div>`;
    (job.relaxation_history || []).forEach((r, i) => {
      html += `
        <div class="timeline-item">
          <div class="tl-dot" style="background:var(--warning)">${i + 2}</div>
          <div class="tl-content">
            <div class="tl-title">JD Relaxed → v${r.version + 1} Resent</div>
            <div class="tl-sub">${new Date(r.relaxed_at).toLocaleString()} · Apps at relaxation: ${r.app_count_at_relaxation}</div>
          </div>
        </div>`;
    });
    if (!job.relaxation_history?.length) {
      html += `
        <div class="timeline-item">
          <div class="tl-dot" style="background:var(--text-muted)">⏳</div>
          <div class="tl-content">
            <div class="tl-title">Auto-Relaxation Pending</div>
            <div class="tl-sub">Will run if applications &lt; 5 after 48 hours</div>
          </div>
        </div>`;
    }
    timeline.innerHTML = html;
  } catch (e) {
    console.error('Status load error:', e);
  }
}

// ═══════════════════════════════════
//  FIX 3: RESUME UPLOAD & SCREENING
// ═══════════════════════════════════
let uploadedFilesList = [];

function handleFileSelect(e) {
  const newFiles = Array.from(e.target.files).filter(f => f.name.endsWith('.pdf') || f.name.endsWith('.txt'));

  // Allow multiple of the same test file to be uploaded by not deduplicating
  newFiles.forEach(f => {
    uploadedFilesList.push(f);
  });

  // Reset the input so the same files can trigger change again if removed
  e.target.value = '';
  renderFileList();
}

function handleDrop(e) {
  e.preventDefault();
  document.getElementById('upload-zone').classList.remove('dragover');
  const newFiles = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.pdf') || f.name.endsWith('.txt'));

  newFiles.forEach(f => {
    uploadedFilesList.push(f);
  });

  renderFileList();
}

function renderFileList() {
  const list = document.getElementById('file-list');
  const btn = document.getElementById('btn-upload');
  if (!uploadedFilesList.length) { list.innerHTML = ''; btn.disabled = true; return; }
  btn.disabled = false;
  list.innerHTML = uploadedFilesList.map((f, i) => `
    <div class="file-item" id="fitem-${i}">
      📄 ${f.name}
      <span style="margin-left:auto;color:var(--text-muted)">${(f.size / 1024).toFixed(1)} KB</span>
      <span class="file-status" style="margin-left:8px;font-size:0.72rem;color:var(--text-dim)">⏳ Pending</span>
    </div>`).join('');
}

async function uploadResumes() {
  if (!uploadedFilesList.length) return;
  setLoading('btn-upload', true, 'Uploading…');
  try {
    const formData = new FormData();
    uploadedFilesList.forEach(f => formData.append('files', f));
    const res = await fetch(API + '/api/upload-resumes', { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    document.getElementById('badge-resumes').textContent = data.uploaded_count;
    document.getElementById('badge-resumes').classList.add('visible');
    document.getElementById('screening-card').style.display = 'block';

    // Mark all as uploaded
    uploadedFilesList.forEach((_, i) => {
      const fitem = document.getElementById('fitem-' + i);
      if (fitem) {
        const status = fitem.querySelector('.file-status');
        if (status) { status.textContent = '✅ Uploaded'; status.style.color = 'var(--success)'; }
      }
    });
    showAlert('alert-screen', 'success', `✅ ${data.uploaded_count} resumes uploaded. Click "Screen All Resumes" to analyze.`);
  } catch (e) {
    showAlert('alert-screen', 'error', 'Upload failed: ' + e.message);
  } finally {
    setLoading('btn-upload', false, '⬆️ Upload Resumes');
  }
}

async function screenResumes() {
  setLoading('btn-screen', true, 'Deep Scanning Resumes with AI…');
  document.getElementById('candidates-list').innerHTML = '';

  // Show progress bar
  const progressDiv = document.getElementById('screening-progress');
  const progressBar = document.getElementById('progress-bar');
  const progressLabel = document.getElementById('progress-label');
  const progressCount = document.getElementById('progress-count');
  progressDiv.style.display = 'block';
  const total = uploadedFilesList.length || 1;
  progressBar.style.width = '5%';
  progressLabel.textContent = 'Reasoning over resumes with LLM...';
  progressCount.textContent = `0 / ${total}`;

  // Simulate progress while waiting
  let pct = 5;
  const interval = setInterval(() => {
    pct = Math.min(pct + Math.random() * 10, 95);
    progressBar.style.width = pct + '%';
    const done = Math.floor((pct / 100) * total);
    progressCount.textContent = `${done} / ${total}`;
    progressLabel.textContent = `Screening resume ${done + 1} of ${total}…`;
  }, 2000);

  try {
    const data = await apiCall('/api/screen-resumes', 'POST');
    clearInterval(interval);
    progressBar.style.width = '100%';
    progressCount.textContent = `${data.total} / ${data.total}`;
    progressLabel.textContent = 'Screening complete!';

    state.screened = data.candidates;
    renderCandidates(data.candidates);
    document.getElementById('shortlist-actions').style.display = 'flex';
    showAlert('alert-screen', 'info', `🧬 Screened ${data.total} resumes with comprehensive LLM evaluation.`);
    updateSessionPills();
  } catch (e) {
    clearInterval(interval);
    progressDiv.style.display = 'none';
    showAlert('alert-screen', 'error', 'Screening failed: ' + e.message);
  } finally {
    setLoading('btn-screen', false, '🧠 Screen All Resumes');
  }
}

function getRecommendation(score) {
  if (score >= 60) return { text: 'Shortlist', cls: 'rec-shortlist' };
  if (score >= 40) return { text: 'Maybe', cls: 'rec-maybe' };
  return { text: 'Reject', cls: 'rec-reject' };
}

function renderCandidates(candidates) {
  const list = document.getElementById('candidates-list');

  // Preserve existing selections
  candidates.forEach(c => {
    if (c.shortlisted) selectedIds.add(c.candidate_id);
  });

  list.innerHTML = candidates.map((c, i) => {
    const rec = getRecommendation(c.final_score);
    const missingSkills = (c.skills || []).length > 0 ? '' : '<span class="tag" style="background:rgba(239,68,68,0.1);color:var(--danger);border-color:rgba(239,68,68,0.2)">No skills found</span>';
    const isSelected = selectedIds.has(c.candidate_id);

    return `
    <div class="candidate-card ${isSelected ? 'selected' : ''}" 
         id="ccard-${i}" onclick="toggleCandidate(${i}, '${c.candidate_id}')" style="display:flex; flex-direction:column; gap:12px; align-items:stretch;">
      <div style="display:flex; align-items:center; gap:16px;">
        <div class="candidate-avatar">${avatarLetters(c.name)}</div>
        <div class="candidate-info">
          <div class="candidate-name">
            ${i < 3 ? '⭐ ' : ''}${c.name}
            <span class="rec-badge ${rec.cls}">${rec.text}</span>
          </div>
          <div class="candidate-email">📧 ${c.email || 'No email'} &nbsp;|&nbsp; 📅 ${c.experience_years}y exp &nbsp;|&nbsp; 🎓 ${c.education || 'N/A'}</div>
          <div class="candidate-tags">
            ${(c.skills || []).slice(0, 8).map(s => `<span class="tag">${s}</span>`).join('')}
            ${missingSkills}
          </div>
          <div style="margin-top: 8px;">
            <button class="btn btn-outline btn-sm" onclick="event.stopPropagation(); loadInterviewQuestions('${c.candidate_id}')">💭 Generate Questions</button>
          </div>
        </div>
        <div class="score-bars" style="flex-shrink:0;">
          <div class="score-block" style="text-align:right;">
            <div class="score-value" style="color:var(--warning);font-size:1.6rem">${c.final_score}/100</div>
            <div class="score-label">Holistic Score</div>
          </div>
          <div class="rank-badge" style="margin-left:12px;">#${i + 1}</div>
        </div>
      </div>
      <div style="padding-top:10px; border-top:1px dashed var(--border); font-size:0.82rem; color:var(--text-dim); line-height:1.5;">
        <strong style="color:var(--text);">🧠 LLM Evaluation:</strong> ${c.evaluation_reasoning || 'No evaluation provided.'}
      </div>
    </div>`;
  }).join('');

  document.getElementById('selected-count').textContent = selectedIds.size;
}

// ---------- INTERVIEW QUESTIONS ----------
let currentInterviewQuestions = [];
let currentCandidateName = "Candidate";

async function loadInterviewQuestions(candidateId) {
  // Must be shortlisted first because the backend expects them to be in the shortlst session
  if (!state.shortlisted || !state.shortlisted.some(c => c.candidate_id === candidateId)) {
    alert("Please shortlist this candidate first before generating questions.");
    return;
  }

  const candidate = state.shortlisted.find(c => c.candidate_id === candidateId);
  currentCandidateName = candidate ? candidate.name : "Candidate";

  const modal = document.getElementById('interview-modal');
  const content = document.getElementById('interview-questions-content');
  const exportBtn = document.getElementById('btn-export-pdf');

  modal.style.display = 'flex';
  exportBtn.style.display = 'none';
  content.innerHTML = '<div style="text-align:center; padding: 20px;">🤖 Analyzing Resume & JD... Generating tailored questions...</div>';

  try {
    const data = await apiCall('/api/interview-questions', 'POST', { candidate_id: candidateId });
    currentInterviewQuestions = data.questions;

    let html = `<div style="margin-bottom: 16px; font-weight: 600;">Custom Interview Kit for ${currentCandidateName}</div>`;

    data.questions.forEach((q, idx) => {
      html += `
        <div style="margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--border);">
          <div style="font-weight: 600; color: var(--text); margin-bottom: 8px;">Q${idx + 1}: ${q.question}</div>
          <div style="font-size: 0.85rem; color: var(--text-dim); margin-bottom: 6px;"><em>Rationale:</em> ${q.rationale}</div>
          <div style="font-size: 0.85rem; color: var(--accent2);"><em>Look for:</em> ${q.expected_answer}</div>
        </div>
      `;
    });

    content.innerHTML = html;
    exportBtn.style.display = 'block';
  } catch (e) {
    content.innerHTML = `<div style="color:var(--danger)">Failed to generate questions: ${e.message}</div>`;
  }
}

function exportInterviewPDF() {
  if (!currentInterviewQuestions || currentInterviewQuestions.length === 0) return;

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();

  let y = 20;

  doc.setFontSize(20);
  doc.setTextColor(40, 40, 80);
  doc.text(`Interview Kit: ${currentCandidateName}`, 14, y);
  y += 10;

  doc.setFontSize(10);
  doc.setTextColor(100, 100, 100);
  doc.text(`Generated by HR AI Agent on ${new Date().toLocaleDateString()}`, 14, y);
  y += 15;

  currentInterviewQuestions.forEach((q, idx) => {
    // Page break if needed
    if (y > 270) {
      doc.addPage();
      y = 20;
    }

    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.setTextColor(30, 30, 30);
    const splitQ = doc.splitTextToSize(`Q${idx + 1}: ${q.question}`, 180);
    doc.text(splitQ, 14, y);
    y += (splitQ.length * 6) + 3;

    doc.setFont("helvetica", "italic");
    doc.setFontSize(10);
    doc.setTextColor(80, 80, 80);
    const splitRat = doc.splitTextToSize(`Rationale: ${q.rationale}`, 180);
    doc.text(splitRat, 14, y);
    y += (splitRat.length * 5) + 3;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(40, 100, 40);
    const splitAns = doc.splitTextToSize(`Look for: ${q.expected_answer}`, 180);
    doc.text(splitAns, 14, y);
    y += (splitAns.length * 5) + 12;
  });

  doc.save(`Interview_Kit_${currentCandidateName.replace(/\s+/g, '_')}.pdf`);
}

function closeInterviewModal() {
  document.getElementById('interview-modal').style.display = 'none';
}

let selectedIds = new Set();

function toggleCandidate(index, id) {
  const card = document.getElementById('ccard-' + index);
  if (selectedIds.has(id)) {
    selectedIds.delete(id);
    card.classList.remove('selected');
  } else {
    selectedIds.add(id);
    card.classList.add('selected');
  }
  document.getElementById('selected-count').textContent = selectedIds.size;
}

async function sendRejections() {
  if (confirm("Send personalized rejection emails to all candidates NOT currently selected?")) {
    setLoading('btn-screen', true, 'Drafting and sending rejections...');
    try {
      const data = await apiCall('/api/send-rejections', 'POST');
      alert(`✅ ${data.message}`);
    } catch (e) {
      alert('Error sending rejections: ' + e.message);
    } finally {
      setLoading('btn-screen', false, '🧬 Screen All Resumes');
    }
  }
}

async function confirmShortlist() {
  if (!selectedIds.size) { alert('Select at least one candidate.'); return; }
  try {
    const data = await apiCall('/api/shortlist', 'POST', {
      candidate_ids: [...selectedIds]
    });
    state.shortlisted = data.candidates;
    document.getElementById('badge-emails').textContent = data.shortlisted_count;
    document.getElementById('badge-emails').classList.add('visible');
    updateSessionPills();
    alert(`✅ ${data.shortlisted_count} candidates shortlisted! Go to Email Center to draft invitations.`);
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

// ---------- EMAIL CENTER ----------
async function autoScheduleInterviews() {
  if (!state.shortlisted || state.shortlisted.length === 0) {
    alert("No shortlisted candidates available to auto-schedule.");
    return;
  }

  const candidateIds = state.shortlisted.map(c => c.candidate_id);

  if (!confirm(`🤖 This will automatically find the best available slots for ${candidateIds.length} candidates and send them calendar invites. Proceed?`)) {
    return;
  }

  const btnScreener = document.getElementById('btn-auto-schedule-screener');
  const btnCalendar = document.getElementById('btn-auto-schedule-calendar');

  if (btnScreener) setLoading('btn-auto-schedule-screener', true, 'Scheduling...');
  if (btnCalendar) setLoading('btn-auto-schedule-calendar', true, 'Scheduling...');

  try {
    const data = await apiCall('/api/calendar/auto-schedule', 'POST', {
      candidate_ids: candidateIds
    });

    let resultMsg = `${data.message}\n\n`;
    data.details.forEach(d => {
      const icon = d.status === 'created' ? '✅' : '❌';
      resultMsg += `${icon} ${d.candidate_name}: ${d.time || d.error}\n`;
    });

    alert(resultMsg);

    // Refresh calendar if we're on the calendar page
    if (document.getElementById('page-calendar').style.display !== 'none') {
      loadCalendarEvents();
    }
  } catch (e) {
    alert(`Failed to auto-schedule: ${e.message}`);
  } finally {
    if (btnScreener) setLoading('btn-auto-schedule-screener', false, '🤖 Auto-Schedule All');
    if (btnCalendar) setLoading('btn-auto-schedule-calendar', false, '🤖 Auto-Schedule Shortlisted');
  }
}

async function draftEmails() {
  const timeEl = document.getElementById('interview-time');
  const linkEl = document.getElementById('meeting-link');
  if (!timeEl.value) { alert('Please set interview date & time.'); return; }

  setLoading('btn-draft', true, 'Drafting with AI…');
  try {
    const data = await apiCall('/api/draft-emails', 'POST', {
      interview_time: new Date(timeEl.value).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' }),
      interview_link: linkEl.value
    });
    state.drafts = data.drafts;
    renderEmailDrafts(data.drafts);
    document.getElementById('drafts-card').style.display = 'block';
  } catch (e) {
    showAlert('alert-send', 'error', 'Draft failed: ' + e.message);
  } finally {
    setLoading('btn-draft', false, '🤖 Draft Emails with AI');
  }
}

function renderEmailDrafts(drafts) {
  const container = document.getElementById('email-drafts-list');
  container.innerHTML = Object.entries(drafts).map(([email, d]) => `
    <div class="email-draft-card">
      <div class="email-draft-header">
        <div>
          <div style="font-weight:600;font-size:0.9rem">${d.name}</div>
          <div style="font-size:0.77rem;color:var(--text-muted)">To: ${email}</div>
          <div style="font-size:0.77rem;color:var(--text-muted)">Subject: ${d.subject}</div>
        </div>
        <button class="btn btn-outline btn-sm" onclick="toggleDraftBody('draft-${email.replace(/[@.]/g, '_')}')">
          👁 Preview
        </button>
      </div>
      <div class="email-draft-body" id="draft-${email.replace(/[@.]/g, '_')}" style="display:none">
${d.body}
      </div>
    </div>`).join('');
}

function toggleDraftBody(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

async function sendEmails() {
  const timeEl = document.getElementById('interview-time');
  const linkEl = document.getElementById('meeting-link');

  if (!confirm(`Are you sure you want to send emails to ALL ${Object.keys(state.drafts).length} shortlisted candidates?`)) {
    return;
  }

  setLoading('btn-send', true, 'Sending to ALL…');
  try {
    const res = await fetch(`${API}/api/send-emails?interview_datetime=${encodeURIComponent(timeEl.value)}&meeting_link=${encodeURIComponent(linkEl.value)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirmed: true })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    const sent = Object.values(data.results).filter(r => r.email_sent).length;
    const calOk = Object.values(data.results).filter(r => r.calendar?.status === 'created').length;
    showAlert('alert-send', 'success',
      `✅ Successfully sent emails to ALL ${sent} candidates! ${calOk} calendar events created.`);
  } catch (e) {
    showAlert('alert-send', 'error', 'Send failed: ' + e.message);
  } finally {
    setLoading('btn-send', false, '🚀 Confirm & Send All');
  }
}

// ═══════════════════════════════
//  FIX 4: MOCK CALENDAR
// ═══════════════════════════════

const TYPE_COLORS = {
  interview: '#6366f1',
  followup: '#f59e0b',
  offer: '#10b981',
};

async function loadCalendar() {
  try {
    const data = await apiCall('/api/calendar/events');
    state.calEvents = data.events || [];
  } catch { state.calEvents = []; }
  renderCalendar();
  renderEventList();
}

function calNav(dir) {
  state.calMonth += dir;
  if (state.calMonth > 11) { state.calMonth = 0; state.calYear++; }
  if (state.calMonth < 0) { state.calMonth = 11; state.calYear--; }
  renderCalendar();
}

function renderCalendar() {
  const grid = document.getElementById('cal-grid');
  const label = document.getElementById('cal-month-label');
  const y = state.calYear, m = state.calMonth;
  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  label.textContent = `${monthNames[m]} ${y}`;

  const firstDay = new Date(y, m, 1).getDay();
  const daysInMonth = new Date(y, m + 1, 0).getDate();
  const today = new Date();
  const isThisMonth = today.getFullYear() === y && today.getMonth() === m;

  let html = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => `<div class="cal-header-cell">${d}</div>`).join('');

  // Empty cells before first
  for (let i = 0; i < firstDay; i++) html += '<div class="cal-day empty"></div>';

  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    const isToday = isThisMonth && today.getDate() === d;
    const dayEvents = state.calEvents.filter(ev => ev.datetime_str && ev.datetime_str.startsWith(dateStr));
    const evDots = dayEvents.map(ev =>
      `<span class="cal-event-dot" style="background:${TYPE_COLORS[ev.event_type] || '#6366f1'}" title="${ev.title}">${ev.title.slice(0, 14)}</span>`
    ).join('');

    html += `<div class="cal-day ${isToday ? 'today' : ''}" onclick="openEventModal('${dateStr}')">
      <div class="cal-day-num">${d}</div>
      ${evDots}
    </div>`;
  }
  grid.innerHTML = html;
}

function renderEventList() {
  const container = document.getElementById('cal-event-list');
  if (!state.calEvents.length) {
    container.innerHTML = '<div style="color:var(--text-muted);font-size:0.85rem">No events scheduled yet.</div>';
    return;
  }
  container.innerHTML = state.calEvents.map(ev => `
    <div class="cal-ev-row">
      <div class="cal-ev-color" style="background:${TYPE_COLORS[ev.event_type] || '#6366f1'}"></div>
      <div class="cal-ev-info">
        <div style="font-weight:500">${ev.title}</div>
        ${ev.candidate_name ? `<div style="font-size:0.75rem;color:var(--text-muted)">👤 ${ev.candidate_name}</div>` : ''}
      </div>
      <div class="cal-ev-time">${new Date(ev.datetime_str).toLocaleString()}</div>
      <button class="btn btn-danger btn-sm" onclick="deleteCalEvent('${ev.id}')" style="padding:4px 8px;font-size:0.72rem">✕</button>
    </div>`).join('');
}

function openEventModal(dateStr) {
  document.getElementById('event-modal').style.display = 'flex';
  const dtInput = document.getElementById('ev-datetime');
  if (dateStr && dateStr !== 'undefined') {
    dtInput.value = dateStr + 'T10:00';
  }
}

function closeEventModal() {
  document.getElementById('event-modal').style.display = 'none';
}

async function submitEvent() {
  const title = document.getElementById('ev-title').value.trim();
  const dt = document.getElementById('ev-datetime').value;
  const type = document.getElementById('ev-type').value;
  const candidate = document.getElementById('ev-candidate').value.trim();
  const notes = document.getElementById('ev-notes').value.trim();
  if (!title || !dt) { alert('Title and date/time are required.'); return; }

  try {
    await apiCall('/api/calendar/events', 'POST', {
      title, datetime_str: dt, event_type: type,
      candidate_name: candidate, notes
    });
    closeEventModal();
    document.getElementById('ev-title').value = '';
    document.getElementById('ev-candidate').value = '';
    document.getElementById('ev-notes').value = '';
    loadCalendar();
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

async function deleteCalEvent(id) {
  try {
    await fetch(`${API}/api/calendar/events/${id}`, { method: 'DELETE' });
    loadCalendar();
  } catch { }
}

// ---------- HELPDESK ----------
async function sendHelpdeskQuery() {
  const input = document.getElementById('helpdesk-input');
  const question = input.value.trim();
  if (!question) return;

  const chatWindow = document.getElementById('chat-window');
  chatWindow.innerHTML += `<div class="chat-bubble user">${question}</div>`;
  input.value = '';
  chatWindow.scrollTop = chatWindow.scrollHeight;

  const typingId = 'typing-' + Date.now();
  chatWindow.innerHTML += `<div class="chat-bubble bot" id="${typingId}"><span class="spinner" style="border-color:rgba(99,102,241,0.3);border-top-color:var(--accent)"></span></div>`;
  chatWindow.scrollTop = chatWindow.scrollHeight;

  try {
    const data = await apiCall('/api/helpdesk', 'POST', { question });
    document.getElementById(typingId).remove();
    chatWindow.innerHTML += `<div class="chat-bubble bot">${data.answer}</div>`;
  } catch (e) {
    document.getElementById(typingId).remove();
    chatWindow.innerHTML += `<div class="chat-bubble bot">⚠️ Sorry, I encountered an error. Please try again.</div>`;
  }
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ---------- ONBOARDING ----------
function populateOnboardingList() {
  const container = document.getElementById('onboarding-candidate-list');
  if (!state.shortlisted.length) {
    container.innerHTML = '<div style="color:var(--text-muted);font-size:0.85rem;margin-bottom:12px">No shortlisted candidates yet. Complete the screening flow first, or enter email manually below.</div>';
    return;
  }
  container.innerHTML = `
    <div class="card-title" style="margin-bottom:10px">Shortlisted Candidates</div>
    ${state.shortlisted.map(c => `
      <div class="candidate-card" onclick="prefillOnboard('${c.email}', '${state.currentRole}')">
        <div class="candidate-avatar">${avatarLetters(c.name)}</div>
        <div class="candidate-info">
          <div class="candidate-name">${c.name}</div>
          <div class="candidate-email">${c.email}</div>
        </div>
        <button class="btn btn-success btn-sm">Select & Onboard</button>
      </div>`).join('')}
    <div class="divider"></div>`;
}

function prefillOnboard(email, role) {
  document.getElementById('onboard-email').value = email;
  document.getElementById('onboard-role').value = role;
  document.getElementById('onboard-salary').value = "$120,000";
}

async function sendOnboarding() {
  const email = document.getElementById('onboard-email').value.trim();
  const role = document.getElementById('onboard-role').value.trim();
  const salary = document.getElementById('onboard-salary').value.trim() || "$120,000";
  if (!email || !role) { alert('Please enter both email and role.'); return; }

  setLoading('btn-onboard', true, 'Sending…');
  try {
    const data = await apiCall('/api/onboard', 'POST', {
      candidate_email: email,
      role: role,
      salary: salary
    });
    const alertType = data.status === 'sent' ? 'success' : data.status === 'not_configured' ? 'warning' : 'error';
    showAlert('alert-onboard', alertType, data.message || data.status);
  } catch (e) {
    showAlert('alert-onboard', 'error', 'Error: ' + e.message);
  } finally {
    setLoading('btn-onboard', false, '🎁 Send Welcome Package');
  }
}

// ---------- ANALYTICS DASHBOARD ----------
let funnelChart, sourceChart;

async function loadAnalytics() {
  try {
    const data = await apiCall('/api/analytics');
    const fData = data.funnel;
    const sData = data.sources;

    // Funnel Chart
    const ctxF = document.getElementById('funnelChart').getContext('2d');
    if (funnelChart) funnelChart.destroy();
    funnelChart = new Chart(ctxF, {
      type: 'bar',
      data: {
        labels: Object.keys(fData),
        datasets: [{
          label: 'Candidates',
          data: Object.values(fData),
          backgroundColor: ['#6366f1', '#8b5cf6', '#10b981', '#f59e0b']
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } }
      }
    });

    // Source Chart
    const ctxS = document.getElementById('sourceChart').getContext('2d');
    if (sourceChart) sourceChart.destroy();
    sourceChart = new Chart(ctxS, {
      type: 'doughnut',
      data: {
        labels: Object.keys(sData),
        datasets: [{
          data: Object.values(sData),
          backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444']
        }]
      },
      options: {
        responsive: true
      }
    });

  } catch (e) {
    console.error("Failed to load analytics", e);
  }
}
// ---------- DOCUMENT GENERATOR ----------
let currentDocumentHtml = "";
let currentDocumentName = "Document";

async function generateOfferLetter() {
  const name = document.getElementById('doc-ol-name').value;
  const role = document.getElementById('doc-ol-role').value;
  const salary = document.getElementById('doc-ol-salary').value;
  const equity = document.getElementById('doc-ol-equity').value;
  const startDate = document.getElementById('doc-ol-startdate').value;

  if (!name || !role || !salary) {
    alert("Please fill in Candidate Name, Role, and Salary.");
    return;
  }

  setLoading('btn-gen-offer', true, 'Generating FAANG-Grade Offer...');

  try {
    const data = await apiCall('/api/documents/offer-letter', 'POST', {
      candidate_name: name,
      role: role,
      salary: salary,
      equity: equity,
      start_date: startDate
    });

    currentDocumentHtml = data.html;
    currentDocumentName = `Offer_Letter_${name.replace(/\s+/g, '_')}`;

    document.getElementById('doc-preview-content').innerHTML = currentDocumentHtml;
    document.getElementById('doc-preview-card').style.display = 'block';
  } catch (e) {
    alert(`Failed to generate offer letter: ${e.message}`);
  } finally {
    setLoading('btn-gen-offer', false, '🪄 Generate Offer Letter');
  }
}

async function generateHandbook() {
  const company = document.getElementById('doc-hb-company').value;
  const values = document.getElementById('doc-hb-values').value;
  const perks = document.getElementById('doc-hb-perks').value;

  if (!company) {
    alert("Please enter a Company Name.");
    return;
  }

  setLoading('btn-gen-handbook', true, 'Drafting Handbook...');

  try {
    const data = await apiCall('/api/documents/handbook', 'POST', {
      company_name: company,
      core_values: values || "Innovation, Teamwork, Impact",
      perks: perks || "Standard health coverage, PTO"
    });

    currentDocumentHtml = data.html;
    currentDocumentName = `Company_Handbook_${company.replace(/\s+/g, '_')}`;

    document.getElementById('doc-preview-content').innerHTML = currentDocumentHtml;
    document.getElementById('doc-preview-card').style.display = 'block';
  } catch (e) {
    alert(`Failed to generate handbook: ${e.message}`);
  } finally {
    setLoading('btn-gen-handbook', false, '🪄 Generate Handbook');
  }
}

function exportDocumentPDF() {
  if (!currentDocumentHtml) return;

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({
    unit: 'pt',
    format: 'a4',
    orientation: 'portrait'
  });

  // Since we have rich HTML generated, we use the jsPDF HTML capability
  doc.html(document.getElementById('doc-preview-content'), {
    callback: function (pdf) {
      pdf.save(`${currentDocumentName}.pdf`);
    },
    x: 40,
    y: 40,
    width: 500, // max width on A4 is ~595pt
    windowWidth: 800 // renders html at 800px and scales it down to 500pt
  });
}

// ---------- HR HELPDESK ----------
function quickReplyHelpdesk(query) {
  document.getElementById('helpdesk-input').value = query;
  sendHelpdeskQuery();
}

async function sendHelpdeskQuery() {
  const inputEl = document.getElementById('helpdesk-input');
  const query = inputEl.value.trim();
  if (!query) return;

  const chatWindow = document.getElementById('chat-window');

  // Render User Message
  const userDiv = document.createElement('div');
  userDiv.className = 'chat-bubble user';
  userDiv.textContent = query;
  chatWindow.appendChild(userDiv);

  inputEl.value = '';
  chatWindow.scrollTop = chatWindow.scrollHeight;

  // Render Bot Loading
  const botDiv = document.createElement('div');
  botDiv.className = 'chat-bubble bot';
  botDiv.innerHTML = '<span style="color:var(--text-muted)">Thinking...</span>';
  chatWindow.appendChild(botDiv);
  chatWindow.scrollTop = chatWindow.scrollHeight;

  try {
    const data = await apiCall('/api/helpdesk', 'POST', { question: query });
    botDiv.innerHTML = data.answer.replace(/\n/g, '<br/>');
  } catch (e) {
    botDiv.innerHTML = `<span style="color:var(--danger)">Error: ${e.message}</span>`;
  }

  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ═══════════════════════════════
//  PHASE 2: PIPELINE STATE MACHINE
// ═══════════════════════════════

async function loadPipeline() {
  try {
    const d = await apiCall('/api/pipeline');
    renderStepper(d);
    const hist = d.history || [];
    document.getElementById('pipeline-history').innerHTML = hist.length
      ? hist.map(h => `<div style="padding:5px 0">✅ <strong>${h.label}</strong>
          <span style="color:var(--text-muted)">— ${new Date(h.at).toLocaleString()}</span></div>`).join('')
      : 'No transitions yet — start by generating a JD.';
  } catch (e) { /* server may be starting */ }
}

function renderStepper(d) {
  const el = document.getElementById('pipeline-stepper');
  if (!el) return;
  const cur = d.current_index || 0;
  el.innerHTML = (d.stages || []).map((s, i) => {
    const st = i < cur ? 'done' : (i === cur ? 'current' : 'todo');
    return `<div class="pstep ${st}"><div class="pstep-dot">${i < cur ? '✓' : (i + 1)}</div>
      <div class="pstep-label">${s.label}</div></div>`;
  }).join('<div class="pstep-line"></div>');
}

async function resetPipeline() {
  if (!confirm('Reset the pipeline to IDLE and clear the current role/session? This cannot be undone.')) return;
  try {
    await apiCall('/api/pipeline/reset', 'POST');
    state.shortlisted = []; state.screened = []; state.currentRole = ''; state.drafts = {};
    updateSessionPills();
    loadPipeline();
    alert('Pipeline reset to IDLE.');
  } catch (e) { alert('Error: ' + e.message); }
}

function downloadCandidatesCSV() {
  window.open(API + '/api/export/candidates.csv', '_blank');
}

async function sendReminders() {
  try {
    const d = await apiCall('/api/reminders/send-today', 'POST');
    alert(d.result || d.message || 'Reminders processed.');
  } catch (e) { alert('Error: ' + e.message); }
}

// ═══════════════════════════════
//  PHASE 2: OFFERS & TRACKING
// ═══════════════════════════════

function populateOfferCandidates() {
  const sel = document.getElementById('offer-candidate');
  if (!sel) return;
  if (!state.shortlisted.length) {
    sel.innerHTML = '<option value="">— shortlist candidates first —</option>';
    return;
  }
  sel.innerHTML = state.shortlisted.map(c =>
    `<option value="${c.candidate_id}" data-name="${c.name}" data-email="${c.email || ''}">${c.name} (${c.email || 'no email'})</option>`
  ).join('');
}

async function loadOffers() {
  populateOfferCandidates();
  try {
    const d = await apiCall('/api/offers');
    renderOffersTable(d.offers || {});
  } catch (e) { /* ignore */ }
}

function renderOffersTable(offers) {
  const el = document.getElementById('offers-table');
  const keys = Object.keys(offers);
  if (!keys.length) { el.innerHTML = 'No offers sent yet.'; return; }
  el.innerHTML = `<div style="overflow-x:auto"><table class="p2-table">
    <thead><tr><th>Candidate</th><th>Role</th><th>Salary</th><th>Status</th><th>Response</th><th>Actions</th></tr></thead>
    <tbody>` + keys.map(cid => {
    const o = offers[cid]; const resp = o.response || 'pending';
    const badge = resp === 'accepted' ? '#10b981' : resp === 'declined' ? '#ef4444' : '#f59e0b';
    return `<tr>
      <td>${o.name || ''}</td><td>${o.role || ''}</td><td>${o.salary || ''}</td>
      <td>${o.status || ''}</td>
      <td><span style="color:${badge};font-weight:600;text-transform:capitalize">${resp}</span></td>
      <td style="white-space:nowrap">
        <button class="btn btn-outline btn-sm" title="Mark accepted" onclick="setOfferResponse('${cid}','accepted')">✅</button>
        <button class="btn btn-outline btn-sm" title="Mark declined" onclick="setOfferResponse('${cid}','declined')">❌</button>
        <button class="btn btn-outline btn-sm" title="Negotiation help" onclick="negotiateOffer('${cid}')">🤝</button>
      </td></tr>`;
  }).join('') + `</tbody></table></div>`;
}

async function sendOffer() {
  const sel = document.getElementById('offer-candidate');
  const cid = sel.value;
  if (!cid) { alert('Select a candidate (shortlist someone first).'); return; }
  const opt = sel.selectedOptions[0];
  setLoading('btn-send-offer', true, 'Sending…');
  try {
    const d = await apiCall('/api/offer/send', 'POST', {
      candidate_id: cid,
      candidate_email: opt.dataset.email,
      role: state.currentRole || '',
      salary: document.getElementById('offer-salary').value.trim() || '$120,000',
      equity: document.getElementById('offer-equity').value.trim() || 'Standard equity package',
      start_date: document.getElementById('offer-startdate').value || '',
    });
    showAlert('alert-offer', d.email_sent ? 'success' : 'warning',
      d.email_sent ? `Offer sent to ${opt.dataset.name}.`
                   : `Offer recorded, but email not sent (${d.email_error || 'no email / Gmail not configured'}).`);
    loadOffers(); loadPipeline();
  } catch (e) {
    showAlert('alert-offer', 'error', 'Error: ' + e.message);
  } finally {
    setLoading('btn-send-offer', false, '📤 Generate & Send Offer');
  }
}

async function setOfferResponse(cid, resp) {
  try {
    const d = await apiCall('/api/offer/response', 'POST', { candidate_id: cid, response: resp });
    loadOffers();
    alert(d.next_step || ('Marked ' + resp));
  } catch (e) { alert('Error: ' + e.message); }
}

async function negotiateOffer(cid) {
  const el = document.getElementById('negotiation-content');
  el.innerHTML = '<div style="padding:20px;text-align:center"><span class="spinner"></span> Generating guidance…</div>';
  document.getElementById('negotiation-modal').style.display = 'flex';
  try {
    const d = await apiCall('/api/offer/negotiate', 'POST', { candidate_id: cid });
    const g = d.guidance || {};
    el.innerHTML = `
      <div style="margin-bottom:14px"><strong>Likely reasons</strong>
        <ul>${(g.likely_reasons || []).map(r => `<li>${r}</li>`).join('')}</ul></div>
      <div style="margin-bottom:14px"><strong>Recommended counter</strong><br>${g.recommended_counter || '—'}</div>
      <div style="margin-bottom:14px"><strong>Non-salary levers</strong>
        <ul>${(g.non_salary_levers || []).map(r => `<li>${r}</li>`).join('')}</ul></div>
      <div style="margin-bottom:14px"><strong>Walk-away advice</strong><br>${g.walk_away_advice || '—'}</div>
      <div><strong>Draft response email</strong>
        <pre style="white-space:pre-wrap;background:var(--surface2);padding:12px;border-radius:8px;margin-top:6px">${g.response_email || '—'}</pre></div>`;
  } catch (e) {
    el.innerHTML = '<div style="color:#ef4444">Error: ' + e.message + '</div>';
  }
}

function closeNegotiation() {
  document.getElementById('negotiation-modal').style.display = 'none';
}

async function checkInbox() {
  setLoading('btn-check-inbox', true, 'Checking…');
  const el = document.getElementById('inbox-results');
  try {
    const d = await apiCall('/api/inbox/check', 'POST', { days_back: 7 });
    if (d.status !== 'ok') {
      el.innerHTML = `<div style="color:var(--warning)">${d.message || d.status}</div>`;
      return;
    }
    const reps = d.replies || [];
    el.innerHTML = reps.length ? reps.map(r => {
      const c = r.intent === 'confirmed' ? '#10b981' : r.intent === 'declined' ? '#ef4444'
        : r.intent === 'reschedule' ? '#f59e0b' : '#6366f1';
      return `<div style="padding:10px 0;border-bottom:1px solid var(--border)">
        <strong>${r.name || r.email}</strong>
        <span style="color:${c};font-weight:600;text-transform:capitalize">[${r.intent}]</span><br>
        <span style="color:var(--text-dim)">${r.summary || ''}</span><br>
        <small style="color:var(--text-muted)">→ ${r.suggested_action || ''}</small></div>`;
    }).join('') : `Scanned ${d.scanned_candidates} candidate(s) — no replies found in the last 7 days.`;
    loadOffers();
  } catch (e) {
    el.innerHTML = '<div style="color:#ef4444">Error: ' + e.message + '</div>';
  } finally {
    setLoading('btn-check-inbox', false, '🔍 Check Replies');
  }
}

// ═══════════════════════════════
//  PHASE 2: ONBOARDING CHECKLIST + INTRO MEETING
// ═══════════════════════════════

function populateOnboardingChecklistCandidates() {
  const sel = document.getElementById('onboard-checklist-candidate');
  if (!sel) return;
  if (!state.shortlisted.length) {
    sel.innerHTML = '<option value="">— shortlist candidates first —</option>';
    return;
  }
  sel.innerHTML = '<option value="">— select candidate —</option>' +
    state.shortlisted.map(c => `<option value="${c.candidate_id}">${c.name}</option>`).join('');
}

async function loadOnboardingChecklist() {
  const cid = document.getElementById('onboard-checklist-candidate').value;
  const el = document.getElementById('onboarding-checklist');
  document.getElementById('intro-meeting-status').textContent = '';
  if (!cid) { el.innerHTML = 'Select a shortlisted candidate to view their onboarding document checklist.'; return; }
  try {
    const d = await apiCall('/api/onboarding/checklist?candidate_id=' + encodeURIComponent(cid));
    el.innerHTML = `<div style="margin-bottom:10px">Progress: <strong>${d.received_count}/${d.total}</strong>${d.complete ? ' ✅ complete' : ''}</div>` +
      d.items.map(it => `<label style="display:flex;align-items:center;gap:8px;padding:5px 0;cursor:pointer">
        <input type="checkbox" ${it.received ? 'checked' : ''} data-doc="${it.name.replace(/"/g, '&quot;')}"
          onchange="toggleOnboardingDoc('${cid}', this.getAttribute('data-doc'), this.checked)"/>
        <span>${it.name}</span></label>`).join('');
    if (d.intro_meeting) {
      document.getElementById('intro-meeting-status').textContent =
        'Intro meeting: ' + (d.intro_meeting.message || d.intro_meeting.title || 'scheduled');
    }
  } catch (e) {
    el.innerHTML = '<span style="color:#ef4444">Error: ' + e.message + '</span>';
  }
}

async function toggleOnboardingDoc(cid, doc, received) {
  try {
    await apiCall('/api/onboarding/document-received', 'POST',
      { candidate_id: cid, document: doc, received: received });
    loadOnboardingChecklist();
    loadPipeline();
  } catch (e) { alert('Error: ' + e.message); }
}

async function scheduleIntroMeeting() {
  const cid = document.getElementById('onboard-checklist-candidate').value;
  if (!cid) { alert('Select a candidate first.'); return; }
  const statusEl = document.getElementById('intro-meeting-status');
  statusEl.textContent = 'Scheduling…';
  try {
    const d = await apiCall('/api/onboarding/schedule-intro', 'POST', { candidate_id: cid });
    statusEl.textContent = d.message || d.status || 'Intro meeting scheduled.';
    loadPipeline();
  } catch (e) {
    statusEl.textContent = 'Error: ' + e.message;
  }
}

// ---------- Init ----------
window.addEventListener('DOMContentLoaded', () => {
  syncInterviewTimeMin();
  setInterval(async () => {
    try {
      const s = await apiCall('/api/session');
      if (s.current_role) state.currentRole = s.current_role;
      updateSessionPills();
    } catch { }
  }, 15000);
});
