<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import LoginPage from "./LoginPage.vue";
import ChronoNoteLogo from "./ChronoNoteLogo.vue";
import HabitHeatmapView from "./HabitHeatmapView.vue";
import StudyModeView from "./StudyModeView.vue";
import StickerTrayDrawer from "./StickerTrayDrawer.vue";
import DocsImageOverlay from "./DocsImageOverlay.vue";
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
  computeProjectDragResult,
  computeSubtaskDragResult,
  computeYearMonthGridSpan,
  extractJournalSnippet,
  filterProjectsByStatus,
  filterSubtasksByStatus,
  formatEditorialDate,
  groupProjectsForKanban,
  isProjectCompleted,
  moveProjectInKanban,
  renderMarkdownPreviewHtml,
  shiftDateIso,
  shiftDateMonths,
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

// Daily Journal Drawer / Active Date state
// Clicking any date on Month View sets selectedJournalDate and opens the Journal Sheet!
const selectedJournalDate = ref("2026-11-01");
const isJournalDrawerOpen = ref(false);
const dailyJournalsMap = ref({ ...DEFAULT_DAILY_JOURNALS });
const journalDraftTitle = ref("Journal — 2026-11-01");
const journalDraftMd = ref(DEFAULT_DAILY_JOURNALS["2026-11-01"].content_md);
const journalSaveStatus = ref(""); // '' | 'saving' | 'saved'
const isEditingJournal = ref(false);
const journalTextareaRef = ref(null);
const drawerJournalTextareaRef = ref(null);

function startEditingJournal(isDrawer = false) {
  isEditingJournal.value = true;
  nextTick(() => {
    if (isDrawer) {
      drawerJournalTextareaRef.value?.focus();
    } else {
      journalTextareaRef.value?.focus();
    }
  });
}

async function stopEditingJournal() {
  isEditingJournal.value = false;
  await saveDailyJournalEntry();
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
const mcpCodeLoading = ref(false);
const mcpCodeError = ref("");
const mcpConnectData = ref(null);
const mcpCopied = ref(false);

async function openMcpConnectModal() {
  showMcpModal.value = true;
  mcpCodeLoading.value = true;
  mcpCodeError.value = "";
  mcpCopied.value = false;
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
  status: "active",
  color: "#b85423",
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
  color: "#2c666e",
});

// Calendar Timeline Controls
const calendarScaleMode = ref("month");
const selectedYear = ref(2026);
const selectedMonth = ref(11); // November
const todayIso = ref("2026-11-01");
const selectedWeekAnchorIso = ref("2026-11-01");

function switchToWeekMode() {
  calendarScaleMode.value = "week";
  const mStr = String(selectedMonth.value).padStart(2, "0");
  selectedWeekAnchorIso.value = `${selectedYear.value}-${mStr}-01`;
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

// Group all projects into the 4 Kanban columns
const projectKanbanColumns = computed(() =>
  groupProjectsForKanban(projects.value)
);

// Sidebar projects filtered by the current All | Active | Completed tab
const sidebarProjects = computed(() =>
  filterProjectsByStatus(
    projects.value.filter((p) => p.status !== "archived"),
    taskFilterMode.value
  )
);

// Pinned projects shown on the Timeline:
// - 'all': shows all pinned projects (active and done)
// - 'active': hides finished projects so only active projects appear
// - 'done': shows completed projects (or projects with completed subtasks)
const pinnedProjects = computed(() =>
  projects.value.filter((p) => {
    if (!p.is_pinned || p.status === "archived") return false;
    if (taskFilterMode.value === "active") {
      return !isProjectCompleted(p);
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
const selectedProject = computed(
  () => projects.value.find((p) => p.id === selectedProjectId.value) || null
);

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
  return filterSubtasksByStatus(withCodes, taskFilterMode.value);
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
      dailyNotesMap: dailyJournalsMap.value,
      todayIso: todayIso.value,
      visibleSubtaskProjectIds: visibleTimelineSubtaskProjectIds.value,
      allProjects: projects.value,
    }
  )
);

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

// Tasks active on the selected journal date across all projects
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

  const proj = projects.value.find((p) => p.id === projectId);
  if (!proj) return;

  const cardEl = event.currentTarget.closest(".week-item-card") || event.currentTarget;
  const container = cardEl.closest(".week-seven-col-area, .week-items-stack-grid, .year-twelve-months-grid");
  const containerRect = container ? container.getBoundingClientRect() : null;

  const numCols = scaleMode === "year" ? 12 : 7;
  const colWidth =
    containerRect && containerRect.width > 0
      ? containerRect.width / numCols
      : scaleMode === "year"
      ? 90
      : 120;

  const rowHeight = 72;
  const pStart = proj.start_date || todayIso.value;
  const pTarget = proj.target_date || pStart;

  if (taskId) {
    const list = projectTasksMap.value[projectId] || [];
    const task = list.find((t) => t.id === taskId);
    if (!task) return;
    const tStart = task.start_date || pStart;
    const tDue = task.due_date || tStart;

    activeTimelineDrag.value = {
      isTask: true,
      projectId,
      taskId,
      projectName: proj.name,
      taskTitle: task.title,
      type, // 'move' | 'resize-start' | 'resize-end'
      scaleMode, // 'month' | 'year'
      startX: event.clientX,
      startY: event.clientY,
      colWidth,
      rowHeight,
      projectStartIso: pStart,
      projectEndIso: pTarget,
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
      projectId,
      projectName: proj.name,
      type, // 'move' | 'resize-start' | 'resize-end'
      scaleMode, // 'month' | 'year'
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
  } else if (drag.scaleMode === "week") {
    const deltaCols = Math.round(deltaX / drag.colWidth);
    deltaDays = deltaCols;
  } else {
    const deltaCols = Math.round(deltaX / drag.colWidth);
    const deltaWeeks = Math.round(deltaY / (drag.rowHeight || 72));
    deltaDays = deltaCols + deltaWeeks * 7;
  }

  drag.deltaDays = deltaDays;

  if (drag.isTask) {
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
    openProjectDrawer(item.projectId, "subtasks");
  }
}

/**
 * Subtle, warm editorial card styling with a crisp left accent border
 * instead of heavy neon all-around borders.
 */
function getCustomColorCardStyle(hexColor, extraGridStyle = {}) {
  const c = hexColor || "#2c666e";
  return {
    ...extraGridStyle,
    borderColor: `${c}38`,
    borderLeft: `3.5px solid ${c}`,
    backgroundColor: `${c}10`,
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
    const today = new Date().toISOString().split("T")[0];
    await openDailyJournalForDate(today, false);
  }
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
        message: `Stamped ${sticker.name} onto ${target.type === 'calendar_date' ? target.key : 'note'}!`,
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

function handleUpdateFloatingImage({ id, x, y, width }) {
  const currentImages = journalFloatingImages.value;
  const target = currentImages.find((img) => img.id === id);
  if (!target) return;

  const newTag = formatDocsImageMarkdown(target.caption, target.url, target.mode, x, y, width);
  journalDraftMd.value = journalDraftMd.value.replace(target.rawDirective, newTag);
}

function handleChangeFloatingImageMode({ id, mode }) {
  const currentImages = journalFloatingImages.value;
  const target = currentImages.find((img) => img.id === id);
  if (!target) return;

  const newTag = formatDocsImageMarkdown(target.caption, target.url, mode, target.x, target.y, target.width);
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
      JSON.stringify(projects.value)
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
      projects.value = JSON.parse(rawP);
    } else if (!currentUser.value || email === "bryce@example.com") {
      projects.value = [...DEFAULT_PROJECTS];
    } else {
      // Clean isolated starter project for this specific newly registered user
      projects.value = [
        {
          id: Date.now(),
          name: "Personal Workspace",
          slug: "personal-workspace",
          description: `${currentUser.value.name || currentUser.value.email}'s synced workspace`,
          color: "#b85423",
          status: "active",
          is_pinned: true,
          sidebar_order: 0,
          start_date: "2026-11-01",
          target_date: "2026-11-30",
        },
      ];
    }

    if (rawT) {
      projectTasksMap.value = JSON.parse(rawT);
    } else {
      projectTasksMap.value = {};
    }
  } catch {
    projects.value = [];
    projectTasksMap.value = {};
  }
}

function clearWorkspaceData() {
  projects.value = [];
  projectTasksMap.value = {};
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
  const filtered = filterSubtasksByStatus(withCodes, taskFilterMode.value);

  const rows = [];
  let rowIndex = 2;

  for (let i = 0; i < filtered.length; i += 1) {
    const t = filtered[i];
    const span = computeYearMonthGridSpan(
      t.start_date,
      t.due_date,
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
    const res = await fetch(`${API_BASE}/sidebar/projects`, {
      headers: getAuthHeaders(),
    });
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
      for (const t of allTasks) {
        if (!grouped[t.project_id]) grouped[t.project_id] = [];
        grouped[t.project_id].push({
          ...t,
          color: t.color || "#2c666e",
        });
      }
      projectTasksMap.value = grouped;
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
    projectTasksMap.value = {};
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
    status: newProject.value.status,
    color: newProject.value.color || "#b85423",
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
      initTimelineNewProjectDates();
      showTimelineAddProject.value = false;
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
  initTimelineNewProjectDates();
  showTimelineAddProject.value = false;
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

async function deleteProject(projectId) {
  if (!projectId) return;
  const proj = projects.value.find((p) => p.id === projectId);
  const name = proj ? proj.name : "this project";
  if (
    !window.confirm(
      `Delete project "${name}" and all of its subtasks? This cannot be undone.`
    )
  ) {
    return;
  }
  projects.value = projects.value.filter((p) => p.id !== projectId);
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
  const payload = {
    project_id: pid,
    title: newSubtask.value.title.trim(),
    description: newSubtask.value.description ? newSubtask.value.description.trim() : "",
    status: "todo",
    color: newSubtask.value.color || "#2c666e",
    start_date: newSubtask.value.start_date || selectedProject.value.start_date,
    due_date: newSubtask.value.due_date || selectedProject.value.target_date,
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
      projectTasksMap.value[pid].push({
        ...created,
        color: created.color || payload.color,
      });
      persistLocalProjectsAndTasks();
      newSubtask.value.title = "";
      newSubtask.value.description = "";
      return;
    }
  } catch {
    // Local fallback
  }

  if (!projectTasksMap.value[pid]) projectTasksMap.value[pid] = [];
  projectTasksMap.value[pid].push({
    id: Date.now(),
    ...payload,
  });
  persistLocalProjectsAndTasks();
  newSubtask.value.title = "";
  newSubtask.value.description = "";
}

async function toggleSubtaskStatus(projectId, taskId) {
  const list = projectTasksMap.value[projectId] || [];
  const target = list.find((t) => t.id === taskId);
  if (!target) return;

  const nextStatus = target.status === "done" ? "todo" : "done";
  target.status = nextStatus;
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
  const list = projectTasksMap.value[projectId] || [];
  const target = list.find((t) => t.id === taskId);
  if (!target) return;
  Object.assign(target, patch);
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
  const list = projectTasksMap.value[projectId] || [];
  projectTasksMap.value[projectId] = list.filter((t) => t.id !== taskId);
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
  <div v-else class="editorial-app">
    <!-- =====================================================================
         EDITORIAL TOP BAR: Warm Serif Wordmark, Navigation Tabs & Google Account
         ===================================================================== -->
    <header class="minimal-topbar">
      <div class="brand-lockup">
        <span class="brand-mark" aria-hidden="true">
          <ChronoNoteLogo :size="22" />
        </span>
        <div class="brand-text">
          <span class="brand-accent">ChronoNote</span>
          <span class="brand-subtitle">Personal Journal &amp; Timeline</span>
        </div>
      </div>

      <nav class="primary-tabs" role="tablist" aria-label="Workspace Pages">
        <button
          type="button"
          class="page-tab-btn"
          :class="{ active: activePage === 'timeline' }"
          @click="activePage = 'timeline'"
        >
          Calendar Timeline
          <span class="tab-count">{{ pinnedProjects.length }}</span>
        </button>
        <button
          type="button"
          class="page-tab-btn"
          :class="{ active: activePage === 'journal' }"
          @click="
            if (requestJournalAccess(selectedJournalDate, false)) {
              activePage = 'journal';
              openDailyJournalForDate(selectedJournalDate, false);
            }
          "
        >
          Daily Journal
          <span class="tab-count">{{ sortedJournalEntries.length }}</span>
        </button>
        <button
          type="button"
          class="page-tab-btn"
          :class="{ active: activePage === 'kanban' }"
          @click="activePage = 'kanban'"
        >
          Projects Board
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
          Habits &amp; Heatmap
          <span
            v-if="habitAnalytics.overall_stats && habitAnalytics.overall_stats.best_current_streak"
            class="tab-count fire-tab-badge"
          >
            🔥 {{ habitAnalytics.overall_stats.best_current_streak }}d
          </span>
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
          Study &amp; Pomodoro
          <span class="tab-count study-badge-count">🍅 Focus</span>
        </button>
      </nav>

      <div class="topbar-right">
        <!-- Journal Security Pill -->
        <button
          type="button"
          class="btn-editorial-ghost journal-lock-pill-btn"
          :class="{ 'is-locked': hasJournalPassword && !isJournalUnlocked }"
          :title="
            hasJournalPassword
              ? (isJournalUnlocked
                  ? 'Journal is unlocked for this session. Click to lock now or change password.'
                  : 'Journal is locked. Click to enter password.')
              : 'Set a password to protect your journal notes.'
          "
          @click="
            hasJournalPassword && !isJournalUnlocked
              ? (showJournalUnlockModal = true)
              : (showJournalSettingsModal = true)
          "
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <template v-if="hasJournalPassword && !isJournalUnlocked">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </template>
            <template v-else>
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 9.9-1" />
            </template>
          </svg>
          <span v-if="!hasJournalPassword">Protect Journal</span>
          <span v-else-if="!isJournalUnlocked">Journal Locked</span>
          <span v-else>Journal Unlocked</span>
        </button>

        <button
          type="button"
          class="btn-editorial-ghost hide-on-mobile"
          @click="openDailyJournalForDate(selectedJournalDate, true)"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M12 20h9" />
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
          </svg>
          <span>Today’s Journal</span>
        </button>

        <!-- Stickers Drawer Toggle Button -->
        <button
          type="button"
          class="btn-editorial-ghost hide-on-mobile sticker-toggle-btn"
          :class="{ active: isStickerDrawerOpen }"
          title="Aesthetic Stickers & Stamps Palette"
          @click="
            activeStickerTarget = {
              type: activePage === 'journal' ? 'note' : 'calendar_date',
              key: activePage === 'journal' ? (activeNote?.id || selectedJournalDate) : selectedJournalDate
            };
            isStickerDrawerOpen = !isStickerDrawerOpen;
            if (isStickerDrawerOpen) {
              fetchStickers();
              fetchStickerPlacements();
            }
          "
        >
          <span>🌸 Stickers</span>
          <span v-if="stickerPlacements.length" class="tab-count">{{ stickerPlacements.length }}</span>
        </button>

        <!-- Theme Customizer Toggle Button -->
        <button
          type="button"
          class="btn-editorial-ghost hide-on-mobile theme-toggle-btn"
          title="Customize Paper Texture, Fonts & Appearance"
          @click="showThemeSettingsModal = true"
        >
          <span>🎨 Theme</span>
        </button>

        <!-- Google Account Pill / Sign-In Trigger -->
        <div v-if="currentUser" class="user-account-pill">
          <img
            v-if="currentUser.picture"
            :src="currentUser.picture"
            :alt="currentUser.name"
            class="user-avatar-img"
          />
          <span v-else class="user-avatar-monogram">
            {{ (currentUser.name || currentUser.email || "U").charAt(0).toUpperCase() }}
          </span>
          <span class="user-name-label">{{ currentUser.name || currentUser.email }}</span>
          <button
            type="button"
            class="mcp-connect-pill-btn"
            title="Connect Claude via MCP"
            @click="openMcpConnectModal"
          >
            🔌 Connect Claude
          </button>
          <button
            type="button"
            class="signout-link-btn"
            title="Sign out"
            @click="signOutUser"
          >
            Sign out
          </button>
        </div>

        <button
          v-else
          type="button"
          class="btn-google-signin"
          @click="showAuthModal = true"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" aria-hidden="true">
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
          <span>Sign in</span>
        </button>

        <button
          type="button"
          class="btn-editorial-ghost btn-reset-trigger hide-on-mobile"
          title="Reset Workspace & Delete All Data"
          @click="openResetModal"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
          <span>Reset Data</span>
        </button>
      </div>
    </header>

    <!-- =====================================================================
         PAGE 1: PROJECTS KANBAN BOARD
         ===================================================================== -->
    <main
      v-if="activePage === 'kanban'"
      class="kanban-page"
      aria-label="Projects Kanban Page"
    >
      <form class="new-project-bar" @submit.prevent="createNewProject(null)">
        <input
          v-model="newProject.name"
          type="text"
          class="input-minimal"
          placeholder="New project title…"
          required
        />
        <input
          v-model="newProject.description"
          type="text"
          class="input-minimal"
          placeholder="Brief scope or objective…"
        />
        <select v-model="newProject.status" class="input-minimal">
          <option value="planned">Planned</option>
          <option value="active">Active</option>
          <option value="on_hold">On Hold</option>
          <option value="completed">Completed</option>
        </select>
        <label class="date-field-inline">
          <span>Tone</span>
          <input
            v-model="newProject.color"
            type="color"
            class="color-picker-input"
          />
        </label>
        <label class="date-field-inline">
          <span>Start</span>
          <input
            v-model="newProject.start_date"
            type="date"
            class="input-minimal"
          />
        </label>
        <label class="date-field-inline">
          <span>Target</span>
          <input
            v-model="newProject.target_date"
            type="date"
            class="input-minimal"
          />
        </label>
        <label class="pin-check-inline">
          <input v-model="newProject.is_pinned" type="checkbox" />
          <span>Show on Timeline</span>
        </label>
        <button type="submit" class="btn-orange-primary">Add Project</button>
      </form>

      <div class="projects-kanban-grid">
        <section
          v-for="col in projectKanbanColumns"
          :key="col.status"
          class="project-kanban-column"
          :class="{
            'drag-over-column':
              draggedProjectId !== null && dragOverColumnStatus === col.status,
          }"
          @dragover.prevent="onColumnDragOver($event, col.status)"
          @dragleave="onColumnDragLeave($event, col.status)"
          @drop.prevent="onColumnDrop($event, col.status)"
        >
          <header class="kanban-col-header">
            <span class="col-title">{{ col.label }}</span>
            <span class="col-count">{{ col.count }}</span>
          </header>

          <div class="kanban-cards-stack">
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
              :style="getCustomColorCardStyle(proj.color || '#b85423')"
              @dragstart="onProjectDragStart($event, proj)"
              @dragend="onProjectDragEnd"
              @dragover.prevent.stop="onCardDragOver($event, proj, col.status)"
              @drop.prevent.stop="onCardDrop($event, proj, col.status)"
              @click="openProjectDrawer(proj.id, 'subtasks')"
            >
              <div class="pcard-top">
                <div class="pcard-title-row">
                  <span
                    class="drag-handle-grip"
                    title="Drag project to another column or reorder"
                    aria-hidden="true"
                  >
                    <svg
                      width="12"
                      height="14"
                      viewBox="0 0 12 14"
                      fill="currentColor"
                    >
                      <circle cx="3.5" cy="2.5" r="1.2" />
                      <circle cx="8.5" cy="2.5" r="1.2" />
                      <circle cx="3.5" cy="7" r="1.2" />
                      <circle cx="8.5" cy="7" r="1.2" />
                      <circle cx="3.5" cy="11.5" r="1.2" />
                      <circle cx="8.5" cy="11.5" r="1.2" />
                    </svg>
                  </span>
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
                        ? 'Mark project active (show on calendar)'
                        : 'Mark project done (hide from calendar)'
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
                  <input
                    type="color"
                    class="color-picker-mini"
                    :value="proj.color || '#b85423'"
                    title="Customize project color"
                    @click.stop
                    @input="
                      updateProjectFields(proj, { color: $event.target.value })
                    "
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
                    class="project-status-toggle-btn"
                    :class="{ done: isProjectCompleted(proj) }"
                    @click="toggleProjectDoneStatus(proj)"
                  >
                    {{ isProjectCompleted(proj) ? "✓ Done" : "Active" }}
                  </button>
                  <button
                    type="button"
                    class="pin-toggle-pill"
                    :class="{ pinned: proj.is_pinned }"
                    @click="
                      updateProjectFields(proj, { is_pinned: !proj.is_pinned })
                    "
                  >
                    {{ proj.is_pinned ? "Pinned" : "Pin" }}
                  </button>
                  <button
                    type="button"
                    class="delete-project-icon-btn"
                    title="Delete project"
                    @click="deleteProject(proj.id)"
                  >
                    🗑️
                  </button>
                </div>
              </div>

              <p v-if="proj.description" class="pcard-desc">
                {{ proj.description }}
              </p>

              <div class="pcard-dates" @click.stop>
                <label class="date-mini">
                  <span>Start</span>
                  <input
                    :value="proj.start_date"
                    type="date"
                    @change="
                      updateProjectFields(proj, {
                        start_date: $event.target.value,
                      })
                    "
                  />
                </label>
                <span class="date-arrow">→</span>
                <label class="date-mini">
                  <span>Target</span>
                  <input
                    :value="proj.target_date"
                    type="date"
                    @change="
                      updateProjectFields(proj, {
                        target_date: $event.target.value,
                      })
                    "
                  />
                </label>
              </div>

              <div class="pcard-footer" @click.stop>
                <div class="status-move-group">
                  <button
                    v-for="targetCol in projectKanbanColumns"
                    :key="targetCol.status"
                    v-show="targetCol.status !== col.status"
                    type="button"
                    class="move-chip"
                    @click="updateProjectFields(proj, { status: targetCol.status })"
                  >
                    → {{ targetCol.label }}
                  </button>
                </div>
                <div class="pcard-footer-actions">
                  <button
                    type="button"
                    class="kanban-subtasks-vis-btn"
                    :class="{ active: isProjectSubtasksVisible(proj.id) }"
                    :title="
                      isProjectSubtasksVisible(proj.id)
                        ? 'Subtasks are visible on timeline · Click to hide'
                        : 'Click to show subtasks on timeline even if project bar is unpinned'
                    "
                    @click="toggleProjectSubtasksVisibility(proj.id)"
                  >
                    {{ isProjectSubtasksVisible(proj.id) ? '👁️ Subtasks On' : '👁️‍🗨️ Subtasks' }}
                  </button>
                  <button
                    type="button"
                    class="note-link-btn"
                    @click="openProjectDrawer(proj.id, 'subtasks')"
                  >
                    Tasks ({{ (projectTasksMap[proj.id] || []).length }})
                  </button>
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
              <span>Drop project here</span>
            </div>
          </div>
        </section>
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
          <span class="sidebar-heading">DAILY ENTRIES</span>
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
            <div class="journal-title-editor-block">
              <span class="journal-kicker">{{ formattedJournalHeading.full }}</span>
              <input
                v-model="journalDraftTitle"
                type="text"
                class="journal-title-input editorial-serif-heading"
                :placeholder="`Journal — ${selectedJournalDate}`"
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
            <label class="btn-ocr-scanner">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                <circle cx="12" cy="13" r="4" />
              </svg>
              <span>Scan Handwritten Page (OCR)</span>
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
              <span>+ Image (Draggable)</span>
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
              <span>+ Image (Inline)</span>
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
              :title="hasJournalPassword ? 'Lock journal session now' : 'Set journal password'"
              @click="hasJournalPassword ? lockJournalSession() : (showJournalSettingsModal = true)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <span>{{ hasJournalPassword ? "Lock Session" : "Protect" }}</span>
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
                <div class="template-menu-header">APPLY TEMPLATE</div>
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

        <!-- Interactive Habit Quick Bar -->
        <div v-if="activeHabits.length > 0" class="journal-habit-quick-bar">
          <span class="habit-bar-kicker">HABITS</span>
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
          <!-- Draggable / Floating Images Layer (Docs style) -->
          <DocsImageOverlay
            v-if="journalFloatingImages.length"
            :images="journalFloatingImages"
            @update-image="handleUpdateFloatingImage"
            @change-mode="handleChangeFloatingImageMode"
            @delete-image="handleDeleteFloatingImage"
          />

          <!-- 1. Rendered Markdown View (Default) -->
          <div
            v-if="!isEditingJournal"
            class="journal-preview-paper clickable-paper"
            :class="[
              { 'is-empty': !journalDraftMd || !journalDraftMd.trim() },
              getPaperStyleClass(customThemePrefs.paperTheme),
              getTypographyClass(customThemePrefs.typographyTheme),
            ]"
            title="Click to write or edit markdown"
            @click="startEditingJournal(false)"
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
            <div class="journal-paper-status-badge">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
              <span>Click to edit markdown</span>
            </div>
          </div>

          <!-- 2. Notepad Textarea View (activated on focus/click; blur renders Markdown again & auto-saves) -->
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
              @blur="stopEditingJournal"
            />
            <div class="notepad-focusout-hint">
              <span>Markdown active &bull; Click outside or focus out to preview &amp; save</span>
            </div>
          </div>
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
        @session-completed="handleStudySessionCompleted"
        @note-updated="handleStudyNoteUpdated"
        @notify="showNotification"
      />
    </main>

    <!-- =====================================================================
         PAGE 3: SPACIOUS CALENDAR TIMELINE (Click any date for Daily Journal!)
         ===================================================================== -->
    <main v-else class="timeline-page" aria-label="Calendar Timeline Page">
      <!-- Mobile Projects Sidebar Toggle Bar -->
      <div class="mobile-sidebar-toggle-bar">
        <button
          type="button"
          class="btn-editorial-ghost"
          @click="showMobileProjectsSidebar = !showMobileProjectsSidebar"
        >
          {{
            showMobileProjectsSidebar
              ? "Hide Projects List"
              : `Projects (${pinnedProjects.length} pinned)`
          }}
        </button>
        <button
          type="button"
          class="btn-ocr-scanner"
          @click="openDailyJournalForDate(selectedJournalDate, true)"
        >
          Open {{ formattedJournalHeading.short }} Journal
        </button>
      </div>

      <!-- Left Sidebar: Pick Pinned Projects + Add New Project Directly to Timeline -->
      <aside
        class="timeline-left-sidebar"
        :class="{ 'mobile-open': showMobileProjectsSidebar }"
        aria-label="Projects Sidebar"
      >
        <div class="sidebar-top-row">
          <span class="sidebar-heading">PROJECTS ON TIMELINE</span>
          <button
            type="button"
            class="btn-orange-mini"
            @click="toggleTimelineAddProject"
          >
            {{ showTimelineAddProject ? "Cancel" : "+ New" }}
          </button>
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
            <span class="swatch-label">Tone:</span>
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
          <button type="submit" class="btn-orange-primary">
            Add &amp; Pin to Timeline
          </button>
        </form>

        <p class="sidebar-hint">
          Select a project to manage subtasks, or click any date on the calendar to open that day’s journal.
        </p>

        <div class="sidebar-project-picker">
          <div
            v-for="proj in sidebarProjects"
            :key="proj.id"
            class="picker-row clickable-card"
            :class="{
              active: proj.is_pinned,
              'is-completed-project-row': isProjectCompleted(proj),
            }"
            :style="{
              borderLeft: `3.5px solid ${proj.color || '#b85423'}`,
              borderColor:
                selectedProjectId === proj.id
                  ? proj.color || '#b85423'
                  : undefined,
            }"
            @click="openProjectDrawer(proj.id, 'subtasks')"
          >
            <div class="picker-top-line">
              <label
                class="picker-label"
                title="Pin or unpin from calendar"
                @click.stop
              >
                <input
                  type="checkbox"
                  :checked="proj.is_pinned"
                  @change="
                    updateProjectFields(proj, {
                      is_pinned: $event.target.checked,
                    })
                  "
                />
              </label>
              <span
                class="picker-name"
                :class="{ 'strikethrough-done': isProjectCompleted(proj) }"
              >
                {{ proj.name }}
              </span>
              <button
                type="button"
                class="project-status-toggle-btn"
                :class="{ done: isProjectCompleted(proj) }"
                :title="
                  isProjectCompleted(proj)
                    ? 'Project is Done — click to mark Active'
                    : 'Project is Active — click to mark Done'
                "
                @click.stop="toggleProjectDoneStatus(proj)"
              >
                {{ isProjectCompleted(proj) ? "✓ Done" : "Active" }}
              </button>
              <input
                type="color"
                class="color-picker-mini"
                :value="proj.color || '#b85423'"
                title="Change project color"
                @click.stop
                @input="
                  updateProjectFields(proj, { color: $event.target.value })
                "
              />
              <button
                type="button"
                class="sidebar-del-btn"
                title="Delete project"
                @click.stop="deleteProject(proj.id)"
              >
                ✕
              </button>
            </div>
            <div class="picker-dates">
              <span class="mono-dates">
                {{ proj.start_date || "—" }} → {{ proj.target_date || "—" }}
              </span>
              <div class="picker-subtask-btns" @click.stop>
                <button
                  type="button"
                  class="sidebar-timeline-subtask-toggle"
                  :class="{ active: isProjectSubtasksVisible(proj.id) }"
                  :title="
                    isProjectSubtasksVisible(proj.id)
                      ? 'Subtasks are visible on timeline · Click to hide'
                      : 'Show subtasks on timeline even if project bar is unpinned'
                  "
                  @click="toggleProjectSubtasksVisibility(proj.id)"
                >
                  {{ isProjectSubtasksVisible(proj.id) ? '👁️ Subtasks On' : '👁️‍🗨️ Subtasks' }}
                </button>
                <button
                  type="button"
                  class="sidebar-subtask-pill"
                  title="Open subtasks manager drawer"
                  @click="openProjectDrawer(proj.id, 'subtasks')"
                >
                  {{ (projectTasksMap[proj.id] || []).length }} tasks
                </button>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <!-- Calendar Year / Month Surface -->
      <section class="calendar-timeline-surface">
        <!-- Calendar Toolbar -->
        <header class="calendar-toolbar">
          <div class="calendar-nav">
            <button
              type="button"
              class="nav-step-btn"
              aria-label="Previous period"
              @click="stepCalendar(-1)"
            >
              ‹
            </button>
            <h2 class="calendar-current-label">
              {{
                calendarScaleMode === "year"
                  ? `${selectedYear} Annual Overview`
                  : calendarScaleMode === "week"
                  ? `${focusedWeekSpec.rangeText}`
                  : `${monthlyWeeksSpec.monthName} ${selectedYear}`
              }}
            </h2>
            <button
              type="button"
              class="nav-step-btn"
              aria-label="Next period"
              @click="stepCalendar(1)"
            >
              ›
            </button>
          </div>

          <div class="scale-Right-controls">
            <!-- Subtask Filter: All | Active | Done -->
            <div class="segmented-scale" aria-label="Subtask Status Filter">
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
                class="scale-btn"
                :class="{ active: taskFilterMode === 'done' }"
                @click="taskFilterMode = 'done'"
              >
                Completed
              </button>
            </div>

            <div v-if="calendarScaleMode === 'month'" class="month-quick-pills">
              <button
                v-for="m in 12"
                :key="m"
                type="button"
                class="month-pill"
                :class="{ active: selectedMonth === m }"
                @click="selectedMonth = m"
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

            <div class="segmented-scale">
              <button
                type="button"
                class="scale-btn"
                :class="{ active: calendarScaleMode === 'year' }"
                @click="calendarScaleMode = 'year'"
              >
                Year
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
                :class="{ active: calendarScaleMode === 'week' }"
                @click="switchToWeekMode"
              >
                Week
              </button>
            </div>

            <button
              type="button"
              class="scale-btn subtasks-all-toggle-btn"
              :title="visibleTimelineSubtaskProjectIds.size > 0 ? 'Hide subtasks on timeline' : 'Show subtasks on timeline'"
              @click="visibleTimelineSubtaskProjectIds.size > 0 ? collapseAllTimelineSubtasks() : expandAllTimelineSubtasks()"
            >
              {{ visibleTimelineSubtaskProjectIds.size > 0 ? 'Hide Subtasks' : 'Show Subtasks' }}
            </button>
          </div>
        </header>

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
                <span class="week-badge">Week {{ week.weekNumber }}</span>
                <span class="week-range-sub">
                  {{ week.days[0].monthShort }} {{ week.days[0].dayNum }} –
                  {{ week.days[6].monthShort }} {{ week.days[6].dayNum }}
                </span>
              </div>

              <div class="week-seven-col-area">
                <!-- Interactive Day Header Strip: Click ANY date to open/write that day's Journal -->
                <div class="week-day-numbers-strip">
                  <button
                    v-for="day in week.days"
                    :key="day.iso"
                    type="button"
                    class="week-day-num-cell"
                    :class="{
                      'outside-month': !day.inMonth,
                      'has-journal-entry': day.hasJournal,
                      'is-selected-journal-day':
                        isJournalDrawerOpen && selectedJournalDate === day.iso,
                    }"
                    :title="`Click to open journal for ${day.iso}`"
                    @click="openDailyJournalForDate(day.iso, true)"
                  >
                    <div class="day-cell-top-row">
                      <span class="day-number-pill">
                        {{ day.dayNum }}
                        <small v-if="!day.inMonth" class="day-month-hint">
                          {{ day.monthShort }}
                        </small>
                      </span>
                      <span v-if="day.hasJournal" class="day-journal-indicator" :title="day.journalTitle || 'Journal'">
                        {{ day.journalTitle || "Journal" }}
                      </span>
                      <span v-else class="day-journal-hover-hint">
                        + Note
                      </span>
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
                  </button>
                </div>

                <div class="week-items-stack-grid">
                  <div class="week-bg-guides">
                    <div
                      v-for="day in week.days"
                      :key="day.iso"
                      class="week-bg-col"
                      @click="openDailyJournalForDate(day.iso, true)"
                    />
                  </div>

                  <div
                    v-for="item in week.items"
                    :key="item.uid"
                    class="week-item-card clickable-card"
                    :class="{
                      'is-done-card': item.status === 'done',
                      'is-project-bar': item.kind === 'project',
                      'is-draggable-project': item.kind === 'project',
                      'is-subtask-bar': item.kind === 'task',
                      'is-draggable-task': item.kind === 'task',
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
                          class="color-badge-solid"
                          :style="{ backgroundColor: item.color }"
                        >
                          {{ item.code }} · Project
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
                          class="color-badge-mono"
                          :style="{ color: item.color, borderColor: `${item.color}44` }"
                        >
                          {{ item.code }}
                        </span>
                      </template>

                      <strong
                        class="week-item-title"
                        :class="{
                          'strikethrough-done': item.status === 'done',
                        }"
                      >
                        {{ item.title }}
                      </strong>

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
                        {{ (projectTasksMap[item.projectId] || []).length }} subtasks
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
             MODE B: WEEK VIEW — 1 FOCUSED 7-DAY TIMELINE ROW
             =============================================================== -->
        <div
          v-else-if="calendarScaleMode === 'week'"
          class="monthly-weeks-scroll-wrapper focused-week-scroll-wrapper"
        >
          <div class="monthly-weeks-container">
            <div class="weekday-header-row">
              <div class="week-label-col">Focus</div>
              <div
                v-for="dow in WEEKDAY_SHORT"
                :key="dow"
                class="weekday-col-head"
              >
                {{ dow }}
              </div>
            </div>

            <div class="week-calendar-row is-focused-single-week">
              <div class="week-side-cell">
                <span class="week-badge">Week View</span>
                <span class="week-range-sub">
                  {{ focusedWeekSpec.days[0].monthShort }} {{ focusedWeekSpec.days[0].dayNum }} –
                  {{ focusedWeekSpec.days[6].monthShort }} {{ focusedWeekSpec.days[6].dayNum }}
                </span>
              </div>

              <div class="week-seven-col-area">
                <!-- Interactive Day Header Strip: Click any date to open/write Journal -->
                <div class="week-day-numbers-strip">
                  <button
                    v-for="day in focusedWeekSpec.days"
                    :key="day.iso"
                    type="button"
                    class="week-day-num-cell"
                    :class="{
                      'has-journal-entry': day.hasJournal,
                      'is-selected-journal-day':
                        isJournalDrawerOpen && selectedJournalDate === day.iso,
                    }"
                    :title="`Click to open journal for ${day.iso}`"
                    @click="openDailyJournalForDate(day.iso, true)"
                  >
                    <div class="day-cell-top-row">
                      <span class="day-number-pill">
                        {{ day.dayNum }}
                        <small class="day-month-hint">
                          {{ day.monthShort }}
                        </small>
                      </span>
                      <span v-if="day.hasJournal" class="day-journal-indicator" :title="day.journalTitle || 'Journal'">
                        {{ day.journalTitle || "Journal" }}
                      </span>
                      <span v-else class="day-journal-hover-hint">
                        + Note
                      </span>
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
                  </button>
                </div>

                <div class="week-items-stack-grid">
                  <div class="week-bg-guides">
                    <div
                      v-for="day in focusedWeekSpec.days"
                      :key="day.iso"
                      class="week-bg-col"
                      @click="openDailyJournalForDate(day.iso, true)"
                    />
                  </div>

                  <div
                    v-for="item in focusedWeekSpec.items"
                    :key="item.uid"
                    class="week-item-card clickable-card"
                    :class="{
                      'is-done-card': item.status === 'done',
                      'is-project-bar': item.kind === 'project',
                      'is-draggable-project': item.kind === 'project',
                      'is-subtask-bar': item.kind === 'task',
                      'is-draggable-task': item.kind === 'task',
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
                        ? startTimelineDrag($event, item.projectId, 'move', 'week')
                        : startTimelineDrag($event, item.projectId, 'move', 'week', item.taskId)
                    "
                    @click="handleTimelineCardClick(item)"
                  >
                    <!-- Left Resize Handle: Project or Subtask -->
                    <div
                      class="timeline-resize-handle handle-left"
                      :title="item.kind === 'project' ? 'Drag to stretch project start date' : 'Drag to stretch subtask start date'"
                      @pointerdown.stop.prevent="
                        item.kind === 'project'
                          ? startTimelineDrag(
                              $event,
                              item.projectId,
                              'resize-start',
                              'week'
                            )
                          : startTimelineDrag(
                              $event,
                              item.projectId,
                              'resize-start',
                              'week',
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
                          class="color-badge-solid"
                          :style="{ backgroundColor: item.color }"
                        >
                          {{ item.code }} · Project
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
                          class="color-badge-mono"
                          :style="{ color: item.color, borderColor: `${item.color}44` }"
                        >
                          {{ item.code }}
                        </span>
                      </template>

                      <strong
                        class="week-item-title"
                        :class="{
                          'strikethrough-done': item.status === 'done',
                        }"
                      >
                        {{ item.title }}
                      </strong>

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
                        {{ (projectTasksMap[item.projectId] || []).length }} subtasks
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
                      :title="item.kind === 'project' ? 'Drag to stretch project target date' : 'Drag to stretch subtask due date'"
                      @pointerdown.stop.prevent="
                        item.kind === 'project'
                          ? startTimelineDrag(
                              $event,
                              item.projectId,
                              'resize-end',
                              'week'
                            )
                          : startTimelineDrag(
                              $event,
                              item.projectId,
                              'resize-end',
                              'week',
                              item.taskId
                            )
                      "
                    />
                  </div>

                  <div v-if="focusedWeekSpec.items.length === 0" class="week-empty-spacer" />
                </div>
              </div>
            </div>
          </div>
        </div>

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

                <!-- Row 2..N: Subtasks stacked vertically (Draggable & Stretchable) -->
                <div
                  v-for="task in getYearProjectTaskRows(proj.id, pIdx)"
                  :key="task.id"
                  class="week-item-card clickable-card is-subtask-bar is-draggable-task"
                  :class="{
                    'is-done-card': task.status === 'done',
                    'is-currently-dragged':
                      activeTimelineDrag &&
                      activeTimelineDrag.isTask &&
                      activeTimelineDrag.taskId === task.id,
                  }"
                  :style="task.gridStyle"
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
                :placeholder="`Journal — ${selectedJournalDate}`"
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
                <div class="template-menu-header">APPLY TEMPLATE</div>
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
            <span class="habit-bar-kicker">HABITS</span>
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

          <!-- 1. Rendered Markdown View (Default) -->
          <div
            v-if="!isEditingJournal"
            class="journal-preview-paper drawer-preview clickable-paper"
            :class="{ 'is-empty': !journalDraftMd || !journalDraftMd.trim() }"
            title="Click to write or edit markdown"
            @click="startEditingJournal(true)"
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
            <div class="journal-paper-status-badge">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
              <span>Click to edit markdown</span>
            </div>
          </div>

          <!-- 2. Notepad Textarea View (activated on focus/click; blur renders Markdown & auto-saves) -->
          <div v-else class="journal-notepad-wrapper">
            <textarea
              ref="drawerJournalTextareaRef"
              v-model="journalDraftMd"
              class="journal-ruled-textarea live-journal-notepad"
              :placeholder="`Write down your notes for ${formattedJournalHeading.full}…`"
              spellcheck="false"
              @blur="stopEditingJournal"
            />
            <div class="notepad-focusout-hint">
              <span>Markdown active &bull; Click outside or focus out to preview &amp; save</span>
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
                  : "✓ Mark Project Done"
              }}
            </button>
            <button
              type="button"
              class="delete-project-btn"
              title="Delete this project"
              @click="deleteProject(selectedProject.id)"
            >
              🗑️ Delete
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

        <div class="slideover-project-desc-row">
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

        <div class="slideover-project-settings">
          <div class="swatch-row">
            <span class="swatch-label">Tone:</span>
            <input
              type="color"
              class="color-picker-mini"
              :value="selectedProject.color || '#b85423'"
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
              <button type="submit" class="btn-orange-primary">
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
              <span class="danger-kicker">DANGER ZONE</span>
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
          if (requestJournalAccess(selectedJournalDate, false)) {
            activePage = 'journal';
            openDailyJournalForDate(selectedJournalDate, false);
          }
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
  </div>
</template>
