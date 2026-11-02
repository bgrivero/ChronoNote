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
  "login-demo",
  "login-last-user",
  "clear-last-user",
]);

const authMode = ref("signin"); // "signin" | "register"
const emailInput = ref("");
const nameInput = ref("");
const passwordInput = ref("");
const googleBtnRef = ref(null);
const showAltOptions = ref(false);

const effectiveUser = computed(() => {
  if (props.lastUser && props.lastUser.email) {
    return props.lastUser;
  }
  return {
    email: "bryce@example.com",
    name: "Bryce",
  };
});

const displayName = computed(() => {
  return (
    effectiveUser.value.name ||
    effectiveUser.value.email
      .split("@")[0]
      .replace(/[._-]+/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase()) ||
    "Bryce"
  );
});

const isBryce = computed(() => effectiveUser.value.email === "bryce@example.com");

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

watch(
  () => props.authError,
  (err) => {
    if (err && (err.toLowerCase().includes("password") || err.toLowerCase().includes("incorrect"))) {
      showAltOptions.value = true;
      authMode.value = "signin";
      if (effectiveUser.value.email) {
        emailInput.value = effectiveUser.value.email;
      }
    }
  }
);

function submitAuth() {
  const email = emailInput.value.trim();
  if (!email || !email.includes("@")) {
    return;
  }
  if (authMode.value === "register") {
    emit("register", {
      email,
      name: nameInput.value.trim() || email.split("@")[0],
      password: passwordInput.value,
    });
  } else {
    emit("login-email", {
      email,
      password: passwordInput.value,
    });
  }
}

function submitPrimaryContinue() {
  if (isBryce.value) {
    emit("login-demo");
  } else {
    emit("login-last-user", effectiveUser.value);
  }
}

function switchToDefaultBryce() {
  emit("clear-last-user");
  emailInput.value = "bryce@example.com";
  nameInput.value = "Bryce";
  passwordInput.value = "";
}

function switchMode(mode) {
  authMode.value = mode;
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
                    0    0    0    1 0"
          />
          <feComponentTransfer>
            <feFuncR type="table" tableValues="0.11 0.72 0.98" />
            <feFuncG type="table" tableValues="0.10 0.33 0.94" />
            <feFuncB type="table" tableValues="0.09 0.14 0.90" />
          </feComponentTransfer>
        </filter>

        <filter id="duotone-verdigris" color-interpolation-filters="sRGB">
          <feColorMatrix
            type="matrix"
            values="0.33 0.33 0.33 0 0
                    0.33 0.33 0.33 0 0
                    0.33 0.33 0.33 0 0
                    0    0    0    1 0"
          />
          <feComponentTransfer>
            <feFuncR type="table" tableValues="0.08 0.17 0.94" />
            <feFuncG type="table" tableValues="0.16 0.40 0.97" />
            <feFuncB type="table" tableValues="0.18 0.43 0.97" />
          </feComponentTransfer>
        </filter>
      </defs>
    </svg>

    <!-- Background Duotone Artworks -->
    <div class="duotone-backdrop" aria-hidden="true">
      <div class="duotone-art-layer art-architectural">
        <svg
          class="duotone-svg duotone-apply-terracotta"
          viewBox="0 0 600 600"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <rect width="600" height="600" fill="#fcf4ee" />
          <g opacity="0.9">
            <path d="M50 600 V240 A250 250 0 0 1 550 240 V600 Z" fill="#2d150b" />
            <path d="M120 600 V270 A180 180 0 0 1 480 270 V600 Z" fill="#fcf4ee" />
            <path d="M180 600 V300 A120 120 0 0 1 420 300 V600 Z" fill="#52200e" />
            <path d="M240 600 V330 A60 60 0 0 1 360 330 V600 Z" fill="#fcf4ee" />
            <polygon points="0,0 600,600 550,600 0,50" fill="#883311" />
            <polygon points="100,0 600,500 600,440 160,0" fill="#2d150b" />
            <line x1="50" y1="50" x2="550" y2="50" stroke="#b85423" stroke-width="2" stroke-dasharray="8 8" />
            <line x1="50" y1="120" x2="550" y2="120" stroke="#b85423" stroke-width="1.5" />
            <line x1="50" y1="190" x2="550" y2="190" stroke="#b85423" stroke-width="1" />
            <circle cx="300" cy="240" r="14" fill="#b85423" />
            <circle cx="300" cy="240" r="28" stroke="#b85423" stroke-width="2" />
          </g>
        </svg>
      </div>

      <div class="duotone-art-layer art-chronograph">
        <svg
          class="duotone-svg duotone-apply-verdigris"
          viewBox="0 0 640 640"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <rect width="640" height="640" fill="#f2f7f7" />
          <g opacity="0.85">
            <circle cx="320" cy="320" r="280" stroke="#0e1f21" stroke-width="3" />
            <circle cx="320" cy="320" r="240" stroke="#2c666e" stroke-width="1.5" stroke-dasharray="4 6" />
            <circle cx="320" cy="320" r="200" stroke="#1c3e43" stroke-width="2" />
            <circle cx="320" cy="320" r="130" fill="#142c30" />
            <circle cx="320" cy="320" r="110" fill="#f2f7f7" />
            <circle cx="320" cy="320" r="40" fill="#2c666e" />
            <line x1="320" y1="40" x2="320" y2="600" stroke="#0e1f21" stroke-width="2" />
            <line x1="40" y1="320" x2="600" y2="320" stroke="#0e1f21" stroke-width="2" />
            <line x1="122" y1="122" x2="518" y2="518" stroke="#2c666e" stroke-width="1.5" />
            <line x1="518" y1="122" x2="122" y2="518" stroke="#2c666e" stroke-width="1.5" />
            <path d="M80 320 A240 240 0 0 1 560 320" stroke="#2c666e" stroke-width="6" />
            <path d="M140 320 A180 180 0 0 1 500 320" stroke="#0e1f21" stroke-width="3" stroke-dasharray="12 6" />
          </g>
        </svg>
      </div>

      <div class="duotone-art-layer art-folio">
        <svg
          class="duotone-svg duotone-apply-terracotta"
          viewBox="0 0 500 500"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <rect width="500" height="500" fill="#fbf9f5" />
          <g opacity="0.6">
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

    <!-- Minimal Centered Content Stage -->
    <main class="login-main-stage">
      <div class="login-card">
        <!-- Minimal Centered Brand Header -->
        <header class="login-header">
          <div class="brand-monogram">
            <ChronoNoteLogo :size="48" />
          </div>
          <h1 class="login-serif-title">ChronoNote</h1>
        </header>

        <!-- Primary 1-Click Enter as Active / Last User -->
        <button
          type="button"
          class="btn-primary-enter"
          :disabled="isAuthenticating"
          @click="submitPrimaryContinue"
        >
          <span v-if="isAuthenticating" class="spinner-inline" />
          <span v-else>Continue as {{ displayName }}</span>
        </button>

        <div v-if="!isBryce" class="switch-user-prompt">
          <span class="last-user-badge" :title="effectiveUser.email">{{ effectiveUser.email }}</span>
          <button
            type="button"
            class="btn-switch-account"
            @click="switchToDefaultBryce"
          >
            Switch to Bryce
          </button>
        </div>

        <!-- Dedicated Account Drawer (Sign In & Register) -->
        <div class="alt-login-wrapper">
          <button
            type="button"
            class="btn-toggle-alt"
            @click="showAltOptions = !showAltOptions"
          >
            <span>{{ showAltOptions ? "Hide options" : "Use different account or register" }}</span>
            <span class="toggle-icon">{{ showAltOptions ? "↑" : "↓" }}</span>
          </button>

          <div v-show="showAltOptions" class="alt-options-drawer">
            <!-- Sign In / Register Tabs -->
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

            <!-- Google One-Tap / GSI button if configured -->
            <div
              v-show="googleClientId"
              ref="googleBtnRef"
              class="google-gsi-mount-point"
            />

            <form class="login-credentials-form" @submit.prevent="submitAuth">
              <div class="login-form-fields">
                <label v-if="authMode === 'register'" class="field-item">
                  <span class="field-caption">Your Name</span>
                  <input
                    v-model="nameInput"
                    type="text"
                    required
                    class="login-input"
                    placeholder="e.g. Alice"
                    autocomplete="name"
                  />
                </label>

                <label class="field-item">
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
                  <span class="field-caption">Password (optional)</span>
                  <input
                    v-model="passwordInput"
                    type="password"
                    class="login-input"
                    placeholder="••••••••"
                    autocomplete="current-password"
                  />
                </label>
              </div>

              <!-- Error Alert -->
              <p v-if="authError" class="login-error-alert" role="alert">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <span>{{ authError }}</span>
              </p>

              <button
                type="submit"
                class="btn-login-submit"
                :disabled="isAuthenticating"
              >
                <span v-if="isAuthenticating" class="spinner-inline" />
                <span v-else>{{ authMode === "register" ? "Create Account" : "Sign In to Account" }}</span>
              </button>
            </form>
          </div>
        </div>
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

.duotone-apply-verdigris {
  filter: url(#duotone-verdigris);
  mix-blend-mode: multiply;
  opacity: 0.25;
}

.art-architectural {
  top: -80px;
  right: -60px;
  width: 520px;
  height: 520px;
  transform: rotate(-7deg);
}

.art-chronograph {
  bottom: -90px;
  left: -80px;
  width: 540px;
  height: 540px;
  transform: rotate(12deg);
}

.art-folio {
  top: 45%;
  right: 8%;
  width: 360px;
  height: 360px;
  transform: translateY(-50%) rotate(4deg);
  opacity: 0.65;
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
  padding: 38px 32px 32px;
  box-shadow:
    0 1px 3px rgba(28, 25, 23, 0.04),
    0 16px 36px -12px rgba(28, 25, 23, 0.12),
    0 0 0 1px rgba(255, 255, 255, 0.8) inset;
  backdrop-filter: blur(8px);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.login-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 12px;
  padding-bottom: 4px;
}

.brand-monogram {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.login-serif-title {
  margin: 0;
  font-family: var(--font-serif, "Instrument Serif", Georgia, serif);
  font-size: 2.35rem;
  font-weight: 400;
  line-height: 1;
  color: var(--text-dark, #1c1917);
  letter-spacing: -0.015em;
  text-align: center;
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

.switch-user-prompt {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  margin-top: -6px;
  padding: 0 4px;
  font-size: 0.78rem;
}

.last-user-badge {
  color: var(--text-muted, #78716c);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.75rem;
  max-width: 190px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-switch-account {
  background: none;
  border: none;
  color: var(--primary-orange, #b85423);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  padding: 2px 4px;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.btn-switch-account:hover {
  color: var(--primary-orange-bright, #9e4418);
}

.alt-login-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding-top: 4px;
}

.btn-toggle-alt {
  background: none;
  border: none;
  padding: 4px 8px;
  color: var(--text-muted, #78716c);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: color 0.15s ease;
}

.btn-toggle-alt:hover {
  color: var(--text-dark, #1c1917);
}

.toggle-icon {
  font-size: 0.72rem;
  opacity: 0.75;
}

.alt-options-drawer {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 10px;
  border-top: 1px dashed var(--border-subtle, #e4ded3);
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
  gap: 12px;
}

.login-form-fields {
  display: flex;
  flex-direction: column;
  gap: 10px;
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
  padding: 9px 12px;
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

.btn-login-submit {
  width: 100%;
  padding: 10px 16px;
  background: var(--text-dark, #1c1917);
  color: #ffffff;
  border: 1px solid var(--text-dark, #1c1917);
  border-radius: 8px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.15s ease;
}

.btn-login-submit:hover:not(:disabled) {
  background: #292524;
  border-color: #292524;
}

.btn-login-submit:disabled {
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
    padding: 28px 22px 24px;
  }
  .art-architectural,
  .art-chronograph,
  .art-folio {
    display: none;
  }
}
</style>
