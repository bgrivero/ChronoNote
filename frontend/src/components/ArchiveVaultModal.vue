<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  archivedProjects: {
    type: Array,
    default: () => [],
  },
  projectTasksMap: {
    type: Object,
    default: () => ({}),
  },
});

const emit = defineEmits(["close", "restore", "delete-permanent"]);

const searchQuery = ref("");

const filteredArchived = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  const list = props.archivedProjects || [];
  if (!q) return list;
  return list.filter(
    (p) =>
      (p.name || "").toLowerCase().includes(q) ||
      (p.area || "").toLowerCase().includes(q) ||
      (p.description || "").toLowerCase().includes(q)
  );
});
</script>

<template>
  <div
    v-if="open"
    class="archive-modal-backdrop"
    role="dialog"
    aria-modal="true"
    aria-label="Archive Vault"
    @click.self="emit('close')"
    @keydown.esc.stop="emit('close')"
  >
    <div class="archive-vault-panel">
      <header class="archive-vault-header">
        <div>
          <h3 class="archive-vault-title">Archive Vault</h3>
          <p class="archive-vault-sub">
            Stored projects stay out of your active calendar &amp; sidebar until restored.
          </p>
        </div>
        <button
          type="button"
          class="close-drawer-btn"
          aria-label="Close Archive Vault"
          @click="emit('close')"
        >
          ✕
        </button>
      </header>

      <div class="archive-vault-search-bar">
        <input
          v-model="searchQuery"
          type="text"
          class="input-minimal"
          placeholder="Filter archived projects by name or folder…"
        />
      </div>

      <div class="archive-vault-list">
        <div
          v-for="proj in filteredArchived"
          :key="proj.id"
          class="archive-vault-row"
        >
          <div class="archive-row-main">
            <span
              class="sidebar-dot"
              :style="{ backgroundColor: proj.color || '#71717a' }"
            />
            <div class="archive-row-info">
              <div class="archive-row-title-line">
                <strong class="archive-row-name">{{ proj.name }}</strong>
                <span v-if="proj.area" class="project-area-tag">{{ proj.area }}</span>
              </div>
              <span class="archive-row-meta">
                {{ proj.start_date || "—" }} → {{ proj.target_date || "—" }} ·
                {{ (projectTasksMap[proj.id] || []).length }} tasks
              </span>
            </div>
          </div>

          <div class="archive-row-actions">
            <button
              type="button"
              class="btn-editorial-ghost"
              @click="emit('restore', proj)"
            >
              Restore
            </button>
            <button
              type="button"
              class="delete-project-btn"
              @click="emit('delete-permanent', proj.id)"
            >
              Delete
            </button>
          </div>
        </div>

        <div v-if="filteredArchived.length === 0" class="archive-empty-state">
          {{
            archivedProjects.length === 0
              ? "No archived projects yet. Archive finished or paused projects to keep your workspace calm."
              : "No archived projects match that filter."
          }}
        </div>
      </div>
    </div>
  </div>
</template>
