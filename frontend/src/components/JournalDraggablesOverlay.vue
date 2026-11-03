<template>
  <div ref="overlayRef" class="journal-draggables-layer" aria-label="Journal Draggable Elements Layer">
    <!-- 1. Floating Images -->
    <div
      v-for="img in images"
      :key="img.id"
      class="draggable-image-card"
      :class="{ 'is-selected': selectedElementId === img.id }"
      :style="getImageStyle(img)"
      @mousedown="startDragImage($event, img)"
      @touchstart="startDragImage($event, img)"
      @click.stop="selectedElementId = img.id"
    >
      <!-- Action Controls Bar -->
      <div class="image-actions-bar" @mousedown.stop @touchstart.stop>
        <span class="mode-badge">{{ img.mode === 'draggable' ? 'Draggable' : img.mode }}</span>
        <button
          type="button"
          class="img-btn-action"
          title="Switch to Inline text"
          @click="$emit('change-image-mode', { id: img.id, mode: 'inline' })"
        >
          Inline
        </button>
        <button
          type="button"
          class="img-btn-action"
          title="Wrap text left"
          @click="$emit('change-image-mode', { id: img.id, mode: 'wrap_left' })"
        >
          Wrap
        </button>
        <button
          type="button"
          class="img-btn-action"
          title="View in Lightbox"
          @click="$emit('view-lightbox', img.url)"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </button>
        <button
          type="button"
          class="img-btn-action delete-btn"
          title="Delete image"
          @click="$emit('delete-image', img)"
        >
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <!-- Main Image Display -->
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
        @mousedown.stop="startResizeImage($event, img)"
        @touchstart.stop="startResizeImage($event, img)"
      />
    </div>

    <!-- 2. Draggable & Resizable Stickers / Emotes -->
    <div
      v-for="stk in stickers"
      :key="stk.id"
      class="draggable-sticker-card"
      :class="{ 'is-selected': selectedElementId === `stk_${stk.id}` }"
      :style="getStickerStyle(stk)"
      @mousedown="startDragSticker($event, stk)"
      @touchstart="startDragSticker($event, stk)"
      @click.stop="selectedElementId = `stk_${stk.id}`"
    >
      <!-- Sticker Controls (Visible on hover or select) -->
      <div class="sticker-actions-pill" @mousedown.stop @touchstart.stop>
        <button
          type="button"
          class="stk-action-btn"
          title="Rotate sticker +15°"
          @click="rotateSticker(stk)"
        >
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
        </button>
        <button
          type="button"
          class="stk-action-btn stk-delete-btn"
          title="Remove sticker"
          @click="$emit('delete-sticker', stk.id)"
        >
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <!-- Sticker Graphic -->
      <div class="sticker-art-wrap">
        <img
          :src="stk.image_url"
          :alt="stk.sticker_name"
          class="journal-sticker-img"
          draggable="false"
        />
      </div>

      <!-- Bottom-Right Resize Handle for Sticker -->
      <div
        class="sticker-resize-handle"
        title="Drag to resize sticker"
        @mousedown.stop="startResizeSticker($event, stk)"
        @touchstart.stop="startResizeSticker($event, stk)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { computeDraggableImageStyle } from "../composables/useDocsImages.js";
import { computeStickerTransformStyle } from "../composables/useStickers.js";

const props = defineProps({
  images: {
    type: Array,
    default: () => [],
  },
  stickers: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits([
  "update-image",
  "change-image-mode",
  "delete-image",
  "view-lightbox",
  "update-sticker",
  "delete-sticker",
]);

const overlayRef = ref(null);
const selectedElementId = ref(null);

function getImageStyle(img) {
  return computeDraggableImageStyle(img);
}

function getStickerStyle(stk) {
  return computeStickerTransformStyle(stk);
}

// ---------------------------------------------------------------------------
// Image Drag & Resize Handlers
// ---------------------------------------------------------------------------
let activeImageDrag = null;

function startDragImage(e, img) {
  selectedElementId.value = img.id;
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const clientY = e.touches ? e.touches[0].clientY : e.clientY;
  const rect = overlayRef.value ? overlayRef.value.getBoundingClientRect() : null;

  activeImageDrag = {
    imgId: img.id,
    startX: clientX,
    startY: clientY,
    origX: img.x || 50,
    origY: img.y || 20,
    containerWidth: rect ? rect.width : window.innerWidth,
  };

  window.addEventListener("mousemove", onDraggingImage);
  window.addEventListener("mouseup", stopDragImage);
  window.addEventListener("touchmove", onDraggingImage, { passive: false });
  window.addEventListener("touchend", stopDragImage);
}

function onDraggingImage(e) {
  if (!activeImageDrag) return;
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const clientY = e.touches ? e.touches[0].clientY : e.clientY;

  const dx = clientX - activeImageDrag.startX;
  const dy = clientY - activeImageDrag.startY;

  const percentDeltaX = (dx / (activeImageDrag.containerWidth || 800)) * 100;
  const newX = Math.max(5, Math.min(95, Math.round(activeImageDrag.origX + percentDeltaX)));
  const newY = Math.max(0, Math.round(activeImageDrag.origY + dy));

  const target = props.images.find((i) => i.id === activeImageDrag.imgId);
  if (target) {
    target.x = newX;
    target.y = newY;
  }
}

function stopDragImage() {
  if (activeImageDrag) {
    const target = props.images.find((i) => i.id === activeImageDrag.imgId);
    if (target) {
      emit("update-image", { id: target.id, x: target.x, y: target.y, width: target.width });
    }
  }
  activeImageDrag = null;
  window.removeEventListener("mousemove", onDraggingImage);
  window.removeEventListener("mouseup", stopDragImage);
  window.removeEventListener("touchmove", onDraggingImage);
  window.removeEventListener("touchend", stopDragImage);
}

let activeImageResize = null;

function startResizeImage(e, img) {
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  activeImageResize = {
    imgId: img.id,
    startX: clientX,
    origWidth: img.width || 300,
  };

  window.addEventListener("mousemove", onResizingImage);
  window.addEventListener("mouseup", stopResizeImage);
  window.addEventListener("touchmove", onResizingImage, { passive: false });
  window.addEventListener("touchend", stopResizeImage);
}

function onResizingImage(e) {
  if (!activeImageResize) return;
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const dx = clientX - activeImageResize.startX;
  const newWidth = Math.max(120, Math.min(800, Math.round(activeImageResize.origWidth + dx)));

  const target = props.images.find((i) => i.id === activeImageResize.imgId);
  if (target) {
    target.width = newWidth;
  }
}

function stopResizeImage() {
  if (activeImageResize) {
    const target = props.images.find((i) => i.id === activeImageResize.imgId);
    if (target) {
      emit("update-image", { id: target.id, x: target.x, y: target.y, width: target.width });
    }
  }
  activeImageResize = null;
  window.removeEventListener("mousemove", onResizingImage);
  window.removeEventListener("mouseup", stopResizeImage);
  window.removeEventListener("touchmove", onResizingImage);
  window.removeEventListener("touchend", stopResizeImage);
}

// ---------------------------------------------------------------------------
// Sticker Drag & Resize Handlers
// ---------------------------------------------------------------------------
let activeStickerDrag = null;

function startDragSticker(e, stk) {
  selectedElementId.value = `stk_${stk.id}`;
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const clientY = e.touches ? e.touches[0].clientY : e.clientY;
  const rect = overlayRef.value ? overlayRef.value.getBoundingClientRect() : null;

  activeStickerDrag = {
    stkId: stk.id,
    startX: clientX,
    startY: clientY,
    origX: stk.pos_x ?? 50,
    origY: stk.pos_y ?? 50,
    containerWidth: rect ? rect.width : 800,
    containerHeight: rect ? rect.height : 600,
  };

  window.addEventListener("mousemove", onDraggingSticker);
  window.addEventListener("mouseup", stopDragSticker);
  window.addEventListener("touchmove", onDraggingSticker, { passive: false });
  window.addEventListener("touchend", stopDragSticker);
}

function onDraggingSticker(e) {
  if (!activeStickerDrag) return;
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const clientY = e.touches ? e.touches[0].clientY : e.clientY;

  const dx = clientX - activeStickerDrag.startX;
  const dy = clientY - activeStickerDrag.startY;

  const pctX = (dx / (activeStickerDrag.containerWidth || 800)) * 100;
  const pctY = (dy / (activeStickerDrag.containerHeight || 600)) * 100;

  const newX = Math.max(4, Math.min(96, Math.round(activeStickerDrag.origX + pctX)));
  const newY = Math.max(4, Math.min(96, Math.round(activeStickerDrag.origY + pctY)));

  const target = props.stickers.find((s) => s.id === activeStickerDrag.stkId);
  if (target) {
    target.pos_x = newX;
    target.pos_y = newY;
  }
}

function stopDragSticker() {
  if (activeStickerDrag) {
    const target = props.stickers.find((s) => s.id === activeStickerDrag.stkId);
    if (target) {
      emit("update-sticker", {
        id: target.id,
        pos_x: target.pos_x,
        pos_y: target.pos_y,
        rotation_deg: target.rotation_deg,
        scale: target.scale,
      });
    }
  }
  activeStickerDrag = null;
  window.removeEventListener("mousemove", onDraggingSticker);
  window.removeEventListener("mouseup", stopDragSticker);
  window.removeEventListener("touchmove", onDraggingSticker);
  window.removeEventListener("touchend", stopDragSticker);
}

// Sticker Scale / Resize
let activeStickerResize = null;

function startResizeSticker(e, stk) {
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const clientY = e.touches ? e.touches[0].clientY : e.clientY;

  activeStickerResize = {
    stkId: stk.id,
    startX: clientX,
    startY: clientY,
    origScale: stk.scale ?? 100,
  };

  window.addEventListener("mousemove", onResizingSticker);
  window.addEventListener("mouseup", stopResizeSticker);
  window.addEventListener("touchmove", onResizingSticker, { passive: false });
  window.addEventListener("touchend", stopResizeSticker);
}

function onResizingSticker(e) {
  if (!activeStickerResize) return;
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const clientY = e.touches ? e.touches[0].clientY : e.clientY;

  const dx = clientX - activeStickerResize.startX;
  const dy = clientY - activeStickerResize.startY;
  const delta = Math.round((dx + dy) / 2);

  const newScale = Math.max(40, Math.min(260, activeStickerResize.origScale + delta));
  const target = props.stickers.find((s) => s.id === activeStickerResize.stkId);
  if (target) {
    target.scale = newScale;
  }
}

function stopResizeSticker() {
  if (activeStickerResize) {
    const target = props.stickers.find((s) => s.id === activeStickerResize.stkId);
    if (target) {
      emit("update-sticker", {
        id: target.id,
        pos_x: target.pos_x,
        pos_y: target.pos_y,
        rotation_deg: target.rotation_deg,
        scale: target.scale,
      });
    }
  }
  activeStickerResize = null;
  window.removeEventListener("mousemove", onResizingSticker);
  window.removeEventListener("mouseup", stopResizeSticker);
  window.removeEventListener("touchmove", onResizingSticker);
  window.removeEventListener("touchend", stopResizeSticker);
}

function rotateSticker(stk) {
  const newRot = ((stk.rotation_deg || 0) + 15) % 360;
  stk.rotation_deg = newRot > 180 ? newRot - 360 : newRot;
  emit("update-sticker", {
    id: stk.id,
    pos_x: stk.pos_x,
    pos_y: stk.pos_y,
    rotation_deg: stk.rotation_deg,
    scale: stk.scale,
  });
}
</script>

<style scoped>
.journal-draggables-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: visible;
  z-index: 25;
}

/* --------------------------------------------------------------------------
   Draggable Image Card
   -------------------------------------------------------------------------- */
.draggable-image-card {
  pointer-events: auto;
  user-select: none;
  background: #ffffff;
  padding: 8px 8px 12px;
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.15s ease;
}

.draggable-image-card:hover,
.draggable-image-card.is-selected {
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15), 0 0 0 2px var(--primary-orange, #ea580c);
}

.image-actions-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 6px;
  padding: 2px 4px;
  background: var(--bg-hover, #f8fafc);
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
  background: #ffffff;
  border-radius: 4px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: #475569;
  transition: all 0.1s ease;
}

.img-btn-action:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
  color: #0f172a;
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
  background: var(--primary-orange, #ea580c);
  border-radius: 3px 0 7px 0;
}

/* --------------------------------------------------------------------------
   Draggable Sticker Card
   -------------------------------------------------------------------------- */
.draggable-sticker-card {
  pointer-events: auto;
  user-select: none;
  cursor: move;
  filter: drop-shadow(0 3px 8px rgba(0, 0, 0, 0.12));
  transition: filter 0.15s ease, outline 0.15s ease;
  position: absolute;
}

.draggable-sticker-card:hover,
.draggable-sticker-card.is-selected {
  filter: drop-shadow(0 6px 16px rgba(0, 0, 0, 0.18));
  outline: 1.5px dashed var(--primary-orange, #ea580c);
  border-radius: 6px;
}

.sticker-actions-pill {
  position: absolute;
  top: -22px;
  right: -8px;
  display: none;
  align-items: center;
  gap: 3px;
  background: rgba(28, 25, 23, 0.88);
  backdrop-filter: blur(4px);
  padding: 2px 4px;
  border-radius: 999px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  z-index: 30;
}

.draggable-sticker-card:hover .sticker-actions-pill,
.draggable-sticker-card.is-selected .sticker-actions-pill {
  display: flex;
}

.stk-action-btn {
  border: none;
  background: transparent;
  color: #ffffff;
  padding: 2px 4px;
  border-radius: 50%;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.65rem;
  line-height: 1;
  transition: background 0.1s ease;
}

.stk-action-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.stk-action-btn.stk-delete-btn:hover {
  background: #ef4444;
}

.sticker-art-wrap {
  display: block;
  width: 68px;
  height: 68px;
  pointer-events: none;
}

.journal-sticker-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  pointer-events: none;
}

.sticker-resize-handle {
  position: absolute;
  bottom: -4px;
  right: -4px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--primary-orange, #ea580c);
  border: 1.5px solid #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
  cursor: se-resize;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.draggable-sticker-card:hover .sticker-resize-handle,
.draggable-sticker-card.is-selected .sticker-resize-handle {
  opacity: 1;
}
</style>
