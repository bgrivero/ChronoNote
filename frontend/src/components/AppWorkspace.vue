<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import LoginPage from "./LoginPage.vue";
import ChronoNoteLogo from "./ChronoNoteLogo.vue";
import HabitHeatmapView from "./HabitHeatmapView.vue";
import StudyModeView from "./StudyModeView.vue";
import StickerTrayDrawer from "./StickerTrayDrawer.vue";
import DocsImageOverlay from "./DocsImageOverlay.vue";
import AccountSettingsModal from "./AccountSettingsModal.vue";
import JournalDraggablesOverlay from "./JournalDraggablesOverlay.vue";
import CalendarTimeGrid from "./CalendarTimeGrid.vue";
import QuickTaskPopover from "./QuickTaskPopover.vue";
import CommandPalette from "./CommandPalette.vue";
import ArchiveVaultModal from "./ArchiveVaultModal.vue";
import { filterStickersByTarget, readFileAsDataUrl } from "../composables/useStickers.js";
import { parseDocsImageDirectives, formatDocsImageMarkdown } from "../composables/useDocsImages.js";
import {
  PAPER_THEMES,
  TYPOGRAPHY_THEMES,
  PROJECT_COLOR_PALETTES,
  loadCustomTheme,
  saveCustomTheme,
  getPaperStyleClass,
  getTypographyClass,
} from "../composables/useCustomThemes.js";
import {
  extractHabitPills,
  toggleHabitInMarkdown,
  applyTemplateVariables,
} from "../composables/useHabitsAndHeatmap.js";
import {
  WEEKDAY_SHORT,
  buildCalendarTimelineColumns,
  buildMonthlyWeekRows,
  buildFocusedWeekRow,
  calculateDateSpanDays,
  clipSubtaskToProjectRange,
  collectOverdueTasks,
  computeProjectDragResult,
  computeSubtaskDragResult,
  computeYearMonthGridSpan,
  extractJournalSnippet,
  extractProjectAreas,
  filterProjectsByStatus,
  filterSubtasksByStatus,
  formatEditorialDate,
  formatTimeDisplay,
  getOverdueNavigationTarget,
  groupProjectsForKanban,
  groupSidebarProjects,
  isProjectCompleted,
  isProjectOverdueExempt,
  isTaskOverdue,
  isTimedTask,
  moveProjectInKanban,
  renderMarkdownPreviewHtml,
  shiftDateIso,
  shiftDateMonths,
  toggleMarkdownCheckboxByIndex,
} from "../composables/useTimelineGeometry.js";
import {
  appendOcrToMarkdown,
  runBrowserHandwritingOcr,
} from "../composables/useHandwritingOcr.js";

// Automatically use relative "/api" in deployed production builds if VITE_API_BASE is not set
const API_BASE =
  import.meta.env?.VITE_API_BASE ||
  (typeof window !== "undefined" &&
  window.location.port &&
  window.location.port !== "8000"
    ? "http://localhost:8000/api"
    : "/api");

const ENV_GOOGLE_CLIENT_ID = import.meta.env?.VITE_GOOGLE_CLIENT_ID || "";

// Warm, curated editorial palette (replaces harsh neon swatches)
const COLOR_SWATCHES = [
  "#b85423", // Warm Terracotta
  "#2c666e", // Deep Verdigris
  "#4a7c59", // Sage Leaf
  "#6d597a", // Muted Plum
  "#b56576", // Dusty Rose
  "#b07d3b", // Raw Ochre
  "#3d5a80", // Slate Indigo
];

const DEFAULT_PROJECTS = [
  {
    id: 1,
    name: "Core Backend & PostgreSQL",
    slug: "core-backend-postgresql",
    description: "FastAPI, SQLAlchemy 2.0 & PostgreSQL 16 schema",
    color: "#b85423",
    status: "active",
    is_pinned: true,
    sidebar_order: 0,
    start_date: "2026-10-05",
    target_date: "2026-11-25",
  },
  {
    id: 2,
    name: "Editorial Calendar & Journal",
    slug: "minimal-kanban-calendar-timeline",
    description: "Warm paper workspace with daily journal & handwritten OCR",
    color: "#2c666e",
    status: "active",
    is_pinned: true,
    sidebar_order: 1,
    start_date: "2026-11-03",
    target_date: "2026-12-15",
  },
  {
    id: 3,
    name: "Markdown & WikiLink Engine",
    slug: "markdown-wikilink-engine",
    description: "Bidirectional [[WikiLinks]], YAML frontmatter & inline tasks",
    color: "#6d597a",
    status: "planned",
    is_pinned: true,
    sidebar_order: 2,
    start_date: "2026-11-10",
    target_date: "2026-12-28",
  },
  {
    id: 4,
    name: "Mobile & Cloud Sync",
    slug: "mobile-offline-sync",
    description: "Responsive phone layout, Google auth & online deployment",
    color: "#4a7c59",
    status: "on_hold",
    is_pinned: false,
    sidebar_order: 3,
    start_date: "2026-08-01",
    target_date: "2026-09-30",
  },
  {
    id: 5,
    name: "Initial Prototype Spec",
    slug: "initial-prototype-spec",
    description: "Architecture specification & test suite setup",
    color: "#b07d3b",
    status: "completed",
    is_pinned: false,
    sidebar_order: 4,
    start_date: "2026-09-01",
    target_date: "2026-10-15",
  },
];

const DEFAULT_DAILY_JOURNALS = {
  "2026-11-01": {
    id: 901,
    title: "Journal — 2026-11-01",
    note_date: "2026-11-01",
    is_daily_note: true,
    content_md: `Morning coffee and sketching out November priorities.
Want to keep my daily notes grounded in one calm place—both typed thoughts and photos of handwritten notebook pages.

- [x] Set up November project milestones @due(2026-11-01)
- [ ] Review weekly reading list`,
    updated_at: "2026-11-01T09:30:00Z",
  },
  "2026-11-04": {
    id: 902,
    title: "Journal — 2026-11-04",
    note_date: "2026-11-04",
    is_daily_note: true,
    content_md: `Mid-week reflection: simplifying the visual language made the calendar much easier to scan on my phone.
Linked thoughts to [[Initial Prototype Spec]]. #journal #reflection`,
    updated_at: "2026-11-04T20:15:00Z",
  },
};

// Primary Navigation Pages: 'timeline' | 'journal' | 'kanban'
const activePage = ref("timeline");

// Mobile Sidebar toggle for Timeline view
const showMobileProjectsSidebar = ref(false);

// Projects state
const projects = ref([...DEFAULT_PROJECTS]);

// Projects Kanban Drag-and-Drop state
const draggedProjectId = ref(null);
const dragOverColumnStatus = ref(null);
const dragOverProjectId = ref(null);
const dragDropPosition = ref("after"); // 'before' | 'after'

// Slide-Over Project Drawer state (null = closed; project id = open)
const selectedProjectId = ref(null);
const drawerTab = ref("subtasks"); // 'subtasks' | 'notes'

function getSystemTodayIso() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

// Daily Journal Drawer / Active Date state
// Clicking any date on Month View sets selectedJournalDate and opens the Journal Sheet!
const selectedJournalDate = ref(getSystemTodayIso());
const isJournalDrawerOpen = ref(false);
const dailyJournalsMap = ref({ ...DEFAULT_DAILY_JOURNALS });
const journalDraftTitle = ref(`Journal — ${getSystemTodayIso()}`);
const journalDraftMd = ref(DEFAULT_DAILY_JOURNALS[getSystemTodayIso()]?.content_md || "");

function navigateToDailyJournal(targetDate = null) {
  const target = targetDate || getSystemTodayIso();
  selectedJournalDate.value = target;
  if (requestJournalAccess(target, false)) {
    activePage.value = "journal";
    openDailyJournalForDate(target, false);
  }
}
const journalSaveStatus = ref(""); // '' | 'saving' | 'saved'
const isEditingJournal = ref(false);
const isJournalMediaEditing = ref(false);
const journalMediaScrollTop = ref(0);
const activeJournalSurface = ref("main");
const journalTextareaRef = ref(null);
const drawerJournalTextareaRef = ref(null);
const journalPreviewRef = ref(null);
const drawerJournalPreviewRef = ref(null);

function handleJournalContentScroll(event) {
  journalMediaScrollTop.value = event.target.scrollTop;
}

function startEditingJournal(isDrawer = false) {
  activeJournalSurface.value = isDrawer ? "drawer" : "main";
  const preview = isDrawer ? drawerJournalPreviewRef.value : journalPreviewRef.value;
  journalMediaScrollTop.value = preview?.scrollTop ?? 0;
  isEditingJournal.value = true;
  nextTick(() => {
    const textarea = isDrawer ? drawerJournalTextareaRef.value : journalTextareaRef.value;
    if (textarea) {
      textarea.scrollTop = journalMediaScrollTop.value;
      textarea.focus();
    }
  });
}

async function stopEditingJournal() {
  const isDrawer = activeJournalSurface.value === "drawer";
  const textarea = isDrawer ? drawerJournalTextareaRef.value : journalTextareaRef.value;
  journalMediaScrollTop.value = textarea?.scrollTop ?? journalMediaScrollTop.value;
  isEditingJournal.value = false;
  await nextTick();
  const preview = isDrawer ? drawerJournalPreviewRef.value : journalPreviewRef.value;
  if (preview) preview.scrollTop = journalMediaScrollTop.value;
  await saveDailyJournalEntry();
}

async function toggleJournalMediaEditing() {
  if (isEditingJournal.value) await stopEditingJournal();
  isJournalMediaEditing.value = !isJournalMediaEditing.value;
}

async function openJournalStickerTray() {
  if (isEditingJournal.value) await stopEditingJournal();
  activeStickerTarget.value = { type: "journal", key: selectedJournalDate.value };
  isStickerDrawerOpen.value = true;
  await Promise.all([fetchStickers(), fetchStickerPlacements()]);
}

// Template Customization & Manager state
const showTemplateManagerModal = ref(false);
const editingTemplateId = ref(null);
const templateForm = ref({
  name: "",
  description: "",
  content_md: "",
  is_default: false,
});
const templateManagerStatus = ref("");
const templateManagerError = ref("");

// Habits & Habit Analytics state
const habitsList = ref([]);
const habitAnalytics = ref({ days: [], overall_stats: {}, habit_streaks: [] });
const availableTemplates = ref([]);
const showTemplateMenu = ref(false);

// Active habits computed list
const activeHabits = computed(() => {
  return (habitsList.value || []).filter((h) => !h.archived);
});

// Journal Password & Session Protection state
const journalSessionToken = ref(
  (typeof sessionStorage !== "undefined" &&
    sessionStorage.getItem("chrononote_journal_session_token")) ||
    ""
);
const hasJournalPassword = ref(
  (typeof localStorage !== "undefined" &&
    localStorage.getItem("chrononote_has_journal_password") === "true") ||
    false
);
const isJournalUnlocked = ref(!hasJournalPassword.value || Boolean(journalSessionToken.value));
const showJournalUnlockModal = ref(false);
const journalPasswordInput = ref("");
const journalUnlockError = ref("");
const pendingJournalDate = ref(null);
const pendingJournalDrawer = ref(false);

// Journal Set/Change Password Dialog state
const showJournalSettingsModal = ref(false);
const journalSettingsCurrentPw = ref("");
const journalSettingsNewPw = ref("");
const journalSettingsConfirmPw = ref("");
const journalSettingsError = ref("");
const journalSettingsSuccess = ref("");

// Handwritten OCR state (used by Daily Journal)
const ocrTarget = ref("journal");
const ocrStatusText = ref("");
const ocrProgress = ref(0);
const isOcrRunning = ref(false);
const ocrEnhanceContrast = ref(true);
const ocrPreviewUrl = ref("");
const ocrExtractedText = ref("");
const ocrError = ref("");
const includeOcrHeading = ref(true);
const hasServerOcrKey = ref(false);
const geminiApiKeyInput = ref("");

// Google Authentication state
const currentUser = ref(null);
const lastUser = ref(null);
const authToken = ref("");
const googleClientId = ref(ENV_GOOGLE_CLIENT_ID);
const authRequired = ref(false);
const showAuthModal = ref(false);
const showMcpModal = ref(false);
const mcpClientTarget = ref("antigravity");
const mcpCodeLoading = ref(false);
const mcpCodeError = ref("");
const mcpConnectData = ref(null);
const mcpCopied = ref(false);
const mcpConfigCopied = ref(false);

const antigravityConfigSnippet = computed(() => {
  const isLocal =
    typeof window !== "undefined" &&
    ["localhost", "127.0.0.1"].includes(window.location.hostname);
  if (isLocal) {
    return JSON.stringify(
      {
        mcpServers: {
          "chrononote-local": {
            command: "python",
            args: ["run_mcp.py"],
            env: { PYTHONPATH: "." },
          },
        },
      },
      null,
      2
    );
  }
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return JSON.stringify(
    {
      mcpServers: {
        chrononote: {
          url: `${origin}/mcp-http/`,
        },
      },
    },
    null,
    2
  );
});

async function openMcpConnectModal(target = "antigravity") {
  mcpClientTarget.value = target;
  showMcpModal.value = true;
  mcpCodeLoading.value = true;
  mcpCodeError.value = "";
  mcpCopied.value = false;
  mcpConfigCopied.value = false;
  try {
    const res = await fetch(`${API_BASE}/auth/mcp-code`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to generate connection code");
    }
    mcpConnectData.value = await res.json();
  } catch (err) {
    mcpCodeError.value = err.message || "Failed to generate connection code";
  } finally {
    mcpCodeLoading.value = false;
  }
}

async function copyMcpCode() {
  if (!mcpConnectData.value?.code) return;
  try {
    await navigator.clipboard.writeText(mcpConnectData.value.code);
    mcpCopied.value = true;
    setTimeout(() => {
      mcpCopied.value = false;
    }, 2500);
  } catch {
    // fallback
  }
}

async function copyAntigravityConfig() {
  try {
    await navigator.clipboard.writeText(antigravityConfigSnippet.value);
    mcpConfigCopied.value = true;
    setTimeout(() => {
      mcpConfigCopied.value = false;
    }, 2500);
  } catch {
    // fallback
  }
}

const authEmailInput = ref("");
const authNameInput = ref("");
const authError = ref("");
const isAuthenticating = ref(false);
const googleBtnContainer = ref(null);

// Subtask status filter: 'all' | 'active' | 'done'
const taskFilterMode = ref("all");

// Show/hide Quick Add Project form in Timeline Left Sidebar
const showTimelineAddProject = ref(false);

// New Project form state
const newProject = ref({
  name: "",
  description: "",
  area: "",
  status: "active",
  color: "#c2410c",
  start_date: "2026-11-01",
  target_date: "2026-11-30",
  is_pinned: true,
});

// New Subtask (A1, A2...) form state inside Slide-Over Drawer
const newSubtask = ref({
  title: "",
  description: "",
  start_date: "2026-11-05",
  due_date: "2026-11-12",
  start_time: "",
  end_time: "",
  priority: "medium",
  is_milestone: false,
  color: "#2c666e",
  deadline_only: false,
});

// Calendar Timeline Controls
const calendarScaleMode = ref("month"); // 'day' | 'week' | 'month' | 'year'
const todayIso = ref(getSystemTodayIso());
const selectedYear = ref(new Date().getFullYear());
const selectedMonth = ref(new Date().getMonth() + 1);
const selectedWeekAnchorIso = ref(todayIso.value);
const selectedDayIso = ref(todayIso.value);
const calendarProjectDisplayMode = ref("all"); // 'all' | 'milestones'

// Workspace Organization, Archiving, Quick-Create & Command Palette State
const isNavSpineOpen = ref(false);
const isSidebarCollapsed = ref(false);
const sidebarSearchQuery = ref("");
const selectedAreaFilter = ref("all");
const sidebarSectionsOpen = ref({
  pinned: true,
  active: true,
  later: false,
  completed: false,
});
const archivedProjects = ref([]);
const showArchiveModal = ref(false);
const showCommandPalette = ref(false);
const showDisplayMenu = ref(false);
const displayMenuRef = ref(null);
const projectsPageView = ref("board"); // 'board' | 'list' | 'archive'
const projectsSearchQuery = ref("");
const hideCompletedProjects = ref(false);
const showNewProjectModal = ref(false);
const collapsedKanbanCols = ref({ completed: false });
const quickTaskModalOpen = ref(false);
const quickTaskDraft = ref({});
const monthDragCreate = ref(null);

// Toast / Undo Snackbar state
const toastNotification = ref(null);
let toastTimer = null;

function showNotification({
  message,
  type = "info",
  undoLabel = null,
  undoFn = null,
  durationMs = 5500,
} = {}) {
  if (!message) return;
  if (toastTimer) clearTimeout(toastTimer);
  toastNotification.value = { message, type, undoLabel, undoFn };
  toastTimer = setTimeout(() => {
    toastNotification.value = null;
    toastTimer = null;
  }, durationMs);
}

function dismissToast() {
  if (toastTimer) clearTimeout(toastTimer);
  toastNotification.value = null;
  toastTimer = null;
}

async function triggerToastUndo() {
  const fn = toastNotification.value?.undoFn;
  dismissToast();
  if (typeof fn === "function") {
    await fn();
  }
}

// Decoupled Standalone One-Off Tasks (Inbox) — starts clean with no random mock items
const standaloneTasks = ref([]);
const standalonePendingCount = computed(
  () => standaloneTasks.value.filter((t) => t.status !== "done").length
);

function jumpToToday() {
  const nowIso = getSystemTodayIso();
  todayIso.value = nowIso;
  const parts = nowIso.split("-").map(Number);
  if (parts.length === 3) {
    selectedYear.value = parts[0];
    selectedMonth.value = parts[1];
  }
  selectedWeekAnchorIso.value = nowIso;
  selectedDayIso.value = nowIso;
}

function switchToWeekMode() {
  calendarScaleMode.value = "week";
  const nowParts = todayIso.value.split("-").map(Number);
  if (
    nowParts.length === 3 &&
    selectedYear.value === nowParts[0] &&
    selectedMonth.value === nowParts[1]
  ) {
    selectedWeekAnchorIso.value = todayIso.value;
  } else {
    const mStr = String(selectedMonth.value).padStart(2, "0");
    selectedWeekAnchorIso.value = `${selectedYear.value}-${mStr}-01`;
  }
}

function switchToDayMode(iso = null) {
  calendarScaleMode.value = "day";
  if (iso) {
    selectedDayIso.value = iso;
    return;
  }
  const nowParts = todayIso.value.split("-").map(Number);
  if (
    nowParts.length === 3 &&
    selectedYear.value === nowParts[0] &&
    selectedMonth.value === nowParts[1]
  ) {
    selectedDayIso.value = todayIso.value;
  } else {
    const mStr = String(selectedMonth.value).padStart(2, "0");
    selectedDayIso.value = `${selectedYear.value}-${mStr}-01`;
  }
}

function loadVisibleSubtaskProjectIds() {
  try {
    const raw = localStorage.getItem("chrononote_visible_subtasks");
    if (raw) {
      const arr = JSON.parse(raw);
      if (Array.isArray(arr)) return new Set(arr);
    }
  } catch {}
  return new Set([1, 2, 3]);
}

// Set of project IDs whose subtasks are currently visible on the timeline
const visibleTimelineSubtaskProjectIds = ref(loadVisibleSubtaskProjectIds());

function persistVisibleSubtaskProjectIds() {
  try {
    localStorage.setItem(
      "chrononote_visible_subtasks",
      JSON.stringify(Array.from(visibleTimelineSubtaskProjectIds.value))
    );
  } catch {}
}

function isProjectSubtasksVisible(projectId) {
  return visibleTimelineSubtaskProjectIds.value.has(projectId);
}

function toggleProjectSubtasksVisibility(projectId) {
  const next = new Set(visibleTimelineSubtaskProjectIds.value);
  if (next.has(projectId)) {
    next.delete(projectId);
  } else {
    next.add(projectId);
  }
  visibleTimelineSubtaskProjectIds.value = next;
  persistVisibleSubtaskProjectIds();
}

function expandAllTimelineSubtasks() {
  const allIds = projects.value.map((p) => p.id);
  visibleTimelineSubtaskProjectIds.value = new Set(allIds);
  persistVisibleSubtaskProjectIds();
}

function collapseAllTimelineSubtasks() {
  visibleTimelineSubtaskProjectIds.value = new Set();
  persistVisibleSubtaskProjectIds();
}

// Subtasks per project (each subtask holds its own notes / description)
const projectTasksMap = ref({
  1: [
    {
      id: 101,
      project_id: 1,
      title: "PostgreSQL schema & migrations",
      description: "- [x] Async engine & connection pool pre-ping\n- [x] Cascade foreign keys configured\n- [ ] Multi-tenant user isolation verified",
      status: "done",
      color: "#2c666e",
      start_date: "2026-11-01",
      due_date: "2026-11-05",
    },
    {
      id: 102,
      project_id: 1,
      title: "Benchmark PostgreSQL connection pooling",
      description: "Measure p95 query latency under 150 concurrent workers with asyncpg pooling.",
      status: "todo",
      color: "#2c666e",
      start_date: "2026-11-04",
      due_date: "2026-11-10",
    },
    {
      id: 103,
      project_id: 1,
      title: "Auto-cascading dependency scheduler",
      description: "DFS topological sort with cycle validation before applying date shifts.",
      status: "todo",
      color: "#4a7c59",
      start_date: "2026-11-06",
      due_date: "2026-11-12",
    },
  ],
  2: [
    {
      id: 201,
      project_id: 2,
      title: "Ship 1-row-per-week Monthly Calendar UI",
      description: "- [x] 7-column calendar matrix (Sun to Sat)\n- [x] Dynamic vertical track allocation",
      status: "done",
      color: "#2c666e",
      start_date: "2026-11-03",
      due_date: "2026-11-09",
    },
    {
      id: 202,
      project_id: 2,
      title: "Daily journal & handwritten OCR integration",
      description: "Direct camera photo capture with offline OCR review panel and Markdown appending.",
      status: "todo",
      color: "#6d597a",
      start_date: "2026-11-11",
      due_date: "2026-11-19",
    },
  ],
});

// Markdown Note state inside the Project Slide-Over Drawer
const activeNote = ref({
  id: null,
  project_id: null,
  title: "",
  content_md: "",
});

// Unique sorted list of project areas/folders
const projectAreas = computed(() => extractProjectAreas(projects.value));

// Filtered projects for the Projects Board / List page
const filteredProjectsForBoard = computed(() => {
  const q = projectsSearchQuery.value.trim().toLowerCase();
  const area = selectedAreaFilter.value;
  return projects.value.filter((p) => {
    if (p.status === "archived") return false;
    if (hideCompletedProjects.value && isProjectCompleted(p)) return false;
    const projArea = (p.area || "").trim();
    if (area && area !== "all") {
      if (area === "__none__" && projArea) return false;
      if (area !== "__none__" && projArea !== area) return false;
    }
    if (q) {
      const hay = `${p.name || ""} ${p.description || ""} ${projArea}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
});

// Group filtered projects into the 4 Kanban columns
const projectKanbanColumns = computed(() =>
  groupProjectsForKanban(filteredProjectsForBoard.value)
);

// Sidebar projects filtered by the current All | Active | Overdue | Completed tab
const sidebarProjects = computed(() =>
  filterProjectsByStatus(
    projects.value.filter((p) => p.status !== "archived"),
    taskFilterMode.value,
    projectTasksMap.value,
    todayIso.value
  )
);

// Grouped sidebar buckets (pinned / active / later / completed) with search & area filters
const sidebarGroups = computed(() =>
  groupSidebarProjects(sidebarProjects.value, {
    query: sidebarSearchQuery.value,
    area: selectedAreaFilter.value,
  })
);

// Pinned projects shown on the Timeline:
// - 'all': shows all pinned projects (active and done)
// - 'active': hides finished projects so only active projects appear
// - 'overdue': hides finished projects so only non-completed projects are eligible
// - 'done': shows completed projects (or projects with completed subtasks)
const pinnedProjects = computed(() =>
  projects.value.filter((p) => {
    if (!p.is_pinned || p.status === "archived") return false;
    if (taskFilterMode.value === "active") {
      return !isProjectCompleted(p);
    }
    if (taskFilterMode.value === "overdue") {
      return !isProjectOverdueExempt(p);
    }
    if (taskFilterMode.value === "done") {
      const tasks = projectTasksMap.value[p.id] || [];
      const hasDoneTask = tasks.some((t) => t.status === "done");
      return isProjectCompleted(p) || hasDoneTask;
    }
    return true;
  })
);

// Projects that have a swimlane in Year View:
// Either pinned projects OR unpinned projects whose subtasks are explicitly toggled visible
const timelineSwimlaneProjects = computed(() => {
  const list = [];
  const seen = new Set();
  for (const p of pinnedProjects.value) {
    seen.add(p.id);
    list.push(p);
  }
  for (const p of projects.value) {
    if (
      !seen.has(p.id) &&
      p.status !== "archived" &&
      isProjectSubtasksVisible(p.id)
    ) {
      seen.add(p.id);
      list.push(p);
    }
  }
  return list;
});

// Currently selected project object for the Slide-Over Drawer
const selectedProject = computed(() => {
  if (selectedProjectId.value === 0 || selectedProjectId.value === "inbox") {
    return {
      id: 0,
      name: "Inbox & One-Off Tasks",
      color: "#e11d48",
      status: "active",
      description: "Decoupled standalone tasks not tied to any project",
      start_date: todayIso.value,
      target_date: todayIso.value,
      is_pinned: false,
    };
  }
  return projects.value.find((p) => p.id === selectedProjectId.value) || null;
});

// Deduplicated, chronologically sorted overdue tasks across Inbox & active projects
const overdueTasksList = computed(() =>
  collectOverdueTasks(
    projectTasksMap.value,
    standaloneTasks.value,
    projects.value,
    todayIso.value
  )
);

const totalOverdueTasksCount = computed(() => overdueTasksList.value.length);

// Prev/Next Overdue Task Navigator state on the calendar
const activeOverdueIndex = ref(0);
const focusedOverdueTaskId = ref(null);
const focusedOverdueDateIso = ref(null);

const activeOverdueTask = computed(() => {
  const list = overdueTasksList.value;
  if (!list.length) return null;
  const idx = Math.min(Math.max(activeOverdueIndex.value, 0), list.length - 1);
  return list[idx] || null;
});

function scrollFocusedOverdueIntoView(taskId, dateIso) {
  if (typeof document === "undefined") return;
  const taskEl =
    taskId !== null && taskId !== undefined
      ? document.querySelector(`[data-overdue-task-id="${taskId}"]`)
      : null;
  const dayEl = dateIso
    ? document.querySelector(`[data-calendar-day-iso="${dateIso}"]`)
    : null;
  const targetEl = taskEl || dayEl;
  if (targetEl && typeof targetEl.scrollIntoView === "function") {
    targetEl.scrollIntoView({
      behavior: "smooth",
      block: "center",
      inline: "nearest",
    });
  }
}

async function jumpToOverdueTaskAt(targetIndex, { scroll = true } = {}) {
  const list = overdueTasksList.value;
  const nav = getOverdueNavigationTarget(list, targetIndex, 0);
  activeOverdueIndex.value = nav.index;

  if (!nav.task) {
    focusedOverdueTaskId.value = null;
    focusedOverdueDateIso.value = null;
    return;
  }

  focusedOverdueTaskId.value = nav.task.id;
  focusedOverdueDateIso.value = nav.targetDateIso;

  if (calendarScaleMode.value === "year") {
    calendarScaleMode.value = "month";
  }

  if (nav.year !== null && nav.month !== null) {
    selectedYear.value = nav.year;
    selectedMonth.value = nav.month;
  }
  if (nav.targetDateIso) {
    selectedWeekAnchorIso.value = nav.targetDateIso;
    selectedDayIso.value = nav.targetDateIso;
  }

  if (scroll) {
    await nextTick();
    scrollFocusedOverdueIntoView(nav.task.id, nav.targetDateIso);
  }
}

async function moveOverdueTaskToToday(task) {
  if (!task) return;
  const origStart = task.start_date;
  const origDue = task.due_date;
  const targetIso = todayIso.value;
  const nextStart =
    origStart && origStart <= targetIso ? origStart : targetIso;
  const pid = task.project_id ?? 0;

  await updateSubtaskFields(pid, task.id, {
    start_date: nextStart,
    due_date: targetIso,
  });

  showNotification({
    type: "success",
    message: `Moved "${task.title}" to Today`,
    undoLabel: "Undo",
    undoFn: async () => {
      await updateSubtaskFields(pid, task.id, {
        start_date: origStart,
        due_date: origDue,
      });
    },
  });
}

async function enterOverdueMode(toggle = false) {
  if (toggle && taskFilterMode.value === "overdue") {
    exitOverdueFilter();
    return;
  }
  const wasOverdue = taskFilterMode.value === "overdue";
  taskFilterMode.value = "overdue";
  showMobileProjectsSidebar.value = false;

  if (overdueTasksList.value.length > 0) {
    await jumpToOverdueTaskAt(wasOverdue ? activeOverdueIndex.value : 0);
  } else {
    activeOverdueIndex.value = 0;
    focusedOverdueTaskId.value = null;
    focusedOverdueDateIso.value = null;
  }
}

function exitOverdueFilter() {
  taskFilterMode.value = "all";
  focusedOverdueTaskId.value = null;
  focusedOverdueDateIso.value = null;
}

async function stepOverdueTask(delta) {
  const list = overdueTasksList.value;
  if (!list.length) return;
  const nav = getOverdueNavigationTarget(list, activeOverdueIndex.value, delta);
  await jumpToOverdueTaskAt(nav.index);
}

watch(taskFilterMode, (mode) => {
  if (mode !== "overdue") {
    focusedOverdueTaskId.value = null;
    focusedOverdueDateIso.value = null;
  }
});

watch(overdueTasksList, (list) => {
  if (!list.length) {
    activeOverdueIndex.value = 0;
    focusedOverdueTaskId.value = null;
    focusedOverdueDateIso.value = null;
    return;
  }
  if (taskFilterMode.value !== "overdue") {
    if (activeOverdueIndex.value >= list.length) {
      activeOverdueIndex.value = 0;
    }
    return;
  }
  const existingIdx =
    focusedOverdueTaskId.value !== null && focusedOverdueTaskId.value !== undefined
      ? list.findIndex((t) => t.id === focusedOverdueTaskId.value)
      : -1;
  const nextIdx =
    existingIdx >= 0
      ? existingIdx
      : Math.min(Math.max(activeOverdueIndex.value, 0), list.length - 1);
  activeOverdueIndex.value = nextIdx;
  const nextTask = list[nextIdx];
  focusedOverdueTaskId.value = nextTask ? nextTask.id : null;
  focusedOverdueDateIso.value = nextTask
    ? nextTask.due_date || nextTask.start_date || null
    : null;
});

// Letter prefix for the selected project (A, B, C...)
const selectedProjectPrefix = computed(() => {
  if (!selectedProject.value) return "A";
  const swimlaneIdx = timelineSwimlaneProjects.value.findIndex(
    (p) => p.id === selectedProject.value.id
  );
  if (swimlaneIdx >= 0) return String.fromCharCode(65 + (swimlaneIdx % 26));
  const allIdx = projects.value.findIndex(
    (p) => p.id === selectedProject.value.id
  );
  return String.fromCharCode(65 + (Math.max(allIdx, 0) % 26));
});

// Subtasks for the selected project with their codes (A1, A2...)
const selectedProjectSubtasks = computed(() => {
  if (!selectedProject.value) return [];
  const raw = projectTasksMap.value[selectedProject.value.id] || [];
  const prefix = selectedProjectPrefix.value;
  const withCodes = raw.map((t, idx) => ({
    ...t,
    code: `${prefix}${idx + 1}`,
  }));
  return filterSubtasksByStatus(withCodes, taskFilterMode.value, todayIso.value);
});

const nextSubtaskCode = computed(() => {
  if (!selectedProject.value) return "A1";
  const count = (projectTasksMap.value[selectedProject.value.id] || []).length;
  return `${selectedProjectPrefix.value}${count + 1}`;
});

// Year Mode: 12 Month columns
const yearCalendarSpec = computed(() =>
  buildCalendarTimelineColumns(selectedYear.value, null)
);

// Month Mode: 1-Row-Per-Week Calendar Grid with taskFilterMode + dailyNotesMap applied
const monthlyWeeksSpec = computed(() =>
  buildMonthlyWeekRows(
    selectedYear.value,
    selectedMonth.value,
    pinnedProjects.value,
    projectTasksMap.value,
    {
      taskFilterMode: taskFilterMode.value,
      projectDisplayMode: calendarProjectDisplayMode.value,
      standaloneTasks: standaloneTasks.value,
      dailyNotesMap: dailyJournalsMap.value,
      todayIso: todayIso.value,
      visibleSubtaskProjectIds: visibleTimelineSubtaskProjectIds.value,
      allProjects: projects.value,
    }
  )
);

// Week Mode: 1 Focused 7-Day Week with full clipping & dragging
const focusedWeekSpec = computed(() =>
  buildFocusedWeekRow(
    selectedWeekAnchorIso.value,
    pinnedProjects.value,
    projectTasksMap.value,
    {
      taskFilterMode: taskFilterMode.value,
      projectDisplayMode: calendarProjectDisplayMode.value,
      standaloneTasks: standaloneTasks.value,
      dailyNotesMap: dailyJournalsMap.value,
      todayIso: todayIso.value,
      visibleSubtaskProjectIds: visibleTimelineSubtaskProjectIds.value,
      allProjects: projects.value,
    }
  )
);

const focusedWeekAllDayItems = computed(() =>
  (focusedWeekSpec.value.items || []).filter(
    (item) => !(item.kind === "task" && item.startTime)
  )
);

// Day Mode: 1 Focused Day with all-day strip + hourly time grid
const dayViewSpec = computed(() => {
  const iso = selectedDayIso.value || todayIso.value;
  const weekSpec = buildFocusedWeekRow(
    iso,
    pinnedProjects.value,
    projectTasksMap.value,
    {
      taskFilterMode: taskFilterMode.value,
      projectDisplayMode: calendarProjectDisplayMode.value,
      standaloneTasks: standaloneTasks.value,
      dailyNotesMap: dailyJournalsMap.value,
      todayIso: todayIso.value,
      visibleSubtaskProjectIds: visibleTimelineSubtaskProjectIds.value,
      allProjects: projects.value,
    }
  );
  const dayIdx = (weekSpec.days || []).findIndex((d) => d.iso === iso);
  const colNum = dayIdx >= 0 ? dayIdx + 1 : 1;
  const targetDay = dayIdx >= 0 ? weekSpec.days[dayIdx] : weekSpec.days[0];

  const allDayItems = (weekSpec.items || [])
    .filter((item) => {
      if (item.kind === "task" && item.startTime) return false;
      const startCol = item.startCol || 1;
      const endCol = item.endCol || startCol;
      return colNum >= startCol && colNum <= endCol;
    })
    .map((item, idx) => ({
      ...item,
      startCol: 1,
      spanCols: 1,
      endCol: 1,
      trackRow: idx + 1,
    }));

  return {
    days: targetDay ? [{ ...targetDay, col: 1 }] : [],
    allDayItems,
    rangeText: formatEditorialDate(iso).full,
  };
});

// Timed tasks bucketed by ISO date for Day & Week hourly grids
const timedTasksByDate = computed(() => {
  const byDate = {};
  const seenIds = new Set();
  const visibleProjs = new Set(pinnedProjects.value.map((p) => p.id));
  for (const p of projects.value) {
    if (p.status === "archived") continue;
    if (taskFilterMode.value === "overdue" || isProjectSubtasksVisible(p.id)) {
      visibleProjs.add(p.id);
    }
  }

  const pushTimed = (task, proj) => {
    if (!task || !isTimedTask(task)) return;
    if (task.id != null) {
      if (seenIds.has(task.id)) return;
      seenIds.add(task.id);
    }
    if (
      filterSubtasksByStatus([task], taskFilterMode.value, todayIso.value)
        .length === 0
    ) {
      return;
    }
    const dateIso = task.start_date || task.due_date;
    if (!dateIso) return;
    if (!byDate[dateIso]) byDate[dateIso] = [];
    byDate[dateIso].push({
      ...task,
      project_id: proj ? proj.id : null,
      projectName: proj ? proj.name : "Inbox",
      displayColor: task.color || proj?.color || (proj ? "#2c666e" : "#e11d48"),
      isOverdue: (!proj || !isProjectOverdueExempt(proj)) && isTaskOverdue(task, todayIso.value),
      isStandalone: !proj,
    });
  };

  for (const proj of projects.value) {
    if (proj.status === "archived" || !visibleProjs.has(proj.id)) continue;
    const projDone = isProjectCompleted(proj);
    if (
      (taskFilterMode.value === "active" && projDone) ||
      (taskFilterMode.value === "overdue" && isProjectOverdueExempt(proj))
    ) {
      continue;
    }
    for (const t of projectTasksMap.value[proj.id] || []) {
      pushTimed(t, proj);
    }
  }

  for (const t of standaloneTasks.value) {
    pushTimed(t, null);
  }

  return byDate;
});

// Editorial formatted date for the currently selected journal date
const formattedJournalHeading = computed(() =>
  formatEditorialDate(selectedJournalDate.value)
);

// Chronological list of all saved daily journal entries
const sortedJournalEntries = computed(() => {
  return Object.values(dailyJournalsMap.value)
    .filter((entry) => entry && (entry.content_md || "").trim().length > 0)
    .sort((a, b) => (b.note_date || "").localeCompare(a.note_date || ""))
    .map((entry) => ({
      ...entry,
      editorialDate: formatEditorialDate(entry.note_date),
      snippet: extractJournalSnippet(entry.content_md, 90),
    }));
});

// Tasks active on the selected journal date across all projects + standalone inbox
const tasksOnSelectedJournalDate = computed(() => {
  const iso = selectedJournalDate.value;
  if (!iso) return [];
  const matches = [];
  for (const proj of projects.value) {
    const list = projectTasksMap.value[proj.id] || [];
    for (const t of list) {
      const start = t.start_date || t.due_date;
      const end = t.due_date || t.start_date;
      if (start && end && start <= iso && end >= iso) {
        matches.push({
          ...t,
          projectName: proj.name,
          projectColor: proj.color || "#b85423",
        });
      }
    }
  }
  for (const t of standaloneTasks.value) {
    const start = t.start_date || t.due_date;
    const end = t.due_date || t.start_date;
    if (start && end && start <= iso && end >= iso) {
      matches.push({
        ...t,
        projectName: "Inbox",
        projectColor: t.color || "#e11d48",
      });
    }
  }
  return matches;
});

const renderedMarkdownHtml = computed(() =>
  renderMarkdownPreviewHtml(activeNote.value.content_md)
);

const renderedJournalHtml = computed(() =>
  renderMarkdownPreviewHtml(journalDraftMd.value)
);

function renderMarkdown(md) {
  return renderMarkdownPreviewHtml(md);
}

async function handleJournalPreviewClick(event, isDrawer = false) {
  const target = event?.target;
  if (target?.closest?.("a.md-link")) return;
  const checkbox = target?.closest?.("input.md-task-checkbox[data-md-task-index]");
  if (checkbox) {
    event.stopPropagation();
    const taskIndex = Number(checkbox.dataset.mdTaskIndex);
    const updated = toggleMarkdownCheckboxByIndex(journalDraftMd.value || "", taskIndex);
    if (updated !== journalDraftMd.value) {
      journalDraftMd.value = updated;
      await saveDailyJournalEntry();
    }
    return;
  }
  startEditingJournal(isDrawer);
}

async function handleSubtaskNotePreviewClick(event, sub) {
  const checkbox = event?.target?.closest?.("input.md-task-checkbox[data-md-task-index]");
  if (!checkbox || !sub) return;
  event.stopPropagation();
  const taskIndex = Number(checkbox.dataset.mdTaskIndex);
  const updated = toggleMarkdownCheckboxByIndex(sub.description || "", taskIndex);
  if (updated !== sub.description) {
    sub.description = updated;
    await updateSubtaskFields(selectedProject.value?.id, sub.id, {
      description: sub.description,
    });
  }
}

async function handleProjectNotePreviewClick(event) {
  const checkbox = event?.target?.closest?.("input.md-task-checkbox[data-md-task-index]");
  if (!checkbox) return;
  event.stopPropagation();
  const taskIndex = Number(checkbox.dataset.mdTaskIndex);
  const updated = toggleMarkdownCheckboxByIndex(activeNote.value.content_md || "", taskIndex);
  if (updated !== activeNote.value.content_md) {
    activeNote.value.content_md = updated;
    await saveNote();
  }
}

// Single-field Project Note Editing state (renders MD by default, double click to edit, blur to save & render)
const isEditingProjectNote = ref(false);
const projectNoteTextareaRef = ref(null);

function startEditingProjectNote() {
  isEditingProjectNote.value = true;
  nextTick(() => {
    projectNoteTextareaRef.value?.focus();
  });
}

async function stopEditingProjectNote() {
  isEditingProjectNote.value = false;
  await saveNote();
}

// Subtask notes state (each subtask has its own notes; renders MD by default, double click to edit, blur to save & render)
const editingSubtaskId = ref(null);
const subtaskTextareaRefs = ref({});

function setSubtaskTextareaRef(taskId, el) {
  if (el) {
    subtaskTextareaRefs.value[taskId] = el;
  }
}

function startEditingSubtaskNote(taskId) {
  editingSubtaskId.value = taskId;
  nextTick(() => {
    const el = subtaskTextareaRefs.value[taskId];
    if (el) {
      el.focus();
      el.setSelectionRange?.(el.value.length, el.value.length);
    }
  });
}

async function stopEditingSubtaskNote(sub) {
  if (editingSubtaskId.value === sub.id) {
    editingSubtaskId.value = null;
    await updateSubtaskFields(selectedProject.value?.id, sub.id, {
      description: sub.description || "",
    });
  }
}

// Timeline Drag & Resize state (drag projects to reposition dates, extend handles to shorten/lengthen total days)
const activeTimelineDrag = ref(null);
const wasTimelineDragging = ref(false);

const computedDragDays = computed(() => {
  if (!activeTimelineDrag.value) return 1;
  return calculateDateSpanDays(
    activeTimelineDrag.value.currentStartDate,
    activeTimelineDrag.value.currentTargetDate
  );
});

const dragModeLabel = computed(() => {
  if (!activeTimelineDrag.value) return "";
  const drag = activeTimelineDrag.value;
  if (drag.isTask) {
    if (drag.type === "move") return "Moving Subtask";
    if (drag.type === "resize-start") return "Stretching Subtask Start";
    return "Stretching Subtask Due";
  }
  if (drag.type === "move") return "Repositioning Project";
  if (drag.type === "resize-start") return "Adjusting Project Start";
  return "Adjusting Project Target";
});

function startTimelineDrag(event, projectId, type, scaleMode, taskId = null) {
  if (event.button !== undefined && event.button !== 0) return;

  const isStandalone = Boolean(taskId && (!projectId || projectId === 0));
  const proj = isStandalone
    ? null
    : projects.value.find((p) => p.id === projectId);
  if (!isStandalone && !proj) return;

  const cardEl = event.currentTarget.closest(".week-item-card") || event.currentTarget;
  const container = cardEl.closest(
    ".week-seven-col-area, .week-items-stack-grid, .year-twelve-months-grid, .timegrid-allday-grid"
  );
  const containerRect = container ? container.getBoundingClientRect() : null;

  const numCols =
    scaleMode === "year" ? 12 : scaleMode === "day" ? 1 : 7;
  const colWidth =
    containerRect && containerRect.width > 0
      ? containerRect.width / numCols
      : scaleMode === "year"
      ? 90
      : 120;

  const rowHeight = 72;
  const pStart = proj ? proj.start_date || todayIso.value : todayIso.value;
  const pTarget = proj ? proj.target_date || pStart : todayIso.value;

  if (taskId) {
    const pKey = isStandalone ? 0 : projectId;
    const list = projectTasksMap.value[pKey] || standaloneTasks.value || [];
    const task = list.find((t) => t.id === taskId);
    if (!task) return;
    const tStart = task.start_date || task.due_date || pStart;
    const tDue = task.due_date || task.start_date || tStart;

    activeTimelineDrag.value = {
      isTask: true,
      isStandalone,
      projectId: pKey,
      taskId,
      projectName: proj ? proj.name : "Inbox",
      taskTitle: task.title,
      type, // 'move' | 'resize-start' | 'resize-end'
      scaleMode, // 'month' | 'week' | 'day' | 'year'
      startX: event.clientX,
      startY: event.clientY,
      colWidth,
      rowHeight,
      projectStartIso: isStandalone ? null : pStart,
      projectEndIso: isStandalone ? null : pTarget,
      origTask: { ...task, start_date: tStart, due_date: tDue },
      origStartDate: tStart,
      origTargetDate: tDue,
      currentStartDate: tStart,
      currentTargetDate: tDue,
      deltaDays: 0,
      hasMoved: false,
    };
  } else {
    const origTasks = (projectTasksMap.value[projectId] || []).map((t) => ({ ...t }));
    activeTimelineDrag.value = {
      isTask: false,
      isStandalone: false,
      projectId,
      projectName: proj.name,
      type, // 'move' | 'resize-start' | 'resize-end'
      scaleMode, // 'month' | 'week' | 'day' | 'year'
      startX: event.clientX,
      startY: event.clientY,
      colWidth,
      rowHeight,
      origProject: { ...proj, start_date: pStart, target_date: pTarget },
      origTasks,
      origStartDate: pStart,
      origTargetDate: pTarget,
      currentStartDate: pStart,
      currentTargetDate: pTarget,
      deltaDays: 0,
      hasMoved: false,
    };
  }

  wasTimelineDragging.value = false;

  window.addEventListener("pointermove", handleTimelineDragMove);
  window.addEventListener("pointerup", handleTimelineDragEnd);
  window.addEventListener("pointercancel", handleTimelineDragEnd);
}

function handleTimelineDragMove(event) {
  if (!activeTimelineDrag.value) return;

  const drag = activeTimelineDrag.value;
  const deltaX = event.clientX - drag.startX;
  const deltaY = event.clientY - drag.startY;

  if (Math.abs(deltaX) > 4 || Math.abs(deltaY) > 4) {
    drag.hasMoved = true;
    wasTimelineDragging.value = true;
  }

  if (!drag.hasMoved) return;

  let deltaDays = 0;
  if (drag.scaleMode === "year") {
    const deltaMonths = Math.round(deltaX / drag.colWidth);
    deltaDays = deltaMonths * 30;
  } else if (drag.scaleMode === "week" || drag.scaleMode === "day") {
    const deltaCols = Math.round(deltaX / drag.colWidth);
    deltaDays = deltaCols;
  } else {
    const deltaCols = Math.round(deltaX / drag.colWidth);
    const deltaWeeks = Math.round(deltaY / (drag.rowHeight || 72));
    deltaDays = deltaCols + deltaWeeks * 7;
  }

  drag.deltaDays = deltaDays;

  if (drag.isTask && drag.isStandalone) {
    let s = drag.origStartDate;
    let e = drag.origTargetDate;
    if (drag.type === "move") {
      s = shiftDateIso(s, deltaDays);
      e = shiftDateIso(e, deltaDays);
    } else if (drag.type === "resize-start") {
      s = shiftDateIso(s, deltaDays);
      if (s > e) s = e;
    } else if (drag.type === "resize-end") {
      e = shiftDateIso(e, deltaDays);
      if (e < s) e = s;
    }
    drag.currentStartDate = s;
    drag.currentTargetDate = e;
    const list = projectTasksMap.value[0] || standaloneTasks.value;
    const t = list.find((x) => x.id === drag.taskId);
    if (t) {
      t.start_date = s;
      t.due_date = e;
    }
    standaloneTasks.value = [...(projectTasksMap.value[0] || standaloneTasks.value)];
  } else if (drag.isTask) {
    const res = computeSubtaskDragResult(
      drag.origTask,
      drag.projectStartIso,
      drag.projectEndIso,
      drag.type,
      deltaDays
    );
    drag.currentStartDate = res.start_date;
    drag.currentTargetDate = res.due_date;

    const list = projectTasksMap.value[drag.projectId] || [];
    const t = list.find((x) => x.id === drag.taskId);
    if (t) {
      t.start_date = res.start_date;
      t.due_date = res.due_date;
    }
  } else {
    const res = computeProjectDragResult(
      drag.origProject,
      drag.origTasks,
      drag.type,
      deltaDays
    );
    drag.currentStartDate = res.start_date;
    drag.currentTargetDate = res.target_date;

    const targetProj = projects.value.find((p) => p.id === drag.projectId);
    if (targetProj) {
      targetProj.start_date = res.start_date;
      targetProj.target_date = res.target_date;
    }

    // Live clipping: ensure no subtask happens before or after the main project!
    const list = projectTasksMap.value[drag.projectId] || [];
    for (const ut of res.tasks) {
      const cur = list.find((t) => t.id === ut.id);
      if (cur) {
        cur.start_date = ut.start_date;
        cur.due_date = ut.due_date;
      }
    }
  }
}

function handleTimelineDragEnd() {
  window.removeEventListener("pointermove", handleTimelineDragMove);
  window.removeEventListener("pointerup", handleTimelineDragEnd);
  window.removeEventListener("pointercancel", handleTimelineDragEnd);

  if (!activeTimelineDrag.value) return;

  const drag = activeTimelineDrag.value;
  const moved = drag.hasMoved;
  const isTask = drag.isTask;
  const projId = drag.projectId;
  const taskId = drag.taskId;
  const finalStart = drag.currentStartDate;
  const finalTarget = drag.currentTargetDate;

  activeTimelineDrag.value = null;

  if (moved) {
    setTimeout(() => {
      wasTimelineDragging.value = false;
    }, 120);

    if (isTask) {
      updateSubtaskFields(projId, taskId, {
        start_date: finalStart,
        due_date: finalTarget,
      });
    } else {
      saveProjectDates(projId, finalStart, finalTarget);

      // Persist any subtasks whose clipped dates changed!
      const currentList = projectTasksMap.value[projId] || [];
      for (const origT of drag.origTasks) {
        const cur = currentList.find((t) => t.id === origT.id);
        if (
          cur &&
          (cur.start_date !== origT.start_date || cur.due_date !== origT.due_date)
        ) {
          updateSubtaskFields(projId, cur.id, {
            start_date: cur.start_date,
            due_date: cur.due_date,
          });
        }
      }
    }
  } else {
    wasTimelineDragging.value = false;
  }
}

async function saveProjectDates(projectId, startDate, targetDate) {
  try {
    const res = await fetch(`${API_BASE}/projects/${projectId}`, {
      method: "PUT",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        start_date: startDate,
        target_date: targetDate,
      }),
    });
    if (res.ok) {
      const updated = await res.json();
      const p = projects.value.find((x) => x.id === projectId);
      if (p) {
        p.start_date = updated.start_date;
        p.target_date = updated.target_date;
      }
    }
  } catch (err) {
    console.error("Failed to persist updated project dates:", err);
  }
}

function handleTimelineCardClick(item) {
  if (wasTimelineDragging.value) {
    return;
  }
  if (item.kind === "project") {
    toggleProjectSubtasksVisibility(item.projectId);
  } else {
    openProjectDrawer(item.projectId ?? 0, "subtasks");
  }
}

// ---------------------------------------------------------------------------
// Direct Calendar Quick Task Creation & Month Drag-to-Create
// ---------------------------------------------------------------------------

function openQuickTaskPopover(partialDraft = {}) {
  const defaultDate =
    partialDraft.start_date ||
    partialDraft.due_date ||
    (calendarScaleMode.value === "day" ? selectedDayIso.value : todayIso.value);
  quickTaskDraft.value = {
    title: "",
    project_id: 0,
    start_date: defaultDate,
    due_date: partialDraft.due_date || defaultDate,
    start_time: partialDraft.start_time || "",
    end_time: partialDraft.end_time || "",
    priority: partialDraft.priority || "medium",
    deadline_only: Boolean(partialDraft.deadline_only),
    is_milestone: Boolean(partialDraft.is_milestone),
    ...partialDraft,
  };
  quickTaskModalOpen.value = true;
}

async function handleQuickTaskSubmit(payload) {
  const isInbox = payload.project_id === null || payload.project_id === undefined;
  const pid = isInbox ? 0 : payload.project_id;
  const proj = isInbox ? null : projects.value.find((p) => p.id === pid);
  const fullPayload = {
    project_id: isInbox ? null : pid,
    title: payload.title,
    description: "",
    status: "todo",
    priority: payload.priority || "medium",
    color: proj?.color || (isInbox ? "#e11d48" : "#2c666e"),
    start_date: payload.start_date || todayIso.value,
    due_date: payload.due_date || payload.start_date || todayIso.value,
    start_time: payload.start_time || null,
    end_time: payload.end_time || null,
    deadline_only: Boolean(payload.deadline_only),
    is_milestone: Boolean(payload.is_milestone),
  };

  let createdItem = null;
  try {
    const res = await fetch(`${API_BASE}/tasks`, {
      method: "POST",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(fullPayload),
    });
    if (res.ok) {
      const created = await res.json();
      createdItem = {
        ...created,
        color: created.color || fullPayload.color,
      };
    }
  } catch {
    // Local fallback below
  }

  if (!createdItem) {
    createdItem = {
      id: Date.now(),
      ...fullPayload,
    };
  }

  if (!projectTasksMap.value[pid]) projectTasksMap.value[pid] = [];
  projectTasksMap.value[pid].push(createdItem);
  if (isInbox) {
    standaloneTasks.value = [...projectTasksMap.value[0]];
  } else if (!isProjectSubtasksVisible(pid)) {
    const nextVis = new Set(visibleTimelineSubtaskProjectIds.value);
    nextVis.add(pid);
    visibleTimelineSubtaskProjectIds.value = nextVis;
    persistVisibleSubtaskProjectIds();
  }
  persistLocalProjectsAndTasks();
  quickTaskModalOpen.value = false;
  showNotification({
    type: "success",
    message: `Added "${createdItem.title}"`,
  });
}

function startMonthDayDragCreate(event, week, dayIso) {
  if (event.button !== 0 || activeTimelineDrag.value) return;
  monthDragCreate.value = {
    weekNumber: week.weekNumber,
    anchorIso: dayIso,
    currentIso: dayIso,
    startIso: dayIso,
    endIso: dayIso,
    startX: event.clientX,
    startY: event.clientY,
    hasMoved: false,
  };
  window.addEventListener("pointerup", finishMonthDayDragCreate);
  window.addEventListener("pointercancel", finishMonthDayDragCreate);
}

function updateMonthDayDragCreate(week, dayIso, event = null) {
  const drag = monthDragCreate.value;
  if (!drag || drag.weekNumber !== week.weekNumber) return;
  if (
    dayIso !== drag.anchorIso ||
    (event && Math.abs(event.clientX - drag.startX) > 6)
  ) {
    drag.hasMoved = true;
  }
  drag.currentIso = dayIso;
  drag.startIso = drag.anchorIso <= dayIso ? drag.anchorIso : dayIso;
  drag.endIso = drag.anchorIso <= dayIso ? dayIso : drag.anchorIso;
}

function finishMonthDayDragCreate() {
  window.removeEventListener("pointerup", finishMonthDayDragCreate);
  window.removeEventListener("pointercancel", finishMonthDayDragCreate);

  const drag = monthDragCreate.value;
  monthDragCreate.value = null;
  if (!drag) return;

  openQuickTaskPopover({
    start_date: drag.startIso,
    due_date: drag.endIso,
    start_time: "",
    end_time: "",
  });
}

function isMonthCellDragHighlighted(week, dayIso) {
  const drag = monthDragCreate.value;
  if (!drag || drag.weekNumber !== week.weekNumber) return false;
  return dayIso >= drag.startIso && dayIso <= drag.endIso;
}

async function handleUpdateTimedTask({ projectId, taskId, patch }) {
  await updateSubtaskFields(projectId ?? 0, taskId, patch);
}

// ---------------------------------------------------------------------------
// Command Palette & Global Keyboard Shortcuts
// ---------------------------------------------------------------------------

async function handleCommandPaletteAction(item) {
  if (!item) return;
  if (item.kind === "action") {
    switch (item.action) {
      case "new-task":
        openQuickTaskPopover();
        break;
      case "jump-today":
        activePage.value = "timeline";
        jumpToToday();
        break;
      case "scale-day":
        activePage.value = "timeline";
        switchToDayMode();
        break;
      case "scale-week":
        activePage.value = "timeline";
        switchToWeekMode();
        break;
      case "scale-month":
        activePage.value = "timeline";
        calendarScaleMode.value = "month";
        break;
      case "scale-year":
        activePage.value = "timeline";
        calendarScaleMode.value = "year";
        break;
      case "overdue":
        activePage.value = "timeline";
        await enterOverdueMode(false);
        break;
      case "journal-today":
        navigateToDailyJournal(todayIso.value);
        break;
      case "go-projects":
        activePage.value = "kanban";
        break;
      case "open-archive":
        showArchiveModal.value = true;
        break;
    }
    return;
  }

  if (item.kind === "project") {
    openProjectDrawer(item.projectId, "subtasks");
    return;
  }

  if (item.kind === "task") {
    openProjectDrawer(item.projectId ?? 0, "subtasks");
    return;
  }

  if (item.kind === "note") {
    if (item.projectId) {
      openProjectDrawer(item.projectId, "notes");
    } else {
      navigateToDailyJournal();
    }
  }
}

function handleGlobalKeydown(event) {
  if (!currentUser.value) return;

  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    showCommandPalette.value = !showCommandPalette.value;
    return;
  }

  if (event.key === "Escape") {
    if (showCommandPalette.value) {
      showCommandPalette.value = false;
      return;
    }
    if (quickTaskModalOpen.value) {
      quickTaskModalOpen.value = false;
      return;
    }
    if (showArchiveModal.value) {
      showArchiveModal.value = false;
      return;
    }
    if (showNewProjectModal.value) {
      showNewProjectModal.value = false;
      return;
    }
    if (showDisplayMenu.value) {
      showDisplayMenu.value = false;
      return;
    }
    if (selectedProjectId.value !== null) {
      closeProjectDrawer();
      return;
    }
    if (isJournalDrawerOpen.value) {
      isJournalDrawerOpen.value = false;
      return;
    }
  }

  const tag = event.target?.tagName?.toLowerCase();
  const isTyping =
    tag === "input" ||
    tag === "textarea" ||
    tag === "select" ||
    event.target?.isContentEditable;
  if (
    isTyping ||
    event.ctrlKey ||
    event.metaKey ||
    event.altKey ||
    showCommandPalette.value ||
    quickTaskModalOpen.value ||
    showArchiveModal.value ||
    showNewProjectModal.value
  ) {
    return;
  }

  const key = event.key.toLowerCase();
  if (key === "n") {
    event.preventDefault();
    openQuickTaskPopover();
  } else if (key === "t" && activePage.value === "timeline") {
    event.preventDefault();
    jumpToToday();
  } else if (key === "d" && activePage.value === "timeline") {
    event.preventDefault();
    switchToDayMode();
  } else if (key === "w" && activePage.value === "timeline") {
    event.preventDefault();
    switchToWeekMode();
  } else if (key === "m" && activePage.value === "timeline") {
    event.preventDefault();
    calendarScaleMode.value = "month";
  } else if (key === "y" && activePage.value === "timeline") {
    event.preventDefault();
    calendarScaleMode.value = "year";
  } else if (key === "o" && activePage.value === "timeline") {
    event.preventDefault();
    enterOverdueMode(false);
  }
}

/**
 * Subtle, warm editorial card styling with a crisp left accent border
 * instead of heavy neon all-around borders.
 */
function getCustomColorCardStyle(hexColor, extraGridStyle = {}) {
  const c = hexColor || "#2a5f52";
  return {
    ...extraGridStyle,
    borderColor: `${c}42`,
    borderLeft: `3px solid ${c}`,
    backgroundColor: `${c}14`,
    boxShadow: "inset 0 1px 0 rgba(255, 250, 240, 0.65)",
  };
}

function getAuthHeaders(extra = {}) {
  const headers = { ...extra };
  if (authToken.value) {
    headers.Authorization = `Bearer ${authToken.value}`;
  }
  if (journalSessionToken.value) {
    headers["X-Journal-Token"] = journalSessionToken.value;
  }
  return headers;
}

async function checkJournalLockStatus() {
  try {
    const res = await fetch(`${API_BASE}/journal/lock-status`, {
      headers: getAuthHeaders(),
    });
    if (res.ok) {
      const data = await res.json();
      hasJournalPassword.value = Boolean(data.has_password);
      isJournalUnlocked.value = Boolean(data.is_unlocked);
      try {
        localStorage.setItem(
          "chrononote_has_journal_password",
          String(hasJournalPassword.value)
        );
      } catch {
        // ignore
      }
      return data;
    }
  } catch {
    // Offline mode: check local flags
  }
  return {
    has_password: hasJournalPassword.value,
    is_unlocked: isJournalUnlocked.value,
  };
}

function lockJournalSession() {
  journalSessionToken.value = "";
  isJournalUnlocked.value = false;
  try {
    sessionStorage.removeItem("chrononote_journal_session_token");
  } catch {
    // ignore
  }
  if (activePage.value === "journal") {
    activePage.value = "timeline";
  }
  isJournalDrawerOpen.value = false;
}

async function unlockJournalSession() {
  journalUnlockError.value = "";
  const pw = journalPasswordInput.value.trim();
  if (!pw) {
    journalUnlockError.value = "Please enter your password.";
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/journal/unlock`, {
      method: "POST",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ password: pw }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Incorrect password");
    }
    const data = await res.json();
    journalSessionToken.value = data.journal_token;
    isJournalUnlocked.value = true;
    try {
      sessionStorage.setItem(
        "chrononote_journal_session_token",
        data.journal_token
      );
    } catch {
      // ignore
    }
    showJournalUnlockModal.value = false;
    journalPasswordInput.value = "";

    // Refresh journals from backend now that we're unlocked
    await fetchProjectsAndTimeline();

    // Resume any pending action
    if (pendingJournalDate.value) {
      const targetDate = pendingJournalDate.value;
      const targetDrawer = pendingJournalDrawer.value;
      pendingJournalDate.value = null;
      await openDailyJournalForDate(targetDate, targetDrawer);
    }
  } catch (err) {
    journalUnlockError.value = err.message || "Failed to unlock journal.";
  }
}

async function saveJournalPassword() {
  journalSettingsError.value = "";
  journalSettingsSuccess.value = "";
  const newPw = journalSettingsNewPw.value.trim();
  const confirmPw = journalSettingsConfirmPw.value.trim();
  const currPw = journalSettingsCurrentPw.value.trim();

  if (!newPw) {
    journalSettingsError.value = "New password cannot be empty.";
    return;
  }
  if (newPw !== confirmPw) {
    journalSettingsError.value = "Passwords do not match.";
    return;
  }
  if (hasJournalPassword.value && !currPw) {
    journalSettingsError.value = "Please provide your current password.";
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/journal/password`, {
      method: "POST",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        password: newPw,
        current_password: currPw || null,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update password");
    }
    const data = await res.json();
    journalSessionToken.value = data.journal_token;
    hasJournalPassword.value = true;
    isJournalUnlocked.value = true;
    try {
      sessionStorage.setItem(
        "chrononote_journal_session_token",
        data.journal_token
      );
      localStorage.setItem("chrononote_has_journal_password", "true");
    } catch {
      // ignore
    }
    journalSettingsSuccess.value = "Password successfully saved for this journal!";
    journalSettingsNewPw.value = "";
    journalSettingsConfirmPw.value = "";
    journalSettingsCurrentPw.value = "";
    setTimeout(() => {
      showJournalSettingsModal.value = false;
      journalSettingsSuccess.value = "";
    }, 1500);
  } catch (err) {
    journalSettingsError.value = err.message || "Failed to save password.";
  }
}

function requestJournalAccess(targetDate = null, openDrawer = false) {
  if (hasJournalPassword.value && !isJournalUnlocked.value) {
    pendingJournalDate.value = targetDate || selectedJournalDate.value;
    pendingJournalDrawer.value = openDrawer;
    journalPasswordInput.value = "";
    journalUnlockError.value = "";
    showJournalUnlockModal.value = true;
    return false;
  }
  return true;
}

async function openProjectDrawer(projId, tab = "subtasks") {
  isJournalDrawerOpen.value = false;
  selectedProjectId.value = projId;
  drawerTab.value = tab;
  isEditingProjectNote.value = false;
  editingSubtaskId.value = null;
  const proj = projects.value.find((p) => p.id === projId);
  if (proj) {
    activeNote.value = {
      id: null,
      project_id: proj.id,
      title: `${proj.name} — Notes`,
      content_md: "",
    };

    try {
      const res = await fetch(`${API_BASE}/notes?project_id=${projId}`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const notes = await res.json();
        const projectNote =
          notes.find((n) => !n.is_daily_note && n.project_id === projId) || notes[0];
        if (projectNote && selectedProjectId.value === projId) {
          activeNote.value = {
            id: projectNote.id,
            project_id: proj.id,
            title: projectNote.title || `${proj.name} — Notes`,
            content_md: projectNote.content_md || "",
          };
        }
      }
    } catch {
      // Local fallback uses empty note
    }
  }
}

function closeProjectDrawer() {
  selectedProjectId.value = null;
}

/**
 * Open a specific date's Daily Journal (triggered by clicking any date cell in Month View
 * or selecting a date in the Journal tab).
 */
async function openDailyJournalForDate(isoDate, openDrawer = true) {
  if (!isoDate) return;
  if (!requestJournalAccess(isoDate, openDrawer)) {
    return;
  }
  selectedJournalDate.value = isoDate;
  selectedProjectId.value = null;
  ocrTarget.value = "journal";
  isEditingJournal.value = false;
  resetOcrState();
  if (openDrawer) {
    isJournalDrawerOpen.value = true;
  }

  // Load from local map first for instant feel
  const existingLocal = dailyJournalsMap.value[isoDate];
  if (existingLocal) {
    journalDraftTitle.value = existingLocal.title || `Journal — ${isoDate}`;
    journalDraftMd.value = existingLocal.content_md || "";
  } else {
    journalDraftTitle.value = `Journal — ${isoDate}`;
    journalDraftMd.value = "";
  }

  // Check backend for saved daily journal
  try {
    const res = await fetch(`${API_BASE}/journal/${isoDate}`, {
      headers: getAuthHeaders(),
    });
    if (res.ok) {
      const remoteNote = await res.json();
      dailyJournalsMap.value = {
        ...dailyJournalsMap.value,
        [isoDate]: remoteNote,
      };
      journalDraftTitle.value = remoteNote.title || `Journal — ${isoDate}`;
      journalDraftMd.value = remoteNote.content_md || "";
    }
  } catch {
    // Offline fallback uses dailyJournalsMap
  }
}

function closeJournalDrawer() {
  isJournalDrawerOpen.value = false;
}

function stepJournalDate(deltaDays) {
  const parts = selectedJournalDate.value.split("-").map(Number);
  if (parts.length !== 3) return;
  const utc = Date.UTC(parts[0], parts[1] - 1, parts[2]) + deltaDays * 86_400_000;
  const nextIso = new Date(utc).toISOString().slice(0, 10);
  openDailyJournalForDate(nextIso, isJournalDrawerOpen.value);
}

async function saveDailyJournalEntry() {
  const iso = selectedJournalDate.value;
  if (!iso) return;
  journalSaveStatus.value = "saving";

  const entryObj = {
    id: dailyJournalsMap.value[iso]?.id || Date.now(),
    title: journalDraftTitle.value.trim() || `Journal — ${iso}`,
    note_date: iso,
    is_daily_note: true,
    content_md: journalDraftMd.value,
    updated_at: new Date().toISOString(),
  };

  // Update reactive map immediately so Month View shows the journal indicator right away
  dailyJournalsMap.value = {
    ...dailyJournalsMap.value,
    [iso]: entryObj,
  };
  persistLocalJournals();

  try {
    const res = await fetch(`${API_BASE}/journal/${iso}`, {
      method: "PUT",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        title: entryObj.title,
        content_md: entryObj.content_md,
        sync_inline_tasks: true,
      }),
    });
    if (res.ok) {
      const saved = await res.json();
      dailyJournalsMap.value = {
        ...dailyJournalsMap.value,
        [iso]: saved,
      };
      persistLocalJournals();
      await fetchProjectsAndTimeline();
      await fetchHabitsAndAnalytics();
    }
  } catch {
    // Offline fallback already saved in dailyJournalsMap & localStorage
  }

  journalSaveStatus.value = "saved";
  setTimeout(() => {
    if (journalSaveStatus.value === "saved") {
      journalSaveStatus.value = "";
    }
  }, 2200);
}

/**
 * Fetch habits list and 52-week heatmap analytics from backend
 */
async function fetchHabitsAndAnalytics() {
  try {
    const [hRes, aRes] = await Promise.all([
      fetch(`${API_BASE}/habits`, { headers: getAuthHeaders() }),
      fetch(`${API_BASE}/analytics/habits`, { headers: getAuthHeaders() }),
    ]);
    if (hRes.ok) {
      habitsList.value = await hRes.json();
    }
    if (aRes.ok) {
      habitAnalytics.value = await aRes.json();
    }
  } catch {
    // Offline fallback: keep existing or empty
  }
}

/**
 * Fetch available journal templates
 */
async function fetchTemplates() {
  try {
    const res = await fetch(`${API_BASE}/templates`, { headers: getAuthHeaders() });
    if (res.ok) {
      availableTemplates.value = await res.json();
    }
  } catch {
    // Fallback if offline
  }
}

/**
 * Toggle habit completion state for a given date
 */
async function handleToggleHabit(habitId, dateIso) {
  const targetDate = dateIso || selectedJournalDate.value;
  try {
    const res = await fetch(`${API_BASE}/habits/${habitId}/toggle`, {
      method: "POST",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ log_date: targetDate }),
    });
    if (res.ok) {
      const habitObj = habitsList.value.find((h) => h.id === habitId);
      if (habitObj && targetDate === selectedJournalDate.value && journalDraftMd.value) {
        journalDraftMd.value = toggleHabitInMarkdown(journalDraftMd.value, habitObj.slug);
      }
      await fetchHabitsAndAnalytics();
    }
  } catch {
    // Local offline toggle
  }
}

/**
 * Create a new custom habit via modal
 */
async function handleCreateHabit(payload) {
  try {
    const res = await fetch(`${API_BASE}/habits`, {
      method: "POST",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      await fetchHabitsAndAnalytics();
    }
  } catch {
    // Local fallback
  }
}

/**
 * Update an existing habit
 */
async function handleUpdateHabit(habitId, payload) {
  try {
    const res = await fetch(`${API_BASE}/habits/${habitId}`, {
      method: "PATCH",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      await fetchHabitsAndAnalytics();
    }
  } catch (err) {
    console.error("Failed to update habit:", err);
  }
}

/**
 * Delete a habit
 */
async function handleDeleteHabit(habitId) {
  try {
    const res = await fetch(`${API_BASE}/habits/${habitId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    if (res.ok) {
      await fetchHabitsAndAnalytics();
    }
  } catch (err) {
    console.error("Failed to delete habit:", err);
  }
}

/**
 * Apply journal template (habits checklist + prompts) to current journal entry
 */
async function applyJournalTemplate(templateId = null) {
  showTemplateMenu.value = false;
  const iso = selectedJournalDate.value;
  try {
    const query = templateId ? `?template_id=${templateId}&target_date=${iso}` : `?target_date=${iso}`;
    const res = await fetch(`${API_BASE}/journal/template${query}`, {
      headers: getAuthHeaders(),
    });
    if (res.ok) {
      const data = await res.json();
      journalDraftMd.value = data.content_md;
      await saveDailyJournalEntry();
      await fetchHabitsAndAnalytics();
      return;
    }
  } catch {
    // Fallback using local template variables
  }

  // Local fallback template scaffolding
  const defaultTpl =
    availableTemplates.value.find((t) => t.id === templateId)?.content_md ||
    `---
date: {{date}}
day: {{day_of_week}}
tags: [journal, daily]
---

### Daily Habits
{{habits_checklist}}

### Notes & Observations
- 

### Evening Reflection
- Highlight of the day: 
- One lesson or realization: 
- Focus for tomorrow: 
`;

  journalDraftMd.value = applyTemplateVariables(defaultTpl, iso, habitsList.value);
  await saveDailyJournalEntry();
}

/**
 * Open the Template Customization Modal
 */
function openTemplateManager(templateToEdit = null) {
  templateManagerStatus.value = "";
  templateManagerError.value = "";
  if (templateToEdit) {
    editingTemplateId.value = templateToEdit.id;
    templateForm.value = {
      name: templateToEdit.name || "",
      description: templateToEdit.description || "",
      content_md: templateToEdit.content_md || "",
      is_default: Boolean(templateToEdit.is_default),
    };
  } else {
    initNewTemplateForm();
  }
  showTemplateManagerModal.value = true;
}

function initNewTemplateForm() {
  editingTemplateId.value = null;
  templateManagerStatus.value = "";
  templateManagerError.value = "";
  templateForm.value = {
    name: "",
    description: "",
    content_md: `---
date: {{date}}
day: {{day_of_week}}
tags: [journal]
---

### Daily Habits
{{habits_checklist}}

### Notes & Thoughts
- 

### Evening Reflection
- Highlight of the day: 
- One lesson or realization: 
- Focus for tomorrow: 
`,
    is_default: false,
  };
}

function selectTemplateToEdit(tpl) {
  openTemplateManager(tpl);
}

async function saveTemplateForm() {
  templateManagerError.value = "";
  templateManagerStatus.value = "";
  if (!templateForm.value.name.trim()) {
    templateManagerError.value = "Template name is required";
    return;
  }
  if (!templateForm.value.content_md.trim()) {
    templateManagerError.value = "Template content cannot be empty";
    return;
  }

  const payload = {
    name: templateForm.value.name.trim(),
    description: templateForm.value.description.trim(),
    content_md: templateForm.value.content_md,
    is_default: templateForm.value.is_default,
  };

  try {
    let res;
    if (editingTemplateId.value) {
      res = await fetch(`${API_BASE}/templates/${editingTemplateId.value}`, {
        method: "PUT",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      });
    } else {
      res = await fetch(`${API_BASE}/templates`, {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      });
    }

    if (res.ok) {
      const saved = await res.json();
      templateManagerStatus.value = "Template saved successfully!";
      await fetchTemplates();
      editingTemplateId.value = saved.id;
    } else {
      const err = await res.json().catch(() => ({}));
      templateManagerError.value = err.detail || "Failed to save template";
    }
  } catch {
    templateManagerError.value = "Network error saving template";
  }
}

async function deleteTemplate(templateId) {
  if (!confirm("Are you sure you want to delete this template?")) return;
  try {
    const res = await fetch(`${API_BASE}/templates/${templateId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    if (res.ok) {
      await fetchTemplates();
      initNewTemplateForm();
      templateManagerStatus.value = "Template deleted.";
    } else {
      const err = await res.json().catch(() => ({}));
      templateManagerError.value = err.detail || "Failed to delete template";
    }
  } catch {
    templateManagerError.value = "Network error deleting template";
  }
}

/**
 * Navigate to a date's journal directly from the heatmap
 */
function jumpToJournalFromHeatmap(dateIso) {
  selectedJournalDate.value = dateIso;
  activePage.value = "journal";
  openDailyJournalForDate(dateIso, false);
}

// ---------------------------------------------------------------------------
// Study Mode State & Handlers
// ---------------------------------------------------------------------------
const workspaceNotes = ref([]);

const allTasksList = computed(() => {
  const result = [];
  for (const list of Object.values(projectTasksMap.value || {})) {
    if (Array.isArray(list)) {
      result.push(...list);
    }
  }
  return result;
});

async function fetchWorkspaceNotes() {
  try {
    const res = await fetch(`${API_BASE}/notes`, {
      headers: getAuthHeaders(),
    });
    if (res.ok) {
      workspaceNotes.value = await res.json();
    }
  } catch {
    // offline/fallback
  }
}

async function handleStudySessionCompleted(session) {
  if (session && session.auto_log_to_journal) {
    const sessionDate = session.session_date || getSystemTodayIso();
    await openDailyJournalForDate(sessionDate, false);

    // Refresh remote daily journals list
    try {
      const journalRes = await fetch(`${API_BASE}/journal`, {
        headers: getAuthHeaders(),
      });
      if (journalRes.ok) {
        const entries = await journalRes.json();
        const nextMap = { ...dailyJournalsMap.value };
        for (const entry of entries) {
          if (entry.note_date) {
            nextMap[entry.note_date] = entry;
          }
        }
        dailyJournalsMap.value = nextMap;
        persistLocalJournals();
      }
    } catch {}

    // Offline / local fallback guarantee
    const entry = dailyJournalsMap.value[sessionDate] || {
      id: Date.now(),
      title: `Journal — ${sessionDate}`,
      note_date: sessionDate,
      content_md: `# Journal — ${sessionDate}\n\n`,
      is_daily_note: true,
    };
    const projLabel = session.project_name ? `[[${session.project_name}]]` : "General Study";
    const bullet = `- [x] Focus (${session.duration_minutes}m) on ${projLabel}: ${session.intention || 'Focused interval'}`;
    if (!entry.content_md.includes(bullet)) {
      const formattedNotes = session.notes
        ? "\n" + session.notes.split("\n").map((l) => (l.trim() ? `  > ${l}` : "  >")).join("\n")
        : "";
      entry.content_md = entry.content_md.trimEnd() + `\n${bullet}${formattedNotes}\n`;
      dailyJournalsMap.value = {
        ...dailyJournalsMap.value,
        [sessionDate]: entry,
      };
      if (selectedJournalDate.value === sessionDate) {
        journalDraftMd.value = entry.content_md;
      }
      persistLocalJournals();
    }
  }
  await fetchWorkspaceNotes();
  await fetchHabitsAndAnalytics();
}

function handleStudyNoteUpdated(updatedNote) {
  if (!updatedNote) return;
  const idx = workspaceNotes.value.findIndex((n) => n.id === updatedNote.id);
  if (idx !== -1) {
    workspaceNotes.value[idx] = updatedNote;
  } else {
    workspaceNotes.value.push(updatedNote);
  }
}

// ---------------------------------------------------------------------------
// Sticker System State & Handlers
// ---------------------------------------------------------------------------
const stickersList = ref([]);
const stickerPlacements = ref([]);
const isStickerDrawerOpen = ref(false);
const isUserDropdownOpen = ref(false);
const showAccountSettingsModal = ref(false);
const userDropdownRef = ref(null);

function handleDocumentClick(e) {
  if (userDropdownRef.value && !userDropdownRef.value.contains(e.target)) {
    isUserDropdownOpen.value = false;
  }
  if (displayMenuRef.value && !displayMenuRef.value.contains(e.target)) {
    showDisplayMenu.value = false;
  }
}

function handleUserUpdated(sessionData) {
  if (sessionData && sessionData.user) {
    currentUser.value = sessionData.user;
    if (sessionData.token) {
      sessionToken.value = sessionData.token;
      localStorage.setItem("chrononote_session_token", sessionData.token);
    }
    showNotification({
      type: "success",
      message: "Account settings updated successfully",
    });
  }
}
const activeStickerTarget = ref({ type: "calendar_date", key: "2026-11-01" });

async function fetchStickers() {
  try {
    const res = await fetch(`${API_BASE}/stickers`, { headers: getAuthHeaders() });
    if (res.ok) {
      stickersList.value = await res.json();
    }
  } catch {
    // offline
  }
}

async function fetchStickerPlacements() {
  try {
    const res = await fetch(`${API_BASE}/stickers/placements`, { headers: getAuthHeaders() });
    if (res.ok) {
      stickerPlacements.value = await res.json();
    }
  } catch {
    // offline
  }
}

async function handleUploadSticker(payload) {
  try {
    const res = await fetch(`${API_BASE}/stickers`, {
      method: "POST",
      headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      const created = await res.json();
      stickersList.value.push(created);
      showNotification({ type: "success", message: `Uploaded sticker "${created.name}"` });
    }
  } catch (err) {
    console.error("Failed to upload sticker:", err);
  }
}

async function handleDeleteSticker(stickerId) {
  try {
    const res = await fetch(`${API_BASE}/stickers/${stickerId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    if (res.ok) {
      stickersList.value = stickersList.value.filter((s) => s.id !== stickerId);
      showNotification({ type: "success", message: "Sticker deleted" });
    }
  } catch (err) {
    console.error("Failed to delete sticker:", err);
  }
}

async function handleStampSticker(sticker) {
  const target = activeStickerTarget.value || { type: "calendar_date", key: selectedJournalDate.value };
  const randomRot = Math.floor(Math.random() * 25) - 12; // -12 to +12 deg
  const payload = {
    sticker_id: sticker.id,
    sticker_name: sticker.name,
    image_url: sticker.image_url,
    target_type: target.type,
    target_key: String(target.key),
    pos_x: 50,
    pos_y: 50,
    rotation_deg: randomRot,
    scale: 100,
  };

  try {
    const res = await fetch(`${API_BASE}/stickers/placements`, {
      method: "POST",
      headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      const created = await res.json();
      stickerPlacements.value.push(created);
      showNotification({
        type: "success",
        message: `Stamped ${sticker.name} onto ${target.type === "journal" ? "this journal" : target.type === "calendar_date" ? target.key : "this note"}!`,
      });
    }
  } catch (err) {
    console.error("Failed to place sticker:", err);
  }
}

async function handleRemovePlacement(placementId) {
  try {
    const res = await fetch(`${API_BASE}/stickers/placements/${placementId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    if (res.ok) {
      stickerPlacements.value = stickerPlacements.value.filter((p) => p.id !== placementId);
      showNotification({ type: "success", message: "Removed sticker" });
    }
  } catch (err) {
    console.error("Failed to remove placement:", err);
  }
}

function getStickersForDate(isoDate) {
  return filterStickersByTarget(stickerPlacements.value, "calendar_date", isoDate);
}

function getStickersForNote(noteKey) {
  return filterStickersByTarget(stickerPlacements.value, "note", noteKey);
}

const journalStickers = computed(() => {
  const dateKey = String(selectedJournalDate.value);
  const noteKey = activeNote.value?.id;
  return stickerPlacements.value.filter(
    (placement) =>
      (placement.target_type === "journal" && String(placement.target_key) === dateKey) ||
      (placement.target_type === "calendar_date" && String(placement.target_key) === dateKey) ||
      (noteKey && placement.target_type === "note" && String(placement.target_key) === String(noteKey))
  );
});

async function handleUpdateStickerPlacement(payload) {
  const { id, pos_x, pos_y, rotation_deg, scale } = payload;
  const existing = stickerPlacements.value.find((p) => p.id === id);
  if (existing) {
    if (pos_x !== undefined) existing.pos_x = pos_x;
    if (pos_y !== undefined) existing.pos_y = pos_y;
    if (rotation_deg !== undefined) existing.rotation_deg = rotation_deg;
    if (scale !== undefined) existing.scale = scale;
  }
  try {
    await fetch(`${API_BASE}/stickers/placements/${id}`, {
      method: "PATCH",
      headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ pos_x, pos_y, rotation_deg, scale }),
    });
  } catch (err) {
    console.error("Failed to update sticker placement:", err);
  }
}

// ---------------------------------------------------------------------------
// Docs-Style Journal Image Handlers (Inline vs Above Text Draggable)
// ---------------------------------------------------------------------------
const journalFloatingImages = computed(() => {
  return parseDocsImageDirectives(journalDraftMd.value).floatingImages;
});

async function handleUploadJournalImage(file, mode = "draggable") {
  if (!file) return;
  try {
    const dataUrl = await readFileAsDataUrl(file);
    const cleanName = file.name.replace(/\.[^/.]+$/, "").slice(0, 40) || "Image";

    const res = await fetch(`${API_BASE}/uploads/images`, {
      method: "POST",
      headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: file.name,
        image_data: dataUrl,
        mode,
      }),
    });

    if (res.ok) {
      const result = await res.json();
      const markdownTag = formatDocsImageMarkdown(
        cleanName,
        result.url,
        mode,
        result.pos_x || 50,
        result.pos_y || 20,
        result.width || 320
      );
      journalDraftMd.value = (journalDraftMd.value || "").trimEnd() + `\n\n${markdownTag}\n`;
      showNotification({
        type: "success",
        message: `Added image as ${mode === 'draggable' ? 'draggable card' : 'inline flow'}!`,
      });
    }
  } catch (err) {
    console.error("Failed to upload image:", err);
  }
}

function handleUpdateFloatingImage({ id, x, y, width, rotation }) {
  const currentImages = journalFloatingImages.value;
  const target = currentImages.find((img) => img.id === id);
  if (!target) return;

  const newTag = formatDocsImageMarkdown(target.caption, target.url, target.mode, x, y, width, rotation);
  journalDraftMd.value = journalDraftMd.value.replace(target.rawDirective, newTag);
}

function handleChangeFloatingImageMode({ id, mode }) {
  const currentImages = journalFloatingImages.value;
  const target = currentImages.find((img) => img.id === id);
  if (!target) return;

  const newTag = formatDocsImageMarkdown(target.caption, target.url, mode, target.x, target.y, target.width, target.rotation);
  journalDraftMd.value = journalDraftMd.value.replace(target.rawDirective, newTag);
}

function handleDeleteFloatingImage(target) {
  if (!target || !target.rawDirective) return;
  journalDraftMd.value = journalDraftMd.value.replace(target.rawDirective, "").trim();
  showNotification({ type: "success", message: "Image removed from journal" });
}

// ---------------------------------------------------------------------------
// Visual Customization & Themes State
// ---------------------------------------------------------------------------
const customThemePrefs = ref(loadCustomTheme());
const showThemeSettingsModal = ref(false);

function updateThemeSetting(key, val) {
  customThemePrefs.value[key] = val;
  saveCustomTheme(customThemePrefs.value);
}

/**
 * Helper to determine if a habit slug is marked completed on a specific date
 */
function isHabitCompletedOnDate(slug, dateIso) {
  if (dateIso === selectedJournalDate.value && journalDraftMd.value) {
    const pills = extractHabitPills(journalDraftMd.value);
    const found = pills.find((p) => p.slug === slug);
    if (found) return found.completed;
  }
  const dayRec = (habitAnalytics.value?.days || []).find((d) => d.date === dateIso);
  return Boolean(dayRec?.habits && dayRec.habits[slug]);
}

function getJournalStorageKey() {
  const email = currentUser.value?.email?.trim().toLowerCase();
  return email
    ? `chrononote_daily_journals_user_${email}`
    : "chrononote_daily_journals_v2";
}

function getProjectStorageKey() {
  const email = currentUser.value?.email?.trim().toLowerCase();
  return email
    ? `chrononote_projects_user_${email}`
    : "chrononote_projects_v2";
}

function getTaskStorageKey() {
  const email = currentUser.value?.email?.trim().toLowerCase();
  return email
    ? `chrononote_tasks_user_${email}`
    : "chrononote_tasks_v2";
}

function persistLocalProjectsAndTasks() {
  try {
    localStorage.setItem(
      getProjectStorageKey(),
      JSON.stringify([...projects.value, ...archivedProjects.value])
    );
    localStorage.setItem(
      getTaskStorageKey(),
      JSON.stringify(projectTasksMap.value)
    );
  } catch {
    // Ignore storage quota errors
  }
}

function loadLocalProjectsAndTasks() {
  try {
    const rawP = localStorage.getItem(getProjectStorageKey());
    const rawT = localStorage.getItem(getTaskStorageKey());
    const email = currentUser.value?.email?.trim().toLowerCase();

    if (rawP) {
      const parsedProjs = JSON.parse(rawP);
      projects.value = parsedProjs.filter((p) => p && p.status !== "archived");
      archivedProjects.value = parsedProjs.filter((p) => p && p.status === "archived");
    } else if (!currentUser.value || email === "bryce@example.com") {
      projects.value = [...DEFAULT_PROJECTS];
      archivedProjects.value = [];
    } else {
      // Clean isolated starter project for this specific newly registered user
      projects.value = [
        {
          id: Date.now(),
          name: "Personal Workspace",
          slug: "personal-workspace",
          description: `${currentUser.value.name || currentUser.value.email}'s synced workspace`,
          area: "",
          color: "#c2410c",
          status: "active",
          is_pinned: true,
          sidebar_order: 0,
          start_date: "2026-11-01",
          target_date: "2026-11-30",
        },
      ];
      archivedProjects.value = [];
    }

    if (rawT) {
      const parsed = JSON.parse(rawT);
      if (parsed[0]) {
        // Strip mock tasks with IDs 9001 and 9002 if present from previous sessions
        parsed[0] = parsed[0].filter((t) => t.id !== 9001 && t.id !== 9002);
      }
      projectTasksMap.value = parsed;
      standaloneTasks.value = parsed[0] || [];
    } else {
      projectTasksMap.value = {};
      standaloneTasks.value = [];
    }
  } catch {
    projects.value = [];
    archivedProjects.value = [];
    projectTasksMap.value = {};
  }
}

function clearWorkspaceData() {
  projects.value = [];
  archivedProjects.value = [];
  projectTasksMap.value = {};
  standaloneTasks.value = [];
  dailyJournalsMap.value = {};
  selectedProjectId.value = null;
  isJournalUnlocked.value = false;
  journalSessionToken.value = "";
}

function persistLocalJournals() {
  if (hasJournalPassword.value && !isJournalUnlocked.value) {
    return;
  }
  try {
    localStorage.setItem(
      getJournalStorageKey(),
      JSON.stringify(dailyJournalsMap.value)
    );
  } catch {
    // Ignore storage quota errors
  }
}

function loadLocalJournals() {
  try {
    const savedKey = localStorage.getItem("chrononote_gemini_ocr_key");
    if (savedKey) {
      geminiApiKeyInput.value = savedKey;
    }
    // If journal has password and is currently locked in this browser session, do not populate plaintext journals
    if (hasJournalPassword.value && !isJournalUnlocked.value) {
      dailyJournalsMap.value = {};
      return;
    }
    const raw = localStorage.getItem(getJournalStorageKey());
    if (raw) {
      const parsed = JSON.parse(raw);
      dailyJournalsMap.value = currentUser.value
        ? { ...parsed }
        : { ...DEFAULT_DAILY_JOURNALS, ...parsed };
    } else {
      dailyJournalsMap.value = currentUser.value
        ? {}
        : { ...DEFAULT_DAILY_JOURNALS };
    }
  } catch {
    // Ignore parse errors
  }
}

function saveGeminiOcrKey() {
  try {
    localStorage.setItem(
      "chrononote_gemini_ocr_key",
      geminiApiKeyInput.value.trim()
    );
  } catch {
    // ignore
  }
}

// ---------------------------------------------------------------------------
// Handwritten Journal OCR Scanner
// ---------------------------------------------------------------------------

function resetOcrState() {
  ocrStatusText.value = "";
  ocrProgress.value = 0;
  isOcrRunning.value = false;
  ocrExtractedText.value = "";
  ocrError.value = "";
  if (ocrPreviewUrl.value) {
    try {
      URL.revokeObjectURL(ocrPreviewUrl.value);
    } catch {
      // ignore
    }
    ocrPreviewUrl.value = "";
  }
}

async function handleOcrFileChange(event, targetMode = "journal") {
  const file = event.target?.files?.[0];
  if (!file) return;
  ocrTarget.value = targetMode;
  ocrError.value = "";
  ocrExtractedText.value = "";
  isOcrRunning.value = true;
  ocrProgress.value = 5;
  ocrStatusText.value = "Loading handwritten page…";
  saveGeminiOcrKey();

  if (ocrPreviewUrl.value) {
    try {
      URL.revokeObjectURL(ocrPreviewUrl.value);
    } catch {
      // ignore
    }
  }
  ocrPreviewUrl.value = URL.createObjectURL(file);

  try {
    const { text } = await runBrowserHandwritingOcr(file, {
      enhanceContrast: ocrEnhanceContrast.value,
      apiBase: API_BASE,
      geminiApiKey: geminiApiKeyInput.value.trim(),
      useServerOcr:
        hasServerOcrKey.value || Boolean(geminiApiKeyInput.value.trim()),
      onProgress: ({ status, progress }) => {
        ocrStatusText.value = status;
        ocrProgress.value = progress;
      },
    });

    if (!text) {
      ocrError.value =
        "No legible handwriting or text was detected. Try taking a clearer photo in even lighting.";
    } else {
      ocrExtractedText.value = text;
    }
  } catch (err) {
    ocrError.value =
      err?.message || "OCR scan could not complete. Please try another photo.";
  } finally {
    isOcrRunning.value = false;
    if (event.target) {
      event.target.value = "";
    }
  }
}

function insertOcrTextIntoNote() {
  if (!ocrExtractedText.value.trim()) return;
  if (ocrTarget.value === "journal") {
    journalDraftMd.value = appendOcrToMarkdown(
      journalDraftMd.value,
      ocrExtractedText.value,
      {
        includeHeader: includeOcrHeading.value,
        sourceLabel: "Handwritten Journal Scan",
      }
    );
    saveDailyJournalEntry();
  }
  resetOcrState();
}

// ---------------------------------------------------------------------------
// Google Account Sign-In System
// ---------------------------------------------------------------------------

function loadSavedAuthSession() {
  try {
    const savedToken = localStorage.getItem("chrononote_session_token");
    const savedUser = localStorage.getItem("chrononote_session_user");
    const savedLast = localStorage.getItem("chrononote_last_user");
    if (savedLast) {
      lastUser.value = JSON.parse(savedLast);
    } else if (savedUser) {
      lastUser.value = JSON.parse(savedUser);
    }
    if (savedToken && savedUser) {
      authToken.value = savedToken;
      currentUser.value = JSON.parse(savedUser);
    }
  } catch {
    // ignore
  }
}

function saveAuthSession(token, user) {
  authToken.value = token;
  currentUser.value = user;
  if (user) {
    lastUser.value = {
      id: user.id,
      email: user.email,
      name: user.name,
      picture: user.picture || "",
    };
  }
  try {
    localStorage.setItem("chrononote_session_token", token);
    localStorage.setItem("chrononote_session_user", JSON.stringify(user));
    if (user) {
      localStorage.setItem("chrononote_last_user", JSON.stringify(lastUser.value));
    }
  } catch {
    // ignore
  }
}

async function signOutUser() {
  authToken.value = "";
  currentUser.value = null;
  try {
    localStorage.removeItem("chrononote_session_token");
    localStorage.removeItem("chrononote_session_user");
  } catch {
    // ignore
  }
  clearWorkspaceData();
  loadLocalJournals();
  loadLocalProjectsAndTasks();
  await fetchProjectsAndTimeline();
  await openDailyJournalForDate(selectedJournalDate.value, false);
}

async function fetchAuthConfig() {
  try {
    const res = await fetch(`${API_BASE}/auth/config`);
    if (res.ok) {
      const cfg = await res.json();
      if (cfg.google_client_id) {
        googleClientId.value = cfg.google_client_id;
      }
      hasServerOcrKey.value = Boolean(cfg.has_server_ocr_key);
      authRequired.value = Boolean(cfg.auth_required);
      if (authRequired.value && !currentUser.value) {
        showAuthModal.value = true;
      }
    }
  } catch {
    // Offline fallback
  }
}

async function handleGoogleCredentialResponse(response) {
  if (!response?.credential) return;
  isAuthenticating.value = true;
  authError.value = "";
  try {
    const res = await fetch(`${API_BASE}/auth/google`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ credential: response.credential }),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || "Google authentication failed");
    }
    const session = await res.json();
    clearWorkspaceData();
    saveAuthSession(session.token, session.user);
    loadLocalJournals();
    loadLocalProjectsAndTasks();
    showAuthModal.value = false;
    await fetchProjectsAndTimeline();
    await openDailyJournalForDate(selectedJournalDate.value, isJournalDrawerOpen.value);
  } catch (err) {
    authError.value = err.message || "Unable to sign in with Google";
  } finally {
    isAuthenticating.value = false;
  }
}

async function handleRegister(credentials) {
  const email = (credentials?.email || "").trim().toLowerCase();
  const name = (credentials?.name || email.split("@")[0]).trim();
  const password = credentials?.password || "";

  if (!email || !email.includes("@")) {
    authError.value = "Please enter a valid email address.";
    return;
  }
  if (!password || password.trim().length < 6) {
    authError.value = "Password is required and must be at least 6 characters.";
    return;
  }

  isAuthenticating.value = true;
  authError.value = "";
  try {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, name, password }),
    });
    if (res.ok) {
      const session = await res.json();
      clearWorkspaceData();
      saveAuthSession(session.token, session.user);
      loadLocalJournals();
      loadLocalProjectsAndTasks();
      isAuthenticating.value = false;
      showAuthModal.value = false;
      await fetchProjectsAndTimeline();
      await openDailyJournalForDate(selectedJournalDate.value, false);
      return;
    }
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Registration failed");
  } catch (err) {
    authError.value = err.message || "Registration failed";
    isAuthenticating.value = false;
  }
}

async function handlePersonalGoogleSignIn(credentials) {
  if (credentials?.email) {
    authEmailInput.value = credentials.email;
    if (credentials.name) authNameInput.value = credentials.name;
  }
  const email = authEmailInput.value.trim().toLowerCase();
  const password = credentials?.password || "";
  if (!email || !email.includes("@")) {
    authError.value = "Please enter a valid email address.";
    return;
  }
  if (!password || !password.trim()) {
    authError.value = "Password is required.";
    return;
  }

  isAuthenticating.value = true;
  authError.value = "";
  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (res.ok) {
      const session = await res.json();
      clearWorkspaceData();
      saveAuthSession(session.token, session.user);
      loadLocalJournals();
      loadLocalProjectsAndTasks();
      showAuthModal.value = false;
      isAuthenticating.value = false;
      await fetchProjectsAndTimeline();
      await openDailyJournalForDate(selectedJournalDate.value, isJournalDrawerOpen.value);
      return;
    }
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Incorrect email or password. Please try again.");
  } catch (err) {
    authError.value = err.message || "Sign-in rejected";
    isAuthenticating.value = false;
  }
}

function handleClearLastUser() {
  lastUser.value = null;
  try {
    localStorage.removeItem("chrononote_last_user");
  } catch {
    // ignore
  }
}

function mountGoogleIdentityButton() {
  if (
    typeof window === "undefined" ||
    !window.google?.accounts?.id ||
    !googleClientId.value ||
    !googleBtnContainer.value
  ) {
    return;
  }
  try {
    window.google.accounts.id.initialize({
      client_id: googleClientId.value,
      callback: handleGoogleCredentialResponse,
    });
    window.google.accounts.id.renderButton(googleBtnContainer.value, {
      theme: "outline",
      size: "large",
      shape: "rectangular",
      width: 320,
      text: "continue_with",
    });
  } catch {
    // Ignore GSI initialization errors if client ID is placeholder
  }
}

watch(showAuthModal, async (isOpen) => {
  if (isOpen) {
    authError.value = "";
    await nextTick();
    mountGoogleIdentityButton();
  }
});

// ---------------------------------------------------------------------------
// Calendar & Project Helpers
// ---------------------------------------------------------------------------

function getYearProjectGridStyle(proj) {
  const span = computeYearMonthGridSpan(
    proj.start_date,
    proj.target_date,
    selectedYear.value
  );
  if (!span.visible) return { display: "none" };
  return getCustomColorCardStyle(proj.color || "#b85423", {
    gridColumn: `${span.startMonthCol} / span ${span.spanMonthCols}`,
    gridRow: 1,
  });
}

function getYearProjectTaskRows(projId, pIdx) {
  if (!isProjectSubtasksVisible(projId)) {
    return [];
  }
  const raw = projectTasksMap.value[projId] || [];
  const prefix = String.fromCharCode(65 + (pIdx % 26));
  const withCodes = raw.map((t, idx) => ({
    ...t,
    code: `${prefix}${idx + 1}`,
  }));
  const filtered = filterSubtasksByStatus(withCodes, taskFilterMode.value, todayIso.value);

  const rows = [];
  let rowIndex = 2;

  for (let i = 0; i < filtered.length; i += 1) {
    const t = filtered[i];
    const effectiveStart = t.deadline_only ? (t.due_date || t.start_date) : t.start_date;
    const effectiveDue = t.deadline_only ? (t.due_date || t.start_date) : t.due_date;
    const span = computeYearMonthGridSpan(
      effectiveStart,
      effectiveDue,
      selectedYear.value
    );
    if (!span.visible) continue;
    rows.push({
      ...t,
      gridStyle: getCustomColorCardStyle(t.color || "#2c666e", {
        gridColumn: `${span.startMonthCol} / span ${span.spanMonthCols}`,
        gridRow: rowIndex,
      }),
    });
    rowIndex += 1;
  }
  return rows;
}

function stepCalendar(delta) {
  if (calendarScaleMode.value === "year") {
    selectedYear.value += delta;
  } else if (calendarScaleMode.value === "day") {
    selectedDayIso.value = shiftDateIso(selectedDayIso.value, delta);
    const dt = new Date(selectedDayIso.value + "T00:00:00Z");
    selectedYear.value = dt.getUTCFullYear();
    selectedMonth.value = dt.getUTCMonth() + 1;
    selectedWeekAnchorIso.value = selectedDayIso.value;
  } else if (calendarScaleMode.value === "week") {
    selectedWeekAnchorIso.value = shiftDateIso(selectedWeekAnchorIso.value, delta * 7);
    const dt = new Date(selectedWeekAnchorIso.value + "T00:00:00Z");
    selectedYear.value = dt.getUTCFullYear();
    selectedMonth.value = dt.getUTCMonth() + 1;
  } else {
    let nextM = selectedMonth.value + delta;
    if (nextM < 1) {
      selectedMonth.value = 12;
      selectedYear.value -= 1;
    } else if (nextM > 12) {
      selectedMonth.value = 1;
      selectedYear.value += 1;
    } else {
      selectedMonth.value = nextM;
    }
  }
}

function drillIntoMonth(col) {
  selectedMonth.value = col.index;
  calendarScaleMode.value = "month";
}

async function fetchProjectsAndTimeline() {
  try {
    const [res, archivedRes] = await Promise.all([
      fetch(`${API_BASE}/sidebar/projects`, {
        headers: getAuthHeaders(),
      }),
      fetch(`${API_BASE}/sidebar/projects?status_filter=archived`, {
        headers: getAuthHeaders(),
      }),
    ]);
    if (res.ok) {
      const data = await res.json();
      projects.value = data.map((p, i) => ({
        ...p,
        color: p.color || DEFAULT_PROJECTS[i % DEFAULT_PROJECTS.length].color,
        start_date:
          p.start_date ||
          DEFAULT_PROJECTS[i % DEFAULT_PROJECTS.length].start_date,
        target_date:
          p.target_date ||
          DEFAULT_PROJECTS[i % DEFAULT_PROJECTS.length].target_date,
      }));
      if (archivedRes.ok) {
        archivedProjects.value = await archivedRes.json();
      }
      persistLocalProjectsAndTasks();
    } else {
      loadLocalProjectsAndTasks();
    }
    const tasksRes = await fetch(`${API_BASE}/tasks`, {
      headers: getAuthHeaders(),
    });
    if (tasksRes.ok) {
      const allTasks = await tasksRes.json();
      const grouped = {};
      const stList = [];
      for (const t of allTasks) {
        const pid = t.project_id || 0;
        if (!grouped[pid]) grouped[pid] = [];
        const item = {
          ...t,
          color: t.color || (t.project_id ? "#2c666e" : "#e11d48"),
        };
        grouped[pid].push(item);
        if (!t.project_id) {
          stList.push(item);
        }
      }
      projectTasksMap.value = grouped;
      standaloneTasks.value = stList;
      persistLocalProjectsAndTasks();
    }
    const journalRes = await fetch(`${API_BASE}/journal`, {
      headers: getAuthHeaders(),
    });
    if (journalRes.ok) {
      const entries = await journalRes.json();
      const nextMap = {};
      for (const entry of entries) {
        if (entry.note_date) {
          nextMap[entry.note_date] = entry;
        }
      }
      dailyJournalsMap.value = nextMap;
      persistLocalJournals();
    }
  } catch {
    // Offline fallback uses scoped local data per user
    loadLocalProjectsAndTasks();
    loadLocalJournals();
  }
}

function getVisibleTimelineBounds() {
  if (calendarScaleMode.value === "month") {
    const y = selectedYear.value;
    const m = selectedMonth.value;
    const mStr = String(m).padStart(2, "0");
    const lastDay = new Date(Date.UTC(y, m, 0)).getUTCDate();
    return {
      start: `${y}-${mStr}-01`,
      target: `${y}-${mStr}-${String(lastDay).padStart(2, "0")}`,
    };
  } else if (calendarScaleMode.value === "week") {
    if (focusedWeekSpec.value?.days?.length === 7) {
      return {
        start: focusedWeekSpec.value.days[0].iso,
        target: focusedWeekSpec.value.days[6].iso,
      };
    }
    const anchor = selectedWeekAnchorIso.value || new Date().toISOString().slice(0, 10);
    return {
      start: anchor,
      target: shiftDateIso(anchor, 6),
    };
  } else {
    const y = selectedYear.value;
    return {
      start: `${y}-01-01`,
      target: `${y}-01-31`,
    };
  }
}

function initTimelineNewProjectDates() {
  const bounds = getVisibleTimelineBounds();
  newProject.value.start_date = bounds.start;
  newProject.value.target_date = bounds.target;
}

function toggleTimelineAddProject() {
  showTimelineAddProject.value = !showTimelineAddProject.value;
  if (showTimelineAddProject.value) {
    initTimelineNewProjectDates();
  }
}

// Workspace Reset / Delete All Data state
const showResetModal = ref(false);
const resetStep = ref(1);
const resetConfirmationInput = ref("");
const isResetting = ref(false);
const resetError = ref("");
const resetSuccess = ref("");

function openResetModal() {
  resetStep.value = 1;
  resetConfirmationInput.value = "";
  resetError.value = "";
  resetSuccess.value = "";
  showResetModal.value = true;
}

function proceedToResetStep2() {
  resetStep.value = 2;
  resetConfirmationInput.value = "";
  resetError.value = "";
}

async function executeWorkspaceReset() {
  if (resetConfirmationInput.value.trim().toUpperCase() !== "RESET") {
    resetError.value = "Please type RESET in capital letters to confirm.";
    return;
  }
  isResetting.value = true;
  resetError.value = "";
  try {
    const res = await fetch(`${API_BASE}/user/reset`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Server failed to reset workspace");
    }

    if (typeof localStorage !== "undefined") {
      localStorage.removeItem("chrononote_projects");
      localStorage.removeItem("chrononote_tasks");
      localStorage.removeItem("chrononote_journals_map");
      localStorage.removeItem("chrononote_has_journal_password");
    }
    if (typeof sessionStorage !== "undefined") {
      sessionStorage.removeItem("chrononote_journal_session_token");
    }

    projects.value = [];
    archivedProjects.value = [];
    projectTasksMap.value = {};
    standaloneTasks.value = [];
    dailyJournalsMap.value = {};
    habitsList.value = [];
    habitAnalytics.value = { days: [], overall_stats: {}, habit_streaks: [] };
    selectedProjectId.value = null;
    activeNote.value = { id: null, project_id: null, title: "", content_md: "" };
    journalDraftTitle.value = "";
    journalDraftMd.value = "";
    hasJournalPassword.value = false;
    isJournalUnlocked.value = true;

    await fetchProjectsAndTimeline();
    await fetchHabitsAndAnalytics();
    await fetchTemplates();

    resetSuccess.value = "All workspace data cleared successfully.";
    setTimeout(() => {
      showResetModal.value = false;
      resetSuccess.value = "";
      isResetting.value = false;
      resetStep.value = 1;
    }, 1000);
  } catch (err) {
    resetError.value = err.message || "Failed to reset workspace.";
    isResetting.value = false;
  }
}

async function createNewProject(pinImmediately = null) {
  if (!newProject.value.name.trim()) return;
  const isPinned =
    pinImmediately !== null ? pinImmediately : newProject.value.is_pinned;

  let start = newProject.value.start_date;
  let target = newProject.value.target_date;
  if (!start || !target) {
    const bounds = getVisibleTimelineBounds();
    start = start || bounds.start;
    target = target || bounds.target;
  }
  if (start && target && start > target) {
    const tmp = start;
    start = target;
    target = tmp;
  }

  const payload = {
    name: newProject.value.name.trim(),
    description: newProject.value.description.trim(),
    area: (newProject.value.area || "").trim(),
    status: newProject.value.status,
    color: newProject.value.color || "#c2410c",
    start_date: start || null,
    target_date: target || null,
    is_pinned: isPinned,
  };

  try {
    const res = await fetch(`${API_BASE}/projects`, {
      method: "POST",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      const created = await res.json();
      projects.value.push(created);
      persistLocalProjectsAndTasks();
      newProject.value.name = "";
      newProject.value.description = "";
      newProject.value.area = "";
      initTimelineNewProjectDates();
      showTimelineAddProject.value = false;
      showNewProjectModal.value = false;
      openProjectDrawer(created.id, "subtasks");
      return;
    }
  } catch {
    // Local fallback
  }

  const localProj = {
    id: Date.now(),
    ...payload,
  };
  projects.value.push(localProj);
  persistLocalProjectsAndTasks();
  newProject.value.name = "";
  newProject.value.description = "";
  newProject.value.area = "";
  initTimelineNewProjectDates();
  showTimelineAddProject.value = false;
  showNewProjectModal.value = false;
  openProjectDrawer(localProj.id, "subtasks");
}

async function updateProjectFields(proj, patch) {
  if (!proj) return;
  Object.assign(proj, patch);
  persistLocalProjectsAndTasks();
  try {
    const res = await fetch(`${API_BASE}/projects/${proj.id}`, {
      method: "PATCH",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(patch),
    });
    if (res.ok) {
      const updated = await res.json();
      Object.assign(proj, updated);
      persistLocalProjectsAndTasks();
    }
  } catch (err) {
    console.error("Failed to update project fields:", err);
  }
}

async function onProjectNameChange(proj, newName) {
  if (!proj) return;
  const trimmed = (newName || "").trim();
  if (!trimmed || trimmed === proj.name) return;
  await updateProjectFields(proj, { name: trimmed });
}

async function archiveProject(proj) {
  if (!proj) return;
  const prevStatus = proj.status || "active";
  projects.value = projects.value.filter((p) => p.id !== proj.id);
  const archivedCopy = { ...proj, status: "archived" };
  archivedProjects.value = [
    archivedCopy,
    ...archivedProjects.value.filter((p) => p.id !== proj.id),
  ];
  if (selectedProjectId.value === proj.id) {
    closeProjectDrawer();
  }
  persistLocalProjectsAndTasks();

  try {
    await fetch(`${API_BASE}/projects/${proj.id}`, {
      method: "PATCH",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ status: "archived" }),
    });
  } catch (err) {
    console.error("Failed to archive project:", err);
  }

  showNotification({
    type: "info",
    message: `Archived "${proj.name}"`,
    undoLabel: "Undo",
    undoFn: () => restoreArchivedProject(archivedCopy, prevStatus),
  });
}

async function restoreArchivedProject(proj, targetStatus = "active") {
  if (!proj) return;
  const restoredStatus =
    targetStatus && targetStatus !== "archived" ? targetStatus : "active";
  archivedProjects.value = archivedProjects.value.filter((p) => p.id !== proj.id);
  const restored = { ...proj, status: restoredStatus };
  projects.value = [
    ...projects.value.filter((p) => p.id !== proj.id),
    restored,
  ];
  persistLocalProjectsAndTasks();

  try {
    const res = await fetch(`${API_BASE}/projects/${proj.id}`, {
      method: "PATCH",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ status: restoredStatus }),
    });
    if (res.ok) {
      const updated = await res.json();
      Object.assign(restored, updated);
      persistLocalProjectsAndTasks();
    }
  } catch (err) {
    console.error("Failed to restore project:", err);
  }

  showNotification({
    type: "success",
    message: `Restored "${proj.name}"`,
  });
}

async function archiveCompletedProjects() {
  const completedList = projects.value.filter(
    (p) => p.status !== "archived" && isProjectCompleted(p)
  );
  if (!completedList.length) return;
  for (const p of completedList) {
    await archiveProject(p);
  }
  showNotification({
    type: "success",
    message: `Archived ${completedList.length} completed project${completedList.length === 1 ? "" : "s"}`,
  });
}

async function deleteProject(projectId) {
  if (!projectId) return;
  const proj =
    projects.value.find((p) => p.id === projectId) ||
    archivedProjects.value.find((p) => p.id === projectId);
  const name = proj ? proj.name : "this project";
  if (
    !window.confirm(
      `Permanently delete project "${name}" and all of its subtasks? This cannot be undone.`
    )
  ) {
    return;
  }
  projects.value = projects.value.filter((p) => p.id !== projectId);
  archivedProjects.value = archivedProjects.value.filter((p) => p.id !== projectId);
  if (projectTasksMap.value && projectTasksMap.value[projectId]) {
    delete projectTasksMap.value[projectId];
  }
  persistLocalProjectsAndTasks();
  if (selectedProjectId.value === projectId) {
    closeProjectDrawer();
  }
  try {
    await fetch(`${API_BASE}/projects/${projectId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
  } catch (err) {
    console.error("Failed to delete project on server:", err);
  }
}

async function toggleProjectDoneStatus(proj) {
  if (!proj) return;
  const nextStatus = isProjectCompleted(proj) ? "active" : "completed";
  await updateProjectFields(proj, { status: nextStatus });
}

async function toggleProjectDoneStatusById(projectId) {
  const proj = projects.value.find((p) => p.id === projectId);
  if (!proj) return;
  await toggleProjectDoneStatus(proj);
}

// ---------------------------------------------------------------------------
// Projects Kanban Drag-and-Drop Handlers
// ---------------------------------------------------------------------------

function onProjectDragStart(event, proj) {
  if (!proj) return;
  // Avoid starting card drag when interacting directly with inputs/buttons
  const tag = event?.target?.tagName?.toLowerCase();
  if (tag === "input" || tag === "select" || tag === "textarea") {
    event.preventDefault();
    return;
  }
  draggedProjectId.value = proj.id;
  dragOverColumnStatus.value = proj.status;
  if (event?.dataTransfer) {
    event.dataTransfer.effectAllowed = "move";
    try {
      event.dataTransfer.setData("text/plain", String(proj.id));
    } catch {
      // ignore in restricted environments
    }
  }
}

function onProjectDragEnd() {
  draggedProjectId.value = null;
  dragOverColumnStatus.value = null;
  dragOverProjectId.value = null;
  dragDropPosition.value = "after";
}

function onColumnDragOver(event, columnStatus) {
  if (draggedProjectId.value === null) return;
  if (event?.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
  dragOverColumnStatus.value = columnStatus;
}

function onColumnDragLeave(event, columnStatus) {
  const currentTarget = event?.currentTarget;
  const relatedTarget = event?.relatedTarget;
  if (
    currentTarget &&
    relatedTarget &&
    typeof currentTarget.contains === "function" &&
    currentTarget.contains(relatedTarget)
  ) {
    return;
  }
  if (dragOverColumnStatus.value === columnStatus) {
    dragOverColumnStatus.value = null;
  }
}

function onCardDragOver(event, targetProj, columnStatus) {
  if (draggedProjectId.value === null || !targetProj) return;
  if (event?.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
  dragOverColumnStatus.value = columnStatus;
  if (String(targetProj.id) === String(draggedProjectId.value)) {
    dragOverProjectId.value = null;
    return;
  }
  dragOverProjectId.value = targetProj.id;

  const rect = event?.currentTarget?.getBoundingClientRect?.();
  if (rect && typeof event.clientY === "number") {
    const midpoint = rect.top + rect.height / 2;
    dragDropPosition.value = event.clientY < midpoint ? "before" : "after";
  } else {
    dragDropPosition.value = "after";
  }
}

async function applyProjectKanbanMove(
  draggedId,
  targetStatus,
  options = {}
) {
  if (draggedId === null || draggedId === undefined) return;
  const {
    projects: nextProjects,
    movedProject,
    orderedProjectIds,
  } = moveProjectInKanban(projects.value, draggedId, targetStatus, options);

  projects.value = nextProjects;
  persistLocalProjectsAndTasks();
  onProjectDragEnd();

  if (!movedProject) return;

  try {
    const res = await fetch(`${API_BASE}/projects-kanban/move`, {
      method: "PATCH",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        project_id: movedProject.id,
        target_status: movedProject.status,
        sidebar_order: movedProject.sidebar_order,
        ordered_project_ids: orderedProjectIds,
      }),
    });
    if (!res.ok) {
      await fetch(`${API_BASE}/projects/${movedProject.id}`, {
        method: "PATCH",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          status: movedProject.status,
          sidebar_order: movedProject.sidebar_order,
        }),
      });
    }
  } catch {
    // Optimistic local state retained
  }
}

async function onColumnDrop(event, targetStatus) {
  const fallbackId = event?.dataTransfer?.getData?.("text/plain");
  const draggedId = draggedProjectId.value ?? fallbackId;
  await applyProjectKanbanMove(draggedId, targetStatus, {
    targetProjectId: dragOverProjectId.value,
    position: dragDropPosition.value,
  });
}

async function onCardDrop(event, targetProj, targetStatus) {
  const fallbackId = event?.dataTransfer?.getData?.("text/plain");
  const draggedId = draggedProjectId.value ?? fallbackId;
  await applyProjectKanbanMove(draggedId, targetStatus, {
    targetProjectId: targetProj?.id ?? null,
    position: dragDropPosition.value,
  });
}

async function addSubtaskToSelectedProject() {
  if (!selectedProject.value || !newSubtask.value.title.trim()) return;
  const pid = selectedProject.value.id;
  const isInbox = pid === 0;
  const payload = {
    project_id: isInbox ? null : pid,
    title: newSubtask.value.title.trim(),
    description: newSubtask.value.description ? newSubtask.value.description.trim() : "",
    status: "todo",
    priority: newSubtask.value.priority || "medium",
    color: newSubtask.value.color || (isInbox ? "#e11d48" : "#2c666e"),
    start_date: newSubtask.value.start_date || selectedProject.value.start_date,
    due_date: newSubtask.value.due_date || selectedProject.value.target_date,
    start_time: newSubtask.value.start_time || null,
    end_time: newSubtask.value.end_time || null,
    is_milestone: Boolean(newSubtask.value.is_milestone),
    deadline_only: Boolean(newSubtask.value.deadline_only),
  };

  try {
    const res = await fetch(`${API_BASE}/tasks`, {
      method: "POST",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      const created = await res.json();
      if (!projectTasksMap.value[pid]) projectTasksMap.value[pid] = [];
      const item = {
        ...created,
        color: created.color || payload.color,
      };
      projectTasksMap.value[pid].push(item);
      if (isInbox) {
        standaloneTasks.value = [...projectTasksMap.value[0]];
      }
      persistLocalProjectsAndTasks();
      newSubtask.value.title = "";
      newSubtask.value.description = "";
      newSubtask.value.start_time = "";
      newSubtask.value.end_time = "";
      newSubtask.value.is_milestone = false;
      return;
    }
  } catch {
    // Local fallback
  }

  if (!projectTasksMap.value[pid]) projectTasksMap.value[pid] = [];
  const localItem = {
    id: Date.now(),
    ...payload,
  };
  projectTasksMap.value[pid].push(localItem);
  if (isInbox) {
    standaloneTasks.value = [...projectTasksMap.value[0]];
  }
  persistLocalProjectsAndTasks();
  newSubtask.value.title = "";
  newSubtask.value.description = "";
  newSubtask.value.start_time = "";
  newSubtask.value.end_time = "";
  newSubtask.value.is_milestone = false;
}

async function toggleSubtaskStatus(projectId, taskId) {
  const pKey = projectId === null || projectId === undefined ? 0 : projectId;
  const list = projectTasksMap.value[pKey] || [];
  const target = list.find((t) => t.id === taskId);
  if (!target) return;

  const nextStatus = target.status === "done" ? "todo" : "done";
  target.status = nextStatus;
  target.progress = nextStatus === "done" ? 100 : 0;
  if (pKey === 0) {
    standaloneTasks.value = [...list];
  }
  persistLocalProjectsAndTasks();

  try {
    await fetch(`${API_BASE}/tasks/${taskId}`, {
      method: "PATCH",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        status: nextStatus,
        progress: nextStatus === "done" ? 100 : 0,
      }),
    });
  } catch {
    // Optimistic local state retained
  }
}

async function updateSubtaskFields(projectId, taskId, patch) {
  const pKey = projectId === null || projectId === undefined ? 0 : projectId;
  const list = projectTasksMap.value[pKey] || [];
  const target = list.find((t) => t.id === taskId);
  if (!target) return;
  Object.assign(target, patch);
  if (pKey === 0) {
    standaloneTasks.value = [...list];
  }
  persistLocalProjectsAndTasks();

  try {
    await fetch(`${API_BASE}/tasks/${taskId}`, {
      method: "PATCH",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(patch),
    });
  } catch {
    // Optimistic local state retained
  }
}

async function deleteSubtask(projectId, taskId) {
  const pKey = projectId === null || projectId === undefined ? 0 : projectId;
  const list = projectTasksMap.value[pKey] || [];
  projectTasksMap.value[pKey] = list.filter((t) => t.id !== taskId);
  if (pKey === 0) {
    standaloneTasks.value = [...(projectTasksMap.value[0] || [])];
  }
  persistLocalProjectsAndTasks();
  try {
    await fetch(`${API_BASE}/tasks/${taskId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
  } catch {
    // Optimistic local state retained
  }
}

async function saveNote() {
  try {
    const method = activeNote.value.id ? "PUT" : "POST";
    const url = activeNote.value.id
      ? `${API_BASE}/notes/${activeNote.value.id}`
      : `${API_BASE}/notes`;
    const res = await fetch(url, {
      method,
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        project_id: activeNote.value.project_id,
        title: activeNote.value.title,
        content_md: activeNote.value.content_md,
        sync_inline_tasks: true,
      }),
    });
    if (res.ok) {
      activeNote.value = await res.json();
      await fetchProjectsAndTimeline();
    }
  } catch {
    // Offline fallback
  }
}

onMounted(async () => {
  document.addEventListener("click", handleDocumentClick);
  window.addEventListener("keydown", handleGlobalKeydown);
  loadSavedAuthSession();
  loadLocalJournals();
  loadLocalProjectsAndTasks();
  fetchAuthConfig();
  await checkJournalLockStatus();
  await fetchProjectsAndTimeline();
  await fetchHabitsAndAnalytics();
  await fetchTemplates();
  await fetchStickers();
  await fetchStickerPlacements();
});

onUnmounted(() => {
  document.removeEventListener("click", handleDocumentClick);
  window.removeEventListener("keydown", handleGlobalKeydown);
  window.removeEventListener("pointerup", finishMonthDayDragCreate);
  window.removeEventListener("pointercancel", finishMonthDayDragCreate);
  if (toastTimer) clearTimeout(toastTimer);
});
</script>

<template>
  <LoginPage
    v-if="!currentUser"
    :google-client-id="googleClientId"
    :auth-error="authError"
    :is-authenticating="isAuthenticating"
    :last-user="lastUser"
    @login-google="handleGoogleCredentialResponse"
    @login-email="handlePersonalGoogleSignIn"
    @register="handleRegister"
    @clear-last-user="handleClearLastUser"
  />
  <div v-else class="editorial-app" :class="{ 'is-nav-open': isNavSpineOpen }">
    <!-- Persistent Top-Left Logo Toggle (Opens/Closes Dark-Bronze Sidebar) -->
    <button
      type="button"
      class="spine-logo-toggle"
      :class="{ active: isNavSpineOpen }"
      :aria-expanded="isNavSpineOpen"
      :title="isNavSpineOpen ? 'Close navigation sidebar' : 'Open navigation sidebar'"
      aria-label="Toggle navigation sidebar"
      @click="isNavSpineOpen = !isNavSpineOpen"
    >
      <span class="brand-mark" aria-hidden="true">
        <ChronoNoteLogo
          :size="22"
          dial-color="var(--spine-dial, #f8f4ec)"
          accent-color="var(--spine-accent, #e07b39)"
          paper-color="var(--spine-paper, #271e18)"
        />
      </span>
    </button>

    <!-- =====================================================================
         COLLAPSIBLE BROWN SPINE RAIL: Vertical Index Tabs, Search & Account
         ===================================================================== -->
    <header class="minimal-topbar">

      <nav class="primary-tabs" role="tablist" aria-label="Workspace Pages">
        <button
          type="button"
          class="page-tab-btn"
          :class="{ active: activePage === 'timeline' }"
          @click="activePage = 'timeline'"
        >
          <span class="tab-index-num">01</span>
          <span>Calendar</span>
        </button>
        <button
          type="button"
          class="page-tab-btn"
          :class="{ active: activePage === 'journal' }"
          @click="navigateToDailyJournal()"
        >
          <span class="tab-index-num">02</span>
          <span>Journal</span>
        </button>
        <button
          type="button"
          class="page-tab-btn"
          :class="{ active: activePage === 'kanban' }"
          @click="activePage = 'kanban'"
        >
          <span class="tab-index-num">03</span>
          <span>Projects</span>
        </button>
        <button
          type="button"
          class="page-tab-btn"
          :class="{ active: activePage === 'analytics' }"
          @click="
            activePage = 'analytics';
            fetchHabitsAndAnalytics();
          "
        >
          <span class="tab-index-num">04</span>
          <span>Habits</span>
        </button>
        <button
          type="button"
          class="page-tab-btn"
          :class="{ active: activePage === 'study' }"
          @click="
            activePage = 'study';
            fetchWorkspaceNotes();
          "
        >
          <span class="tab-index-num">05</span>
          <span>Study</span>
        </button>
      </nav>

      <div class="topbar-right">
        <button
          type="button"
          class="cmd-trigger-btn"
          title="Search & commands (Ctrl+K)"
          aria-label="Search and commands"
          @click="showCommandPalette = true"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <span class="spine-hide-label">Search</span>
          <kbd class="cmd-trigger-kbd spine-hide-label">⌘K</kbd>
        </button>
        <!-- Minimal User Dropdown (Encapsulates Account, Protect Journal, Today's Journal, Stickers, Theme, Connect Claude) -->
        <div ref="userDropdownRef" class="user-dropdown-container">
          <button
            type="button"
            class="user-dropdown-trigger"
            :class="{ active: isUserDropdownOpen }"
            :title="currentUser?.name || currentUser?.email || 'Account menu'"
            aria-label="User account and quick navigation menu"
            @click="isUserDropdownOpen = !isUserDropdownOpen"
          >
            <img
              v-if="currentUser?.picture"
              :src="currentUser.picture"
              :alt="currentUser.name"
              class="user-avatar-img"
            />
            <span v-else class="user-avatar-monogram">
              {{ (currentUser?.name || currentUser?.email || "U").charAt(0).toUpperCase() }}
            </span>
            <span class="user-name-label spine-hide-label">{{ currentUser?.name || currentUser?.email || "Account" }}</span>
            <svg class="chevron-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          <!-- Dropdown Menu Body -->
          <div v-if="isUserDropdownOpen" class="user-menu-dropdown animate-fade-in" @click.stop>
            <!-- User Header -->
            <div class="user-menu-header">
              <div class="user-menu-avatar-wrap">
                <img
                  v-if="currentUser?.picture"
                  :src="currentUser.picture"
                  :alt="currentUser.name"
                  class="user-menu-avatar"
                />
                <span v-else class="user-menu-monogram">
                  {{ (currentUser?.name || currentUser?.email || "U").charAt(0).toUpperCase() }}
                </span>
              </div>
              <div class="user-menu-info">
                <div class="user-menu-name">{{ currentUser?.name || "Local User" }}</div>
                <div class="user-menu-email">{{ currentUser?.email || "guest@local" }}</div>
              </div>
            </div>

            <div class="user-menu-divider" />

            <!-- Account Settings Page Link -->
            <button
              type="button"
              class="user-menu-item"
              @click="isUserDropdownOpen = false; showAccountSettingsModal = true"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
              <span class="user-menu-item-text">Account Settings</span>
            </button>

            <!-- Today's Journal -->
            <button
              type="button"
              class="user-menu-item"
              @click="isUserDropdownOpen = false; openDailyJournalForDate(selectedJournalDate, true)"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M12 20h9" />
                <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
              </svg>
              <span class="user-menu-item-text">Today’s Journal</span>
            </button>

            <!-- Protect Journal -->
            <button
              type="button"
              class="user-menu-item"
              @click="
                isUserDropdownOpen = false;
                hasJournalPassword && !isJournalUnlocked
                  ? (showJournalUnlockModal = true)
                  : (showJournalSettingsModal = true);
              "
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path v-if="hasJournalPassword && !isJournalUnlocked" d="M7 11V7a5 5 0 0 1 10 0v4" />
                <path v-else d="M7 11V7a5 5 0 0 1 9.9-1" />
              </svg>
              <span class="user-menu-item-text">
                {{ !hasJournalPassword ? "Protect Journal" : (!isJournalUnlocked ? "Unlock Journal" : "Journal Security") }}
              </span>
              <span class="menu-item-pill" :class="{ 'is-active': isJournalUnlocked }">
                {{ !hasJournalPassword ? "Disabled" : (!isJournalUnlocked ? "Locked" : "Unlocked") }}
              </span>
            </button>

            <!-- Stickers & Stamps -->
            <button
              type="button"
              class="user-menu-item"
              @click="
                isUserDropdownOpen = false;
                activeStickerTarget = {
                  type: 'calendar_date',
                  key: selectedJournalDate
                };
                isStickerDrawerOpen = true;
                fetchStickers();
                fetchStickerPlacements();
              "
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <circle cx="12" cy="12" r="10" />
                <path d="M8 14s1.5 2 4 2 4-2 4-2" />
                <line x1="9" y1="9" x2="9.01" y2="9" />
                <line x1="15" y1="9" x2="15.01" y2="9" />
              </svg>
              <span class="user-menu-item-text">Stickers</span>
              <span v-if="stickerPlacements.length" class="menu-item-pill">{{ stickerPlacements.length }}</span>
            </button>

            <!-- Theme Settings -->
            <button
              type="button"
              class="user-menu-item"
              @click="isUserDropdownOpen = false; showThemeSettingsModal = true"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <circle cx="13.5" cy="6.5" r=".5" />
                <circle cx="17.5" cy="10.5" r=".5" />
                <circle cx="8.5" cy="7.5" r=".5" />
                <circle cx="6.5" cy="12.5" r=".5" />
                <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z" />
              </svg>
              <span class="user-menu-item-text">Theme</span>
            </button>

            <!-- Connect Antigravity -->
            <button
              type="button"
              class="user-menu-item"
              @click="isUserDropdownOpen = false; openMcpConnectModal('antigravity')"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
              </svg>
              <span class="user-menu-item-text">Connect Antigravity</span>
            </button>

            <!-- Connect Claude -->
            <button
              type="button"
              class="user-menu-item"
              @click="isUserDropdownOpen = false; openMcpConnectModal('claude')"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
              </svg>
              <span class="user-menu-item-text">Connect Claude</span>
            </button>

            <div class="user-menu-divider" />

            <!-- Reset Workspace Data -->
            <button
              type="button"
              class="user-menu-item item-danger"
              @click="isUserDropdownOpen = false; openResetModal()"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
              <span class="user-menu-item-text">Reset Workspace</span>
            </button>

            <!-- Sign Out / Sign In -->
            <button
              v-if="currentUser"
              type="button"
              class="user-menu-item item-signout"
              @click="isUserDropdownOpen = false; signOutUser()"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              <span class="user-menu-item-text">Sign Out</span>
            </button>
            <button
              v-else
              type="button"
              class="user-menu-item item-signin"
              @click="isUserDropdownOpen = false; showAuthModal = true"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                <polyline points="10 17 15 12 10 7" />
                <line x1="15" y1="12" x2="3" y2="12" />
              </svg>
              <span class="user-menu-item-text">Sign In</span>
            </button>
          </div>
        </div>
      </div>
</header>

    <!-- =====================================================================
         PAGE 1: PROJECTS KANBAN BOARD
         ===================================================================== -->
    <main
      v-if="activePage === 'kanban'"
      class="kanban-page"
      aria-label="Projects Board Page"
    >
      <div class="projects-toolbar-bar">
        <div class="projects-toolbar-left">
          <div class="segmented-scale" role="group" aria-label="Projects View">
            <button
              type="button"
              class="scale-btn"
              :class="{ active: projectsPageView === 'board' }"
              @click="projectsPageView = 'board'"
            >
              Board
            </button>
            <button
              type="button"
              class="scale-btn"
              :class="{ active: projectsPageView === 'list' }"
              @click="projectsPageView = 'list'"
            >
              List
            </button>
            <button
              type="button"
              class="scale-btn"
              :class="{ active: projectsPageView === 'archive' }"
              @click="projectsPageView = 'archive'"
            >
              Archive ({{ archivedProjects.length }})
            </button>
          </div>

          <input
            v-if="projectsPageView !== 'archive'"
            v-model="projectsSearchQuery"
            type="text"
            class="input-minimal projects-search-input"
            placeholder="Filter projects…"
          />

          <select
            v-if="projectsPageView !== 'archive' && projectAreas.length > 0"
            v-model="selectedAreaFilter"
            class="input-minimal projects-area-select"
            aria-label="Filter by folder"
          >
            <option value="all">All folders</option>
            <option v-for="ar in projectAreas" :key="ar" :value="ar">
              {{ ar }}
            </option>
            <option value="__none__">Uncategorized</option>
          </select>

          <label
            v-if="projectsPageView !== 'archive'"
            class="pin-check-inline"
          >
            <input v-model="hideCompletedProjects" type="checkbox" />
            <span>Hide completed</span>
          </label>
        </div>

        <div class="projects-toolbar-right">
          <button
            v-if="projects.some((p) => p.status !== 'archived' && isProjectCompleted(p))"
            type="button"
            class="btn-editorial-ghost"
            title="Move all completed projects into Archive Vault"
            @click="archiveCompletedProjects"
          >
            Archive Completed
          </button>
          <button
            type="button"
            class="btn-ink-primary"
            @click="showNewProjectModal = true"
          >
            + New Project
          </button>
        </div>
      </div>

      <div class="projects-body-wrap">
      <!-- VIEW 1: CLEAN KANBAN BOARD -->
      <div v-if="projectsPageView === 'board'" class="projects-kanban-grid">
        <section
          v-for="(col, colIdx) in projectKanbanColumns"
          :key="col.status"
          class="project-kanban-column"
          :class="{
            'drag-over-column':
              draggedProjectId !== null && dragOverColumnStatus === col.status,
            'is-collapsed-col': collapsedKanbanCols[col.status],
          }"
          @dragover.prevent="onColumnDragOver($event, col.status)"
          @dragleave="onColumnDragLeave($event, col.status)"
          @drop.prevent="onColumnDrop($event, col.status)"
        >
          <header class="kanban-col-header">
            <span class="col-title-wrap">
              <span class="col-index-num">0{{ colIdx + 1 }}</span>
              <span class="col-title">{{ col.label }}</span>
            </span>
            <div class="kanban-col-head-right">
              <span class="col-count">{{ col.count }}</span>
              <button
                v-if="col.status === 'completed' || col.status === 'on_hold'"
                type="button"
                class="kanban-col-collapse-btn"
                :title="collapsedKanbanCols[col.status] ? 'Expand column' : 'Collapse column'"
                @click="collapsedKanbanCols[col.status] = !collapsedKanbanCols[col.status]"
              >
                {{ collapsedKanbanCols[col.status] ? "▸" : "▾" }}
              </button>
            </div>
          </header>

          <div v-if="!collapsedKanbanCols[col.status]" class="kanban-cards-stack">
            <article
              v-for="proj in col.projects"
              :key="proj.id"
              class="project-kanban-card clickable-card draggable-kanban-card"
              :class="{
                'is-dragging': draggedProjectId === proj.id,
                'drag-over-before':
                  dragOverProjectId === proj.id &&
                  dragDropPosition === 'before' &&
                  draggedProjectId !== proj.id,
                'drag-over-after':
                  dragOverProjectId === proj.id &&
                  dragDropPosition === 'after' &&
                  draggedProjectId !== proj.id,
              }"
              draggable="true"
              @dragstart="onProjectDragStart($event, proj)"
              @dragend="onProjectDragEnd"
              @dragover.prevent.stop="onCardDragOver($event, proj, col.status)"
              @drop.prevent.stop="onCardDrop($event, proj, col.status)"
              @click="openProjectDrawer(proj.id, 'subtasks')"
            >
              <div class="pcard-top">
                <div class="pcard-title-row">
                  <span
                    class="sidebar-dot"
                    :style="{ backgroundColor: proj.color || '#c2410c' }"
                  />
                  <strong
                    class="pcard-title"
                    :class="{ 'strikethrough-done': isProjectCompleted(proj) }"
                  >
                    {{ proj.name }}
                  </strong>
                </div>
                <div class="pcard-top-actions" @click.stop>
                  <button
                    type="button"
                    class="pcard-icon-btn"
                    :class="{ active: proj.is_pinned }"
                    :title="proj.is_pinned ? 'Unpin from calendar' : 'Pin to calendar'"
                    @click="updateProjectFields(proj, { is_pinned: !proj.is_pinned })"
                  >
                    {{ proj.is_pinned ? "Pinned" : "Pin" }}
                  </button>
                  <button
                    type="button"
                    class="pcard-icon-btn"
                    title="Archive project"
                    @click="archiveProject(proj)"
                  >
                    Archive
                  </button>
                </div>
              </div>

              <div v-if="proj.area || proj.overdue_tasks > 0" class="pcard-tags-row">
                <span v-if="proj.area" class="project-area-tag">{{ proj.area }}</span>
                <span v-if="proj.overdue_tasks > 0" class="overdue-tag-pill">
                  {{ proj.overdue_tasks }} overdue
                </span>
              </div>

              <p v-if="proj.description" class="pcard-desc">
                {{ proj.description }}
              </p>

              <!-- Slim 2px progress bar -->
              <div
                v-if="(projectTasksMap[proj.id] || []).length > 0"
                class="pcard-progress-track"
                :title="`${proj.progress_pct || 0}% complete`"
              >
                <div
                  class="pcard-progress-fill"
                  :style="{
                    width: `${
                      Math.round(
                        ((projectTasksMap[proj.id] || []).filter(
                          (t) => t.status === 'done' || t.progress === 100
                        ).length /
                          Math.max((projectTasksMap[proj.id] || []).length, 1)) *
                          100
                      )
                    }%`,
                    backgroundColor: proj.color || '#c2410c',
                  }"
                />
              </div>

              <div class="pcard-footer" @click.stop>
                <span class="mono-dates">
                  {{ proj.start_date || "—" }} → {{ proj.target_date || "—" }}
                </span>
                <div class="pcard-footer-actions">
                  <button
                    type="button"
                    class="kanban-subtasks-vis-btn"
                    :class="{ active: isProjectSubtasksVisible(proj.id) }"
                    @click="toggleProjectSubtasksVisibility(proj.id)"
                  >
                    {{ isProjectSubtasksVisible(proj.id) ? "Timeline On" : "Timeline" }}
                  </button>
                  <span class="pcard-task-count">
                    {{ (projectTasksMap[proj.id] || []).length }} tasks
                  </span>
                </div>
              </div>
            </article>

            <div
              v-if="col.projects.length === 0"
              class="kanban-empty-dropzone"
              :class="{
                'active-dropzone':
                  draggedProjectId !== null &&
                  dragOverColumnStatus === col.status,
              }"
            >
              <span>Drop here</span>
            </div>
          </div>
        </section>
      </div>

      <!-- VIEW 2: COMPACT LIST / TABLE -->
      <div v-else-if="projectsPageView === 'list'" class="projects-list-table-wrap">
        <table class="projects-list-table">
          <thead>
            <tr>
              <th>Project</th>
              <th>Folder</th>
              <th>Status</th>
              <th>Timeline</th>
              <th>Tasks</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="proj in filteredProjectsForBoard"
              :key="proj.id"
              class="projects-list-row"
              @click="openProjectDrawer(proj.id, 'subtasks')"
            >
              <td>
                <div class="list-proj-name-cell">
                  <span
                    class="sidebar-dot"
                    :style="{ backgroundColor: proj.color || '#c2410c' }"
                  />
                  <strong :class="{ 'strikethrough-done': isProjectCompleted(proj) }">
                    {{ proj.name }}
                  </strong>
                </div>
              </td>
              <td>
                <span v-if="proj.area" class="project-area-tag">{{ proj.area }}</span>
                <span v-else class="text-faint">—</span>
              </td>
              <td @click.stop>
                <select
                  :value="proj.status"
                  class="input-minimal list-status-select"
                  @change="updateProjectFields(proj, { status: $event.target.value })"
                >
                  <option value="planned">Planned</option>
                  <option value="active">Active</option>
                  <option value="on_hold">On Hold</option>
                  <option value="completed">Completed</option>
                </select>
              </td>
              <td class="mono-dates">
                {{ proj.start_date || "—" }} → {{ proj.target_date || "—" }}
              </td>
              <td class="mono-dates">
                {{
                  (projectTasksMap[proj.id] || []).filter(
                    (t) => t.status === "done" || t.progress === 100
                  ).length
                }}
                / {{ (projectTasksMap[proj.id] || []).length }}
              </td>
              <td class="list-actions-cell" @click.stop>
                <button
                  type="button"
                  class="pcard-icon-btn"
                  :class="{ active: proj.is_pinned }"
                  @click="updateProjectFields(proj, { is_pinned: !proj.is_pinned })"
                >
                  {{ proj.is_pinned ? "Pinned" : "Pin" }}
                </button>
                <button
                  type="button"
                  class="pcard-icon-btn"
                  @click="archiveProject(proj)"
                >
                  Archive
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="filteredProjectsForBoard.length === 0" class="archive-empty-state">
          No projects match the current filters.
        </div>
      </div>

      <!-- VIEW 3: INLINE ARCHIVE VAULT -->
      <div v-else class="projects-archive-inline">
        <div
          v-for="proj in archivedProjects"
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
              @click="restoreArchivedProject(proj)"
            >
              Restore
            </button>
            <button
              type="button"
              class="delete-project-btn"
              @click="deleteProject(proj.id)"
            >
              Delete
            </button>
          </div>
        </div>
        <div v-if="archivedProjects.length === 0" class="archive-empty-state">
          No archived projects yet.
        </div>
      </div>
      </div>
    </main>

    <!-- =====================================================================
         PAGE 2: DAILY JOURNAL PAGE (Day-by-Day Notebook + Handwritten OCR)
         ===================================================================== -->
    <main
      v-else-if="activePage === 'journal'"
      class="journal-page"
      aria-label="Daily Journal Page"
    >
      <!-- Left Column: Chronological Journal Stream & Date Picker -->
      <aside class="journal-stream-sidebar">
        <div class="sidebar-top-row">
          <span class="sidebar-heading">Entries</span>
          <input
            type="date"
            class="input-minimal date-jump-input"
            :value="selectedJournalDate"
            aria-label="Jump to journal date"
            @change="openDailyJournalForDate($event.target.value, false)"
          />
        </div>

        <p class="sidebar-hint">
          Select any date or click a day cell in Month View to write or scan handwritten journal pages.
        </p>

        <div class="journal-entries-list">
          <button
            v-for="entry in sortedJournalEntries"
            :key="entry.note_date"
            type="button"
            class="journal-stream-card clickable-card"
            :class="{ active: selectedJournalDate === entry.note_date }"
            @click="openDailyJournalForDate(entry.note_date, false)"
          >
            <div class="jcard-header">
              <span class="jcard-date-serif">{{ entry.editorialDate.short }}</span>
              <span class="jcard-weekday">{{ entry.editorialDate.weekday }}</span>
            </div>
            <p class="jcard-snippet">
              {{ entry.snippet || "Empty entry" }}
            </p>
          </button>
        </div>
      </aside>

      <!-- Right Surface: Full Editorial Journal Page + Handwritten OCR -->
      <section class="journal-editor-surface">
        <header class="journal-surface-header">
          <div class="journal-date-stepper">
            <button
              type="button"
              class="nav-step-btn"
              title="Previous day"
              @click="stepJournalDate(-1)"
            >
              ‹
            </button>
            <span class="journal-poster-day" aria-hidden="true">
              {{ (selectedJournalDate || "").slice(8, 10) }}
            </span>
            <div class="journal-title-editor-block">
              <span class="journal-kicker">{{ formattedJournalHeading.full }}</span>
              <input
                v-model="journalDraftTitle"
                type="text"
                class="journal-title-input editorial-serif-heading"
                :placeholder="formattedJournalHeading.full"
                title="Click to edit journal title"
                @blur="saveDailyJournalEntry"
              />
            </div>
            <button
              type="button"
              class="nav-step-btn"
              title="Next day"
              @click="stepJournalDate(1)"
            >
              ›
            </button>
          </div>

          <div class="journal-header-actions">
            <span v-if="journalSaveStatus === 'saved'" class="save-pill">
              Saved
            </span>
            <label class="btn-ocr-scanner" title="Scan Handwritten Page (OCR)">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                <circle cx="12" cy="13" r="4" />
              </svg>
              <span>Scan OCR</span>
              <input
                type="file"
                accept="image/*"
                capture="environment"
                class="sr-only-file"
                @change="handleOcrFileChange($event, 'journal')"
              />
            </label>

            <!-- Docs-Style Image Uploaders -->
            <label class="btn-editorial-ghost" title="Upload image as draggable floating card (Docs style)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <polyline points="21 15 16 10 5 21" />
              </svg>
              <span>+ Float Image</span>
              <input
                type="file"
                accept="image/*"
                class="sr-only-file"
                @change="handleUploadJournalImage($event.target.files?.[0], 'draggable')"
              />
            </label>
            <label class="btn-editorial-ghost" title="Upload image in-line with markdown text">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="3" y1="6" x2="21" y2="6" />
                <rect x="3" y="9" width="10" height="9" rx="1" />
                <line x1="16" y1="11" x2="21" y2="11" />
                <line x1="16" y1="15" x2="21" y2="15" />
                <line x1="3" y1="21" x2="21" y2="21" />
              </svg>
              <span>+ Inline Image</span>
              <input
                type="file"
                accept="image/*"
                class="sr-only-file"
                @change="handleUploadJournalImage($event.target.files?.[0], 'inline')"
              />
            </label>

            <button
              type="button"
              class="btn-editorial-ghost"
              title="Choose a sticker to add to this journal"
              @click="openJournalStickerTray"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 3a9 9 0 1 0 9 9c0-1.1-.9-2-2-2h-2a2 2 0 0 1-2-2V6c0-1.7-1.3-3-3-3Z" />
                <circle cx="7.5" cy="11" r="1" />
                <circle cx="10" cy="7.5" r="1" />
              </svg>
              <span>+ Sticker</span>
            </button>
            <button
              type="button"
              class="btn-editorial-ghost"
              :class="{ 'is-active': isJournalMediaEditing }"
              :title="isJournalMediaEditing ? 'Finish arranging journal media' : 'Arrange images and stickers'"
              @click="toggleJournalMediaEditing"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 9V4h5" /><path d="M20 9V4h-5" />
                <path d="M4 15v5h5" /><path d="M20 15v5h-5" />
              </svg>
              <span>{{ isJournalMediaEditing ? 'Done' : 'Arrange' }}</span>
            </button>

            <button
              type="button"
              class="btn-editorial-ghost"
              :title="hasJournalPassword ? 'Lock journal session now' : 'Set journal password'"
              @click="hasJournalPassword ? lockJournalSession() : (showJournalSettingsModal = true)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <span>{{ hasJournalPassword ? "Lock" : "Protect" }}</span>
            </button>

            <!-- Templates Dropdown -->
            <div class="template-dropdown-wrapper">
              <button
                type="button"
                class="btn-editorial-ghost template-menu-trigger"
                title="Choose or customize journal template"
                @click="showTemplateMenu = !showTemplateMenu"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <line x1="3" y1="9" x2="21" y2="9" />
                  <line x1="9" y1="21" x2="9" y2="9" />
                </svg>
                <span>Templates ▾</span>
              </button>
              <div v-if="showTemplateMenu" class="template-dropdown-menu">
                <div class="template-menu-header">Templates</div>
                <button
                  v-for="tpl in availableTemplates"
                  :key="tpl.id"
                  type="button"
                  class="template-menu-item"
                  @click="applyJournalTemplate(tpl.id)"
                >
                  <div class="tpl-item-title-row">
                    <span class="tpl-title">{{ tpl.name }}</span>
                    <span v-if="tpl.is_default" class="tpl-badge-default">Default</span>
                  </div>
                  <span v-if="tpl.description" class="tpl-desc">{{ tpl.description }}</span>
                </button>
                <div class="template-menu-divider" />
                <button
                  type="button"
                  class="template-menu-item manage-action-item"
                  @click="showTemplateMenu = false; openTemplateManager()"
                >
                  <span class="tpl-title">+ Create &amp; Manage Templates...</span>
                  <span class="tpl-desc">Customize prompts, checklists &amp; default templates</span>
                </button>
              </div>
            </div>

            <button
              type="button"
              class="btn-orange-primary"
              @click="saveDailyJournalEntry"
            >
              Save Entry
            </button>
          </div>
        </header>

        <div class="journal-surface-body">
        <!-- Interactive Habit Quick Bar -->
        <div v-if="activeHabits.length > 0" class="journal-habit-quick-bar">
          <span class="habit-bar-kicker">Habits</span>
          <div class="habit-pills-list">
            <button
              v-for="h in activeHabits"
              :key="h.id"
              type="button"
              class="habit-pill-btn"
              :class="{ completed: isHabitCompletedOnDate(h.slug, selectedJournalDate) }"
              :title="isHabitCompletedOnDate(h.slug, selectedJournalDate) ? 'Completed! Click to uncheck' : 'Click to complete'"
              @click="handleToggleHabit(h.id, selectedJournalDate)"
            >
              <span class="pill-check">{{ isHabitCompletedOnDate(h.slug, selectedJournalDate) ? '✓' : '○' }}</span>
              <span class="pill-title">{{ h.name }}</span>
              <span v-if="h.current_streak > 0" class="pill-flame">{{ h.current_streak }}d streak</span>
            </button>
          </div>
        </div>

        <!-- Empty state one-click scaffold banner -->
        <div v-if="!journalDraftMd.trim()" class="empty-journal-scaffold-banner">
          <div class="scaffold-banner-info">
            <span class="scaffold-banner-badge">BLANK DAY</span>
            <div>
              <h4 class="scaffold-banner-title">No notes recorded for this date yet</h4>
              <p class="scaffold-banner-desc">Click below to start writing, or apply a template to scaffold prompts and habits.</p>
            </div>
          </div>
          <div class="scaffold-banner-actions">
            <button
              type="button"
              class="btn-editorial-ghost"
              @click="startEditingJournal(false)"
            >
              Start Writing
            </button>
            <button
              type="button"
              class="btn-scaffold-action"
              @click="applyJournalTemplate(null)"
            >
              Apply Default Template
            </button>
          </div>
        </div>

        <!-- OCR Scanner Progress & Review Panel -->
        <div
          v-if="
            ocrTarget === 'journal' &&
            (isOcrRunning || ocrExtractedText || ocrError)
          "
          class="ocr-review-panel"
        >
          <div class="ocr-panel-top">
            <div class="ocr-panel-status">
              <strong>Handwriting &amp; Notebook OCR</strong>
              <span v-if="isOcrRunning" class="ocr-status-muted">
                {{ ocrStatusText }} ({{ ocrProgress }}%)
              </span>
              <span v-else-if="ocrExtractedText" class="ocr-status-ready">
                Text extracted — review and insert below
              </span>
            </div>
            <div class="ocr-panel-options">
              <label class="pin-check-inline">
                <input v-model="ocrEnhanceContrast" type="checkbox" />
                <span>Enhance ink contrast</span>
              </label>
              <label class="pin-check-inline">
                <input v-model="includeOcrHeading" type="checkbox" />
                <span>Add scan heading</span>
              </label>
              <button
                type="button"
                class="close-drawer-btn"
                @click="resetOcrState"
              >
                ×
              </button>
            </div>
          </div>

          <div v-if="isOcrRunning" class="ocr-progress-bar-track">
            <div
              class="ocr-progress-bar-fill"
              :style="{ width: `${ocrProgress}%` }"
            />
          </div>

          <p v-if="ocrError" class="ocr-error-msg">{{ ocrError }}</p>

          <div v-if="ocrExtractedText || ocrPreviewUrl" class="ocr-split-preview">
            <img
              v-if="ocrPreviewUrl"
              :src="ocrPreviewUrl"
              alt="Scanned journal page"
              class="ocr-thumb-img"
            />
            <div v-if="ocrExtractedText" class="ocr-extracted-box">
              <textarea
                v-model="ocrExtractedText"
                class="drawer-textarea ocr-textarea"
                rows="5"
              />
              <div class="ocr-Extracted-actions">
                <button
                  type="button"
                  class="btn-orange-primary"
                  @click="insertOcrTextIntoNote"
                >
                  Insert into {{ formattedJournalHeading.short }} Journal
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Active Project Tasks on this Date -->
        <div
          v-if="tasksOnSelectedJournalDate.length > 0"
          class="journal-day-tasks-strip"
        >
          <span class="strip-label">Scheduled on this day:</span>
          <div class="strip-chips">
            <span
              v-for="t in tasksOnSelectedJournalDate"
              :key="t.id"
              class="day-task-chip"
              :style="{ borderLeft: `3px solid ${t.projectColor}` }"
            >
              {{ t.title }}
              <small>({{ t.projectName }})</small>
            </span>
          </div>
        </div>

        <div class="journal-paper-body">
          <JournalDraggablesOverlay
            :images="journalFloatingImages"
            :stickers="journalStickers"
            :media-editing="isJournalMediaEditing"
            :scroll-offset="journalMediaScrollTop"
            @update-image="handleUpdateFloatingImage"
            @change-image-mode="handleChangeFloatingImageMode"
            @delete-image="handleDeleteFloatingImage"
            @update-sticker="handleUpdateStickerPlacement"
            @delete-sticker="handleRemovePlacement"
          />
          <!-- Rendered Markdown View -->
          <div
            v-if="!isEditingJournal"
            ref="journalPreviewRef"
            class="journal-preview-paper clickable-paper"
            :class="[
              { 'is-empty': !journalDraftMd || !journalDraftMd.trim() },
              getPaperStyleClass(customThemePrefs.paperTheme),
              getTypographyClass(customThemePrefs.typographyTheme),
            ]"
            title="Click to write or edit markdown"
            @scroll="handleJournalContentScroll"
            @click="handleJournalPreviewClick($event, false)"
          >
            <div
              v-if="journalDraftMd && journalDraftMd.trim()"
              class="journal-rendered-prose"
              v-html="renderedJournalHtml"
            />
            <div v-else class="empty-journal-paper-placeholder">
              <p class="journal-placeholder-heading">No journal entry recorded for this date.</p>
              <p class="journal-placeholder-sub">Click anywhere to start writing in Markdown, or choose a template above.</p>
              <small class="journal-placeholder-hint">Supports headings, checklists <code>- [ ]</code>, #tags, [[WikiLinks]], and @habit(slug).</small>
            </div>
          </div>

          <!-- Markdown Editor -->
          <div
            v-else
            class="journal-notepad-wrapper"
            :class="[
              getPaperStyleClass(customThemePrefs.paperTheme),
              getTypographyClass(customThemePrefs.typographyTheme),
            ]"
          >
            <textarea
              ref="journalTextareaRef"
              v-model="journalDraftMd"
              class="journal-ruled-textarea live-journal-notepad"
              :placeholder="`Write your thoughts for ${formattedJournalHeading.full} in Markdown…`"
              spellcheck="false"
              @scroll="handleJournalContentScroll"
              @blur="stopEditingJournal"
            />
            <div class="notepad-focusout-hint">
              <span>Markdown active &bull; Click outside or focus out to save</span>
            </div>
          </div>
        </div>
        <button
          v-if="!isEditingJournal"
          type="button"
          class="journal-edit-cta"
          @click="startEditingJournal(false)"
        >
          Click to edit markdown
        </button>
        </div>
      </section>
    </main>

    <!-- =====================================================================
         PAGE 4: HABIT CONSISTENCY & 52-WEEK HEATMAP ANALYTICS
         ===================================================================== -->
    <main
      v-else-if="activePage === 'analytics'"
      class="analytics-page"
      aria-label="Habits Heatmap & Analytics Page"
    >
      <HabitHeatmapView
        :analytics-data="habitAnalytics"
        :habits-list="habitsList"
        :active-date="selectedJournalDate"
        @select-date="jumpToJournalFromHeatmap"
        @create-habit="handleCreateHabit"
        @update-habit="handleUpdateHabit"
        @delete-habit="handleDeleteHabit"
        @toggle-habit="handleToggleHabit"
      />
    </main>

    <!-- =====================================================================
         PAGE 4: STUDY SANCTUARY & POMODORO CLOCK
         ===================================================================== -->
    <main
      v-else-if="activePage === 'study'"
      class="study-page"
      aria-label="Study & Pomodoro Page"
    >
      <StudyModeView
        :projects="projects"
        :notes="workspaceNotes"
        :tasks="allTasksList"
        :selected-journal-date="selectedJournalDate"
        :api-base="API_BASE"
        :get-auth-headers="getAuthHeaders"
        @session-completed="handleStudySessionCompleted"
        @note-updated="handleStudyNoteUpdated"
        @notify="showNotification"
      />
    </main>

    <!-- =====================================================================
         PAGE 3: SPACIOUS CALENDAR TIMELINE (Click any date for Daily Journal!)
         ===================================================================== -->
    <main
      v-else
      class="timeline-page"
      :class="{ 'is-sidebar-collapsed': isSidebarCollapsed }"
      aria-label="Calendar Timeline Page"
    >
      <!-- Mobile Projects Sidebar Toggle Bar -->
      <div class="mobile-sidebar-toggle-bar">
        <button
          type="button"
          class="btn-editorial-ghost"
          @click="showMobileProjectsSidebar = !showMobileProjectsSidebar"
        >
          {{
            showMobileProjectsSidebar
              ? "Hide Projects"
              : `Projects (${pinnedProjects.length})`
          }}
        </button>
        <button
          type="button"
          class="btn-ink-primary"
          @click="openQuickTaskPopover()"
        >
          + Task
        </button>
      </div>

      <!-- Left Sidebar: Calm, Collapsible, Grouped Projects Drawer -->
      <aside
        class="timeline-left-sidebar"
        :class="{
          'mobile-open': showMobileProjectsSidebar,
          'desktop-collapsed': isSidebarCollapsed,
        }"
        aria-label="Projects Sidebar"
      >
        <div class="sidebar-top-row">
          <span class="sidebar-heading">Workspace</span>
          <div class="sidebar-top-actions">
            <button
              type="button"
              class="btn-orange-mini"
              @click="toggleTimelineAddProject"
            >
              {{ showTimelineAddProject ? "Cancel" : "+ Project" }}
            </button>
            <button
              type="button"
              class="sidebar-collapse-btn"
              title="Collapse sidebar"
              aria-label="Collapse sidebar"
              @click="isSidebarCollapsed = true"
            >
              ‹
            </button>
          </div>
        </div>

        <form
          v-if="showTimelineAddProject"
          class="sidebar-add-proj-form"
          @submit.prevent="createNewProject(true)"
        >
          <input
            v-model="newProject.name"
            type="text"
            class="input-minimal"
            placeholder="Project title…"
            required
          />
          <input
            v-model="newProject.area"
            type="text"
            list="project-area-suggestions"
            class="input-minimal"
            placeholder="Folder / area (optional)…"
          />
          <div class="sidebar-form-dates">
            <label class="date-mini">
              <span>Start</span>
              <input v-model="newProject.start_date" type="date" />
            </label>
            <label class="date-mini">
              <span>Target</span>
              <input v-model="newProject.target_date" type="date" />
            </label>
          </div>
          <div class="swatch-row">
            <span class="swatch-label">Tone</span>
            <input
              v-model="newProject.color"
              type="color"
              class="color-picker-mini"
            />
            <button
              v-for="sw in COLOR_SWATCHES"
              :key="sw"
              type="button"
              class="color-swatch-dot"
              :class="{ active: newProject.color === sw }"
              :style="{ backgroundColor: sw }"
              @click="newProject.color = sw"
            />
          </div>
          <button type="submit" class="btn-ink-primary">
            Create &amp; Pin
          </button>
        </form>

        <!-- Search & Folder Filter -->
        <div class="sidebar-filter-controls">
          <input
            v-model="sidebarSearchQuery"
            type="text"
            class="sidebar-search-input"
            placeholder="Filter projects…"
          />
          <select
            v-if="projectAreas.length > 0"
            v-model="selectedAreaFilter"
            class="sidebar-area-select"
            aria-label="Filter projects by folder"
          >
            <option value="all">All folders</option>
            <option v-for="ar in projectAreas" :key="ar" :value="ar">
              {{ ar }}
            </option>
            <option value="__none__">Uncategorized</option>
          </select>
        </div>

        <!-- Overdue Tasks Banner (Visible when overdue items exist) -->
        <div
          v-if="totalOverdueTasksCount > 0"
          class="sidebar-overdue-alert clickable-card"
          :class="{ active: taskFilterMode === 'overdue' }"
          title="Click to jump to overdue tasks across projects and inbox"
          @click="enterOverdueMode(true)"
        >
          <div class="overdue-alert-left">
            <span class="overdue-alert-icon">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </span>
            <strong class="overdue-alert-title">{{ totalOverdueTasksCount }} Overdue</strong>
          </div>
          <span class="overdue-count-pill">{{ totalOverdueTasksCount }}</span>
        </div>

        <div class="sidebar-scroll-list">
          <!-- Standalone One-Off Tasks / Inbox Row -->
          <div
            class="sidebar-flat-row is-inbox-row"
            :class="{ active: selectedProjectId === 0 }"
            title="Standalone tasks not tied to a project"
            @click="openProjectDrawer(0, 'subtasks')"
          >
            <span class="sidebar-dot" style="background-color: var(--danger)"></span>
            <span class="sidebar-row-name">Inbox (One-Off)</span>
            <span class="sidebar-row-count">
              {{ standalonePendingCount }}/{{ standaloneTasks.length }}
            </span>
          </div>

          <!-- Collapsible Project Sections -->
          <template
            v-for="sec in [
              { key: 'pinned', label: 'Pinned', items: sidebarGroups.pinned },
              { key: 'active', label: 'Active', items: sidebarGroups.active },
              { key: 'later', label: 'Planned & On Hold', items: sidebarGroups.later },
              { key: 'completed', label: 'Completed', items: sidebarGroups.completed },
            ]"
            :key="sec.key"
          >
            <div v-if="sec.items.length > 0" class="sidebar-section">
              <button
                type="button"
                class="sidebar-section-head"
                @click="sidebarSectionsOpen[sec.key] = !sidebarSectionsOpen[sec.key]"
              >
                <span class="sidebar-section-chevron">
                  {{ sidebarSectionsOpen[sec.key] ? "▾" : "▸" }}
                </span>
                <span class="sidebar-section-title">{{ sec.label }}</span>
                <span class="sidebar-section-count">{{ sec.items.length }}</span>
              </button>

              <div v-if="sidebarSectionsOpen[sec.key]" class="sidebar-section-rows">
                <div
                  v-for="proj in sec.items"
                  :key="proj.id"
                  class="sidebar-flat-row"
                  :class="{
                    active: selectedProjectId === proj.id,
                    'is-pinned-row': proj.is_pinned,
                    'is-completed-project-row': isProjectCompleted(proj),
                  }"
                  @click="openProjectDrawer(proj.id, 'subtasks')"
                >
                  <span
                    class="sidebar-dot"
                    :style="{ backgroundColor: proj.color || '#c2410c' }"
                  />
                  <span
                    class="sidebar-row-name"
                    :class="{ 'strikethrough-done': isProjectCompleted(proj) }"
                    :title="proj.name"
                  >
                    {{ proj.name }}
                  </span>
                  <span
                    v-if="proj.overdue_tasks > 0"
                    class="sidebar-overdue-dot"
                    :title="`${proj.overdue_tasks} overdue`"
                  />
                  <span class="sidebar-row-count">
                    {{ (projectTasksMap[proj.id] || []).length }}
                  </span>
                  <div class="sidebar-row-hover-actions" @click.stop>
                    <button
                      type="button"
                      class="sidebar-mini-action"
                      :class="{ active: proj.is_pinned }"
                      :title="proj.is_pinned ? 'Unpin from calendar' : 'Pin to calendar'"
                      @click="updateProjectFields(proj, { is_pinned: !proj.is_pinned })"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 17v5" />
                        <path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z" />
                      </svg>
                    </button>
                    <button
                      type="button"
                      class="sidebar-mini-action"
                      :class="{ active: isProjectSubtasksVisible(proj.id) }"
                      :title="isProjectSubtasksVisible(proj.id) ? 'Hide tasks on calendar' : 'Show tasks on calendar'"
                      @click="toggleProjectSubtasksVisibility(proj.id)"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="8" y1="6" x2="21" y2="6" />
                        <line x1="8" y1="12" x2="21" y2="12" />
                        <line x1="8" y1="18" x2="21" y2="18" />
                        <line x1="3" y1="6" x2="3.01" y2="6" />
                        <line x1="3" y1="12" x2="3.01" y2="12" />
                        <line x1="3" y1="18" x2="3.01" y2="18" />
                      </svg>
                    </button>
                    <button
                      type="button"
                      class="sidebar-mini-action"
                      title="Archive project"
                      @click="archiveProject(proj)"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="21 8 21 21 3 21 3 8" />
                        <rect x="1" y="3" width="22" height="5" />
                        <line x1="10" y1="12" x2="14" y2="12" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>

        <footer class="sidebar-footer">
          <button
            type="button"
            class="sidebar-archive-btn"
            @click="showArchiveModal = true"
          >
            <span>Archive Vault</span>
            <span class="sidebar-section-count">{{ archivedProjects.length }}</span>
          </button>
        </footer>
      </aside>

      <!-- Calendar Surface -->
      <section class="calendar-timeline-surface">
        <!-- Calendar Toolbar -->
        <header class="calendar-toolbar">
          <div class="calendar-nav">
            <button
              v-if="isSidebarCollapsed"
              type="button"
              class="nav-step-btn"
              title="Show sidebar"
              aria-label="Show sidebar"
              @click="isSidebarCollapsed = false"
            >
              ›
            </button>
            <button
              type="button"
              class="btn-today-jump"
              title="Jump to Today (T)"
              @click="jumpToToday"
            >
              Today
            </button>
            <div class="calendar-step-pair">
              <button
                type="button"
                class="nav-step-btn"
                aria-label="Previous period"
                @click="stepCalendar(-1)"
              >
                ‹
              </button>
              <button
                type="button"
                class="nav-step-btn"
                aria-label="Next period"
                @click="stepCalendar(1)"
              >
                ›
              </button>
            </div>
            <h2 class="calendar-current-label">
              {{
                calendarScaleMode === "year"
                  ? `${selectedYear}`
                  : calendarScaleMode === "day"
                  ? dayViewSpec.rangeText
                  : calendarScaleMode === "week"
                  ? `${focusedWeekSpec.rangeText}`
                  : `${monthlyWeeksSpec.monthName} ${selectedYear}`
              }}
            </h2>
          </div>

          <div class="scale-Right-controls">
            <!-- Subtask Filter: All | Active | Overdue | Done -->
            <div class="segmented-scale" aria-label="Task Status Filter">
              <button
                type="button"
                class="scale-btn"
                :class="{ active: taskFilterMode === 'all' }"
                @click="taskFilterMode = 'all'"
              >
                All
              </button>
              <button
                type="button"
                class="scale-btn"
                :class="{ active: taskFilterMode === 'active' }"
                @click="taskFilterMode = 'active'"
              >
                Active
              </button>
              <button
                type="button"
                class="scale-btn scale-btn-overdue"
                :class="{ active: taskFilterMode === 'overdue' }"
                @click="enterOverdueMode(false)"
              >
                Overdue
                <span v-if="totalOverdueTasksCount > 0" class="overdue-bubble">
                  {{ totalOverdueTasksCount }}
                </span>
              </button>
              <button
                type="button"
                class="scale-btn"
                :class="{ active: taskFilterMode === 'done' }"
                @click="taskFilterMode = 'done'"
              >
                Done
              </button>
            </div>

            <!-- Scale Mode: Day | Week | Month | Year -->
            <div class="segmented-scale" aria-label="Calendar Scale">
              <button
                type="button"
                class="scale-btn"
                :class="{ active: calendarScaleMode === 'day' }"
                @click="switchToDayMode()"
              >
                Day
              </button>
              <button
                type="button"
                class="scale-btn"
                :class="{ active: calendarScaleMode === 'week' }"
                @click="switchToWeekMode"
              >
                Week
              </button>
              <button
                type="button"
                class="scale-btn"
                :class="{ active: calendarScaleMode === 'month' }"
                @click="calendarScaleMode = 'month'"
              >
                Month
              </button>
              <button
                type="button"
                class="scale-btn"
                :class="{ active: calendarScaleMode === 'year' }"
                @click="calendarScaleMode = 'year'"
              >
                Year
              </button>
            </div>

            <!-- Display Options Dropdown -->
            <div ref="displayMenuRef" class="display-menu-wrap">
              <button
                type="button"
                class="scale-btn display-menu-trigger"
                :class="{ active: showDisplayMenu }"
                @click.stop="showDisplayMenu = !showDisplayMenu"
              >
                Display ▾
              </button>

              <div v-if="showDisplayMenu" class="display-popover-menu" @click.stop>
                <button
                  type="button"
                  class="display-menu-row"
                  @click="
                    calendarProjectDisplayMode =
                      calendarProjectDisplayMode === 'milestones' ? 'all' : 'milestones'
                  "
                >
                  <span>Milestone pins only</span>
                  <span class="display-menu-state">
                    {{ calendarProjectDisplayMode === "milestones" ? "On" : "Off" }}
                  </span>
                </button>
                <button
                  type="button"
                  class="display-menu-row"
                  @click="
                    visibleTimelineSubtaskProjectIds.size > 0
                      ? collapseAllTimelineSubtasks()
                      : expandAllTimelineSubtasks()
                  "
                >
                  <span>Show project subtasks</span>
                  <span class="display-menu-state">
                    {{ visibleTimelineSubtaskProjectIds.size > 0 ? "On" : "Off" }}
                  </span>
                </button>

                <div v-if="calendarScaleMode === 'month'" class="display-month-jump">
                  <span class="display-menu-section-label">Jump to month</span>
                  <div class="display-month-grid">
                    <button
                      v-for="m in 12"
                      :key="m"
                      type="button"
                      class="month-pill"
                      :class="{ active: selectedMonth === m }"
                      @click="
                        selectedMonth = m;
                        showDisplayMenu = false;
                      "
                    >
                      {{
                        [
                          "Jan",
                          "Feb",
                          "Mar",
                          "Apr",
                          "May",
                          "Jun",
                          "Jul",
                          "Aug",
                          "Sep",
                          "Oct",
                          "Nov",
                          "Dec",
                        ][m - 1]
                      }}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <button
              type="button"
              class="btn-ink-primary toolbar-add-task-btn"
              title="Quick create task (N)"
              @click="openQuickTaskPopover()"
            >
              + Task
            </button>
          </div>
        </header>

        <!-- Prev / Next Overdue Task Navigator Bar (Visible in Overdue mode) -->
        <div
          v-if="taskFilterMode === 'overdue'"
          class="overdue-navigator-bar"
          role="region"
          aria-label="Overdue task navigation"
        >
          <template v-if="activeOverdueTask">
            <div class="overdue-nav-summary">
              <span class="overdue-nav-counter">
                {{ Math.min(activeOverdueIndex, overdueTasksList.length - 1) + 1 }} / {{ overdueTasksList.length }}
              </span>
              <button
                type="button"
                class="overdue-nav-current-btn"
                title="Jump calendar to this overdue task's due date"
                @click="jumpToOverdueTaskAt(activeOverdueIndex)"
              >
                <span
                  class="overdue-nav-dot"
                  :style="{ backgroundColor: activeOverdueTask.displayColor }"
                ></span>
                <strong class="overdue-nav-task-title">{{ activeOverdueTask.title }}</strong>
                <span class="overdue-nav-meta">
                  {{ activeOverdueTask.projectName }} · Due {{ formatEditorialDate(activeOverdueTask.due_date).short }}
                </span>
              </button>
            </div>
            <div class="overdue-nav-actions">
              <button
                type="button"
                class="overdue-nav-step-btn"
                title="Reschedule this task to Today"
                @click="moveOverdueTaskToToday(activeOverdueTask)"
              >
                Move to Today
              </button>
              <button
                type="button"
                class="overdue-nav-step-btn"
                :disabled="overdueTasksList.length <= 1"
                title="Jump to previous overdue task"
                @click="stepOverdueTask(-1)"
              >
                ‹ Prev overdue
              </button>
              <button
                type="button"
                class="overdue-nav-step-btn"
                :disabled="overdueTasksList.length <= 1"
                title="Jump to next overdue task"
                @click="stepOverdueTask(1)"
              >
                Next overdue ›
              </button>
              <button
                type="button"
                class="overdue-nav-open-btn"
                title="Open task drawer"
                @click="openProjectDrawer(activeOverdueTask.project_id ?? 0, 'subtasks')"
              >
                Open
              </button>
              <button
                type="button"
                class="overdue-nav-close-btn"
                aria-label="Exit overdue view"
                title="Return to all tasks"
                @click="exitOverdueFilter"
              >
                ✕
              </button>
            </div>
          </template>
          <template v-else>
            <span class="overdue-nav-empty-text">
              All caught up — no overdue tasks remaining.
            </span>
            <button
              type="button"
              class="overdue-nav-step-btn"
              @click="exitOverdueFilter"
            >
              Show All Tasks
            </button>
          </template>
        </div>

        <!-- ===============================================================
             MODE A: MONTHLY VIEW — 1 ROW PER WEEK (Click any date for Journal!)
             =============================================================== -->
        <div
          v-if="calendarScaleMode === 'month'"
          class="monthly-weeks-scroll-wrapper"
        >
          <div class="monthly-weeks-container">
            <div class="weekday-header-row">
              <div class="week-label-col">Week</div>
              <div
                v-for="dow in WEEKDAY_SHORT"
                :key="dow"
                class="weekday-col-head"
              >
                {{ dow }}
              </div>
            </div>

            <div
              v-for="week in monthlyWeeksSpec.weeks"
              :key="week.weekNumber"
              class="week-calendar-row"
            >
              <div class="week-side-cell">
                <span class="week-badge">W{{ String(week.weekNumber).padStart(2, "0") }}</span>
                <span class="week-range-sub">
                  {{ week.days[0].monthShort }} {{ week.days[0].dayNum }} –
                  {{ week.days[6].monthShort }} {{ week.days[6].dayNum }}
                </span>
              </div>

              <div class="week-seven-col-area">
                <!-- Interactive Day Header Strip: Click date to open Journal, or + to add task -->
                <div class="week-day-numbers-strip">
                  <div
                    v-for="day in week.days"
                    :key="day.iso"
                    role="button"
                    tabindex="0"
                    class="week-day-num-cell"
                    :data-calendar-day-iso="day.iso"
                    :class="{
                      'outside-month': !day.inMonth,
                      'is-today-cell': day.isToday,
                      'has-journal-entry': day.hasJournal,
                      'is-selected-journal-day':
                        isJournalDrawerOpen && selectedJournalDate === day.iso,
                      'is-focused-overdue-day':
                        taskFilterMode === 'overdue' && focusedOverdueDateIso === day.iso,
                    }"
                    :title="`Click to open journal for ${day.iso}`"
                    @click="openDailyJournalForDate(day.iso, true)"
                    @keydown.enter.prevent="openDailyJournalForDate(day.iso, true)"
                  >
                    <div class="day-cell-top-row">
                      <span
                        class="day-number-pill"
                        :class="{ 'is-today-pill': day.isToday }"
                      >
                        {{ day.dayNum }}
                        <small v-if="!day.inMonth || day.dayNum === 1" class="day-month-hint">
                          {{ day.monthShort }}
                        </small>
                      </span>
                      <div class="day-cell-top-right">
                        <span v-if="day.hasJournal" class="day-journal-indicator" :title="day.journalTitle || 'Journal'">
                          {{ day.journalTitle || "Note" }}
                        </span>
                        <span v-else class="day-journal-hover-hint">
                          Note
                        </span>
                        <button
                          type="button"
                          class="day-quick-add-btn"
                          :title="`Add task on ${day.iso}`"
                          @click.stop="
                            openQuickTaskPopover({
                              start_date: day.iso,
                              due_date: day.iso,
                            })
                          "
                        >
                          +
                        </button>
                      </div>
                    </div>
                    <!-- Calendar Day Placed Stickers -->
                    <div v-if="getStickersForDate(day.iso).length" class="day-stickers-layer">
                      <span
                        v-for="stk in getStickersForDate(day.iso)"
                        :key="stk.id"
                        class="calendar-day-sticker"
                        :style="{ transform: `rotate(${stk.rotation_deg}deg) scale(${stk.scale / 100})` }"
                        :title="`${stk.sticker_name} (Click to remove)`"
                        @click.stop="handleRemovePlacement(stk.id)"
                      >
                        <img :src="stk.image_url" :alt="stk.sticker_name" class="day-sticker-img" />
                      </span>
                    </div>
                    <p v-if="day.hasJournal && day.journalSnippet" class="day-journal-snippet">
                      {{ day.journalSnippet }}
                    </p>
                  </div>
                </div>

                <div class="week-items-stack-grid">
                  <div class="week-bg-guides">
                    <div
                      v-for="day in week.days"
                      :key="day.iso"
                      class="week-bg-col"
                      :class="{
                        'is-today-col': day.isToday,
                        'is-drag-creating-day': isMonthCellDragHighlighted(week, day.iso),
                      }"
                      title="Click or drag across days to create a task"
                      @pointerdown="startMonthDayDragCreate($event, week, day.iso)"
                      @pointerenter="updateMonthDayDragCreate(week, day.iso, $event)"
                    />
                  </div>

                  <div
                    v-for="item in week.items"
                    :key="item.uid"
                    class="week-item-card clickable-card"
                    :data-overdue-task-id="
                      item.taskId &&
                      focusedOverdueDateIso &&
                      week.weekStartIso <= focusedOverdueDateIso &&
                      focusedOverdueDateIso <= week.weekEndIso
                        ? item.taskId
                        : undefined
                    "
                    :class="{
                      'is-done-card': item.status === 'done',
                      'is-project-bar': item.kind === 'project',
                      'is-draggable-project': item.kind === 'project',
                      'is-subtask-bar': item.kind === 'task',
                      'is-draggable-task': item.kind === 'task',
                      'is-overdue-card': item.isOverdue,
                      'is-focused-overdue-card':
                        taskFilterMode === 'overdue' &&
                        item.taskId &&
                        focusedOverdueTaskId === item.taskId,
                      'is-milestone-card': item.isMilestone,
                      'is-currently-dragged':
                        activeTimelineDrag &&
                        ((activeTimelineDrag.isTask && activeTimelineDrag.taskId === item.taskId) ||
                         (!activeTimelineDrag.isTask && activeTimelineDrag.projectId === item.projectId)),
                    }"
                    :style="
                      getCustomColorCardStyle(item.color, {
                        gridColumn: `${item.startCol} / span ${item.spanCols}`,
                        gridRow: item.trackRow,
                      })
                    "
                    @pointerdown="
                      item.kind === 'project'
                        ? startTimelineDrag($event, item.projectId, 'move', 'month')
                        : startTimelineDrag($event, item.projectId, 'move', 'month', item.taskId)
                    "
                    @click="handleTimelineCardClick(item)"
                  >
                    <!-- Left Resize Handle: Project or Subtask -->
                    <div
                      class="timeline-resize-handle handle-left"
                      :title="item.kind === 'project' ? 'Drag to extend or shorten project start date' : 'Drag to stretch subtask start date'"
                      @pointerdown.stop.prevent="
                        item.kind === 'project'
                          ? startTimelineDrag(
                              $event,
                              item.projectId,
                              'resize-start',
                              'month'
                            )
                          : startTimelineDrag(
                              $event,
                              item.projectId,
                              'resize-start',
                              'month',
                              item.taskId
                            )
                      "
                    />
                    <div class="week-item-main">
                      <template v-if="item.kind === 'project'">
                        <button
                          type="button"
                          class="subtask-check-btn"
                          :class="{ checked: item.status === 'done' }"
                          :style="
                            item.status === 'done'
                              ? {
                                  backgroundColor: item.color,
                                  borderColor: item.color,
                                }
                              : { borderColor: item.color }
                          "
                          :title="
                            item.status === 'done'
                              ? 'Mark project active'
                              : 'Mark project done'
                          "
                          @click.stop="toggleProjectDoneStatusById(item.projectId)"
                        >
                          <svg
                            v-if="item.status === 'done'"
                            width="11"
                            height="11"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="3"
                          >
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        </button>
                        <span
                          class="color-badge-mono"
                          :style="{ color: item.color, borderColor: `${item.color}44` }"
                        >
                          {{ item.code }}
                        </span>
                      </template>

                      <template v-else-if="item.kind === 'milestone'">
                        <span class="milestone-diamond-badge" :style="{ backgroundColor: item.color }">
                          ◆
                        </span>
                      </template>
                      <template v-else>
                        <button
                          type="button"
                          class="subtask-check-btn"
                          :class="{ checked: item.status === 'done' }"
                          :style="
                            item.status === 'done'
                              ? {
                                  backgroundColor: item.color,
                                  borderColor: item.color,
                                }
                              : { borderColor: item.color }
                          "
                          title="Toggle subtask done"
                          @click.stop="
                            toggleSubtaskStatus(item.projectId, item.taskId)
                          "
                        >
                          <svg
                            v-if="item.status === 'done'"
                            width="11"
                            height="11"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="3"
                          >
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        </button>
                        <span
                          v-if="item.code"
                          class="color-badge-mono"
                          :style="{ color: item.color, borderColor: `${item.color}44` }"
                        >
                          {{ item.code }}
                        </span>
                      </template>

                      <span v-if="item.timePrefix" class="task-time-badge">
                        {{ item.timePrefix }}
                      </span>

                      <strong
                        class="week-item-title"
                        :class="{
                          'strikethrough-done': item.status === 'done',
                        }"
                      >
                        {{ item.title }}
                      </strong>

                      <span v-if="item.isOverdue" class="overdue-tag-pill">
                        Overdue
                      </span>

                      <!-- Subtasks toggle button pill right on the project card -->
                      <button
                        v-if="item.kind === 'project' && (projectTasksMap[item.projectId] || []).length > 0"
                        type="button"
                        class="subtasks-toggle-badge"
                        :class="{ 'is-expanded': isProjectSubtasksVisible(item.projectId) }"
                        :title="isProjectSubtasksVisible(item.projectId) ? 'Click to hide subtasks on timeline' : 'Click to show subtasks on timeline'"
                        @click.stop="toggleProjectSubtasksVisibility(item.projectId)"
                      >
                        {{ isProjectSubtasksVisible(item.projectId) ? '▼' : '▶' }}
                        {{ (projectTasksMap[item.projectId] || []).length }}
                      </button>

                      <!-- Quick drawer button to view/edit notes -->
                      <button
                        v-if="item.kind === 'project'"
                        type="button"
                        class="card-drawer-open-btn"
                        title="Open project notes and drawer"
                        @click.stop="openProjectDrawer(item.projectId, 'subtasks')"
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                      </button>
                    </div>

                    <div class="week-item-meta">
                      <span
                        v-if="item.kind === 'task'"
                        class="task-proj-origin"
                        :style="{ color: item.color }"
                      >
                        {{ item.projectName }}
                      </span>
                      <span class="item-dates-label">{{ item.dateRangeText }}</span>
                    </div>

                    <!-- Right Resize Handle: Project or Subtask -->
                    <div
                      class="timeline-resize-handle handle-right"
                      :title="item.kind === 'project' ? 'Drag to extend or shorten project target date' : 'Drag to stretch subtask due date'"
                      @pointerdown.stop.prevent="
                        item.kind === 'project'
                          ? startTimelineDrag(
                              $event,
                              item.projectId,
                              'resize-end',
                              'month'
                            )
                          : startTimelineDrag(
                              $event,
                              item.projectId,
                              'resize-end',
                              'month',
                              item.taskId
                            )
                      "
                    />
                  </div>

                  <div v-if="week.items.length === 0" class="week-empty-spacer" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ===============================================================
             MODE B: DAY & TIMED WEEK VIEWS (Hourly Time-Blocking Grid)
             =============================================================== -->
        <CalendarTimeGrid
          v-else-if="calendarScaleMode === 'day' || calendarScaleMode === 'week'"
          :days="calendarScaleMode === 'day' ? dayViewSpec.days : focusedWeekSpec.days"
          :all-day-items="calendarScaleMode === 'day' ? dayViewSpec.allDayItems : focusedWeekAllDayItems"
          :timed-tasks-by-date="timedTasksByDate"
          :today-iso="todayIso"
          :task-filter-mode="taskFilterMode"
          :focused-overdue-task-id="focusedOverdueTaskId"
          :focused-overdue-date-iso="focusedOverdueDateIso"
          :project-tasks-map="projectTasksMap"
          :visible-subtask-project-ids="visibleTimelineSubtaskProjectIds"
          :active-timeline-drag="activeTimelineDrag"
          @quick-create="openQuickTaskPopover($event)"
          @open-journal="openDailyJournalForDate($event, true)"
          @card-click="handleTimelineCardClick($event)"
          @toggle-task="toggleSubtaskStatus($event.projectId, $event.taskId)"
          @toggle-project-done="toggleProjectDoneStatusById($event)"
          @toggle-project-subtasks="toggleProjectSubtasksVisibility($event)"
          @open-project-drawer="openProjectDrawer($event, 'subtasks')"
          @update-timed-task="handleUpdateTimedTask($event)"
          @start-allday-drag="
            startTimelineDrag(
              $event.event,
              $event.projectId,
              $event.type,
              calendarScaleMode,
              $event.taskId
            )
          "
        />

        <!-- ===============================================================
             MODE C: YEAR VIEW — 12 MONTH COLUMNS (JAN .. DEC)
             =============================================================== -->
        <div v-else class="year-view-scroll-wrapper">
          <div class="year-view-container">
            <div class="year-grid-row year-header-row">
              <div class="cal-corner-cell">Pinned Project</div>
              <div
                v-for="col in yearCalendarSpec.columns"
                :key="col.key"
                class="cal-col-header clickable"
                :title="`Click to open ${col.label} ${selectedYear} month view`"
                @click="drillIntoMonth(col)"
              >
                <span class="cal-col-main">{{ col.label }}</span>
                <span class="cal-col-sub">{{ col.subLabel }}</span>
              </div>
            </div>

            <div
              v-for="(proj, pIdx) in timelineSwimlaneProjects"
              :key="proj.id"
              class="year-project-swimlane"
            >
              <div
                class="cal-project-cell clickable-card"
                @click="openProjectDrawer(proj.id, 'subtasks')"
              >
                <div class="cal-proj-title">
                  {{ proj.name }}
                  <span
                    v-if="!proj.is_pinned"
                    class="unpinned-subtasks-badge"
                    title="Project bar is unpinned; only subtasks are displayed"
                  >
                    (Subtasks Only)
                  </span>
                </div>
                <div class="cal-proj-dates">
                  {{ proj.start_date }} → {{ proj.target_date }}
                </div>
                <button
                  type="button"
                  class="note-link-btn"
                  @click.stop="toggleProjectSubtasksVisibility(proj.id)"
                >
                  {{ isProjectSubtasksVisible(proj.id) ? '▼' : '▶' }}
                  {{ (projectTasksMap[proj.id] || []).length }} subtasks
                </button>
              </div>

              <div class="year-twelve-months-grid">
                <div class="year-bg-guides">
                  <div v-for="m in 12" :key="m" class="year-bg-col" />
                </div>

                <!-- Row 1: Project Span Bar (ONLY rendered if project is actually pinned!) -->
                <div
                  v-if="proj.is_pinned && (taskFilterMode !== 'done' || isProjectCompleted(proj))"
                  class="week-item-card clickable-card is-project-bar is-draggable-project"
                  :class="{
                    'is-done-card': isProjectCompleted(proj),
                    'is-currently-dragged':
                      activeTimelineDrag &&
                      !activeTimelineDrag.isTask &&
                      activeTimelineDrag.projectId === proj.id,
                  }"
                  :style="getYearProjectGridStyle(proj)"
                  @pointerdown="
                    startTimelineDrag($event, proj.id, 'move', 'year')
                  "
                  @click="
                    !wasTimelineDragging &&
                      toggleProjectSubtasksVisibility(proj.id)
                  "
                >
                  <!-- Left Resize Handle: shorten/lengthen start date in Year View -->
                  <div
                    class="timeline-resize-handle handle-left"
                    title="Drag to extend or shorten start date"
                    @pointerdown.stop.prevent="
                      startTimelineDrag(
                        $event,
                        proj.id,
                        'resize-start',
                        'year'
                      )
                    "
                  />

                  <div class="week-item-main">
                    <button
                      type="button"
                      class="subtask-check-btn"
                      :class="{ checked: isProjectCompleted(proj) }"
                      :style="
                        isProjectCompleted(proj)
                          ? {
                              backgroundColor: proj.color || '#b85423',
                              borderColor: proj.color || '#b85423',
                            }
                          : { borderColor: proj.color || '#b85423' }
                      "
                      :title="
                        isProjectCompleted(proj)
                          ? 'Mark project active'
                          : 'Mark project done (remove from calendar)'
                      "
                      @click.stop="toggleProjectDoneStatus(proj)"
                    >
                      <svg
                        v-if="isProjectCompleted(proj)"
                        width="11"
                        height="11"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="3"
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    </button>
                    <span
                      class="color-badge-solid"
                      :style="{ backgroundColor: proj.color || '#b85423' }"
                    >
                      Project
                    </span>
                    <strong
                      class="week-item-title"
                      :class="{ 'strikethrough-done': isProjectCompleted(proj) }"
                    >
                      {{ proj.name }}
                    </strong>

                    <!-- Subtasks toggle button pill in Year View -->
                    <button
                      v-if="(projectTasksMap[proj.id] || []).length > 0"
                      type="button"
                      class="subtasks-toggle-badge"
                      :class="{ 'is-expanded': isProjectSubtasksVisible(proj.id) }"
                      :title="isProjectSubtasksVisible(proj.id) ? 'Click to hide subtasks on timeline' : 'Click to show subtasks on timeline'"
                      @click.stop="toggleProjectSubtasksVisibility(proj.id)"
                    >
                      {{ isProjectSubtasksVisible(proj.id) ? '▼' : '▶' }}
                      {{ (projectTasksMap[proj.id] || []).length }} subtasks
                    </button>

                    <!-- Drawer open button -->
                    <button
                      type="button"
                      class="card-drawer-open-btn"
                      title="Open project notes and drawer"
                      @click.stop="openProjectDrawer(proj.id, 'subtasks')"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                      </svg>
                    </button>
                  </div>
                  <div class="week-item-meta">
                    <span class="item-dates-label">
                      {{ proj.start_date }} → {{ proj.target_date }}
                    </span>
                  </div>

                  <!-- Right Resize Handle: shorten/lengthen target date in Year View -->
                  <div
                    class="timeline-resize-handle handle-right"
                    title="Drag to extend or shorten target date"
                    @pointerdown.stop.prevent="
                      startTimelineDrag(
                        $event,
                        proj.id,
                        'resize-end',
                        'year'
                      )
                    "
                  />
                </div>
              </div>

              <!-- Aligned Subtask Swimrows (Readable left label + 12-month bar on right) -->
              <div
                v-for="task in getYearProjectTaskRows(proj.id, pIdx)"
                :key="task.id"
                class="year-subtask-swimrow"
              >
                <div
                  class="year-subtask-label-cell"
                  :title="`${task.code} · ${task.title} (${task.start_date} → ${task.due_date})`"
                  @click="openProjectDrawer(proj.id, 'subtasks')"
                >
                  <button
                    type="button"
                    class="subtask-check-btn"
                    :class="{ checked: task.status === 'done' }"
                    :style="
                      task.status === 'done'
                        ? {
                            backgroundColor: task.color || '#2c666e',
                            borderColor: task.color || '#2c666e',
                          }
                        : { borderColor: task.color || '#2c666e' }
                    "
                    @click.stop="toggleSubtaskStatus(proj.id, task.id)"
                  >
                    <svg
                      v-if="task.status === 'done'"
                      width="11"
                      height="11"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="3"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </button>
                  <span
                    class="color-badge-mono"
                    :style="{
                      color: task.color || '#2c666e',
                      borderColor: `${task.color || '#2c666e'}44`,
                    }"
                  >
                    {{ task.code }}
                  </span>
                  <div class="year-subtask-label-text">
                    <span
                      class="year-subtask-label-title"
                      :class="{ 'strikethrough-done': task.status === 'done' }"
                    >
                      {{ task.title }}
                    </span>
                    <span class="year-subtask-label-dates">
                      {{ task.start_date }} → {{ task.due_date }}
                    </span>
                  </div>
                </div>

                <div class="year-twelve-months-grid is-subtask-row">
                  <div class="year-bg-guides">
                    <div v-for="m in 12" :key="m" class="year-bg-col" />
                  </div>

                  <div
                    class="week-item-card clickable-card is-subtask-bar is-draggable-task"
                    :class="{
                      'is-done-card': task.status === 'done',
                      'is-currently-dragged':
                        activeTimelineDrag &&
                        activeTimelineDrag.isTask &&
                        activeTimelineDrag.taskId === task.id,
                    }"
                    :style="{ ...task.gridStyle, gridRow: 1 }"
                    :title="`${task.code} · ${task.title} (${task.start_date} → ${task.due_date})`"
                    @pointerdown="
                      startTimelineDrag($event, proj.id, 'move', 'year', task.id)
                    "
                    @click="!wasTimelineDragging && openProjectDrawer(proj.id, 'subtasks')"
                  >
                    <!-- Left Resize Handle for Subtask in Year View -->
                    <div
                      class="timeline-resize-handle handle-left"
                      title="Drag to extend or shorten subtask start date in Year View"
                      @pointerdown.stop.prevent="
                        startTimelineDrag(
                          $event,
                          proj.id,
                          'resize-start',
                          'year',
                          task.id
                        )
                      "
                    />

                    <div class="week-item-main">
                      <span
                        class="color-badge-mono"
                        :style="{
                          color: task.color || '#2c666e',
                          borderColor: `${task.color || '#2c666e'}44`,
                        }"
                      >
                        {{ task.code }}
                      </span>
                      <strong
                        class="week-item-title"
                        :class="{ 'strikethrough-done': task.status === 'done' }"
                      >
                        {{ task.title }}
                      </strong>
                    </div>
                    <div class="week-item-meta">
                      <span class="item-dates-label">
                        {{ task.start_date }} → {{ task.due_date }}
                      </span>
                    </div>

                    <!-- Right Resize Handle for Subtask in Year View -->
                    <div
                      class="timeline-resize-handle handle-right"
                      title="Drag to extend or shorten subtask due date in Year View"
                      @pointerdown.stop.prevent="
                        startTimelineDrag(
                          $event,
                          proj.id,
                          'resize-end',
                          'year',
                          task.id
                        )
                      "
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Floating real-time drag indicator badge -->
        <div
          v-if="activeTimelineDrag && activeTimelineDrag.hasMoved"
          class="timeline-drag-badge-indicator"
        >
          <div class="drag-badge-pill">
            <span class="drag-mode-tag">{{ dragModeLabel }}</span>
            <strong class="drag-proj-name">
              {{ activeTimelineDrag.isTask ? activeTimelineDrag.taskTitle : activeTimelineDrag.projectName }}
            </strong>
            <span class="drag-date-range">
              {{ activeTimelineDrag.currentStartDate }} → {{ activeTimelineDrag.currentTargetDate }}
            </span>
            <span class="drag-days-count">
              ({{ computedDragDays }} {{ computedDragDays === 1 ? 'day' : 'days' }})
            </span>
          </div>
        </div>
      </section>
    </main>

    <!-- =====================================================================
         SLIDE-OVER DRAWER 1: DAILY JOURNAL SHEET (Opens when clicking any date in Month View)
         ===================================================================== -->
    <div
      v-if="isJournalDrawerOpen"
      class="slideover-backdrop"
      @click.self="closeJournalDrawer"
    >
      <aside
        class="slideover-drawer journal-slideover"
        aria-label="Daily Journal Entry Drawer"
      >
        <header class="slideover-header">
          <div class="journal-drawer-title-block">
            <span class="journal-kicker">{{ formattedJournalHeading.full }}</span>
            <div class="journal-drawer-date-row">
              <button
                type="button"
                class="nav-step-btn"
                title="Previous day"
                @click="stepJournalDate(-1)"
              >
                ‹
              </button>
              <input
                v-model="journalDraftTitle"
                type="text"
                class="journal-drawer-title-input editorial-serif-drawer-title"
                :placeholder="formattedJournalHeading.full"
                title="Click to edit journal title"
                @blur="saveDailyJournalEntry"
              />
              <button
                type="button"
                class="nav-step-btn"
                title="Next day"
                @click="stepJournalDate(1)"
              >
                ›
              </button>
            </div>
          </div>
          <button
            type="button"
            class="close-drawer-btn"
            aria-label="Close journal drawer"
            @click="closeJournalDrawer"
          >
            ✕
          </button>
        </header>

        <!-- Action Bar: Camera Handwritten OCR + Preview + Save -->
        <div class="journal-drawer-toolbar">
          <label class="btn-ocr-scanner">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </svg>
            <span>Scan Handwritten Journal (OCR)</span>
            <input
              type="file"
              accept="image/*"
              capture="environment"
              class="sr-only-file"
              @change="handleOcrFileChange($event, 'journal')"
            />
          </label>

          <div class="journal-drawer-right-btns">
            <span v-if="journalSaveStatus === 'saved'" class="save-pill">
              Saved
            </span>
            <button
              type="button"
              class="btn-editorial-ghost"
              :title="hasJournalPassword ? 'Lock journal session now' : 'Set journal password'"
              @click="hasJournalPassword ? lockJournalSession() : (showJournalSettingsModal = true)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <span>{{ hasJournalPassword ? "Lock Session" : "Protect" }}</span>
            </button>

            <!-- Templates Dropdown in Drawer -->
            <div class="template-dropdown-wrapper">
              <button
                type="button"
                class="btn-editorial-ghost template-menu-trigger"
                title="Choose or customize journal template"
                @click="showTemplateMenu = !showTemplateMenu"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <line x1="3" y1="9" x2="21" y2="9" />
                  <line x1="9" y1="21" x2="9" y2="9" />
                </svg>
                <span>Templates ▾</span>
              </button>
              <div v-if="showTemplateMenu" class="template-dropdown-menu">
                <div class="template-menu-header">Templates</div>
                <button
                  v-for="tpl in availableTemplates"
                  :key="tpl.id"
                  type="button"
                  class="template-menu-item"
                  @click="applyJournalTemplate(tpl.id)"
                >
                  <div class="tpl-item-title-row">
                    <span class="tpl-title">{{ tpl.name }}</span>
                    <span v-if="tpl.is_default" class="tpl-badge-default">Default</span>
                  </div>
                  <span v-if="tpl.description" class="tpl-desc">{{ tpl.description }}</span>
                </button>
                <div class="template-menu-divider" />
                <button
                  type="button"
                  class="template-menu-item manage-action-item"
                  @click="showTemplateMenu = false; openTemplateManager()"
                >
                  <span class="tpl-title">+ Create &amp; Manage Templates...</span>
                  <span class="tpl-desc">Customize prompts, checklists &amp; default templates</span>
                </button>
              </div>
            </div>

            <button
              type="button"
              class="btn-orange-primary"
              @click="saveDailyJournalEntry"
            >
              Save Note
            </button>
          </div>
        </div>

        <!-- Handwritten OCR Review Box inside Drawer -->
        <div
          v-if="
            ocrTarget === 'journal' &&
            (isOcrRunning || ocrExtractedText || ocrError)
          "
          class="ocr-review-panel"
        >
          <div class="ocr-panel-top">
            <strong>Handwritten Page Scanner</strong>
            <span v-if="isOcrRunning" class="ocr-status-muted">
              {{ ocrStatusText }} ({{ ocrProgress }}%)
            </span>
            <button
              type="button"
              class="close-drawer-btn"
              @click="resetOcrState"
            >
              ×
            </button>
          </div>

          <div v-if="isOcrRunning" class="ocr-progress-bar-track">
            <div
              class="ocr-progress-bar-fill"
              :style="{ width: `${ocrProgress}%` }"
            />
          </div>

          <p v-if="ocrError" class="ocr-error-msg">{{ ocrError }}</p>

          <div v-if="ocrExtractedText || ocrPreviewUrl" class="ocr-split-preview">
            <img
              v-if="ocrPreviewUrl"
              :src="ocrPreviewUrl"
              alt="Scanned journal photo"
              class="ocr-thumb-img"
            />
            <div v-if="ocrExtractedText" class="ocr-extracted-box">
              <textarea
                v-model="ocrExtractedText"
                class="drawer-textarea ocr-textarea"
                rows="4"
              />
              <div class="ocr-Extracted-actions">
                <label class="pin-check-inline">
                  <input v-model="includeOcrHeading" type="checkbox" />
                  <span>Include scan heading</span>
                </label>
                <button
                  type="button"
                  class="btn-orange-primary"
                  @click="insertOcrTextIntoNote"
                >
                  Insert into Note
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Tasks active on this date -->
        <div
          v-if="tasksOnSelectedJournalDate.length > 0"
          class="journal-day-tasks-strip"
        >
          <span class="strip-label">Active on {{ selectedJournalDate }}:</span>
          <div class="strip-chips">
            <span
              v-for="t in tasksOnSelectedJournalDate"
              :key="t.id"
              class="day-task-chip"
              :style="{ borderLeft: `3px solid ${t.projectColor}` }"
            >
              {{ t.title }}
            </span>
          </div>
        </div>

        <div class="slideover-body">
          <!-- Interactive Habit Quick Bar in Drawer -->
          <div v-if="activeHabits.length > 0" class="journal-habit-quick-bar drawer-habit-bar">
            <span class="habit-bar-kicker">Habits</span>
            <div class="habit-pills-list">
              <button
                v-for="h in activeHabits"
                :key="h.id"
                type="button"
                class="habit-pill-btn"
                :class="{ completed: isHabitCompletedOnDate(h.slug, selectedJournalDate) }"
                :title="isHabitCompletedOnDate(h.slug, selectedJournalDate) ? 'Completed! Click to uncheck' : 'Click to complete'"
                @click="handleToggleHabit(h.id, selectedJournalDate)"
              >
                <span class="pill-check">{{ isHabitCompletedOnDate(h.slug, selectedJournalDate) ? '✓' : '○' }}</span>
                <span class="pill-title">{{ h.name }}</span>
                <span v-if="h.current_streak > 0" class="pill-flame">{{ h.current_streak }}d streak</span>
              </button>
            </div>
          </div>

          <!-- Empty state one-click scaffold banner in Drawer -->
          <div v-if="!journalDraftMd.trim()" class="empty-journal-scaffold-banner drawer-scaffold-banner">
            <div class="scaffold-banner-info">
              <span class="scaffold-banner-badge">BLANK ENTRY</span>
              <div>
                <h4 class="scaffold-banner-title">No notes recorded yet</h4>
                <p class="scaffold-banner-desc">Scaffold with habit checklist and reflection prompts.</p>
              </div>
            </div>
            <button
              type="button"
              class="btn-scaffold-action"
              @click="applyJournalTemplate(null)"
            >
              Apply Default Template
            </button>
          </div>

          <div class="journal-drawer-paper-body">
            <JournalDraggablesOverlay
              :images="journalFloatingImages"
              :stickers="journalStickers"
              :media-editing="isJournalMediaEditing"
              :scroll-offset="journalMediaScrollTop"
              @update-image="handleUpdateFloatingImage"
              @change-image-mode="handleChangeFloatingImageMode"
              @delete-image="handleDeleteFloatingImage"
              @update-sticker="handleUpdateStickerPlacement"
              @delete-sticker="handleRemovePlacement"
            />
          <div
            v-if="!isEditingJournal"
            ref="drawerJournalPreviewRef"
            class="journal-preview-paper drawer-preview clickable-paper"
            :class="{ 'is-empty': !journalDraftMd || !journalDraftMd.trim() }"
            title="Click to write or edit markdown"
            @scroll="handleJournalContentScroll"
            @click="handleJournalPreviewClick($event, true)"
          >
            <div
              v-if="journalDraftMd && journalDraftMd.trim()"
              class="journal-rendered-prose"
              v-html="renderedJournalHtml"
            />
            <div v-else class="empty-journal-paper-placeholder">
              <p class="journal-placeholder-heading">No journal entry recorded for this date.</p>
              <p class="journal-placeholder-sub">Click here to write in Markdown, or apply a template above.</p>
            </div>
          </div>

          <div v-else class="journal-notepad-wrapper">
            <textarea
              ref="drawerJournalTextareaRef"
              v-model="journalDraftMd"
              class="journal-ruled-textarea live-journal-notepad"
              :placeholder="`Write down your notes for ${formattedJournalHeading.full}…`"
              spellcheck="false"
              @scroll="handleJournalContentScroll"
              @blur="stopEditingJournal"
            />
            <div class="notepad-focusout-hint">
              <span>Markdown active &bull; Click outside or focus out to save</span>
            </div>
          </div>
          </div>
        </div>
      </aside>
    </div>

    <!-- =====================================================================
         SLIDE-OVER DRAWER 2: PROJECT SUBTASKS (A1, A2...) & MARKDOWN NOTES + OCR
         ===================================================================== -->
    <div
      v-if="selectedProject"
      class="slideover-backdrop"
      @click.self="closeProjectDrawer"
    >
      <aside
        class="slideover-drawer"
        aria-label="Project Subtasks and Notes Drawer"
      >
        <header class="slideover-header">
          <div class="inspector-title-group">
            <span
              class="color-badge-solid"
              :style="{ backgroundColor: selectedProject.color || '#b85423' }"
            >
              Project {{ selectedProjectPrefix }}
            </span>
            <input
              class="inspector-proj-name-input"
              :value="selectedProject.name"
              placeholder="Project Name…"
              title="Click to rename project"
              @change="onProjectNameChange(selectedProject, $event.target.value)"
            />
          </div>
          <div class="drawer-header-right-actions">
            <button
              v-if="selectedProject.id !== 0"
              type="button"
              class="project-status-toggle-btn"
              :class="{ done: isProjectCompleted(selectedProject) }"
              :title="
                isProjectCompleted(selectedProject)
                  ? 'Mark project Active (restore to calendar)'
                  : 'Mark project Done (hide from calendar)'
              "
              @click="toggleProjectDoneStatus(selectedProject)"
            >
              {{
                isProjectCompleted(selectedProject)
                  ? "✓ Completed · Reopen"
                  : "✓ Mark Done"
              }}
            </button>
            <button
              v-if="selectedProject.id !== 0"
              type="button"
              class="btn-editorial-ghost"
              title="Archive project into Archive Vault"
              @click="archiveProject(selectedProject)"
            >
              Archive
            </button>
            <button
              v-if="selectedProject.id !== 0"
              type="button"
              class="delete-project-btn"
              title="Delete this project"
              @click="deleteProject(selectedProject.id)"
            >
              Delete
            </button>
            <button
              type="button"
              class="close-drawer-btn"
              aria-label="Close drawer"
              @click="closeProjectDrawer"
            >
              ✕
            </button>
          </div>
        </header>

        <div v-if="selectedProject.id !== 0" class="slideover-project-desc-row">
          <textarea
            class="inspector-proj-desc-input"
            :value="selectedProject.description || ''"
            placeholder="Add project description / goals (click away or press Tab to save)…"
            rows="2"
            @change="
              updateProjectFields(selectedProject, {
                description: $event.target.value,
              })
            "
          ></textarea>
        </div>

        <div v-if="selectedProject.id !== 0" class="slideover-project-settings">
          <div class="drawer-area-row">
            <label class="date-mini drawer-area-label">
              <span>Folder</span>
              <input
                type="text"
                list="project-area-suggestions"
                class="input-minimal drawer-area-input"
                :value="selectedProject.area || ''"
                placeholder="e.g. Work, School, Personal…"
                @change="
                  updateProjectFields(selectedProject, {
                    area: $event.target.value,
                  })
                "
              />
            </label>
          </div>

          <div class="swatch-row">
            <span class="swatch-label">Tone:</span>
            <input
              type="color"
              class="color-picker-mini"
              :value="selectedProject.color || '#c2410c'"
              @input="
                updateProjectFields(selectedProject, {
                  color: $event.target.value,
                })
              "
            />
            <button
              v-for="sw in COLOR_SWATCHES"
              :key="sw"
              type="button"
              class="color-swatch-dot"
              :class="{ active: selectedProject.color === sw }"
              :style="{ backgroundColor: sw }"
              @click="updateProjectFields(selectedProject, { color: sw })"
            />
          </div>

          <div class="pcard-dates">
            <label class="date-mini">
              <span>Start</span>
              <input
                :value="selectedProject.start_date"
                type="date"
                @change="
                  updateProjectFields(selectedProject, {
                    start_date: $event.target.value,
                  })
                "
              />
            </label>
            <span class="date-arrow">→</span>
            <label class="date-mini">
              <span>Target</span>
              <input
                :value="selectedProject.target_date"
                type="date"
                @change="
                  updateProjectFields(selectedProject, {
                    target_date: $event.target.value,
                  })
                "
              />
            </label>
          </div>

          <div class="drawer-timeline-vis-box">
            <label
              class="drawer-vis-checkbox-label"
              title="Show or hide this project's subtasks on the calendar timeline"
            >
              <input
                type="checkbox"
                :checked="isProjectSubtasksVisible(selectedProject.id)"
                @change="toggleProjectSubtasksVisibility(selectedProject.id)"
              />
              <span class="vis-label-text">
                Show Subtasks on Calendar Timeline
              </span>
            </label>
            <span
              v-if="!selectedProject.is_pinned"
              class="unpinned-hint-pill"
              title="Subtasks will show on the timeline while the project span bar remains hidden"
            >
              Project bar unpinned
            </span>
          </div>
        </div>

        <div class="slideover-tabs">
          <button
            type="button"
            class="scale-btn"
            :class="{ active: drawerTab === 'subtasks' }"
            @click="drawerTab = 'subtasks'"
          >
            Subtasks ({{ selectedProjectSubtasks.length }})
          </button>
          <button
            type="button"
            class="scale-btn"
            :class="{ active: drawerTab === 'notes' }"
            @click="drawerTab = 'notes'"
          >
            Project Notes
          </button>
        </div>

        <!-- TAB 1: SUBTASKS (A1, A2...) MANAGER -->
        <div v-if="drawerTab === 'subtasks'" class="slideover-body">
          <form
            class="slideover-add-subtask"
            @submit.prevent="addSubtaskToSelectedProject"
          >
            <div class="add-sub-top">
              <span
                class="color-badge-solid"
                :style="{ backgroundColor: newSubtask.color }"
              >
                {{ nextSubtaskCode }}
              </span>
              <input
                v-model="newSubtask.title"
                type="text"
                class="input-minimal subtask-title-input"
                :placeholder="`Add subtask ${nextSubtaskCode}…`"
                required
              />
            </div>

            <div class="add-sub-middle">
              <input
                v-model="newSubtask.description"
                type="text"
                class="input-minimal subtask-notes-input"
                placeholder="Initial Markdown notes (optional)…"
              />
            </div>

            <div class="add-sub-bottom">
              <label class="date-mini">
                <span>Start</span>
                <input v-model="newSubtask.start_date" type="date" />
              </label>
              <label class="date-mini">
                <span>Due</span>
                <input v-model="newSubtask.due_date" type="date" />
              </label>
              <label class="date-mini">
                <span>From</span>
                <input v-model="newSubtask.start_time" type="time" />
              </label>
              <label class="date-mini">
                <span>To</span>
                <input v-model="newSubtask.end_time" type="time" />
              </label>
              <label class="date-mini">
                <span>Priority</span>
                <select v-model="newSubtask.priority" class="input-minimal">
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </label>
              <label
                class="deadline-only-toggle"
                title="Only show on timeline as a single-day deadline on the due date"
              >
                <input v-model="newSubtask.deadline_only" type="checkbox" />
                <span>Deadline only</span>
              </label>
              <label
                class="deadline-only-toggle"
                title="Render as milestone diamond"
              >
                <input v-model="newSubtask.is_milestone" type="checkbox" />
                <span>Milestone</span>
              </label>
              <div class="swatch-row">
                <input
                  v-model="newSubtask.color"
                  type="color"
                  class="color-picker-mini"
                />
                <button
                  v-for="sw in COLOR_SWATCHES"
                  :key="sw"
                  type="button"
                  class="color-swatch-dot"
                  :class="{ active: newSubtask.color === sw }"
                  :style="{ backgroundColor: sw }"
                  @click="newSubtask.color = sw"
                />
              </div>
              <button type="submit" class="btn-ink-primary">
                Add {{ nextSubtaskCode }}
              </button>
            </div>
          </form>

          <div class="subtasks-list-grid">
            <div
              v-for="sub in selectedProjectSubtasks"
              :key="sub.id"
              class="subtask-row-card"
              :style="getCustomColorCardStyle(sub.color || '#2c666e')"
            >
              <div class="subtask-card-header">
                <div class="subtask-left">
                  <button
                    type="button"
                    class="subtask-check-btn"
                    :class="{ checked: sub.status === 'done' }"
                    :style="
                      sub.status === 'done'
                        ? {
                            backgroundColor: sub.color || '#2c666e',
                            borderColor: sub.color || '#2c666e',
                          }
                        : { borderColor: sub.color || '#2c666e' }
                    "
                    @click="toggleSubtaskStatus(selectedProject.id, sub.id)"
                  >
                    <svg
                      v-if="sub.status === 'done'"
                      width="11"
                      height="11"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="3"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </button>
                  <span
                    class="color-badge-mono"
                    :style="{
                      color: sub.color || '#2c666e',
                      borderColor: `${sub.color || '#2c666e'}44`,
                    }"
                  >
                    {{ sub.code }}
                  </span>
                  <strong
                    class="week-item-title"
                    :class="{ 'strikethrough-done': sub.status === 'done' }"
                  >
                    {{ sub.title }}
                  </strong>
                </div>

                <div class="subtask-controls">
                  <label class="date-mini">
                    <span>Start</span>
                    <input
                      type="date"
                      :value="sub.start_date"
                      @change="
                        updateSubtaskFields(selectedProject.id, sub.id, {
                          start_date: $event.target.value,
                        })
                      "
                    />
                  </label>
                  <label class="date-mini">
                    <span>Due</span>
                    <input
                      type="date"
                      :value="sub.due_date"
                      @change="
                        updateSubtaskFields(selectedProject.id, sub.id, {
                          due_date: $event.target.value,
                        })
                      "
                    />
                  </label>
                  <label class="date-mini">
                    <span>From</span>
                    <input
                      type="time"
                      :value="sub.start_time || ''"
                      @change="
                        updateSubtaskFields(selectedProject.id, sub.id, {
                          start_time: $event.target.value || null,
                        })
                      "
                    />
                  </label>
                  <label class="date-mini">
                    <span>To</span>
                    <input
                      type="time"
                      :value="sub.end_time || ''"
                      @change="
                        updateSubtaskFields(selectedProject.id, sub.id, {
                          end_time: $event.target.value || null,
                        })
                      "
                    />
                  </label>
                  <select
                    :value="sub.priority || 'medium'"
                    class="input-minimal subtask-priority-select"
                    title="Task priority"
                    @change="
                      updateSubtaskFields(selectedProject.id, sub.id, {
                        priority: $event.target.value,
                      })
                    "
                  >
                    <option value="low">Low</option>
                    <option value="medium">Med</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                  <label
                    class="deadline-only-toggle"
                    title="Only show on timeline as a single-day deadline on the due date"
                  >
                    <input
                      type="checkbox"
                      :checked="Boolean(sub.deadline_only)"
                      @change="
                        updateSubtaskFields(selectedProject.id, sub.id, {
                          deadline_only: $event.target.checked,
                        })
                      "
                    />
                    <span>Deadline</span>
                  </label>
                  <label
                    class="deadline-only-toggle"
                    title="Show as milestone diamond"
                  >
                    <input
                      type="checkbox"
                      :checked="Boolean(sub.is_milestone)"
                      @change="
                        updateSubtaskFields(selectedProject.id, sub.id, {
                          is_milestone: $event.target.checked,
                        })
                      "
                    />
                    <span>Milestone</span>
                  </label>
                  <input
                    type="color"
                    class="color-picker-mini"
                    :value="sub.color || '#2c666e'"
                    title="Customize subtask color"
                    @input="
                      updateSubtaskFields(selectedProject.id, sub.id, {
                        color: $event.target.value,
                      })
                    "
                  />
                  <button
                    type="button"
                    class="delete-sub-btn"
                    title="Delete subtask"
                    @click="deleteSubtask(selectedProject.id, sub.id)"
                  >
                    ×
                  </button>
                </div>
              </div>

              <!-- Subtask's Own Note Field: renders MD automatically, double click for notepad, blur to render -->
              <div class="subtask-note-section">
                <!-- 1. Rendered Markdown view (default single field) -->
                <div
                  v-if="editingSubtaskId !== sub.id"
                  class="subtask-note-display clickable-note"
                  :class="{ 'is-empty': !sub.description || !sub.description.trim() }"
                  title="Double-click to edit note for this subtask"
                  @click="handleSubtaskNotePreviewClick($event, sub)"
                  @dblclick="startEditingSubtaskNote(sub.id)"
                >
                  <div
                    v-if="sub.description && sub.description.trim()"
                    class="subtask-note-markdown"
                    v-html="renderMarkdown(sub.description)"
                  />
                  <div v-else class="subtask-note-placeholder">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                    </svg>
                    <span>Double-click to add notes for {{ sub.code }}…</span>
                  </div>
                  <span v-if="sub.description && sub.description.trim()" class="subtask-note-hover-hint">
                    Double-click to edit
                  </span>
                </div>

                <!-- 2. Notepad textarea view (activated by double click, blurs back to markdown preview) -->
                <div v-else class="subtask-note-editor-wrapper">
                  <textarea
                    :ref="(el) => setSubtaskTextareaRef(sub.id, el)"
                    v-model="sub.description"
                    class="subtask-note-textarea"
                    placeholder="Write Markdown notes for this subtask… Click outside to render &amp; save."
                    rows="3"
                    spellcheck="false"
                    @blur="stopEditingSubtaskNote(sub)"
                  />
                  <div class="subtask-editor-hint">
                    <span>Click outside or focus out to render Markdown &amp; save</span>
                  </div>
                </div>
              </div>
            </div>

            <p
              v-if="selectedProjectSubtasks.length === 0"
              class="empty-sub-hint"
            >
              No subtasks matching filter ({{ taskFilterMode }}). Add
              {{ nextSubtaskCode }} above.
            </p>
          </div>
        </div>

        <!-- TAB 2: MARKDOWN NOTES EDITOR -->
        <div v-else class="slideover-body">
          <div class="drawer-header">
            <input
              v-model="activeNote.title"
              type="text"
              class="input-minimal title-input"
              placeholder="Note Title…"
            />
            <button type="button" class="btn-orange-primary" @click="saveNote">
              Save &amp; Sync
            </button>
          </div>

          <!-- Single Note Field (renders MD automatically, double-click to edit in notepad, blur to render & save) -->
          <div class="single-note-field-container">
            <!-- 1. Rendered Markdown View (Default) -->
            <div
              v-if="!isEditingProjectNote"
              class="single-field-preview drawer-preview clickable-preview"
              :class="{
                'is-empty':
                  !activeNote.content_md || !activeNote.content_md.trim(),
              }"
              title="Double-click to open notepad"
              @click="handleProjectNotePreviewClick($event)"
              @dblclick="startEditingProjectNote"
            >
              <div
                v-if="activeNote.content_md && activeNote.content_md.trim()"
                class="rendered-markdown-content"
                v-html="renderedMarkdownHtml"
              />
              <div v-else class="empty-note-placeholder">
                <p class="placeholder-title">No notes written yet.</p>
                <p class="placeholder-desc">
                  <strong>Double-click</strong> here to open the notepad and write in Markdown.
                </p>
                <small class="placeholder-sub">
                  Supports headings, checklists <code>- [ ]</code>, #tags, [[WikiLinks]], and directives.
                </small>
              </div>
              <div class="note-field-status-badge">
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"
                  />
                  <path
                    d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"
                  />
                </svg>
                <span>Double-click to edit note</span>
              </div>
            </div>

            <!-- 2. Notepad Textarea View (activated on double-click; blur renders Markdown again & auto-saves) -->
            <div v-else class="single-field-notepad-wrapper">
              <textarea
                ref="projectNoteTextareaRef"
                v-model="activeNote.content_md"
                class="drawer-textarea single-field-textarea live-notepad"
                placeholder="Type your Markdown notes here… Focus out (click outside) to render Markdown & save."
                spellcheck="false"
                @blur="stopEditingProjectNote"
              />
              <div class="notepad-focusout-hint">
                <span>Notepad active &bull; Click outside or focus out to preview &amp; save</span>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>

    <!-- =====================================================================
         MCP AI CONNECT MODAL (Antigravity & Claude)
         ===================================================================== -->
    <div
      v-if="showMcpModal"
      class="slideover-backdrop auth-modal-backdrop"
      @click.self="showMcpModal = false"
    >
      <div
        class="auth-modal-card mcp-modal-card"
        role="dialog"
        :aria-label="mcpClientTarget === 'antigravity' ? 'Connect Antigravity to ChronoNote' : 'Connect Claude to ChronoNote'"
      >
        <div class="auth-modal-header">
          <div>
            <span class="journal-kicker">MODEL CONTEXT PROTOCOL</span>
            <h2 class="editorial-serif-drawer-title">
              {{ mcpClientTarget === 'antigravity' ? 'Connect Antigravity' : 'Connect Claude' }}
            </h2>
          </div>
          <button
            type="button"
            class="close-drawer-btn"
            aria-label="Close"
            @click="showMcpModal = false"
          >
            ✕
          </button>
        </div>

        <div class="mcp-modal-body">
          <div class="mcp-client-tabs" role="tablist" aria-label="AI Client">
            <button
              type="button"
              role="tab"
              :aria-selected="mcpClientTarget === 'antigravity'"
              class="mcp-client-tab"
              :class="{ active: mcpClientTarget === 'antigravity' }"
              @click="mcpClientTarget = 'antigravity'"
            >
              Antigravity
            </button>
            <button
              type="button"
              role="tab"
              :aria-selected="mcpClientTarget === 'claude'"
              class="mcp-client-tab"
              :class="{ active: mcpClientTarget === 'claude' }"
              @click="mcpClientTarget = 'claude'"
            >
              Claude
            </button>
          </div>

          <p class="mcp-modal-desc">
            <template v-if="mcpClientTarget === 'antigravity'">
              Connect Google Antigravity to your personal ChronoNote workspace.
            </template>
            <template v-else>
              Connect Claude Desktop or Claude Code to your personal ChronoNote workspace.
            </template>
          </p>

          <div class="mcp-account-badge">
            <span class="mcp-badge-label">Active Account:</span>
            <strong>{{ currentUser?.name || currentUser?.email }}</strong>
            <span class="mcp-badge-email">({{ currentUser?.email }})</span>
          </div>

          <div v-if="mcpCodeLoading" class="mcp-loading-state" style="text-align: center; padding: 1.5rem; color: #64748b; font-size: 0.88rem;">
            Generating temporary connection code...
          </div>

          <div v-else-if="mcpCodeError" class="ocr-error-msg" style="margin-top: 0.5rem;">
            {{ mcpCodeError }}
          </div>

          <div v-else class="mcp-code-container">
            <div class="mcp-code-label">Your 6-Digit Connection Code</div>
            <div class="mcp-code-display">
              <span class="mcp-digits">{{ mcpConnectData?.code || '------' }}</span>
              <button
                type="button"
                class="btn-copy-code"
                @click="copyMcpCode"
              >
                {{ mcpCopied ? 'Copied! ✓' : 'Copy Code' }}
              </button>
            </div>
            <div class="mcp-expires-note">Expires in 15 minutes &bull; Single-use only</div>

            <div class="mcp-instructions-box">
              <span class="mcp-inst-title">
                {{ mcpClientTarget === 'antigravity' ? 'Prompt Antigravity:' : 'Prompt Claude Desktop or Claude Code:' }}
              </span>
              <code>Connect to ChronoNote with code {{ mcpConnectData?.code }}</code>
            </div>

            <div v-if="mcpClientTarget === 'antigravity'" class="mcp-instructions-box">
              <div class="mcp-config-header">
                <span class="mcp-inst-title">Config (~/.gemini/config/mcp_config.json):</span>
                <button
                  type="button"
                  class="btn-copy-mini"
                  @click="copyAntigravityConfig"
                >
                  {{ mcpConfigCopied ? 'Copied! ✓' : 'Copy JSON' }}
                </button>
              </div>
              <pre class="mcp-config-pre"><code>{{ antigravityConfigSnippet }}</code></pre>
            </div>
          </div>
        </div>

        <div style="display: flex; justify-content: flex-end; padding: 0.5rem 0 0 0;">
          <button
            type="button"
            class="btn-editorial-ghost"
            style="border: 1px solid var(--border-subtle); padding: 0.45rem 1.1rem; border-radius: 6px; cursor: pointer;"
            @click="showMcpModal = false"
          >
            Done
          </button>
        </div>
      </div>
    </div>

    <!-- =====================================================================
         GOOGLE ACCOUNT SIGN-IN MODAL
         ===================================================================== -->
    <div
      v-if="showAuthModal"
      class="slideover-backdrop auth-modal-backdrop"
      @click.self="!authRequired && (showAuthModal = false)"
    >
      <div class="auth-modal-card" role="dialog" aria-label="Sign in with Google">
        <div class="auth-modal-header">
          <div>
            <span class="journal-kicker">PERSONAL WORKSPACE</span>
            <h2 class="editorial-serif-drawer-title">Sign in to ChronoNote</h2>
          </div>
          <button
            v-if="!authRequired"
            type="button"
            class="close-drawer-btn"
            @click="showAuthModal = false"
          >
            ✕
          </button>
        </div>

        <p class="auth-modal-desc">
          Sync your daily journal, handwritten OCR scans, and project timeline across your desktop and phone.
        </p>

        <!-- Official Google Identity Services Button Container (when Client ID is configured) -->
        <div
          v-show="googleClientId"
          ref="googleBtnContainer"
          class="google-gsi-container"
        />

        <!-- Personal Google Account Form (Works immediately in local/personal mode or alongside GSI) -->
        <form
          class="personal-auth-form"
          @submit.prevent="handlePersonalGoogleSignIn"
        >
          <label class="auth-field-label">
            <span>Google Account Email</span>
            <input
              v-model="authEmailInput"
              type="email"
              class="input-minimal"
              placeholder="you@gmail.com"
              required
            />
          </label>
          <label class="auth-field-label">
            <span>Display Name (optional)</span>
            <input
              v-model="authNameInput"
              type="text"
              class="input-minimal"
              placeholder="Your name"
            />
          </label>

          <p v-if="authError" class="ocr-error-msg">{{ authError }}</p>

          <button
            type="submit"
            class="btn-google-submit"
            :disabled="isAuthenticating"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
              <path
                fill="#EA4335"
                d="M12 5c1.6 0 3 .6 4.1 1.7l3.1-3.1C17.3 1.8 14.8 1 12 1 7.4 1 3.5 3.6 1.6 7.4l3.7 2.8C6.2 7.2 8.9 5 12 5z"
              />
              <path
                fill="#4285F4"
                d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.6l3.7 2.9c2.2-2 3.7-5 3.7-8.7z"
              />
              <path
                fill="#FBBC05"
                d="M5.3 14.8c-.2-.8-.4-1.6-.4-2.5s.2-1.7.4-2.5L1.6 7C.6 9 0 11.2 0 13.5s.6 4.5 1.6 6.5l3.7-2.9z"
              />
              <path
                fill="#34A853"
                d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3.1 0-5.8-2.1-6.7-5l-3.7 2.8C3.5 19.9 7.4 23 12 23z"
              />
            </svg>
            <span>
              {{ isAuthenticating ? "Signing in…" : "Continue with Google Account" }}
            </span>
          </button>

          <div class="auth-modal-danger-divider" />
          <div class="auth-modal-danger-zone">
            <div class="danger-zone-header">
              <span class="danger-kicker">Danger zone</span>
              <p class="danger-desc">
                Need a fresh start? Clear all projects, tasks, notes, journal entries, and habits.
              </p>
            </div>
            <button
              type="button"
              class="btn-danger-solid-sm"
              @click="showAuthModal = false; openResetModal()"
            >
              Delete All Workspace Data…
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- =====================================================================
         JOURNAL PASSWORD UNLOCK MODAL (Session-Based Access)
         ===================================================================== -->
    <div
      v-if="showJournalUnlockModal"
      class="slideover-backdrop auth-modal-backdrop"
      @click.self="showJournalUnlockModal = false"
    >
      <div class="auth-modal-card" role="dialog" aria-label="Unlock Daily Journal">
        <div class="auth-modal-header">
          <div>
            <span class="journal-kicker">PROTECTED JOURNAL</span>
            <h2 class="editorial-serif-drawer-title">Enter Journal Password</h2>
          </div>
          <button
            type="button"
            class="close-drawer-btn"
            @click="showJournalUnlockModal = false"
          >
            ✕
          </button>
        </div>

        <p class="auth-modal-desc">
          Your daily journal entries are password protected. Unlocking grants access for your current browsing session until you close Chrome.
        </p>

        <form class="personal-auth-form" @submit.prevent="unlockJournalSession">
          <label class="auth-field-label">
            <span>Journal Password</span>
            <input
              v-model="journalPasswordInput"
              type="password"
              class="input-minimal"
              placeholder="••••••••"
              required
              autofocus
            />
          </label>

          <p v-if="journalUnlockError" class="ocr-error-msg">
            {{ journalUnlockError }}
          </p>

          <div class="journal-modal-actions">
            <button
              type="button"
              class="btn-editorial-ghost"
              @click="showJournalUnlockModal = false"
            >
              Cancel
            </button>
            <button type="submit" class="btn-orange-primary">
              Unlock for This Session
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- =====================================================================
         JOURNAL PASSWORD SETTINGS / CHANGE MODAL
         ===================================================================== -->
    <div
      v-if="showJournalSettingsModal"
      class="slideover-backdrop auth-modal-backdrop"
      @click.self="showJournalSettingsModal = false"
    >
      <div class="auth-modal-card" role="dialog" aria-label="Journal Security Settings">
        <div class="auth-modal-header">
          <div>
            <span class="journal-kicker">JOURNAL SECURITY</span>
            <h2 class="editorial-serif-drawer-title">
              {{ hasJournalPassword ? "Change Journal Password" : "Set Journal Password" }}
            </h2>
          </div>
          <button
            type="button"
            class="close-drawer-btn"
            @click="showJournalSettingsModal = false"
          >
            ✕
          </button>
        </div>

        <p class="auth-modal-desc">
          Require a password whenever you view your daily journals. Access is remembered only during your active browser session. Closing Chrome will automatically lock it again.
        </p>

        <form class="personal-auth-form" @submit.prevent="saveJournalPassword">
          <label v-if="hasJournalPassword" class="auth-field-label">
            <span>Current Password</span>
            <input
              v-model="journalSettingsCurrentPw"
              type="password"
              class="input-minimal"
              placeholder="Current password"
              required
            />
          </label>

          <label class="auth-field-label">
            <span>New Password</span>
            <input
              v-model="journalSettingsNewPw"
              type="password"
              class="input-minimal"
              placeholder="Enter password"
              required
            />
          </label>

          <label class="auth-field-label">
            <span>Confirm New Password</span>
            <input
              v-model="journalSettingsConfirmPw"
              type="password"
              class="input-minimal"
              placeholder="Confirm password"
              required
            />
          </label>

          <p v-if="journalSettingsError" class="ocr-error-msg">
            {{ journalSettingsError }}
          </p>
          <p v-if="journalSettingsSuccess" class="ocr-status-ready">
            {{ journalSettingsSuccess }}
          </p>

          <div class="journal-modal-actions">
            <button
              v-if="hasJournalPassword && isJournalUnlocked"
              type="button"
              class="btn-editorial-ghost"
              @click="lockJournalSession(); showJournalSettingsModal = false"
            >
              Lock Session Now
            </button>
            <button type="submit" class="btn-orange-primary">
              {{ hasJournalPassword ? "Update Password" : "Save Password" }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- =====================================================================
         MOBILE BOTTOM NAVIGATION BAR (For effortless one-handed phone use)
         ===================================================================== -->
    <nav class="mobile-bottom-nav" aria-label="Mobile Navigation">
      <button
        type="button"
        class="mobile-nav-item"
        :class="{ active: activePage === 'timeline' && !isJournalDrawerOpen }"
        @click="
          isJournalDrawerOpen = false;
          activePage = 'timeline';
        "
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
          <line x1="16" y1="2" x2="16" y2="6" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="3" y1="10" x2="21" y2="10" />
        </svg>
        <span>Calendar</span>
      </button>

      <button
        type="button"
        class="mobile-nav-item"
        :class="{ active: activePage === 'journal' || isJournalDrawerOpen }"
        @click="
          isJournalDrawerOpen = false;
          navigateToDailyJournal();
        "
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M12 20h9" />
          <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
        </svg>
        <span>Journal</span>
      </button>

      <button
        type="button"
        class="mobile-nav-item"
        :class="{ active: activePage === 'kanban' }"
        @click="
          isJournalDrawerOpen = false;
          activePage = 'kanban';
        "
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <rect x="3" y="3" width="7" height="18" rx="1" />
          <rect x="14" y="3" width="7" height="11" rx="1" />
        </svg>
        <span>Board</span>
      </button>

      <button
        type="button"
        class="mobile-nav-item"
        :class="{ active: activePage === 'analytics' }"
        @click="
          isJournalDrawerOpen = false;
          activePage = 'analytics';
          fetchHabitsAndAnalytics();
        "
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M12 20v-6M6 20V10M18 20V4" />
        </svg>
        <span>Habits</span>
      </button>

      <button
        type="button"
        class="mobile-nav-item"
        :class="{ active: activePage === 'study' }"
        @click="
          isJournalDrawerOpen = false;
          activePage = 'study';
          fetchWorkspaceNotes();
        "
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
        <span>Study</span>
      </button>

      <button
        type="button"
        class="mobile-nav-item"
        @click="showAuthModal = true"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
        <span>{{ currentUser ? "Account" : "Sign In" }}</span>
      </button>
    </nav>

    <!-- =====================================================================
         JOURNAL TEMPLATE CUSTOMIZATION & MANAGER MODAL
         ===================================================================== -->
    <div
      v-if="showTemplateManagerModal"
      class="slideover-backdrop modal-backdrop"
      @click.self="showTemplateManagerModal = false"
    >
      <div class="template-manager-card" role="dialog" aria-label="Customize Journal Templates">
        <div class="template-manager-header">
          <div>
            <span class="journal-kicker">CUSTOM TEMPLATES</span>
            <h2 class="editorial-serif-drawer-title">Journal Templates</h2>
          </div>
          <button
            type="button"
            class="close-drawer-btn"
            @click="showTemplateManagerModal = false"
          >
            ×
          </button>
        </div>

        <div class="template-manager-layout">
          <!-- Left sidebar: List of templates -->
          <div class="template-manager-sidebar">
            <div class="tpl-sidebar-top">
              <span class="tpl-sidebar-title">Templates</span>
              <button
                type="button"
                class="btn-tpl-new"
                @click="initNewTemplateForm"
              >
                + New
              </button>
            </div>

            <div class="tpl-sidebar-list">
              <div
                v-for="tpl in availableTemplates"
                :key="tpl.id"
                class="tpl-sidebar-item"
                :class="{ active: editingTemplateId === tpl.id }"
                @click="selectTemplateToEdit(tpl)"
              >
                <div class="tpl-item-header">
                  <span class="tpl-item-name">{{ tpl.name }}</span>
                  <span v-if="tpl.is_default" class="tpl-badge-default">Default</span>
                </div>
                <p v-if="tpl.description" class="tpl-item-desc">{{ tpl.description }}</p>
              </div>
            </div>
          </div>

          <!-- Right panel: Template Editor Form -->
          <div class="template-manager-editor">
            <div class="tpl-editor-header">
              <h3 class="tpl-editor-title">
                {{ editingTemplateId ? "Edit Template" : "Create New Template" }}
              </h3>
              <span class="tpl-editor-sub">
                Customize prompts, checklists, and dynamic placeholders for your daily journal.
              </span>
            </div>

            <form class="template-editor-form" @submit.prevent="saveTemplateForm">
              <div class="form-group">
                <label class="form-label" for="tpl-name">Template Name *</label>
                <input
                  id="tpl-name"
                  v-model="templateForm.name"
                  type="text"
                  class="input-minimal"
                  placeholder="e.g. Daily Reflection &amp; Habits"
                  required
                />
              </div>

              <div class="form-group">
                <label class="form-label" for="tpl-desc">Description (Optional)</label>
                <input
                  id="tpl-desc"
                  v-model="templateForm.description"
                  type="text"
                  class="input-minimal"
                  placeholder="e.g. Standard daily journal with habit check-in and notes"
                />
              </div>

              <div class="form-group">
                <label class="form-label" for="tpl-body">Markdown Content *</label>
                <textarea
                  id="tpl-body"
                  v-model="templateForm.content_md"
                  class="input-minimal template-markdown-editor"
                  rows="9"
                  placeholder="Write your template markdown here..."
                  required
                />
              </div>

              <!-- Dynamic Variables Guide -->
              <div class="template-vars-card">
                <span class="vars-card-title">Dynamic Variables</span>
                <div class="vars-tags-list">
                  <div class="var-tag-row">
                    <code>&#123;&#123;date&#125;&#125;</code>
                    <span>Current ISO date (e.g. 2026-11-02)</span>
                  </div>
                  <div class="var-tag-row">
                    <code>&#123;&#123;day_of_week&#125;&#125;</code>
                    <span>Current day name (e.g. Monday)</span>
                  </div>
                  <div class="var-tag-row">
                    <code>&#123;&#123;habits_checklist&#125;&#125;</code>
                    <span>Interactive checklist of all your active tracked habits</span>
                  </div>
                </div>
              </div>

              <label class="pin-check-inline tpl-default-check">
                <input v-model="templateForm.is_default" type="checkbox" />
                <span>Set as default template for empty daily journals</span>
              </label>

              <p v-if="templateManagerError" class="ocr-error-msg">
                {{ templateManagerError }}
              </p>
              <p v-if="templateManagerStatus" class="ocr-status-ready">
                {{ templateManagerStatus }}
              </p>

              <div class="template-form-actions">
                <button
                  v-if="editingTemplateId"
                  type="button"
                  class="btn-editorial-ghost btn-danger-ghost"
                  @click="deleteTemplate(editingTemplateId)"
                >
                  Delete
                </button>
                <div v-else />

                <div class="actions-right">
                  <button
                    type="button"
                    class="btn-editorial-ghost"
                    @click="showTemplateManagerModal = false"
                  >
                    Close
                  </button>
                  <button type="submit" class="btn-orange-primary">
                    {{ editingTemplateId ? "Save Changes" : "Create Template" }}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>

    <!-- =====================================================================
         WORKSPACE RESET & DATA WIPEOUT MODAL (2-STEP CONFIRMATION)
         ===================================================================== -->
    <div
      v-if="showResetModal"
      class="slideover-backdrop modal-backdrop"
      @click.self="!isResetting && (showResetModal = false)"
    >
      <div class="auth-modal-card reset-modal-card" role="dialog" aria-label="Reset Workspace & Delete All Data">
        <div class="auth-modal-header">
          <div>
            <span class="journal-kicker reset-kicker">DANGER &bull; STEP {{ resetStep }} OF 2</span>
            <h2 class="editorial-serif-drawer-title reset-title">
              {{ resetStep === 1 ? "Clear All Workspace Data?" : "Confirm Permanent Deletion" }}
            </h2>
          </div>
          <button
            v-if="!isResetting"
            type="button"
            class="close-drawer-btn"
            @click="showResetModal = false"
          >
            ×
          </button>
        </div>

        <!-- STEP 1: Summary of destruction & First Confirmation -->
        <div v-if="resetStep === 1" class="reset-step-body">
          <div class="reset-warning-banner">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <div>
              <strong>This action is irreversible.</strong>
              <p>Everything in your ChronoNote account will be permanently deleted from the database and local storage.</p>
            </div>
          </div>

          <div class="reset-items-list">
            <div class="reset-item-row">
              <span class="reset-bullet">&times;</span>
              <span>All Projects &amp; Timeline schedules</span>
            </div>
            <div class="reset-item-row">
              <span class="reset-bullet">&times;</span>
              <span>All Subtasks (A1, A2...) &amp; dependencies</span>
            </div>
            <div class="reset-item-row">
              <span class="reset-bullet">&times;</span>
              <span>All Daily Journal entries &amp; handwritten OCR logs</span>
            </div>
            <div class="reset-item-row">
              <span class="reset-bullet">&times;</span>
              <span>All Markdown Notes &amp; WikiLinks</span>
            </div>
            <div class="reset-item-row">
              <span class="reset-bullet">&times;</span>
              <span>All Tracked Habits &amp; 52-week activity history</span>
            </div>
            <div class="reset-item-row">
              <span class="reset-bullet">&times;</span>
              <span>Custom Templates (reset back to clean defaults)</span>
            </div>
          </div>

          <div class="reset-modal-actions">
            <button
              type="button"
              class="btn-editorial-ghost"
              @click="showResetModal = false"
            >
              Cancel
            </button>
            <button
              type="button"
              class="btn-danger-solid"
              @click="proceedToResetStep2"
            >
              I Understand, Continue to Step 2 &rarr;
            </button>
          </div>
        </div>

        <!-- STEP 2: Strict Typing Confirmation & Final Confirmation Button -->
        <div v-else class="reset-step-body">
          <p class="reset-confirm-prompt">
            To prevent accidental data loss, please type <strong class="reset-match-word">RESET</strong> into the field below to activate the delete button:
          </p>

          <input
            v-model="resetConfirmationInput"
            type="text"
            class="input-minimal reset-text-input"
            placeholder="Type RESET to confirm"
            :disabled="isResetting"
            autofocus
            @keydown.enter.prevent="resetConfirmationInput.trim().toUpperCase() === 'RESET' && executeWorkspaceReset()"
          />

          <p v-if="resetError" class="ocr-error-msg">{{ resetError }}</p>
          <p v-if="resetSuccess" class="ocr-status-ready">{{ resetSuccess }}</p>

          <div class="reset-modal-actions">
            <button
              type="button"
              class="btn-editorial-ghost"
              :disabled="isResetting"
              @click="resetStep = 1"
            >
              &larr; Back
            </button>
            <button
              type="button"
              class="btn-danger-solid"
              :disabled="resetConfirmationInput.trim().toUpperCase() !== 'RESET' || isResetting"
              @click="executeWorkspaceReset"
            >
              {{ isResetting ? "Wiping Data…" : "Permanently Delete Everything" }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- =====================================================================
         VISUAL THEMES & PAPER STYLES CUSTOMIZER MODAL
         ===================================================================== -->
    <div
      v-if="showThemeSettingsModal"
      class="slideover-backdrop modal-backdrop"
      @click.self="showThemeSettingsModal = false"
    >
      <div class="theme-modal-card" role="dialog" aria-label="Visual Themes & Paper Styles">
        <div class="template-manager-header">
          <div>
            <span class="journal-kicker">CUSTOM APPEARANCE</span>
            <h2 class="editorial-serif-drawer-title">Paper Textures &amp; Fonts</h2>
          </div>
          <button
            type="button"
            class="close-drawer-btn"
            @click="showThemeSettingsModal = false"
          >
            ×
          </button>
        </div>

        <!-- Section 1: Paper Styles -->
        <div>
          <h4 class="setup-label">Paper Texture</h4>
          <div class="theme-options-grid">
            <div
              v-for="p in PAPER_THEMES"
              :key="p.id"
              class="theme-option-card"
              :class="{ active: customThemePrefs.paperTheme === p.id }"
              @click="updateThemeSetting('paperTheme', p.id)"
            >
              <div class="theme-swatch-circle" :style="{ backgroundColor: p.bg }"></div>
              <span class="theme-card-title">{{ p.name }}</span>
              <span class="theme-card-desc">{{ p.desc }}</span>
            </div>
          </div>
        </div>

        <!-- Section 2: Typography Pairings -->
        <div>
          <h4 class="setup-label">Typography Pairing</h4>
          <div class="theme-options-grid">
            <div
              v-for="f in TYPOGRAPHY_THEMES"
              :key="f.id"
              class="theme-option-card"
              :class="{ active: customThemePrefs.typographyTheme === f.id }"
              @click="updateThemeSetting('typographyTheme', f.id)"
            >
              <span class="theme-card-title">{{ f.name }}</span>
              <span class="theme-card-desc" :style="{ fontFamily: f.fontHeader }">The quick brown fox</span>
            </div>
          </div>
        </div>

        <div class="reset-modal-actions">
          <button
            type="button"
            class="btn-orange-primary"
            @click="showThemeSettingsModal = false"
          >
            Apply &amp; Done
          </button>
        </div>
      </div>
    </div>

    <!-- =====================================================================
         STICKER & STAMP PALETTE DRAWER
         ===================================================================== -->
    <!-- Account Settings Modal -->
    <AccountSettingsModal
      v-if="showAccountSettingsModal"
      :current-user="currentUser"
      :api-base="API_BASE"
      :get-auth-headers="getAuthHeaders"
      @close="showAccountSettingsModal = false"
      @user-updated="handleUserUpdated"
    />

    <StickerTrayDrawer
      :is-open="isStickerDrawerOpen"
      :stickers="stickersList"
      :placements="stickerPlacements"
      :target-type="activeStickerTarget.type"
      :target-key="activeStickerTarget.key"
      :active-date-iso="selectedJournalDate"
      @close="isStickerDrawerOpen = false"
      @stamp-sticker="handleStampSticker"
      @upload-sticker="handleUploadSticker"
      @delete-sticker="handleDeleteSticker"
      @remove-placement="handleRemovePlacement"
    />

    <!-- Quick Calendar Task Creation Popover -->
    <QuickTaskPopover
      :open="quickTaskModalOpen"
      :initial-draft="quickTaskDraft"
      :projects="projects.filter((p) => p.status !== 'archived')"
      @close="quickTaskModalOpen = false"
      @submit="handleQuickTaskSubmit"
    />

    <!-- Global Command Palette (Ctrl/Cmd + K) -->
    <CommandPalette
      :open="showCommandPalette"
      :projects="projects.filter((p) => p.status !== 'archived')"
      :overdue-count="totalOverdueTasksCount"
      :api-base="API_BASE"
      :auth-headers="getAuthHeaders()"
      @close="showCommandPalette = false"
      @select-action="handleCommandPaletteAction"
    />

    <!-- Archive Vault Modal -->
    <ArchiveVaultModal
      :open="showArchiveModal"
      :archived-projects="archivedProjects"
      :project-tasks-map="projectTasksMap"
      @close="showArchiveModal = false"
      @restore="restoreArchivedProject($event)"
      @delete-permanent="deleteProject($event)"
    />

    <!-- Clean New Project Modal (Projects Board / List) -->
    <div
      v-if="showNewProjectModal"
      class="quick-popover-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="New Project"
      @click.self="showNewProjectModal = false"
    >
      <form class="quick-task-popover new-project-modal" @submit.prevent="createNewProject(null)">
        <div class="quick-popover-top">
          <span class="quick-popover-kicker">New Project</span>
          <button
            type="button"
            class="close-drawer-btn"
            @click="showNewProjectModal = false"
          >
            ✕
          </button>
        </div>
        <input
          v-model="newProject.name"
          type="text"
          class="quick-popover-title-input"
          placeholder="Project name…"
          required
          autofocus
        />
        <input
          v-model="newProject.description"
          type="text"
          class="input-minimal"
          placeholder="Scope or objective (optional)…"
        />
        <div class="quick-popover-row quick-dates-row">
          <label class="quick-field">
            <span>Folder / Area</span>
            <input
              v-model="newProject.area"
              type="text"
              list="project-area-suggestions"
              class="input-minimal"
              placeholder="Work, School, Personal…"
            />
          </label>
          <label class="quick-field">
            <span>Status</span>
            <select v-model="newProject.status" class="input-minimal">
              <option value="planned">Planned</option>
              <option value="active">Active</option>
              <option value="on_hold">On Hold</option>
              <option value="completed">Completed</option>
            </select>
          </label>
        </div>
        <div class="quick-popover-row quick-dates-row">
          <label class="quick-field">
            <span>Start date</span>
            <input v-model="newProject.start_date" type="date" class="input-minimal" />
          </label>
          <label class="quick-field">
            <span>Target date</span>
            <input v-model="newProject.target_date" type="date" class="input-minimal" />
          </label>
        </div>
        <div class="swatch-row">
          <span class="swatch-label">Tone</span>
          <input v-model="newProject.color" type="color" class="color-picker-mini" />
          <button
            v-for="sw in COLOR_SWATCHES"
            :key="sw"
            type="button"
            class="color-swatch-dot"
            :class="{ active: newProject.color === sw }"
            :style="{ backgroundColor: sw }"
            @click="newProject.color = sw"
          />
        </div>
        <label class="pin-check-inline">
          <input v-model="newProject.is_pinned" type="checkbox" />
          <span>Pin to Calendar Timeline</span>
        </label>
        <div class="quick-popover-footer">
          <button type="button" class="btn-editorial-ghost" @click="showNewProjectModal = false">
            Cancel
          </button>
          <button type="submit" class="btn-ink-primary">
            Create Project
          </button>
        </div>
      </form>
    </div>

    <!-- Folder / Area Suggestions Datalist -->
    <datalist id="project-area-suggestions">
      <option v-for="ar in projectAreas" :key="ar" :value="ar" />
      <option value="Work" />
      <option value="School" />
      <option value="Personal" />
    </datalist>

    <!-- Undo / Notification Snackbar -->
    <div v-if="toastNotification" class="toast-snackbar" role="status" aria-live="polite">
      <span class="toast-message">{{ toastNotification.message }}</span>
      <button
        v-if="toastNotification.undoLabel && toastNotification.undoFn"
        type="button"
        class="toast-undo-btn"
        @click="triggerToastUndo"
      >
        {{ toastNotification.undoLabel }}
      </button>
      <button
        type="button"
        class="toast-close-btn"
        aria-label="Dismiss"
        @click="dismissToast"
      >
        ✕
      </button>
    </div>
  </div>
</template>
