import test from "node:test";
import assert from "node:assert/strict";

import {
  buildCalendarTimelineColumns,
  buildMonthlyWeekRows,
  buildFocusedWeekRow,
  calculateDateSpanDays,
  cascadeDependentTasksClient,
  computeDependencyBezierPath,
  computeKnowledgeGraphLayout,
  computeTimelineBarGeometry,
  computeYearMonthGridSpan,
  extractJournalSnippet,
  filterProjectsByStatus,
  filterSubtasksByStatus,
  formatEditorialDate,
  groupProjectsForKanban,
  groupTasksForKanban,
  isProjectCompleted,
  moveProjectInKanban,
  packSwimlaneTaskCards,
  partitionSidebarProjects,
  renderMarkdownPreviewHtml,
  shiftDateIso,
  shiftDateMonths,
  clipSubtaskToProjectRange,
  computeProjectDragResult,
  computeSubtaskDragResult,
} from "../src/composables/useTimelineGeometry.js";
import {
  appendOcrToMarkdown,
  cleanOcrText,
} from "../src/composables/useHandwritingOcr.js";
import {
  buildHabitHeatmapGrid,
  getHeatmapLevel,
  extractHabitPills,
  toggleHabitInMarkdown,
  applyTemplateVariables,
} from "../src/composables/useHabitsAndHeatmap.js";
import {
  formatPomodoroTime,
  calculatePomodoroProgress,
  getNextPomodoroMode,
  formatStudyLogMarkdown,
  computeRemainingSeconds,
} from "../src/composables/useStudyPomodoro.js";
import {
  computeStickerTransformStyle,
  filterStickersByTarget,
  sanitizeStickerCategory,
} from "../src/composables/useStickers.js";
import {
  parseDocsImageDirectives,
  formatDocsImageMarkdown,
  computeDraggableImageStyle,
} from "../src/composables/useDocsImages.js";
import {
  PAPER_THEMES,
  TYPOGRAPHY_THEMES,
  getPaperStyleClass,
  getTypographyClass,
} from "../src/composables/useCustomThemes.js";

test("Left Sidebar partitions pinned vs regular projects, orders by sidebar_order, and filters archived", () => {
  const sampleProjects = [
    { id: 1, name: "Core Backend", status: "active", is_pinned: false, sidebar_order: 2 },
    { id: 2, name: "Design System", status: "active", is_pinned: true, sidebar_order: 5 },
    { id: 3, name: "Timeline Canvas", status: "active", is_pinned: false, sidebar_order: 1 },
    { id: 4, name: "Old Prototype", status: "archived", is_pinned: false, sidebar_order: 0 },
  ];

  const result = partitionSidebarProjects(sampleProjects);
  assert.equal(result.all.length, 3);
  assert.deepEqual(
    result.pinned.map((p) => p.id),
    [2]
  );
  assert.deepEqual(
    result.regular.map((p) => p.id),
    [3, 1]
  );

  const filtered = partitionSidebarProjects(sampleProjects, { query: "timeline" });
  assert.equal(filtered.all.length, 1);
  assert.equal(filtered.all[0].name, "Timeline Canvas");
});

test("Timeline bar geometry calculates leftPct, widthPct, and window clipping accurately", () => {
  const geom = computeTimelineBarGeometry(
    "2026-11-03",
    "2026-11-05",
    "2026-11-01",
    "2026-11-10"
  );
  assert.equal(geom.visible, true);
  assert.equal(geom.leftPct, 20);
  assert.equal(geom.widthPct, 30);
  assert.equal(geom.isClippedLeft, false);
  assert.equal(geom.isClippedRight, false);

  const clipped = computeTimelineBarGeometry(
    "2026-10-25",
    "2026-11-02",
    "2026-11-01",
    "2026-11-10"
  );
  assert.equal(clipped.visible, true);
  assert.equal(clipped.leftPct, 0);
  assert.equal(clipped.widthPct, 20);
  assert.equal(clipped.isClippedLeft, true);
  assert.equal(clipped.isClippedRight, false);

  const outside = computeTimelineBarGeometry(
    "2026-12-01",
    "2026-12-05",
    "2026-11-01",
    "2026-11-10"
  );
  assert.equal(outside.visible, false);
});

test("SVG Dependency Bezier path connects task coordinates smoothly", () => {
  const path = computeDependencyBezierPath({ x: 100, y: 40 }, { x: 220, y: 90 });
  assert.equal(path, "M 100 40 C 160 40, 160 90, 220 90");
});

test("Client-side auto-cascading dependency simulation shifts downstream task chain", () => {
  const initialTasks = [
    { id: 10, title: "DB Schema", start_date: "2026-11-01", due_date: "2026-11-03", depends_on_id: null },
    { id: 11, title: "API Endpoints", start_date: "2026-11-04", due_date: "2026-11-06", depends_on_id: 10 },
    { id: 12, title: "E2E Tests", start_date: "2026-11-07", due_date: "2026-11-08", depends_on_id: 11 },
  ];

  const { tasks, cascadedIds } = cascadeDependentTasksClient(initialTasks, 10, "2026-11-08");
  assert.deepEqual(cascadedIds, [11, 12]);

  const t11 = tasks.find((t) => t.id === 11);
  const t12 = tasks.find((t) => t.id === 12);
  assert.equal(t11.start_date, "2026-11-09");
  assert.equal(t11.due_date, "2026-11-11");
  assert.equal(t12.start_date, "2026-11-12");
  assert.equal(t12.due_date, "2026-11-13");
});

test("Kanban board grouping organizes tasks into 4 status columns with counts", () => {
  const tasks = [
    { id: 1, title: "T1", status: "todo" },
    { id: 2, title: "T2", status: "in_progress" },
    { id: 3, title: "T3", status: "done" },
    { id: 4, title: "T4", status: "todo" },
  ];
  const columns = groupTasksForKanban(tasks);
  assert.equal(columns.length, 4);
  assert.equal(columns.find((c) => c.status === "todo").count, 2);
  assert.equal(columns.find((c) => c.status === "in_progress").count, 1);
  assert.equal(columns.find((c) => c.status === "review").count, 0);
  assert.equal(columns.find((c) => c.status === "done").count, 1);
});

test("Knowledge Graph layout assigns deterministic SVG coordinates to nodes and edges", () => {
  const rawGraph = {
    nodes: [
      { id: "project:1", kind: "project", label: "Core", color: "#6366f1" },
      { id: "note:1", kind: "note", label: "Spec", color: "#38bdf8" },
      { id: "tag:vue3", kind: "tag", label: "#vue3", color: "#a855f7" },
    ],
    edges: [
      { source: "note:1", target: "project:1", relation: "belongs_to" },
      { source: "note:1", target: "tag:vue3", relation: "tagged" },
    ],
  };

  const layout = computeKnowledgeGraphLayout(rawGraph, { width: 800, height: 400 });
  assert.equal(layout.nodes.length, 3);
  assert.equal(layout.edges.length, 2);
  for (const node of layout.nodes) {
    assert.equal(typeof node.x, "number");
    assert.equal(typeof node.y, "number");
  }
  assert.equal(layout.edges[0].x1, layout.nodes[1].x);
  assert.equal(layout.edges[0].y1, layout.nodes[1].y);
});

test("Markdown preview renderer highlights [[WikiLinks]], #tags, inline @directives, and checkboxes", () => {
  const md = `---
owner: bryce
---
# Architecture Overview
See [[Database Spec|DB Schema]] for #fastapi details.
- [ ] Ship Timeline UI @start(2026-11-02) @due(2026-11-08) @priority(high)
- [x] Initial Repo Setup @milestone
`;
  const html = renderMarkdownPreviewHtml(md);

  assert.ok(!html.includes("owner: bryce"), "Frontmatter should be stripped from preview HTML");
  assert.ok(html.includes("<h1>Architecture Overview</h1>"));
  assert.ok(
    html.includes('<a class="wikilink" data-slug="database-spec" href="#/notes/database-spec">[[DB Schema]]</a>')
  );
  assert.ok(html.includes('<span class="tag-pill">#fastapi</span>'));
  assert.ok(html.includes('<span class="directive-pill directive-due">@due(2026-11-08)</span>'));
  assert.ok(html.includes('<span class="directive-pill directive-milestone">@milestone</span>'));
  assert.ok(html.includes('class="md-task-row is-done"'));
});

test("Roadmap swimlane card packer assigns codes (A1, A2) and stacks overlapping day cards into sub-rows", () => {
  const tasks = [
    { id: 1, title: "Hero seed world", start_date: "2026-11-01", due_date: "2026-11-02", is_milestone: false },
    { id: 2, title: "Fast seed-db path", start_date: "2026-11-02", due_date: "2026-11-02", is_milestone: false },
    { id: 3, title: "Entities check", start_date: "2026-11-03", due_date: "2026-11-03", is_milestone: false },
  ];

  const packed = packSwimlaneTaskCards(tasks, "2026-11-01", "2026-11-08", "A");
  assert.equal(packed.length, 3);
  assert.equal(packed[0].code, "A1");
  assert.equal(packed[0].startCol, 1);
  assert.equal(packed[0].spanCols, 2);
  assert.equal(packed[0].subRow, 1);

  // Task 2 overlaps Day 2 (col 2), so it packs into subRow 2 underneath A1
  assert.equal(packed[1].code, "A2");
  assert.equal(packed[1].startCol, 2);
  assert.equal(packed[1].subRow, 2);

  // Task 3 starts on Day 3 (col 3), so it reuses subRow 1
  assert.equal(packed[2].code, "A3");
  assert.equal(packed[2].startCol, 3);
  assert.equal(packed[2].subRow, 1);
});

test("Page 1 Projects Kanban groups projects into Planned, Active, On Hold, and Completed columns", () => {
  const sampleProjects = [
    { id: 1, name: "P1", status: "planned", start_date: "2026-11-01", target_date: "2026-12-01" },
    { id: 2, name: "P2", status: "active", start_date: "2026-10-01", target_date: "2026-11-15" },
    { id: 3, name: "P3", status: "on_hold", start_date: "2026-08-01", target_date: "2026-09-01" },
    { id: 4, name: "P4", status: "completed", start_date: "2026-06-01", target_date: "2026-07-01" },
  ];
  const cols = groupProjectsForKanban(sampleProjects);
  assert.equal(cols.length, 4);
  assert.deepEqual(
    cols.map((c) => [c.status, c.count]),
    [
      ["planned", 1],
      ["active", 1],
      ["on_hold", 1],
      ["completed", 1],
    ]
  );
});

test("Page 2 Calendar Timeline builds 12-month Year columns and 30-day November Month columns", () => {
  const yearSpec = buildCalendarTimelineColumns(2026, null);
  assert.equal(yearSpec.mode, "year");
  assert.equal(yearSpec.windowStartIso, "2026-01-01");
  assert.equal(yearSpec.windowEndIso, "2026-12-31");
  assert.equal(yearSpec.columns.length, 12);
  assert.equal(yearSpec.columns[0].label, "Jan");
  assert.equal(yearSpec.columns[10].label, "Nov");

  const monthSpec = buildCalendarTimelineColumns(2026, 11);
  assert.equal(monthSpec.mode, "month");
  assert.equal(monthSpec.monthName, "Nov");
  assert.equal(monthSpec.windowStartIso, "2026-11-01");
  assert.equal(monthSpec.windowEndIso, "2026-11-30");
  assert.equal(monthSpec.columns.length, 30);
});

test("Monthly 1-row-per-week builder stacks overlapping tasks into separate vertical trackRows so they never overlap", () => {
  const pinnedProjects = [
    { id: 1, name: "Core Engine", is_pinned: true, start_date: "2026-11-01", target_date: "2026-11-25" },
  ];
  const tasksMap = {
    1: [
      { id: 101, title: "Schema setup", status: "done", start_date: "2026-11-02", due_date: "2026-11-05" },
      { id: 102, title: "Benchmark pooling", status: "todo", start_date: "2026-11-03", due_date: "2026-11-06" },
    ],
  };

  const monthWeeks = buildMonthlyWeekRows(2026, 11, pinnedProjects, tasksMap);
  assert.equal(monthWeeks.monthName, "November");
  assert.ok(monthWeeks.weeks.length >= 5);

  const week1 = monthWeeks.weeks[0];
  assert.equal(week1.days.length, 7);
  // Week 1 has 1 project bar + 2 overlapping tasks -> 3 distinct vertical tracks (trackRow 1, 2, 3)
  assert.equal(week1.items.length, 3);
  assert.deepEqual(
    week1.items.map((i) => i.trackRow),
    [1, 2, 3]
  );

  const yearSpan = computeYearMonthGridSpan("2026-10-05", "2026-11-25", 2026);
  assert.equal(yearSpan.visible, true);
  assert.equal(yearSpan.startMonthCol, 10);
  assert.equal(yearSpan.spanMonthCols, 2);
});

test("Milestone Layer suppresses long project spans and renders target milestones and milestone diamonds", () => {
  const pinnedProjects = [
    { id: 1, name: "Long Architecture Refactor", is_pinned: true, start_date: "2026-11-01", target_date: "2026-11-20" },
  ];
  const tasksMap = {
    1: [
      { id: 101, title: "Database Schema Signoff", is_milestone: true, status: "todo", start_date: "2026-11-04", due_date: "2026-11-04" },
      { id: 102, title: "Regular subtask", is_milestone: false, status: "todo", start_date: "2026-11-02", due_date: "2026-11-05" },
    ],
  };

  // 1. In 'milestones' mode, the long 20-day project bar is replaced by a milestone target on 2026-11-20
  const milestoneWeeks = buildMonthlyWeekRows(2026, 11, pinnedProjects, tasksMap, {
    projectDisplayMode: "milestones",
  });

  const week1Items = milestoneWeeks.weeks[0].items;
  // Week 1 should NOT have the 20-day project span bar
  assert.ok(!week1Items.some((i) => i.kind === "project"));
  // Week 1 should contain the milestone diamond task
  const milestoneItem = week1Items.find((i) => i.taskId === 101);
  assert.ok(milestoneItem);
  assert.equal(milestoneItem.isMilestone, true);
  assert.equal(milestoneItem.code, "◆");
});

test("Overdue status filtering identifies past due tasks and projects", () => {
  const tasks = [
    { id: 1, title: "Past Task", status: "todo", due_date: "2026-11-01" },
    { id: 2, title: "Completed Task", status: "done", due_date: "2026-11-01" },
    { id: 3, title: "Future Task", status: "todo", due_date: "2026-11-15" },
  ];

  const overdue = filterSubtasksByStatus(tasks, "overdue", "2026-11-05");
  assert.equal(overdue.length, 1);
  assert.equal(overdue[0].id, 1);

  const projects = [
    { id: 1, name: "Overdue Project", status: "active", target_date: "2026-11-02" },
    { id: 2, name: "Healthy Project", status: "active", target_date: "2026-11-20" },
  ];
  const overdueProjs = filterProjectsByStatus(projects, "overdue", {}, "2026-11-05");
  assert.equal(overdueProjs.length, 1);
  assert.equal(overdueProjs[0].id, 1);
});

test("Decoupled standalone one-off tasks appear on monthly calendar with inbox badge", () => {
  const standaloneTasks = [
    { id: 999, title: "Pay Quarterly Taxes", status: "todo", due_date: "2026-11-03", color: "#e11d48" },
  ];

  const monthWeeks = buildMonthlyWeekRows(2026, 11, [], {}, {
    standaloneTasks,
    todayIso: "2026-11-01",
  });

  const week1Items = monthWeeks.weeks[0].items;
  const standaloneItem = week1Items.find((i) => i.taskId === 999);
  assert.ok(standaloneItem);
  assert.equal(standaloneItem.isStandalone, true);
  assert.equal(standaloneItem.code, "");
  assert.equal(standaloneItem.projectName, "Inbox");
});

test("Subtask status filter ('all' | 'active' | 'done') and custom project/subtask colors work in Monthly Week rows", () => {
  const pinnedProjects = [
    { id: 1, name: "Core Engine", color: "#ea580c", is_pinned: true, start_date: "2026-11-01", target_date: "2026-11-25" },
  ];
  const tasksMap = {
    1: [
      { id: 101, title: "Done Subtask A1", status: "done", color: "#10b981", start_date: "2026-11-02", due_date: "2026-11-04" },
      { id: 102, title: "Active Subtask A2", status: "todo", color: "#8b5cf6", start_date: "2026-11-03", due_date: "2026-11-05" },
    ],
  };

  assert.equal(filterSubtasksByStatus(tasksMap[1], "all").length, 2);
  assert.equal(filterSubtasksByStatus(tasksMap[1], "active").length, 1);
  assert.equal(filterSubtasksByStatus(tasksMap[1], "done").length, 1);

  const activeOnlyWeeks = buildMonthlyWeekRows(2026, 11, pinnedProjects, tasksMap, {
    taskFilterMode: "active",
  });
  const week1Items = activeOnlyWeeks.weeks[0].items;
  // Should include 1 project bar + 1 active subtask (A2 retains its code A2 and custom color #8b5cf6)
  assert.equal(week1Items.length, 2);
  assert.equal(week1Items[0].color, "#ea580c");
  assert.equal(week1Items[1].code, "A2");
  assert.equal(week1Items[1].color, "#8b5cf6");
});

test("Month View attaches Daily Journal indicators and snippets to specific dates", () => {
  const dailyNotesMap = {
    "2026-11-01": {
      title: "Journal — 2026-11-01",
      content_md: "---\ndate: 2026-11-01\n---\n# Journal — 2026-11-01\nMorning coffee and quiet reflection.",
    },
  };
  const monthWeeks = buildMonthlyWeekRows(2026, 11, [], {}, {
    dailyNotesMap,
    todayIso: "2026-11-01",
  });

  const nov1Cell = monthWeeks.weeks[0].days.find((d) => d.iso === "2026-11-01");
  assert.equal(nov1Cell.hasJournal, true);
  assert.equal(nov1Cell.isToday, true);
  assert.ok(nov1Cell.journalSnippet.includes("Morning coffee"));

  const nov2Cell = monthWeeks.weeks[0].days.find((d) => d.iso === "2026-11-02");
  assert.equal(nov2Cell.hasJournal, false);

  const editorial = formatEditorialDate("2026-11-01");
  assert.equal(editorial.full, "Sunday, November 1, 2026");
  assert.equal(extractJournalSnippet("# Title\n- [x] Walk outside @due(2026-11-01)"), "Title · Walk outside");
});

test("Handwritten OCR helpers clean noise and append recognized text into Markdown notes", () => {
  const noisyOcr = "  Morning   pages from notebook \n~\n\n\n- Sketch layout ideas  \n| \n";
  const cleaned = cleanOcrText(noisyOcr);
  assert.equal(cleaned, "Morning pages from notebook\n\n- Sketch layout ideas");

  const merged = appendOcrToMarkdown("# Daily Note", noisyOcr, {
    includeHeader: true,
    sourceLabel: "Handwritten Journal Scan",
  });
  assert.ok(merged.includes("### Handwritten Journal Scan"));
  assert.ok(merged.includes("Morning pages from notebook"));
});

test("All / Active / Completed filter tabs apply identically to both Projects and Subtasks on Month View", () => {
  const projects = [
    {
      id: 1,
      name: "Active Project",
      status: "active",
      is_pinned: true,
      start_date: "2026-11-01",
      target_date: "2026-11-10",
    },
    {
      id: 2,
      name: "Finished Project",
      status: "completed",
      is_pinned: true,
      start_date: "2026-11-01",
      target_date: "2026-11-10",
    },
  ];
  const tasksMap = {
    1: [{ id: 101, title: "Active Task", status: "todo", start_date: "2026-11-02", due_date: "2026-11-04" }],
    2: [{ id: 201, title: "Old Task", status: "done", start_date: "2026-11-02", due_date: "2026-11-04" }],
  };

  assert.equal(isProjectCompleted(projects[0]), false);
  assert.equal(isProjectCompleted(projects[1]), true);
  assert.equal(filterProjectsByStatus(projects, "all").length, 2);
  assert.equal(filterProjectsByStatus(projects, "active").length, 1);
  assert.equal(filterProjectsByStatus(projects, "done").length, 1);

  // 1. 'all' shows everything: both active & completed projects, plus both active & completed subtasks
  const allWeeks = buildMonthlyWeekRows(2026, 11, projects, tasksMap, {
    taskFilterMode: "all",
  });
  const allWeek1Items = allWeeks.weeks[0].items;
  assert.equal(allWeek1Items.length, 4, "'all' mode should show both projects and both tasks");

  // 2. 'active' hides completed projects and completed subtasks
  const activeWeeks = buildMonthlyWeekRows(2026, 11, projects, tasksMap, {
    taskFilterMode: "active",
  });
  const activeWeek1Items = activeWeeks.weeks[0].items;
  assert.equal(activeWeek1Items.length, 2, "'active' mode should only show Active Project + Active Task");
  assert.ok(
    activeWeek1Items.every((item) => item.projectId === 1),
    "Finished project (id=2) is hidden when clicking Active"
  );

  // 3. 'done' shows only completed projects and completed subtasks
  const doneWeeks = buildMonthlyWeekRows(2026, 11, projects, tasksMap, {
    taskFilterMode: "done",
  });
  const doneWeek1Items = doneWeeks.weeks[0].items;
  assert.ok(
    doneWeek1Items.some((item) => item.projectId === 2 && item.kind === "project"),
    "Completed project appears when viewing the 'done' filter"
  );
  assert.ok(
    !doneWeek1Items.some((item) => item.projectId === 1 && item.kind === "project"),
    "Active project bar is hidden when viewing the 'done' filter"
  );
});

test("Projects Kanban drag-and-drop moves projects across status columns and reorders cards", () => {
  const initialProjects = [
    { id: 1, name: "P1", status: "planned", sidebar_order: 0 },
    { id: 2, name: "P2", status: "active", sidebar_order: 1 },
    { id: 3, name: "P3", status: "active", sidebar_order: 2 },
    { id: 4, name: "P4", status: "on_hold", sidebar_order: 3 },
  ];

  // 1. Drag P1 from 'planned' and drop onto 'active' column before P2
  const move1 = moveProjectInKanban(initialProjects, 1, "active", {
    targetProjectId: 2,
    position: "before",
  });
  assert.equal(move1.movedProject.status, "active");
  const cols1 = groupProjectsForKanban(move1.projects);
  assert.equal(cols1.find((c) => c.status === "planned").count, 0);
  assert.deepEqual(
    cols1.find((c) => c.status === "active").projects.map((p) => p.id),
    [1, 2, 3]
  );

  // 2. Reorder within 'active' column: drag P1 after P3
  const move2 = moveProjectInKanban(move1.projects, 1, "active", {
    targetProjectId: 3,
    position: "after",
  });
  const cols2 = groupProjectsForKanban(move2.projects);
  assert.deepEqual(
    cols2.find((c) => c.status === "active").projects.map((p) => p.id),
    [2, 3, 1]
  );

  // 3. Drag P4 into empty 'completed' column
  const move3 = moveProjectInKanban(move2.projects, 4, "completed");
  const cols3 = groupProjectsForKanban(move3.projects);
  assert.equal(cols3.find((c) => c.status === "completed").count, 1);
  assert.equal(cols3.find((c) => c.status === "completed").projects[0].id, 4);
  assert.deepEqual(
    move3.projects.map((p) => p.sidebar_order),
    [0, 1, 2, 3]
  );
});

test("Date shift and span helpers support project timeline dragging and extending", () => {
  // 1. Shifting days (drag to reposition)
  assert.equal(shiftDateIso("2026-11-05", 3), "2026-11-08");
  assert.equal(shiftDateIso("2026-11-05", -6), "2026-10-30");
  assert.equal(shiftDateIso("2026-11-01", 0), "2026-11-01");

  // 2. Calculating total duration days (extend to shorten/lengthen)
  assert.equal(calculateDateSpanDays("2026-11-01", "2026-11-05"), 5);
  assert.equal(calculateDateSpanDays("2026-11-05", "2026-11-05"), 1);
  assert.equal(calculateDateSpanDays("2026-10-28", "2026-11-03"), 7);

  // 3. Shifting months (year view timeline drag)
  assert.equal(shiftDateMonths("2026-11-15", 1), "2026-12-15");
  assert.equal(shiftDateMonths("2026-11-15", -2), "2026-09-15");
  assert.equal(shiftDateMonths("2026-01-31", 1), "2026-02-28");
});

test("Dragging or resizing a project clips subtasks s.t. no subtask happens before or after the main project", () => {
  const origProj = { id: 10, start_date: "2026-11-05", target_date: "2026-11-20" };
  const origTasks = [
    { id: 101, start_date: "2026-11-05", due_date: "2026-11-08" },
    { id: 102, start_date: "2026-11-10", due_date: "2026-11-15" },
    { id: 103, start_date: "2026-11-18", due_date: "2026-11-20" },
  ];

  // 1. Resize-start: Dragging project start forward from Nov 05 to Nov 12
  // Subtask 101 (Nov 05-08) is before the new start, so it gets clipped to Nov 12..Nov 12
  // Subtask 102 (Nov 10-15) has start Nov 10 < Nov 12, so its start clips to Nov 12
  // Subtask 103 (Nov 18-20) remains intact
  const resizeStartRes = computeProjectDragResult(origProj, origTasks, "resize-start", 7);
  assert.equal(resizeStartRes.start_date, "2026-11-12");
  assert.equal(resizeStartRes.target_date, "2026-11-20");
  assert.deepEqual(resizeStartRes.tasks.find((t) => t.id === 101), {
    id: 101,
    start_date: "2026-11-12",
    due_date: "2026-11-12",
  });
  assert.deepEqual(resizeStartRes.tasks.find((t) => t.id === 102), {
    id: 102,
    start_date: "2026-11-12",
    due_date: "2026-11-15",
  });
  assert.deepEqual(resizeStartRes.tasks.find((t) => t.id === 103), {
    id: 103,
    start_date: "2026-11-18",
    due_date: "2026-11-20",
  });

  // Verify no subtask starts before the main project or ends after the main project
  for (const t of resizeStartRes.tasks) {
    assert.ok(t.start_date >= resizeStartRes.start_date, "subtask start >= project start");
    assert.ok(t.due_date <= resizeStartRes.target_date, "subtask due <= project target");
  }

  // 2. Resize-end: Shortening project end from Nov 20 to Nov 12
  // Subtask 103 (Nov 18-20) gets clipped to Nov 12..Nov 12
  // Subtask 102 (Nov 10-15) gets due clipped from Nov 15 to Nov 12
  const resizeEndRes = computeProjectDragResult(origProj, origTasks, "resize-end", -8);
  assert.equal(resizeEndRes.start_date, "2026-11-05");
  assert.equal(resizeEndRes.target_date, "2026-11-12");
  assert.deepEqual(resizeEndRes.tasks.find((t) => t.id === 103), {
    id: 103,
    start_date: "2026-11-12",
    due_date: "2026-11-12",
  });
  assert.deepEqual(resizeEndRes.tasks.find((t) => t.id === 102), {
    id: 102,
    start_date: "2026-11-10",
    due_date: "2026-11-12",
  });
  for (const t of resizeEndRes.tasks) {
    assert.ok(t.start_date >= resizeEndRes.start_date, "subtask start >= project start");
    assert.ok(t.due_date <= resizeEndRes.target_date, "subtask due <= project target");
  }

  // 3. Move: shifting whole project by 3 days
  const moveRes = computeProjectDragResult(origProj, origTasks, "move", 3);
  assert.equal(moveRes.start_date, "2026-11-08");
  assert.equal(moveRes.target_date, "2026-11-23");
  assert.deepEqual(moveRes.tasks.find((t) => t.id === 101), {
    id: 101,
    start_date: "2026-11-08",
    due_date: "2026-11-11",
  });
});

test("Subtasks are draggable and stretchable, strictly constrained to the main project range", () => {
  const projStart = "2026-11-05";
  const projEnd = "2026-11-15";
  const origTask = { start_date: "2026-11-07", due_date: "2026-11-10" };

  // 1. Move subtask forward by 3 days: Nov 07-10 -> Nov 10-13 (within project range)
  const moved = computeSubtaskDragResult(origTask, projStart, projEnd, "move", 3);
  assert.equal(moved.start_date, "2026-11-10");
  assert.equal(moved.due_date, "2026-11-13");

  // 2. Move subtask past project end: clamped so it doesn't overshoot projEnd
  const moveOver = computeSubtaskDragResult(origTask, projStart, projEnd, "move", 10);
  assert.equal(moveOver.due_date, projEnd);
  assert.equal(moveOver.start_date, "2026-11-12");

  // 3. Stretch start handle (resize-start) backward beyond project start: clamped to projStart
  const stretchStart = computeSubtaskDragResult(origTask, projStart, projEnd, "resize-start", -5);
  assert.equal(stretchStart.start_date, projStart);
  assert.equal(stretchStart.due_date, "2026-11-10");

  // 4. Stretch end handle (resize-end) forward beyond project end: clamped to projEnd
  const stretchEnd = computeSubtaskDragResult(origTask, projStart, projEnd, "resize-end", 10);
  assert.equal(stretchEnd.start_date, "2026-11-07");
  assert.equal(stretchEnd.due_date, projEnd);
});

test("Clicking on main project makes subtasks optionally visible on the timeline", () => {
  const sampleProjects = [
    { id: 1, name: "Alpha", start_date: "2026-11-01", target_date: "2026-11-15", status: "active" },
    { id: 2, name: "Beta", start_date: "2026-11-01", target_date: "2026-11-15", status: "active" },
  ];
  const sampleTasks = {
    1: [{ id: 11, title: "Alpha Task", start_date: "2026-11-02", due_date: "2026-11-04" }],
    2: [{ id: 21, title: "Beta Task", start_date: "2026-11-05", due_date: "2026-11-07" }],
  };

  // Only project 1 subtasks visible
  const specProj1 = buildMonthlyWeekRows(2026, 11, sampleProjects, sampleTasks, {
    visibleSubtaskProjectIds: new Set([1]),
  });
  const allWeekItems1 = specProj1.weeks.flatMap((w) => w.items);
  assert.ok(allWeekItems1.some((it) => it.kind === "task" && it.taskId === 11));
  assert.ok(!allWeekItems1.some((it) => it.kind === "task" && it.taskId === 21));

  // No subtasks visible (collapsed)
  const specNone = buildMonthlyWeekRows(2026, 11, sampleProjects, sampleTasks, {
    visibleSubtaskProjectIds: new Set(),
  });
  const allWeekItemsNone = specNone.weeks.flatMap((w) => w.items);
  assert.ok(!allWeekItemsNone.some((it) => it.kind === "task"));

  // Both projects subtasks visible (expanded)
  const specBoth = buildMonthlyWeekRows(2026, 11, sampleProjects, sampleTasks, {
    visibleSubtaskProjectIds: new Set([1, 2]),
  });
  const allWeekItemsBoth = specBoth.weeks.flatMap((w) => w.items);
  assert.ok(allWeekItemsBoth.some((it) => it.kind === "task" && it.taskId === 11));
  assert.ok(allWeekItemsBoth.some((it) => it.kind === "task" && it.taskId === 21));
});

test("Week View builds a single focused 7-day row with days, projects, clipped subtasks, and track stacking", () => {
  const sampleProjects = [
    { id: 1, name: "Core Architecture", start_date: "2026-11-01", target_date: "2026-11-15", status: "active" },
  ];
  const sampleTasks = {
    1: [
      { id: 101, title: "Subtask 1", start_date: "2026-11-02", due_date: "2026-11-04" },
      { id: 102, title: "Subtask 2", start_date: "2026-11-04", due_date: "2026-11-06" },
    ],
  };
  const dailyNotes = {
    "2026-11-03": { title: "Arch Note", content_md: "Architectural decisions for timeline." },
  };

  const weekRow = buildFocusedWeekRow("2026-11-03", sampleProjects, sampleTasks, {
    dailyNotesMap: dailyNotes,
    todayIso: "2026-11-03",
    visibleSubtaskProjectIds: new Set([1]),
  });

  // Verify 7 days are generated
  assert.equal(weekRow.days.length, 7);
  assert.equal(weekRow.weekStartIso, "2026-11-01"); // Sunday
  assert.equal(weekRow.weekEndIso, "2026-11-07");   // Saturday

  // Verify journal indicator
  const tuesday = weekRow.days.find((d) => d.iso === "2026-11-03");
  assert.ok(tuesday.hasJournal);
  assert.equal(tuesday.isToday, true);

  // Verify items contain both the project span and its subtasks
  assert.ok(weekRow.items.some((it) => it.kind === "project" && it.projectId === 1));
  assert.ok(weekRow.items.some((it) => it.kind === "task" && it.taskId === 101));
  assert.ok(weekRow.items.some((it) => it.kind === "task" && it.taskId === 102));

  // Verify trackRow vertical stacking avoids collisions
  const projItem = weekRow.items.find((it) => it.kind === "project");
  assert.equal(projItem.trackRow, 1);
  assert.ok(weekRow.totalTracks >= 2);
});

test("Habit Heatmap Grid builds 52 full weeks with correct intensities and weekday alignment", () => {
  const sampleDays = [
    { date: "2026-11-01", total_habits: 4, completed_count: 4, rate: 1.0, habits: { run: true } },
    { date: "2026-11-02", total_habits: 4, completed_count: 2, rate: 0.5, habits: { run: true } },
    { date: "2026-11-03", total_habits: 4, completed_count: 1, rate: 0.25, habits: { run: true } },
  ];

  const grid = buildHabitHeatmapGrid(sampleDays, new Date("2026-11-03T12:00:00Z"));
  assert.equal(grid.length, 52); // 52 columns

  // Each column must have 7 days (Monday to Sunday)
  for (const week of grid) {
    assert.equal(week.days.length, 7);
  }

  // Level intensity mapping
  assert.equal(getHeatmapLevel(0), 0);
  assert.equal(getHeatmapLevel(0.2), 1);
  assert.equal(getHeatmapLevel(0.5), 2);
  assert.equal(getHeatmapLevel(0.7), 3);
  assert.equal(getHeatmapLevel(1.0), 4);
});

test("Markdown habit directives extract pills and toggle states accurately", () => {
  const md = `### Habits
- [ ] Morning Workout @habit(workout)
- [x] Read 20 pages @habit(reading, Book Reading) @val(20)
`;

  const pills = extractHabitPills(md);
  assert.equal(pills.length, 2);
  assert.equal(pills[0].slug, "workout");
  assert.equal(pills[0].completed, false);
  assert.equal(pills[1].slug, "reading");
  assert.equal(pills[1].name, "Book Reading");
  assert.equal(pills[1].completed, true);

  // Toggle workout from [ ] to [x]
  const updated1 = toggleHabitInMarkdown(md, "workout", true);
  assert.ok(updated1.includes("- [x] Morning Workout @habit(workout)"));

  // Toggle reading from [x] to [ ]
  const updated2 = toggleHabitInMarkdown(updated1, "reading", false);
  assert.ok(updated2.includes("- [ ] Read 20 pages @habit(reading"));
});

test("Daily Template variable replacement scaffolds date and habit checklist", () => {
  const tpl = `---
date: {{date}}
day: {{day_of_week}}
---
### Habits
{{habits_checklist}}
`;
  const habits = [
    { slug: "stretch", name: "Morning Stretch", archived: false },
    { slug: "run", name: "Run 5K", archived: false },
    { slug: "old", name: "Archived Habit", archived: true },
  ];

  const result = applyTemplateVariables(tpl, "2026-11-02", habits);
  assert.ok(result.includes("date: 2026-11-02"));
  assert.ok(result.includes("day: Monday"));
  assert.ok(result.includes("- [ ] Morning Stretch @habit(stretch)"));
  assert.ok(result.includes("- [ ] Run 5K @habit(run)"));
  assert.ok(!result.includes("Archived Habit"));
});

test("Study Pomodoro time formatting and circular dashoffset calculations", () => {
  assert.equal(formatPomodoroTime(1500), "25:00");
  assert.equal(formatPomodoroTime(65), "01:05");
  assert.equal(formatPomodoroTime(0), "00:00");

  const progress = calculatePomodoroProgress(750, 1500, 120);
  assert.equal(progress.percent, 50);
  // circumference = 2 * PI * 120 ~= 753.98, at 50% dashoffset ~= 376.99
  assert.ok(progress.dashoffset > 370 && progress.dashoffset < 380);
});

test("Study Pomodoro interval cycling and markdown auto-log bullet generation", () => {
  // Cycle 1 focus -> short break
  const step1 = getNextPomodoroMode("focus", 0);
  assert.equal(step1.nextMode, "short_break");
  assert.equal(step1.completedCount, 1);

  // Short break -> focus
  const step2 = getNextPomodoroMode("short_break", 1);
  assert.equal(step2.nextMode, "focus");

  // Cycle 4 focus -> long break
  const step4 = getNextPomodoroMode("focus", 3);
  assert.equal(step4.nextMode, "long_break");
  assert.equal(step4.completedCount, 4);

  // Markdown log bullet
  const bullet = formatStudyLogMarkdown("Neuroscience", 25, "Read chapter 3", "Slides");
  assert.equal(bullet, "- [x] Focus (25m) on [[Neuroscience]] (Slides): Read chapter 3");
});

test("Study Pomodoro wall-clock time remaining prevents background tab throttling drift", () => {
  const now = 1000000;
  // 25 minutes remaining (1500 seconds)
  const targetEnd = now + 1500 * 1000;

  // After 10 minutes (600s), tab wake up
  const wakeUpAfter10Min = now + 600 * 1000;
  assert.equal(computeRemainingSeconds(targetEnd, wakeUpAfter10Min), 900);

  // When past target time (tab was asleep past the session end)
  const wakeUpPastEnd = targetEnd + 5000;
  assert.equal(computeRemainingSeconds(targetEnd, wakeUpPastEnd), 0);
});

test("Sticker placement filters by date/note and computes CSS transform styling", () => {
  const placements = [
    { id: 1, target_type: "calendar_date", target_key: "2026-11-04", sticker_name: "Coffee", pos_x: 70, pos_y: 30, rotation_deg: 10, scale: 120 },
    { id: 2, target_type: "calendar_date", target_key: "2026-11-05", sticker_name: "Star", pos_x: 50, pos_y: 50, rotation_deg: 0, scale: 100 },
    { id: 3, target_type: "note", target_key: "note-101", sticker_name: "Trophy", pos_x: 80, pos_y: 20, rotation_deg: -15, scale: 90 },
  ];

  const dateMatches = filterStickersByTarget(placements, "calendar_date", "2026-11-04");
  assert.equal(dateMatches.length, 1);
  assert.equal(dateMatches[0].sticker_name, "Coffee");

  const noteMatches = filterStickersByTarget(placements, "note", "note-101");
  assert.equal(noteMatches.length, 1);
  assert.equal(noteMatches[0].sticker_name, "Trophy");

  const style = computeStickerTransformStyle(dateMatches[0]);
  assert.equal(style.left, "70%");
  assert.equal(style.top, "30%");
  assert.ok(style.transform.includes("rotate(10deg)"));
  assert.ok(style.transform.includes("scale(1.2)"));

  assert.equal(sanitizeStickerCategory("achievement"), "achievement");
  assert.equal(sanitizeStickerCategory("UNKNOWN_CAT"), "custom");
});

test("Docs-style image parsing, layout directives, and draggable styling", () => {
  const mdWithImages = `
# Project Notes
Here is an inline diagram:
![Architecture](/api/uploads/images/arch.png)

And here is a draggable floating card:
![Mind Map](/api/uploads/images/mindmap.png){mode="draggable", x="45", y="120", w="350"}

And a wrap-left diagram:
![Chart](/api/uploads/images/chart.png){mode="wrap_left", w="240"}
`;

  const parsed = parseDocsImageDirectives(mdWithImages);
  assert.equal(parsed.floatingImages.length, 2);
  const dragImg = parsed.floatingImages[0];
  assert.equal(dragImg.caption, "Mind Map");
  assert.equal(dragImg.mode, "draggable");
  assert.equal(dragImg.x, 45);
  assert.equal(dragImg.y, 120);
  assert.equal(dragImg.width, 350);

  const style = computeDraggableImageStyle(dragImg);
  assert.equal(style.left, "45%");
  assert.equal(style.top, "120px");
  assert.equal(style.width, "350px");

  // Format docs image markdown
  const formattedInline = formatDocsImageMarkdown("Diagram", "/uploads/d.png", "inline");
  assert.equal(formattedInline, "![Diagram](/uploads/d.png)");

  const formattedDrag = formatDocsImageMarkdown("Flow", "/uploads/f.png", "draggable", 60, 40, 400);
  assert.equal(formattedDrag, '![Flow](/uploads/f.png){mode="draggable", x="60", y="40", w="400"}');

  // Verify markdown preview renderer outputs docs image wrappers
  const rendered = renderMarkdownPreviewHtml(mdWithImages);
  assert.ok(rendered.includes('class="md-img-inline"'));
  assert.ok(rendered.includes('class="md-img-wrap-left"'));
});

test("Custom paper themes, typography pairings, and style classes", () => {
  assert.ok(PAPER_THEMES.length >= 5);
  const paperIds = PAPER_THEMES.map((p) => p.id);
  assert.ok(paperIds.includes("clean_cream"));
  assert.ok(paperIds.includes("dot_grid"));
  assert.ok(paperIds.includes("lined_paper"));

  assert.equal(getPaperStyleClass("dot_grid"), "paper-theme-dot_grid");
  assert.equal(getPaperStyleClass("nonexistent"), "paper-theme-clean_cream");

  assert.equal(getTypographyClass("handwritten"), "font-theme-handwritten");
  assert.equal(getTypographyClass("monospace"), "font-theme-monospace");
  assert.equal(getTypographyClass("invalid"), "font-theme-editorial");
});





