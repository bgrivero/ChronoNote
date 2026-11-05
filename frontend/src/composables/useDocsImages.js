/**
 * Docs-Style Image Layout Engine (Inline, Wrap, Above Text / Draggable)
 */

function numberOrDefault(value, fallback) {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function parseDocsImageDirectives(markdownText) {
  if (!markdownText) return { cleanMarkdown: "", floatingImages: [] };

  const floatingImages = [];
  // Match ![alt](url){mode="draggable", x="…", y="…", w="…", rot="…"}
  const directiveRegex = /!\[([^\]]*)\]\(([^)]+)\)\{(?:mode="([^"]*)")?(?:,\s*x="([^"]*)")?(?:,\s*y="([^"]*)")?(?:,\s*w="([^"]*)")?(?:,\s*rot="([^"]*)")?\}/g;

  let match;
  const cleanMarkdown = markdownText;

  while ((match = directiveRegex.exec(markdownText)) !== null) {
    const [fullMatch, caption, url, mode, xStr, yStr, wStr, rotationStr] = match;
    const imgMode = mode || "draggable";

    floatingImages.push({
      id: `img_${floatingImages.length + 1}`,
      rawDirective: fullMatch,
      caption: caption || "Uploaded Image",
      url,
      mode: imgMode,
      x: numberOrDefault(xStr, 50),
      y: numberOrDefault(yStr, 20),
      width: numberOrDefault(wStr, 300),
      rotation: numberOrDefault(rotationStr, 0),
    });
  }

  return { cleanMarkdown, floatingImages };
}

export function formatDocsImageMarkdown(caption, url, mode = "inline", x = 50, y = 20, width = 300, rotation = 0) {
  const safeCaption = caption || "Image";
  if (mode === "inline") {
    return `![${safeCaption}](${url})`;
  }
  if (mode === "wrap_left" || mode === "wrap_right") {
    return `![${safeCaption}](${url}){mode="${mode}", w="${width}"}`;
  }

  const rotationSuffix = Number(rotation) ? `, rot="${rotation}"` : "";
  return `![${safeCaption}](${url}){mode="draggable", x="${x}", y="${y}", w="${width}"${rotationSuffix}}`;
}

export function computeDraggableImageStyle(img) {
  const x = img.x ?? 50;
  const y = img.y ?? 20;
  const width = img.width ?? 300;
  const rotation = img.rotation ?? 0;

  return {
    position: "absolute",
    left: `${x}%`,
    top: `${y}px`,
    width: `${width}px`,
    transform: `translate(-50%, 0) rotate(${rotation}deg)`,
    zIndex: 20,
    cursor: "move",
  };
}
