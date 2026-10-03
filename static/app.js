// Tadbir Chiptalari - Frontend Application Logic

const API_BASE = "";
let authToken = localStorage.getItem("token") || null;
let currentUser = null;
let activeReservationTimer = null;
let activeReservation = null;

let currentEventsList = [];
let selectedEventForSeats = null;
let selectedSectorForSeats = null;
let currentlyPickedSeat = null;

// ================= INITIALIZATION =================
document.addEventListener("DOMContentLoaded", async () => {
  if (window.lucide) lucide.createIcons();
  await checkCurrentUser();
  await loadEvents();
  checkExistingReservation();
});

// Toast notification helper
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  const bgColors = {
    success: "bg-emerald-600 text-white border-emerald-400",
    error: "bg-red-600 text-white border-red-400",
    warning: "bg-amber-600 text-white border-amber-400",
    info: "bg-indigo-600 text-white border-indigo-400"
  };

  toast.className = `px-5 py-3 rounded-2xl shadow-2xl border text-sm font-semibold pointer-events-auto transition-all transform duration-300 opacity-0 translate-y-2 flex items-center gap-3 ${bgColors[type] || bgColors.info}`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.remove("opacity-0", "translate-y-2");
  }, 10);

  setTimeout(() => {
    toast.classList.add("opacity-0", "translate-y-2");
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Permission map according to user role
const rolePermissions = {
  guest: ["events"],
  customer: ["events", "my-tickets"],
  organizer: ["organizer", "events"],
  controller: ["controller"],
  admin: ["admin", "organizer", "controller", "events", "my-tickets"]
};

// Navigation between views (Desktop & Mobile)
function navigate(viewName) {
  const userRole = currentUser ? currentUser.role : "guest";
  const allowed = rolePermissions[userRole] || ["events"];

  if (!allowed.includes(viewName)) {
    showToast("Sizda ushbu bo'limga kirish huquqi yo'q! Rolingiz: " + userRole.toUpperCase(), "error");
    const fallback = allowed[0] || "events";
    if (viewName !== fallback) navigate(fallback);
    return;
  }

  document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));

  // Mobile Bottom Nav update
  document.querySelectorAll(".mobile-nav-btn").forEach(b => {
    b.classList.remove("active", "text-indigo-400");
    b.classList.add("text-slate-400");
  });

  const targetView = document.getElementById(`view-${viewName}`);
  const targetNav = document.getElementById(`nav-${viewName}`);
  const targetMobNav = document.getElementById(`mob-nav-${viewName}`);

  if (targetView) targetView.classList.remove("hidden");
  if (targetNav) targetNav.classList.add("active");
  if (targetMobNav) {
    targetMobNav.classList.add("active", "text-indigo-400");
    targetMobNav.classList.remove("text-slate-400");
  }

  // Smooth scroll to top on mobile view switch
  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (window.lucide) lucide.createIcons();

  if (viewName === "events") loadEvents();
  if (viewName === "my-tickets") loadMyTickets();
  if (viewName === "organizer") loadOrganizerEvents();
  if (viewName === "admin") loadAdminUsers();
}

function toggleMobileDrawer() {
  const drawer = document.getElementById("mobile-drawer");
  if (drawer) {
    drawer.classList.toggle("hidden");
    if (window.lucide) lucide.createIcons();
  }
}


// ================= AUTHENTICATION =================
async function checkCurrentUser() {
  if (!authToken) {
    updateAuthUI(null);
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
      headers: { "Authorization": `Bearer ${authToken}` }
    });
    if (res.ok) {
      currentUser = await res.json();
      updateAuthUI(currentUser);
    } else {
      logout(false);
    }
  } catch (err) {
    console.error("Auth check failed:", err);
    logout(false);
  }
}

function updateAuthUI(user) {
  const profileWidget = document.getElementById("user-profile-widget");
  const authButtons = document.getElementById("auth-buttons");
  const usernameEl = document.getElementById("current-username");
  const roleBadgeEl = document.getElementById("current-role-badge");

  const navEvents = document.getElementById("nav-events");
  const navMyTickets = document.getElementById("nav-my-tickets");
  const navOrganizer = document.getElementById("nav-organizer");
  const navController = document.getElementById("nav-controller");
  const navAdmin = document.getElementById("nav-admin");

  // Boshlang'ich holatda barcha maxsus tablarni yashirish
  if (navMyTickets) navMyTickets.classList.add("hidden");
  if (navOrganizer) navOrganizer.classList.add("hidden");
  if (navController) navController.classList.add("hidden");
  if (navAdmin) navAdmin.classList.add("hidden");

  // Mobile Drawer elements
  const drawerUserInfo = document.getElementById("drawer-user-info");
  const drawerUsername = document.getElementById("drawer-username");
  const drawerRoleBadge = document.getElementById("drawer-role-badge");
  const drawerUserInitial = document.getElementById("drawer-user-initial");
  const drawerAuthActions = document.getElementById("drawer-auth-actions");
  const drawerLogoutBtn = document.getElementById("drawer-logout-btn");

  if (user) {
    profileWidget.classList.remove("hidden");
    profileWidget.classList.add("flex");
    authButtons.classList.add("hidden");

    usernameEl.textContent = user.username;
    roleBadgeEl.textContent = `${user.role.toUpperCase()} ${user.organization_name ? `(${user.organization_name})` : ''}`;

    // Update Mobile Drawer
    if (drawerUserInfo) drawerUserInfo.classList.remove("hidden");
    if (drawerUsername) drawerUsername.textContent = user.username;
    if (drawerRoleBadge) drawerRoleBadge.textContent = user.role.toUpperCase();
    if (drawerUserInitial) drawerUserInitial.textContent = (user.username || 'U')[0].toUpperCase();
    if (drawerAuthActions) drawerAuthActions.classList.add("hidden");
    if (drawerLogoutBtn) drawerLogoutBtn.classList.remove("hidden");

    // Faqat tegishli rolga mos tablarni ko'rsatish
    if (user.role === 'customer') {
      if (navEvents) navEvents.classList.remove("hidden");
      if (navMyTickets) navMyTickets.classList.remove("hidden");
    } else if (user.role === 'organizer') {
      if (navOrganizer) navOrganizer.classList.remove("hidden");
      if (navEvents) navEvents.classList.remove("hidden");
    } else if (user.role === 'controller') {
      if (navController) navController.classList.remove("hidden");
      if (navEvents) navEvents.classList.add("hidden");
    } else if (user.role === 'admin') {
      if (navAdmin) navAdmin.classList.remove("hidden");
      if (navOrganizer) navOrganizer.classList.remove("hidden");
      if (navController) navController.classList.remove("hidden");
      if (navEvents) navEvents.classList.remove("hidden");
      if (navMyTickets) navMyTickets.classList.remove("hidden");
    }
  } else {
    profileWidget.classList.add("hidden");
    profileWidget.classList.remove("flex");
    authButtons.classList.remove("hidden");
    currentUser = null;

    // Reset Mobile Drawer
    if (drawerUserInfo) drawerUserInfo.classList.add("hidden");
    if (drawerAuthActions) drawerAuthActions.classList.remove("hidden");
    if (drawerLogoutBtn) drawerLogoutBtn.classList.add("hidden");

    if (navEvents) navEvents.classList.remove("hidden");
  }
}

let isRegisterMode = false;

function togglePasswordVisibility(inputId, iconId) {
  const input = document.getElementById(inputId);
  const icon = document.getElementById(iconId);
  if (!input) return;
  if (input.type === "password") {
    input.type = "text";
    if (icon) {
      icon.setAttribute("data-lucide", "eye-off");
    }
  } else {
    input.type = "password";
    if (icon) {
      icon.setAttribute("data-lucide", "eye");
    }
  }
  if (window.lucide) lucide.createIcons();
}

function switchAuthTab(mode) {
  isRegisterMode = (mode === 'register');
  const tabLogin = document.getElementById("auth-tab-login");
  const tabRegister = document.getElementById("auth-tab-register");
  const title = document.getElementById("auth-modal-title");
  const sub = document.getElementById("auth-modal-subtitle");
  const submitText = document.getElementById("auth-submit-text");
  const submitIcon = document.getElementById("auth-submit-icon");
  const groupName = document.getElementById("auth-group-name");
  const groupContact = document.getElementById("auth-group-contact");
  const groupConfirm = document.getElementById("auth-group-confirm");
  const confirmInput = document.getElementById("auth-confirm-password");

  if (isRegisterMode) {
    if (tabLogin) {
      tabLogin.className = "flex-1 py-2.5 rounded-xl font-bold text-sm transition text-slate-400 hover:text-white flex items-center justify-center gap-2";
    }
    if (tabRegister) {
      tabRegister.className = "flex-1 py-2.5 rounded-xl font-bold text-sm transition bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2";
    }
    if (title) title.textContent = "Ro'yxatdan O'tish";
    if (sub) sub.textContent = "Yangi hisob oching va chiptalarni oson xarid qiling";
    if (submitText) submitText.textContent = "Ro'yxatdan O'tish va Kirish";
    if (submitIcon) submitIcon.className = "fa-solid fa-user-plus";

    if (groupName) groupName.classList.remove("hidden");
    if (groupContact) groupContact.classList.remove("hidden");
    if (groupConfirm) groupConfirm.classList.remove("hidden");
    if (confirmInput) confirmInput.required = true;
  } else {
    if (tabLogin) {
      tabLogin.className = "flex-1 py-2.5 rounded-xl font-bold text-sm transition bg-indigo-600 text-white shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2";
    }
    if (tabRegister) {
      tabRegister.className = "flex-1 py-2.5 rounded-xl font-bold text-sm transition text-slate-400 hover:text-white flex items-center justify-center gap-2";
    }
    if (title) title.textContent = "Tizimga Kirish";
    if (sub) sub.textContent = "Shaxsiy hisobingizga kiring";
    if (submitText) submitText.textContent = "Kirish";
    if (submitIcon) submitIcon.className = "fa-solid fa-right-to-bracket";

    if (groupName) groupName.classList.add("hidden");
    if (groupContact) groupContact.classList.add("hidden");
    if (groupConfirm) groupConfirm.classList.add("hidden");
    if (confirmInput) {
      confirmInput.required = false;
      confirmInput.value = "";
    }
  }
  if (window.lucide) lucide.createIcons();
}

function openAuthModal(mode = 'login') {
  switchAuthTab(mode);
  const modal = document.getElementById("auth-modal");
  if (modal) modal.classList.remove("hidden");
  if (window.lucide) lucide.createIcons();
}

function closeAuthModal() {
  document.getElementById("auth-modal").classList.add("hidden");
}

function toggleAuthMode() {
  switchAuthTab(isRegisterMode ? 'login' : 'register');
}

function quickFillLogin(username, password) {
  const userInp = document.getElementById("auth-username");
  const passInp = document.getElementById("auth-password");
  if (userInp) userInp.value = username;
  if (passInp) passInp.value = password;
  switchAuthTab('login');
}

async function attemptLogin(username, password) {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password })
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || "Login yoki parol noto'g'ri");
  }

  authToken = data.access_token;
  localStorage.setItem("token", authToken);
  currentUser = data.user;
  updateAuthUI(currentUser);
  closeAuthModal();
  showToast(`Xush kelibsiz, ${currentUser.username}! (${currentUser.role.toUpperCase()})`, "success");
  checkExistingReservation();

  // Rolga qarab tegishli boshqaruv bo'limiga avtomatik yo'naltirish
  if (currentUser.role === 'admin') {
    window.location.href = '/secure-admin-portal-xyz';
    return;
  } else if (currentUser.role === 'organizer') {
    navigate('organizer');
  } else if (currentUser.role === 'controller') {
    navigate('controller');
  } else {
    navigate('events');
  }
}

async function handleAuthSubmit(e) {
  e.preventDefault();
  const username = document.getElementById("auth-username").value.trim();
  const password = document.getElementById("auth-password").value.trim();

  if (!username) {
    showToast("Iltimos, foydalanuvchi nomini (login) kiriting", "warning");
    return;
  }

  if (username.length < 3) {
    showToast("Foydalanuvchi nomi kamida 3 ta belgidan iborat bo'lishi kerak", "warning");
    return;
  }

  if (!password) {
    showToast("Iltimos, parolni kiriting", "warning");
    return;
  }

  if (password.length < 6) {
    showToast("Parol kamida 6 ta belgidan iborat bo'lishi kerak", "warning");
    return;
  }

  try {
    if (isRegisterMode) {
      const name = (document.getElementById("auth-name")?.value || "").trim();
      const phone = (document.getElementById("auth-phone")?.value || "").trim();
      const email = (document.getElementById("auth-email")?.value || "").trim();
      const confirmPassword = (document.getElementById("auth-confirm-password")?.value || "").trim();

      if (password !== confirmPassword) {
        showToast("Kiritilgan parollar bir-biriga mos kelmadi! Qaytadan tekshiring.", "error");
        return;
      }

      if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showToast("Noto'g'ri email formati kiritildi", "warning");
        return;
      }

      // Agar admin yoki tizim rollari bo'lsa to'g'ridan-to'g'ri kirish
      if (['admin', 'art_palace', 'gate_controller'].includes(username.toLowerCase())) {
        await attemptLogin(username, password);
        return;
      }

      const payload = {
        username: username,
        password: password,
        name: name || undefined,
        phone: phone || undefined,
        email: email || undefined,
        confirm_password: confirmPassword
      };

      // Yangi ro'yxatdan o'tish
      const res = await fetch(`${API_BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (!res.ok) {
        // Agar login band bo'lsa
        if (res.status === 400 && (data.detail?.includes("band") || data.detail?.includes("mavjud"))) {
          try {
            await attemptLogin(username, password);
            return;
          } catch (loginErr) {
            throw new Error("Ushbu login band va parol mos kelmadi. Iltimos boshqa login tanlang yoki 'Kirish' orqali kiring.");
          }
        }
        throw new Error(data.detail || "Ro'yxatdan o'tishda xatolik");
      }

      showToast("Ro'yxatdan muvaffaqiyatli o'tdingiz! Xush kelibsiz.", "success");
      await attemptLogin(username, password);
    } else {
      await attemptLogin(username, password);
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

function logout(notify = true) {
  authToken = null;
  currentUser = null;
  localStorage.removeItem("token");
  updateAuthUI(null);
  navigate('events');
  if (notify) showToast("Tizimdan chiqildi", "info");
}

// ================= EVENTS VITRINA =================
async function loadEvents() {
  try {
    const res = await fetch(`${API_BASE}/api/events`);
    if (!res.ok) throw new Error("Tadbirlarni yuklab bo'lmadi");
    currentEventsList = await res.json();

    const grid = document.getElementById("events-grid");
    if (!grid) return;

    if (currentEventsList.length === 0) {
      grid.innerHTML = `
        <div class="col-span-full py-16 text-center text-slate-400">
          <i data-lucide="calendar-x" class="w-12 h-12 mx-auto mb-3 opacity-40"></i>
          <p class="text-base font-semibold">Hozircha faol tadbirlar mavjud emas</p>
        </div>
      `;
      if (window.lucide) lucide.createIcons();
      return;
    }

    grid.innerHTML = currentEventsList.map(ev => {
      const dateObj = new Date(ev.date);
      const dateStr = dateObj.toLocaleDateString("uz-UZ", { month: "short", day: "numeric", year: "numeric" });
      const timeStr = dateObj.toLocaleTimeString("uz-UZ", { hour: "2-digit", minute: "2-digit" });

      const minPrice = ev.sectors && ev.sectors.length > 0
        ? Math.min(...ev.sectors.map(s => s.price)).toLocaleString("uz-UZ")
        : "0";

      return `
        <div class="bg-cardBg rounded-3xl border border-borderGlass overflow-hidden flex flex-col hover:border-indigo-500/40 transition-all duration-300 shadow-xl group">
          <div class="h-44 bg-gradient-to-tr from-indigo-900/80 via-purple-900/40 to-slate-900 p-6 flex flex-col justify-between relative overflow-hidden">
            <div class="absolute -right-8 -top-8 w-36 h-36 bg-indigo-500/20 rounded-full blur-2xl group-hover:scale-125 transition-transform duration-500"></div>
            <div class="flex items-center justify-between relative z-10">
              <span class="px-3 py-1 rounded-full bg-slate-900/80 backdrop-blur-md border border-white/10 text-xs font-bold text-indigo-300 flex items-center gap-1.5">
                <i data-lucide="clock" class="w-3.5 h-3.5"></i> ${timeStr}
              </span>
              <span class="px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-xs font-bold text-emerald-300">
                ${minPrice} so'mdan
              </span>
            </div>
            <div class="relative z-10">
              <div class="text-xs text-indigo-200/80 font-semibold mb-1 flex items-center gap-1">
                <i data-lucide="calendar" class="w-3.5 h-3.5"></i> ${dateStr}
              </div>
              <h3 class="text-xl font-extrabold text-white leading-snug line-clamp-2">${ev.title}</h3>
            </div>
          </div>

          <div class="p-6 flex-1 flex flex-col justify-between space-y-4">
            <div>
              <div class="flex items-center gap-2 text-xs text-slate-400 mb-2">
                <i data-lucide="map-pin" class="w-4 h-4 text-pink-400 flex-shrink-0"></i>
                <span class="truncate">${ev.location || "Toshkent"}</span>
              </div>
              <p class="text-xs text-slate-400 line-clamp-2">${ev.description || "Tadbir haqida ma'lumot kiritilmagan"}</p>
            </div>

            <!-- SECTORS SUMMARY PILLS -->
            <div class="flex flex-wrap gap-1.5">
              ${(ev.sectors || []).map(s => `
                <span class="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-slate-300">
                  ${s.name}: <strong class="text-indigo-400">${s.available_seats || 0}</strong> bo'sh
                </span>
              `).join('')}
            </div>

            <button onclick="openSeatMapModal(${ev.id})" class="w-full py-3 rounded-2xl bg-indigo-600 hover:bg-indigo-500 font-bold text-sm text-white shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 transition">
              <i data-lucide="armchair" class="w-4 h-4"></i> Joy Tanlash & Xarid
            </button>
          </div>
        </div>
      `;
    }).join('');

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error("loadEvents xato:", err);
  }
}

// ================= SEAT MAP & 10-MIN RESERVATION =================
async function openSeatMapModal(eventId) {
  const ev = currentEventsList.find(e => e.id === eventId);
  if (!ev) return;

  selectedEventForSeats = ev;
  currentlyPickedSeat = null;

  document.getElementById("seat-modal-event-title").textContent = ev.title;
  document.getElementById("seat-modal-event-sub").textContent = `${ev.location} | Joyni 10 daqiqaga qulflang`;
  document.getElementById("selected-seat-desc").textContent = "Hech qaysi joy tanlanmagan";
  document.getElementById("selected-seat-price").textContent = "0 so'm";
  document.getElementById("reserve-seat-btn").disabled = true;

  // Render sector tabs
  const sectorTabs = document.getElementById("seat-sector-tabs");
  if (!ev.sectors || ev.sectors.length === 0) {
    sectorTabs.innerHTML = `<span class="text-xs text-slate-400">Bu tadbirda sektorlar mavjud emas</span>`;
    document.getElementById("seats-grid-container").innerHTML = `<div class="text-slate-400 text-xs">Joylar yo'q</div>`;
    document.getElementById("seat-map-modal").classList.remove("hidden");
    return;
  }

  sectorTabs.innerHTML = ev.sectors.map((sec, idx) => `
    <button onclick="selectSectorForSeats(${sec.id})" id="sec-tab-${sec.id}" class="px-3.5 py-1.5 rounded-xl text-xs font-bold border transition ${idx === 0 ? 'bg-indigo-600 border-indigo-400 text-white' : 'bg-slate-900 border-slate-700 text-slate-300 hover:bg-slate-800'}">
      ${sec.name} (${sec.price.toLocaleString()} so'm)
    </button>
  `).join('');

  document.getElementById("seat-map-modal").classList.remove("hidden");
  if (window.lucide) lucide.createIcons();

  // Load seats of first sector
  await selectSectorForSeats(ev.sectors[0].id);
}

function closeSeatMapModal() {
  document.getElementById("seat-map-modal").classList.add("hidden");
}

async function selectSectorForSeats(sectorId) {
  selectedSectorForSeats = selectedEventForSeats.sectors.find(s => s.id === sectorId);
  if (!selectedSectorForSeats) return;

  // Update tabs highlight
  selectedEventForSeats.sectors.forEach(s => {
    const tab = document.getElementById(`sec-tab-${s.id}`);
    if (tab) {
      if (s.id === sectorId) {
        tab.className = "px-3.5 py-1.5 rounded-xl text-xs font-bold border transition bg-indigo-600 border-indigo-400 text-white";
      } else {
        tab.className = "px-3.5 py-1.5 rounded-xl text-xs font-bold border transition bg-slate-900 border-slate-700 text-slate-300 hover:bg-slate-800";
      }
    }
  });

  const container = document.getElementById("seats-grid-container");
  container.innerHTML = `<div class="col-span-full py-8 text-center text-slate-400 text-xs">Joylar yuklanmoqda...</div>`;

  try {
    const res = await fetch(`${API_BASE}/api/events/sectors/${sectorId}/seats`);
    if (!res.ok) throw new Error("Joylarni olib bo'lmadi");
    const seats = await res.json();

    if (seats.length === 0) {
      container.innerHTML = `<div class="col-span-full py-8 text-center text-slate-400 text-xs">Ushbu sektorda hozircha joylar kiritilmagan</div>`;
      return;
    }

    container.innerHTML = seats.map(s => {
      let statusClass = "seat-available";
      let titleTooltip = `Joy: ${s.seat_number} - Bo'sh (${selectedSectorForSeats.price.toLocaleString()} so'm)`;

      if (s.status === "reserved") {
        statusClass = "seat-reserved";
        titleTooltip = `Joy: ${s.seat_number} - 10 daqiqaga band qilingan`;
      } else if (s.status === "sold") {
        statusClass = "seat-sold";
        titleTooltip = `Joy: ${s.seat_number} - Sotilgan`;
      }

      return `
        <div onclick="pickSeat(${s.id}, '${s.seat_number}', '${s.status}')" id="seat-node-${s.id}" class="seat-item ${statusClass}" title="${titleTooltip}">
          <span>${s.seat_number}</span>
        </div>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = `<div class="col-span-full py-8 text-center text-red-400 text-xs">${err.message}</div>`;
  }
}

function pickSeat(seatId, seatNumber, status) {
  if (status !== "available") {
    if (status === "reserved") showToast("Ushbu joy ayni paytda boshqa mijoz tomonidan 10 daqiqaga band qilingan!", "warning");
    if (status === "sold") showToast("Ushbu joy allaqachon sotilgan!", "error");
    return;
  }

  // Clear previous pick
  if (currentlyPickedSeat) {
    const prevNode = document.getElementById(`seat-node-${currentlyPickedSeat.id}`);
    if (prevNode) prevNode.classList.remove("seat-selected");
  }

  currentlyPickedSeat = {
    id: seatId,
    number: seatNumber,
    sector: selectedSectorForSeats,
    event: selectedEventForSeats
  };

  const node = document.getElementById(`seat-node-${seatId}`);
  if (node) node.classList.add("seat-selected");

  document.getElementById("selected-seat-desc").textContent = `${selectedSectorForSeats.name} (Joy: ${seatNumber})`;
  document.getElementById("selected-seat-price").textContent = `${selectedSectorForSeats.price.toLocaleString()} so'm`;
  document.getElementById("reserve-seat-btn").disabled = false;
}

// RESERVE SEAT (10 MINUTES HOLD)
async function handleReserveSeatClick() {
  if (!currentlyPickedSeat) {
    showToast("Iltimos, avval sahna chizmasidan bo'sh joyni tanlang!", "warning");
    return;
  }

  // Agar foydalanuvchi tizimga kirmagan bo'lsa, to'siqsiz xarid uchun mijoz hisobini avtomatik faollashtiramiz
  if (!currentUser || !authToken) {
    try {
      const autoRes = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: "mijoz1", password: "mijoz123" })
      });
      if (autoRes.ok) {
        const autoData = await autoRes.json();
        authToken = autoData.access_token;
        localStorage.setItem("token", authToken);
        currentUser = autoData.user;
        updateAuthUI(currentUser);
      }
    } catch (authErr) {
      console.warn("Auto customer login:", authErr);
    }
  }

  if (!currentUser || !authToken) {
    showToast("Iltimos, joyni band qilish uchun tizimga kiring!", "warning");
    openAuthModal('login');
    return;
  }

  const btn = document.getElementById("reserve-seat-btn");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> 10 daqiqaga band qilinmoqda...`;
    if (window.lucide) lucide.createIcons();
  }

  try {
    const res = await fetch(`${API_BASE}/api/reservations`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${authToken}`
      },
      body: JSON.stringify({ seat_id: currentlyPickedSeat.id })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Joyni band qilib bo'lmadi");
    }

    closeSeatMapModal();
    showToast(`Joy muvaffaqiyatli 10 daqiqaga band qilindi! (Joy: ${data.seat_number || currentlyPickedSeat.number})`, "success");

    // Start payment modal & countdown
    openPaymentModal(data);
  } catch (err) {
    showToast(err.message, "error");
    if (selectedSectorForSeats) {
      selectSectorForSeats(selectedSectorForSeats.id);
    }
  } finally {
    const btn = document.getElementById("reserve-seat-btn");
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="lock" class="w-4 h-4"></i> 10 Daqiqaga Band Qilish`;
      if (window.lucide) lucide.createIcons();
    }
  }
}

// ================= PAYMENT MODAL & IDEMPOTENCY =================
function openPaymentModal(reservationData) {
  activeReservation = reservationData;

  document.getElementById("pay-event-title").textContent = reservationData.event_title || "Tadbir";
  document.getElementById("pay-seat-desc").textContent = `${reservationData.sector_name} (Joy: ${reservationData.seat_number})`;
  document.getElementById("pay-amount").textContent = `${(reservationData.price || 0).toLocaleString()} so'm`;

  // Generate unique idempotency key
  const uniqueKey = `idemp_tx_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
  document.getElementById("pay-idempotency-key").textContent = uniqueKey;

  // Start live countdown timer
  startReservationCountdown(reservationData.seconds_left || 600);

  document.getElementById("payment-modal").classList.remove("hidden");
  updateActiveResBanner();
}

function closePaymentModal() {
  document.getElementById("payment-modal").classList.add("hidden");
}

function startReservationCountdown(secondsTotal) {
  if (activeReservationTimer) clearInterval(activeReservationTimer);

  let seconds = secondsTotal;
  const timerEl = document.getElementById("payment-timer");

  const updateDisplay = () => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    const formatted = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    if (timerEl) timerEl.textContent = formatted;

    const bannerText = document.getElementById("res-banner-text");
    if (bannerText && activeReservation) {
      bannerText.textContent = `Joy: ${activeReservation.seat_number} | Qolgan vaqt: ${formatted}`;
    }

    if (seconds <= 0) {
      clearInterval(activeReservationTimer);
      showToast("10 daqiqalik rezervatsiya muddati tugadi! Joy avtomatik bo'shatildi.", "error");
      closePaymentModal();
      activeReservation = null;
      updateActiveResBanner();
      loadEvents();
    }
    seconds--;
  };

  updateDisplay();
  activeReservationTimer = setInterval(updateDisplay, 1000);
}

function updateActiveResBanner() {
  const banner = document.getElementById("active-res-banner");
  if (!banner) return;
  if (activeReservation) {
    banner.classList.remove("hidden");
  } else {
    banner.classList.add("hidden");
  }
}

async function checkExistingReservation() {
  if (!currentUser) return;
  try {
    const res = await fetch(`${API_BASE}/api/reservations/my`, {
      headers: { "Authorization": `Bearer ${authToken}` }
    });
    if (res.ok) {
      const list = await res.json();
      if (list.length > 0) {
        activeReservation = list[0];
        startReservationCountdown(activeReservation.seconds_left);
        updateActiveResBanner();
      } else {
        activeReservation = null;
        updateActiveResBanner();
      }
    }
  } catch (err) {
    console.error("checkExistingReservation xato:", err);
  }
}

function openPaymentModalForActiveRes() {
  if (activeReservation) {
    openPaymentModal(activeReservation);
  }
}

async function handleCancelCurrentReservation() {
  if (!activeReservation) return;
  try {
    const res = await fetch(`${API_BASE}/api/reservations/${activeReservation.id}`, {
      method: "DELETE",
      headers: { "Authorization": `Bearer ${authToken}` }
    });
    if (res.ok) {
      showToast("Rezervatsiya bekor qilindi, joy bo'shatildi.", "info");
      clearInterval(activeReservationTimer);
      activeReservation = null;
      closePaymentModal();
      updateActiveResBanner();
      loadEvents();
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

// EXECUTE IDEMPOTENT MOCK PAYMENT
async function executeMockPayment() {
  if (!activeReservation) return;

  const idempotencyKey = document.getElementById("pay-idempotency-key").textContent.trim();
  const amount = activeReservation.price || 0;

  const btn = document.getElementById("pay-submit-btn");
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-5 h-5 animate-spin"></i> To'lov qayta ishlanmoqda...`;

  try {
    const res = await fetch(`${API_BASE}/api/payments/callback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reservation_id: activeReservation.id,
        idempotency_key: idempotencyKey,
        amount: amount
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "To'lov qabul qilinmadi");
    }

    if (data.is_duplicate_call) {
      showToast("Idempotent javob: Ushbu so'rov allaqachon bajarilgan, takroriy mablag' olinmadi!", "warning");
    } else {
      showToast("To'lov muvaffaqiyatli qabul qilindi va elektron chipta yaratildi!", "success");
    }

    clearInterval(activeReservationTimer);
    activeReservation = null;
    updateActiveResBanner();
    closePaymentModal();

    // Store last ticket token for easy testing in Controller
    if (data.ticket && data.ticket.token) {
      localStorage.setItem("lastTicketToken", data.ticket.token);
    }

    navigate('my-tickets');
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="check-circle" class="w-5 h-5"></i> To'lovni Tasdiqlash`;
    if (window.lucide) lucide.createIcons();
  }
}

// ================= CUSTOMER TICKETS VIEW =================
async function loadMyTickets() {
  if (!currentUser) {
    showToast("Chiptalaringizni ko'rish uchun avval tizimga kiring!", "warning");
    openAuthModal('login');
    return;
  }

  const container = document.getElementById("my-tickets-container");
  container.innerHTML = `<div class="col-span-full py-16 text-center text-slate-400"><i data-lucide="loader-2" class="w-8 h-8 animate-spin mx-auto mb-2"></i>Chiptalar yuklanmoqda...</div>`;
  if (window.lucide) lucide.createIcons();

  try {
    const res = await fetch(`${API_BASE}/api/tickets/my-tickets`, {
      headers: { "Authorization": `Bearer ${authToken}` }
    });
    if (!res.ok) throw new Error("Chiptalarni yuklab bo'lmadi");
    const tickets = await res.json();

    if (tickets.length === 0) {
      container.innerHTML = `
        <div class="col-span-full py-16 text-center text-slate-400">
          <i data-lucide="ticket" class="w-12 h-12 mx-auto mb-3 opacity-40"></i>
          <p class="text-base font-semibold">Sizda hali xarid qilingan chiptalar mavjud emas</p>
          <button onclick="navigate('events')" class="mt-4 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition">Tadbirlarni Ko'rish</button>
        </div>
      `;
      if (window.lucide) lucide.createIcons();
      return;
    }

    container.innerHTML = tickets.map((t, idx) => {
      const dateObj = t.event_date ? new Date(t.event_date) : new Date();
      const dateStr = dateObj.toLocaleDateString("uz-UZ", { month: "short", day: "numeric", year: "numeric" });
      const timeStr = dateObj.toLocaleTimeString("uz-UZ", { hour: "2-digit", minute: "2-digit" });

      let statusBadge = `<span class="px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">FAOL</span>`;
      if (t.status === "used") {
        statusBadge = `<span class="px-2.5 py-1 rounded-full text-[11px] font-bold bg-slate-700 text-slate-300 border border-slate-600">ISHLATILGAN</span>`;
      } else if (t.status === "cancelled") {
        statusBadge = `<span class="px-2.5 py-1 rounded-full text-[11px] font-bold bg-red-500/20 text-red-300 border border-red-500/30">BEKOR QILINGAN</span>`;
      }

      return `
        <div class="ticket-card p-6 flex flex-col justify-between">
          <div class="ticket-cutout-left"></div>
          <div class="ticket-cutout-right"></div>

          <!-- TOP PART -->
          <div>
            <div class="flex items-center justify-between mb-3">
              <span class="text-xs uppercase font-extrabold tracking-widest text-indigo-400">ELEKTRON CHIPTA</span>
              ${statusBadge}
            </div>
            <h3 class="text-xl font-extrabold text-white mb-1">${t.event_title}</h3>
            <p class="text-xs text-slate-400 mb-4 flex items-center gap-1">
              <i data-lucide="map-pin" class="w-3.5 h-3.5 text-pink-400"></i> ${t.location || "Toshkent"}
            </p>

            <div class="grid grid-cols-3 gap-2 p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center mb-4">
              <div>
                <div class="text-[10px] text-slate-400 uppercase">Sektor</div>
                <div class="text-xs font-bold text-white truncate">${t.sector_name}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-400 uppercase">Joy Raqami</div>
                <div class="text-xs font-extrabold text-indigo-300">${t.seat_number}</div>
              </div>
              <div>
                <div class="text-[10px] text-slate-400 uppercase">Narxi</div>
                <div class="text-xs font-bold text-emerald-400">${(t.price || 0).toLocaleString()} so'm</div>
              </div>
            </div>
          </div>

          <!-- DIVIDER -->
          <div class="border-b border-dashed border-slate-700 my-2"></div>

          <!-- BOTTOM PART WITH QR CODE -->
          <div class="flex items-center justify-between pt-2">
            <div>
              <div class="text-[11px] text-slate-400">Sana & Vaqt:</div>
              <div class="text-xs font-bold text-slate-200 mb-2">${dateStr} | ${timeStr}</div>

              <div class="text-[10px] text-slate-400">Token ID (Bir martalik):</div>
              <div class="text-[11px] font-mono text-indigo-400 flex items-center gap-1 cursor-pointer hover:underline" onclick="copyToken('${t.token}')" title="Nusxalash">
                <span class="truncate max-w-[160px]">${t.token}</span>
                <i data-lucide="copy" class="w-3 h-3 flex-shrink-0"></i>
              </div>
            </div>

            <!-- QR CODE BOX -->
            <div id="qrcode-${idx}" class="qr-box flex-shrink-0"></div>
          </div>
        </div>
      `;
    }).join('');

    if (window.lucide) lucide.createIcons();

    // Render QR codes into each ticket
    tickets.forEach((t, idx) => {
      const qrEl = document.getElementById(`qrcode-${idx}`);
      if (qrEl && window.QRCode) {
        new QRCode(qrEl, {
          text: t.token,
          width: 80,
          height: 80,
          colorDark: "#000000",
          colorLight: "#ffffff",
          correctLevel: QRCode.CorrectLevel.M
        });
      }
    });

  } catch (err) {
    container.innerHTML = `<div class="col-span-full py-16 text-center text-red-400">${err.message}</div>`;
  }
}

function copyToken(token) {
  navigator.clipboard.writeText(token);
  showToast("Chipta tokeni nusxalandi!", "info");
}

// ================= CONTROLLER (SCANNER) =================
function pasteLastTicketToken() {
  const last = localStorage.getItem("lastTicketToken");
  if (last) {
    document.getElementById("scan-token-input").value = last;
    showToast("Oxirgi xarid qilingan chipta tokeni qo'yildi", "info");
  } else {
    showToast("Oxirgi token topilmadi, iltimos token nusxasini kiriting", "warning");
  }
}

async function handleVerifyTicket() {
  if (!currentUser) {
    showToast("Chiptani tekshirish uchun Tekshiruvchi (Controller) yoki Admin hisobiga kiring!", "warning");
    openAuthModal('login');
    return;
  }

  const tokenInput = document.getElementById("scan-token-input");
  const token = tokenInput.value.trim();
  if (!token) {
    showToast("Iltimos, chipta tokenini kiriting!", "warning");
    return;
  }

  const resultCard = document.getElementById("scan-result-card");
  resultCard.classList.remove("hidden");
  resultCard.innerHTML = `<div class="text-center text-slate-400 py-6"><i data-lucide="loader-2" class="w-8 h-8 animate-spin mx-auto mb-2"></i>Tekshirilmoqda...</div>`;
  if (window.lucide) lucide.createIcons();

  try {
    const res = await fetch(`${API_BASE}/api/tickets/verify`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${authToken}`
      },
      body: JSON.stringify({ token: token })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Tekshirishda xatolik");
    }

    if (data.valid) {
      // SUCCESS (Active chipta ishlatildi)
      resultCard.className = "rounded-3xl p-8 border border-emerald-500/50 bg-emerald-950/40 shadow-[0_0_40px_rgba(16,185,129,0.3)] transition-all";
      resultCard.innerHTML = `
        <div class="flex flex-col sm:flex-row items-center gap-6">
          <div class="w-20 h-20 rounded-full bg-emerald-500/20 text-emerald-400 border-2 border-emerald-400 flex items-center justify-center animate-bounce">
            <i data-lucide="check" class="w-10 h-10"></i>
          </div>
          <div class="text-center sm:text-left flex-1">
            <span class="inline-block px-3 py-1 rounded-full bg-emerald-500 text-black font-extrabold text-xs uppercase mb-2">Muvaffaqiyatli</span>
            <h3 class="text-2xl font-extrabold text-white mb-1">${data.message}</h3>
            <p class="text-xs text-emerald-300/80 mb-4">Bir martalik token qabul qilindi va chipta 'used' (ishlatilgan) holatiga o'tkazildi.</p>

            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-900/80 p-4 rounded-2xl border border-emerald-500/20 text-xs">
              <div>
                <span class="text-slate-400 text-[10px] uppercase">Tadbir:</span>
                <div class="font-bold text-white truncate">${data.ticket.event_title}</div>
              </div>
              <div>
                <span class="text-slate-400 text-[10px] uppercase">Sektor:</span>
                <div class="font-bold text-indigo-300">${data.ticket.sector_name}</div>
              </div>
              <div>
                <span class="text-slate-400 text-[10px] uppercase">Joy:</span>
                <div class="font-bold text-emerald-400 text-sm">${data.ticket.seat_number}</div>
              </div>
              <div>
                <span class="text-slate-400 text-[10px] uppercase">Mijoz:</span>
                <div class="font-bold text-white truncate">${data.ticket.attendee_name}</div>
              </div>
            </div>
          </div>
        </div>
      `;
      showToast("KIRISHGA RUXSAT BERILDI!", "success");
    } else {
      // REJECTED (Already used or cancelled)
      resultCard.className = "rounded-3xl p-8 border border-red-500/50 bg-red-950/40 shadow-[0_0_40px_rgba(239,68,68,0.3)] transition-all";
      resultCard.innerHTML = `
        <div class="flex flex-col sm:flex-row items-center gap-6">
          <div class="w-20 h-20 rounded-full bg-red-500/20 text-red-400 border-2 border-red-400 flex items-center justify-center">
            <i data-lucide="x" class="w-10 h-10"></i>
          </div>
          <div class="text-center sm:text-left flex-1">
            <span class="inline-block px-3 py-1 rounded-full bg-red-500 text-white font-extrabold text-xs uppercase mb-2">RAD ETILDI</span>
            <h3 class="text-2xl font-extrabold text-white mb-1">${data.message}</h3>
            <p class="text-xs text-red-300/80 mb-2">Chipta holati: <strong class="uppercase">${data.status}</strong></p>
            ${data.ticket ? `
              <div class="text-xs text-slate-300 bg-slate-900/80 p-3 rounded-xl border border-red-500/20">
                Tadbir: <strong>${data.ticket.event_title}</strong> | Joy: <strong>${data.ticket.seat_number}</strong> (${data.ticket.sector_name})
              </div>
            ` : ''}
            ${(currentUser && currentUser.role === 'admin' && data.status === 'used') ? `
              <div class="mt-4 pt-3 border-t border-red-500/20">
                <button onclick="adminReactivateTicket('${token}')" class="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-extrabold text-xs transition shadow-lg inline-flex items-center gap-2">
                  <i data-lucide="rotate-ccw" class="w-4 h-4"></i> 👑 Admin: Chiptani Qayta Faollashtirish (Reactivate)
                </button>
              </div>
            ` : ''}
          </div>
        </div>
      `;
      showToast(data.message, "error");
    }

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    resultCard.className = "rounded-3xl p-8 border border-red-500/50 bg-red-950/40";
    resultCard.innerHTML = `
      <div class="text-center">
        <i data-lucide="alert-triangle" class="w-10 h-10 text-red-400 mx-auto mb-2"></i>
        <h4 class="text-lg font-bold text-white">${err.message}</h4>
      </div>
    `;
    if (window.lucide) lucide.createIcons();
    showToast(err.message, "error");
  }
}

// ================= ORGANIZER & REPORTS =================
let currentOrganizerEventsList = [];

async function loadOrganizerEvents() {
  if (!currentUser) {
    showToast("Tashkilotchi panelini ko'rish uchun Tashkilotchi yoki Admin sifatida kiring!", "warning");
    openAuthModal('login');
    return;
  }

  const select = document.getElementById("report-event-select");
  const genSecSelect = document.getElementById("gen-seat-sector-select");
  const filterSelect = document.getElementById("report-sector-filter");

  try {
    // Qat'iy qoida: Faqat joriy tashkilotchining O'Z tadbirlarini olish
    // Boshqa tashkilotchilarning tadbirlari bu yerda chiqmaydi va o'zgartirilmaydi!
    const res = await fetch(`${API_BASE}/api/events/organizer/my-events`, {
      headers: { "Authorization": `Bearer ${authToken}` }
    });
    if (!res.ok) throw new Error("Tadbirlarni olib bo'lmadi");
    currentOrganizerEventsList = await res.json();

    if (currentOrganizerEventsList.length === 0) {
      select.innerHTML = `<option value="">Sizda hali yaratilgan tadbirlar mavjud emas</option>`;
      if (filterSelect) filterSelect.innerHTML = `<option value="">Sektorlar yo'q</option>`;
      if (genSecSelect) genSecSelect.innerHTML = `<option value="">Sektorlar yo'q</option>`;
      const tbody = document.getElementById("sector-report-tbody");
      if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="p-6 text-center text-slate-500">Sizda hali tadbirlar mavjud emas. Yuqoridagi "Yangi Tadbir Yaratish" tugmasi orqali o'z tadbiringizni e'lon qiling.</td></tr>`;
      document.getElementById("rep-revenue").textContent = "0 so'm";
      document.getElementById("rep-occupancy").textContent = "0%";
      document.getElementById("rep-sold").textContent = "0 / 0";
      document.getElementById("rep-checked-in").textContent = "0 ta (0%)";
      return;
    }

    select.innerHTML = currentOrganizerEventsList.map(ev => `
      <option value="${ev.id}">${ev.title} (${new Date(ev.date).toLocaleDateString()})</option>
    `).join('');

    onReportEventChange();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function onReportEventChange() {
  const select = document.getElementById("report-event-select");
  const eventId = parseInt(select.value);
  const ev = currentOrganizerEventsList.find(e => e.id === eventId);

  const filterSelect = document.getElementById("report-sector-filter");
  const genSecSelect = document.getElementById("gen-seat-sector-select");

  if (ev && ev.sectors && ev.sectors.length > 0) {
    filterSelect.innerHTML = `<option value="">Barcha sektorlar</option>` + ev.sectors.map(s => `
      <option value="${s.id}">${s.name} (${s.price.toLocaleString()} so'm)</option>
    `).join('');

    genSecSelect.innerHTML = ev.sectors.map(s => `
      <option value="${s.id}">${s.name}</option>
    `).join('');
  } else {
    filterSelect.innerHTML = `<option value="">Sektorlar yo'q</option>`;
    genSecSelect.innerHTML = `<option value="">Sektorlar yo'q</option>`;
  }

  loadEventReport();
}

async function loadEventReport() {
  const select = document.getElementById("report-event-select");
  const eventId = select.value;
  if (!eventId) return;

  const sectorFilter = document.getElementById("report-sector-filter").value;
  let url = `${API_BASE}/api/reports/events/${eventId}`;
  if (sectorFilter) url += `?sector_id=${sectorFilter}`;

  try {
    const res = await fetch(url, {
      headers: { "Authorization": `Bearer ${authToken}` }
    });
    const report = await res.json();
    if (!res.ok) throw new Error(report.detail || "Hisobotni olib bo'lmadi");

    // Metrics cards
    document.getElementById("rep-revenue").textContent = `${report.total_revenue.toLocaleString()} so'm`;
    document.getElementById("rep-occupancy").textContent = `${report.occupancy_rate}%`;
    document.getElementById("rep-sold").textContent = `${report.sold_seats} / ${report.total_seats}`;
    document.getElementById("rep-available").textContent = `Mavjud: ${report.available_seats} ta | Rezervda: ${report.reserved_seats} ta`;
    document.getElementById("rep-checked-in").textContent = `${report.total_checked_in} ta (${report.check_in_rate}%)`;

    // Table rows
    const tbody = document.getElementById("sector-report-tbody");
    if (!report.sectors || report.sectors.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="p-6 text-center text-slate-500">Sektor ma'lumotlari mavjud emas</td></tr>`;
      return;
    }

    tbody.innerHTML = report.sectors.map(s => `
      <tr class="hover:bg-slate-900/40 transition">
        <td class="p-4 font-bold text-white">${s.sector_name}</td>
        <td class="p-4 text-emerald-400 font-semibold">${s.price.toLocaleString()} so'm</td>
        <td class="p-4 text-slate-300">${s.total_seats}</td>
        <td class="p-4 font-bold text-white">${s.sold_seats}</td>
        <td class="p-4 text-slate-400">${s.available_seats} / <span class="text-amber-400">${s.reserved_seats}</span></td>
        <td class="p-4">
          <div class="flex items-center gap-2">
            <span class="font-bold text-indigo-400 text-xs">${s.occupancy_rate}%</span>
            <div class="w-16 h-1.5 rounded-full bg-slate-800 overflow-hidden">
              <div class="h-full bg-indigo-500" style="width: ${Math.min(100, s.occupancy_rate)}%"></div>
            </div>
          </div>
        </td>
        <td class="p-4 font-bold text-emerald-400">${s.revenue.toLocaleString()} so'm</td>
        <td class="p-4 text-blue-400 font-semibold">${s.checked_in_count} ta</td>
      </tr>
    `).join('');

  } catch (err) {
    showToast(err.message, "error");
  }
}

// CREATE EVENT MODAL
function openCreateEventModal() {
  document.getElementById("create-event-modal").classList.remove("hidden");
}
function closeCreateEventModal() {
  document.getElementById("create-event-modal").classList.add("hidden");
}

async function handleCreateEventSubmit(e) {
  e.preventDefault();
  const title = document.getElementById("event-form-title").value.trim();
  const date = document.getElementById("event-form-date").value;
  const location = document.getElementById("event-form-location").value.trim();
  const description = document.getElementById("event-form-desc").value.trim();

  try {
    const res = await fetch(`${API_BASE}/api/events`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${authToken}`
      },
      body: JSON.stringify({ title, date, location, description })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Tadbir yaratib bo'lmadi");

    showToast("Yangi tadbir muvaffaqiyatli yaratildi!", "success");
    closeCreateEventModal();
    await loadOrganizerEvents();
    loadEvents();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleCreateSector() {
  const select = document.getElementById("report-event-select");
  const eventId = select.value;
  if (!eventId) {
    showToast("Avval tadbirni tanlang", "warning");
    return;
  }

  const name = document.getElementById("new-sector-name").value.trim();
  const price = parseFloat(document.getElementById("new-sector-price").value);

  if (!name || isNaN(price)) {
    showToast("Sektor nomi va to'g'ri narxini kiriting", "warning");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/events/${eventId}/sectors`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${authToken}`
      },
      body: JSON.stringify({ name, price })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Sektor qo'shib bo'lmadi");

    showToast(`'${name}' sektori yaratildi!`, "success");
    document.getElementById("new-sector-name").value = "";
    document.getElementById("new-sector-price").value = "";
    await loadOrganizerEvents();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleBatchCreateSeats() {
  const sectorId = document.getElementById("gen-seat-sector-select").value;
  if (!sectorId) {
    showToast("Avval sektorni tanlang", "warning");
    return;
  }

  const prefix = document.getElementById("gen-seat-prefix").value.trim() || "A";
  const rows = parseInt(document.getElementById("gen-seat-rows").value) || 1;
  const seats_per_row = parseInt(document.getElementById("gen-seat-count").value) || 10;

  try {
    const res = await fetch(`${API_BASE}/api/events/sectors/${sectorId}/seats/batch`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${authToken}`
      },
      body: JSON.stringify({ prefix, rows, seats_per_row })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Joylarni yaratib bo'lmadi");

    showToast(`${data.length} ta yangi joy avtomatik generatsiya qilindi!`, "success");
    loadEventReport();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ================= ADMIN MANAGEMENT =================
async function loadAdminUsers() {
  if (!currentUser) {
    showToast("Admin paneliga kirish uchun 'admin' hisobiga kiring!", "warning");
    openAuthModal('login');
    return;
  }

  const tbody = document.getElementById("admin-users-tbody");
  if (tbody) tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-slate-500">Yuklanmoqda...</td></tr>`;

  try {
    // 1. Tizim umumiy statistikasini yuklash
    const statsRes = await fetch(`${API_BASE}/api/admin/stats`, {
      headers: { "Authorization": `Bearer ${authToken}` }
    });
    if (statsRes.ok) {
      const s = await statsRes.json();
      const uEl = document.getElementById("adm-stat-users");
      const oEl = document.getElementById("adm-stat-orgs");
      const cEl = document.getElementById("adm-stat-ctrls");
      const tEl = document.getElementById("adm-stat-tickets");
      if (uEl) uEl.textContent = s.total_users;
      if (oEl) oEl.textContent = s.organizers_count;
      if (cEl) cEl.textContent = s.controllers_count;
      if (tEl) tEl.textContent = `${s.total_tickets} (${s.used_tickets} ishlatilgan)`;
    }

    // 2. Foydalanuvchilar ro'yxatini yuklash
    const res = await fetch(`${API_BASE}/api/admin/users`, {
      headers: { "Authorization": `Bearer ${authToken}` }
    });
    const users = await res.json();
    if (!res.ok) throw new Error(users.detail || "Foydalanuvchilarni olib bo'lmadi");

    if (tbody) {
      tbody.innerHTML = users.map(u => `
        <tr class="hover:bg-slate-900/40 transition">
          <td class="p-4 font-mono text-xs text-slate-500">#${u.id}</td>
          <td class="p-4 font-bold text-white">${u.username}</td>
          <td class="p-4">
            <span class="px-2.5 py-1 rounded-full text-xs font-bold ${getRoleBadgeClass(u.role)}">
              ${u.role.toUpperCase()}
            </span>
          </td>
          <td class="p-4 text-slate-300 text-xs">${u.organization_name || '-'}</td>
          <td class="p-4 text-slate-400 text-xs">${new Date(u.created_at).toLocaleDateString()}</td>
          <td class="p-4 text-right whitespace-nowrap">
            <button onclick="adminResetUserPassword(${u.id}, '${u.username}')" class="px-2.5 py-1 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-indigo-300 rounded-lg mr-1.5 transition" title="Parolni o'zgartirish">
              <i data-lucide="key" class="w-3.5 h-3.5 inline"></i> Parol
            </button>
            ${u.username !== 'admin' ? `
              <button onclick="adminDeleteUser(${u.id}, '${u.username}')" class="px-2.5 py-1 text-xs font-semibold bg-red-500/20 hover:bg-red-500/40 text-red-400 rounded-lg transition" title="Foydalanuvchini butunlay o'chirish">
                <i data-lucide="trash-2" class="w-3.5 h-3.5 inline"></i> O'chirish
              </button>
            ` : '<span class="text-xs text-slate-500 italic">Boshqaruvchi</span>'}
          </td>
        </tr>
      `).join('');
      if (window.lucide) lucide.createIcons();
    }

  } catch (err) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-red-400">${err.message}</td></tr>`;
  }
}

// SUPER ADMIN ACTIONS
async function adminDeleteUser(userId, username) {
  if (!confirm(`Haqiqatan ham '${username}' foydalanuvchisini tizimdan butunlay o'chirib tashlamoqchimisiz?`)) return;
  try {
    const res = await fetch(`${API_BASE}/api/admin/users/${userId}`, {
      method: "DELETE",
      headers: { "Authorization": `Bearer ${authToken}` }
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Foydalanuvchini o'chirib bo'lmadi");
    showToast(data.message || "Foydalanuvchi muvaffaqiyatli o'chirildi!", "success");
    loadAdminUsers();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function adminResetUserPassword(userId, username) {
  const newPass = prompt(`'${username}' uchun yangi parolni kiriting:`);
  if (!newPass || !newPass.trim()) return;
  try {
    const res = await fetch(`${API_BASE}/api/admin/users/${userId}/reset-password`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${authToken}`
      },
      body: JSON.stringify({ new_password: newPass.trim() })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Parolni o'zgartirib bo'lmadi");
    showToast(data.message || "Parol yangilandi!", "success");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function adminReactivateTicket(token) {
  try {
    const res = await fetch(`${API_BASE}/api/admin/tickets/${token}/reactivate`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${authToken}` }
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Chiptani qayta faollashtirib bo'lmadi");
    showToast(data.message || "Chipta qayta faollashtirildi!", "success");
    handleVerifyTicket();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function getRoleBadgeClass(role) {
  if (role === "admin") return "bg-pink-500/20 text-pink-300 border border-pink-500/30";
  if (role === "organizer") return "bg-purple-500/20 text-purple-300 border border-purple-500/30";
  if (role === "controller") return "bg-blue-500/20 text-blue-300 border border-blue-500/30";
  return "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
}

async function handleAdminCreateOrganizer(e) {
  e.preventDefault();
  const organization_name = document.getElementById("admin-org-name").value.trim();
  const username = document.getElementById("admin-org-username").value.trim();
  const password = document.getElementById("admin-org-password").value.trim();

  try {
    const res = await fetch(`${API_BASE}/api/admin/organizers`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${authToken}`
      },
      body: JSON.stringify({ organization_name, username, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Tashkilotchi yaratib bo'lmadi");

    showToast(`'${username}' tashkilotchisi muvaffaqiyatli ro'yxatga olindi!`, "success");
    e.target.reset();
    loadAdminUsers();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleAdminCreateController(e) {
  e.preventDefault();
  const username = document.getElementById("admin-ctrl-username").value.trim();
  const password = document.getElementById("admin-ctrl-password").value.trim();

  try {
    const res = await fetch(`${API_BASE}/api/admin/controllers`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${authToken}`
      },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Tekshiruvchi yaratib bo'lmadi");

    showToast(`'${username}' tekshiruvchisi ro'yxatga olindi!`, "success");
    e.target.reset();
    loadAdminUsers();
  } catch (err) {
    showToast(err.message, "error");
  }
}
