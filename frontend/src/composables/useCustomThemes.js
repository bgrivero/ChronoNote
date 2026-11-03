/**
 * Custom Visual Themes & Paper Styles Composable
 */

export const PAPER_THEMES = [
  { id: "clean_cream", name: "Warm Cream", bg: "#fdfbf7", desc: "Default calm editorial paper" },
  { id: "dot_grid", name: "Dot Grid", bg: "#fcfaf6", desc: "Bullet journal dot grid pattern" },
  { id: "lined_paper", name: "Lined Notebook", bg: "#fdfcf9", desc: "Classic college-ruled journal lines" },
  { id: "sepia_parchment", name: "Sepia Parchment", bg: "#f6ede0", desc: "Warm vintage archival parchment" },
  { id: "dark_slate", name: "Dark Slate", bg: "#1e293b", desc: "Serene night study slate" },
];

export const TYPOGRAPHY_THEMES = [
  { id: "editorial", name: "Regular Sans (Default)", fontHeader: "var(--font-sans)", fontBody: "var(--font-sans)" },
  { id: "handwritten", name: "Cozy Handwritten", fontHeader: '"Caveat", "Patrick Hand", cursive, serif', fontBody: 'system-ui, -apple-system, sans-serif' },
  { id: "monospace", name: "Clean Monospace", fontHeader: '"JetBrains Mono", "Fira Code", monospace', fontBody: '"JetBrains Mono", monospace' },
];

export const PROJECT_COLOR_PALETTES = [
  { name: "Terracotta", hex: "#e06c53" },
  { name: "Sage Emerald", hex: "#10b981" },
  { name: "Deep Indigo", hex: "#6366f1" },
  { name: "Amber Honey", hex: "#f59e0b" },
  { name: "Rose Quartz", hex: "#f43f5e" },
  { name: "Nordic Teal", hex: "#0891b2" },
  { name: "Dark Violet", hex: "#8b5cf6" },
  { name: "Warm Slate", hex: "#475569" },
];

const THEME_STORAGE_KEY = "chrononote_custom_visual_theme_v3";

export function loadCustomTheme() {
  try {
    const raw = localStorage.getItem(THEME_STORAGE_KEY);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch {
    // ignore
  }
  return {
    paperTheme: "clean_cream",
    typographyTheme: "editorial",
    activePalette: "#6366f1",
  };
}

export function saveCustomTheme(prefs) {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // ignore
  }
}

export function getPaperStyleClass(paperThemeId) {
  const valid = PAPER_THEMES.map((t) => t.id);
  return valid.includes(paperThemeId) ? `paper-theme-${paperThemeId}` : "paper-theme-clean_cream";
}

export function getTypographyClass(fontThemeId) {
  const valid = TYPOGRAPHY_THEMES.map((t) => t.id);
  return valid.includes(fontThemeId) ? `font-theme-${fontThemeId}` : "font-theme-editorial";
}
