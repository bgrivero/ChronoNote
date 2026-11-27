<script setup>
import { nextTick, ref, watch } from "vue";

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  initialDraft: {
    type: Object,
    default: () => ({}),
  },
  projects: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["close", "submit"]);

const titleInputRef = ref(null);
const hasTime = ref(false);
const form = ref({
  title: "",
  projectId: 0,
  start_date: "",
  due_date: "",
  start_time: "09:00",
  end_time: "10:00",
  priority: "medium",
  deadline_only: false,
  is_milestone: false,
});

watch(
  () => [props.open, props.initialDraft],
  async ([isOpen]) => {
    if (!isOpen) return;
    const d = props.initialDraft || {};
    const explicitStartTime = d.start_time || "";
    hasTime.value = Boolean(explicitStartTime);
    form.value = {
      title: d.title || "",
      projectId: d.project_id ?? 0,
      start_date: d.start_date || d.due_date || "",
      due_date: d.due_date || d.start_date || "",
      start_time: explicitStartTime || "09:00",
      end_time: d.end_time || "10:00",
      priority: d.priority || "medium",
      deadline_only: Boolean(d.deadline_only),
      is_milestone: Boolean(d.is_milestone),
    };
    await nextTick();
    titleInputRef.value?.focus();
  },
  { immediate: true }
);

function toggleTimed() {
  hasTime.value = !hasTime.value;
  if (hasTime.value && !form.value.start_time) {
    form.value.start_time = "09:00";
    form.value.end_time = "10:00";
  }
}

function submitTask() {
  const title = (form.value.title || "").trim();
  if (!title) return;

  let startDate = form.value.start_date || form.value.due_date;
  let dueDate = form.value.due_date || form.value.start_date;
  if (startDate && dueDate && startDate > dueDate) {
    const tmp = startDate;
    startDate = dueDate;
    dueDate = tmp;
  }

  emit("submit", {
    project_id: form.value.projectId === 0 ? null : form.value.projectId,
    title,
    start_date: startDate || null,
    due_date: dueDate || null,
    start_time: hasTime.value ? form.value.start_time || null : null,
    end_time: hasTime.value ? form.value.end_time || null : null,
    priority: form.value.priority || "medium",
    deadline_only: Boolean(form.value.deadline_only),
    is_milestone: Boolean(form.value.is_milestone),
  });
}
</script>

<template>
  <div
    v-if="open"
    class="quick-popover-backdrop"
    role="dialog"
    aria-modal="true"
    aria-label="Create task"
    @click.self="emit('close')"
    @keydown.esc.stop="emit('close')"
  >
    <form class="quick-task-popover" @submit.prevent="submitTask">
      <div class="quick-popover-top">
        <span class="quick-popover-kicker">New Task</span>
        <button
          type="button"
          class="close-drawer-btn"
          aria-label="Close"
          @click="emit('close')"
        >
          ✕
        </button>
      </div>

      <input
        ref="titleInputRef"
        v-model="form.title"
        type="text"
        class="quick-popover-title-input"
        placeholder="What needs to be done?"
        required
      />

      <div class="quick-popover-row">
        <label class="quick-field">
          <span>Project</span>
          <select v-model="form.projectId" class="input-minimal">
            <option :value="0">Inbox (One-Off)</option>
            <option v-for="proj in projects" :key="proj.id" :value="proj.id">
              {{ proj.name }}
            </option>
          </select>
        </label>
      </div>

      <div class="quick-popover-row quick-dates-row">
        <label class="quick-field">
          <span>Start date</span>
          <input v-model="form.start_date" type="date" class="input-minimal" />
        </label>
        <label class="quick-field">
          <span>Due date</span>
          <input v-model="form.due_date" type="date" class="input-minimal" />
        </label>
      </div>

      <div class="quick-popover-time-bar">
        <button
          type="button"
          class="quick-time-toggle-btn"
          :class="{ active: hasTime }"
          @click="toggleTimed"
        >
          {{ hasTime ? "Timed block" : "+ Add time" }}
        </button>
        <template v-if="hasTime">
          <input v-model="form.start_time" type="time" class="input-minimal quick-time-input" />
          <span class="date-arrow">–</span>
          <input v-model="form.end_time" type="time" class="input-minimal quick-time-input" />
        </template>
      </div>

      <div class="quick-popover-options">
        <div class="quick-priority-pills" role="group" aria-label="Priority">
          <button
            v-for="p in ['low', 'medium', 'high', 'urgent']"
            :key="p"
            type="button"
            class="quick-prio-chip"
            :class="{ active: form.priority === p, [`prio-${p}`]: true }"
            @click="form.priority = p"
          >
            {{ p.charAt(0).toUpperCase() + p.slice(1) }}
          </button>
        </div>

        <div class="quick-flags-row">
          <label class="deadline-only-toggle">
            <input v-model="form.deadline_only" type="checkbox" />
            <span>Deadline only</span>
          </label>
          <label class="deadline-only-toggle">
            <input v-model="form.is_milestone" type="checkbox" />
            <span>Milestone</span>
          </label>
        </div>
      </div>

      <div class="quick-popover-footer">
        <button type="button" class="btn-editorial-ghost" @click="emit('close')">
          Cancel
        </button>
        <button type="submit" class="btn-ink-primary">
          Create Task
        </button>
      </div>
    </form>
  </div>
</template>
