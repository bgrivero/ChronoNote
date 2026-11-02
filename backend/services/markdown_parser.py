from dataclasses import dataclass, field
from datetime import date
import re
from typing import Any
import yaml


FRONTMATTER_RE = re.compile(r"\A---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|$)", re.DOTALL)
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
WIKILINK_RE = re.compile(r"\[\[([^\]|#\n]+?)(?:\|([^\]\n]+?))?\]\]")
TAG_RE = re.compile(r"(?:^|(?<=\s))#([a-zA-Z][a-zA-Z0-9_-]{1,49})\b")
TASK_LINE_RE = re.compile(r"^[ \t]*[-*][ \t]+\[([ xX])\][ \t]+(.+)$", re.MULTILINE)

START_DIRECTIVE_RE = re.compile(r"@start\((\d{4}-\d{2}-\d{2})\)")
DUE_DIRECTIVE_RE = re.compile(r"@due\((\d{4}-\d{2}-\d{2})\)")
PRIORITY_DIRECTIVE_RE = re.compile(r"@priority\((low|medium|high|urgent)\)", re.IGNORECASE)
MILESTONE_DIRECTIVE_RE = re.compile(r"@milestone\b", re.IGNORECASE)
HABIT_DIRECTIVE_RE = re.compile(r"@habit\(([^,\)]+?)(?:,\s*([^\)]+?))?\)", re.IGNORECASE)
VAL_DIRECTIVE_RE = re.compile(r"@val\(([^\)]+?)\)", re.IGNORECASE)


def slugify(value: str) -> str:
    """Convert a title or identifier into a URL/WikiLink-safe slug."""
    cleaned = re.sub(r"[^\w\s-]", "", value.strip().lower())
    cleaned = re.sub(r"[\s_]+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or "untitled"


@dataclass
class ExtractedWikiLink:
    target_title: str
    target_slug: str
    display_text: str
    context_snippet: str


@dataclass
class ExtractedInlineTask:
    raw_line: str
    title: str
    completed: bool
    status: str
    progress: int
    priority: str = "medium"
    start_date: date | None = None
    due_date: date | None = None
    is_milestone: bool = False


@dataclass
class ExtractedHabit:
    slug: str
    name: str
    completed: bool
    value: str | None = None
    raw_line: str = ""


@dataclass
class ParsedMarkdownResult:
    frontmatter: dict[str, Any] = field(default_factory=dict)
    body_md: str = ""
    tags: list[str] = field(default_factory=list)
    wikilinks: list[ExtractedWikiLink] = field(default_factory=list)
    inline_tasks: list[ExtractedInlineTask] = field(default_factory=list)
    habits: list[ExtractedHabit] = field(default_factory=list)


def _safe_parse_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return None


def parse_markdown_note(content_md: str) -> ParsedMarkdownResult:
    """Parse YAML frontmatter, #tags, [[WikiLinks]], and inline tasks from Markdown."""
    if not content_md:
        return ParsedMarkdownResult()

    frontmatter: dict[str, Any] = {}
    body_md = content_md

    fm_match = FRONTMATTER_RE.match(content_md)
    if fm_match:
        raw_yaml = fm_match.group(1)
        body_md = content_md[fm_match.end() :]
        try:
            loaded = yaml.safe_load(raw_yaml)
            if isinstance(loaded, dict):
                # Convert any date objects in YAML to ISO strings for JSON serialization
                frontmatter = {
                    str(k): (v.isoformat() if isinstance(v, date) else v)
                    for k, v in loaded.items()
                }
        except yaml.YAMLError:
            frontmatter = {}

    # Strip fenced and inline code before scanning for tags, links, and tasks
    stripped_body = FENCED_CODE_RE.sub("", body_md)
    stripped_no_inline = INLINE_CODE_RE.sub("", stripped_body)

    # 1. Extract tags (merge frontmatter tags if present)
    seen_tags: set[str] = set()
    tags: list[str] = []

    fm_tags = frontmatter.get("tags")
    if isinstance(fm_tags, list):
        for t in fm_tags:
            tag_clean = str(t).lstrip("#").strip().lower()
            if tag_clean and tag_clean not in seen_tags:
                seen_tags.add(tag_clean)
                tags.append(tag_clean)

    for match in TAG_RE.finditer(stripped_no_inline):
        tag_val = match.group(1).lower()
        if tag_val not in seen_tags:
            seen_tags.add(tag_val)
            tags.append(tag_val)

    # 2. Extract [[WikiLinks]] line by line to preserve context snippet
    wikilinks: list[ExtractedWikiLink] = []
    seen_links: set[tuple[str, str]] = set()
    for line in stripped_body.splitlines():
        line_clean = line.strip()
        for wl_match in WIKILINK_RE.finditer(line):
            target_raw = wl_match.group(1).strip()
            alias_raw = (wl_match.group(2) or target_raw).strip()
            target_slug = slugify(target_raw)
            key = (target_slug, alias_raw)
            if key not in seen_links:
                seen_links.add(key)
                wikilinks.append(
                    ExtractedWikiLink(
                        target_title=target_raw,
                        target_slug=target_slug,
                        display_text=alias_raw,
                        context_snippet=line_clean[:280],
                    )
                )

    # 3. Extract inline tasks (- [ ] or - [x]) with timeline and habit directives
    inline_tasks: list[ExtractedInlineTask] = []
    habits: list[ExtractedHabit] = []
    seen_habit_slugs: set[str] = set()

    for task_match in TASK_LINE_RE.finditer(stripped_body):
        check_char = task_match.group(1)
        raw_task_text = task_match.group(2).strip()
        completed = check_char.lower() == "x"

        start_match = START_DIRECTIVE_RE.search(raw_task_text)
        due_match = DUE_DIRECTIVE_RE.search(raw_task_text)
        prio_match = PRIORITY_DIRECTIVE_RE.search(raw_task_text)
        milestone_match = MILESTONE_DIRECTIVE_RE.search(raw_task_text)
        habit_match = HABIT_DIRECTIVE_RE.search(raw_task_text)
        val_match = VAL_DIRECTIVE_RE.search(raw_task_text)

        start_dt = _safe_parse_date(start_match.group(1) if start_match else None)
        due_dt = _safe_parse_date(due_match.group(1) if due_match else None)
        priority = prio_match.group(1).lower() if prio_match else "medium"
        is_milestone = bool(milestone_match)

        # Clean directives out of human-readable task title
        clean_title = START_DIRECTIVE_RE.sub("", raw_task_text)
        clean_title = DUE_DIRECTIVE_RE.sub("", clean_title)
        clean_title = PRIORITY_DIRECTIVE_RE.sub("", clean_title)
        clean_title = MILESTONE_DIRECTIVE_RE.sub("", clean_title)
        clean_title = HABIT_DIRECTIVE_RE.sub("", clean_title)
        clean_title = VAL_DIRECTIVE_RE.sub("", clean_title)
        clean_title = re.sub(r"\s{2,}", " ", clean_title).strip()

        if habit_match:
            h_raw_slug = habit_match.group(1).strip()
            h_explicit_name = habit_match.group(2).strip() if habit_match.group(2) else None
            h_slug = slugify(h_raw_slug)
            h_name = h_explicit_name or clean_title or h_raw_slug.replace("-", " ").title()
            h_val = val_match.group(1).strip() if val_match else None
            if h_slug not in seen_habit_slugs:
                seen_habit_slugs.add(h_slug)
                habits.append(
                    ExtractedHabit(
                        slug=h_slug,
                        name=h_name,
                        completed=completed,
                        value=h_val,
                        raw_line=task_match.group(0).strip(),
                    )
                )

        if clean_title:
            inline_tasks.append(
                ExtractedInlineTask(
                    raw_line=task_match.group(0).strip(),
                    title=clean_title,
                    completed=completed,
                    status="done" if completed else "todo",
                    progress=100 if completed else 0,
                    priority=priority,
                    start_date=start_dt,
                    due_date=due_dt,
                    is_milestone=is_milestone,
                )
            )

    # 4. Check frontmatter for habit declarations
    fm_habits = frontmatter.get("habits")
    if isinstance(fm_habits, dict):
        for k, v in fm_habits.items():
            h_slug = slugify(str(k))
            if h_slug and h_slug not in seen_habit_slugs:
                seen_habit_slugs.add(h_slug)
                is_completed = bool(v) if not isinstance(v, (int, float)) or v > 0 else False
                val_str = str(v) if not isinstance(v, bool) else None
                name_str = str(k).replace("_", " ").replace("-", " ").title()
                habits.append(
                    ExtractedHabit(
                        slug=h_slug,
                        name=name_str,
                        completed=is_completed,
                        value=val_str,
                        raw_line="",
                    )
                )
    elif isinstance(fm_habits, list):
        for item in fm_habits:
            if isinstance(item, str):
                h_slug = slugify(item)
                if h_slug and h_slug not in seen_habit_slugs:
                    seen_habit_slugs.add(h_slug)
                    name_str = item.replace("_", " ").replace("-", " ").title()
                    habits.append(
                        ExtractedHabit(
                            slug=h_slug,
                            name=name_str,
                            completed=True,
                            value=None,
                            raw_line="",
                        )
                    )

    return ParsedMarkdownResult(
        frontmatter=frontmatter,
        body_md=body_md,
        tags=tags,
        wikilinks=wikilinks,
        inline_tasks=inline_tasks,
        habits=habits,
    )
