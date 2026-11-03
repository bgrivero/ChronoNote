/**
 * Docs-Style Image Layout Engine (Inline, Wrap, Above Text / Draggable)
 */

export function parseDocsImageDirectives(markdownText) {
  if (!markdownText) return { cleanMarkdown: "", floatingImages: [] };

  const floatingImages = [];
  // Match ![alt](url){mode="draggable" ...} or @image(url, mode=..., x=..., y=..., width=...)
  const directiveRegex = /!\[([^\]]*)\]\(([^)]+)\)\{(?:mode="([^"]*)")?(?:,\s*x="([^"]*)")?(?:,\s*y="([^"]*)")?(?:,\s*w="([^"]*)")?\}/g;

  let match;
  let cleanMarkdown = markdownText;

  while ((match = directiveRegex.exec(markdownText)) !== null) {
    const [fullMatch, caption, url, mode, xStr, yStr, wStr] = match;
    const imgMode = mode || "draggable";
    const x = parseFloat(xStr) || 50;
    const y = parseFloat(yStr) || 20;
    const width = parseFloat(wStr) || 300;

    floatingImages.push({
      id: `img_${floatingImages.length + 1}`,
      rawDirective: fullMatch,
      caption: caption || "Uploaded Image",
      url,
      mode: imgMode,
      x,
      y,
      width,
    });
  }

  return { cleanMarkdown, floatingImages };
}

export function formatDocsImageMarkdown(caption, url, mode = "inline", x = 50, y = 20, width = 300) {
  const safeCaption = caption || "Image";
  if (mode === "inline") {
    return `![${safeCaption}](${url})`;
  }
  if (mode === "wrap_left" || mode === "wrap_right") {
    return `![${safeCaption}](${url}){mode="${mode}", w="${width}"}`;
  }
  // draggable / above text
  return `![${safeCaption}](${url}){mode="draggable", x="${x}", y="${y}", w="${width}"}`;
}

export function computeDraggableImageStyle(img) {
  const x = img.x ?? 50;
  const y = img.y ?? 20;
  const width = img.width ?? 300;

  return {
    position: "absolute",
    left: `${x}%`,
    top: `${y}px`,
    width: `${width}px`,
    transform: "translate(-50%, 0)",
    zIndex: 20,
    cursor: "move",
  };
}
