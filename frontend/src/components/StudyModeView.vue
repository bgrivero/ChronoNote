<template>
  <div
    class="study-mode-view"
    :class="{ 'zen-fullscreen': isFullscreen }"
    aria-label="Study Mode and Pomodoro Clock"
  >
    <!-- Study Mode Navigation & Control Bar -->
    <header class="study-header">
      <div class="study-kicker-group">
        <span class="study-kicker">FOCUS SANCTUARY &amp; POMODORO</span>
        <h1 class="study-title">Study &amp; Deep Work Sanctuary</h1>
        <p class="study-subtitle">
          Intentionally targeted study sessions tied to your projects, daily journal, and habit streak.
        </p>
      </div>

      <div class="study-header-actions">
        <!-- Sound Mute/Unmute Toggle -->
        <button
          type="button"
          class="btn-editorial-subtle"
          :title="isMuted ? 'Unmute Bell' : 'Mute Bell'"
          @click="isMuted = !isMuted"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path v-if="isMuted" d="M13.73 21a2 2 0 0 1-3.46 0M18.63 13A17.89 17.89 0 0 1 18 8M6.26 6.26A5.86 5.86 0 0 0 6 8c0 7-3 9-3 9h14M1 1l22 22" />
            <path v-else d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          <span v-if="isMuted">Muted</span>
          <span v-else>Bell On</span>
        </button>

        <!-- Ambient Noise (Synthesized Offline) -->
        <button
          type="button"
          class="btn-editorial-subtle"
          :class="{ active: isAmbientPlaying }"
          @click="toggleAmbientNoise"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M3 18v-6a9 9 0 0 1 18 0v6" />
            <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z" />
          </svg>
          <span>{{ isAmbientPlaying ? 'Ambient Rain Playing' : 'Play Soft Rain' }}</span>
        </button>

        <!-- Zen Fullscreen Toggle -->
        <button
          type="button"
          class="btn-editorial-subtle"
          @click="isFullscreen = !isFullscreen"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <polyline v-if="isFullscreen" points="4 14 10 14 10 20M20 10 14 10 14 4M14 10 21 3M3 21 10 14" />
            <polyline v-else points="15 3 21 3 21 9M9 21 3 21 3 15M21 3 14 10M3 21 10 14" />
          </svg>
          <span>{{ isFullscreen ? 'Exit Zen Fullscreen' : 'Zen Fullscreen' }}</span>
        </button>
      </div>
    </header>

    <!-- Project & Intention Setup Shelf -->
    <section class="study-setup-card">
      <div class="setup-grid">
        <!-- Project Selector -->
        <div class="setup-field">
          <label class="setup-label" for="study-project-select">Target Project</label>
          <select
            id="study-project-select"
            v-model="selectedProjectId"
            class="setup-select"
            @change="onProjectChange"
          >
            <option :value="null">General Study / Uncategorized</option>
            <option
              v-for="p in projects"
              :key="p.id"
              :value="p.id"
            >
              {{ p.name }} ({{ p.status }})
            </option>
          </select>
        </div>

        <!-- Task Selector (Optional) -->
        <div class="setup-field">
          <label class="setup-label" for="study-task-select">Associated Task (Optional)</label>
          <select
            id="study-task-select"
            v-model="selectedTaskId"
            class="setup-select"
            :disabled="!availableTasks.length"
          >
            <option :value="null">-- Entire Project Scope --</option>
            <option
              v-for="t in availableTasks"
              :key="t.id"
              :value="t.id"
            >
              {{ t.title }} [{{ t.status }}]
            </option>
          </select>
        </div>

        <!-- Note Selector (For Split Canvas) -->
        <div class="setup-field">
          <label class="setup-label" for="study-note-select">Reference / Study Note</label>
          <select
            id="study-note-select"
            v-model="selectedNoteId"
            class="setup-select"
            @change="onNoteChange"
          >
            <option :value="null">Free Scratchpad</option>
            <option
              v-for="n in projectNotes"
              :key="n.id"
              :value="n.id"
            >
              {{ n.title }}
            </option>
          </select>
        </div>

        <!-- Session Intention -->
        <div class="setup-field setup-field-wide">
          <label class="setup-label" for="study-intention-input">Current Intention / Micro-Goal</label>
          <div class="intention-input-wrap">
            <input
              id="study-intention-input"
              v-model="sessionIntention"
              type="text"
              class="setup-input"
              placeholder="e.g. Master dynamic programming, Review chapter 4, Draft specs…"
            />
            <div class="quick-tags">
              <button
                v-for="tag in quickIntentions"
                :key="tag"
                type="button"
                class="quick-tag-pill"
                @click="sessionIntention = tag"
              >
                {{ tag }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Main Split Canvas: Left Note Editor & Right Pomodoro Clock -->
    <div class="study-main-split">
      <!-- Left: Active Study / Scratchpad Note -->
      <section class="study-note-pane">
        <div class="note-pane-header">
          <div class="note-title-badge">
            <svg class="badge-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            <span class="badge-text">{{ activeNoteTitle }}</span>
          </div>

          <div class="note-quick-actions">
            <button
              type="button"
              class="note-btn-action"
              @click="insertNoteSnippet('- [ ] Focus Key Takeaway: ')"
            >
              + Key Takeaway
            </button>
            <button
              type="button"
              class="note-btn-action"
              @click="insertNoteSnippet('- [ ] Question to resolve: ')"
            >
              + Question
            </button>
            <button
              type="button"
              class="note-btn-action"
              :disabled="isSavingNote"
              @click="saveCurrentStudyNote"
            >
              {{ isSavingNote ? 'Saving…' : 'Save Note' }}
            </button>
          </div>
        </div>

        <div class="study-editor-area">
          <textarea
            ref="studyTextarea"
            v-model="activeNoteContent"
            class="study-textarea"
            placeholder="Write your study notes, reflections, formulas, and insights here during your Pomodoro session…"
          ></textarea>
        </div>
      </section>

      <!-- Right: Pomodoro Clock & Stats -->
      <section class="study-clock-pane">
        <!-- Interval Mode Tabs -->
        <div class="timer-mode-tabs" role="tablist">
          <button
            type="button"
            class="mode-tab-btn"
            :class="{ active: activeMode === 'focus' }"
            @click="switchMode('focus')"
          >
            Focus ({{ focusDurationMin }}m)
          </button>
          <button
            type="button"
            class="mode-tab-btn"
            :class="{ active: activeMode === 'short_break' }"
            @click="switchMode('short_break')"
          >
            Short Break ({{ shortBreakDurationMin }}m)
          </button>
          <button
            type="button"
            class="mode-tab-btn"
            :class="{ active: activeMode === 'long_break' }"
            @click="switchMode('long_break')"
          >
            Long Break ({{ longBreakDurationMin }}m)
          </button>
        </div>

        <!-- Radial Progress Clock -->
        <div class="clock-display-wrap">
          <svg class="progress-ring-svg" viewBox="0 0 280 280">
            <circle
              class="progress-ring-bg"
              stroke-width="10"
              cx="140"
              cy="140"
              r="120"
              fill="transparent"
            />
            <circle
              class="progress-ring-fg"
              :class="activeMode"
              stroke-width="10"
              stroke-linecap="round"
              cx="140"
              cy="140"
              r="120"
              fill="transparent"
              :stroke-dasharray="circumference"
              :stroke-dashoffset="strokeDashoffset"
            />
          </svg>

          <div class="clock-inner-content">
            <span class="clock-mode-label">{{ modeLabel }}</span>
            <div class="clock-digits">{{ formattedRemaining }}</div>
            <span class="clock-target-project">
              {{ currentProjectName }}
            </span>
            <span class="clock-cycle-label">
              Pomodoro #{{ (pomoCycleCount % 4) + 1 }} of 4
            </span>
          </div>
        </div>

        <!-- Clock Play/Pause/Skip Controls -->
        <div class="clock-controls">
          <button
            type="button"
            class="btn-clock-toggle"
            :class="{ running: isRunning }"
            @click="toggleTimer"
          >
            <span v-if="!isRunning">▶ Start Session</span>
            <span v-else>⏸ Pause</span>
          </button>

          <button
            type="button"
            class="btn-clock-secondary"
            title="Skip to next interval"
            @click="skipInterval"
          >
            ⏭ Skip
          </button>

          <button
            type="button"
            class="btn-clock-secondary"
            title="Reset timer"
            @click="resetTimer"
          >
            ↺ Reset
          </button>
        </div>

        <!-- Auto-Log Options -->
        <div class="study-options-strip">
          <label class="study-checkbox-label">
            <input v-model="autoLogToJournal" type="checkbox" />
            <span>Auto-log completed session to Daily Journal</span>
          </label>
          <label class="study-checkbox-label">
            <input v-model="syncHabit" type="checkbox" />
            <span>Sync with 'Study' habit streak</span>
          </label>
        </div>

        <!-- Metric KPI Pills -->
        <div class="study-kpis">
          <div class="kpi-mini-card">
            <span class="kpi-mini-val">{{ stats.today_focus_minutes || 0 }}m</span>
            <span class="kpi-mini-lbl">Focused Today</span>
          </div>
          <div class="kpi-mini-card">
            <span class="kpi-mini-val">{{ stats.today_sessions_count || 0 }}</span>
            <span class="kpi-mini-lbl">Pomodoros Done</span>
          </div>
          <div class="kpi-mini-card">
            <span class="kpi-mini-val">{{ stats.current_streak_days || 0 }}d</span>
            <span class="kpi-mini-lbl">Study Streak</span>
          </div>
        </div>

        <!-- Recent Completed Sessions -->
        <div v-if="stats.recent_sessions && stats.recent_sessions.length" class="recent-sessions-box">
          <h4 class="recent-title">Recent Completed Sessions</h4>
          <ul class="recent-list">
            <li
              v-for="s in stats.recent_sessions.slice(0, 4)"
              :key="s.id"
              class="recent-item"
            >
              <span class="recent-dot" :style="{ backgroundColor: s.project_color || '#6366f1' }"></span>
              <div class="recent-details">
                <span class="recent-name">{{ s.project_name || 'General Study' }}</span>
                <span class="recent-intent">{{ s.intention || 'Focused interval' }}</span>
              </div>
              <span class="recent-time">{{ s.duration_minutes }}m</span>
            </li>
          </ul>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  projects: {
    type: Array,
    default: () => [],
  },
  notes: {
    type: Array,
    default: () => [],
  },
  tasks: {
    type: Array,
    default: () => [],
  },
  selectedJournalDate: {
    type: String,
    default: () => new Date().toISOString().split("T")[0],
  },
});

const emit = defineEmits(["session-completed", "note-updated", "notify"]);

// Fullscreen toggle
const isFullscreen = ref(false);

// Mode durations (in minutes)
const focusDurationMin = ref(25);
const shortBreakDurationMin = ref(5);
const longBreakDurationMin = ref(15);

// Timer State
const activeMode = ref("focus"); // 'focus' | 'short_break' | 'long_break'
const isRunning = ref(false);
const secondsRemaining = ref(25 * 60);
const pomoCycleCount = ref(0);
const isMuted = ref(false);
const isAmbientPlaying = ref(false);

// Project & Note Selection
const selectedProjectId = ref(null);
const selectedTaskId = ref(null);
const selectedNoteId = ref(null);
const sessionIntention = ref("");
const autoLogToJournal = ref(true);
const syncHabit = ref(true);

// Note editor scratchpad
const activeNoteContent = ref("");
const isSavingNote = ref(false);
const scratchpadStorageKey = "chrononote_study_scratchpad";

// Quick Intention suggestions
const quickIntentions = [
  "Chapter Reading",
  "Code Practice",
  "Spec Drafting",
  "Problem Solving",
  "Flashcards / Review",
];

// Stats
const stats = ref({
  total_focus_minutes: 0,
  today_focus_minutes: 0,
  today_sessions_count: 0,
  current_streak_days: 0,
  project_breakdown: [],
  recent_sessions: [],
});

let timerInterval = null;
let audioCtx = null;
let ambientSourceNode = null;

// Progress circle math
const radius = 120;
const circumference = 2 * Math.PI * radius;

const totalSecondsForMode = computed(() => {
  if (activeMode.value === "focus") return focusDurationMin.value * 60;
  if (activeMode.value === "short_break") return shortBreakDurationMin.value * 60;
  return longBreakDurationMin.value * 60;
});

const strokeDashoffset = computed(() => {
  const fraction = secondsRemaining.value / (totalSecondsForMode.value || 1);
  return circumference * (1 - fraction);
});

const formattedRemaining = computed(() => {
  const m = Math.floor(secondsRemaining.value / 60);
  const s = secondsRemaining.value % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
});

const modeLabel = computed(() => {
  if (activeMode.value === "focus") return "Focus Session";
  if (activeMode.value === "short_break") return "Short Break";
  return "Long Break";
});

const currentProject = computed(() => {
  if (!selectedProjectId.value) return null;
  return props.projects.find((p) => p.id === selectedProjectId.value) || null;
});

const currentProjectName = computed(() => {
  return currentProject.value ? currentProject.value.name : "General Study";
});

const availableTasks = computed(() => {
  if (!selectedProjectId.value) return [];
  return props.tasks.filter((t) => t.project_id === selectedProjectId.value);
});

const projectNotes = computed(() => {
  if (!selectedProjectId.value) {
    return props.notes.filter((n) => !n.is_daily_note);
  }
  return props.notes.filter(
    (n) => n.project_id === selectedProjectId.value && !n.is_daily_note
  );
});

const activeNote = computed(() => {
  if (!selectedNoteId.value) return null;
  return props.notes.find((n) => n.id === selectedNoteId.value) || null;
});

const activeNoteTitle = computed(() => {
  if (activeNote.value) return activeNote.value.title;
  return "Freeform Study Scratchpad";
});

// Watch note selection to populate text
function onNoteChange() {
  if (activeNote.value) {
    activeNoteContent.value = activeNote.value.content_md || "";
  } else {
    activeNoteContent.value = localStorage.getItem(scratchpadStorageKey) || "";
  }
}

function onProjectChange() {
  selectedTaskId.value = null;
  // If current note is not in project, reset
  if (selectedNoteId.value && activeNote.value && activeNote.value.project_id !== selectedProjectId.value) {
    selectedNoteId.value = null;
    onNoteChange();
  }
}

function insertNoteSnippet(snippet) {
  activeNoteContent.value = (activeNoteContent.value || "").trimEnd() + `\n${snippet}`;
}

async function saveCurrentStudyNote() {
  isSavingNote.value = true;
  try {
    if (activeNote.value) {
      const res = await fetch(`/api/notes/${activeNote.value.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content_md: activeNoteContent.value }),
      });
      if (res.ok) {
        const updated = await res.json();
        emit("note-updated", updated);
        emit("notify", { type: "success", message: `Saved ${activeNote.value.title}` });
      }
    } else {
      localStorage.setItem(scratchpadStorageKey, activeNoteContent.value);
      emit("notify", { type: "success", message: "Saved Scratchpad" });
    }
  } catch (err) {
    console.error("Failed to save note:", err);
  } finally {
    isSavingNote.value = false;
  }
}

// Timer Controls
function switchMode(mode) {
  isRunning.value = false;
  clearInterval(timerInterval);
  activeMode.value = mode;
  if (mode === "focus") {
    secondsRemaining.value = focusDurationMin.value * 60;
  } else if (mode === "short_break") {
    secondsRemaining.value = shortBreakDurationMin.value * 60;
  } else {
    secondsRemaining.value = longBreakDurationMin.value * 60;
  }
}

function toggleTimer() {
  if (isRunning.value) {
    pauseTimer();
  } else {
    startTimer();
  }
}

function startTimer() {
  isRunning.value = true;
  timerInterval = setInterval(() => {
    if (secondsRemaining.value > 0) {
      secondsRemaining.value -= 1;
    } else {
      onIntervalComplete();
    }
  }, 1000);
}

function pauseTimer() {
  isRunning.value = false;
  clearInterval(timerInterval);
}

function resetTimer() {
  pauseTimer();
  switchMode(activeMode.value);
}

function skipInterval() {
  pauseTimer();
  if (activeMode.value === "focus") {
    pomoCycleCount.value += 1;
    if (pomoCycleCount.value % 4 === 0) {
      switchMode("long_break");
    } else {
      switchMode("short_break");
    }
  } else {
    switchMode("focus");
  }
}

// Sound Synthesis (Web Audio API)
function playHarmonicBell() {
  if (isMuted.value) return;
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const now = ctx.currentTime;
    
    // Fundamental tone + subtle harmonic shimmer
    [528, 1056].forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, now);
      gain.gain.setValueAtTime(idx === 0 ? 0.25 : 0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 1.8);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 2.0);
    });
  } catch (err) {
    console.warn("AudioContext not supported or blocked:", err);
  }
}

// Synthesize Gentle Rain / White Noise with low-pass filter
function toggleAmbientNoise() {
  if (isAmbientPlaying.value) {
    stopAmbientNoise();
  } else {
    startAmbientNoise();
  }
}

function startAmbientNoise() {
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === "suspended") {
      audioCtx.resume();
    }

    const bufferSize = audioCtx.sampleRate * 2;
    const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
    const data = buffer.getChannelData(0);
    let lastOut = 0.0;

    // Pink / soft rain noise approximation
    for (let i = 0; i < bufferSize; i++) {
      const white = Math.random() * 2 - 1;
      lastOut = (lastOut + 0.02 * white) / 1.02;
      data[i] = lastOut * 3.5;
    }

    ambientSourceNode = audioCtx.createBufferSource();
    ambientSourceNode.buffer = buffer;
    ambientSourceNode.loop = true;

    const filter = audioCtx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(800, audioCtx.currentTime);

    const gain = audioCtx.createGain();
    gain.gain.setValueAtTime(0.12, audioCtx.currentTime);

    ambientSourceNode.connect(filter);
    filter.connect(gain);
    gain.connect(audioCtx.destination);

    ambientSourceNode.start(0);
    isAmbientPlaying.value = true;
  } catch (err) {
    console.warn("Failed to generate ambient noise:", err);
  }
}

function stopAmbientNoise() {
  if (ambientSourceNode) {
    try {
      ambientSourceNode.stop();
      ambientSourceNode.disconnect();
    } catch (e) {}
    ambientSourceNode = null;
  }
  isAmbientPlaying.value = false;
}

// On interval finished
async function onIntervalComplete() {
  pauseTimer();
  playHarmonicBell();

  if (activeMode.value === "focus") {
    // Record session to backend
    await recordCompletedSession();
    pomoCycleCount.value += 1;

    // Switch to break
    if (pomoCycleCount.value % 4 === 0) {
      switchMode("long_break");
    } else {
      switchMode("short_break");
    }
  } else {
    // Break finished, return to focus
    switchMode("focus");
  }
}

async function recordCompletedSession() {
  const duration = focusDurationMin.value;
  try {
    const payload = {
      project_id: selectedProjectId.value,
      task_id: selectedTaskId.value,
      note_id: selectedNoteId.value,
      duration_minutes: duration,
      session_type: "focus",
      intention: sessionIntention.value || "General study session",
      notes: activeNoteContent.value ? activeNoteContent.value.slice(0, 300) : "",
      auto_log_to_journal: autoLogToJournal.value,
      sync_habit_slug: syncHabit.value ? "study" : null,
    };

    const res = await fetch("/api/study/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      const created = await res.json();
      emit("session-completed", created);
      emit("notify", {
        type: "success",
        message: `Completed ${duration}m Focus Session on ${currentProjectName.value}!`,
      });
      await fetchStudyStats();
    }
  } catch (err) {
    console.error("Failed to record study session:", err);
  }
}

async function fetchStudyStats() {
  try {
    const res = await fetch("/api/study/stats");
    if (res.ok) {
      stats.value = await res.json();
    }
  } catch (err) {
    console.error("Failed to fetch study stats:", err);
  }
}

onMounted(() => {
  onNoteChange();
  fetchStudyStats();
});

onBeforeUnmount(() => {
  clearInterval(timerInterval);
  stopAmbientNoise();
  if (audioCtx) {
    try {
      audioCtx.close();
    } catch (e) {}
  }
});
</script>

<style scoped>
.study-mode-view {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 2rem 2.5rem;
  max-width: 1360px;
  margin: 0 auto;
  width: 100%;
  color: var(--color-ink, #2d2a26);
  background: var(--color-paper, #fdfbf7);
  box-sizing: border-box;
}

.zen-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 9999;
  max-width: 100%;
  height: 100vh;
  overflow-y: auto;
  background: var(--color-paper, #fdfbf7);
  padding: 2rem 4rem;
}

/* Header */
.study-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid var(--color-border, #e5dfd5);
  padding-bottom: 1.25rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.study-kicker {
  font-family: var(--font-mono, monospace);
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--color-muted, #7c7467);
  font-weight: 600;
}

.study-title {
  font-family: var(--font-serif, "Playfair Display", Georgia, serif);
  font-size: 1.85rem;
  margin: 0.2rem 0 0.35rem;
  font-weight: 700;
  color: var(--color-ink, #2d2a26);
}

.study-subtitle {
  font-size: 0.92rem;
  color: var(--color-muted, #7c7467);
  margin: 0;
}

.study-header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.btn-editorial-subtle {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.85rem;
  border: 1px solid var(--color-border, #e5dfd5);
  border-radius: 6px;
  background: #fff;
  color: var(--color-ink, #2d2a26);
  font-size: 0.82rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-editorial-subtle:hover {
  background: #f7f3ee;
  border-color: #cbbfb0;
}

.btn-editorial-subtle.active {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1e40af;
}

/* Setup Card */
.study-setup-card {
  background: #fff;
  border: 1px solid var(--color-border, #e5dfd5);
  border-radius: 10px;
  padding: 1.25rem 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.setup-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.2rem;
}

.setup-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.setup-field-wide {
  grid-column: 1 / -1;
}

.setup-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-muted, #7c7467);
}

.setup-select,
.setup-input {
  width: 100%;
  padding: 0.55rem 0.75rem;
  border: 1px solid var(--color-border, #e5dfd5);
  border-radius: 6px;
  font-size: 0.88rem;
  background: #fcfbf9;
  color: var(--color-ink, #2d2a26);
  box-sizing: border-box;
}

.setup-select:focus,
.setup-input:focus {
  outline: none;
  border-color: #4f46e5;
  background: #fff;
}

.intention-input-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.quick-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.quick-tag-pill {
  padding: 0.25rem 0.6rem;
  border: 1px dashed var(--color-border, #e5dfd5);
  border-radius: 14px;
  background: #faf8f5;
  font-size: 0.76rem;
  color: var(--color-muted, #7c7467);
  cursor: pointer;
  transition: all 0.15s ease;
}

.quick-tag-pill:hover {
  background: #f0ebe1;
  color: var(--color-ink, #2d2a26);
}

/* Split Main */
.study-main-split {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 1.75rem;
  align-items: start;
}

/* Left Note Pane */
.study-note-pane {
  background: #fff;
  border: 1px solid var(--color-border, #e5dfd5);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  height: 580px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
  overflow: hidden;
}

.note-pane-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.85rem 1.25rem;
  border-bottom: 1px solid var(--color-border, #e5dfd5);
  background: #faf8f5;
}

.note-title-badge {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 600;
  font-size: 0.9rem;
}

.note-quick-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.note-btn-action {
  padding: 0.35rem 0.65rem;
  border: 1px solid var(--color-border, #e5dfd5);
  border-radius: 5px;
  background: #fff;
  font-size: 0.78rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.note-btn-action:hover {
  background: #f0ece3;
}

.study-editor-area {
  flex: 1;
  display: flex;
  position: relative;
}

.study-textarea {
  width: 100%;
  height: 100%;
  border: none;
  resize: none;
  padding: 1.25rem;
  font-family: var(--font-serif, "Playfair Display", Georgia, serif);
  font-size: 0.96rem;
  line-height: 1.68;
  color: var(--color-ink, #2d2a26);
  background: #fff;
  box-sizing: border-box;
}

.study-textarea:focus {
  outline: none;
}

/* Right Clock Pane */
.study-clock-pane {
  background: #fff;
  border: 1px solid var(--color-border, #e5dfd5);
  border-radius: 10px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.timer-mode-tabs {
  display: flex;
  background: #f5efe6;
  padding: 0.3rem;
  border-radius: 8px;
  gap: 0.25rem;
  width: 100%;
}

.mode-tab-btn {
  flex: 1;
  padding: 0.5rem 0.4rem;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--color-muted, #7c7467);
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
}

.mode-tab-btn.active {
  background: #fff;
  color: var(--color-ink, #2d2a26);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

/* Clock Radial Display */
.clock-display-wrap {
  position: relative;
  width: 250px;
  height: 250px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0.5rem 0;
}

.progress-ring-svg {
  position: absolute;
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.progress-ring-bg {
  stroke: #ece6dc;
}

.progress-ring-fg {
  transition: stroke-dashoffset 0.5s ease;
}

.progress-ring-fg.focus {
  stroke: #e06c53; /* Warm terracotta */
}

.progress-ring-fg.short_break {
  stroke: #10b981; /* Sage emerald */
}

.progress-ring-fg.long_break {
  stroke: #6366f1; /* Calming indigo */
}

.clock-inner-content {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.clock-mode-label {
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-muted, #7c7467);
  font-weight: 600;
}

.clock-digits {
  font-family: var(--font-mono, monospace);
  font-size: 3.2rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-ink, #2d2a26);
  line-height: 1.1;
  margin: 0.15rem 0;
}

.clock-target-project {
  font-size: 0.84rem;
  font-weight: 600;
  color: #4b5563;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.clock-cycle-label {
  font-size: 0.72rem;
  color: var(--color-muted, #7c7467);
  margin-top: 0.2rem;
}

/* Controls */
.clock-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
}

.btn-clock-toggle {
  flex: 2;
  padding: 0.75rem 1rem;
  border: none;
  border-radius: 8px;
  background: #2d2a26;
  color: #fff;
  font-weight: 600;
  font-size: 0.92rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-clock-toggle:hover {
  background: #1c1a17;
}

.btn-clock-toggle.running {
  background: #e06c53;
}

.btn-clock-secondary {
  flex: 1;
  padding: 0.75rem 0.5rem;
  border: 1px solid var(--color-border, #e5dfd5);
  border-radius: 8px;
  background: #fff;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-ink, #2d2a26);
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-clock-secondary:hover {
  background: #f7f3ee;
}

/* Checkboxes */
.study-options-strip {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  width: 100%;
  border-top: 1px solid #f0ece3;
  padding-top: 0.85rem;
}

.study-checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.78rem;
  color: var(--color-muted, #7c7467);
  cursor: pointer;
}

/* KPIs */
.study-kpis {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  width: 100%;
}

.kpi-mini-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.65rem 0.4rem;
  border-radius: 6px;
  background: #faf8f5;
  border: 1px solid #f0ebe2;
}

.kpi-mini-val {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--color-ink, #2d2a26);
}

.kpi-mini-lbl {
  font-size: 0.68rem;
  color: var(--color-muted, #7c7467);
  text-transform: uppercase;
  margin-top: 0.15rem;
}

/* Recent list */
.recent-sessions-box {
  width: 100%;
  border-top: 1px solid #f0ece3;
  padding-top: 0.85rem;
}

.recent-title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-muted, #7c7467);
  margin: 0 0 0.5rem;
}

.recent-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.recent-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.78rem;
}

.recent-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.recent-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.recent-name {
  font-weight: 600;
  color: var(--color-ink, #2d2a26);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recent-intent {
  font-size: 0.72rem;
  color: var(--color-muted, #7c7467);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recent-time {
  font-family: var(--font-mono, monospace);
  font-weight: 600;
  color: #6b7280;
}

@media (max-width: 1024px) {
  .study-main-split {
    grid-template-columns: 1fr;
  }
  .setup-grid {
    grid-template-columns: 1fr;
  }
}
</style>
