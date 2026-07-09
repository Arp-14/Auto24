// Общая логика авторизации для всех страниц фронта.
// Токен и роль храним в localStorage — благодаря этому при обновлении
// страницы (F5) авторизация НЕ слетает, в отличие от старой версии,
// где токен жил только в переменной JS и терялся при перезагрузке.

const API_BASE = ""; // фронт и API на одном домене, поэтому базовый путь пустой

function getToken() {
  return localStorage.getItem("auto24_token");
}

function getRole() {
  return localStorage.getItem("auto24_role");
}

function getInstructorId() {
  return localStorage.getItem("auto24_instructor_id");
}

function saveSession(token, role, instructorId) {
  localStorage.setItem("auto24_token", token);
  localStorage.setItem("auto24_role", role);
  if (instructorId !== undefined && instructorId !== null) {
    localStorage.setItem("auto24_instructor_id", instructorId);
  }
}

function clearSession() {
  localStorage.removeItem("auto24_token");
  localStorage.removeItem("auto24_role");
  localStorage.removeItem("auto24_instructor_id");
}

function logout() {
  clearSession();
  window.location.href = "/app/login.html";
}

// Обёртка над fetch, которая сама добавляет заголовок Authorization
// и обрабатывает протухшую/неверную сессию (401) — сразу выкидывает на логин.
async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = options.headers ? { ...options.headers } : {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(API_BASE + path, { ...options, headers });

  if (response.status === 401) {
    clearSession();
    window.location.href = "/app/login.html";
    throw new Error("Сессия истекла");
  }

  return response;
}

// Проверяет при загрузке страницы, что токен ещё жив, и что роль подходящая.
// Вызывать в начале каждой защищённой страницы: requireRole("admin") / requireRole("instructor")
async function requireRole(expectedRole) {
  const token = getToken();
  const role = getRole();

  if (!token || role !== expectedRole) {
    window.location.href = "/app/login.html";
    return false;
  }

  try {
    const res = await apiFetch("/auth/me");
    if (!res.ok) {
      window.location.href = "/app/login.html";
      return false;
    }
    return true;
  } catch (e) {
    return false;
  }
}

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}
