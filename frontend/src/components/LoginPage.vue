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
  <div class="login-view-root">
    <!-- SVG Duotone Filters Definition -->
    <svg class="duotone-filter-defs" aria-hidden="true" width="0" height="0">
      <defs>
        <filter id="duotone-terracotta" color-interpolation-filters="sRGB">
          <feColorMatrix
            type="matrix"
            values="0.33 0.33 0.33 0 0
                    0.33 0.33 0.33 0 0
                    0.33 0.33 0.33 0 0
                    0 0 0 1 0"
          />
          <feComponentTransfer>
            <feFuncR type="table" tableValues="0.965 0.722" />
            <feFuncG type="table" tableValues="0.953 0.329" />
            <feFuncB type="table" tableValues="0.925 0.137" />
          </feComponentTransfer>
        </filter>
        <filter id="duotone-verdigris" color-interpolation-filters="sRGB">
          <feColorMatrix
            type="matrix"
            values="0.33 0.33 0.33 0 0
                    0.33 0.33 0.33 0 0
                    0.33 0.33 0.33 0 0
                    0 0 0 1 0"
          />
          <feComponentTransfer>
            <feFuncR type="table" tableValues="0.965 0.173" />
            <feFuncG type="table" tableValues="0.953 0.400" />
            <feFuncB type="table" tableValues="0.925 0.431" />
          </feComponentTransfer>
        </filter>
      </defs>
    </svg>

    <!-- Warm Architectural / Drafting Editorial Backdrop -->
    <div class="duotone-backdrop" aria-hidden="true">
      <div class="duotone-art-layer art-architectural duotone-apply-terracotta">
        <svg class="duotone-svg" viewBox="0 0 500 500" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect width="500" height="500" fill="#fbf9f5" />
          <g stroke="#b85423" stroke-width="1.2" opacity="0.85">
            <line x1="40" y1="50" x2="460" y2="50" stroke="#b85423" stroke-width="2" />
            <line x1="40" y1="90" x2="460" y2="90" stroke="#b85423" stroke-width="1" stroke-dasharray="6 6" />
            <line x1="40" y1="130" x2="460" y2="130" stroke="#b85423" stroke-width="1" stroke-dasharray="6 6" />
            <line x1="40" y1="170" x2="460" y2="170" stroke="#b85423" stroke-width="1" stroke-dasharray="6 6" />
            <line x1="40" y1="210" x2="460" y2="210" stroke="#b85423" stroke-width="1" stroke-dasharray="6 6" />
            <line x1="40" y1="250" x2="460" y2="250" stroke="#b85423" stroke-width="1" stroke-dasharray="6 6" />
            <line x1="40" y1="290" x2="460" y2="290" stroke="#b85423" stroke-width="1" stroke-dasharray="6 6" />
            <line x1="40" y1="330" x2="460" y2="330" stroke="#b85423" stroke-width="1" stroke-dasharray="6 6" />
            <line x1="40" y1="370" x2="460" y2="370" stroke="#b85423" stroke-width="1" stroke-dasharray="6 6" />
            <line x1="40" y1="410" x2="460" y2="410" stroke="#b85423" stroke-width="1" stroke-dasharray="6 6" />
            <line x1="40" y1="450" x2="460" y2="450" stroke="#b85423" stroke-width="2" />
            <line x1="120" y1="30" x2="120" y2="470" stroke="#b85423" stroke-width="1.5" />
            <line x1="380" y1="30" x2="380" y2="470" stroke="#b85423" stroke-width="1.5" />
          </g>
        </svg>
      </div>
    </div>

    <!-- Centered Editorial Login Card -->
    <main class="login-main-stage">
      <div class="login-card">
        <!-- Brand Header -->
        <header class="login-header">
          <div class="brand-monogram">
            <ChronoNoteLogo :size="48" />
          </div>
          <h1 class="login-serif-title">ChronoNote</h1>
          <p class="login-sub-caption">Personal Journal &amp; Timeline</p>
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
            <span v-else>{{ authMode === "register" ? "Create Account" : "Sign In" }}</span>
          </button>
        </form>
      </div>
    </main>
  </div>
</template>

<style scoped>
.login-view-root {
  position: relative;
  min-height: 100dvh;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--bg-page, #f6f3ec);
  overflow: hidden;
  padding: 24px 16px;
}

.duotone-filter-defs {
  position: absolute;
  width: 0;
  height: 0;
  pointer-events: none;
}

.duotone-backdrop {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: 1;
}

.duotone-art-layer {
  position: absolute;
  filter: drop-shadow(0 16px 32px rgba(28, 25, 23, 0.08));
}

.duotone-svg {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 24px;
}

.duotone-apply-terracotta {
  filter: url(#duotone-terracotta);
  mix-blend-mode: multiply;
  opacity: 0.22;
}

.art-architectural {
  top: -80px;
  right: -60px;
  width: 520px;
  height: 520px;
  transform: rotate(-7deg);
}

.login-main-stage {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 380px;
  margin: 0 auto;
}

.login-card {
  background: var(--bg-card, #ffffff);
  border: 1px solid var(--border-subtle, #e4ded3);
  border-radius: 20px;
  padding: 34px 28px 28px;
  box-shadow:
    0 1px 3px rgba(28, 25, 23, 0.04),
    0 16px 36px -12px rgba(28, 25, 23, 0.12),
    0 0 0 1px rgba(255, 255, 255, 0.8) inset;
  backdrop-filter: blur(8px);
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.login-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 6px;
  padding-bottom: 2px;
}

.brand-monogram {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 2px;
}

.login-serif-title {
  margin: 0;
  font-family: var(--font-serif, "Instrument Serif", Georgia, serif);
  font-size: 2.2rem;
  font-weight: 400;
  line-height: 1;
  color: var(--text-dark, #1c1917);
  letter-spacing: -0.015em;
  text-align: center;
}

.login-sub-caption {
  margin: 0;
  font-size: 0.78rem;
  color: var(--text-muted, #78716c);
}

.returning-user-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-elevated, #fbf9f5);
  border: 1px solid var(--border-subtle, #e4ded3);
  border-radius: 10px;
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
  color: var(--text-muted, #78716c);
}

.returning-name {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-dark, #1c1917);
}

.returning-email {
  font-size: 0.72rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--text-muted, #78716c);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-switch-account {
  background: none;
  border: none;
  color: var(--primary-orange, #b85423);
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
  padding: 4px;
  text-decoration: underline;
  text-underline-offset: 2px;
  white-space: nowrap;
}

.btn-switch-account:hover {
  color: var(--primary-orange-bright, #9e4418);
}

.auth-tab-row {
  display: flex;
  background: var(--bg-elevated, #fbf9f5);
  border: 1px solid var(--border-subtle, #e4ded3);
  border-radius: 8px;
  padding: 3px;
  gap: 4px;
}

.auth-tab-btn {
  flex: 1;
  padding: 6px 12px;
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--text-muted, #78716c);
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.auth-tab-btn.active {
  background: #ffffff;
  color: var(--text-dark, #1c1917);
  box-shadow: 0 1px 3px rgba(28, 25, 23, 0.08);
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
  gap: 14px;
}

.login-form-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-caption {
  font-size: 0.76rem;
  font-weight: 600;
  color: var(--text-muted, #78716c);
}

.login-input {
  width: 100%;
  padding: 10px 12px;
  font-size: 0.88rem;
  font-family: var(--font-sans);
  background: #ffffff;
  border: 1px solid var(--border-strong, #d4cbbd);
  border-radius: 8px;
  color: var(--text-dark, #1c1917);
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.login-input:focus {
  border-color: var(--primary-orange, #b85423);
  box-shadow: 0 0 0 3px rgba(184, 84, 35, 0.12);
}

.login-error-alert {
  margin: 0;
  padding: 8px 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #b91c1c;
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
  background: var(--primary-orange, #b85423);
  color: #ffffff;
  border: none;
  border-radius: 10px;
  font-size: 0.92rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(184, 84, 35, 0.2);
  transition: all 0.15s ease;
}

.btn-primary-enter:hover:not(:disabled) {
  background: var(--primary-orange-bright, #9e4418);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(184, 84, 35, 0.25);
}

.btn-primary-enter:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.spinner-inline {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 640px) {
  .login-card {
    padding: 26px 20px 22px;
  }
  .art-architectural {
    display: none;
  }
}
</style>
