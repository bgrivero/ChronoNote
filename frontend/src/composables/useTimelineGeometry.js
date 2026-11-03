/**
 * Composable utilities for ChronoNote's Vue 3 Projects Kanban (Tab 1),
 * Spacious Calendar Year & 1-Row-Per-Week Monthly Timeline (Tab 2),
 * and Live Markdown Editor.
 */

const MS_PER_DAY = 86_400_000;
const MONTH_NAMES_SHORT = [
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
];
const MONTH_NAMES_FULL = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];
export const WEEKDAY_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const WEEKDAY_FULL = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
];

/**
 * Extract a clean, readable plain-text snippet from a Markdown journal note.
 * @param {string | null | undefined} contentMd
 * @param {number} maxLength
 * @returns {string}
 */
export function extractJournalSnippet(contentMd, maxLength = 54) {
  if (!contentMd || typeof contentMd !== "string") return "";
  const strippedFrontmatter = contentMd.replace(
    /^---\s*\r?\n[\s\S]*?\r?\n---\s*(?:\r?\n|$)/,
    ""
  );
  const lines = strippedFrontmatter
    .split(/\r?\n/)
    .map((line) =>
      line
        .replace(/^#+\s*/, "")
        .replace(/^\s*[-*]\s+\[[ xX]\]\s*/, "")
        .replace(/^\s*[-*]\s+/, "")
        .replace(/\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]/g, (_, target, alias) => alias || target)
        .replace(/@(start|due|priority)\([^)]+\)/gi, "")
        .replace(/@milestone\b/gi, "")
        .trim()
    )
    .filter((line) => line.length > 0 && !/^journal\s*[—-]/i.test(line) && !/^daily note/i.test(line));

  const joined = lines.join(" · ").replace(/\s+/g, " ").trim();
  if (!joined) return "";
  if (joined.length <= maxLength) return joined;
  return `${joined.slice(0, maxLength - 1).trimEnd()}…`;
}

/**
 * Format an ISO YYYY-MM-DD date string into an editorial human-readable heading.
 * @param {string} isoDate
 */
export function formatEditorialDate(isoDate) {
  const utcMs = parseIsoDateUtc(isoDate);
  if (utcMs === null) {
    return { full: isoDate || "", weekday: "", short: isoDate || "", dayNum: "" };
  }
  const dt = new Date(utcMs);
  const weekday = WEEKDAY_FULL[dt.getUTCDay()];
  const monthFull = MONTH_NAMES_FULL[dt.getUTCMonth()];
  const monthShort = MONTH_NAMES_SHORT[dt.getUTCMonth()];
  const dayNum = dt.getUTCDate();
  const year = dt.getUTCFullYear();
  return {
    full: `${weekday}, ${monthFull} ${dayNum}, ${year}`,
    weekday,
    short: `${monthShort} ${dayNum}, ${year}`,
    dayNum: `${dayNum}`,
    monthShort,
    year: `${year}`,
  };
}

/**
 * Parse an ISO YYYY-MM-DD date string into UTC midnight timestamp (ms).
 * @param {string | null | undefined} isoDate
 * @returns {number | null}
 */
export function parseIsoDateUtc(isoDate) {
  if (!isoDate || typeof isoDate !== "string") return null;
  const parts = isoDate.split("-").map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return null;
  return Date.UTC(parts[0], parts[1] - 1, parts[2]);
}

/**
 * Format a UTC midnight timestamp (ms) back into YYYY-MM-DD.
 * @param {number} utcMs
 * @returns {string}
 */
export function formatIsoDateUtc(utcMs) {
  return new Date(utcMs).toISOString().slice(0, 10);
}

/**
 * Shift an ISO YYYY-MM-DD date string by a given number of days.
 * @param {string | null | undefined} isoDate
 * @param {number} deltaDays
 * @returns {string}
 */
export function shiftDateIso(isoDate, deltaDays = 0) {
  const ms = parseIsoDateUtc(isoDate);
  if (ms === null) return isoDate || "";
  return formatIsoDateUtc(ms + deltaDays * MS_PER_DAY);
}

/**
 * Shift an ISO YYYY-MM-DD date string by a given number of months.
 * Clamps to the last day of the target month if needed.
 * @param {string | null | undefined} isoDate
 * @param {number} deltaMonths
 * @returns {string}
 */
export function shiftDateMonths(isoDate, deltaMonths = 0) {
  const ms = parseIsoDateUtc(isoDate);
  if (ms === null) return isoDate || "";
  const d = new Date(ms);
  const curYear = d.getUTCFullYear();
  const curMonth = d.getUTCMonth();
  const curDay = d.getUTCDate();

  const targetDate = new Date(Date.UTC(curYear, curMonth + deltaMonths, 1));
  const maxDays = new Date(
    Date.UTC(targetDate.getUTCFullYear(), targetDate.getUTCMonth() + 1, 0)
  ).getUTCDate();
  const safeDay = Math.min(curDay, maxDays);
  return formatIsoDateUtc(
    Date.UTC(targetDate.getUTCFullYear(), targetDate.getUTCMonth(), safeDay)
  );
}

/**
 * Calculate the inclusive number of days between two ISO YYYY-MM-DD dates.
 * @param {string | null | undefined} startIso
 * @param {string | null | undefined} endIso
 * @returns {number}
 */
export function calculateDateSpanDays(startIso, endIso) {
  const s = parseIsoDateUtc(startIso);
  const e = parseIsoDateUtc(endIso);
  if (s === null || e === null) return 1;
  return Math.max(Math.round((e - s) / MS_PER_DAY) + 1, 1);
}

function clampIso(iso, minIso, maxIso) {
  if (!iso) return iso;
  if (minIso && iso < minIso) return minIso;
  if (maxIso && iso > maxIso) return maxIso;
  return iso;
}

/**
 * Clip a single subtask's [start, due] range so it never falls before the
 * parent project's start or after its target date.
 * @param {{start_date?: string, due_date?: string}} task
 * @param {string} projectStartIso
 * @param {string} projectEndIso
 * @returns {{start_date: string, due_date: string}}
 */
export function clipSubtaskToProjectRange(task, projectStartIso, projectEndIso) {
  const rawStart = task.start_date || task.due_date || projectStartIso;
  const rawDue = task.due_date || task.start_date || projectEndIso;
  let start = clampIso(rawStart, projectStartIso, projectEndIso);
  let due = clampIso(rawDue, projectStartIso, projectEndIso);
  if (start > due) start = due;
  return { start_date: start, due_date: due };
}

/**
 * Compute new project dates + clipped subtask dates while dragging a project.
 * - 'move': the project and all subtasks shift together by deltaDays.
 * - 'resize-start' / 'resize-end': the project range changes and subtasks are
 *   clipped so none start before or end after the project.
 *
 * @param {{start_date: string, target_date: string}} origProject
 * @param {Array<{id: any, start_date?: string, due_date?: string}>} origTasks
 * @param {'move' | 'resize-start' | 'resize-end'} type
 * @param {number} deltaDays
 */
export function computeProjectDragResult(origProject, origTasks, type, deltaDays) {
  const oStart = origProject.start_date;
  const oEnd = origProject.target_date || oStart;
  let start = oStart;
  let end = oEnd;

  if (type === "move") {
    start = shiftDateIso(oStart, deltaDays);
    end = shiftDateIso(oEnd, deltaDays);
  } else if (type === "resize-start") {
    start = shiftDateIso(oStart, deltaDays);
    if (start > oEnd) start = oEnd;
  } else if (type === "resize-end") {
    end = shiftDateIso(oEnd, deltaDays);
    if (end < oStart) end = oStart;
  }

  const tasks = (origTasks || []).map((t) => {
    const shifted =
      type === "move"
        ? {
            start_date: t.start_date ? shiftDateIso(t.start_date, deltaDays) : t.start_date,
            due_date: t.due_date ? shiftDateIso(t.due_date, deltaDays) : t.due_date,
          }
        : { start_date: t.start_date, due_date: t.due_date };
    return { id: t.id, ...clipSubtaskToProjectRange(shifted, start, end) };
  });

  return { start_date: start, target_date: end, tasks };
}

/**
 * Compute new subtask dates while dragging/resizing a subtask, constrained to
 * the parent project's [start, target] range.
 * - 'move' keeps the duration and stops at the project boundaries.
 * - 'resize-start' / 'resize-end' stretch one edge without crossing the other
 *   edge or the project boundaries.
 *
 * @param {{start_date: string, due_date: string}} origTask
 * @param {string} projectStartIso
 * @param {string} projectEndIso
 * @param {'move' | 'resize-start' | 'resize-end'} type
 * @param {number} deltaDays
 */
export function computeSubtaskDragResult(
  origTask,
  projectStartIso,
  projectEndIso,
  type,
  deltaDays
) {
  const base = clipSubtaskToProjectRange(origTask, projectStartIso, projectEndIso);
  let start = base.start_date;
  let due = base.due_date;

  if (type === "move") {
    const durationDays = calculateDateSpanDays(start, due) - 1;
    const projSpan = calculateDateSpanDays(projectStartIso, projectEndIso) - 1;
    if (durationDays >= projSpan) {
      return { start_date: projectStartIso, due_date: projectEndIso };
    }
    let nextStart = shiftDateIso(start, deltaDays);
    if (nextStart < projectStartIso) nextStart = projectStartIso;
    let nextDue = shiftDateIso(nextStart, durationDays);
    if (nextDue > projectEndIso) {
      nextDue = projectEndIso;
      nextStart = shiftDateIso(nextDue, -durationDays);
    }
    return { start_date: nextStart, due_date: nextDue };
  }

  if (type === "resize-start") {
    start = clampIso(shiftDateIso(start, deltaDays), projectStartIso, due);
  } else if (type === "resize-end") {
    due = clampIso(shiftDateIso(due, deltaDays), start, projectEndIso);
  }
  return { start_date: start, due_date: due };
}

/**
 * Filter and partition projects for the Left Sidebar into pinned and active lists.
 */
export function partitionSidebarProjects(projects, options = {}) {
  const query = (options.query || "").trim().toLowerCase();
  const statusFilter = options.status || null;

  const filtered = (projects || []).filter((p) => {
    if (statusFilter && p.status !== statusFilter) return false;
    if (!statusFilter && p.status === "archived") return false;
    if (query) {
      const hay = `${p.name || ""} ${p.description || ""} ${p.slug || ""}`.toLowerCase();
      return hay.includes(query);
    }
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    if (Boolean(a.is_pinned) !== Boolean(b.is_pinned)) {
      return a.is_pinned ? -1 : 1;
    }
    const orderDiff = (a.sidebar_order ?? 0) - (b.sidebar_order ?? 0);
    if (orderDiff !== 0) return orderDiff;
    return (a.id ?? 0) - (b.id ?? 0);
  });

  return {
    all: sorted,
    pinned: sorted.filter((p) => Boolean(p.is_pinned)),
    regular: sorted.filter((p) => !p.is_pinned),
  };
}

/**
 * Group projects into the 4 Project Kanban columns (planned, active, on_hold, completed).
 */
export function groupProjectsForKanban(projects) {
  const columns = [
    { status: "planned", label: "Planned", projects: [] },
    { status: "active", label: "Active", projects: [] },
    { status: "on_hold", label: "On Hold", projects: [] },
    { status: "completed", label: "Completed", projects: [] },
  ];
  const map = Object.fromEntries(columns.map((c) => [c.status, c]));
  for (const p of projects || []) {
    if (p.status === "archived") continue;
    const bucket = map[p.status] || map.planned;
    bucket.projects.push(p);
  }
  return columns.map((c) => ({ ...c, count: c.projects.length }));
}

/**
 * Move and/or reorder a project across or within Kanban columns.
 * Updates the dragged project's status to `targetStatus`, places it relative to
 * `targetProjectId` (when provided) or at the end of the target column, and
 * normalizes `sidebar_order` across all projects.
 *
 * @param {Array<Object>} projects
 * @param {number | string} draggedProjectId
 * @param {'planned' | 'active' | 'on_hold' | 'completed'} targetStatus
 * @param {{ targetProjectId?: number | string | null, position?: 'before' | 'after' }} options
 */
export function moveProjectInKanban(
  projects,
  draggedProjectId,
  targetStatus,
  options = {}
) {
  const list = Array.isArray(projects) ? projects.map((p) => ({ ...p })) : [];
  const draggedIdx = list.findIndex(
    (p) => String(p.id) === String(draggedProjectId)
  );
  if (draggedIdx === -1) {
    return {
      projects: list,
      movedProject: null,
      orderedProjectIds: list.map((p) => p.id),
    };
  }

  const validStatuses = new Set(["planned", "active", "on_hold", "completed"]);
  const nextStatus = validStatuses.has(targetStatus)
    ? targetStatus
    : list[draggedIdx].status;

  const [movedProject] = list.splice(draggedIdx, 1);
  movedProject.status = nextStatus;

  const targetProjectId = options.targetProjectId ?? null;
  const position = options.position === "before" ? "before" : "after";

  if (
    targetProjectId !== null &&
    String(targetProjectId) !== String(draggedProjectId)
  ) {
    const targetIdx = list.findIndex(
      (p) => String(p.id) === String(targetProjectId)
    );
    if (targetIdx !== -1) {
      const insertIdx = position === "before" ? targetIdx : targetIdx + 1;
      list.splice(insertIdx, 0, movedProject);
    } else {
      list.push(movedProject);
    }
  } else {
    // Dropped onto column container: place after the last project in that status column (or end of list)
    let lastInColIdx = -1;
    for (let i = 0; i < list.length; i += 1) {
      if (list[i].status === nextStatus) {
        lastInColIdx = i;
      }
    }
    if (lastInColIdx !== -1) {
      list.splice(lastInColIdx + 1, 0, movedProject);
    } else {
      list.push(movedProject);
    }
  }

  const reindexed = list.map((proj, idx) => ({
    ...proj,
    sidebar_order: idx,
  }));
  const updatedMoved =
    reindexed.find((p) => String(p.id) === String(draggedProjectId)) ||
    movedProject;

  return {
    projects: reindexed,
    movedProject: updatedMoved,
    orderedProjectIds: reindexed.map((p) => p.id),
  };
}

/**
 * Build Calendar Timeline columns for Year mode (12 months) or Month mode.
 */
export function buildCalendarTimelineColumns(year, month = null) {
  const pad2 = (n) => String(n).padStart(2, "0");

  if (month === null || month === undefined) {
    const columns = [];
    for (let m = 1; m <= 12; m += 1) {
      const lastDay = new Date(Date.UTC(year, m, 0)).getUTCDate();
      const startIso = `${year}-${pad2(m)}-01`;
      const endIso = `${year}-${pad2(m)}-${pad2(lastDay)}`;
      columns.push({
        index: m,
        key: `${year}-${pad2(m)}`,
        label: MONTH_NAMES_SHORT[m - 1],
        subLabel: `${year}`,
        startIso,
        endIso,
      });
    }
    return {
      mode: "year",
      year,
      month: null,
      windowStartIso: `${year}-01-01`,
      windowEndIso: `${year}-12-31`,
      columns,
    };
  }

  const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const columns = [];
  for (let d = 1; d <= lastDay; d += 1) {
    const dtUtc = new Date(Date.UTC(year, month - 1, d));
    const dow = WEEKDAY_SHORT[dtUtc.getUTCDay()];
    const iso = `${year}-${pad2(month)}-${pad2(d)}`;
    columns.push({
      index: d,
      key: iso,
      label: `${d}`,
      subLabel: dow,
      startIso: iso,
      endIso: iso,
    });
  }

  return {
    mode: "month",
    year,
    month,
    monthName: MONTH_NAMES_SHORT[month - 1],
    monthFullName: MONTH_NAMES_FULL[month - 1],
    windowStartIso: `${year}-${pad2(month)}-01`,
    windowEndIso: `${year}-${pad2(month)}-${pad2(lastDay)}`,
    columns,
  };
}

/**
 * Return true if a project has been marked as completed/done.
 * @param {Object | null | undefined} project
 * @returns {boolean}
 */
export function isProjectCompleted(project) {
  return Boolean(
    project && (project.status === "completed" || project.status === "done")
  );
}

/**
 * Filter a list of projects by status filter mode ('all' | 'active' | 'done').
 * @param {Array<Object>} projects
 * @param {'all' | 'active' | 'done'} filterMode
 */
export function filterProjectsByStatus(projects, filterMode = "active") {
  const list = (projects || []).filter((p) => p.status !== "archived");
  if (filterMode === "active") {
    return list.filter((p) => !isProjectCompleted(p));
  }
  if (filterMode === "done") {
    return list.filter((p) => isProjectCompleted(p));
  }
  return list;
}

/**
 * Filter a list of subtasks by status filter mode ('all' | 'active' | 'done').
 * @param {Array<Object>} tasks
 * @param {'all' | 'active' | 'done'} filterMode
 */
export function filterSubtasksByStatus(tasks, filterMode = "all") {
  const list = tasks || [];
  if (filterMode === "active") {
    return list.filter((t) => t.status !== "done");
  }
  if (filterMode === "done") {
    return list.filter((t) => t.status === "done");
  }
  return list;
}

/**
 * Build a 1-Row-Per-Week Monthly Calendar structure where each Week is a 7-column row (Sun..Sat)
 * and every Project span or Task overlapping that week is placed on its own vertical track
 * so items NEVER overlap horizontally and each item lengthens the week row vertically.
 *
 * @param {number} year - e.g. 2026
 * @param {number} month - 1..12 (e.g. 11 for November)
 * @param {Array<Object>} pinnedProjects - Pinned projects with start_date and target_date
 * @param {Object<number, Array<Object>>} projectTasksMap - Map of project_id -> tasks array
 * @param {{ taskFilterMode?: 'all' | 'active' | 'done' }} options
 */
export function buildMonthlyWeekRows(
  year,
  month,
  pinnedProjects = [],
  projectTasksMap = {},
  options = {}
) {
  const taskFilterMode = options.taskFilterMode || "all";
  const dailyNotesMap = options.dailyNotesMap || {};
  const todayIso = options.todayIso || "";
  const firstDayUtc = Date.UTC(year, month - 1, 1);
  const lastDayDate = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const lastDayUtc = Date.UTC(year, month - 1, lastDayDate);

  // Align start of Week 1 to Sunday (0..6)
  const firstDow = new Date(firstDayUtc).getUTCDay();
  const gridStartUtc = firstDayUtc - firstDow * MS_PER_DAY;

  // Align end of final Week to Saturday
  const lastDow = new Date(lastDayUtc).getUTCDay();
  const gridEndUtc = lastDayUtc + (6 - lastDow) * MS_PER_DAY;

  const totalCalendarDays = Math.round((gridEndUtc - gridStartUtc) / MS_PER_DAY) + 1;
  const numWeeks = Math.round(totalCalendarDays / 7);

  const weeks = [];
  for (let w = 0; w < numWeeks; w += 1) {
    const weekStartUtc = gridStartUtc + w * 7 * MS_PER_DAY;
    const weekEndUtc = weekStartUtc + 6 * MS_PER_DAY;
    const weekStartIso = formatIsoDateUtc(weekStartUtc);
    const weekEndIso = formatIsoDateUtc(weekEndUtc);

    const days = [];
    for (let d = 0; d < 7; d += 1) {
      const dayUtc = weekStartUtc + d * MS_PER_DAY;
      const dt = new Date(dayUtc);
      const iso = formatIsoDateUtc(dayUtc);
      const inMonth = dt.getUTCFullYear() === year && dt.getUTCMonth() === month - 1;
      const journalEntry = dailyNotesMap[iso] || null;
      const rawMd =
        typeof journalEntry === "string"
          ? journalEntry
          : journalEntry?.content_md || "";
      const snippet = extractJournalSnippet(rawMd, 44);
      const hasJournal = Boolean(
        journalEntry && (rawMd.trim().length > 0 || journalEntry?.title)
      );

      days.push({
        col: d + 1,
        iso,
        dayNum: dt.getUTCDate(),
        monthShort: MONTH_NAMES_SHORT[dt.getUTCMonth()],
        dowShort: WEEKDAY_SHORT[d],
        inMonth,
        isToday: iso === todayIso,
        hasJournal,
        journalTitle: journalEntry?.title || null,
        journalSnippet: snippet,
      });
    }

    // Collect all project spans and task bars that overlap this 7-day week
    const rawItems = [];

    const candidateProjects = [];
    const seenProjIds = new Set();
    for (const proj of pinnedProjects || []) {
      if (proj && !seenProjIds.has(proj.id)) {
        seenProjIds.add(proj.id);
        candidateProjects.push(proj);
      }
    }
    const allProjList = options.allProjects || [];
    for (const proj of allProjList) {
      if (proj && !seenProjIds.has(proj.id) && proj.status !== "archived") {
        const areSubtasksVisible =
          options.visibleSubtaskProjectIds === undefined ||
          options.visibleSubtaskProjectIds === null ||
          (options.visibleSubtaskProjectIds instanceof Set
            ? options.visibleSubtaskProjectIds.has(proj.id)
            : Array.isArray(options.visibleSubtaskProjectIds)
            ? options.visibleSubtaskProjectIds.includes(proj.id)
            : Boolean(options.visibleSubtaskProjectIds[proj.id]));
        if (areSubtasksVisible) {
          seenProjIds.add(proj.id);
          candidateProjects.push(proj);
        }
      }
    }

    for (let pIdx = 0; pIdx < candidateProjects.length; pIdx += 1) {
      const proj = candidateProjects[pIdx];
      const projIsDone = isProjectCompleted(proj);

      // In 'active' filter mode, finished projects (and their subtasks) are hidden
      if (taskFilterMode === "active" && projIsDone) {
        continue;
      }

      const prefix = String.fromCharCode(65 + (pIdx % 26));
      const projColor = proj.color || "#ea580c";

      // 1. Project Span Bar in this week:
      // Show ONLY if the original project is pinned/visible on timeline
      const isOriginalProjectVisible = proj.is_pinned !== false && proj.status !== "archived";
      const shouldShowProjectBar =
        isOriginalProjectVisible &&
        (taskFilterMode === "all" ||
          (taskFilterMode === "active" && !projIsDone) ||
          (taskFilterMode === "done" && projIsDone));

      if (shouldShowProjectBar) {
        const pGeom = computeTimelineBarGeometry(
          proj.start_date,
          proj.target_date,
          weekStartIso,
          weekEndIso
        );
        if (pGeom.visible) {
          rawItems.push({
            uid: `proj-${proj.id}-w${w + 1}`,
            kind: "project",
            projectId: proj.id,
            projectName: proj.name,
            status: projIsDone ? "done" : "active",
            code: prefix,
            title: proj.name,
            color: projColor,
            dateRangeText: `${proj.start_date} → ${proj.target_date}`,
            startCol: pGeom.startCol,
            spanCols: pGeom.spanCols,
            endCol: pGeom.startCol + pGeom.spanCols - 1,
            isClippedLeft: pGeom.isClippedLeft,
            isClippedRight: pGeom.isClippedRight,
          });
        }
      }

      // 2. Tasks belonging to this project in this week (if subtasks are optionally visible)
      const areSubtasksVisible =
        options.visibleSubtaskProjectIds === undefined ||
        options.visibleSubtaskProjectIds === null ||
        (options.visibleSubtaskProjectIds instanceof Set
          ? options.visibleSubtaskProjectIds.has(proj.id)
          : Array.isArray(options.visibleSubtaskProjectIds)
          ? options.visibleSubtaskProjectIds.includes(proj.id)
          : Boolean(options.visibleSubtaskProjectIds[proj.id]));

      if (areSubtasksVisible) {
        const pTasksRaw = (projectTasksMap[proj.id] || []).map((t, idx) => ({
          ...t,
          code: t.code || `${prefix}${idx + 1}`,
        }));
        const pTasks = filterSubtasksByStatus(pTasksRaw, taskFilterMode);

        for (let tIdx = 0; tIdx < pTasks.length; tIdx += 1) {
          const task = pTasks[tIdx];
          const tGeom = computeTimelineBarGeometry(
            task.start_date,
            task.due_date,
            weekStartIso,
            weekEndIso
          );
          if (tGeom.visible) {
            rawItems.push({
              uid: `task-${task.id}-w${w + 1}`,
              kind: "task",
              taskId: task.id,
              projectId: proj.id,
              projectName: proj.name,
              code: task.code,
              title: task.title,
              status: task.status || "todo",
              color: task.color || "#0891b2",
              dateRangeText: `${task.start_date || ""} → ${task.due_date || ""}`,
              startCol: tGeom.startCol,
              spanCols: tGeom.spanCols,
              endCol: tGeom.startCol + tGeom.spanCols - 1,
              isClippedLeft: tGeom.isClippedLeft,
              isClippedRight: tGeom.isClippedRight,
            });
          }
        }
      }
    }

    // Assign each item a vertical track (trackRow = 1, 2, 3...) so overlapping items
    // NEVER collide and instead lengthen the week row vertically.
    const rowEndCols = [];
    for (const item of rawItems) {
      let placedRow = -1;
      // Project spans always start a fresh visual group; tasks can share a row only if non-overlapping
      if (item.kind !== "project") {
        for (let r = 0; r < rowEndCols.length; r += 1) {
          if (rowEndCols[r].kind === "task" && item.startCol > rowEndCols[r].endCol) {
            placedRow = r;
            rowEndCols[r].endCol = item.endCol;
            break;
          }
        }
      }
      if (placedRow === -1) {
        placedRow = rowEndCols.length;
        rowEndCols.push({ kind: item.kind, endCol: item.endCol });
      }
      item.trackRow = placedRow + 1;
    }

    weeks.push({
      weekNumber: w + 1,
      weekStartIso,
      weekEndIso,
      days,
      items: rawItems,
      totalTracks: rowEndCols.length,
    });
  }

  return {
    year,
    month,
    monthName: MONTH_NAMES_FULL[month - 1],
    weeks,
  };
}

/**
 * Build geometry and items for a single focused 7-day Week View.
 *
 * @param {string} anchorIso - Any date ISO string inside the desired week (e.g. "2026-11-03")
 * @param {Array<Object>} pinnedProjects
 * @param {Object<number, Array<Object>>} projectTasksMap
 * @param {Object} options
 */
export function buildFocusedWeekRow(
  anchorIso,
  pinnedProjects = [],
  projectTasksMap = {},
  options = {}
) {
  const taskFilterMode = options.taskFilterMode || "all";
  const dailyNotesMap = options.dailyNotesMap || {};
  const todayIso = options.todayIso || "";
  const visibleSubtaskProjectIds = options.visibleSubtaskProjectIds;

  const anchorUtc =
    parseIsoDateUtc(anchorIso) ??
    parseIsoDateUtc(todayIso) ??
    Date.now();

  const dtAnchor = new Date(anchorUtc);
  const dow = dtAnchor.getUTCDay(); // 0 (Sun) .. 6 (Sat)
  const weekStartUtc = anchorUtc - dow * MS_PER_DAY;
  const weekEndUtc = weekStartUtc + 6 * MS_PER_DAY;
  const weekStartIso = formatIsoDateUtc(weekStartUtc);
  const weekEndIso = formatIsoDateUtc(weekEndUtc);

  const days = [];
  for (let d = 0; d < 7; d += 1) {
    const dayUtc = weekStartUtc + d * MS_PER_DAY;
    const dt = new Date(dayUtc);
    const iso = formatIsoDateUtc(dayUtc);
    const journalEntry = dailyNotesMap[iso] || null;
    const rawMd =
      typeof journalEntry === "string"
        ? journalEntry
        : journalEntry?.content_md || "";
    const snippet = extractJournalSnippet(rawMd, 60);
    const hasJournal = Boolean(
      journalEntry && (rawMd.trim().length > 0 || journalEntry?.title)
    );

    days.push({
      col: d + 1,
      iso,
      dayNum: dt.getUTCDate(),
      monthShort: MONTH_NAMES_SHORT[dt.getUTCMonth()],
      dowShort: WEEKDAY_SHORT[d],
      inMonth: true,
      isToday: iso === todayIso,
      hasJournal,
      journalTitle: journalEntry?.title || null,
      journalSnippet: snippet,
    });
  }

  const rawItems = [];

  const candidateProjects = [];
  const seenProjIds = new Set();
  for (const proj of pinnedProjects || []) {
    if (proj && !seenProjIds.has(proj.id)) {
      seenProjIds.add(proj.id);
      candidateProjects.push(proj);
    }
  }
  const allProjList = options.allProjects || [];
  for (const proj of allProjList) {
    if (proj && !seenProjIds.has(proj.id) && proj.status !== "archived") {
      const areSubtasksVisible =
        visibleSubtaskProjectIds === undefined ||
        visibleSubtaskProjectIds === null ||
        (visibleSubtaskProjectIds instanceof Set
          ? visibleSubtaskProjectIds.has(proj.id)
          : Array.isArray(visibleSubtaskProjectIds)
          ? visibleSubtaskProjectIds.includes(proj.id)
          : Boolean(visibleSubtaskProjectIds[proj.id]));
      if (areSubtasksVisible) {
        seenProjIds.add(proj.id);
        candidateProjects.push(proj);
      }
    }
  }

  for (let pIdx = 0; pIdx < candidateProjects.length; pIdx += 1) {
    const proj = candidateProjects[pIdx];
    const projIsDone = isProjectCompleted(proj);

    if (taskFilterMode === "active" && projIsDone) {
      continue;
    }

    const prefix = String.fromCharCode(65 + (pIdx % 26));
    const projColor = proj.color || "#ea580c";

    const isOriginalProjectVisible = proj.is_pinned !== false && proj.status !== "archived";
    const shouldShowProjectBar =
      isOriginalProjectVisible &&
      (taskFilterMode === "all" ||
        (taskFilterMode === "active" && !projIsDone) ||
        (taskFilterMode === "done" && projIsDone));

    if (shouldShowProjectBar) {
      const pGeom = computeTimelineBarGeometry(
        proj.start_date,
        proj.target_date,
        weekStartIso,
        weekEndIso
      );
      if (pGeom.visible) {
        rawItems.push({
          uid: `week-proj-${proj.id}`,
          kind: "project",
          projectId: proj.id,
          projectName: proj.name,
          status: projIsDone ? "done" : "active",
          code: prefix,
          title: proj.name,
          color: projColor,
          dateRangeText: `${proj.start_date} → ${proj.target_date}`,
          startCol: pGeom.startCol,
          spanCols: pGeom.spanCols,
          endCol: pGeom.startCol + pGeom.spanCols - 1,
          isClippedLeft: pGeom.isClippedLeft,
          isClippedRight: pGeom.isClippedRight,
        });
      }
    }

    const areSubtasksVisible =
      visibleSubtaskProjectIds === undefined ||
      visibleSubtaskProjectIds === null ||
      (visibleSubtaskProjectIds instanceof Set
        ? visibleSubtaskProjectIds.has(proj.id)
        : Array.isArray(visibleSubtaskProjectIds)
        ? visibleSubtaskProjectIds.includes(proj.id)
        : Boolean(visibleSubtaskProjectIds[proj.id]));

    if (areSubtasksVisible) {
      const pTasksRaw = (projectTasksMap[proj.id] || []).map((t, idx) => ({
        ...t,
        code: t.code || `${prefix}${idx + 1}`,
      }));
      const pTasks = filterSubtasksByStatus(pTasksRaw, taskFilterMode);

      for (let tIdx = 0; tIdx < pTasks.length; tIdx += 1) {
        const task = pTasks[tIdx];
        const tGeom = computeTimelineBarGeometry(
          task.start_date,
          task.due_date,
          weekStartIso,
          weekEndIso
        );
        if (tGeom.visible) {
          rawItems.push({
            uid: `week-task-${task.id}`,
            kind: "task",
            taskId: task.id,
            projectId: proj.id,
            projectName: proj.name,
            code: task.code,
            title: task.title,
            status: task.status || "todo",
            color: task.color || "#0891b2",
            dateRangeText: `${task.start_date || ""} → ${task.due_date || ""}`,
            startCol: tGeom.startCol,
            spanCols: tGeom.spanCols,
            endCol: tGeom.startCol + tGeom.spanCols - 1,
            isClippedLeft: tGeom.isClippedLeft,
            isClippedRight: tGeom.isClippedRight,
          });
        }
      }
    }
  }

  const rowEndCols = [];
  for (const item of rawItems) {
    let placedRow = -1;
    if (item.kind !== "project") {
      for (let r = 0; r < rowEndCols.length; r += 1) {
        if (rowEndCols[r].kind === "task" && item.startCol > rowEndCols[r].endCol) {
          placedRow = r;
          rowEndCols[r].endCol = item.endCol;
          break;
        }
      }
    }
    if (placedRow === -1) {
      placedRow = rowEndCols.length;
      rowEndCols.push({ kind: item.kind, endCol: item.endCol });
    }
    item.trackRow = placedRow + 1;
  }

  const startYear = new Date(weekStartUtc).getUTCFullYear();
  const rangeText = `${days[0].monthShort} ${days[0].dayNum} – ${days[6].monthShort} ${days[6].dayNum}, ${startYear}`;

  return {
    weekStartIso,
    weekEndIso,
    rangeText,
    days,
    items: rawItems,
    totalTracks: rowEndCols.length,
  };
}

/**
 * Compute horizontal timeline bar geometry (leftPct, widthPct, startCol, spanCols, clipping flags)
 * for a project or task inside [windowStartIso, windowEndIso] (inclusive).
 */
export function computeTimelineBarGeometry(
  itemStartIso,
  itemEndIso,
  windowStartIso,
  windowEndIso
) {
  const winStart = parseIsoDateUtc(windowStartIso);
  const winEnd = parseIsoDateUtc(windowEndIso);
  if (winStart === null || winEnd === null || winEnd < winStart) {
    throw new Error("Invalid timeline window dates");
  }

  const rawStart = parseIsoDateUtc(itemStartIso || itemEndIso);
  const rawEnd = parseIsoDateUtc(itemEndIso || itemStartIso);
  if (rawStart === null || rawEnd === null) {
    return {
      visible: false,
      leftPct: 0,
      widthPct: 0,
      startCol: 1,
      spanCols: 1,
      isClippedLeft: false,
      isClippedRight: false,
    };
  }

  const effStart = Math.min(rawStart, rawEnd);
  const effEnd = Math.max(rawStart, rawEnd);

  if (effEnd < winStart || effStart > winEnd) {
    return {
      visible: false,
      leftPct: 0,
      widthPct: 0,
      startCol: 1,
      spanCols: 1,
      isClippedLeft: effStart < winStart,
      isClippedRight: effEnd > winEnd,
    };
  }

  const totalDays = Math.floor((winEnd - winStart) / MS_PER_DAY) + 1;
  const clampedStart = Math.max(effStart, winStart);
  const clampedEnd = Math.min(effEnd, winEnd);

  const offsetDays = Math.floor((clampedStart - winStart) / MS_PER_DAY);
  const spanDays = Math.floor((clampedEnd - clampedStart) / MS_PER_DAY) + 1;

  const leftPct = Number(((offsetDays / totalDays) * 100).toFixed(2));
  const widthPct = Number(((spanDays / totalDays) * 100).toFixed(2));

  return {
    visible: true,
    leftPct,
    widthPct,
    startCol: offsetDays + 1,
    spanCols: spanDays,
    isClippedLeft: effStart < winStart,
    isClippedRight: effEnd > winEnd,
  };
}

/**
 * Compute Month-Column span (1..12) for a project or task in Year View (Jan..Dec)
 * so Year View also uses clean CSS Grid columns and vertical row stacking without overlap.
 */
export function computeYearMonthGridSpan(itemStartIso, itemEndIso, year) {
  const winStartIso = `${year}-01-01`;
  const winEndIso = `${year}-12-31`;
  const geom = computeTimelineBarGeometry(
    itemStartIso,
    itemEndIso,
    winStartIso,
    winEndIso
  );
  if (!geom.visible) {
    return { visible: false, startMonthCol: 1, spanMonthCols: 1 };
  }

  const effStartMs = Math.max(
    parseIsoDateUtc(itemStartIso || itemEndIso),
    parseIsoDateUtc(winStartIso)
  );
  const effEndMs = Math.min(
    parseIsoDateUtc(itemEndIso || itemStartIso),
    parseIsoDateUtc(winEndIso)
  );

  const startMonth = new Date(effStartMs).getUTCMonth() + 1; // 1..12
  const endMonth = new Date(effEndMs).getUTCMonth() + 1; // 1..12

  return {
    visible: true,
    startMonthCol: startMonth,
    spanMonthCols: Math.max(endMonth - startMonth + 1, 1),
    leftPct: geom.leftPct,
    widthPct: geom.widthPct,
  };
}

/**
 * Pack tasks within a project swimlane into non-overlapping horizontal sub-rows.
 */
export function packSwimlaneTaskCards(
  tasks,
  windowStartIso,
  windowEndIso,
  codePrefix = "A"
) {
  const winStart = parseIsoDateUtc(windowStartIso);
  const winEnd = parseIsoDateUtc(windowEndIso);
  if (winStart === null || winEnd === null) return [];

  const decorated = [];
  let seq = 1;

  for (const t of tasks || []) {
    const geom = computeTimelineBarGeometry(
      t.start_date,
      t.due_date,
      windowStartIso,
      windowEndIso
    );
    if (!geom.visible) continue;

    const code = t.is_milestone ? `M${seq}` : `${codePrefix}${seq}`;
    seq += 1;

    decorated.push({
      ...t,
      code,
      startCol: geom.startCol,
      spanCols: geom.spanCols,
      endCol: geom.startCol + geom.spanCols - 1,
      leftPct: geom.leftPct,
      widthPct: geom.widthPct,
    });
  }

  decorated.sort((a, b) => a.startCol - b.startCol || b.spanCols - a.spanCols);

  const rowEndCols = [];
  for (const card of decorated) {
    let placedRow = -1;
    for (let r = 0; r < rowEndCols.length; r += 1) {
      if (card.startCol > rowEndCols[r]) {
        placedRow = r;
        rowEndCols[r] = card.endCol;
        break;
      }
    }
    if (placedRow === -1) {
      placedRow = rowEndCols.length;
      rowEndCols.push(card.endCol);
    }
    card.subRow = placedRow + 1;
  }

  return decorated;
}

/**
 * Build an SVG cubic Bezier path string.
 */
export function computeDependencyBezierPath(fromPt, toPt) {
  const dx = Math.max(Math.abs(toPt.x - fromPt.x) * 0.5, 24);
  const cx1 = Number((fromPt.x + dx).toFixed(1));
  const cx2 = Number((toPt.x - dx).toFixed(1));
  return `M ${fromPt.x} ${fromPt.y} C ${cx1} ${fromPt.y}, ${cx2} ${toPt.y}, ${toPt.x} ${toPt.y}`;
}

/**
 * Client-side optimistic cascade preview.
 */
export function cascadeDependentTasksClient(tasks, rootTaskId, newDueDateIso) {
  const cloned = tasks.map((t) => ({ ...t }));
  const byId = new Map(cloned.map((t) => [t.id, t]));
  const root = byId.get(rootTaskId);
  if (!root) return { tasks: cloned, cascadedIds: [] };

  root.due_date = newDueDateIso;
  const cascadedIds = [];
  const visited = new Set([rootTaskId]);

  function walk(pred) {
    const predEndMs = parseIsoDateUtc(pred.due_date || pred.start_date);
    if (predEndMs === null) return;

    for (const candidate of cloned) {
      if (candidate.depends_on_id === pred.id && !visited.has(candidate.id)) {
        visited.add(candidate.id);
        const minStartMs = predEndMs + MS_PER_DAY;
        const cStartMs = parseIsoDateUtc(candidate.start_date || candidate.due_date);
        const cEndMs = parseIsoDateUtc(candidate.due_date || candidate.start_date);

        if (cStartMs !== null && cStartMs < minStartMs) {
          const durationMs = cEndMs !== null ? Math.max(cEndMs - cStartMs, 0) : 0;
          candidate.start_date = formatIsoDateUtc(minStartMs);
          candidate.due_date = formatIsoDateUtc(minStartMs + durationMs);
          cascadedIds.push(candidate.id);
          walk(candidate);
        }
      }
    }
  }

  walk(root);
  return { tasks: cloned, cascadedIds };
}

/**
 * Group tasks into Kanban columns (todo, in_progress, review, done).
 */
export function groupTasksForKanban(tasks) {
  const columns = [
    { status: "todo", label: "To Do", tasks: [] },
    { status: "in_progress", label: "In Progress", tasks: [] },
    { status: "review", label: "In Review", tasks: [] },
    { status: "done", label: "Done", tasks: [] },
  ];
  const map = Object.fromEntries(columns.map((c) => [c.status, c]));
  for (const t of tasks || []) {
    const bucket = map[t.status] || map.todo;
    bucket.tasks.push(t);
  }
  return columns.map((c) => ({ ...c, count: c.tasks.length }));
}

/**
 * Compute deterministic radial coordinates for Knowledge Graph nodes and edges.
 */
export function computeKnowledgeGraphLayout(graph, viewport = {}) {
  const width = viewport.width || 800;
  const height = viewport.height || 420;
  const cx = width / 2;
  const cy = height / 2;

  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];
  const count = nodes.length;

  const positionedNodes = nodes.map((node, index) => {
    if (count === 1) {
      return { ...node, x: cx, y: cy };
    }
    const radiusRatio =
      node.kind === "project" ? 0.25 : node.kind === "note" ? 0.38 : 0.45;
    const rx = width * radiusRatio;
    const ry = height * radiusRatio;
    const angle = (2 * Math.PI * index) / count - Math.PI / 2;
    return {
      ...node,
      x: Number((cx + rx * Math.cos(angle)).toFixed(1)),
      y: Number((cy + ry * Math.sin(angle)).toFixed(1)),
    };
  });

  const nodeById = new Map(positionedNodes.map((n) => [n.id, n]));
  const positionedEdges = edges
    .map((edge) => {
      const src = nodeById.get(edge.source);
      const dst = nodeById.get(edge.target);
      if (!src || !dst) return null;
      return {
        ...edge,
        x1: src.x,
        y1: src.y,
        x2: dst.x,
        y2: dst.y,
      };
    })
    .filter(Boolean);

  return {
    nodes: positionedNodes,
    edges: positionedEdges,
  };
}

/**
 * Render Markdown text with ChronoNote syntax extensions.
 */
export function renderMarkdownPreviewHtml(markdownText) {
  if (!markdownText) return "";

  const withoutFrontmatter = markdownText.replace(
    /^---\s*\r?\n[\s\S]*?\r?\n---\s*(?:\r?\n|$)/,
    ""
  );

  const lines = withoutFrontmatter.split(/\r?\n/);
  const htmlLines = lines.map((rawLine) => {
    let line = rawLine
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    line = line.replace(
      /\[\[([^\]|#]+?)(?:\|([^\]]+?))?\]\]/g,
      (_, target, alias) => {
        const slug = target
          .trim()
          .toLowerCase()
          .replace(/[^\w\s-]/g, "")
          .replace(/[\s_]+/g, "-");
        const label = (alias || target).trim();
        return `<a class="wikilink" data-slug="${slug}" href="#/notes/${slug}">[[${label}]]</a>`;
      }
    );

    line = line.replace(
      /@(start|due|priority)\(([^)]+)\)/gi,
      '<span class="directive-pill directive-$1">@$1($2)</span>'
    );
    line = line.replace(
      /@milestone\b/gi,
      '<span class="directive-pill directive-milestone">@milestone</span>'
    );

    line = line.replace(
      /(^|\s)#([a-zA-Z][a-zA-Z0-9_-]{1,49})\b/g,
      '$1<span class="tag-pill">#$2</span>'
    );

    // Docs-style image layouts: Wrap Left, Wrap Right, or Draggable
    line = line.replace(
      /!\[([^\]]*)\]\(([^)]+)\)\{(?:mode="([^"]*)")?(?:,\s*(?:x="[^"]*",\s*y="[^"]*",\s*)?w="([^"]*)")?[^}]*\}/g,
      (_, alt, src, mode, width) => {
        const wStyle = width ? `max-width: ${width}px; width: 100%;` : "";
        if (mode === "wrap_left") {
          return `<div class="md-img-wrap-left" style="${wStyle}"><img src="${src}" alt="${alt}" class="docs-rendered-img" /><span class="docs-img-caption">${alt}</span></div>`;
        }
        if (mode === "wrap_right") {
          return `<div class="md-img-wrap-right" style="${wStyle}"><img src="${src}" alt="${alt}" class="docs-rendered-img" /><span class="docs-img-caption">${alt}</span></div>`;
        }
        if (mode === "draggable") {
          return `<div class="md-img-draggable-placeholder" data-src="${src}" data-alt="${alt}"></div>`;
        }
        return `<div class="md-img-inline" style="${wStyle}"><img src="${src}" alt="${alt}" class="docs-rendered-img" /><span class="docs-img-caption">${alt}</span></div>`;
      }
    );

    // Standard inline markdown image
    line = line.replace(
      /!\[([^\]]*)\]\(([^)]+)\)/g,
      '<div class="md-img-inline"><img src="$2" alt="$1" class="docs-rendered-img" /><span class="docs-img-caption">$1</span></div>'
    );

    if (/^###\s+(.+)/.test(line)) {
      return `<h3>${line.replace(/^###\s+/, "")}</h3>`;
    }
    if (/^##\s+(.+)/.test(line)) {
      return `<h2>${line.replace(/^##\s+/, "")}</h2>`;
    }
    if (/^#\s+(.+)/.test(line)) {
      return `<h1>${line.replace(/^#\s+/, "")}</h1>`;
    }

    const taskMatch = line.match(/^\s*[-*]\s+\[([ xX])\]\s+(.+)$/);
    if (taskMatch) {
      const checked = taskMatch[1].toLowerCase() === "x";
      return `<div class="md-task-row ${checked ? "is-done" : ""}"><input type="checkbox" ${
        checked ? "checked" : ""
      } readonly /><span>${taskMatch[2]}</span></div>`;
    }

    return line ? `<p>${line}</p>` : "";
  });

  return htmlLines.filter(Boolean).join("\n");
}
