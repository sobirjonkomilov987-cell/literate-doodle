/**
 * AdminPro - Professional Admin Authentication & Dashboard Controller
 */

const API_BASE = window.location.origin;
let adminToken = localStorage.getItem("admin_token") || localStorage.getItem("token") || null;
let currentAdmin = null;
let revenueChart = null;
let rolesChart = null;
let allUsersData = [];

// ================= INITIALIZATION & ROUTING =================
document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
  initLucide();
  handleUrlRouting();
  await verifyAdminSession();
});

function initLucide() {
  if (window.lucide) {
    lucide.createIcons();
  }
}

// ================= THEME TOGGLE (DARK / LIGHT) =================
function initTheme() {
  const savedTheme = localStorage.getItem("admin_theme") || "dark";
  applyTheme(savedTheme);
}

function toggleTheme() {
  const isDark = document.documentElement.classList.contains("dark");
  const newTheme = isDark ? "light" : "dark";
  applyTheme(newTheme);
  localStorage.setItem("admin_theme", newTheme);
}

function applyTheme(theme) {
  const icon = document.getElementById("theme-icon");
  if (theme === "light") {
    document.documentElement.classList.remove("dark");
    document.documentElement.classList.add("light");
    if (icon) icon.setAttribute("data-lucide", "moon");
  } else {
    document.documentElement.classList.remove("light");
    document.documentElement.classList.add("dark");
    if (icon) icon.setAttribute("data-lucide", "sun");
  }
  initLucide();
}

// ================= ROUTING & VIEW CONTROLLERS =================
function handleUrlRouting() {
  const path = window.location.pathname;
  const hash = window.location.hash;

  if (path.includes("/admin/register") || hash === "#register") {
    switchAuthView("register");
  } else if (path.includes("/admin/login") || hash === "#login") {
    switchAuthView("login");
  } else if (path.includes("/admin/profile") || hash === "#profile") {
    navigateToView("profile");
  } else if (path.includes("/admin/users") || hash === "#users") {
    navigateToView("users");
  } else if (path.includes("/admin/activities") || hash === "#activities") {
    navigateToView("activities");
  } else {
    navigateToView("dashboard");
  }
}

function switchAuthView(view) {
  const loginCard = document.getElementById("view-admin-login");
  const registerCard = document.getElementById("view-admin-register");
  const authWrapper = document.getElementById("auth-views-wrapper");
  const appContainer = document.getElementById("admin-app-container");

  if (appContainer) appContainer.classList.add("hidden");
  if (authWrapper) authWrapper.classList.remove("hidden");

  if (view === "register") {
    if (loginCard) loginCard.classList.add("hidden");
    if (registerCard) registerCard.classList.remove("hidden");
  } else {
    if (registerCard) registerCard.classList.add("hidden");
    if (loginCard) loginCard.classList.remove("hidden");
  }
  initLucide();
}

function navigateToView(viewName) {
  // If not authenticated, cannot view dashboard or inner views
  if (!adminToken || !currentAdmin || currentAdmin.role !== "admin") {
    switchAuthView("login");
    return;
  }

  const authWrapper = document.getElementById("auth-views-wrapper");
  const appContainer = document.getElementById("admin-app-container");

  if (authWrapper) authWrapper.classList.add("hidden");
  if (appContainer) appContainer.classList.remove("hidden");

  // Hide all view panels
  document.querySelectorAll(".admin-view").forEach(panel => panel.classList.add("hidden"));

  // Update navigation button active state
  document.querySelectorAll("#admin-sidebar nav button").forEach(btn => {
    btn.className = "w-full flex items-center gap-3.5 px-4 py-3 rounded-2xl text-sm font-semibold transition text-slate-400 hover:text-white hover:bg-slate-800/60";
  });

  const activeBtn = document.getElementById(`nav-item-${viewName}`);
  if (activeBtn) {
    activeBtn.className = "w-full flex items-center gap-3.5 px-4 py-3 rounded-2xl text-sm font-semibold transition text-white bg-brand-600 shadow-lg shadow-brand-600/30";
  }

  // Show selected panel
  const targetPanel = document.getElementById(`panel-${viewName}`);
  if (targetPanel) targetPanel.classList.remove("hidden");

  // Update header title
  const headerTitle = document.getElementById("page-header-title");
  const headerSub = document.getElementById("page-header-sub");
  if (viewName === "dashboard") {
    if (headerTitle) headerTitle.textContent = "Umumiy Dashboard";
    if (headerSub) headerSub.textContent = "Tizim holati va real-vaqt tahlillari";
    refreshDashboardData();
  } else if (viewName === "users") {
    if (headerTitle) headerTitle.textContent = "Foydalanuvchilar Boshqaruvi";
    if (headerSub) headerSub.textContent = "Adminlar, tashkilotchilar va mijozlarni nazorat qilish";
    loadAllUsers();
  } else if (viewName === "activities") {
    if (headerTitle) headerTitle.textContent = "Audit & Xavfsizlik Logi";
    if (headerSub) headerSub.textContent = "Oxirgi 50 ta muhim tizim amallari ro'yxati";
    loadAllActivities();
  } else if (viewName === "profile") {
    if (headerTitle) headerTitle.textContent = "Admin Profili & Sozlamalar";
    if (headerSub) headerSub.textContent = "Shaxsiy ma'lumotlar va xavfsizlik sozlamalari";
    loadProfileView();
  }

  initLucide();
}

function toggleMobileSidebar() {
  const sidebar = document.getElementById("admin-sidebar");
  if (sidebar) {
    sidebar.classList.toggle("hidden");
  }
}

// ================= SESSION & AUTH VERIFICATION =================
async function verifyAdminSession() {
  if (!adminToken) {
    switchAuthView("login");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });

    if (res.ok) {
      const user = await res.json();
      if (user.role === "admin") {
        currentAdmin = user;
        updateAdminUIProfile(user);
        navigateToView("dashboard");
      } else {
        showToast("Kirish taqiqlangan! Faqat admin hisoblariga ruxsat etiladi.", "error");
        handleAdminLogout(false);
      }
    } else {
      handleAdminLogout(false);
    }
  } catch (err) {
    console.error("Session check error:", err);
    handleAdminLogout(false);
  }
}

function updateAdminUIProfile(admin) {
  const greetingEl = document.getElementById("dash-greeting-name");
  const sidebarName = document.getElementById("sidebar-user-name");
  const topbarName = document.getElementById("topbar-user-name");
  const sidebarAvatar = document.getElementById("sidebar-user-avatar");
  const topbarAvatar = document.getElementById("topbar-user-avatar");

  const displayName = admin.name || admin.username;
  const avatarUrl = admin.avatar || `https://api.dicebear.com/7.x/bottts/svg?seed=${admin.username}`;

  if (greetingEl) greetingEl.textContent = displayName;
  if (sidebarName) sidebarName.textContent = displayName;
  if (topbarName) topbarName.textContent = displayName;
  if (sidebarAvatar) sidebarAvatar.src = avatarUrl;
  if (topbarAvatar) topbarAvatar.src = avatarUrl;
}

// ================= AUTHENTICATION ACTIONS =================
function fillDemoAdminCredentials() {
  const loginInp = document.getElementById("login-identifier");
  const passInp = document.getElementById("login-password");
  if (loginInp) loginInp.value = "admin";
  if (passInp) passInp.value = "sobirjon123";
  showToast("Bosh admin ma'lumotlari kiritildi!", "info");
}

function togglePasswordVisibility(inputId, iconId) {
  const input = document.getElementById(inputId);
  const icon = document.getElementById(iconId);
  if (input.type === "password") {
    input.type = "text";
    icon.setAttribute("data-lucide", "eye-off");
  } else {
    input.type = "password";
    icon.setAttribute("data-lucide", "eye");
  }
  initLucide();
}

async function handleAdminLogin(e) {
  e.preventDefault();
  const login = document.getElementById("login-identifier").value.trim();
  const password = document.getElementById("login-password").value.trim();
  const btn = document.getElementById("btn-login-submit");

  if (!login || !password) {
    showToast("Iltimos, login va parolni kiriting", "warning");
    return;
  }

  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Tekshirilmoqda...`;
  initLucide();

  try {
    const res = await fetch(`${API_BASE}/api/auth/admin/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ login, password })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Login yoki parol noto'g'ri");
    }

    adminToken = data.access_token;
    localStorage.setItem("admin_token", adminToken);
    localStorage.setItem("token", adminToken); // Asosiy sayt uchun ham
    currentAdmin = data.user;

    showToast(`Xush kelibsiz, ${currentAdmin.name || currentAdmin.username}!`, "success");
    updateAdminUIProfile(currentAdmin);
    navigateToView("dashboard");

  } catch (err) {
    const card = document.getElementById("view-admin-login");
    if (card) {
      card.classList.add("shake");
      setTimeout(() => card.classList.remove("shake"), 500);
    }
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span>Kirish</span><i data-lucide="arrow-right" class="w-4 h-4"></i>`;
    initLucide();
  }
}

// Live Validation for Registration
function checkPasswordStrength(password) {
  const bar = document.getElementById("strength-bar");
  const label = document.getElementById("strength-label");
  if (!bar || !label) return;

  if (password.length === 0) {
    bar.style.width = "0%";
    label.textContent = "Kutilmoqda...";
    label.className = "font-bold text-slate-400";
    return;
  }

  let strength = 0;
  if (password.length >= 8) strength += 1;
  if (/[A-Z]/.test(password)) strength += 1;
  if (/[0-9]/.test(password)) strength += 1;
  if (/[^A-Za-z0-9]/.test(password)) strength += 1;

  if (password.length < 8) {
    bar.style.width = "25%";
    bar.className = "h-full bg-red-500 transition-all duration-300";
    label.textContent = "Juda qisqa (min 8 ta)";
    label.className = "font-bold text-red-400";
  } else if (strength <= 2) {
    bar.style.width = "50%";
    bar.className = "h-full bg-amber-500 transition-all duration-300";
    label.textContent = "O'rtacha";
    label.className = "font-bold text-amber-400";
  } else if (strength === 3) {
    bar.style.width = "75%";
    bar.className = "h-full bg-teal-500 transition-all duration-300";
    label.textContent = "Yaxshi";
    label.className = "font-bold text-teal-400";
  } else {
    bar.style.width = "100%";
    bar.className = "h-full bg-emerald-500 transition-all duration-300";
    label.textContent = "Kuchli xavfsiz!";
    label.className = "font-bold text-emerald-400";
  }
}

function validatePasswordMatch() {
  const pass = document.getElementById("reg-password").value;
  const confirm = document.getElementById("reg-confirm-password").value;
  const errEl = document.getElementById("pass-match-error");
  if (!errEl) return;

  if (confirm.length > 0 && pass !== confirm) {
    errEl.classList.remove("hidden");
  } else {
    errEl.classList.add("hidden");
  }
}

async function handleAdminRegister(e) {
  e.preventDefault();
  const name = document.getElementById("reg-name").value.trim();
  const username = document.getElementById("reg-username").value.trim();
  const email = document.getElementById("reg-email").value.trim();
  const phone = document.getElementById("reg-phone").value.trim();
  const password = document.getElementById("reg-password").value.trim();
  const confirm_password = document.getElementById("reg-confirm-password").value.trim();
  const btn = document.getElementById("btn-register-submit");

  // Validatsiyalar
  if (password.length < 8) {
    showToast("Parol kamida 8 ta belgidan iborat bo'lishi shart!", "warning");
    return;
  }

  if (password !== confirm_password) {
    showToast("Kiritilgan parollar bir-biriga mos kelmadi!", "warning");
    return;
  }

  const emailRegex = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
  if (!emailRegex.test(email)) {
    showToast("Email manzili formati noto'g'ri (masalan: admin@example.com)", "warning");
    return;
  }

  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Ro'yxatdan o'tkazilmoqda...`;
  initLucide();

  try {
    const res = await fetch(`${API_BASE}/api/auth/admin/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        username,
        email,
        phone,
        password,
        confirm_password
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Ro'yxatdan o'tishda xatolik yuz berdi");
    }

    adminToken = data.access_token;
    localStorage.setItem("admin_token", adminToken);
    localStorage.setItem("token", adminToken);
    currentAdmin = data.user;

    showToast("Admin sifatida muvaffaqiyatli ro'yxatdan o'tdingiz!", "success");
    updateAdminUIProfile(currentAdmin);
    navigateToView("dashboard");

  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="shield-plus" class="w-4 h-4"></i><span>Admin Sifatida Ro'yxatdan O'tish</span>`;
    initLucide();
  }
}

function handleAdminLogout(notify = true) {
  adminToken = null;
  currentAdmin = null;
  localStorage.removeItem("admin_token");
  localStorage.removeItem("token");
  if (notify) showToast("Tizimdan xavfsiz chiqildi", "info");
  switchAuthView("login");
}

// ================= FORGOT PASSWORD =================
function openForgotPasswordModal() {
  document.getElementById("modal-forgot-password").classList.remove("hidden");
  initLucide();
}

function closeForgotPasswordModal() {
  document.getElementById("modal-forgot-password").classList.add("hidden");
}

async function handleForgotPasswordSubmit(e) {
  e.preventDefault();
  const login = document.getElementById("forgot-login").value.trim();
  const new_password = document.getElementById("forgot-new-password").value.trim();

  if (new_password.length < 8) {
    showToast("Yangi parol kamida 8 ta belgidan iborat bo'lishi kerak", "warning");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/auth/admin/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ login, new_password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Parolni tiklashda xatolik");

    showToast(data.message || "Parol muvaffaqiyatli yangilandi!", "success");
    closeForgotPasswordModal();
    const passInp = document.getElementById("login-password");
    if (passInp) passInp.value = new_password;
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ================= DASHBOARD & CHARTS =================
async function refreshDashboardData() {
  if (!adminToken) return;

  try {
    const res = await fetch(`${API_BASE}/api/admin/dashboard/stats`, {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error("Statistikani yuklashda xatolik");

    const data = await res.json();

    // 1. Stat Metrikalari
    document.getElementById("stat-total-users").textContent = data.total_users;
    document.getElementById("stat-total-orders").textContent = data.total_orders;
    document.getElementById("stat-total-products").textContent = data.total_products;
    document.getElementById("stat-total-revenue").textContent = formatMoney(data.total_revenue);

    // 2. Rollar taqsimoti badge'lari
    const roles = data.role_distribution || {};
    document.getElementById("badge-cnt-admin").textContent = roles.admin || 0;
    document.getElementById("badge-cnt-org").textContent = roles.organizer || 0;
    document.getElementById("badge-cnt-cust").textContent = roles.customer || 0;
    document.getElementById("badge-cnt-ctrl").textContent = roles.controller || 0;

    // 3. Yangi ro'yxatdan o'tganlar jadvali
    renderRecentUsers(data.recent_users || []);

    // 4. Oxirgi faoliyatlar
    renderRecentActivities(data.recent_activities || []);

    // 5. Bildirishnomalar
    renderNotifications(data.notifications || [], data.unread_notifications_count || 0);

    // 6. Grafiklar
    renderCharts(data.chart_data, data.role_distribution);

  } catch (err) {
    console.error("Dashboard refresh error:", err);
  }
}

function renderCharts(chartData, roleDist) {
  if (!chartData) return;

  // A. REVENUE & ORDERS CHART
  const revCtx = document.getElementById("chart-revenue-canvas");
  if (revCtx) {
    if (revenueChart) revenueChart.destroy();

    const isLight = document.documentElement.classList.contains("light");
    const gridColor = isLight ? "rgba(226, 232, 240, 0.8)" : "rgba(255, 255, 255, 0.05)";
    const textColor = isLight ? "#64748b" : "#94a3b8";

    revenueChart = new Chart(revCtx, {
      type: "line",
      data: {
        labels: chartData.labels,
        datasets: [
          {
            label: "Daromad (so'm)",
            data: chartData.revenue,
            borderColor: "#6366f1",
            backgroundColor: "rgba(99, 102, 241, 0.15)",
            borderWidth: 3,
            fill: true,
            tension: 0.4,
            yAxisID: "y"
          },
          {
            label: "Buyurtmalar (dona)",
            data: chartData.orders,
            borderColor: "#10b981",
            backgroundColor: "transparent",
            borderWidth: 2,
            borderDash: [5, 5],
            tension: 0.3,
            yAxisID: "y1"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            labels: { color: textColor, font: { family: "Plus Jakarta Sans", size: 11 } }
          }
        },
        scales: {
          x: {
            grid: { color: gridColor },
            ticks: { color: textColor, font: { size: 10 } }
          },
          y: {
            type: "linear",
            display: true,
            position: "left",
            grid: { color: gridColor },
            ticks: {
              color: textColor,
              callback: val => val >= 1000000 ? (val / 1000000).toFixed(1) + "M" : val
            }
          },
          y1: {
            type: "linear",
            display: true,
            position: "right",
            grid: { drawOnChartArea: false },
            ticks: { color: textColor }
          }
        }
      }
    });
  }

  // B. ROLES DISTRIBUTION DOUGHNUT CHART
  const rolesCtx = document.getElementById("chart-roles-canvas");
  if (rolesCtx && roleDist) {
    if (rolesChart) rolesChart.destroy();

    rolesChart = new Chart(rolesCtx, {
      type: "doughnut",
      data: {
        labels: ["Admin", "Tashkilotchi", "Mijoz", "Nazoratchi"],
        datasets: [{
          data: [roleDist.admin || 1, roleDist.organizer || 1, roleDist.customer || 1, roleDist.controller || 1],
          backgroundColor: ["#6366f1", "#a855f7", "#10b981", "#3b82f6"],
          borderWidth: 0,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "70%",
        plugins: {
          legend: { display: false }
        }
      }
    });
  }
}

function renderRecentUsers(users) {
  const tbody = document.getElementById("dash-recent-users-tbody");
  if (!tbody) return;

  if (users.length === 0) {
    tbody.innerHTML = `<tr><td colspan="3" class="p-4 text-center text-slate-500">Foydalanuvchilar topilmadi</td></tr>`;
    return;
  }

  tbody.innerHTML = users.map(u => {
    const avatar = u.avatar || `https://api.dicebear.com/7.x/bottts/svg?seed=${u.username}`;
    const roleBadges = {
      admin: '<span class="px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 font-bold text-[10px]">ADMIN</span>',
      organizer: '<span class="px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 font-bold text-[10px]">TASHKILOT</span>',
      controller: '<span class="px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-bold text-[10px]">NAZORAT</span>',
      customer: '<span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-bold text-[10px]">MIJOZ</span>',
      user: '<span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-bold text-[10px]">USER</span>'
    };
    const roleHtml = roleBadges[u.role] || roleBadges.customer;
    const timeStr = u.created_at ? new Date(u.created_at).toLocaleDateString("uz-UZ") : "Yangi";

    return `
      <tr class="hover:bg-slate-800/40 transition">
        <td class="p-3.5 flex items-center gap-2.5">
          <img src="${avatar}" class="w-7 h-7 rounded-xl border border-slate-700 bg-slate-900" alt="Avatar">
          <div class="overflow-hidden">
            <span class="font-bold text-white block truncate">${u.name || u.username}</span>
            <span class="text-[10px] text-slate-500 font-mono">@${u.username}</span>
          </div>
        </td>
        <td class="p-3.5">${roleHtml}</td>
        <td class="p-3.5 text-slate-400 font-mono text-[11px]">${timeStr}</td>
      </tr>
    `;
  }).join("");
}

function renderRecentActivities(activities) {
  const container = document.getElementById("dash-recent-activities-list");
  if (!container) return;

  if (activities.length === 0) {
    container.innerHTML = `<div class="text-xs text-slate-500 text-center py-4">Faoliyatlar jurnali bo'sh</div>`;
    return;
  }

  container.innerHTML = activities.map(act => {
    const timeStr = act.created_at ? new Date(act.created_at).toLocaleTimeString("uz-UZ", { hour: "2-digit", minute: "2-digit" }) : "";
    return `
      <div class="flex items-start gap-3 p-2.5 rounded-2xl bg-slate-900/60 border border-slate-800/60 hover:border-slate-700 transition">
        <div class="w-8 h-8 rounded-xl bg-brand-500/10 text-brand-400 flex items-center justify-center flex-shrink-0 mt-0.5 border border-brand-500/20">
          <i data-lucide="check-circle-2" class="w-4 h-4"></i>
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between">
            <span class="font-bold text-xs text-white truncate">${act.action}</span>
            <span class="text-[10px] text-slate-500 font-mono">${timeStr}</span>
          </div>
          <p class="text-[11px] text-slate-400 truncate mt-0.5">${act.details || ''}</p>
          <span class="text-[10px] text-brand-400 font-mono">@${act.username}</span>
        </div>
      </div>
    `;
  }).join("");
  initLucide();
}

function renderNotifications(notifs, unreadCount) {
  const badge = document.getElementById("unread-notif-badge");
  const list = document.getElementById("notifications-list");
  if (badge) {
    if (unreadCount > 0) {
      badge.textContent = unreadCount;
      badge.classList.remove("hidden");
    } else {
      badge.classList.add("hidden");
    }
  }

  if (list) {
    if (notifs.length === 0) {
      list.innerHTML = `<div class="p-3 text-center text-slate-500">Bildirishnomalar yo'q</div>`;
      return;
    }
    list.innerHTML = notifs.map(n => `
      <div class="p-2.5 hover:bg-slate-800/50 transition rounded-xl">
        <div class="font-bold text-slate-200 text-xs">${n.title}</div>
        <div class="text-[11px] text-slate-400 mt-0.5">${n.message}</div>
      </div>
    `).join("");
  }
}

function toggleNotificationDropdown() {
  const panel = document.getElementById("notification-dropdown");
  if (panel) panel.classList.toggle("hidden");
}

async function markAllNotificationsAsRead() {
  if (!adminToken) return;
  try {
    await fetch(`${API_BASE}/api/admin/notifications/mark-all-read`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    const badge = document.getElementById("unread-notif-badge");
    if (badge) badge.classList.add("hidden");
    showToast("Barcha bildirishnomalar o'qilgan deb belgilandi", "success");
  } catch (err) {
    console.error(err);
  }
}

// ================= ALL USERS VIEW =================
async function loadAllUsers() {
  if (!adminToken) return;
  try {
    const res = await fetch(`${API_BASE}/api/admin/users`, {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error("Foydalanuvchilarni yuklashda xatolik");

    allUsersData = await res.json();
    renderUsersTable(allUsersData);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderUsersTable(users) {
  const tbody = document.getElementById("all-users-tbody");
  if (!tbody) return;

  if (users.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-slate-500">Foydalanuvchilar topilmadi</td></tr>`;
    return;
  }

  tbody.innerHTML = users.map(u => {
    const avatar = u.avatar || `https://api.dicebear.com/7.x/bottts/svg?seed=${u.username}`;
    const roleBadges = {
      admin: '<span class="px-2.5 py-1 rounded-full bg-indigo-500/20 text-indigo-400 font-bold text-[11px] border border-indigo-500/30">ADMIN</span>',
      organizer: '<span class="px-2.5 py-1 rounded-full bg-purple-500/20 text-purple-400 font-bold text-[11px] border border-purple-500/30">ORGANIZER</span>',
      controller: '<span class="px-2.5 py-1 rounded-full bg-blue-500/20 text-blue-400 font-bold text-[11px] border border-blue-500/30">CONTROLLER</span>',
      customer: '<span class="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 font-bold text-[11px] border border-emerald-500/30">CUSTOMER</span>',
      user: '<span class="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 font-bold text-[11px] border border-emerald-500/30">USER</span>'
    };
    const roleHtml = roleBadges[u.role] || roleBadges.customer;

    return `
      <tr class="hover:bg-slate-800/40 transition">
        <td class="p-4 font-mono text-slate-500">#${u.id}</td>
        <td class="p-4 flex items-center gap-3">
          <img src="${avatar}" class="w-8 h-8 rounded-xl border border-slate-700 bg-slate-900" alt="Avatar">
          <div>
            <span class="font-bold text-white block">${u.name || u.username}</span>
            <span class="text-xs text-slate-400 font-mono">@${u.username}</span>
          </div>
        </td>
        <td class="p-4 text-slate-300">
          <div>${u.email || '<span class="text-slate-600">-</span>'}</div>
          <div class="text-[11px] text-slate-500 font-mono">${u.phone || ''}</div>
        </td>
        <td class="p-4">${roleHtml}</td>
        <td class="p-4 text-slate-400 text-xs">${u.organization_name || '<span class="text-slate-600">Yo\'q</span>'}</td>
        <td class="p-4 text-right">
          ${u.role !== 'admin' ? `
            <button onclick="deleteUserByAdmin(${u.id}, '${u.username}')" class="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-xl transition" title="Foydalanuvchini o'chirish">
              <i data-lucide="trash-2" class="w-4 h-4"></i>
            </button>
          ` : '<span class="text-[10px] text-slate-600 uppercase font-bold">Himoyalangan</span>'}
        </td>
      </tr>
    `;
  }).join("");
  initLucide();
}

function filterUsersTable() {
  const query = document.getElementById("users-search-input").value.toLowerCase();
  const filtered = allUsersData.filter(u => 
    (u.name && u.name.toLowerCase().includes(query)) ||
    u.username.toLowerCase().includes(query) ||
    (u.email && u.email.toLowerCase().includes(query)) ||
    u.role.toLowerCase().includes(query)
  );
  renderUsersTable(filtered);
}

async function deleteUserByAdmin(userId, username) {
  if (!confirm(`Haqiqatan ham '${username}' foydalanuvchisini o'chirmoqchimisiz?`)) return;

  try {
    const res = await fetch(`${API_BASE}/api/admin/users/${userId}`, {
      method: "DELETE",
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "O'chirishda xatolik");

    showToast(data.message || "Foydalanuvchi o'chirildi", "success");
    loadAllUsers();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ================= AUDIT ACTIVITIES VIEW =================
async function loadAllActivities() {
  if (!adminToken) return;
  try {
    const res = await fetch(`${API_BASE}/api/admin/activities`, {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error("Loglarni yuklashda xatolik");

    const logs = await res.json();
    const container = document.getElementById("full-activities-container");
    if (!container) return;

    if (logs.length === 0) {
      container.innerHTML = `<div class="text-sm text-slate-500 text-center py-8">Xavfsizlik loglari mavjud emas</div>`;
      return;
    }

    container.innerHTML = logs.map(act => {
      const timeStr = act.created_at ? new Date(act.created_at).toLocaleString("uz-UZ") : "";
      return `
        <div class="flex items-start gap-4 p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 hover:border-brand-500/40 transition">
          <div class="w-10 h-10 rounded-2xl bg-brand-500/10 text-brand-400 flex items-center justify-center flex-shrink-0 border border-brand-500/20">
            <i data-lucide="shield" class="w-5 h-5"></i>
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <span class="font-bold text-sm text-white">${act.action}</span>
              <span class="text-xs text-slate-500 font-mono">${timeStr}</span>
            </div>
            <p class="text-xs text-slate-300 mt-1">${act.details || ''}</p>
            <div class="mt-2 flex items-center gap-2">
              <span class="px-2 py-0.5 rounded-lg bg-slate-800 text-[10px] font-mono text-brand-400">Amal qiluvchi: @${act.username}</span>
            </div>
          </div>
        </div>
      `;
    }).join("");
    initLucide();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ================= PROFILE & PASSWORD VIEW =================
async function loadProfileView() {
  if (!adminToken) return;
  try {
    const res = await fetch(`${API_BASE}/api/admin/profile`, {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (!res.ok) return;

    currentAdmin = await res.json();
    updateProfileForm(currentAdmin);
  } catch (err) {
    console.error(err);
  }
}

function updateProfileForm(admin) {
  document.getElementById("profile-card-name").textContent = admin.name || admin.username;
  document.getElementById("profile-card-username").textContent = `@${admin.username}`;
  
  const avatarUrl = admin.avatar || `https://api.dicebear.com/7.x/bottts/svg?seed=${admin.username}`;
  document.getElementById("profile-card-avatar").src = avatarUrl;
  document.getElementById("prof-avatar-val").value = avatarUrl;

  document.getElementById("prof-name").value = admin.name || '';
  document.getElementById("prof-username").value = admin.username;
  document.getElementById("prof-email").value = admin.email || '';
  document.getElementById("prof-phone").value = admin.phone || '';
}

function selectAvatar(seed) {
  const url = `https://api.dicebear.com/7.x/bottts/svg?seed=${seed}`;
  document.getElementById("profile-card-avatar").src = url;
  document.getElementById("prof-avatar-val").value = url;
  showToast("Avatar tanlandi, saqlash tugmasini bosing", "info");
}

async function handleUpdateProfile(e) {
  e.preventDefault();
  const name = document.getElementById("prof-name").value.trim();
  const email = document.getElementById("prof-email").value.trim();
  const phone = document.getElementById("prof-phone").value.trim();
  const avatar = document.getElementById("prof-avatar-val").value;

  try {
    const res = await fetch(`${API_BASE}/api/admin/profile`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${adminToken}`
      },
      body: JSON.stringify({ name, email, phone, avatar })
    });
    const updated = await res.json();
    if (!res.ok) throw new Error(updated.detail || "Profilni yangilashda xatolik");

    currentAdmin = updated;
    updateAdminUIProfile(currentAdmin);
    showToast("Profil ma'lumotlari muvaffaqiyatli saqlandi!", "success");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleChangePassword(e) {
  e.preventDefault();
  const current_password = document.getElementById("pass-current").value.trim();
  const new_password = document.getElementById("pass-new").value.trim();
  const confirm_new_password = document.getElementById("pass-confirm").value.trim();

  if (new_password.length < 8) {
    showToast("Yangi parol kamida 8 ta belgidan iborat bo'lishi kerak", "warning");
    return;
  }

  if (new_password !== confirm_new_password) {
    showToast("Yangi parollar bir-biriga mos kelmadi", "warning");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/admin/profile/change-password`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${adminToken}`
      },
      body: JSON.stringify({ current_password, new_password, confirm_new_password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Parolni o'zgartirishda xatolik");

    showToast(data.message || "Parolingiz muvaffaqiyatli yangilandi!", "success");
    document.getElementById("pass-current").value = "";
    document.getElementById("pass-new").value = "";
    document.getElementById("pass-confirm").value = "";
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ================= TOAST NOTIFICATION UTILITY =================
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  const icons = {
    success: "check-circle",
    error: "alert-triangle",
    warning: "alert-circle",
    info: "info"
  };
  const colors = {
    success: "bg-emerald-950/90 text-emerald-300 border-emerald-500/40 shadow-emerald-500/20",
    error: "bg-red-950/90 text-red-300 border-red-500/40 shadow-red-500/20",
    warning: "bg-amber-950/90 text-amber-300 border-amber-500/40 shadow-amber-500/20",
    info: "bg-indigo-950/90 text-indigo-300 border-indigo-500/40 shadow-indigo-500/20"
  };

  toast.className = `p-4 rounded-2xl border backdrop-blur-xl shadow-xl flex items-center gap-3 transition-all duration-300 pointer-events-auto transform translate-y-2 opacity-0 ${colors[type] || colors.info}`;
  toast.innerHTML = `
    <i data-lucide="${icons[type] || icons.info}" class="w-5 h-5 flex-shrink-0"></i>
    <span class="text-xs font-semibold flex-1">${message}</span>
  `;

  container.appendChild(toast);
  initLucide();

  requestAnimationFrame(() => {
    toast.classList.remove("translate-y-2", "opacity-0");
  });

  setTimeout(() => {
    toast.classList.add("translate-y-2", "opacity-0");
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function formatMoney(amount) {
  return Number(amount || 0).toLocaleString("uz-UZ") + " so'm";
}
