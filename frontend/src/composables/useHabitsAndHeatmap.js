/**
 * useHabitsAndHeatmap.js
 * Composable for GitHub-style habit heatmap geometry, streak analytics,
 * markdown habit directive synchronization, and template scaffolding.
 */

/**
 * Maps a completion rate (0.0 to 1.0) to a GitHub-style intensity level (0 to 4).
 */
export function getHeatmapLevel(rate) {
  if (!rate || rate <= 0) return 0;
  if (rate <= 0.25) return 1;
  if (rate <= 0.5) return 2;
  if (rate <= 0.75) return 3;
  return 4;
}

/**
 * Builds a 52-week x 7-day GitHub-style contribution matrix from a list of day records.
 * Row 0 = Monday, Row 6 = Sunday.
 * Returns columns (weeks), each containing 7 day slots.
 */
export function buildHabitHeatmapGrid(daysList = [], referenceDate = new Date()) {
  const dayMap = new Map();
  for (const d of daysList) {
    if (d && d.date) {
      dayMap.set(d.date, d);
    }
  }

  // Determine end date (reference date or today) and align to Sunday of that week
  const ref = new Date(referenceDate);
  const end = new Date(Date.UTC(ref.getUTCFullYear(), ref.getUTCMonth(), ref.getUTCDate()));
  const endDayOfWeek = (end.getUTCDay() + 6) % 7; // 0=Mon, 6=Sun
  const alignedEnd = new Date(end.getTime() + (6 - endDayOfWeek) * 86_400_000);

  // 52 full weeks = 364 days total (52 columns of 7 days)
  const totalDays = 52 * 7;
  const alignedStart = new Date(alignedEnd.getTime() - (totalDays - 1) * 86_400_000);

  const weeks = [];
  let currentDay = new Date(alignedStart);

  for (let w = 0; w < 52; w++) {
    const weekDays = [];
    for (let dayRow = 0; dayRow < 7; dayRow++) {
      const iso = currentDay.toISOString().slice(0, 10);
      const record = dayMap.get(iso) || {
        date: iso,
        total_habits: 0,
        completed_count: 0,
        rate: 0.0,
        habits: {},
      };

      const level = getHeatmapLevel(record.rate);
      const isFuture = currentDay.getTime() > end.getTime();

      weekDays.push({
        date: iso,
        dayRow, // 0=Mon, 6=Sun
        level: isFuture ? 0 : level,
        isFuture,
        total_habits: record.total_habits || 0,
        completed_count: record.completed_count || 0,
        rate: record.rate || 0.0,
        habits: record.habits || {},
        formattedDate: formatHeatmapDate(currentDay),
      });

      currentDay = new Date(currentDay.getTime() + 86_400_000);
    }
    weeks.push({
      weekIndex: w,
      days: weekDays,
      monthLabel: getMonthLabelForWeek(weekDays[0].date, w, weeks),
    });
  }

  return weeks;
}

/**
 * Format a human-friendly date string for tooltips.
 */
export function formatHeatmapDate(d) {
  const dateObj = typeof d === "string" ? new Date(d + "T00:00:00Z") : d;
  return dateObj.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

function getMonthLabelForWeek(firstDayIso, weekIdx, allWeeks) {
  const parts = firstDayIso.split("-");
  const monthNum = parseInt(parts[1], 10);
  const dayNum = parseInt(parts[2], 10);

  // Show month label if the first day of the week falls in the first 7 days of the month
  if (dayNum <= 7 || weekIdx === 0) {
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const label = monthNames[monthNum - 1];
    // Avoid duplicate adjacent month labels
    if (weekIdx > 0 && allWeeks[weekIdx - 1]?.monthLabel === label) {
      return "";
    }
    return label;
  }
  return "";
}

/**
 * Extract habit pills from markdown content.
 * Matches: - [x] Title @habit(slug) or - [ ] Title @habit(slug)
 */
export function extractHabitPills(markdown = "") {
  if (!markdown) return [];
  const lines = markdown.split(/\r?\n/);
  const habits = [];
  const re = /^[ \t]*[-*][ \t]+\[([ xX])\][ \t]+(.*?)@habit\(([^,\)]+)(?:,\s*([^\)]+))?\)(.*)$/i;

  for (const line of lines) {
    const m = line.match(re);
    if (m) {
      const completed = m[1].toLowerCase() === "x";
      const rawTitle = (m[2] + m[5]).trim();
      const slug = m[3].trim();
      const explicitName = m[4] ? m[4].trim() : null;
      const cleanTitle = rawTitle.replace(/@val\([^\)]+\)/gi, "").trim();

      habits.push({
        slug,
        name: explicitName || cleanTitle || slug,
        completed,
        rawLine: line,
      });
    }
  }
  return habits;
}

/**
 * Toggle a habit's checkbox state directly inside markdown content.
 */
export function toggleHabitInMarkdown(markdown = "", habitSlug, forceCompleted = null) {
  if (!markdown || !habitSlug) return markdown;
  const re = new RegExp(
    `^([ \\t]*[-*][ \\t]+\\[)([ xX])(\\][ \\t]+.*@habit\\(${habitSlug}[,\\)].*)$`,
    "im"
  );
  const match = markdown.match(re);
  if (!match) return markdown;

  const currentCompleted = match[2].toLowerCase() === "x";
  const newCompleted = forceCompleted !== null ? forceCompleted : !currentCompleted;
  const newMark = newCompleted ? "x" : " ";

  return markdown.replace(re, `$1${newMark}$3`);
}

/**
 * Apply template placeholders to scaffold a new daily journal note.
 */
export function applyTemplateVariables(templateMd, isoDate, habits = []) {
  if (!templateMd) return "";
  const dateObj = new Date(isoDate + "T00:00:00Z");
  const weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

  let habitChecklist = "";
  if (habits && habits.length > 0) {
    habitChecklist = habits
      .filter((h) => !h.archived)
      .map((h) => `- [ ] ${h.name} @habit(${h.slug})`)
      .join("\n");
  } else {
    habitChecklist = [
      "- [ ] Morning Routine @habit(morning-routine)",
      "- [ ] Deep Work Block @habit(deep-work)",
      "- [ ] Reading / Learning @habit(reading)",
    ].join("\n");
  }

  return templateMd
    .replace(/\{\{date\}\}/g, isoDate)
    .replace(/\{\{day_of_week\}\}/g, weekdays[dateObj.getUTCDay()])
    .replace(/\{\{year\}\}/g, String(dateObj.getUTCFullYear()))
    .replace(/\{\{month\}\}/g, months[dateObj.getUTCMonth()])
    .replace(/\{\{habits_checklist\}\}/g, habitChecklist);
}
