/**
 * Pomodoro & Study Mode Helper Utilities
 */

export function formatPomodoroTime(totalSeconds) {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds || 0));
  const m = Math.floor(safeSeconds / 60);
  const s = safeSeconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function calculatePomodoroProgress(secondsRemaining, totalSeconds, radius = 120) {
  const safeTotal = Math.max(1, totalSeconds || 1);
  const safeRemaining = Math.max(0, Math.min(secondsRemaining, safeTotal));
  const fraction = safeRemaining / safeTotal;
  const circumference = 2 * Math.PI * radius;
  const dashoffset = circumference * (1 - fraction);
  return {
    fraction,
    percent: Math.round(fraction * 100),
    dashoffset: Number(dashoffset.toFixed(2)),
    circumference: Number(circumference.toFixed(2)),
  };
}

export function getNextPomodoroMode(currentMode, completedCycleCount) {
  if (currentMode === "focus") {
    const nextCount = completedCycleCount + 1;
    if (nextCount % 4 === 0) {
      return { nextMode: "long_break", completedCount: nextCount };
    }
    return { nextMode: "short_break", completedCount: nextCount };
  }
  return { nextMode: "focus", completedCount: completedCycleCount };
}

/**
 * Calculates remaining seconds using wall-clock timestamps to avoid timer drift
 * caused by browser background tab throttling.
 */
export function computeRemainingSeconds(targetTimestampMs, currentTimestampMs = Date.now()) {
  const diffMs = targetTimestampMs - currentTimestampMs;
  return Math.max(0, Math.round(diffMs / 1000));
}

export function formatStudyLogMarkdown(projectName, durationMinutes, intention = "", taskTitle = "") {
  const projTag = projectName ? `[[${projectName}]]` : "General Study";
  const taskTag = taskTitle ? ` (${taskTitle})` : "";
  const intentTag = intention ? `: ${intention.trim()}` : "";
  return `- [x] Focus (${durationMinutes}m) on ${projTag}${taskTag}${intentTag}`;
}
