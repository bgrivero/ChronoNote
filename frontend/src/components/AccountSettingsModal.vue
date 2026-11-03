<template>
  <div class="modal-backdrop" @click.self="$emit('close')">
    <div class="account-settings-card" role="dialog" aria-modal="true" aria-labelledby="account-settings-title">
      <!-- Header -->
      <div class="modal-header">
        <div class="header-titles">
          <span class="settings-kicker">USER PREFERENCES</span>
          <h3 id="account-settings-title" class="settings-title">Account Settings</h3>
          <p class="settings-subtitle">Manage your profile, username, and account security credentials.</p>
        </div>
        <button
          type="button"
          class="modal-close-btn"
          aria-label="Close Account Settings"
          @click="$emit('close')"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <!-- Content Body -->
      <div class="modal-scroll-body">
        <!-- Notification Banners -->
        <div v-if="successMsg" class="feedback-banner success-banner">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span>{{ successMsg }}</span>
        </div>

        <div v-if="errorMsg" class="feedback-banner error-banner">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{{ errorMsg }}</span>
        </div>

        <!-- Section 1: Profile Details -->
        <section class="settings-section">
          <div class="section-heading-row">
            <h4 class="section-title">Profile Information</h4>
            <span class="account-type-badge">
              {{ currentUser?.has_password ? 'Password Account' : 'Google / Local Account' }}
            </span>
          </div>

          <div class="form-grid">
            <div class="form-group">
              <label for="acc-name" class="form-label">Username / Display Name</label>
              <input
                id="acc-name"
                v-model="form.name"
                type="text"
                class="form-input"
                placeholder="Your username or display name"
                maxlength="120"
              />
            </div>

            <div class="form-group">
              <label for="acc-email" class="form-label">Email Address</label>
              <input
                id="acc-email"
                v-model="form.email"
                type="email"
                class="form-input"
                placeholder="name@example.com"
                :disabled="isGoogleUser"
              />
              <span v-if="isGoogleUser" class="field-hint">
                Managed via Google Sign-In. Email cannot be edited directly.
              </span>
            </div>
          </div>
        </section>

        <div class="section-divider" />

        <!-- Section 2: Password & Security (Strict) -->
        <section class="settings-section">
          <div class="section-heading-row">
            <h4 class="section-title">Account Password</h4>
            <span class="security-status-badge" :class="{ 'has-pwd': currentUser?.has_password }">
              {{ currentUser?.has_password ? 'Active Password' : 'No Password Set' }}
            </span>
          </div>

          <p class="section-desc">
            To change or set your account password, provide a strong password meeting all strict security requirements.
          </p>

          <div class="password-fields-box">
            <!-- Current Password (if already has password) -->
            <div v-if="currentUser?.has_password" class="form-group">
              <label for="acc-current-pw" class="form-label">
                Current Password <span class="required-star">*</span>
              </label>
              <div class="pw-input-wrap">
                <input
                  id="acc-current-pw"
                  v-model="form.currentPassword"
                  :type="showCurrentPw ? 'text' : 'password'"
                  class="form-input"
                  placeholder="Enter current password to verify"
                  autocomplete="current-password"
                />
                <button
                  type="button"
                  class="pw-toggle-btn"
                  :aria-label="showCurrentPw ? 'Hide password' : 'Show password'"
                  @click="showCurrentPw = !showCurrentPw"
                >
                  <svg v-if="showCurrentPw" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                  <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- New Password -->
            <div class="form-group">
              <label for="acc-new-pw" class="form-label">
                New Password
              </label>
              <div class="pw-input-wrap">
                <input
                  id="acc-new-pw"
                  v-model="form.newPassword"
                  :type="showNewPw ? 'text' : 'password'"
                  class="form-input"
                  placeholder="Create a strict new password"
                  autocomplete="new-password"
                />
                <button
                  type="button"
                  class="pw-toggle-btn"
                  :aria-label="showNewPw ? 'Hide password' : 'Show password'"
                  @click="showNewPw = !showNewPw"
                >
                  <svg v-if="showNewPw" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                  <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- Confirm New Password -->
            <div v-if="form.newPassword" class="form-group animate-fade-in">
              <label for="acc-confirm-pw" class="form-label">
                Confirm New Password
              </label>
              <div class="pw-input-wrap">
                <input
                  id="acc-confirm-pw"
                  v-model="form.confirmPassword"
                  :type="showConfirmPw ? 'text' : 'password'"
                  class="form-input"
                  placeholder="Re-enter new password"
                  autocomplete="new-password"
                />
                <button
                  type="button"
                  class="pw-toggle-btn"
                  :aria-label="showConfirmPw ? 'Hide password' : 'Show password'"
                  @click="showConfirmPw = !showConfirmPw"
                >
                  <svg v-if="showConfirmPw" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                  <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- Strict Password Requirements Checklist (Live Feedback) -->
            <div v-if="form.newPassword" class="strict-rules-box animate-fade-in">
              <div class="rules-header">
                <span class="rules-title">STRICT PASSWORD REQUIREMENTS</span>
                <span class="rules-status" :class="passwordStrengthClass">
                  {{ passwordStrengthLabel }}
                </span>
              </div>

              <div class="rules-list">
                <div class="rule-item" :class="{ met: rules.length }">
                  <span class="rule-icon">{{ rules.length ? '✓' : '○' }}</span>
                  <span>At least 8 characters in length</span>
                </div>
                <div class="rule-item" :class="{ met: rules.uppercase }">
                  <span class="rule-icon">{{ rules.uppercase ? '✓' : '○' }}</span>
                  <span>At least one uppercase letter (A-Z)</span>
                </div>
                <div class="rule-item" :class="{ met: rules.lowercase }">
                  <span class="rule-icon">{{ rules.lowercase ? '✓' : '○' }}</span>
                  <span>At least one lowercase letter (a-z)</span>
                </div>
                <div class="rule-item" :class="{ met: rules.digit }">
                  <span class="rule-icon">{{ rules.digit ? '✓' : '○' }}</span>
                  <span>At least one numeric digit (0-9)</span>
                </div>
                <div class="rule-item" :class="{ met: rules.special }">
                  <span class="rule-icon">{{ rules.special ? '✓' : '○' }}</span>
                  <span>At least one special character (!@#$%^&*...)</span>
                </div>
                <div class="rule-item" :class="{ met: rules.differentFromCurrent }">
                  <span class="rule-icon">{{ rules.differentFromCurrent ? '✓' : '○' }}</span>
                  <span>Different from your current password</span>
                </div>
                <div v-if="form.confirmPassword" class="rule-item" :class="{ met: rules.matchesConfirm }">
                  <span class="rule-icon">{{ rules.matchesConfirm ? '✓' : '○' }}</span>
                  <span>Confirmation passwords match</span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- Footer Actions -->
      <div class="modal-footer">
        <button
          type="button"
          class="btn-editorial-ghost"
          @click="$emit('close')"
        >
          Cancel
        </button>
        <button
          type="button"
          class="btn-orange-primary"
          :disabled="isSaveDisabled || isSaving"
          @click="saveAccountSettings"
        >
          <span v-if="isSaving">Saving Changes…</span>
          <span v-else>Save Changes</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from "vue";

const props = defineProps({
  currentUser: {
    type: Object,
    default: null,
  },
  apiBase: {
    type: String,
    required: true,
  },
  getAuthHeaders: {
    type: Function,
    required: true,
  },
});

const emit = defineEmits(["close", "user-updated"]);

const form = reactive({
  name: props.currentUser?.name || "",
  email: props.currentUser?.email || "",
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const isSaving = ref(false);
const successMsg = ref("");
const errorMsg = ref("");

const showCurrentPw = ref(false);
const showNewPw = ref(false);
const showConfirmPw = ref(false);

const isGoogleUser = computed(() => {
  return props.currentUser?.email && !props.currentUser?.has_password && props.currentUser?.picture;
});

// Watch current user changes
watch(
  () => props.currentUser,
  (u) => {
    if (u) {
      form.name = u.name || "";
      form.email = u.email || "";
    }
  },
  { immediate: true }
);

// Strict Password Validation Computeds
const SPECIAL_CHARS = "!@#$%^&*()_+-=[]{};':\",.<>/?~`|\\";

const rules = computed(() => {
  const pw = form.newPassword || "";
  const currentPw = form.currentPassword || "";
  const confirmPw = form.confirmPassword || "";

  return {
    length: pw.length >= 8 && pw.length <= 128,
    uppercase: /[A-Z]/.test(pw),
    lowercase: /[a-z]/.test(pw),
    digit: /\d/.test(pw),
    special: [...pw].some((c) => SPECIAL_CHARS.includes(c)),
    differentFromCurrent: !currentPw || pw !== currentPw,
    matchesConfirm: confirmPw.length > 0 && pw === confirmPw,
  };
});

const isStrictPasswordValid = computed(() => {
  if (!form.newPassword) return true; // not changing password
  return (
    rules.value.length &&
    rules.value.uppercase &&
    rules.value.lowercase &&
    rules.value.digit &&
    rules.value.special &&
    rules.value.differentFromCurrent &&
    rules.value.matchesConfirm
  );
});

const passedRuleCount = computed(() => {
  let count = 0;
  if (rules.value.length) count++;
  if (rules.value.uppercase) count++;
  if (rules.value.lowercase) count++;
  if (rules.value.digit) count++;
  if (rules.value.special) count++;
  return count;
});

const passwordStrengthLabel = computed(() => {
  if (!form.newPassword) return "";
  const count = passedRuleCount.value;
  if (count <= 2) return "Weak";
  if (count <= 4) return "Medium";
  return "Strong";
});

const passwordStrengthClass = computed(() => {
  if (!form.newPassword) return "";
  const count = passedRuleCount.value;
  if (count <= 2) return "strength-weak";
  if (count <= 4) return "strength-medium";
  return "strength-strong";
});

const isSaveDisabled = computed(() => {
  if (!form.name || !form.name.trim()) return true;
  if (form.newPassword) {
    if (!isStrictPasswordValid.value) return true;
    if (props.currentUser?.has_password && !form.currentPassword.trim()) return true;
  }
  return false;
});

async function saveAccountSettings() {
  errorMsg.value = "";
  successMsg.value = "";
  isSaving.value = true;

  try {
    const payload = {
      name: form.name.trim(),
    };

    if (form.email && form.email.trim() !== props.currentUser?.email) {
      payload.email = form.email.trim();
    }

    if (form.newPassword) {
      if (props.currentUser?.has_password) {
        payload.current_password = form.currentPassword.trim();
      }
      payload.new_password = form.newPassword.trim();
      payload.confirm_password = form.confirmPassword.trim();
    }

    const res = await fetch(`${props.apiBase}/auth/profile`, {
      method: "PATCH",
      headers: {
        ...props.getAuthHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to update account settings");
    }

    successMsg.value = "Account settings updated successfully.";
    form.currentPassword = "";
    form.newPassword = "";
    form.confirmPassword = "";

    emit("user-updated", data);
  } catch (err) {
    errorMsg.value = err.message || "An error occurred while saving.";
  } finally {
    isSaving.value = false;
  }
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(28, 25, 23, 0.45);
  backdrop-filter: blur(3px);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.account-settings-card {
  background: var(--bg-card, #ffffff);
  border: 1px solid var(--border-subtle, #e5e7eb);
  border-radius: 12px;
  width: min(580px, 100%);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 12px 35px rgba(0, 0, 0, 0.14);
  overflow: hidden;
  animation: modalEnter 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modalEnter {
  from {
    opacity: 0;
    transform: scale(0.97) translateY(8px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-header {
  padding: 20px 24px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid var(--border-subtle, #e5e7eb);
}

.settings-kicker {
  display: block;
  font-family: var(--font-mono, monospace);
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--primary-orange, #ea580c);
  margin-bottom: 4px;
}

.settings-title {
  font-family: var(--font-serif, "Playfair Display", Georgia, serif);
  font-size: 1.35rem;
  font-weight: 600;
  color: var(--text-dark, #1c1917);
  margin: 0 0 4px;
}

.settings-subtitle {
  font-size: 0.8rem;
  color: var(--text-muted, #64748b);
  margin: 0;
}

.modal-close-btn {
  border: none;
  background: transparent;
  color: var(--text-muted, #64748b);
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s ease, color 0.15s ease;
}

.modal-close-btn:hover {
  background: var(--bg-hover, #f1f5f9);
  color: var(--text-dark, #1c1917);
}

.modal-scroll-body {
  padding: 20px 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.feedback-banner {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 0.82rem;
  display: flex;
  align-items: center;
  gap: 10px;
}

.success-banner {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}

.error-banner {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.settings-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-heading-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-dark, #1c1917);
  margin: 0;
}

.section-desc {
  font-size: 0.8rem;
  color: var(--text-muted, #64748b);
  margin: 0;
}

.account-type-badge,
.security-status-badge {
  font-family: var(--font-mono, monospace);
  font-size: 0.68rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--bg-elevated, #f8fafc);
  color: var(--text-muted, #64748b);
  border: 1px solid var(--border-subtle, #e2e8f0);
}

.security-status-badge.has-pwd {
  background: #f0fdf4;
  color: #15803d;
  border-color: #bbf7d0;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

@media (max-width: 520px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--text-dark, #1c1917);
}

.required-star {
  color: #dc2626;
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  font-size: 0.86rem;
  border: 1px solid var(--border-subtle, #d1d5db);
  border-radius: 7px;
  background: var(--bg-card, #ffffff);
  color: var(--text-dark, #1c1917);
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.form-input:focus {
  border-color: var(--primary-orange, #ea580c);
  box-shadow: 0 0 0 2px var(--primary-orange-soft, rgba(234, 88, 12, 0.15));
}

.form-input:disabled {
  background: var(--bg-page, #f8fafc);
  color: var(--text-muted, #94a3b8);
  cursor: not-allowed;
}

.field-hint {
  font-size: 0.72rem;
  color: var(--text-muted, #64748b);
}

.section-divider {
  height: 1px;
  background: var(--border-subtle, #e5e7eb);
}

.password-fields-box {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pw-input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.pw-input-wrap .form-input {
  padding-right: 36px;
}

.pw-toggle-btn {
  position: absolute;
  right: 8px;
  border: none;
  background: transparent;
  color: var(--text-muted, #64748b);
  cursor: pointer;
  padding: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.pw-toggle-btn:hover {
  color: var(--text-dark, #1c1917);
}

/* Strict Password Rules Box */
.strict-rules-box {
  background: var(--bg-elevated, #f8fafc);
  border: 1px solid var(--border-subtle, #e2e8f0);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rules-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rules-title {
  font-family: var(--font-mono, monospace);
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--text-muted, #64748b);
  letter-spacing: 0.05em;
}

.rules-status {
  font-family: var(--font-mono, monospace);
  font-size: 0.68rem;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
}

.rules-status.strength-weak {
  background: #fee2e2;
  color: #dc2626;
}

.rules-status.strength-medium {
  background: #fef3c7;
  color: #d97706;
}

.rules-status.strength-strong {
  background: #dcfce7;
  color: #16a34a;
}

.rules-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.rule-item {
  font-size: 0.76rem;
  color: var(--text-muted, #64748b);
  display: flex;
  align-items: center;
  gap: 8px;
  transition: color 0.15s ease;
}

.rule-item.met {
  color: #15803d;
  font-weight: 500;
}

.rule-icon {
  font-family: var(--font-mono, monospace);
  font-size: 0.72rem;
  width: 14px;
  text-align: center;
}

.modal-footer {
  padding: 14px 24px;
  border-top: 1px solid var(--border-subtle, #e5e7eb);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  background: var(--bg-elevated, #fafaf9);
}

.animate-fade-in {
  animation: fadeIn 0.15s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
