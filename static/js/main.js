// ---- TOAST ----
function showToast(message, type = "info", duration = 3500) {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  const icons = {
    success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
    error: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
    info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`
  };
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `${icons[type] || icons.info}<span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = "0"; toast.style.transform = "translateX(20px)"; toast.style.transition = "all 0.3s"; setTimeout(() => toast.remove(), 300); }, duration);
}
window.showToast = showToast;

// ---- MODAL ----
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) { modal.classList.add("open"); document.body.style.overflow = "hidden"; }
}
function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) { modal.classList.remove("open"); document.body.style.overflow = ""; }
}
window.openModal = openModal;
window.closeModal = closeModal;
document.addEventListener("click", e => {
  if (e.target.classList.contains("modal-overlay")) {
    e.target.classList.remove("open");
    document.body.style.overflow = "";
  }
});

// ---- TABS ----
function initTabs(container) {
  const btns = container.querySelectorAll(".tab-btn");
  const contents = container.querySelectorAll(".tab-content");
  btns.forEach(btn => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      btns.forEach(b => b.classList.remove("active"));
      contents.forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      const targetEl = container.querySelector(`#tab-${target}`);
      if (targetEl) targetEl.classList.add("active");
    });
  });
}
document.querySelectorAll("[data-tabs]").forEach(initTabs);

// ---- COPY ----
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => showToast("Copied to clipboard", "success")).catch(() => {
    const el = document.createElement("textarea");
    el.value = text;
    document.body.appendChild(el);
    el.select();
    document.execCommand("copy");
    el.remove();
    showToast("Copied", "success");
  });
}
window.copyToClipboard = copyToClipboard;

// ---- BANNER SLIDER ----
function initBannerSlider() {
  const slider = document.querySelector(".banner-slider");
  if (!slider) return;
  const slides = slider.querySelectorAll(".banner-slide");
  const dotsContainer = slider.querySelector(".banner-dots");
  if (slides.length === 0) return;
  let current = 0;
  const dots = [];
  if (dotsContainer) {
    slides.forEach((_, i) => {
      const dot = document.createElement("div");
      dot.className = "banner-dot" + (i === 0 ? " active" : "");
      dot.addEventListener("click", () => goTo(i));
      dotsContainer.appendChild(dot);
      dots.push(dot);
    });
  }
  function goTo(index) {
    slides[current].classList.remove("active");
    if (dots[current]) dots[current].classList.remove("active");
    current = index;
    slides[current].classList.add("active");
    if (dots[current]) dots[current].classList.add("active");
  }
  slides[0].classList.add("active");
  if (slides.length > 1) setInterval(() => goTo((current + 1) % slides.length), 4000);
}
initBannerSlider();

// ---- COUNTDOWN ----
function initCountdowns() {
  document.querySelectorAll("[data-countdown]").forEach(el => {
    const target = parseInt(el.dataset.countdown);
    function update() {
      const diff = Math.max(0, target - Date.now());
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      el.textContent = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
      if (diff > 0) setTimeout(update, 1000);
      else el.textContent = "Ended";
    }
    update();
  });
}
initCountdowns();

// ---- API HELPER ----
async function apiPost(url, data) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  });
  return res.json();
}
window.apiPost = apiPost;

// ---- NOTIFICATION COUNT ----
async function updateNotifCount() {
  try {
    const r = await fetch("/api/notifications/count");
    const data = await r.json();
    const dot = document.querySelector(".notif-dot");
    if (dot) dot.style.display = data.count > 0 ? "block" : "none";
    const badge = document.querySelector(".notif-badge");
    if (badge) badge.textContent = data.count > 0 ? data.count : "";
  } catch(e) {}
}
updateNotifCount();
setInterval(updateNotifCount, 30000);

// ---- BALANCE UPDATE ----
async function updateBalance() {
  try {
    const r = await fetch("/api/user/balance");
    if (r.ok) {
      const data = await r.json();
      const el = document.querySelector(".balance-display");
      if (el) el.textContent = parseFloat(data.balance).toLocaleString("en-IN", {minimumFractionDigits: 2});
    }
  } catch(e) {}
}
if (document.querySelector(".balance-display")) {
  updateBalance();
  setInterval(updateBalance, 60000);
}

// ---- FORMAT CURRENCY ----
function formatCurrency(amount) {
  return parseFloat(amount).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
window.formatCurrency = formatCurrency;

// ---- PASSWORD TOGGLE ----
document.querySelectorAll(".input-toggle").forEach(btn => {
  btn.addEventListener("click", () => {
    const input = btn.closest(".input-group").querySelector("input");
    if (input) { input.type = input.type === "password" ? "text" : "password"; }
  });
});

// ---- CONFIRM ACTION ----
function confirmAction(message, callback) {
  if (window.confirm(message)) callback();
}
window.confirmAction = confirmAction;

// ---- SVG INLINE LOADER ----
function loadSvgSprites() {
  const sprites = [
    "/static/svg/icons.svg",
    "/static/svg/vip_badges.svg",
    "/static/svg/rank_badges.svg",
    "/static/svg/game_assets.svg",
    "/static/svg/profile_frames.svg",
    "/static/svg/achievement_badges.svg"
  ];
  sprites.forEach(src => {
    fetch(src).then(r => r.text()).then(svg => {
      const div = document.createElement("div");
      div.style.display = "none";
      div.innerHTML = svg;
      document.body.prepend(div);
    }).catch(() => {});
  });
}
loadSvgSprites();
