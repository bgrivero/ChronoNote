<template>
  <div class="habit-heatmap-view" aria-label="Habit Heatmap & Analytics">
    <!-- Header with Stats & Filter -->
    <div class="heatmap-header">
      <div class="header-left">
        <div class="heatmap-kicker">HABIT CONSISTENCY &amp; ACTIVITY</div>
        <h2 class="heatmap-title">Habit Consistency &amp; Activity</h2>
        <p class="heatmap-subtitle">
          Rolling 52-week activity matrix synchronized with your daily journal logs.
        </p>
      </div>

      <div class="header-actions">
        <select
          v-model="selectedHabitFilter"
          class="select-habit-filter"
          aria-label="Filter heatmap by habit"
        >
          <option value="all">All Tracked Habits</option>
          <option v-for="h in activeHabits" :key="h.id" :value="h.slug">
            {{ h.name }}
          </option>
        </select>

        <button
          type="button"
          class="btn-editorial-primary"
          @click="showCreateHabitModal = true"
        >
          + New Habit
        </button>
      </div>
    </div>

    <!-- Top Architectural Ledger Strip (Continuous Hairline-Divided Numerals) -->
    <div class="habits-body-content">
    <div class="kpi-ledger-strip">
      <div class="kpi-ledger-cell">
        <span class="kpi-label">CURRENT STREAK</span>
        <div class="kpi-value-row">
          <span class="kpi-number">{{ overallStats.best_current_streak || 0 }}</span>
          <span class="kpi-unit">days</span>
        </div>
        <span class="kpi-subtext">Consecutive active journal days</span>
      </div>

      <div class="kpi-ledger-cell">
        <span class="kpi-label">BEST STREAK</span>
        <div class="kpi-value-row">
          <span class="kpi-number">{{ overallStats.best_longest_streak || 0 }}</span>
          <span class="kpi-unit">days</span>
        </div>
        <span class="kpi-subtext">All-time uninterrupted run</span>
      </div>

      <div class="kpi-ledger-cell">
        <span class="kpi-label">30-DAY RATE</span>
        <div class="kpi-value-row">
          <span class="kpi-number">{{ overallStats.average_completion_rate || 0 }}%</span>
        </div>
        <span class="kpi-subtext">Rolling daily adherence</span>
      </div>

      <div class="kpi-ledger-cell">
        <span class="kpi-label">LOGGED TODAY</span>
        <div class="kpi-value-row">
          <span class="kpi-number">{{ overallStats.today_completed || 0 }}</span>
          <span class="kpi-unit">/ {{ activeHabits.length }}</span>
        </div>
        <span class="kpi-subtext">{{ activeHabits.length }} active habits tracked</span>
      </div>
    </div>

    <!-- 52-Week Editorial Heatmap Matrix -->
    <div class="heatmap-card">
      <div class="heatmap-card-header">
        <div class="hm-header-left">
          <span class="hm-card-title">ANNUAL ACTIVITY MATRIX (52 WEEKS)</span>
          <span class="hm-card-hint">Click any day square to open that day's journal</span>
        </div>
        <div class="heatmap-legend">
          <span class="legend-text">Less</span>
          <span class="legend-swatch level-0" title="0%"></span>
          <span class="legend-swatch level-1" title="1-25%"></span>
          <span class="legend-swatch level-2" title="26-50%"></span>
          <span class="legend-swatch level-3" title="51-75%"></span>
          <span class="legend-swatch level-4" title="76-100%"></span>
          <span class="legend-text">More</span>
        </div>
      </div>

      <div class="heatmap-scroll-wrapper">
        <div class="heatmap-matrix-layout">
          <!-- Weekday Labels -->
          <div class="weekday-labels-col">
            <span class="weekday-label">Mon</span>
            <span class="weekday-label">Tue</span>
            <span class="weekday-label">Wed</span>
            <span class="weekday-label">Thu</span>
            <span class="weekday-label">Fri</span>
            <span class="weekday-label">Sat</span>
            <span class="weekday-label">Sun</span>
          </div>

          <!-- Heatmap SVG Grid -->
          <div class="svg-matrix-container">
            <svg
              :width="svgWidth"
              :height="svgHeight"
              class="heatmap-svg"
              role="img"
              aria-label="Habit Heatmap Grid"
            >
              <!-- Month Labels -->
              <g class="month-labels-group">
                <text
                  v-for="(m, idx) in monthLabels"
                  :key="idx"
                  :x="m.x"
                  y="12"
                  class="month-svg-text"
                >
                  {{ m.text }}
                </text>
              </g>

              <!-- Weeks & Day Squares -->
              <g transform="translate(0, 22)">
                <g
                  v-for="(week, wIdx) in heatmapWeeks"
                  :key="wIdx"
                  :transform="`translate(${wIdx * (cellSize + cellGap)}, 0)`"
                >
                  <rect
                    v-for="day in week.days"
                    :key="day.date"
                    :y="day.dayRow * (cellSize + cellGap)"
                    :width="cellSize"
                    :height="cellSize"
                    rx="1"
                    ry="1"
                    class="heatmap-cell"
                    :class="[
                      `level-${getCellLevel(day)}`,
                      { 'is-future': day.isFuture, 'is-selected': day.date === activeDate },
                    ]"
                    @click="onSelectDay(day)"
                    @mouseenter="onHoverDay($event, day)"
                    @mouseleave="hoveredDay = null"
                  />
                </g>
              </g>
            </svg>
          </div>
        </div>
      </div>

      <!-- Hover Tooltip -->
      <div
        v-if="hoveredDay"
        class="heatmap-tooltip"
        :style="{ left: `${tooltipPos.x}px`, top: `${tooltipPos.y}px` }"
      >
        <div class="tt-date">{{ hoveredDay.formattedDate }}</div>
        <div class="tt-stats">
          <span v-if="selectedHabitFilter === 'all'">
            {{ hoveredDay.completed_count }} of {{ hoveredDay.total_habits }} habits ({{ Math.round(hoveredDay.rate * 100) }}%)
          </span>
          <span v-else>
            {{ hoveredDay.habits[selectedHabitFilter] ? "Completed" : "Not logged" }}
          </span>
        </div>
        <div class="tt-action">Click to jump to journal</div>
      </div>
    </div>

    <!-- Habit Cards & Streak Details -->
    <div class="habits-section">
      <div class="section-top">
        <h3 class="section-title">Tracked Habits</h3>
        <span class="section-count">{{ activeHabits.length }} active habits</span>
      </div>

      <div class="habit-cards-grid">
        <div
          v-for="habit in activeHabits"
          :key="habit.id"
          class="habit-card"
          :style="{ borderLeftColor: habit.color || '#2c666e' }"
        >
          <div class="habit-card-top">
            <div class="habit-title-box">
              <span class="habit-name">{{ habit.name }}</span>
              <span class="habit-slug">@habit({{ habit.slug }})</span>
            </div>
            <div class="habit-card-actions">
              <button
                type="button"
                class="habit-edit-action-btn"
                title="Edit habit"
                @click="openEditHabitModal(habit)"
              >
                Edit
              </button>
              <button
                type="button"
                class="habit-quick-toggle"
                :class="{ completed: isHabitCompletedToday(habit.slug) }"
                :title="isHabitCompletedToday(habit.slug) ? 'Completed today! Click to uncheck' : 'Click to complete for today'"
                @click="$emit('toggle-habit', habit.id, todayIso)"
              >
                <span class="toggle-indicator">{{ isHabitCompletedToday(habit.slug) ? "✓" : "○" }}</span>
                <span>{{ isHabitCompletedToday(habit.slug) ? "Done Today" : "Log Today" }}</span>
              </button>
            </div>
          </div>

          <div class="habit-meta-row">
            <div class="meta-stat">
              <span class="meta-val">{{ habit.current_streak || 0 }}d</span>
              <span class="meta-lbl">Current Streak</span>
            </div>
            <div class="meta-stat">
              <span class="meta-val">{{ habit.longest_streak || 0 }}d</span>
              <span class="meta-lbl">Best Streak</span>
            </div>
            <div class="meta-stat">
              <span class="meta-val">{{ habit.completion_rate_30d || 0 }}%</span>
              <span class="meta-lbl">30-Day Rate</span>
            </div>
            <div class="meta-stat">
              <span class="meta-val">{{ habit.total_completions || 0 }}</span>
              <span class="meta-lbl">Total Logs</span>
            </div>
          </div>

          <div class="progress-bar-bg">
            <div
              class="progress-bar-fill"
              :style="{
                width: `${Math.min(100, Math.max(0, habit.completion_rate_30d || 0))}%`,
                backgroundColor: habit.color || '#2c666e',
              }"
            ></div>
          </div>
        </div>
      </div>
    </div>
    </div>

    <!-- Create Habit Modal Dialog -->
    <div
      v-if="showCreateHabitModal"
      class="modal-backdrop"
      role="dialog"
      aria-modal="true"
      @click.self="showCreateHabitModal = false"
    >
      <div class="modal-card">
        <div class="modal-header">
          <h3 class="modal-title">Create New Habit</h3>
          <button
            type="button"
            class="modal-close-btn"
            @click="showCreateHabitModal = false"
          >
            ×
          </button>
        </div>

        <form class="modal-form" @submit.prevent="submitCreateHabit">
          <div class="form-group">
            <label class="form-label" for="habit-name">Habit Name *</label>
            <input
              id="habit-name"
              v-model="newHabitForm.name"
              type="text"
              class="input-minimal"
              placeholder="e.g. Morning Walk, Read 20 Pages"
              required
            />
          </div>

          <div class="form-group">
            <label class="form-label" for="habit-slug">Identifier Slug</label>
            <input
              id="habit-slug"
              v-model="newHabitForm.slug"
              type="text"
              class="input-minimal"
              placeholder="e.g. walk, reading (optional, auto-generated)"
            />
            <span class="form-hint">Used in markdown journal entries: @habit(slug)</span>
          </div>

          <div class="form-row">
            <div class="form-group half">
              <label class="form-label" for="habit-color">Color Accent</label>
              <input
                id="habit-color"
                v-model="newHabitForm.color"
                type="color"
                class="input-color"
              />
            </div>
            <div class="form-group half">
              <label class="form-label" for="habit-target">Weekly Target</label>
              <select
                id="habit-target"
                v-model.number="newHabitForm.target_days_per_week"
                class="input-minimal"
              >
                <option :value="7">Every day (7d/wk)</option>
                <option :value="5">Weekdays (5d/wk)</option>
                <option :value="4">4 days a week</option>
                <option :value="3">3 days a week</option>
              </select>
            </div>
          </div>

          <div class="modal-actions">
            <button
              type="button"
              class="btn-editorial-ghost"
              @click="showCreateHabitModal = false"
            >
              Cancel
            </button>
            <button
              type="submit"
              class="btn-editorial-primary"
              :disabled="!newHabitForm.name.trim()"
            >
              Create Habit
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Edit Habit Modal Dialog -->
    <div
      v-if="showEditHabitModal"
      class="modal-backdrop"
      role="dialog"
      aria-modal="true"
      @click.self="showEditHabitModal = false"
    >
      <div class="modal-card">
        <div class="modal-header">
          <h3 class="modal-title">Edit Habit</h3>
          <button
            type="button"
            class="modal-close-btn"
            @click="showEditHabitModal = false"
          >
            ×
          </button>
        </div>

        <form class="modal-form" @submit.prevent="submitEditHabit">
          <div class="form-group">
            <label class="form-label" for="edit-habit-name">Habit Name *</label>
            <input
              id="edit-habit-name"
              v-model="editHabitForm.name"
              type="text"
              class="input-minimal"
              placeholder="e.g. Morning Walk, Read 20 Pages"
              required
            />
          </div>

          <div class="form-group">
            <label class="form-label" for="edit-habit-slug">Identifier Slug</label>
            <input
              id="edit-habit-slug"
              v-model="editHabitForm.slug"
              type="text"
              class="input-minimal"
              placeholder="e.g. walk, reading"
            />
            <span class="form-hint">Used in markdown journal entries: @habit(slug)</span>
          </div>

          <div class="form-row">
            <div class="form-group half">
              <label class="form-label" for="edit-habit-color">Color Accent</label>
              <input
                id="edit-habit-color"
                v-model="editHabitForm.color"
                type="color"
                class="input-color"
              />
            </div>
            <div class="form-group half">
              <label class="form-label" for="edit-habit-target">Weekly Target</label>
              <select
                id="edit-habit-target"
                v-model.number="editHabitForm.target_days_per_week"
                class="input-minimal"
              >
                <option :value="7">Every day (7d/wk)</option>
                <option :value="5">Weekdays (5d/wk)</option>
                <option :value="4">4 days a week</option>
                <option :value="3">3 days a week</option>
              </select>
            </div>
          </div>

          <div class="modal-actions-between">
            <button
              type="button"
              class="btn-editorial-danger"
              @click="submitDeleteHabit"
            >
              Delete Habit
            </button>
            <div class="modal-actions-right">
              <button
                type="button"
                class="btn-editorial-ghost"
                @click="showEditHabitModal = false"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="btn-editorial-primary"
                :disabled="!editHabitForm.name.trim()"
              >
                Save Changes
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { buildHabitHeatmapGrid, getHeatmapLevel } from "../composables/useHabitsAndHeatmap.js";

const props = defineProps({
  analyticsData: {
    type: Object,
    default: () => ({ days: [], overall_stats: {}, habit_streaks: [] }),
  },
  habitsList: {
    type: Array,
    default: () => [],
  },
  activeDate: {
    type: String,
    default: () => new Date().toISOString().slice(0, 10),
  },
});

const emit = defineEmits(["select-date", "create-habit", "update-habit", "delete-habit", "toggle-habit"]);

const todayIso = new Date().toISOString().slice(0, 10);
const selectedHabitFilter = ref("all");
const hoveredDay = ref(null);
const tooltipPos = ref({ x: 0, y: 0 });
const showCreateHabitModal = ref(false);
const showEditHabitModal = ref(false);
const editingHabitId = ref(null);

const newHabitForm = ref({
  name: "",
  slug: "",
  color: "#2c666e",
  target_days_per_week: 7,
});

const editHabitForm = ref({
  name: "",
  slug: "",
  color: "#2c666e",
  target_days_per_week: 7,
});

function openEditHabitModal(habit) {
  editingHabitId.value = habit.id;
  editHabitForm.value = {
    name: habit.name || "",
    slug: habit.slug || "",
    color: habit.color || "#2c666e",
    target_days_per_week: habit.target_days_per_week || 7,
  };
  showEditHabitModal.value = true;
}

function submitEditHabit() {
  if (!editingHabitId.value || !editHabitForm.value.name.trim()) return;
  emit("update-habit", editingHabitId.value, {
    name: editHabitForm.value.name.trim(),
    slug: editHabitForm.value.slug?.trim() || undefined,
    color: editHabitForm.value.color,
    target_days_per_week: editHabitForm.value.target_days_per_week,
  });
  showEditHabitModal.value = false;
}

function submitDeleteHabit() {
  if (!editingHabitId.value) return;
  const name = editHabitForm.value.name || "this habit";
  if (!window.confirm(`Are you sure you want to delete habit "${name}" and all of its recorded history?`)) {
    return;
  }
  emit("delete-habit", editingHabitId.value);
  showEditHabitModal.value = false;
}

const cellSize = 13;
const cellGap = 3.5;

const activeHabits = computed(() => {
  return (props.habitsList || []).filter((h) => !h.archived);
});

const overallStats = computed(() => {
  return props.analyticsData?.overall_stats || {};
});

const heatmapWeeks = computed(() => {
  const days = props.analyticsData?.days || [];
  return buildHabitHeatmapGrid(days, new Date());
});

const svgWidth = computed(() => {
  return 52 * (cellSize + cellGap) + 10;
});

const svgHeight = computed(() => {
  return 7 * (cellSize + cellGap) + 30;
});

const monthLabels = computed(() => {
  const labels = [];
  heatmapWeeks.value.forEach((w, wIdx) => {
    if (w.monthLabel) {
      labels.push({
        text: w.monthLabel,
        x: wIdx * (cellSize + cellGap),
      });
    }
  });
  return labels;
});

function getCellLevel(day) {
  if (selectedHabitFilter.value === "all") {
    return day.level;
  }
  const isDone = Boolean(day.habits && day.habits[selectedHabitFilter.value]);
  return isDone ? 4 : 0;
}

function isHabitCompletedToday(slug) {
  const todayEntry = (props.analyticsData?.days || []).find((d) => d.date === todayIso);
  return Boolean(todayEntry?.habits && todayEntry.habits[slug]);
}

function onHoverDay(evt, day) {
  hoveredDay.value = day;
  const rect = evt.target.getBoundingClientRect();
  tooltipPos.value = {
    x: rect.left + rect.width / 2,
    y: rect.top - 8,
  };
}

function onSelectDay(day) {
  if (day && day.date) {
    emit("select-date", day.date);
  }
}

function submitCreateHabit() {
  if (!newHabitForm.value.name.trim()) return;
  emit("create-habit", {
    name: newHabitForm.value.name.trim(),
    slug: newHabitForm.value.slug.trim() || undefined,
    color: newHabitForm.value.color,
    target_days_per_week: newHabitForm.value.target_days_per_week,
  });
  showCreateHabitModal.value = false;
  newHabitForm.value = {
    name: "",
    slug: "",
    color: "#2c666e",
    target_days_per_week: 7,
  };
}
</script>

<style scoped>
.habit-heatmap-view {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 0;
  color: var(--text-dark);
}

.heatmap-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  background: var(--bg-spine);
  color: var(--on-spine);
  min-height: 54px;
  padding: 12px 28px 14px calc(var(--rail-w) + 16px);
  position: relative;
  border-bottom: 1px solid var(--spine-line);
  transition: padding-left 0.22s cubic-bezier(0.22, 1, 0.36, 1);
}

.heatmap-header::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 2px;
  background: var(--stripe-gradient);
  pointer-events: none;
}

:global(.editorial-app.is-nav-open) .heatmap-header {
  padding-left: 28px;
}

.habits-body-content {
  padding: 24px 32px 56px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1420px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}

.heatmap-kicker {
  font-family: var(--font-mono);
  font-size: 0.66rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: var(--accent-amber);
  text-transform: uppercase;
}

.heatmap-title {
  font-family: var(--font-serif);
  font-size: 2rem;
  font-weight: 500;
  letter-spacing: -0.02em;
  line-height: 1.04;
  color: var(--on-spine);
  margin: 2px 0 2px;
}

.heatmap-subtitle {
  font-size: 0.84rem;
  color: var(--on-spine-muted);
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.select-habit-filter {
  padding: 7px 12px;
  border-radius: 3px;
  border: 1px solid var(--spine-line-strong);
  background: var(--bg-spine-elevated);
  font-family: var(--font-sans);
  font-size: 0.82rem;
  color: var(--on-spine);
  cursor: pointer;
  outline: none;
  transition: border-color 0.15s ease;
}

.select-habit-filter:focus {
  border-color: var(--accent-amber);
}

.btn-editorial-primary {
  background: var(--primary-orange);
  color: var(--paper);
  border: 1px solid var(--primary-orange-bright);
  padding: 8px 16px;
  border-radius: 3px;
  font-family: var(--font-sans);
  font-size: 0.83rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease;
}

.btn-editorial-primary:hover {
  background: var(--primary-orange-bright);
}

/* Continuous Architectural Ledger Strip */
.kpi-ledger-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0;
  border-top: 1px solid var(--border-strong);
  border-bottom: 1px solid var(--border-strong);
  border-left: 1px solid var(--border-subtle);
  border-right: 1px solid var(--border-subtle);
  background: var(--bg-card);
}

.kpi-ledger-cell {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-subtle);
}

.kpi-ledger-cell:last-child {
  border-right: none;
}

.kpi-label {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  text-transform: uppercase;
}

.kpi-value-row {
  display: flex;
  align-items: baseline;
  gap: 7px;
  margin: 8px 0 4px;
}

.kpi-number {
  font-family: var(--font-serif);
  font-size: 3.1rem;
  font-weight: 500;
  color: var(--text-dark);
  line-height: 0.9;
  letter-spacing: -0.02em;
}

.kpi-unit {
  font-family: var(--font-serif);
  font-style: italic;
  font-size: 1.05rem;
  color: var(--text-muted);
}

.kpi-subtext {
  font-size: 0.74rem;
  color: var(--text-muted);
}

/* Heatmap Card (Flush Leaded-Glass Pane) */
.heatmap-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  padding: 20px 22px;
  box-shadow: none;
}

.heatmap-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}

.hm-card-title {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--text-dark);
  text-transform: uppercase;
}

.hm-card-hint {
  font-size: 0.76rem;
  color: var(--text-muted);
  margin-left: 12px;
}

.heatmap-legend {
  display: flex;
  align-items: center;
  gap: 5px;
}

.legend-text {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--text-muted);
}

.legend-swatch {
  width: 12px;
  height: 12px;
  border-radius: 1px;
  display: inline-block;
}

/* Warm Stained-Glass Amber -> Terracotta -> Garnet Ramp */
.level-0 {
  fill: #e6ddd0;
  background-color: #e6ddd0;
}

.level-1 {
  fill: #ebd2a0;
  background-color: #ebd2a0;
}

.level-2 {
  fill: #dc973c;
  background-color: #dc973c;
}

.level-3 {
  fill: #c25122;
  background-color: #c25122;
}

.level-4 {
  fill: #722618;
  background-color: #722618;
}

.heatmap-scroll-wrapper {
  overflow-x: auto;
  padding-bottom: 6px;
}

.heatmap-matrix-layout {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  min-width: 860px;
}

.weekday-labels-col {
  display: flex;
  flex-direction: column;
  padding-top: 22px;
  gap: 3.5px;
}

.weekday-label {
  font-family: var(--font-mono);
  font-size: 0.62rem;
  color: var(--text-muted);
  height: 13px;
  line-height: 13px;
  text-align: right;
  width: 24px;
}

.svg-matrix-container {
  flex: 1;
}

.month-svg-text {
  font-size: 10px;
  fill: var(--text-muted);
  font-family: var(--font-mono);
}

.heatmap-cell {
  cursor: pointer;
  transition: opacity 0.1s ease, stroke 0.1s ease;
}

.heatmap-cell:hover {
  stroke: var(--text-dark);
  stroke-width: 1.5;
}

.heatmap-cell.is-selected {
  stroke: var(--primary-orange);
  stroke-width: 2;
}

.heatmap-cell.is-future {
  cursor: default;
  opacity: 0.35;
}

/* Tooltip */
.heatmap-tooltip {
  position: fixed;
  transform: translate(-50%, -100%);
  background: var(--ink-surface);
  color: var(--on-ink);
  border: 1px solid var(--border-strong);
  padding: 8px 12px;
  border-radius: 3px;
  font-size: 0.78rem;
  pointer-events: none;
  z-index: 1000;
  box-shadow: var(--shadow-sm);
  white-space: nowrap;
}

.tt-date {
  font-family: var(--font-serif);
  font-size: 0.96rem;
  font-weight: 500;
  color: var(--bg-card);
  margin-bottom: 2px;
}

.tt-stats {
  color: var(--accent-amber);
  font-weight: 500;
}

.tt-action {
  font-size: 0.68rem;
  color: var(--on-spine-muted);
  margin-top: 3px;
}

/* Habits list section */
.habits-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 8px;
}

.section-title {
  font-family: var(--font-serif);
  font-size: 1.65rem;
  font-weight: 500;
  color: var(--text-dark);
  margin: 0;
}

.section-count {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
}

.habit-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}

.habit-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-left-width: 3px;
  border-radius: 2px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: none;
}

.habit-card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.habit-card-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.habit-edit-action-btn {
  font-size: 0.74rem;
  font-weight: 500;
  padding: 5px 9px;
  border-radius: 3px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-page);
  color: var(--text-muted);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.15s ease;
}

.habit-edit-action-btn:hover {
  border-color: var(--secondary-cyan);
  color: var(--secondary-cyan);
  background: var(--secondary-cyan-soft);
}

.habit-name {
  font-weight: 600;
  font-size: 0.96rem;
  color: var(--text-dark);
  display: block;
}

.habit-slug {
  font-size: 0.72rem;
  font-family: var(--font-mono);
  color: var(--secondary-cyan);
}

.habit-quick-toggle {
  font-size: 0.78rem;
  font-weight: 500;
  padding: 5px 11px;
  border-radius: 3px;
  border: 1px solid var(--border-strong);
  background: var(--bg-page);
  color: var(--text-body);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
}

.habit-quick-toggle:hover {
  background: var(--bg-elevated);
  color: var(--text-dark);
}

.habit-quick-toggle.completed {
  background: var(--secondary-cyan-soft);
  border-color: var(--secondary-cyan-border);
  color: var(--secondary-cyan);
  font-weight: 600;
}

.toggle-indicator {
  font-weight: 700;
}

.habit-meta-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.meta-stat {
  display: flex;
  flex-direction: column;
}

.meta-val {
  font-family: var(--font-serif);
  font-weight: 600;
  font-size: 1.15rem;
  line-height: 1.05;
  color: var(--text-dark);
}

.meta-lbl {
  font-family: var(--font-mono);
  font-size: 0.64rem;
  color: var(--text-muted);
}

.progress-bar-bg {
  height: 2px;
  background: var(--bg-elevated);
  border-radius: 0;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 0;
  transition: width 0.3s ease;
}

/* Modal styles */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(28, 21, 17, 0.45);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 16px;
}

.modal-card {
  background: var(--bg-card);
  border: 1px solid var(--border-strong);
  border-radius: 4px;
  width: 100%;
  max-width: 440px;
  padding: 24px;
  box-shadow: var(--shadow-lg);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-title {
  font-family: var(--font-serif);
  font-size: 1.55rem;
  font-weight: 500;
  color: var(--text-dark);
  margin: 0;
}

.modal-close-btn {
  background: none;
  border: none;
  font-size: 1.4rem;
  color: var(--text-muted);
  cursor: pointer;
  line-height: 1;
}

.modal-close-btn:hover {
  color: var(--text-dark);
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-group.half {
  flex: 1;
}

.form-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-body);
}

.form-hint {
  font-size: 0.72rem;
  color: var(--text-muted);
}

.input-minimal {
  padding: 8px 12px;
  border-radius: 3px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-page);
  font-family: var(--font-sans);
  font-size: 0.85rem;
  color: var(--text-dark);
  outline: none;
  transition: border-color 0.15s ease;
}

.input-minimal:focus {
  border-color: var(--primary-orange);
  background: var(--paper);
}

.input-color {
  height: 38px;
  width: 100%;
  padding: 2px;
  border-radius: 3px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  cursor: pointer;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
}

.modal-actions-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  width: 100%;
}

.modal-actions-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-editorial-danger {
  background: var(--danger-tint);
  border: 1px solid var(--danger-ring);
  color: var(--garnet-overdue);
  padding: 8px 14px;
  border-radius: 3px;
  font-family: var(--font-sans);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-editorial-danger:hover {
  background: var(--garnet-overdue);
  color: var(--white);
  border-color: var(--garnet-overdue);
}

.btn-editorial-ghost {
  background: transparent;
  border: 1px solid var(--border-strong);
  color: var(--text-body);
  padding: 8px 16px;
  border-radius: 3px;
  font-family: var(--font-sans);
  font-size: 0.84rem;
  cursor: pointer;
  transition: background 0.15s ease;
}

.btn-editorial-ghost:hover {
  background: var(--bg-subtle-hover);
  color: var(--text-dark);
}

@media (max-width: 900px) {
  .kpi-ledger-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .kpi-ledger-cell:nth-child(2) {
    border-right: none;
  }
  .kpi-ledger-cell:nth-child(1),
  .kpi-ledger-cell:nth-child(2) {
    border-bottom: 1px solid var(--border-subtle);
  }
}
</style>
