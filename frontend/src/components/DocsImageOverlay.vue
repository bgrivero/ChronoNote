<template>
  <div class="docs-image-overlay-layer" aria-label="Draggable Image Layer">
    <div
      v-for="img in images"
      :key="img.id"
      class="draggable-image-card"
      :class="{ 'is-selected': selectedImageId === img.id }"
      :style="getImageStyle(img)"
      @mousedown="startDrag($event, img)"
      @touchstart="startDrag($event, img)"
      @click.stop="selectedImageId = img.id"
    >
      <!-- Action Controls Bar (Appears on Hover/Select) -->
      <div class="image-actions-bar" @mousedown.stop @touchstart.stop>
        <span class="mode-badge" :title="`Layout: ${img.mode}`">
          {{ img.mode === 'draggable' ? '📌 Draggable' : img.mode }}
        </span>
        <button
          type="button"
          class="img-btn-action"
          title="Switch to Inline text"
          @click="$emit('change-mode', { id: img.id, mode: 'inline' })"
        >
          📄 Inline
        </button>
        <button
          type="button"
          class="img-btn-action"
          title="Wrap text left"
          @click="$emit('change-mode', { id: img.id, mode: 'wrap_left' })"
        >
          ◀ Wrap
        </button>
        <button
          type="button"
          class="img-btn-action"
          title="View in Lightbox"
          @click="$emit('view-lightbox', img.url)"
        >
          🔍
        </button>
        <button
          type="button"
          class="img-btn-action delete-btn"
          title="Delete image"
          @click="$emit('delete-image', img)"
        >
          ✕
        </button>
      </div>

      <!-- Main Image Display (Polaroid / Aesthetic Frame) -->
      <div class="image-inner-frame">
        <img
          :src="img.url"
          :alt="img.caption || 'Journal Image'"
          class="docs-draggable-img"
          draggable="false"
        />
        <span v-if="img.caption" class="image-caption">{{ img.caption }}</span>
      </div>

      <!-- Bottom-Right Resize Grab Handle -->
      <div
        class="resize-handle se-handle"
        title="Drag to resize width"
        @mousedown.stop="startResize($event, img)"
        @touchstart.stop="startResize($event, img)"
      ></div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { computeDraggableImageStyle } from "../composables/useDocsImages.js";

const props = defineProps({
  images: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits([
  "update-image",
  "change-mode",
  "delete-image",
  "view-lightbox",
]);

const selectedImageId = ref(null);

function getImageStyle(img) {
  return computeDraggableImageStyle(img);
}

// Drag & Drop
let activeDrag = null;

function startDrag(e, img) {
  selectedImageId.value = img.id;
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const clientY = e.touches ? e.touches[0].clientY : e.clientY;

  activeDrag = {
    imgId: img.id,
    startX: clientX,
    startY: clientY,
    origX: img.x || 50,
    origY: img.y || 20,
  };

  window.addEventListener("mousemove", onDragging);
  window.addEventListener("mouseup", stopDrag);
  window.addEventListener("touchmove", onDragging, { passive: false });
  window.addEventListener("touchend", stopDrag);
}

function onDragging(e) {
  if (!activeDrag) return;
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const clientY = e.touches ? e.touches[0].clientY : e.clientY;

  const dx = clientX - activeDrag.startX;
  const dy = clientY - activeDrag.startY;

  // Approximate percentage conversion for x based on viewport width
  const percentDeltaX = (dx / (window.innerWidth || 1000)) * 100;
  const newX = Math.max(5, Math.min(95, Math.round(activeDrag.origX + percentDeltaX)));
  const newY = Math.max(0, Math.round(activeDrag.origY + dy));

  const target = props.images.find((i) => i.id === activeDrag.imgId);
  if (target) {
    target.x = newX;
    target.y = newY;
  }
}

function stopDrag() {
  if (activeDrag) {
    const target = props.images.find((i) => i.id === activeDrag.imgId);
    if (target) {
      emit("update-image", { id: target.id, x: target.x, y: target.y, width: target.width });
    }
  }
  activeDrag = null;
  window.removeEventListener("mousemove", onDragging);
  window.removeEventListener("mouseup", stopDrag);
  window.removeEventListener("touchmove", onDragging);
  window.removeEventListener("touchend", stopDrag);
}

// Resize Handling
let activeResize = null;

function startResize(e, img) {
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  activeResize = {
    imgId: img.id,
    startX: clientX,
    origWidth: img.width || 300,
  };

  window.addEventListener("mousemove", onResizing);
  window.addEventListener("mouseup", stopResize);
  window.addEventListener("touchmove", onResizing, { passive: false });
  window.addEventListener("touchend", stopResize);
}

function onResizing(e) {
  if (!activeResize) return;
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const dx = clientX - activeResize.startX;
  const newWidth = Math.max(120, Math.min(800, Math.round(activeResize.origWidth + dx)));

  const target = props.images.find((i) => i.id === activeResize.imgId);
  if (target) {
    target.width = newWidth;
  }
}

function stopResize() {
  if (activeResize) {
    const target = props.images.find((i) => i.id === activeResize.imgId);
    if (target) {
      emit("update-image", { id: target.id, x: target.x, y: target.y, width: target.width });
    }
  }
  activeResize = null;
  window.removeEventListener("mousemove", onResizing);
  window.removeEventListener("mouseup", stopResize);
  window.removeEventListener("touchmove", onResizing);
  window.removeEventListener("touchend", stopResize);
}
</script>

<style scoped>
.docs-image-overlay-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: visible;
}

.draggable-image-card {
  pointer-events: auto;
  user-select: none;
  background: #fff;
  padding: 8px 8px 12px;
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.15s ease;
}

.draggable-image-card:hover,
.draggable-image-card.is-selected {
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15), 0 0 0 2px #6366f1;
}

.image-actions-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 6px;
  padding: 2px 4px;
  background: #f8fafc;
  border-radius: 6px;
  font-size: 0.72rem;
}

.mode-badge {
  font-size: 0.68rem;
  font-weight: 600;
  color: #4b5563;
  margin-right: auto;
}

.img-btn-action {
  padding: 2px 6px;
  font-size: 0.68rem;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.1s ease;
}

.img-btn-action:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.img-btn-action.delete-btn:hover {
  background: #fee2e2;
  color: #dc2626;
  border-color: #fca5a5;
}

.image-inner-frame {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.docs-draggable-img {
  width: 100%;
  height: auto;
  border-radius: 4px;
  display: block;
}

.image-caption {
  font-size: 0.74rem;
  font-family: var(--font-serif, Georgia, serif);
  font-style: italic;
  color: #64748b;
  margin-top: 6px;
  text-align: center;
}

.resize-handle {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 14px;
  height: 14px;
  cursor: se-resize;
  background: #6366f1;
  border-radius: 3px 0 7px 0;
}
</style>
