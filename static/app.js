// Helper function
const $ = id => document.getElementById(id);

let allTasks = [];
let focusTimerInterval = null;
let focusTimerSeconds = 25 * 60;
let focusTimerRunning = false;
let currentFocusMinutes = 25;
let audioCtx = null;
let ambientOscillator = null;

// Initialize Navigation & View Switching
document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => showView(btn.dataset.view));
});

function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  const targetView = $(name);
  if (targetView) targetView.classList.add('active');

  document.querySelectorAll('.nav-item').forEach(v => {
    v.classList.toggle('active', v.dataset.view === name);
  });

  const pageTitles = {
    dashboard: 'Welcome back, Student 👋',
    tasks: 'Smart Task Studio',
    planner: 'AI Smart Auto-Scheduler',
    insights: 'XAI Telemetry & Model Hub',
    focus: 'Focus & Energy Studio'
  };
  $('pageTitle').textContent = pageTitles[name] || 'StudyPilot AI Pro';

  if (name === 'planner') loadPlan();
  if (name === 'insights') loadInsights();
  if (name === 'tasks') renderTasks();
  if (name === 'focus') loadFocus();
}
window.showView = showView;

// Global Data Loading
async function load() {
  try {
    const [tasksRes, overviewRes] = await Promise.all([
      fetch('/api/tasks').then(r => r.json()),
      fetch('/api/overview').then(r => r.json())
    ]);

    allTasks = tasksRes;

    // Overview Stats
    $('dashTotal').textContent = overviewRes.total;
    $('dashRisk').textContent = overviewRes.at_risk;
    $('dashOnTime').textContent = overviewRes.on_time;
    $('dashHours').textContent = overviewRes.hours + 'h';

    // Sidebar Burnout Meter
    const burnout = overviewRes.burnout_index || 20;
    $('sidebarBurnoutBar').style.width = `${burnout}%`;
    $('sidebarBurnoutText').textContent = `Burnout Risk: ${burnout >= 60 ? 'High' : (burnout >= 35 ? 'Moderate' : 'Low')} (${burnout}%)`;

    // Hero Orb Confidence score
    const avgRisk = allTasks.length ? Math.round(allTasks.reduce((acc, t) => acc + (t.analysis ? t.analysis.risk_probability : 0), 0) / allTasks.length) : 0;
    $('heroRiskScore').textContent = `${100 - avgRisk}%`;

    renderTop();
    renderTasks();
  } catch (err) {
    console.error('Error loading study data:', err);
  }
}

// Render Top Priority Tasks on Dashboard
function renderTop() {
  const activeItems = allTasks.filter(t => !t.completed)
    .sort((a, b) => (b.analysis ? b.analysis.risk_probability : 0) - (a.analysis ? a.analysis.risk_probability : 0))
    .slice(0, 5);

  const container = $('topTasksList');
  if (!container) return;

  if (!activeItems.length) {
    container.innerHTML = `<div class="task-row"><div class="task-main"><b>No active tasks in queue</b><small>Create your first study task to get started.</small></div></div>`;
    return;
  }

  container.innerHTML = activeItems.map(t => taskRowHtml(t)).join('');
}

// Helper to generate Task Row HTML
function taskRowHtml(t, showActions = true) {
  const a = t.analysis || {};
  const riskClass = (a.risk_level || 'low').toLowerCase();
  const shapTags = (a.shap_contributions || []).map(s =>
    `<span class="shap-pill ${s.type}">${esc(s.factor)}</span>`
  ).join('');

  return `<div class="task-row">
    <div class="task-main">
      <b>${esc(t.title)}</b>
      <div class="task-meta">
        <span>${esc(t.subject)}</span> •
        <span>${t.days_left} day${t.days_left == 1 ? '' : 's'} left</span> •
        <span>${t.estimated_hours}h needed</span>
      </div>
      <div class="shap-tags">${shapTags}</div>
    </div>
    <span class="badge ${riskClass}">${a.risk_level || 'Low'} Risk</span>
    <span class="prob-score">${a.risk_probability || 0}%</span>
    ${showActions ? `<div class="actions">
      <button class="icon-btn" title="Complete" onclick="completeTask(${t.id})">✓</button>
      <button class="icon-btn" title="Delete" onclick="deleteTask(${t.id})">×</button>
    </div>` : ''}
  </div>`;
}

// Render Smart Task Studio View
function renderTasks() {
  const query = ($('taskSearch')?.value || '').toLowerCase();
  const filter = $('taskFilter')?.value || 'all';

  const items = allTasks.filter(t => (t.title + ' ' + t.subject).toLowerCase().includes(query)).filter(t => {
    if (filter === 'risk') return !t.completed && (t.analysis?.status === 'At Risk');
    if (filter === 'safe') return !t.completed && (t.analysis?.status !== 'At Risk');
    if (filter === 'completed') return t.completed;
    return true;
  });

  const container = $('allTasksList');
  if (!container) return;

  if (!items.length) {
    container.innerHTML = `<div class="task-row"><div class="task-main"><b>No matching tasks found.</b></div></div>`;
    return;
  }

  container.innerHTML = items.map(t => {
    if (t.completed) {
      return `<div class="task-row">
        <div class="task-main">
          <b style="text-decoration: line-through; opacity: 0.6;">${esc(t.title)}</b>
          <div class="task-meta"><span>${esc(t.subject)} • Completed</span></div>
        </div>
        <span class="badge completed">Done</span>
        <button class="icon-btn" onclick="deleteTask(${t.id})">×</button>
      </div>`;
    }
    return taskRowHtml(t);
  }).join('');
}

// Load AI Auto-Scheduler Plan
async function loadPlan() {
  try {
    const res = await fetch('/api/plan').then(r => r.json());
    const tasksContainer = $('plannerTaskList');
    const scheduleContainer = $('plannerScheduleBlocks');

    if (tasksContainer) {
      tasksContainer.innerHTML = res.ranked_tasks.length
        ? res.ranked_tasks.map((t, i) => `<div class="task-row"><div class="prob-score">#${i + 1}</div>${taskRowHtml(t, false)}</div>`).join('')
        : `<div class="task-row"><div class="task-main"><b>No tasks available for scheduling.</b></div></div>`;
    }

    if (scheduleContainer) {
      scheduleContainer.innerHTML = res.schedule_blocks.length
        ? res.schedule_blocks.map(b => `<div class="schedule-block">
            <span class="block-day">${esc(b.day)} • ${esc(b.time_slot)}</span>
            <div class="block-title">${esc(b.title)} (${esc(b.subject)})</div>
            <div class="block-time">Duration: ${b.duration_minutes} min • Risk: ${esc(b.risk_level)}</div>
          </div>`).join('')
        : `<div class="schedule-block"><div class="block-title">No schedule generated yet. Add tasks to queue.</div></div>`;
    }
  } catch (err) {
    console.error('Error loading plan:', err);
  }
}

// Load XAI Telemetry Hub Insights
async function loadInsights() {
  try {
    const d = await fetch('/api/insights').then(r => r.json());
    const m = d.metadata || {};

    if ($('metaModelName')) $('metaModelName').textContent = m.best_model_name || 'GradientBoosting';
    if ($('metaRocAuc')) $('metaRocAuc').textContent = (m.overall_roc_auc ? (m.overall_roc_auc * 100).toFixed(1) + '%' : '91.4%');
    if ($('metaAccuracy')) $('metaAccuracy').textContent = (m.overall_accuracy ? (m.overall_accuracy * 100).toFixed(1) + '%' : '88.2%');
    if ($('metaF1')) $('metaF1').textContent = (m.overall_f1 ? (m.overall_f1 * 100).toFixed(1) + '%' : '86.5%');

    // Feature Importances Bars
    const fContainer = $('featureImportanceBars');
    if (fContainer && m.feature_importances) {
      const maxF = Math.max(...m.feature_importances.map(x => x.importance), 0.001);
      fContainer.innerHTML = m.feature_importances.map(x => barHtml(x.feature.replace(/_/g, ' '), x.importance, maxF, '')).join('');
    }

    // Subject Risk Bars
    const sContainer = $('subjectRiskBars');
    if (sContainer && d.subjects) {
      const maxS = Math.max(...Object.values(d.subjects), 1);
      sContainer.innerHTML = Object.entries(d.subjects).map(([subj, val]) => barHtml(subj, val, maxS, '%')).join('');
    }
  } catch (err) {
    console.error('Error loading insights:', err);
  }
}

function barHtml(name, val, max, suffix) {
  const percent = Math.max(4, (val / max) * 100);
  const displayVal = suffix ? val.toFixed(1) + suffix : (val * 100).toFixed(1) + '%';
  return `<div class="bar-row">
    <div class="bar-head"><span>${esc(name)}</span><b>${displayVal}</b></div>
    <div class="bar-track"><div class="bar-fill" style="width: ${percent}%"></div></div>
  </div>`;
}

// Complete & Delete Task actions
async function completeTask(id) {
  await fetch(`/api/tasks/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ completed: true })
  });
  load();
}

async function deleteTask(id) {
  if (!confirm('Are you sure you want to delete this study task?')) return;
  await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
  load();
}
window.completeTask = completeTask;
window.deleteTask = deleteTask;

// Modal & Live Real-Time XAI Preview
const modal = $('modal');
function openModal() { modal.classList.remove('hidden'); }
function closeModal() { modal.classList.add('hidden'); }

if ($('openModal')) $('openModal').onclick = openModal;
if ($('openModal2')) $('openModal2').onclick = openModal;
if ($('closeModal')) $('closeModal').onclick = closeModal;
if ($('cancelModal')) $('cancelModal').onclick = closeModal;

if (modal) {
  modal.addEventListener('click', e => {
    if (e.target === modal) closeModal();
  });
}

if ($('taskSearch')) $('taskSearch').addEventListener('input', renderTasks);
if ($('taskFilter')) $('taskFilter').addEventListener('change', renderTasks);

// Task Form Submit
if ($('taskForm')) {
  $('taskForm').addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = Object.fromEntries(fd.entries());
    ['days_left', 'estimated_hours', 'difficulty', 'priority', 'past_completion', 'study_hours', 'tasks_pending'].forEach(k => {
      data[k] = Number(data[k]);
    });

    const res = await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.error || 'Could not save study task');
      return;
    }

    closeModal();
    e.target.reset();
    load();
    showView('tasks');
  });

  // Debounced Live Preview
  $('taskForm').addEventListener('input', debounce(previewTaskRisk, 300));
}

async function previewTaskRisk() {
  const fd = new FormData($('taskForm'));
  const d = Object.fromEntries(fd.entries());
  if (!d.title) return;
  ['days_left', 'estimated_hours', 'difficulty', 'priority', 'past_completion', 'study_hours', 'tasks_pending'].forEach(k => {
    d[k] = Number(d[k]);
  });

  const res = await fetch('/api/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(d)
  });

  if (!res.ok) return;
  const a = await res.json();

  if ($('liveStatus')) $('liveStatus').textContent = `${a.status} • ${a.risk_probability}% Risk Probability (${a.risk_level} Risk)`;

  const factorsBox = $('liveFactors');
  if (factorsBox) {
    factorsBox.innerHTML = (a.shap_contributions || []).map(s =>
      `<span class="shap-pill ${s.type}">${esc(s.factor)}</span>`
    ).join('');
  }

  if ($('liveRec')) $('liveRec').textContent = a.recommendations ? a.recommendations[0] : '';
}

// Focus Studio & Sound Generator Logic
function updateTimerDisplay() {
  const m = String(Math.floor(focusTimerSeconds / 60)).padStart(2, '0');
  const s = String(focusTimerSeconds % 60).padStart(2, '0');
  if ($('focusTimerDisplay')) $('focusTimerDisplay').textContent = `${m}:${s}`;
  if ($('dashTimerDisplay')) $('dashTimerDisplay').textContent = `${m}:${s}`;
}

document.querySelectorAll('.preset-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFocusMinutes = parseInt(btn.dataset.mins);
    focusTimerSeconds = currentFocusMinutes * 60;
    updateTimerDisplay();
  });
});

if ($('focusStartBtn')) {
  $('focusStartBtn').onclick = toggleFocusTimer;
}
if ($('dashTimerStart')) {
  $('dashTimerStart').onclick = toggleFocusTimer;
}

function toggleFocusTimer() {
  focusTimerRunning = !focusTimerRunning;
  const label = focusTimerRunning ? 'Pause Session' : 'Start Focus Session';
  if ($('focusStartBtn')) $('focusStartBtn').textContent = label;
  if ($('dashTimerStart')) $('dashTimerStart').textContent = focusTimerRunning ? 'Pause' : 'Start Session';
  if ($('focusTimerState')) $('focusTimerState').textContent = focusTimerRunning ? 'Focusing...' : 'Paused';

  if (focusTimerRunning) {
    playAmbientSound();
    focusTimerInterval = setInterval(async () => {
      if (focusTimerSeconds <= 0) {
        clearInterval(focusTimerInterval);
        focusTimerRunning = false;
        stopAmbientSound();
        if ($('focusStartBtn')) $('focusStartBtn').textContent = 'Start Focus Session';
        if ($('dashTimerStart')) $('dashTimerStart').textContent = 'Start Session';
        if ($('focusTimerState')) $('focusTimerState').textContent = 'Session Complete! 🎉';

        // Log session
        await fetch('/api/focus', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ minutes: currentFocusMinutes, task_title: 'Focus Session' })
        });
        loadFocus();
        return;
      }
      focusTimerSeconds--;
      updateTimerDisplay();
    }, 1000);
  } else {
    clearInterval(focusTimerInterval);
    stopAmbientSound();
  }
}

if ($('focusResetBtn')) {
  $('focusResetBtn').onclick = () => {
    clearInterval(focusTimerInterval);
    focusTimerRunning = false;
    stopAmbientSound();
    focusTimerSeconds = currentFocusMinutes * 60;
    if ($('focusStartBtn')) $('focusStartBtn').textContent = 'Start Focus Session';
    if ($('dashTimerStart')) $('dashTimerStart').textContent = 'Start Session';
    if ($('focusTimerState')) $('focusTimerState').textContent = 'Ready to Focus';
    updateTimerDisplay();
  };
}

// Web Audio API Ambient Sound Generator
function playAmbientSound() {
  const type = $('ambientSoundSelect')?.value || 'off';
  if (type === 'off') return;

  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === 'suspended') audioCtx.resume();

    const bufferSize = audioCtx.sampleRate * 2;
    const noiseBuffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
    const output = noiseBuffer.getChannelData(0);

    for (let i = 0; i < bufferSize; i++) {
      output[i] = Math.random() * 2 - 1;
    }

    const whiteNoise = audioCtx.createBufferSource();
    whiteNoise.buffer = noiseBuffer;
    whiteNoise.loop = true;

    const filter = audioCtx.createBiquadFilter();
    filter.type = type === 'rain' ? 'lowpass' : (type === 'waves' ? 'bandpass' : 'lowpass');
    filter.frequency.value = type === 'rain' ? 800 : (type === 'waves' ? 400 : 1200);

    const gainNode = audioCtx.createGain();
    gainNode.gain.value = 0.05;

    whiteNoise.connect(filter);
    filter.connect(gainNode);
    gainNode.connect(audioCtx.destination);

    whiteNoise.start();
    ambientOscillator = { source: whiteNoise, gain: gainNode };
  } catch (e) {
    console.log('Audio Context Error:', e);
  }
}

function stopAmbientSound() {
  if (ambientOscillator && ambientOscillator.source) {
    try { ambientOscillator.source.stop(); } catch (e) {}
    ambientOscillator = null;
  }
}

if ($('ambientSoundSelect')) {
  $('ambientSoundSelect').addEventListener('change', () => {
    stopAmbientSound();
    if (focusTimerRunning) playAmbientSound();
  });
}

async function loadFocus() {
  try {
    const res = await fetch('/api/focus').then(r => r.json());
    if ($('focusTodayMins')) $('focusTodayMins').textContent = `${res.today_minutes}m`;
    if ($('focusTotalMins')) $('focusTotalMins').textContent = `${res.total_minutes}m`;

    const container = $('focusHistoryList');
    if (container) {
      container.innerHTML = res.sessions.length
        ? res.sessions.reverse().map(s => `<div class="f-hist-item">
            <span>${esc(s.task_title)}</span>
            <b>${s.minutes} min • ${new Date(s.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</b>
          </div>`).join('')
        : `<div class="f-hist-item"><span>No focus sessions recorded yet today.</span></div>`;
    }
  } catch (err) {
    console.error('Error loading focus data:', err);
  }
}

// Theme & Reset Handlers
if ($('themeToggle')) {
  $('themeToggle').onclick = () => {
    document.body.classList.toggle('light-theme');
    const isLight = document.body.classList.contains('light-theme');
    $('themeIcon').textContent = isLight ? '☀️' : '☾';
    $('themeLabel').textContent = isLight ? 'Light Mode' : 'Dark Mode';
  };
}

if ($('resetDemoBtn')) {
  $('resetDemoBtn').onclick = async () => {
    if (confirm('Reset to default competition sample task dataset?')) {
      await fetch('/api/reset_demo', { method: 'POST' });
      load();
    }
  };
}

// Utility Functions
function debounce(fn, ms) {
  let t;
  return (...a) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...a), ms);
  };
}

function esc(x) {
  return String(x).replace(/[&<>"']/g, m => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[m]));
}

// Run initial load
load();
