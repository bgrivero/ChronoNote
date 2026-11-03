<template>
  <aside
    v-if="isOpen"
    class="sticker-tray-drawer"
    aria-label="Stickers & Stamps Palette"
  >
    <div class="tray-header">
      <div class="tray-title-group">
        <span class="tray-kicker">AESTHETIC STAMPS &amp; STICKERS</span>
        <h3 class="tray-title">Stickers &amp; Stamps</h3>
      </div>
      <button
        type="button"
        class="tray-close-btn"
        aria-label="Close stickers tray"
        @click="$emit('close')"
      >
        ✕
      </button>
    </div>

    <!-- Target Context Banner -->
    <div class="target-context-banner">
      <span class="context-pill">
        📍 Target: <strong>{{ targetLabel }}</strong>
      </span>
      <span class="context-hint">Click any sticker below to stamp it onto {{ targetHint }}</span>
    </div>

    <!-- Category Tabs & Upload Button -->
    <div class="tray-controls">
      <div class="category-tabs">
        <button
          v-for="cat in categories"
          :key="cat.value"
          type="button"
          class="cat-tab-btn"
          :class="{ active: selectedCategory === cat.value }"
          @click="selectedCategory = cat.value"
        >
          {{ cat.label }}
        </button>
      </div>

      <!-- Custom Upload Button -->
      <label class="btn-upload-sticker" title="Upload transparent PNG or SVG sticker">
        <input
          ref="fileInput"
          type="file"
          accept="image/png, image/svg+xml, image/webp, image/jpeg"
          style="display: none"
          @change="handleFileUpload"
        />
        <span>+ Upload Sticker</span>
      </label>
    </div>

    <!-- Sticker Grid -->
    <div class="stickers-grid">
      <div
        v-for="stk in filteredStickers"
        :key="stk.id"
        class="sticker-card"
        :title="`Click to stamp ${stk.name}`"
        @click="$emit('stamp-sticker', stk)"
      >
        <div class="sticker-img-wrap">
          <img :src="stk.image_url" :alt="stk.name" class="sticker-img" />
        </div>
        <span class="sticker-name">{{ stk.name }}</span>

        <!-- Delete button for custom stickers -->
        <button
          v-if="stk.category === 'custom'"
          type="button"
          class="btn-delete-custom"
          title="Delete custom sticker"
          @click.stop="$emit('delete-sticker', stk.id)"
        >
          ✕
        </button>
      </div>
    </div>

    <!-- Placed Stickers on this Target List -->
    <div v-if="placedOnTarget.length" class="placed-section">
      <h4 class="placed-title">Placed on {{ targetLabel }} ({{ placedOnTarget.length }})</h4>
      <div class="placed-chips">
        <div
          v-for="p in placedOnTarget"
          :key="p.id"
          class="placed-chip"
        >
          <img :src="p.image_url" :alt="p.sticker_name" class="placed-chip-img" />
          <span class="placed-chip-name">{{ p.sticker_name }}</span>
          <button
            type="button"
            class="placed-chip-remove"
            title="Remove sticker"
            @click="$emit('remove-placement', p.id)"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed, ref } from "vue";
import { readFileAsDataUrl } from "../composables/useStickers.js";

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
  stickers: {
    type: Array,
    default: () => [],
  },
  placements: {
    type: Array,
    default: () => [],
  },
  targetType: {
    type: String,
    default: "calendar_date", // 'calendar_date' | 'note'
  },
  targetKey: {
    type: String,
    default: "",
  },
  activeDateIso: {
    type: String,
    default: "",
  },
});

const emit = defineEmits([
  "close",
  "stamp-sticker",
  "upload-sticker",
  "delete-sticker",
  "remove-placement",
]);

const fileInput = ref(null);
const selectedCategory = ref("all");

const categories = [
  { value: "all", label: "All" },
  { value: "achievement", label: "Badges" },
  { value: "study", label: "Study" },
  { value: "lifestyle", label: "Daily" },
  { value: "custom", label: "My Uploads" },
];

const targetLabel = computed(() => {
  if (props.targetType === "calendar_date") {
    return `Date ${props.targetKey || props.activeDateIso}`;
  }
  return `Note: ${props.targetKey || "Current Note"}`;
});

const targetHint = computed(() => {
  if (props.targetType === "calendar_date") {
    return "the calendar day";
  }
  return "this note";
});

const filteredStickers = computed(() => {
  if (selectedCategory.value === "all") return props.stickers;
  return props.stickers.filter((s) => s.category === selectedCategory.value);
});

const placedOnTarget = computed(() => {
  const curKey = props.targetKey || props.activeDateIso;
  return props.placements.filter(
    (p) => p.target_type === props.targetType && String(p.target_key) === String(curKey)
  );
});

async function handleFileUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;

  try {
    const dataUrl = await readFileAsDataUrl(file);
    const cleanName = file.name.replace(/\.[^/.]+$/, "").slice(0, 40);
    emit("upload-sticker", {
      name: cleanName || "Custom Sticker",
      category: "custom",
      image_url: dataUrl,
    });
    selectedCategory.value = "custom";
    if (fileInput.value) fileInput.value.value = "";
  } catch (err) {
    console.error("Failed to read file:", err);
  }
}
</script>

<style scoped>
.sticker-tray-drawer {
  position: fixed;
  top: 56px;
  right: 0;
  bottom: 0;
  width: 340px;
  max-width: 90vw;
  background: var(--color-paper, #fdfbf7);
  border-left: 1px solid var(--color-border, #e5dfd5);
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.06);
  z-index: 1050;
  display: flex;
  flex-direction: column;
  padding: 1.25rem 1.25rem;
  box-sizing: border-box;
  animation: slideInRight 0.2s ease-out;
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

.tray-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.85rem;
}

.tray-kicker {
  font-family: var(--font-mono, monospace);
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-muted, #7c7467);
  font-weight: 600;
}

.tray-title {
  font-family: var(--font-serif, "Playfair Display", Georgia, serif);
  font-size: 1.25rem;
  margin: 0.15rem 0 0;
  color: var(--color-ink, #2d2a26);
}

.tray-close-btn {
  background: none;
  border: none;
  font-size: 1.1rem;
  color: var(--color-muted, #7c7467);
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
}

.tray-close-btn:hover {
  background: #f0ebe1;
  color: #111;
}

.target-context-banner {
  background: #f5efe6;
  border-radius: 6px;
  padding: 0.55rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  margin-bottom: 0.85rem;
}

.context-pill {
  font-size: 0.78rem;
  color: var(--color-ink, #2d2a26);
}

.context-hint {
  font-size: 0.7rem;
  color: var(--color-muted, #7c7467);
}

.tray-controls {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin-bottom: 1rem;
}

.category-tabs {
  display: flex;
  gap: 0.25rem;
  overflow-x: auto;
  padding-bottom: 0.2rem;
}

.cat-tab-btn {
  padding: 0.25rem 0.55rem;
  font-size: 0.74rem;
  border: 1px solid var(--color-border, #e5dfd5);
  border-radius: 12px;
  background: #fff;
  color: var(--color-muted, #7c7467);
  cursor: pointer;
  white-space: nowrap;
}

.cat-tab-btn.active {
  background: #2d2a26;
  color: #fff;
  border-color: #2d2a26;
}

.btn-upload-sticker {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.45rem 0.75rem;
  border: 1px dashed #cbbfb0;
  border-radius: 6px;
  background: #fff;
  font-size: 0.78rem;
  font-weight: 500;
  color: #4b5563;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-upload-sticker:hover {
  background: #fcfbf9;
  border-color: #6366f1;
  color: #6366f1;
}

/* Grid */
.stickers-grid {
  flex: 1;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.65rem;
  padding-right: 0.25rem;
}

.sticker-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #fff;
  border: 1px solid var(--color-border, #e5dfd5);
  border-radius: 8px;
  padding: 0.6rem 0.4rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.sticker-card:hover {
  transform: translateY(-2px);
  border-color: #93c5fd;
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.05);
}

.sticker-img-wrap {
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sticker-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.sticker-name {
  font-size: 0.68rem;
  color: var(--color-muted, #7c7467);
  text-align: center;
  margin-top: 0.35rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  width: 100%;
}

.btn-delete-custom {
  position: absolute;
  top: 2px;
  right: 2px;
  background: #fee2e2;
  border: none;
  border-radius: 50%;
  width: 16px;
  height: 16px;
  font-size: 0.6rem;
  color: #b91c1c;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

/* Placed section */
.placed-section {
  border-top: 1px solid var(--color-border, #e5dfd5);
  padding-top: 0.85rem;
  margin-top: 0.85rem;
}

.placed-title {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-muted, #7c7467);
  margin: 0 0 0.5rem;
}

.placed-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  max-height: 100px;
  overflow-y: auto;
}

.placed-chip {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  background: #fff;
  border: 1px solid var(--color-border, #e5dfd5);
  border-radius: 14px;
  padding: 0.2rem 0.45rem;
  font-size: 0.72rem;
}

.placed-chip-img {
  width: 16px;
  height: 16px;
  object-fit: contain;
}

.placed-chip-name {
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.placed-chip-remove {
  background: none;
  border: none;
  font-size: 0.68rem;
  color: #ef4444;
  cursor: pointer;
  padding: 0;
  margin-left: 2px;
}
</style>
