<template>
  <div
    ref="overlayRef"
    class="journal-draggables-layer"
    :class="{ 'is-interactive': mediaEditing }"
    :style="{ transform: `translateY(${-scrollOffset}px)` }"
    aria-label="Journal media layer"
    :aria-hidden="!mediaEditing"
    @click.stop="clearSelection"
  >
    <div
      v-for="img in images"
      :key="img.id"
      class="draggable-image-card"
      :class="{ 'is-selected': selectedElementId === img.id }"
      :style="getImageStyle(img)"
      @mousedown.stop="startDragImage($event, img)"
      @touchstart.stop="startDragImage($event, img)"
      @click.stop="selectElement(img.id)"
    >
      <div v-if="selectedElementId === img.id" class="image-actions-bar" @mousedown.stop @touchstart.stop>
        <span class="mode-badge">Image</span>
        <button type="button" class="img-btn-action" title="Switch to inline text" @click="$emit('change-image-mode', { id: img.id, mode: 'inline' })">Inline</button>
        <button type="button" class="img-btn-action delete-btn" title="Delete image" @click="$emit('delete-image', img)">Remove</button>
      </div>

      <div class="image-inner-frame">
        <img :src="img.url" :alt="img.caption || 'Journal image'" class="docs-draggable-img" draggable="false" />
        <span v-if="img.caption" class="image-caption">{{ img.caption }}</span>
      </div>

      <div
        v-if="selectedElementId === img.id"
        class="rotate-handle image-rotate-handle"
        title="Drag to rotate image"
        @mousedown.stop="startRotateImage($event, img)"
        @touchstart.stop="startRotateImage($event, img)"
      >↻</div>
      <div
        v-if="selectedElementId === img.id"
        class="resize-handle nw-handle"
        title="Drag a corner to resize image"
        @mousedown.stop="startResizeImage($event, img, -1)"
        @touchstart.stop="startResizeImage($event, img, -1)"
      />
      <div
        v-if="selectedElementId === img.id"
        class="resize-handle ne-handle"
        title="Drag a corner to resize image"
        @mousedown.stop="startResizeImage($event, img, 1)"
        @touchstart.stop="startResizeImage($event, img, 1)"
      />
      <div
        v-if="selectedElementId === img.id"
        class="resize-handle sw-handle"
        title="Drag a corner to resize image"
        @mousedown.stop="startResizeImage($event, img, -1)"
        @touchstart.stop="startResizeImage($event, img, -1)"
      />
      <div
        v-if="selectedElementId === img.id"
        class="resize-handle se-handle"
        title="Drag a corner to resize image"
        @mousedown.stop="startResizeImage($event, img, 1)"
        @touchstart.stop="startResizeImage($event, img, 1)"
      />
    </div>

    <div
      v-for="stk in stickers"
      :key="stk.id"
      class="draggable-sticker-card"
      :class="{ 'is-selected': selectedElementId === `stk_${stk.id}` }"
      :style="getStickerStyle(stk)"
      @mousedown.stop="startDragSticker($event, stk)"
      @touchstart.stop="startDragSticker($event, stk)"
      @click.stop="selectElement(`stk_${stk.id}`)"
    >
      <div v-if="selectedElementId === `stk_${stk.id}`" class="sticker-actions-panel" @mousedown.stop @touchstart.stop>
        <button type="button" class="stk-action-btn stk-delete-btn" title="Remove sticker" @click="$emit('delete-sticker', stk.id)">Remove</button>
      </div>

      <div class="sticker-art-wrap">
        <img :src="stk.image_url" :alt="stk.sticker_name" class="journal-sticker-img" draggable="false" />
      </div>

      <div v-if="selectedElementId === `stk_${stk.id}`" class="rotate-handle sticker-rotate-handle" title="Drag to rotate sticker" @mousedown.stop="startRotateSticker($event, stk)" @touchstart.stop="startRotateSticker($event, stk)">↻</div>
      <div v-if="selectedElementId === `stk_${stk.id}`" class="sticker-resize-handle nw-handle" title="Drag a corner to resize sticker" @mousedown.stop="startResizeSticker($event, stk, -1, -1)" @touchstart.stop="startResizeSticker($event, stk, -1, -1)" />
      <div v-if="selectedElementId === `stk_${stk.id}`" class="sticker-resize-handle ne-handle" title="Drag a corner to resize sticker" @mousedown.stop="startResizeSticker($event, stk, 1, -1)" @touchstart.stop="startResizeSticker($event, stk, 1, -1)" />
      <div v-if="selectedElementId === `stk_${stk.id}`" class="sticker-resize-handle sw-handle" title="Drag a corner to resize sticker" @mousedown.stop="startResizeSticker($event, stk, -1, 1)" @touchstart.stop="startResizeSticker($event, stk, -1, 1)" />
      <div v-if="selectedElementId === `stk_${stk.id}`" class="sticker-resize-handle se-handle" title="Drag a corner to resize sticker" @mousedown.stop="startResizeSticker($event, stk, 1, 1)" @touchstart.stop="startResizeSticker($event, stk, 1, 1)" />
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { computeDraggableImageStyle } from "../composables/useDocsImages.js";
import { computeStickerTransformStyle } from "../composables/useStickers.js";

const props = defineProps({
  images: { type: Array, default: () => [] },
  stickers: { type: Array, default: () => [] },
  mediaEditing: { type: Boolean, default: false },
  scrollOffset: { type: Number, default: 0 },
});

const emit = defineEmits([
  "update-image",
  "change-image-mode",
  "delete-image",
  "update-sticker",
  "delete-sticker",
]);

const overlayRef = ref(null);
const selectedElementId = ref(null);
let activeImageDrag = null;
let activeImageResize = null;
let activeImageRotation = null;
let activeStickerDrag = null;
let activeStickerResize = null;
let activeStickerRotation = null;

watch(() => props.mediaEditing, (enabled) => {
  if (!enabled) {
    selectedElementId.value = null;
    removeAllListeners();
  }
});

function getImageStyle(img) {
  return computeDraggableImageStyle(img);
}

function getStickerStyle(sticker) {
  return computeStickerTransformStyle(sticker);
}

function selectElement(id) {
  if (props.mediaEditing) selectedElementId.value = id;
}

function clearSelection() {
  selectedElementId.value = null;
}

function clearSelectionOnOutsidePointer(event) {
  if (props.mediaEditing && overlayRef.value && !overlayRef.value.contains(event.target)) {
    clearSelection();
  }
}

function pointerPosition(event) {
  const point = event.touches?.[0] || event.changedTouches?.[0] || event;
  return { x: point.clientX, y: point.clientY };
}

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, Math.round(value)));
}

function preventTouchScroll(event) {
  if (event.cancelable) event.preventDefault();
}

function addListeners(moveHandler, endHandler) {
  window.addEventListener("mousemove", moveHandler);
  window.addEventListener("mouseup", endHandler);
  window.addEventListener("touchmove", moveHandler, { passive: false });
  window.addEventListener("touchend", endHandler);
  window.addEventListener("touchcancel", endHandler);
}

function removeListeners(moveHandler, endHandler) {
  window.removeEventListener("mousemove", moveHandler);
  window.removeEventListener("mouseup", endHandler);
  window.removeEventListener("touchmove", moveHandler);
  window.removeEventListener("touchend", endHandler);
  window.removeEventListener("touchcancel", endHandler);
}

function removeAllListeners() {
  removeListeners(onDraggingImage, stopDragImage);
  removeListeners(onResizingImage, stopResizeImage);
  removeListeners(onRotatingImage, stopRotateImage);
  removeListeners(onDraggingSticker, stopDragSticker);
  removeListeners(onResizingSticker, stopResizeSticker);
  removeListeners(onRotatingSticker, stopRotateSticker);
  activeImageDrag = null;
  activeImageResize = null;
  activeImageRotation = null;
  activeStickerDrag = null;
  activeStickerResize = null;
  activeStickerRotation = null;
}

function updateImage(img, changes) {
  if (!props.mediaEditing) return;
  Object.assign(img, changes);
  emit("update-image", {
    id: img.id,
    x: img.x ?? 50,
    y: img.y ?? 20,
    width: img.width ?? 300,
    rotation: img.rotation ?? 0,
  });
}

function rotationAngle(event, card) {
  const point = pointerPosition(event);
  const rect = card.getBoundingClientRect();
  return Math.atan2(point.y - (rect.top + rect.height / 2), point.x - (rect.left + rect.width / 2)) * (180 / Math.PI);
}

function normalizeRotation(degrees) {
  const normalized = ((degrees + 180) % 360 + 360) % 360 - 180;
  return Math.round(normalized);
}

function startRotateImage(event, img) {
  if (!props.mediaEditing || event.button > 0) return;
  preventTouchScroll(event);
  const card = event.currentTarget.parentElement;
  activeImageRotation = {
    id: img.id,
    startAngle: rotationAngle(event, card),
    originalRotation: img.rotation ?? 0,
    card,
  };
  addListeners(onRotatingImage, stopRotateImage);
}

function onRotatingImage(event) {
  if (!activeImageRotation || !props.mediaEditing) return;
  preventTouchScroll(event);
  const target = props.images.find((image) => image.id === activeImageRotation.id);
  if (!target) return;
  target.rotation = normalizeRotation(
    activeImageRotation.originalRotation + rotationAngle(event, activeImageRotation.card) - activeImageRotation.startAngle
  );
}

function stopRotateImage() {
  if (activeImageRotation) {
    const target = props.images.find((image) => image.id === activeImageRotation.id);
    if (target) updateImage(target, {});
  }
  activeImageRotation = null;
  removeListeners(onRotatingImage, stopRotateImage);
}

function startDragImage(event, img) {
  if (!props.mediaEditing || event.button > 0) return;
  preventTouchScroll(event);
  selectElement(img.id);
  const point = pointerPosition(event);
  const rect = overlayRef.value?.getBoundingClientRect();
  activeImageDrag = {
    id: img.id,
    startX: point.x,
    startY: point.y,
    originalX: img.x ?? 50,
    originalY: img.y ?? 20,
    containerWidth: rect?.width || window.innerWidth,
    containerHeight: rect?.height || window.innerHeight,
  };
  addListeners(onDraggingImage, stopDragImage);
}

function onDraggingImage(event) {
  if (!activeImageDrag || !props.mediaEditing) return;
  preventTouchScroll(event);
  const point = pointerPosition(event);
  const target = props.images.find((image) => image.id === activeImageDrag.id);
  if (!target) return;
  const x = activeImageDrag.originalX + ((point.x - activeImageDrag.startX) / activeImageDrag.containerWidth) * 100;
  const y = activeImageDrag.originalY + point.y - activeImageDrag.startY;
  target.x = clamp(x, 5, 95);
  target.y = clamp(y, 0, Math.max(0, activeImageDrag.containerHeight - 40));
}

function stopDragImage() {
  if (activeImageDrag) {
    const target = props.images.find((image) => image.id === activeImageDrag.id);
    if (target) updateImage(target, {});
  }
  activeImageDrag = null;
  removeListeners(onDraggingImage, stopDragImage);
}

function startResizeImage(event, img, horizontalDirection) {
  if (!props.mediaEditing || event.button > 0) return;
  preventTouchScroll(event);
  const point = pointerPosition(event);
  activeImageResize = {
    id: img.id,
    startX: point.x,
    originalWidth: img.width ?? 300,
    horizontalDirection,
  };
  addListeners(onResizingImage, stopResizeImage);
}

function onResizingImage(event) {
  if (!activeImageResize || !props.mediaEditing) return;
  preventTouchScroll(event);
  const target = props.images.find((image) => image.id === activeImageResize.id);
  if (!target) return;
  target.width = clamp(
    activeImageResize.originalWidth +
      (pointerPosition(event).x - activeImageResize.startX) * activeImageResize.horizontalDirection,
    120,
    800
  );
}

function stopResizeImage() {
  if (activeImageResize) {
    const target = props.images.find((image) => image.id === activeImageResize.id);
    if (target) updateImage(target, {});
  }
  activeImageResize = null;
  removeListeners(onResizingImage, stopResizeImage);
}

function updateSticker(sticker, changes) {
  if (!props.mediaEditing) return;
  Object.assign(sticker, changes);
  emit("update-sticker", {
    id: sticker.id,
    pos_x: sticker.pos_x ?? 50,
    pos_y: sticker.pos_y ?? 50,
    rotation_deg: sticker.rotation_deg ?? 0,
    scale: sticker.scale ?? 100,
  });
}

function startRotateSticker(event, sticker) {
  if (!props.mediaEditing || event.button > 0) return;
  preventTouchScroll(event);
  const card = event.currentTarget.parentElement;
  activeStickerRotation = {
    id: sticker.id,
    startAngle: rotationAngle(event, card),
    originalRotation: sticker.rotation_deg ?? 0,
    card,
  };
  addListeners(onRotatingSticker, stopRotateSticker);
}

function onRotatingSticker(event) {
  if (!activeStickerRotation || !props.mediaEditing) return;
  preventTouchScroll(event);
  const target = props.stickers.find((sticker) => sticker.id === activeStickerRotation.id);
  if (!target) return;
  target.rotation_deg = normalizeRotation(
    activeStickerRotation.originalRotation + rotationAngle(event, activeStickerRotation.card) - activeStickerRotation.startAngle
  );
}

function stopRotateSticker() {
  if (activeStickerRotation) {
    const target = props.stickers.find((sticker) => sticker.id === activeStickerRotation.id);
    if (target) updateSticker(target, {});
  }
  activeStickerRotation = null;
  removeListeners(onRotatingSticker, stopRotateSticker);
}

function startDragSticker(event, sticker) {
  if (!props.mediaEditing || event.button > 0) return;
  preventTouchScroll(event);
  selectElement(`stk_${sticker.id}`);
  const point = pointerPosition(event);
  const rect = overlayRef.value?.getBoundingClientRect();
  activeStickerDrag = {
    id: sticker.id,
    startX: point.x,
    startY: point.y,
    originalX: sticker.pos_x ?? 50,
    originalY: sticker.pos_y ?? 50,
    containerWidth: rect?.width || 800,
    containerHeight: rect?.height || 600,
  };
  addListeners(onDraggingSticker, stopDragSticker);
}

function onDraggingSticker(event) {
  if (!activeStickerDrag || !props.mediaEditing) return;
  preventTouchScroll(event);
  const point = pointerPosition(event);
  const target = props.stickers.find((sticker) => sticker.id === activeStickerDrag.id);
  if (!target) return;
  target.pos_x = clamp(activeStickerDrag.originalX + ((point.x - activeStickerDrag.startX) / activeStickerDrag.containerWidth) * 100, 4, 96);
  target.pos_y = clamp(activeStickerDrag.originalY + ((point.y - activeStickerDrag.startY) / activeStickerDrag.containerHeight) * 100, 4, 96);
}

function stopDragSticker() {
  if (activeStickerDrag) {
    const target = props.stickers.find((sticker) => sticker.id === activeStickerDrag.id);
    if (target) updateSticker(target, {});
  }
  activeStickerDrag = null;
  removeListeners(onDraggingSticker, stopDragSticker);
}

function startResizeSticker(event, sticker, horizontalDirection, verticalDirection) {
  if (!props.mediaEditing || event.button > 0) return;
  preventTouchScroll(event);
  const point = pointerPosition(event);
  activeStickerResize = {
    id: sticker.id,
    startX: point.x,
    startY: point.y,
    originalScale: sticker.scale ?? 100,
    horizontalDirection,
    verticalDirection,
  };
  addListeners(onResizingSticker, stopResizeSticker);
}

function onResizingSticker(event) {
  if (!activeStickerResize || !props.mediaEditing) return;
  preventTouchScroll(event);
  const point = pointerPosition(event);
  const target = props.stickers.find((sticker) => sticker.id === activeStickerResize.id);
  if (!target) return;
  const distance =
    ((point.x - activeStickerResize.startX) * activeStickerResize.horizontalDirection +
      (point.y - activeStickerResize.startY) * activeStickerResize.verticalDirection) /
    2;
  target.scale = clamp(activeStickerResize.originalScale + distance, 40, 260);
}

function stopResizeSticker() {
  if (activeStickerResize) {
    const target = props.stickers.find((sticker) => sticker.id === activeStickerResize.id);
    if (target) updateSticker(target, {});
  }
  activeStickerResize = null;
  removeListeners(onResizingSticker, stopResizeSticker);
}

onMounted(() => window.addEventListener("pointerdown", clearSelectionOnOutsidePointer));
onBeforeUnmount(() => {
  removeAllListeners();
  window.removeEventListener("pointerdown", clearSelectionOnOutsidePointer);
});
</script>

<style scoped>
.journal-draggables-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: visible;
  z-index: 50;
  will-change: transform;
}

.journal-draggables-layer.is-interactive {
  pointer-events: none;
}

.draggable-image-card,
.draggable-sticker-card {
  pointer-events: none;
  user-select: none;
  touch-action: none;
}

.journal-draggables-layer.is-interactive .draggable-image-card,
.journal-draggables-layer.is-interactive .draggable-sticker-card {
  pointer-events: auto;
}

.draggable-image-card {
  background: #ffffff;
  padding: 8px 8px 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.15s ease;
}

.draggable-image-card.is-selected {
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15), 0 0 0 2px var(--primary-orange, #ea580c);
}

.image-actions-bar,
.sticker-actions-panel {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  padding: 5px 6px;
  background: var(--bg-hover, #f8fafc);
  border-radius: 6px;
  font-size: 0.72rem;
}

.mode-badge {
  font-size: 0.68rem;
  font-weight: 700;
  color: #4b5563;
}

.img-btn-action,
.stk-action-btn {
  border: 1px solid #e2e8f0;
  background: #ffffff;
  color: #475569;
  border-radius: 4px;
  padding: 3px 6px;
  font-size: 0.68rem;
  cursor: pointer;
}

.img-btn-action:hover,
.stk-action-btn:hover { background: #f1f5f9; color: #0f172a; }
.img-btn-action.delete-btn:hover,
.stk-delete-btn:hover { background: #fee2e2; color: #dc2626; border-color: #fca5a5; }

.image-inner-frame { display: flex; flex-direction: column; align-items: center; }
.docs-draggable-img { width: 100%; height: auto; border-radius: 4px; display: block; }
.image-caption { margin-top: 6px; color: #64748b; font-family: var(--font-serif, Georgia, serif); font-size: 0.74rem; font-style: italic; text-align: center; }

.resize-handle,
.sticker-resize-handle {
  position: absolute;
  width: 18px;
  height: 18px;
  background: var(--primary-orange, #ea580c);
  border: 2px solid #ffffff;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
}

.nw-handle { top: -7px; left: -7px; cursor: nw-resize; }
.ne-handle { top: -7px; right: -7px; cursor: ne-resize; }
.sw-handle { bottom: -7px; left: -7px; cursor: sw-resize; }
.se-handle { right: -7px; bottom: -7px; cursor: se-resize; }

.rotate-handle {
  position: absolute;
  z-index: 35;
  display: grid;
  width: 24px;
  height: 24px;
  place-items: center;
  border: 2px solid #ffffff;
  border-radius: 50%;
  background: var(--primary-orange, #ea580c);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.28);
  color: #ffffff;
  cursor: grab;
  font-size: 16px;
  font-weight: 700;
  line-height: 1;
}

.rotate-handle:active { cursor: grabbing; }
.image-rotate-handle { top: -14px; right: -14px; }
.sticker-rotate-handle { top: -14px; left: -14px; }

.draggable-sticker-card {
  position: absolute;
  cursor: move;
  filter: drop-shadow(0 3px 8px rgba(0, 0, 0, 0.12));
}

.draggable-sticker-card.is-selected {
  filter: drop-shadow(0 6px 16px rgba(0, 0, 0, 0.18));
  outline: 2px dashed var(--primary-orange, #ea580c);
  border-radius: 6px;
}

.sticker-actions-panel {
  position: absolute;
  top: -38px;
  right: -14px;
  z-index: 30;
  margin: 0;
  white-space: nowrap;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
}

.sticker-art-wrap { display: block; width: 68px; height: 68px; pointer-events: none; }
.journal-sticker-img { width: 100%; height: 100%; object-fit: contain; display: block; pointer-events: none; }

@media (max-width: 700px) {
  .image-actions-bar { flex-wrap: wrap; max-width: 250px; }
  .sticker-actions-panel { right: auto; left: 0; width: auto; white-space: normal; }
}
</style>
