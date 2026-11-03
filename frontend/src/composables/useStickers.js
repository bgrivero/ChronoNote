/**
 * Sticker Placement & Customization Composable
 */

export function filterStickersByTarget(placements, targetType, targetKey) {
  if (!Array.isArray(placements)) return [];
  return placements.filter(
    (p) => p.target_type === targetType && String(p.target_key) === String(targetKey)
  );
}

export function computeStickerTransformStyle(placement) {
  const x = placement.pos_x ?? 50;
  const y = placement.pos_y ?? 50;
  const rot = placement.rotation_deg ?? 0;
  const scale = (placement.scale ?? 100) / 100;

  return {
    left: `${x}%`,
    top: `${y}%`,
    transform: `translate(-50%, -50%) rotate(${rot}deg) scale(${scale})`,
    position: "absolute",
    pointerEvents: "auto",
    userSelect: "none",
  };
}

export function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    if (!file) {
      reject(new Error("No file provided"));
      return;
    }
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = (err) => reject(err);
    reader.readAsDataURL(file);
  });
}

export function sanitizeStickerCategory(category) {
  const valid = ["preset", "lifestyle", "study", "achievement", "custom"];
  const clean = String(category || "").toLowerCase().trim();
  return valid.includes(clean) ? clean : "custom";
}
