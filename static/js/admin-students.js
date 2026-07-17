async function loadStudents() {
  const container = document.getElementById("studentsList");
  container.innerHTML = `<div class="empty-state">Загрузка...</div>`;

  const res = await apiFetch("/admin/students/all");
  const students = await res.json();

  if (!students.length) {
    container.innerHTML = `<div class="empty-state">Учеников пока нет</div>`;
    return;
  }

  container.innerHTML = students.map((s) => `
    <div class="card" data-id="${s.id}">
      <div class="card-row">
        <div>
          <div class="card-title">${escapeHtml(s.full_name)}</div>
          <div class="card-sub">
            Прогресс: ${s.used_lessons}/${s.total_lessons} занятий ·
            Telegram: ${s.telegram_id === "не привязан" ? "❌ не привязан" : "✅ привязан"}
          </div>
          <div class="card-sub">Ключ: <code>${escapeHtml(s.identification_key)}</code></div>
        </div>
        <div style="display:flex; gap:8px;">
          <button class="btn ghost small" onclick="resetTelegram(${s.id})">Отвязать Telegram</button>
          <button class="btn danger small" onclick="deleteStudent(${s.id})">Удалить</button>
        </div>
      </div>
      <div style="display:flex; gap:8px; align-items:center; margin-top:12px; padding-top:12px; border-top:1px solid var(--border);">
        <input type="number" min="1" placeholder="Кол-во занятий" id="addLessons-${s.id}" style="max-width:160px;">
        <button class="btn small" onclick="addLessons(${s.id})">+ Добавить занятия</button>
      </div>
    </div>
  `).join("");
}

document.getElementById("createStudentForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const full_name = document.getElementById("newStudentName").value;
  const total_lessons = document.getElementById("newStudentLessons").value;
  const body = new URLSearchParams({ full_name, total_lessons });

  const res = await apiFetch("/admin/students/create", { method: "POST", body });
  const data = await res.json();

  if (!res.ok) {
    showToast(data.detail || "Ошибка", "error");
    return;
  }

  showToast(`Ученик добавлен. Ключ для бота: ${data.key}`, "success");
  e.target.reset();
  loadedTabs.delete("students");
  openTab("students");
});

async function resetTelegram(id) {
  if (!confirm("Отвязать Telegram у этого ученика?")) return;
  const res = await apiFetch(`/admin/students/${id}/reset-telegram`, { method: "POST" });
  const data = await res.json();
  showToast(data.message || "Готово", res.ok ? "success" : "error");
  if (res.ok) { loadedTabs.delete("students"); openTab("students"); }
}

async function deleteStudent(id) {
  if (!confirm("Удалить ученика без возможности восстановления?")) return;
  const res = await apiFetch(`/admin/students/${id}`, { method: "DELETE" });
  const data = await res.json();
  showToast(data.message || "Готово", res.ok ? "success" : "error");
  if (res.ok) { loadedTabs.delete("students"); openTab("students"); }
}

async function addLessons(id) {
  const input = document.getElementById(`addLessons-${id}`);
  const amount = parseInt(input.value, 10);
  if (!amount || amount < 1) {
    showToast("Укажи количество занятий", "error");
    return;
  }
  const body = new URLSearchParams({ amount });
  const res = await apiFetch(`/admin/students/${id}/add-lessons`, { method: "POST", body });
  const data = await res.json();
  showToast(data.message || "Готово", res.ok ? "success" : "error");
  if (res.ok) { loadedTabs.delete("students"); openTab("students"); }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
