<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import {
  computeTimedBlockLayout,
  formatMinutesToTime,
  formatTimeDisplay,
  snapMinutes,
} from "../composables/useTimelineGeometry.js";

const HOUR_HEIGHT = 56;
const TOTAL_GRID_HEIGHT = HOUR_HEIGHT * 24;

const props = defineProps({
  days: {
    type: Array,
    default: () => [],
  },
  allDayItems: {
    type: Array,
    default: () => [],
  },
  timedTasksByDate: {
    type: Object,
    default: () => ({}),
  },
  todayIso: {
    type: String,
    default: "",
  },
  taskFilterMode: {
    type: String,
    default: "all",
  },
  focusedOverdueTaskId: {
    type: [Number, String],
    default: null,
  },
  focusedOverdueDateIso: {
    type: String,
    default: null,
  },
  projectTasksMap: {
    type: Object,
    default: () => ({}),
  },
  visibleSubtaskProjectIds: {
    type: Object,
    default: () => new Set(),
  },
  activeTimelineDrag: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits([
  "quick-create",
  "open-journal",
  "card-click",
  "toggle-task",
  "toggle-project-done",
  "toggle-project-subtasks",
  "open-project-drawer",
  "update-timed-task",
  "start-allday-drag",
]);

const scrollAreaRef = ref(null);
const gridColumnsRef = ref(null);
const nowMinutes = ref(getCurrentLocalMinutes());
let nowTimer = null;

function getCurrentLocalMinutes() {
  const d = new Date();
  return d.getHours() * 60 + d.getMinutes();
}

const hoursList = Array.from({ length: 24 }, (_, h) => {
  const period = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return {
    hour: h,
    label: h === 0 ? "" : `${h12} ${period}`,
  };
});

const localTzLabel = computed(() => {
  const offsetMin = -new Date().getTimezoneOffset();
  if (offsetMin === 0) return "UTC";
  const sign = offsetMin >= 0 ? "+" : "-";
  const absHours = Math.floor(Math.abs(offsetMin) / 60);
  const remMins = Math.abs(offsetMin) % 60;
  return remMins === 0
    ? `GMT${sign}${absHours}`
    : `GMT${sign}${absHours}:${String(remMins).padStart(2, "0")}`;
});

const currentTimeTopPx = computed(() => (nowMinutes.value / 60) * HOUR_HEIGHT);

const gridStyleVars = computed(() => ({
  "--grid-days": Math.max(props.days.length, 1),
}));

// Active vertical drag-to-create state on empty hourly slot
const slotCreateDrag = ref(null);

// Active drag-move or bottom-edge resize on an existing timed task block
const blockDrag = ref(null);
const justDraggedBlock = ref(false);

const layoutByDate = computed(() => {
  const out = {};
  for (const day of props.days) {
    const rawList = props.timedTasksByDate[day.iso] || [];
    out[day.iso] = computeTimedBlockLayout(rawList, HOUR_HEIGHT);
  }
  return out;
});

function isProjectSubtasksVisibleLocal(projectId) {
  if (!props.visibleSubtaskProjectIds) return false;
  if (props.visibleSubtaskProjectIds instanceof Set) {
    return props.visibleSubtaskProjectIds.has(projectId);
  }
  return Boolean(props.visibleSubtaskProjectIds[projectId]);
}

function getAllDayCardStyle(hexColor, item) {
  const c = hexColor || "#2a5f52";
  return {
    gridColumn: `${item.startCol} / span ${item.spanCols}`,
    gridRow: item.trackRow,
    borderColor: `${c}42`,
    borderLeft: `3px solid ${c}`,
    backgroundColor: `${c}14`,
    boxShadow: "inset 0 1px 0 rgba(255, 250, 240, 0.65)",
  };
}

function isBlockActivelyDragged(taskId) {
  return blockDrag.value && blockDrag.value.taskId === taskId;
}

function getTimedBlocksForColumn(dayIso, dayIdx) {
  const baseBlocks = layoutByDate.value[dayIso] || [];
  const drag = blockDrag.value;
  if (!drag) return baseBlocks;

  // Hide original block when dragged across to another day column
  const filtered = baseBlocks.filter(
    (b) => !(b.task.id === drag.taskId && drag.targetDayIdx !== dayIdx)
  );

  // If dragged onto this column from another column, inject a live preview block
  if (drag.targetDayIdx === dayIdx && drag.origDayIdx !== dayIdx) {
    filtered.push({
      task: drag.task,
      startMin: drag.currentStartMin,
      endMin: drag.currentEndMin,
      topPx: (drag.currentStartMin / 60) * HOUR_HEIGHT,
      heightPx: Math.max(((drag.currentEndMin - drag.currentStartMin) / 60) * HOUR_HEIGHT, 20),
      colIndex: 0,
      colCount: 1,
      leftPct: 0,
      widthPct: 100,
      timeRangeLabel: formatMinutesRangeLabel(drag.currentStartMin, drag.currentEndMin),
    });
  }
  return filtered;
}

function formatMinutesRangeLabel(startMin, endMin) {
  const s = formatTimeDisplay(formatMinutesToTime(startMin));
  const e =
    endMin >= 1440 ? "12 AM" : formatTimeDisplay(formatMinutesToTime(endMin));
  return `${s} – ${e}`;
}

function getTimedBlockStyle(block) {
  const drag = blockDrag.value;
  const isDragged = drag && drag.taskId === block.task.id;
  const topPx = isDragged ? (drag.currentStartMin / 60) * HOUR_HEIGHT : block.topPx;
  const heightPx = isDragged
    ? Math.max(((drag.currentEndMin - drag.currentStartMin) / 60) * HOUR_HEIGHT, 20)
    : block.heightPx;

  const c = block.task.displayColor || block.task.color || "#2a5f52";
  const left = isDragged ? 2 : `calc(${block.leftPct}% + 2px)`;
  const width = isDragged ? "calc(100% - 4px)" : `calc(${block.widthPct}% - 4px)`;

  return {
    top: `${topPx}px`,
    height: `${heightPx}px`,
    left: typeof left === "number" ? `${left}px` : left,
    width,
    borderLeft: `3px solid ${c}`,
    backgroundColor: `${c}14`,
    borderColor: `${c}42`,
    boxShadow: "inset 0 1px 0 rgba(255, 250, 240, 0.65)",
  };
}

function getTimedBlockLabel(block) {
  if (blockDrag.value && blockDrag.value.taskId === block.task.id) {
    return formatMinutesRangeLabel(
      blockDrag.value.currentStartMin,
      blockDrag.value.currentEndMin
    );
  }
  return block.timeRangeLabel;
}

// ---------------------------------------------------------------------------
// Empty Slot Click / Vertical Drag-to-Create
// ---------------------------------------------------------------------------

function yToMinutes(clientY, colEl) {
  const rect = colEl.getBoundingClientRect();
  const relY = Math.min(Math.max(clientY - rect.top, 0), TOTAL_GRID_HEIGHT);
  const rawMinutes = (relY / HOUR_HEIGHT) * 60;
  return snapMinutes(rawMinutes, 15);
}

function startSlotDragCreate(event, dayIso) {
  if (event.button !== 0 || blockDrag.value) return;
  const colEl = event.currentTarget;
  const anchorMin = yToMinutes(event.clientY, colEl);

  slotCreateDrag.value = {
    dayIso,
    colEl,
    startX: event.clientX,
    startY: event.clientY,
    anchorMin,
    currentMin: Math.min(anchorMin + 60, 1440),
    hasMoved: false,
  };

  window.addEventListener("pointermove", handleSlotDragMove);
  window.addEventListener("pointerup", handleSlotDragEnd);
  window.addEventListener("pointercancel", handleSlotDragEnd);
}

function handleSlotDragMove(event) {
  const drag = slotCreateDrag.value;
  if (!drag) return;
  if (Math.abs(event.clientY - drag.startY) > 5) {
    drag.hasMoved = true;
  }
  if (drag.hasMoved) {
    drag.currentMin = yToMinutes(event.clientY, drag.colEl);
  }
}

function handleSlotDragEnd() {
  window.removeEventListener("pointermove", handleSlotDragMove);
  window.removeEventListener("pointerup", handleSlotDragEnd);
  window.removeEventListener("pointercancel", handleSlotDragEnd);

  const drag = slotCreateDrag.value;
  slotCreateDrag.value = null;
  if (!drag) return;

  let startMin;
  let endMin;
  if (drag.hasMoved) {
    startMin = Math.min(drag.anchorMin, drag.currentMin);
    endMin = Math.max(drag.anchorMin, drag.currentMin);
    if (endMin - startMin < 15) {
      endMin = Math.min(startMin + 30, 1439);
    }
  } else {
    // Simple click: round down to clean 30-min mark with 60-min default duration
    startMin = Math.min(Math.floor(drag.anchorMin / 30) * 30, 23 * 60);
    endMin = Math.min(startMin + 60, 1439);
  }

  startMin = Math.min(Math.max(startMin, 0), 1438);
  endMin = Math.min(Math.max(endMin, startMin + 15), 1439);

  emit("quick-create", {
    start_date: drag.dayIso,
    due_date: drag.dayIso,
    start_time: formatMinutesToTime(startMin),
    end_time: formatMinutesToTime(endMin),
  });
}

const slotPreviewRange = computed(() => {
  const drag = slotCreateDrag.value;
  if (!drag || !drag.hasMoved) return null;
  const startMin = Math.min(drag.anchorMin, drag.currentMin);
  const endMin = Math.max(Math.max(drag.anchorMin, drag.currentMin), startMin + 15);
  return {
    dayIso: drag.dayIso,
    topPx: (startMin / 60) * HOUR_HEIGHT,
    heightPx: Math.max(((endMin - startMin) / 60) * HOUR_HEIGHT, 18),
    label: formatMinutesRangeLabel(startMin, Math.min(endMin, 1439)),
  };
});

// ---------------------------------------------------------------------------
// Existing Timed Block Drag-to-Move & Bottom-Edge Resize
// ---------------------------------------------------------------------------

function startBlockDrag(event, block, type, dayIdx) {
  if (event.button !== 0) return;
  const colsRect = gridColumnsRef.value?.getBoundingClientRect();
  const colWidth =
    colsRect && props.days.length > 0 ? colsRect.width / props.days.length : 140;

  blockDrag.value = {
    taskId: block.task.id,
    projectId: block.task.project_id ?? 0,
    task: block.task,
    type, // 'move' | 'resize-end'
    origDayIdx: dayIdx,
    targetDayIdx: dayIdx,
    origStartMin: block.startMin,
    origEndMin: block.endMin,
    currentStartMin: block.startMin,
    currentEndMin: block.endMin,
    startX: event.clientX,
    startY: event.clientY,
    colWidth,
    hasMoved: false,
  };

  window.addEventListener("pointermove", handleBlockDragMove);
  window.addEventListener("pointerup", handleBlockDragEnd);
  window.addEventListener("pointercancel", handleBlockDragEnd);
}

function handleBlockDragMove(event) {
  const drag = blockDrag.value;
  if (!drag) return;

  const dx = event.clientX - drag.startX;
  const dy = event.clientY - drag.startY;
  if (Math.abs(dx) > 4 || Math.abs(dy) > 4) {
    drag.hasMoved = true;
  }
  if (!drag.hasMoved) return;

  const signedDeltaMin = Math.round(((dy / HOUR_HEIGHT) * 60) / 15) * 15;

  if (drag.type === "resize-end") {
    const nextEnd = Math.min(
      Math.max(drag.origEndMin + signedDeltaMin, drag.origStartMin + 15),
      1439
    );
    drag.currentEndMin = nextEnd;
  } else {
    const duration = drag.origEndMin - drag.origStartMin;
    const nextStart = Math.min(
      Math.max(drag.origStartMin + signedDeltaMin, 0),
      1439 - duration
    );
    drag.currentStartMin = nextStart;
    drag.currentEndMin = Math.min(nextStart + duration, 1439);

    if (props.days.length > 1 && drag.colWidth > 0) {
      const colShift = Math.round(dx / drag.colWidth);
      drag.targetDayIdx = Math.min(
        Math.max(drag.origDayIdx + colShift, 0),
        props.days.length - 1
      );
    }
  }
}

function handleBlockDragEnd() {
  window.removeEventListener("pointermove", handleBlockDragMove);
  window.removeEventListener("pointerup", handleBlockDragEnd);
  window.removeEventListener("pointercancel", handleBlockDragEnd);

  const drag = blockDrag.value;
  blockDrag.value = null;
  if (!drag || !drag.hasMoved) return;

  justDraggedBlock.value = true;
  setTimeout(() => {
    justDraggedBlock.value = false;
  }, 120);

  const targetDay = props.days[drag.targetDayIdx] || props.days[drag.origDayIdx];
  const patch = {
    start_time: formatMinutesToTime(drag.currentStartMin),
    end_time: formatMinutesToTime(drag.currentEndMin),
  };
  if (targetDay && drag.targetDayIdx !== drag.origDayIdx) {
    patch.start_date = targetDay.iso;
    patch.due_date = targetDay.iso;
  }

  emit("update-timed-task", {
    projectId: drag.projectId,
    taskId: drag.taskId,
    patch,
  });
}

function handleBlockClick(block) {
  if (justDraggedBlock.value) return;
  emit("card-click", {
    kind: "task",
    projectId: block.task.project_id ?? 0,
    taskId: block.task.id,
  });
}

function scrollToWorkingHours() {
  if (scrollAreaRef.value) {
    scrollAreaRef.value.scrollTop = Math.max(0, 7 * HOUR_HEIGHT - 24);
  }
}

onMounted(() => {
  nowTimer = setInterval(() => {
    nowMinutes.value = getCurrentLocalMinutes();
  }, 60_000);
  nextTick(scrollToWorkingHours);
});

watch(
  () => props.days.length,
  () => {
    nextTick(scrollToWorkingHours);
  }
);

onUnmounted(() => {
  if (nowTimer) clearInterval(nowTimer);
  window.removeEventListener("pointermove", handleSlotDragMove);
  window.removeEventListener("pointerup", handleSlotDragEnd);
  window.removeEventListener("pointercancel", handleSlotDragEnd);
  window.removeEventListener("pointermove", handleBlockDragMove);
  window.removeEventListener("pointerup", handleBlockDragEnd);
  window.removeEventListener("pointercancel", handleBlockDragEnd);
});
</script>

<template>
  <div class="timegrid-shell" :style="gridStyleVars">
    <!-- Sticky Day Header Strip -->
    <div class="timegrid-header-row">
      <div class="timegrid-gutter-head">{{ localTzLabel }}</div>
      <div class="timegrid-days-header">
        <div
          v-for="day in days"
          :key="day.iso"
          class="timegrid-day-head"
          :data-calendar-day-iso="day.iso"
          :class="{
            'is-today-col': day.isToday,
            'is-focused-overdue-day':
              taskFilterMode === 'overdue' && focusedOverdueDateIso === day.iso,
          }"
        >
          <div class="timegrid-day-head-main">
            <span class="timegrid-dow">{{ day.dowShort }}</span>
            <span
              class="day-number-pill"
              :class="{ 'is-today-pill': day.isToday }"
            >
              {{ day.dayNum }}
            </span>
            <small v-if="day.dayNum === 1 || days.length === 1" class="day-month-hint">
              {{ day.monthShort }}
            </small>
          </div>
          <div class="timegrid-day-head-actions">
            <button
              type="button"
              class="timegrid-journal-chip"
              :class="{ 'has-entry': day.hasJournal }"
              :title="`Open journal for ${day.iso}`"
              @click.stop="emit('open-journal', day.iso)"
            >
              {{ day.hasJournal ? (day.journalTitle || "Journal") : "+ Note" }}
            </button>
            <button
              type="button"
              class="day-quick-add-btn"
              title="Add task on this date"
              @click.stop="
                emit('quick-create', {
                  start_date: day.iso,
                  due_date: day.iso,
                  start_time: null,
                  end_time: null,
                })
              "
            >
              +
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Compact All-Day & Project Spans Strip -->
    <div class="timegrid-allday-row">
      <div class="timegrid-gutter-allday">All-day</div>
      <div class="timegrid-allday-grid">
        <div class="timegrid-allday-bg">
          <div
            v-for="day in days"
            :key="day.iso"
            class="timegrid-allday-col"
            title="Click to add an all-day task"
            @click="
              emit('quick-create', {
                start_date: day.iso,
                due_date: day.iso,
                start_time: null,
                end_time: null,
              })
            "
          />
        </div>

        <div
          v-for="item in allDayItems"
          :key="item.uid"
          class="week-item-card clickable-card timegrid-allday-card"
          :data-overdue-task-id="item.taskId || undefined"
          :class="{
            'is-done-card': item.status === 'done',
            'is-project-bar': item.kind === 'project',
            'is-draggable-project': item.kind === 'project',
            'is-subtask-bar': item.kind === 'task',
            'is-draggable-task': item.kind === 'task',
            'is-overdue-card': item.isOverdue,
            'is-focused-overdue-card':
              taskFilterMode === 'overdue' &&
              item.taskId &&
              focusedOverdueTaskId === item.taskId,
            'is-milestone-card': item.isMilestone,
            'is-currently-dragged':
              activeTimelineDrag &&
              ((activeTimelineDrag.isTask && activeTimelineDrag.taskId === item.taskId) ||
                (!activeTimelineDrag.isTask && activeTimelineDrag.projectId === item.projectId)),
          }"
          :style="getAllDayCardStyle(item.color, item)"
          @pointerdown="
            item.kind === 'project'
              ? emit('start-allday-drag', { event: $event, projectId: item.projectId, type: 'move' })
              : emit('start-allday-drag', {
                  event: $event,
                  projectId: item.projectId,
                  type: 'move',
                  taskId: item.taskId,
                })
          "
          @click="emit('card-click', item)"
        >
          <div
            class="timeline-resize-handle handle-left"
            @pointerdown.stop.prevent="
              item.kind === 'project'
                ? emit('start-allday-drag', {
                    event: $event,
                    projectId: item.projectId,
                    type: 'resize-start',
                  })
                : emit('start-allday-drag', {
                    event: $event,
                    projectId: item.projectId,
                    type: 'resize-start',
                    taskId: item.taskId,
                  })
            "
          />
          <div class="week-item-main">
            <template v-if="item.kind === 'project'">
              <button
                type="button"
                class="subtask-check-btn"
                :class="{ checked: item.status === 'done' }"
                :style="
                  item.status === 'done'
                    ? { backgroundColor: item.color, borderColor: item.color }
                    : { borderColor: item.color }
                "
                @click.stop="emit('toggle-project-done', item.projectId)"
              >
                <svg
                  v-if="item.status === 'done'"
                  width="10"
                  height="10"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="3"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </button>
              <span class="color-badge-mono" :style="{ color: item.color }">
                {{ item.code }}
              </span>
            </template>
            <template v-else-if="item.kind === 'milestone'">
              <span class="milestone-diamond-badge" :style="{ backgroundColor: item.color }">◆</span>
            </template>
            <template v-else>
              <button
                type="button"
                class="subtask-check-btn"
                :class="{ checked: item.status === 'done' }"
                :style="
                  item.status === 'done'
                    ? { backgroundColor: item.color, borderColor: item.color }
                    : { borderColor: item.color }
                "
                @click.stop="
                  emit('toggle-task', { projectId: item.projectId, taskId: item.taskId })
                "
              >
                <svg
                  v-if="item.status === 'done'"
                  width="10"
                  height="10"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="3"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </button>
            </template>
            <strong
              class="week-item-title"
              :class="{ 'strikethrough-done': item.status === 'done' }"
            >
              {{ item.title }}
            </strong>
            <span v-if="item.isOverdue" class="overdue-tag-pill">Overdue</span>
            <button
              v-if="item.kind === 'project' && (projectTasksMap[item.projectId] || []).length > 0"
              type="button"
              class="subtasks-toggle-badge"
              :class="{ 'is-expanded': isProjectSubtasksVisibleLocal(item.projectId) }"
              @click.stop="emit('toggle-project-subtasks', item.projectId)"
            >
              {{ isProjectSubtasksVisibleLocal(item.projectId) ? "▼" : "▶" }}
              {{ (projectTasksMap[item.projectId] || []).length }}
            </button>
          </div>
          <div
            class="timeline-resize-handle handle-right"
            @pointerdown.stop.prevent="
              item.kind === 'project'
                ? emit('start-allday-drag', {
                    event: $event,
                    projectId: item.projectId,
                    type: 'resize-end',
                  })
                : emit('start-allday-drag', {
                    event: $event,
                    projectId: item.projectId,
                    type: 'resize-end',
                    taskId: item.taskId,
                  })
            "
          />
        </div>
      </div>
    </div>

    <!-- Scrollable 24-Hour Time-Blocking Grid -->
    <div ref="scrollAreaRef" class="timegrid-scroll-body">
      <div class="timegrid-canvas" :style="{ height: `${TOTAL_GRID_HEIGHT}px` }">
        <!-- Left Time Labels Gutter -->
        <div class="timegrid-hour-gutter">
          <div
            v-for="h in hoursList"
            :key="h.hour"
            class="timegrid-hour-label"
            :style="{ height: `${HOUR_HEIGHT}px` }"
          >
            <span v-if="h.label">{{ h.label }}</span>
          </div>
        </div>

        <!-- Day Columns Area -->
        <div ref="gridColumnsRef" class="timegrid-columns-wrap">
          <!-- Horizontal Hour & Half-Hour Hairlines -->
          <div class="timegrid-hour-lines" aria-hidden="true">
            <div
              v-for="h in hoursList"
              :key="h.hour"
              class="timegrid-hour-row"
              :style="{ height: `${HOUR_HEIGHT}px` }"
            >
              <div class="timegrid-halfhour-line" />
            </div>
          </div>

          <!-- Per-Day Interactive Columns -->
          <div
            v-for="(day, dayIdx) in days"
            :key="day.iso"
            class="timegrid-day-col"
            :class="{ 'is-today-col': day.isToday }"
            @pointerdown="startSlotDragCreate($event, day.iso)"
          >
            <!-- Current Time Indicator Line -->
            <div
              v-if="day.iso === todayIso"
              class="timegrid-now-line"
              :style="{ top: `${currentTimeTopPx}px` }"
            >
              <span class="timegrid-now-dot" />
            </div>

            <!-- Drag-to-Create Preview Ghost -->
            <div
              v-if="slotPreviewRange && slotPreviewRange.dayIso === day.iso"
              class="timegrid-create-ghost"
              :style="{
                top: `${slotPreviewRange.topPx}px`,
                height: `${slotPreviewRange.heightPx}px`,
              }"
            >
              <span class="timegrid-ghost-label">New task · {{ slotPreviewRange.label }}</span>
            </div>

            <!-- Scheduled Timed Task Blocks -->
            <div
              v-for="block in getTimedBlocksForColumn(day.iso, dayIdx)"
              :key="block.task.id"
              class="timegrid-task-block"
              :data-overdue-task-id="block.task.id"
              :class="{
                'is-done-card': block.task.status === 'done',
                'is-overdue-card': block.task.isOverdue,
                'is-focused-overdue-card':
                  taskFilterMode === 'overdue' &&
                  focusedOverdueTaskId === block.task.id,
                'is-dragging-block': isBlockActivelyDragged(block.task.id),
              }"
              :style="getTimedBlockStyle(block)"
              @pointerdown.stop="startBlockDrag($event, block, 'move', dayIdx)"
              @click.stop="handleBlockClick(block)"
            >
              <div class="timegrid-block-head">
                <button
                  type="button"
                  class="subtask-check-btn timegrid-block-check"
                  :class="{ checked: block.task.status === 'done' }"
                  :style="
                    block.task.status === 'done'
                      ? {
                          backgroundColor: block.task.displayColor || '#2c666e',
                          borderColor: block.task.displayColor || '#2c666e',
                        }
                      : { borderColor: block.task.displayColor || '#2c666e' }
                  "
                  title="Toggle task done"
                  @pointerdown.stop
                  @click.stop="
                    emit('toggle-task', {
                      projectId: block.task.project_id ?? 0,
                      taskId: block.task.id,
                    })
                  "
                >
                  <svg
                    v-if="block.task.status === 'done'"
                    width="10"
                    height="10"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="3"
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </button>
                <span
                  class="timegrid-block-title"
                  :class="{ 'strikethrough-done': block.task.status === 'done' }"
                >
                  {{ block.task.title }}
                </span>
                <span v-if="block.task.isOverdue" class="overdue-tag-pill">Overdue</span>
              </div>

              <div class="timegrid-block-meta">
                <span>{{ getTimedBlockLabel(block) }}</span>
                <span v-if="block.heightPx >= 42 && block.task.projectName">
                  · {{ block.task.projectName }}
                </span>
              </div>

              <div
                class="timegrid-block-resize-handle"
                title="Drag bottom edge to adjust duration"
                @pointerdown.stop.prevent="startBlockDrag($event, block, 'resize-end', dayIdx)"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
