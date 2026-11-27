<script setup>
import { ref, computed, watch, onMounted } from "vue";
import ChronoNoteLogo from "./ChronoNoteLogo.vue";

const props = defineProps({
  googleClientId: {
    type: String,
    default: "",
  },
  authError: {
    type: String,
    default: "",
  },
  isAuthenticating: {
    type: Boolean,
    default: false,
  },
  lastUser: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits([
  "login-google",
  "login-email",
  "register",
  "clear-last-user",
]);

const authMode = ref("signin"); // "signin" | "register"
const emailInput = ref("");
const nameInput = ref("");
const passwordInput = ref("");
const localError = ref("");
const googleBtnRef = ref(null);

const todayDisplay = computed(() => {
  const now = new Date();
  const dayNum = String(now.getDate()).padStart(2, "0");
  const weekday = now.toLocaleDateString("en-US", { weekday: "long" });
  const month = now.toLocaleDateString("en-US", { month: "long" });
  const year = String(now.getFullYear());
  return { dayNum, weekday, month, year };
});

const effectiveUser = computed(() => {
  if (props.lastUser && props.lastUser.email) {
    return props.lastUser;
  }
  return null;
});

const displayName = computed(() => {
  if (effectiveUser.value) {
    return (
      effectiveUser.value.name ||
      effectiveUser.value.email
        .split("@")[0]
        .replace(/[._-]+/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase())
    );
  }
  return "";
});

watch(
  () => props.lastUser,
  (u) => {
    if (u?.email) {
      emailInput.value = u.email;
      if (u.name) nameInput.value = u.name;
    }
  },
  { immediate: true }
);

function switchMode(mode) {
  authMode.value = mode;
  localError.value = "";
  passwordInput.value = "";
}

function handleSwitchAccount() {
  emit("clear-last-user");
  emailInput.value = "";
  nameInput.value = "";
  passwordInput.value = "";
  localError.value = "";
}

function submitAuth() {
  localError.value = "";
  const email = emailInput.value.trim().toLowerCase();
  if (!email || !email.includes("@")) {
    localError.value = "Please enter a valid email address.";
    return;
  }

  const password = passwordInput.value.trim();
  if (!password) {
    localError.value = "Password is required.";
    return;
  }

  if (authMode.value === "register" && password.length < 6) {
    localError.value = "Password must be at least 6 characters.";
    return;
  }

  if (authMode.value === "register") {
    emit("register", {
      email,
      name: nameInput.value.trim() || email.split("@")[0],
      password,
    });
  } else {
    emit("login-email", {
      email,
      password,
    });
  }
}

onMounted(() => {
  if (
    typeof window !== "undefined" &&
    window.google?.accounts?.id &&
    props.googleClientId &&
    googleBtnRef.value
  ) {
    try {
      window.google.accounts.id.initialize({
        client_id: props.googleClientId,
        callback: (res) => emit("login-google", res),
      });
      window.google.accounts.id.renderButton(googleBtnRef.value, {
        theme: "outline",
        size: "large",
        shape: "rectangular",
        width: 320,
      });
    } catch {
      // Ignore if gsi is unavailable or offline
    }
  }
});
</script>

<template>
  <div class="login-entry-shell">
    <!-- Left 58%: Structural 2-Row Prairie Stained-Glass + Dark Bronze Plinth -->
    <aside class="login-architectural-pane" aria-hidden="true">
      <!-- Row 1: Pure CSS Grid Prairie Mosaic (Strictly above plinth, never overlaps) -->
      <div class="prairie-mosaic-grid">
        <div class="mosaic-pane pane-umber" />
        <div class="mosaic-pane pane-amber" />
        <div class="mosaic-split-col">
          <div class="mosaic-pane pane-terracotta" />
          <div class="mosaic-pane pane-verdigris" />
        </div>

        <div class="mosaic-left-stack">
          <div class="mosaic-pane pane-walnut" />
          <div class="mosaic-pane pane-charcoal" />
        </div>
        <div class="mosaic-center-cluster">
          <div class="mosaic-top-pair">
            <div class="mosaic-pane pane-verdigris" />
            <div class="mosaic-pane pane-umber-soft" />
          </div>
          <div class="mosaic-pane pane-sienna-deep" />
        </div>

        <div class="mosaic-sill-row">
          <div class="mosaic-pane pane-terracotta" />
          <div class="mosaic-pane pane-verdigris" />
          <div class="mosaic-pane pane-walnut" />
        </div>
      </div>

      <!-- Row 2: Dedicated Dark-Bronze Plinth -->
      <div class="login-plinth-panel">
        <div class="plinth-brand-seal">
          <div class="plinth-logo-frame">
            <ChronoNoteLogo
              :size="26"
              dial-color="#F8F4EC"
              accent-color="#E07B39"
              paper-color="#271E18"
            />
          </div>
          <div class="plinth-brand-meta">
            <span class="plinth-brand-kicker">CHRONONOTE</span>
            <span class="plinth-brand-sub">Notes, Timeline &amp; Habits</span>
          </div>
        </div>

        <div class="plinth-poster-date">
          <span class="plinth-day-numeral">{{ todayDisplay.dayNum }}</span>
          <div class="plinth-day-script">
            <span class="plinth-weekday-italic">{{ todayDisplay.weekday }}</span>
            <span class="plinth-month-label">{{ todayDisplay.month }}</span>
          </div>
        </div>
      </div>

      <!-- Turned Year Margin inside dedicated right gutter -->
      <div class="turned-year-margin">{{ todayDisplay.year }}</div>
    </aside>

    <!-- Right 42%: Flush Sunlit Alabaster Entry Form -->
    <main class="login-form-pane">
      <div class="login-form-inner">
        <header class="login-pane-header">
          <div class="mobile-only-seal">
            <ChronoNoteLogo :size="36" />
          </div>
          <span class="login-pane-kicker">WORKSPACE ENTRY</span>
          <h1 class="login-serif-title">ChronoNote</h1>
          <p class="login-sub-caption">Personal journal, calendar &amp; projects</p>
        </header>

        <!-- Returning User Welcome -->
        <div v-if="effectiveUser && authMode === 'signin'" class="returning-user-card">
          <div class="returning-user-meta">
            <span class="returning-greeting">Welcome back,</span>
            <span class="returning-name">{{ displayName }}</span>
            <span class="returning-email">{{ effectiveUser.email }}</span>
          </div>
          <button
            type="button"
            class="btn-switch-account"
            @click="handleSwitchAccount"
          >
            Switch account
          </button>
        </div>

        <!-- Auth Mode Tabs (Sign In / Register) -->
        <div class="auth-tab-row">
          <button
            type="button"
            class="auth-tab-btn"
            :class="{ active: authMode === 'signin' }"
            @click="switchMode('signin')"
          >
            Sign In
          </button>
          <button
            type="button"
            class="auth-tab-btn"
            :class="{ active: authMode === 'register' }"
            @click="switchMode('register')"
          >
            Register
          </button>
        </div>

        <!-- Google One-Tap Mount Point (if client ID configured) -->
        <div
          v-show="googleClientId"
          ref="googleBtnRef"
          class="google-gsi-mount-point"
        />

        <!-- Secure Credentials Form -->
        <form class="login-credentials-form" @submit.prevent="submitAuth">
          <div class="login-form-fields">
            <label v-if="authMode === 'register'" class="field-item">
              <span class="field-caption">Your Name</span>
              <input
                v-model="nameInput"
                type="text"
                class="login-input"
                placeholder="e.g. Bryce"
                autocomplete="name"
              />
            </label>

            <label v-if="!effectiveUser || authMode === 'register'" class="field-item">
              <span class="field-caption">Email Address</span>
              <input
                v-model="emailInput"
                type="email"
                required
                class="login-input"
                placeholder="name@example.com"
                autocomplete="email"
              />
            </label>

            <label class="field-item">
              <span class="field-caption">Password</span>
              <input
                v-model="passwordInput"
                type="password"
                required
                minlength="6"
                class="login-input"
                :placeholder="authMode === 'register' ? 'At least 6 characters' : '••••••••'"
                autocomplete="current-password"
                autofocus
              />
            </label>
          </div>

          <!-- Error Alert -->
          <p v-if="localError || authError" class="login-error-alert" role="alert">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{{ localError || authError }}</span>
          </p>

          <button
            type="submit"
            class="btn-primary-enter"
            :disabled="isAuthenticating"
          >
            <span v-if="isAuthenticating" class="spinner-inline" />
            <span v-else>{{ authMode === "register" ? "Create Account" : "Enter Workspace" }}</span>
          </button>
        </form>
      </div>
    </main>
  </div>
</template>

<style scoped>
.login-entry-shell {
  min-height: 100dvh;
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1.38fr) minmax(360px, 1fr);
  background: var(--bg-card);
}

/* Left 58%: Structural 2-Row Prairie Mosaic + Dark Bronze Plinth */
.login-architectural-pane {
  position: relative;
  background: var(--spine-deep);
  border-right: 1px solid rgba(28, 21, 17, 0.35);
  display: grid;
  grid-template-rows: minmax(220px, 1fr) auto;
  gap: 6px;
  padding: 24px 48px 24px 24px;
  min-height: 100dvh;
}

.prairie-mosaic-grid {
  display: grid;
  grid-template-columns: 1.45fr 0.9fr 0.72fr;
  grid-template-rows: 0.95fr 1.25fr 0.24fr;
  gap: 6px;
  min-height: 0;
}

.mosaic-pane {
  border-radius: 1px;
  box-shadow: inset 0 1px 0 var(--spine-line-soft);
}

.pane-umber {
  background: #2c241f;
}

.pane-umber-soft {
  background: #352c26;
}

.pane-charcoal {
  background: #2a221d;
}

.pane-amber {
  background: #b67824;
}

.pane-terracotta {
  background: #a8411d;
}

.pane-verdigris {
  background: #284d43;
}

.pane-walnut {
  background: #46311d;
}

.pane-sienna-deep {
  background: #4c2416;
}

.mosaic-split-col {
  display: grid;
  grid-template-rows: 1fr 1fr;
  gap: 6px;
}

.mosaic-left-stack {
  display: grid;
  grid-template-columns: 0.45fr 1fr;
  gap: 6px;
}

.mosaic-center-cluster {
  grid-column: 2 / 4;
  display: grid;
  grid-template-rows: 1fr 1fr;
  gap: 6px;
}

.mosaic-top-pair {
  display: grid;
  grid-template-columns: 0.65fr 1fr;
  gap: 6px;
}

.mosaic-sill-row {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: 1.1fr 0.65fr 1.6fr;
  gap: 6px;
}

.turned-year-margin {
  position: absolute;
  top: 28px;
  right: 16px;
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  font-family: var(--font-mono);
  font-size: 0.76rem;
  letter-spacing: 0.28em;
  color: rgba(248, 244, 236, 0.52);
  user-select: none;
}

.login-plinth-panel {
  background: #211914;
  border-top: 1px solid var(--spine-line-soft);
  padding: 24px 28px 22px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.plinth-brand-seal {
  display: inline-flex;
  align-items: center;
  gap: 14px;
}

.plinth-logo-frame {
  width: 44px;
  height: 44px;
  border: 1px solid rgba(248, 244, 236, 0.22);
  background: var(--bg-spine);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
  flex-shrink: 0;
}

.plinth-brand-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.plinth-brand-kicker {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.16em;
  color: var(--bg-card);
}

.plinth-brand-sub {
  font-size: 0.8rem;
  color: rgba(248, 244, 236, 0.66);
}

.plinth-poster-date {
  display: flex;
  align-items: flex-end;
  gap: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--spine-line);
}

.plinth-day-numeral {
  font-family: var(--font-serif);
  font-size: clamp(4.4rem, 6.2vw, 5.8rem);
  font-weight: 400;
  line-height: 0.82;
  letter-spacing: -0.04em;
  color: var(--bg-card);
}

.plinth-day-script {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-bottom: 4px;
}

.plinth-weekday-italic {
  font-family: var(--font-serif);
  font-style: italic;
  font-size: 1.85rem;
  font-weight: 400;
  line-height: 1.05;
  color: var(--accent-amber);
}

.plinth-month-label {
  font-family: var(--font-mono);
  font-size: 0.74rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(248, 244, 236, 0.74);
}

/* Right 42%: Flush Alabaster Form Pane */
.login-form-pane {
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 36px;
}

.login-form-inner {
  width: 100%;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.login-pane-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border-subtle);
}

.mobile-only-seal {
  display: none;
  margin-bottom: 6px;
}

.login-pane-kicker {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: var(--primary-orange);
}

.login-serif-title {
  margin: 0;
  font-family: var(--font-serif, Georgia, serif);
  font-size: 2.55rem;
  font-weight: 500;
  font-optical-sizing: auto;
  line-height: 0.98;
  color: var(--text-dark);
  letter-spacing: -0.02em;
}

.login-sub-caption {
  margin: 2px 0 0;
  font-size: 0.82rem;
  color: var(--text-muted);
}

.returning-user-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-page);
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--primary-orange);
  border-radius: 2px;
  padding: 10px 12px;
  gap: 8px;
}

.returning-user-meta {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.returning-greeting {
  font-size: 0.72rem;
  color: var(--text-muted);
}

.returning-name {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-dark);
}

.returning-email {
  font-size: 0.72rem;
  font-family: var(--font-mono);
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-switch-account {
  background: none;
  border: none;
  color: var(--primary-orange);
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
  padding: 4px;
  text-decoration: underline;
  text-underline-offset: 2px;
  white-space: nowrap;
}

.btn-switch-account:hover {
  color: var(--primary-orange-bright);
}

.auth-tab-row {
  display: flex;
  border-bottom: 1px solid var(--border-subtle);
  gap: 18px;
}

.auth-tab-btn {
  padding: 7px 2px 9px;
  font-family: var(--font-sans);
  font-size: 0.84rem;
  font-weight: 500;
  color: var(--text-muted);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  cursor: pointer;
  transition: color 0.15s ease, border-color 0.15s ease;
}

.auth-tab-btn:hover {
  color: var(--text-dark);
}

.auth-tab-btn.active {
  color: var(--text-dark);
  border-bottom-color: var(--primary-orange);
  font-weight: 600;
}

.google-gsi-mount-point {
  display: flex;
  justify-content: center;
  min-height: 40px;
}

.login-credentials-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.login-form-fields {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field-caption {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
}

.login-input {
  width: 100%;
  padding: 10px 12px;
  font-size: 0.9rem;
  font-family: var(--font-sans);
  background: var(--paper);
  border: 1px solid var(--border-strong);
  border-radius: 3px;
  color: var(--text-dark);
  outline: none;
  transition: border-color 0.15s ease, background-color 0.15s ease;
}

.login-input:focus {
  border-color: var(--primary-orange);
  background: var(--white);
}

.login-error-alert {
  margin: 0;
  padding: 9px 12px;
  background: var(--danger-soft);
  border: 1px solid var(--danger-border);
  border-left: 3px solid var(--danger);
  border-radius: 2px;
  color: var(--danger-strong);
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-primary-enter {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  background: var(--primary-orange);
  color: var(--paper);
  border: 1px solid var(--primary-orange-bright);
  border-radius: 3px;
  font-family: var(--font-sans);
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.08s ease;
}

.btn-primary-enter:hover:not(:disabled) {
  background: var(--primary-orange-bright);
}

.btn-primary-enter:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.spinner-inline {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: var(--white);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 860px) {
  .login-entry-shell {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }

  .login-architectural-pane {
    min-height: auto;
    grid-template-rows: 52px auto;
    padding: 16px 40px 16px 16px;
    border-right: none;
    border-bottom: 1px solid rgba(28, 21, 17, 0.35);
  }

  .prairie-mosaic-grid {
    grid-template-columns: 1.2fr 0.8fr 1fr;
    grid-template-rows: 1fr;
  }

  .mosaic-left-stack,
  .mosaic-center-cluster,
  .mosaic-sill-row {
    display: none;
  }

  .login-plinth-panel {
    padding: 16px 18px;
    gap: 12px;
  }

  .turned-year-margin {
    top: 16px;
    right: 12px;
  }

  .plinth-day-numeral {
    font-size: 3.4rem;
  }

  .plinth-weekday-italic {
    font-size: 1.4rem;
  }

  .login-form-pane {
    padding: 28px 20px 40px;
    align-items: flex-start;
  }

  .mobile-only-seal {
    display: inline-flex;
  }
}
</style>
