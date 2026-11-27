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
    <div class="study-body-content">
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

        <!-- Radial Progress Sundial -->
        <div class="clock-display-wrap">
          <svg class="progress-ring-svg" viewBox="0 0 280 280">
            <!-- Horological 12-Hour Architectural Tick Marks -->
            <g class="dial-ticks" stroke="rgba(28, 21, 17, 0.22)" stroke-width="1.5" stroke-linecap="butt">
              <line
                v-for="tick in 12"
                :key="tick"
                x1="140"
                y1="6"
                x2="140"
                :y2="tick % 3 === 0 ? 18 : 13"
                :transform="`rotate(${tick * 30} 140 140)`"
              />
            </g>
            <circle
              class="progress-ring-bg"
              stroke-width="9"
              cx="140"
              cy="140"
              r="116"
              fill="transparent"
            />
            <circle
              class="progress-ring-fg"
              :class="activeMode"
              stroke-width="9"
              stroke-linecap="butt"
              cx="140"
              cy="140"
              r="116"
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
            <span v-if="sessionIntention" class="clock-intention-italic">
              {{ sessionIntention }}
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
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { computeRemainingSeconds } from "../composables/useStudyPomodoro.js";

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
  apiBase: {
    type: String,
    default: "/api",
  },
  getAuthHeaders: {
    type: Function,
    default: () => ({}),
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
let targetEndTime = null;
let audioCtx = null;
let ambientSourceNode = null;

// Progress circle math
const radius = 116;
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
      const headers = {
        "Content-Type": "application/json",
        ...props.getAuthHeaders(),
      };
      const res = await fetch(`${props.apiBase}/notes/${activeNote.value.id}`, {
        method: "PUT",
        headers,
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
  pauseTimer();
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

function syncTimerWithTarget() {
  if (!targetEndTime || !isRunning.value) return;
  const remaining = computeRemainingSeconds(targetEndTime);
  secondsRemaining.value = remaining;
  if (remaining <= 0) {
    secondsRemaining.value = 0;
    pauseTimer();
    onIntervalComplete();
  }
}

function startTimer() {
  if (secondsRemaining.value <= 0) {
    secondsRemaining.value = totalSecondsForMode.value;
  }
  isRunning.value = true;
  targetEndTime = Date.now() + secondsRemaining.value * 1000;
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
  timerInterval = setInterval(() => {
    syncTimerWithTarget();
  }, 250);
}

function pauseTimer() {
  if (isRunning.value && targetEndTime) {
    secondsRemaining.value = computeRemainingSeconds(targetEndTime);
  }
  isRunning.value = false;
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
  targetEndTime = null;
}

function resetTimer() {
  pauseTimer();
  switchMode(activeMode.value);
}

function handleVisibilityChange() {
  if (isRunning.value && typeof document !== "undefined" && !document.hidden) {
    syncTimerWithTarget();
  }
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
let isCompletingInterval = false;

async function onIntervalComplete() {
  if (isCompletingInterval) return;
  isCompletingInterval = true;
  pauseTimer();
  playHarmonicBell();

  try {
    if (activeMode.value === "focus") {
      // Auto-save active note if content exists
      if (activeNote.value && activeNoteContent.value) {
        await saveCurrentStudyNote();
      }
      // Record session to backend and journal
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
  } catch (err) {
    console.error("Error during onIntervalComplete:", err);
  } finally {
    isCompletingInterval = false;
  }
}

async function recordCompletedSession() {
  const duration = focusDurationMin.value;
  try {
    const todayIsoStr = props.selectedJournalDate || new Date().toISOString().split("T")[0];
    const payload = {
      project_id: selectedProjectId.value,
      task_id: selectedTaskId.value,
      note_id: selectedNoteId.value,
      duration_minutes: duration,
      session_type: "focus",
      intention: sessionIntention.value || "General study session",
      notes: (activeNoteContent.value || "").trim(),
      auto_log_to_journal: autoLogToJournal.value,
      sync_habit_slug: syncHabit.value ? "study" : null,
      session_date: todayIsoStr,
    };

    const headers = {
      "Content-Type": "application/json",
      ...props.getAuthHeaders(),
    };

    let created = null;
    try {
      const res = await fetch(`${props.apiBase}/study/sessions`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        created = await res.json();
      } else {
        console.warn("Backend study session record returned status:", res.status);
      }
    } catch (fetchErr) {
      console.warn("Network error recording study session:", fetchErr);
    }

    if (!created) {
      created = {
        ...payload,
        id: Date.now(),
        project_name: currentProjectName.value,
        project_color: currentProject.value?.color || "#6366f1",
        task_title: props.tasks.find((t) => t.id === selectedTaskId.value)?.title || null,
        created_at: new Date().toISOString(),
      };
    }

    emit("session-completed", created);
    emit("notify", {
      type: "success",
      message: `Completed ${duration}m Focus Session on ${currentProjectName.value}!`,
    });
    await fetchStudyStats();
  } catch (err) {
    console.error("Failed to record study session:", err);
  }
}

async function fetchStudyStats() {
  try {
    const res = await fetch(`${props.apiBase}/study/stats`, {
      headers: props.getAuthHeaders(),
    });
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
  if (typeof document !== "undefined") {
    document.addEventListener("visibilitychange", handleVisibilityChange);
  }
});

onBeforeUnmount(() => {
  clearInterval(timerInterval);
  if (typeof document !== "undefined") {
    document.removeEventListener("visibilitychange", handleVisibilityChange);
  }
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
  gap: 0;
  padding: 0;
  max-width: none;
  margin: 0;
  width: 100%;
  color: var(--text-dark);
  background: transparent;
  box-sizing: border-box;
}

.zen-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 9999;
  max-width: 100%;
  height: 100vh;
  overflow-y: auto;
  background: var(--bg-page);
  padding: 0;
}

/* Header: Dark-Bronze Architectural Fascia */
.study-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-spine);
  color: var(--on-spine);
  min-height: 54px;
  border-bottom: 1px solid var(--spine-line);
  padding: 12px 28px 14px calc(var(--rail-w) + 16px);
  position: relative;
  flex-wrap: wrap;
  gap: 1rem;
  transition: padding-left 0.22s cubic-bezier(0.22, 1, 0.36, 1);
}

.study-header::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 2px;
  background: var(--stripe-gradient);
  pointer-events: none;
}

:global(.editorial-app.is-nav-open) .study-header,
.zen-fullscreen .study-header {
  padding-left: 28px;
}

.study-body-content {
  padding: 22px 32px 48px;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-width: 1420px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}

.study-kicker {
  font-family: var(--font-mono, monospace);
  font-size: 0.66rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent-amber);
  font-weight: 600;
}

.study-title {
  font-family: var(--font-serif, Georgia, serif);
  font-size: 2rem;
  margin: 0.1rem 0 0.15rem;
  font-weight: 500;
  line-height: 1.04;
  letter-spacing: -0.02em;
  color: var(--on-spine);
}

.study-subtitle {
  font-size: 0.84rem;
  color: var(--on-spine-muted);
  margin: 0;
}

.study-header-actions {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-wrap: wrap;
}

.btn-editorial-subtle {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.46rem 0.85rem;
  border: 1px solid var(--spine-line-strong);
  border-radius: 3px;
  background: var(--bg-spine-elevated);
  color: var(--on-spine);
  font-family: var(--font-sans);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-editorial-subtle:hover {
  background: var(--spine-hover);
  border-color: var(--spine-line-strong);
}

.btn-editorial-subtle.active {
  background: rgba(226, 151, 54, 0.18);
  border-color: var(--accent-amber);
  color: var(--accent-amber);
}

/* Setup Card */
.study-setup-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 2px;
  padding: 1.15rem 1.4rem;
  box-shadow: none;
}

.setup-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.1rem;
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
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}

.setup-select,
.setup-input {
  width: 100%;
  padding: 0.52rem 0.72rem;
  border: 1px solid var(--border-subtle);
  border-radius: 3px;
  font-family: var(--font-sans);
  font-size: 0.86rem;
  background: var(--bg-page);
  color: var(--text-dark);
  box-sizing: border-box;
}

.setup-select:focus,
.setup-input:focus {
  outline: none;
  border-color: var(--primary-orange);
  background: var(--paper);
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
  padding: 0.22rem 0.6rem;
  border: 1px dashed var(--border-strong);
  border-radius: 2px;
  background: var(--bg-page);
  font-size: 0.75rem;
  color: var(--text-body);
  cursor: pointer;
  transition: all 0.15s ease;
}

.quick-tag-pill:hover {
  background: var(--primary-orange-soft);
  border-color: var(--primary-orange-border);
  color: var(--primary-orange);
}

/* Split Main: Continuous Leaded-Glass Folio */
.study-main-split {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 0;
  align-items: stretch;
  border: 1px solid var(--border-strong);
  background: var(--bg-card);
}

/* Left Note Pane */
.study-note-pane {
  background: var(--bg-card);
  border: none;
  border-right: 1px solid var(--border-subtle);
  border-radius: 0;
  display: flex;
  flex-direction: column;
  height: 590px;
  box-shadow: none;
  overflow: hidden;
}

.note-pane-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.85rem 1.25rem;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-page);
  gap: 0.75rem;
  flex-wrap: wrap;
}

.note-title-badge {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-family: var(--font-serif);
  font-weight: 600;
  font-size: 1.08rem;
  color: var(--text-dark);
}

.note-quick-actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.note-btn-action {
  padding: 0.34rem 0.68rem;
  border: 1px solid var(--border-subtle);
  border-radius: 3px;
  background: var(--bg-card);
  color: var(--text-body);
  font-family: var(--font-sans);
  font-size: 0.76rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.note-btn-action:hover {
  background: var(--primary-orange-soft);
  border-color: var(--primary-orange-border);
  color: var(--primary-orange);
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
  padding: 1.35rem 1.5rem;
  font-family: var(--font-sans);
  font-size: 0.96rem;
  line-height: 1.7;
  color: var(--text-dark);
  background: var(--bg-card);
  box-sizing: border-box;
}

.study-textarea:focus {
  outline: none;
}

/* Right Clock Pane */
.study-clock-pane {
  background: var(--bg-card);
  border: none;
  border-radius: 0;
  padding: 1.5rem 1.65rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.25rem;
  box-shadow: none;
}

.timer-mode-tabs {
  display: flex;
  background: var(--bg-page);
  border: 1px solid var(--border-subtle);
  padding: 3px;
  border-radius: 3px;
  gap: 2px;
  width: 100%;
}

.mode-tab-btn {
  flex: 1;
  padding: 0.48rem 0.4rem;
  border: none;
  background: transparent;
  border-radius: 2px;
  font-family: var(--font-sans);
  font-size: 0.77rem;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: center;
}

.mode-tab-btn.active {
  background: var(--ink-surface);
  color: var(--on-ink);
  font-weight: 600;
}

/* Clock Radial Sundial Display */
.clock-display-wrap {
  position: relative;
  width: 260px;
  height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0.25rem 0;
}

.progress-ring-svg {
  position: absolute;
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.progress-ring-bg {
  stroke: var(--bg-elevated);
}

.progress-ring-fg {
  transition: stroke-dashoffset 0.5s ease;
}

.progress-ring-fg.focus {
  stroke: var(--primary-orange);
}

.progress-ring-fg.short_break {
  stroke: var(--secondary-cyan);
}

.progress-ring-fg.long_break {
  stroke: var(--amber-glass);
}

.clock-inner-content {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  max-width: 190px;
}

.clock-mode-label {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  font-weight: 600;
}

.clock-digits {
  font-family: var(--font-serif, Georgia, serif);
  font-size: 3.75rem;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  color: var(--text-dark);
  line-height: 0.98;
  margin: 0.2rem 0 0.25rem;
}

.clock-target-project {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-body);
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.clock-intention-italic {
  font-family: var(--font-serif, Georgia, serif);
  font-style: italic;
  font-size: 0.92rem;
  color: var(--primary-orange);
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 2px;
}

.clock-cycle-label {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}

/* Controls */
.clock-controls {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  width: 100%;
}

.btn-clock-toggle {
  flex: 2;
  padding: 0.72rem 1rem;
  border: 1px solid var(--ink-surface);
  border-radius: 3px;
  background: var(--ink-surface);
  color: var(--on-ink);
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 0.88rem;
  cursor: pointer;
  transition: background 0.15s ease;
}

.btn-clock-toggle:hover {
  background: var(--ink-surface-hover);
}

.btn-clock-toggle.running {
  background: var(--primary-orange);
  border-color: var(--primary-orange-bright);
}

.btn-clock-secondary {
  flex: 1;
  padding: 0.72rem 0.5rem;
  border: 1px solid var(--border-subtle);
  border-radius: 3px;
  background: var(--bg-page);
  font-family: var(--font-sans);
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--text-dark);
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.btn-clock-secondary:hover {
  background: var(--bg-elevated);
  border-color: var(--border-strong);
}

/* Checkboxes */
.study-options-strip {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  width: 100%;
  border-top: 1px solid var(--border-subtle);
  padding-top: 0.85rem;
}

.study-checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.78rem;
  color: var(--text-muted);
  cursor: pointer;
}

.study-checkbox-label input {
  accent-color: var(--primary-orange);
}

/* Flush Hairline KPI Ledger Strip */
.study-kpis {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0;
  width: 100%;
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-page);
}

.kpi-mini-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.75rem 0.4rem;
  border-radius: 0;
  background: transparent;
  border: none;
  border-right: 1px solid var(--border-subtle);
}

.kpi-mini-card:last-child {
  border-right: none;
}

.kpi-mini-val {
  font-family: var(--font-serif, Georgia, serif);
  font-size: 1.55rem;
  font-weight: 500;
  line-height: 1;
  color: var(--text-dark);
}

.kpi-mini-lbl {
  font-family: var(--font-mono);
  font-size: 0.62rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 0.25rem;
}

/* Recent list */
.recent-sessions-box {
  width: 100%;
  padding-top: 0.25rem;
}

.recent-title {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin: 0 0 0.55rem;
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
  gap: 0.55rem;
  font-size: 0.78rem;
  padding: 0.35rem 0;
  border-bottom: 1px solid var(--border-faint);
}

.recent-item:last-child {
  border-bottom: none;
}

.recent-dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
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
  color: var(--text-dark);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recent-intent {
  font-size: 0.72rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recent-time {
  font-family: var(--font-mono, monospace);
  font-weight: 600;
  color: var(--text-muted);
}

@media (max-width: 1024px) {
  .study-mode-view {
    padding: 1.5rem 1.25rem 2.5rem;
  }
  .study-main-split {
    grid-template-columns: 1fr;
  }
  .study-note-pane {
    border-right: none;
    border-bottom: 1px solid var(--border-subtle);
    height: 440px;
  }
  .setup-grid {
    grid-template-columns: 1fr;
  }
}
</style>
