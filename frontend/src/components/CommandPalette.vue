<script setup>
import { computed, nextTick, ref, watch } from "vue";

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  projects: {
    type: Array,
    default: () => [],
  },
  overdueCount: {
    type: Number,
    default: 0,
  },
  apiBase: {
    type: String,
    default: "/api",
  },
  authHeaders: {
    type: Object,
    default: () => ({}),
  },
});

const emit = defineEmits(["close", "select-action"]);

const inputRef = ref(null);
const query = ref("");
const activeIdx = ref(0);
const remoteResults = ref([]);
const isSearching = ref(false);
let debounceTimer = null;

const quickActions = computed(() => {
  const list = [
    { id: "act-new-task", kind: "action", title: "New Task", subtitle: "Quick add to calendar or Inbox", shortcut: "N", action: "new-task" },
    { id: "act-today", kind: "action", title: "Jump to Today", subtitle: "Center calendar on today", shortcut: "T", action: "jump-today" },
    { id: "act-day", kind: "action", title: "Day View", subtitle: "Switch to hourly Day view", shortcut: "D", action: "scale-day" },
    { id: "act-week", kind: "action", title: "Week View", subtitle: "Switch to timed 7-day grid", shortcut: "W", action: "scale-week" },
    { id: "act-month", kind: "action", title: "Month View", subtitle: "Switch to monthly grid", shortcut: "M", action: "scale-month" },
    { id: "act-year", kind: "action", title: "Year View", subtitle: "Switch to 12-month overview", shortcut: "Y", action: "scale-year" },
    { id: "act-overdue", kind: "action", title: `Review Overdue Tasks (${props.overdueCount})`, subtitle: "Open overdue navigator", shortcut: "O", action: "overdue" },
    { id: "act-journal", kind: "action", title: "Open Today's Journal", subtitle: "Switch to Daily Journal", action: "journal-today" },
    { id: "act-projects", kind: "action", title: "Projects Board", subtitle: "Manage planned, active & completed projects", action: "go-projects" },
    { id: "act-archive", kind: "action", title: "Open Archive Vault", subtitle: "View or restore archived projects", action: "open-archive" },
  ];
  const q = query.value.trim().toLowerCase();
  if (!q) return list;
  return list.filter(
    (item) =>
      item.title.toLowerCase().includes(q) ||
      item.subtitle.toLowerCase().includes(q)
  );
});

const matchingProjects = computed(() => {
  const q = query.value.trim().toLowerCase();
  const base = props.projects || [];
  const filtered = q
    ? base.filter(
        (p) =>
          (p.name || "").toLowerCase().includes(q) ||
          (p.area || "").toLowerCase().includes(q)
      )
    : base.slice(0, 5);
  return filtered.map((p) => ({
    id: `proj-${p.id}`,
    kind: "project",
    title: p.name,
    subtitle: p.area ? `${p.area} · ${p.status}` : `Project (${p.status})`,
    projectId: p.id,
    color: p.color,
  }));
});

const combinedItems = computed(() => {
  const items = [];
  const seenProjectIds = new Set();

  for (const act of quickActions.value) {
    items.push(act);
  }
  for (const proj of matchingProjects.value) {
    seenProjectIds.add(proj.projectId);
    items.push(proj);
  }
  for (const res of remoteResults.value) {
    if (res.kind === "project" && seenProjectIds.has(res.id)) continue;
    items.push({
      id: `remote-${res.kind}-${res.id}`,
      kind: res.kind,
      title: res.title,
      subtitle: res.subtitle,
      projectId: res.project_id,
      raw: res,
    });
  }
  return items;
});

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      query.value = "";
      remoteResults.value = [];
      activeIdx.value = 0;
      await nextTick();
      inputRef.value?.focus();
    } else if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
  }
);

watch(query, (val) => {
  activeIdx.value = 0;
  if (debounceTimer) clearTimeout(debounceTimer);
  const trimmed = val.trim();
  if (!trimmed) {
    remoteResults.value = [];
    isSearching.value = false;
    return;
  }
  isSearching.value = true;
  debounceTimer = setTimeout(async () => {
    try {
      const res = await fetch(
        `${props.apiBase}/search?q=${encodeURIComponent(trimmed)}`,
        { headers: props.authHeaders }
      );
      if (res.ok) {
        remoteResults.value = await res.json();
      }
    } catch {
      remoteResults.value = [];
    } finally {
      isSearching.value = false;
    }
  }, 180);
});

function selectItem(item) {
  if (!item) return;
  emit("select-action", item);
  emit("close");
}

function handleKeydown(event) {
  const total = combinedItems.value.length;
  if (event.key === "Escape") {
    event.preventDefault();
    emit("close");
  } else if (event.key === "ArrowDown" && total > 0) {
    event.preventDefault();
    activeIdx.value = (activeIdx.value + 1) % total;
  } else if (event.key === "ArrowUp" && total > 0) {
    event.preventDefault();
    activeIdx.value = (activeIdx.value - 1 + total) % total;
  } else if (event.key === "Enter" && total > 0) {
    event.preventDefault();
    selectItem(combinedItems.value[activeIdx.value]);
  }
}
</script>

<template>
  <div
    v-if="open"
    class="cmd-palette-backdrop"
    role="dialog"
    aria-modal="true"
    aria-label="Command palette"
    @click.self="emit('close')"
  >
    <div class="cmd-palette-panel" @keydown="handleKeydown">
      <div class="cmd-palette-input-row">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          ref="inputRef"
          v-model="query"
          type="text"
          class="cmd-palette-input"
          placeholder="Search tasks, projects, notes, or type a command…"
        />
        <span v-if="isSearching" class="cmd-searching-hint">Searching…</span>
        <kbd class="cmd-kbd">Esc</kbd>
      </div>

      <div class="cmd-palette-results">
        <button
          v-for="(item, idx) in combinedItems"
          :key="item.id"
          type="button"
          class="cmd-result-row"
          :class="{ active: idx === activeIdx }"
          @mouseenter="activeIdx = idx"
          @click="selectItem(item)"
        >
          <span class="cmd-result-left">
            <span
              v-if="item.color"
              class="cmd-proj-dot"
              :style="{ backgroundColor: item.color }"
            />
            <span v-else class="cmd-kind-badge">{{ item.kind }}</span>
            <span class="cmd-result-title">{{ item.title }}</span>
            <span class="cmd-result-sub">{{ item.subtitle }}</span>
          </span>
          <kbd v-if="item.shortcut" class="cmd-kbd">{{ item.shortcut }}</kbd>
        </button>

        <div v-if="combinedItems.length === 0" class="cmd-empty-state">
          No matching commands, projects, tasks, or notes.
        </div>
      </div>
    </div>
  </div>
</template>
