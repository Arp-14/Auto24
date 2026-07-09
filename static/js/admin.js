// Переключение вкладок в панели администратора.
// Данные каждой вкладки подгружаются лениво — при первом открытии,
// логика подгрузки лежит в своих файлах: admin-students.js, admin-instructors.js, admin-branches.js

const loadedTabs = new Set();

function initTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => openTab(btn.dataset.tab));
  });
  openTab("students"); // вкладка по умолчанию
}

function openTab(tabName) {
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === tabName));
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${tabName}`));

  if (loadedTabs.has(tabName)) return;
  loadedTabs.add(tabName);

  if (tabName === "students") loadStudents();
  if (tabName === "instructors") loadInstructors();
  if (tabName === "branches") loadBranches();
}

document.addEventListener("DOMContentLoaded", async () => {
  const ok = await requireRole("admin");
  if (!ok) return;
  initTabs();
  document.getElementById("logoutBtn").addEventListener("click", logout);
});
