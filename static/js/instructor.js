// Логика панели инструктора. Авторизация теперь настоящая (пароль + токен),
// токен живёт в localStorage через shared auth.js — поэтому обновление
// страницы (F5) больше не сбрасывает сессию, как было в старой версии.

let instructorId = null;
let currentSlotId = null;
let weekOffset = 0;

// ── УТИЛИТЫ ──────────────────────────────────────────────────
async function get(path) {
  const r = await apiFetch(path);
  return r.json();
}
async function post(path, body) {
  const r = await apiFetch(path, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  return r.json();
}
async function put(path, body) {
  const r = await apiFetch(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}
async function del(path) {
  const r = await apiFetch(path, { method: "DELETE" });
  return r.json();
}

const MONTHS_SHORT = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'];
const DAYS_RU      = ['Вс','Пн','Вт','Ср','Чт','Пт','Сб'];

function getMonday(offset) {
  const today = new Date();
  today.setHours(0,0,0,0);
  const dow = today.getDay();
  const diff = dow === 0 ? -6 : 1 - dow;
  const monday = new Date(today);
  monday.setDate(today.getDate() + diff + offset * 7);
  return monday;
}
function fmt(d) { return d.toISOString().split('T')[0]; }

// ── ИНИЦИАЛИЗАЦИЯ ────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  const ok = await requireRole("instructor");
  if (!ok) return;

  instructorId = getInstructorId();
  const instructor = await get(`/instructors/${instructorId}`);
  document.getElementById('header-name').textContent = instructor.full_name || '—';

  document.getElementById('logoutBtn').addEventListener('click', logout);
  document.getElementById('reject-modal').addEventListener('click', function (e) {
    if (e.target === this) closeModal();
  });

  loadRequests();
  loadSchedule();
  loadSettings();
});

// ── ТАБЫ ─────────────────────────────────────────────────────
function switchTab(name) {
  const pages = ['requests','schedule','settings'];
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', pages[i] === name));
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
}

// ── ЗАЯВКИ ───────────────────────────────────────────────────
async function loadRequests() {
  const list = document.getElementById('requests-list');
  list.innerHTML = '<div class="loader">Загрузка...</div>';
  const slots = await get(`/admin/pending/${instructorId}`);
  document.getElementById('badge').textContent = slots.length ? ` (${slots.length})` : '';

  if (!slots.length) {
    list.innerHTML = `<div class="empty"><div class="empty-icon">✅</div><div class="empty-text">Новых заявок нет</div><div class="empty-sub">Все записи обработаны</div></div>`;
    return;
  }

  function dateToISO(ddmmyyyy) {
    const [d,m,y] = ddmmyyyy.split('.');
    return `${y}-${m}-${d}`;
  }

  list.innerHTML = slots.map(s => `
    <div class="booking-card" id="card-${s.id}">
      <div class="booking-date">${s.date} · ${DAYS_RU[new Date(dateToISO(s.date)).getDay()]}</div>
      <div class="booking-time">🕐 ${s.time}</div>
      <div class="booking-student">Ученик: <span>${s.student_name}</span></div>
      <div class="booking-actions">
        <button class="btn btn-green" onclick="confirmSlot(${s.id})">✓ Принять</button>
        <button class="btn btn-red" onclick="openRejectModal(${s.id},'${s.student_name}','${s.date}','${s.time}')">✕ Отказать</button>
      </div>
    </div>`).join('');
}

async function confirmSlot(slotId) {
  await post(`/admin/confirm/${slotId}`);
  document.getElementById(`card-${slotId}`)?.remove();
  const left = document.querySelectorAll('[id^="card-"]').length;
  document.getElementById('badge').textContent = left ? ` (${left})` : '';
  if (!left) loadRequests();
  showToastLocal('Запись подтверждена ✓');
}

function openRejectModal(slotId, name, date, time) {
  currentSlotId = slotId;
  document.getElementById('reject-modal-info').textContent = `${name} · ${date} в ${time}`;
  document.getElementById('reject-reason').value = '';
  document.getElementById('reject-modal').classList.add('open');
}
function closeModal() { document.getElementById('reject-modal').classList.remove('open'); currentSlotId = null; }

async function confirmReject() {
  const reason = document.getElementById('reject-reason').value.trim();
  await post(`/admin/reject/${currentSlotId}`, { message: reason || null });
  closeModal();
  document.getElementById(`card-${currentSlotId}`)?.remove();
  const left = document.querySelectorAll('[id^="card-"]').length;
  document.getElementById('badge').textContent = left ? ` (${left})` : '';
  if (!left) loadRequests();
  showToastLocal('Запись отклонена', '#ef4444');
}

// ── РАСПИСАНИЕ ───────────────────────────────────────────────
function changeWeek(dir) {
  if (dir < 0 && weekOffset === 0) return;
  weekOffset += dir;
  loadSchedule();
}

async function loadSchedule() {
  const list = document.getElementById('schedule-list');
  list.innerHTML = '<div class="loader">Загрузка...</div>';

  const monday = getMonday(weekOffset);
  const sunday = new Date(monday); sunday.setDate(monday.getDate() + 6);
  const wStart = fmt(monday); const wEnd = fmt(sunday);

  const mo = monday; const su = sunday;
  document.getElementById('week-label').textContent =
    `${mo.getDate()} ${MONTHS_SHORT[mo.getMonth()]} — ${su.getDate()} ${MONTHS_SHORT[su.getMonth()]}`;

  const allSlots = await get(`/admin/slots/all/${instructorId}?week_start=${wStart}&week_end=${wEnd}`);

  const byDate = {};
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday); d.setDate(monday.getDate() + i);
    byDate[fmt(d)] = [];
  }
  for (const s of allSlots) {
    byDate[s.date].push(s);
  }

  const html = Object.entries(byDate).map(([date, slots]) => {
    const d = new Date(date);
    const dayName = DAYS_RU[d.getDay()];
    const dayStr  = `${d.getDate()} ${MONTHS_SHORT[d.getMonth()]}`;
    const isPast  = d < new Date(getMonday(0));

    const slotRows = slots.sort((a,b) => a.time.localeCompare(b.time)).map(s => {
      let badge = '', info = '', delBtn = '';
      if (s.is_booked) {
        if (s.status === 'confirmed') {
          badge = `<span class="status-badge badge-confirmed">Подтверждено</span>`;
          info  = `<div class="student-name">${s.student_name}</div><div class="slot-status-text">Занято · подтверждено</div>`;
        } else {
          badge = `<span class="status-badge badge-pending">Ожидает</span>`;
          info  = `<div class="student-name">${s.student_name}</div><div class="slot-status-text">Ожидает подтверждения</div>`;
        }
      } else {
        badge = `<span class="status-badge badge-free">Свободно</span>`;
        info  = `<div class="student-name" style="color:var(--muted)">Свободно</div>`;
        if (!isPast) {
          delBtn = `<button class="btn btn-icon btn-red" onclick="deleteSlot(${s.id},'${date}')" title="Удалить слот">✕</button>`;
        }
      }
      return `<div class="slot-row">
        <div class="slot-time">${s.time.slice(0,5)}</div>
        <div class="slot-info">${info}</div>
        ${badge}
        ${delBtn}
      </div>`;
    }).join('');

    const addForm = !isPast ? `
      <div class="add-slot-form" id="add-form-${date}">
        <select id="add-time-${date}">
          ${['07:00','08:00','09:00','10:00','11:00','12:00','13:00','14:00','15:00','16:00','17:00','18:00','19:00','20:00']
            .map(t => `<option value="${t}">${t}</option>`).join('')}
        </select>
        <button class="btn btn-primary btn-sm" onclick="addSlot('${date}')">Добавить</button>
        <button class="btn btn-ghost btn-sm" onclick="toggleAddForm('${date}')">Отмена</button>
      </div>` : '';

    const addBtn = !isPast ? `<button class="day-add-btn" onclick="toggleAddForm('${date}')">+ Слот</button>` : '';

    return `<div class="day-card">
      <div class="day-header">
        <span>${dayName} <span class="day-date">${dayStr}</span></span>
        <div style="display:flex;align-items:center;gap:8px;">
          <span style="font-size:12px;color:var(--muted);font-weight:400">${slots.length} слот${slots.length===1?'':'ов'}</span>
          ${addBtn}
        </div>
      </div>
      ${slotRows}
      ${addForm}
    </div>`;
  }).join('');

  list.innerHTML = html;
}

function toggleAddForm(date) {
  const form = document.getElementById(`add-form-${date}`);
  form.classList.toggle('open');
}

async function addSlot(date) {
  const time = document.getElementById(`add-time-${date}`).value;
  const result = await post(
    `/admin/slots/add?instructor_id=${instructorId}&date=${date}&time=${time}:00`
  );
  if (result.detail) {
    showToastLocal('Такой слот уже существует', '#ef4444');
    return;
  }
  showToastLocal(`Слот ${time} добавлен ✓`);
  loadSchedule();
}

async function deleteSlot(slotId) {
  const result = await del(`/admin/slots/${slotId}`);
  if (result.detail) {
    showToastLocal(result.detail, '#ef4444');
    return;
  }
  showToastLocal('Слот удалён');
  loadSchedule();
}

// ── НАСТРОЙКИ ────────────────────────────────────────────────
async function loadSettings() {
  const data = await get(`/admin/instructor/${instructorId}/default-message`);
  document.getElementById('default-message').value = data.message || '';
}

async function saveDefaultMessage() {
  const msg = document.getElementById('default-message').value.trim();
  if (!msg) { showToastLocal('Введите сообщение', '#ef4444'); return; }
  await put(`/admin/instructor/${instructorId}/default-message`, { message: msg });
  showToastLocal('Сохранено ✓');
}

// Тост в стиле этой конкретной страницы (старый дизайн уже завязан на #toast + классы show)
function showToastLocal(text, color = '#22c55e') {
  const t = document.getElementById('toast');
  t.textContent = text;
  t.style.borderColor = color;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2800);
}
