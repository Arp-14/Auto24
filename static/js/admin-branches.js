async function loadBranches() {
  const container = document.getElementById("branchesList");
  container.innerHTML = `<div class="empty-state">Загрузка...</div>`;

  const res = await apiFetch("/branches/");
  const branches = await res.json();

  if (!branches.length) {
    container.innerHTML = `<div class="empty-state">Отделений пока нет</div>`;
    return;
  }

  container.innerHTML = branches.map((b) => `
    <div class="card card-row">
      <div class="card-title">${escapeHtml(b.name)}</div>
      <button class="btn danger small" onclick="deleteBranch(${b.id})">Удалить</button>
    </div>
  `).join("");
}

document.getElementById("createBranchForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("newBranchName").value;
  const body = new URLSearchParams({ name });

  const res = await apiFetch("/branches/create", { method: "POST", body });
  const data = await res.json();

  if (!res.ok) {
    showToast(data.detail || "Ошибка", "error");
    return;
  }

  showToast(`Отделение "${data.name}" добавлено`, "success");
  e.target.reset();
  loadedTabs.delete("branches");
  openTab("branches");
  // список отделений для формы инструктора мог устареть — перегрузим при следующем открытии
  loadedTabs.delete("instructors");
});

async function deleteBranch(id) {
  if (!confirm("Удалить отделение?")) return;
  const res = await apiFetch(`/branches/${id}`, { method: "DELETE" });
  const data = await res.json();
  showToast(data.message || data.detail || "Готово", res.ok ? "success" : "error");
  if (res.ok) { loadedTabs.delete("branches"); openTab("branches"); }
}
