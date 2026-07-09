let branchesCache = [];

async function loadInstructors() {
  const container = document.getElementById("instructorsList");
  container.innerHTML = `<div class="empty-state">Загрузка...</div>`;

  const [instrRes, branchRes] = await Promise.all([
    apiFetch("/instructors/"),
    apiFetch("/branches/"),
  ]);
  const instructors = await instrRes.json();
  branchesCache = await branchRes.json();

  fillBranchSelect();

  if (!instructors.length) {
    container.innerHTML = `<div class="empty-state">Инструкторов пока нет</div>`;
    return;
  }

  container.innerHTML = instructors.map((i) => {
    const branch = branchesCache.find((b) => b.id === i.branch_id);
    return `
    <div class="card card-row">
      <div style="display:flex; align-items:center; gap:14px;">
        <img class="instructor-photo" src="/${i.photo_path}" onerror="this.style.opacity=0.3" />
        <div>
          <div class="card-title">${escapeHtml(i.full_name)}</div>
          <div class="card-sub">
            ${escapeHtml(i.car_model)} · ${(i.transmission_type === "automatic" || i.transmission_type === "автомат") ? "АКПП" : "МКПП"} ·
            отделение: ${branch ? escapeHtml(branch.name) : "не указано"}
          </div>
          <div class="card-sub">За рулём с ${i.driving_since} г. · инструктор с ${i.instructor_since} г.</div>
        </div>
      </div>
      <button class="btn danger small" onclick="deleteInstructor(${i.id})">Удалить</button>
    </div>
  `;
  }).join("");
}

function fillBranchSelect() {
  const select = document.getElementById("newInstructorBranch");
  select.innerHTML = branchesCache.map((b) => `<option value="${b.id}">${escapeHtml(b.name)}</option>`).join("")
    || `<option value="">Сначала добавьте отделение</option>`;
}

document.getElementById("createInstructorForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const formData = new FormData(form);

  const res = await apiFetch("/instructors/create", { method: "POST", body: formData });
  const data = await res.json();

  if (!res.ok) {
    showToast(data.detail || "Ошибка создания инструктора", "error");
    return;
  }

  showToast(`Инструктор "${data.full_name}" добавлен`, "success");
  form.reset();
  loadedTabs.delete("instructors");
  openTab("instructors");
});

async function deleteInstructor(id) {
  if (!confirm("Удалить инструктора? Это действие необратимо.")) return;
  const res = await apiFetch(`/instructors/${id}`, { method: "DELETE" });
  const data = await res.json();
  showToast(data.message || "Готово", res.ok ? "success" : "error");
  if (res.ok) { loadedTabs.delete("instructors"); openTab("instructors"); }
}
