from datetime import date

from backend.services.markdown_parser import parse_markdown_note, slugify


def test_slugify_normalizes_titles():
    assert slugify("Q4 Product Launch & Roadmap!") == "q4-product-launch-roadmap"
    assert slugify("   ") == "untitled"


def test_parse_yaml_frontmatter_and_tags():
    md = """---
owner: bryce
status: draft
tags:
  - roadmap
  - Q4
---
# Heading Should Not Be Tag
Here is a note about #fastapi and #vue3 integration.
```python
# comment_in_code_block_not_a_tag
```
Inline `#ignored_inline_tag` should also be skipped.
"""
    parsed = parse_markdown_note(md)
    assert parsed.frontmatter["owner"] == "bryce"
    assert parsed.frontmatter["status"] == "draft"
    assert parsed.tags == ["roadmap", "q4", "fastapi", "vue3"]


def test_parse_wikilinks_with_and_without_aliases():
    md = """
We discussed [[Architecture Spec]] and linked it to [[Design System|UI Kit v2]].
Duplicate reference to [[Architecture Spec]] on another line.
"""
    parsed = parse_markdown_note(md)
    assert len(parsed.wikilinks) == 2
    assert parsed.wikilinks[0].target_slug == "architecture-spec"
    assert parsed.wikilinks[0].display_text == "Architecture Spec"
    assert parsed.wikilinks[1].target_slug == "design-system"
    assert parsed.wikilinks[1].display_text == "UI Kit v2"


def test_parse_inline_tasks_with_timeline_directives():
    md = """
## Action Items
- [ ] Build left sidebar component @start(2026-11-02) @due(2026-11-06) @priority(high)
- [x] Setup FastAPI database models @due(2026-11-01) @priority(urgent)
- [ ] Public Beta Release @start(2026-11-15) @due(2026-11-15) @milestone
"""
    parsed = parse_markdown_note(md)
    assert len(parsed.inline_tasks) == 3

    t1 = parsed.inline_tasks[0]
    assert t1.title == "Build left sidebar component"
    assert t1.completed is False
    assert t1.status == "todo"
    assert t1.progress == 0
    assert t1.priority == "high"
    assert t1.start_date == date(2026, 11, 2)
    assert t1.due_date == date(2026, 11, 6)
    assert t1.is_milestone is False

    t2 = parsed.inline_tasks[1]
    assert t2.title == "Setup FastAPI database models"
    assert t2.completed is True
    assert t2.status == "done"
    assert t2.progress == 100
    assert t2.priority == "urgent"
    assert t2.due_date == date(2026, 11, 1)

    t3 = parsed.inline_tasks[2]
    assert t3.title == "Public Beta Release"
    assert t3.is_milestone is True
    assert t3.due_date == date(2026, 11, 15)
