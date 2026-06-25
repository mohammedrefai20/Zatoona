"""Normalize a Notion page payload (fetched by the student's Notion MCP) into ingestible text.

The fetch happens at the agent/client layer through the student's own Notion MCP connection;
this module only turns the returned page into markdown text plus provenance, so Team A keeps no
Notion SDK dependency. The expected payload is a dict with ``title``, ``url`` or ``id``, and a
``blocks`` list of Notion-style block objects (each ``{"type": <t>, <t>: {"rich_text": [...]}}``,
optionally with nested ``children``).

# future: only readable text blocks are kept; images, embeds, and child databases are skipped.
# Lift that ceiling by OCR'ing block images and reading linked databases as structured rows.
"""

_PREFIX = {
    "heading_1": "# ",
    "heading_2": "## ",
    "heading_3": "### ",
    "paragraph": "",
    "bulleted_list_item": "- ",
    "numbered_list_item": "- ",
    "to_do": "- ",
    "quote": "> ",
    "callout": "",
}


def normalize_page(payload):
    title = (payload.get("title") or "").strip()
    source_ref = payload.get("url") or payload.get("id") or title
    lines = _render_blocks(payload.get("blocks") or [])
    return "\n".join(lines).strip(), source_ref, title


def _render_blocks(blocks):
    lines = []
    for block in blocks:
        btype = block.get("type")
        text = _plain_text(block.get(btype)) if btype in _PREFIX else ""
        if btype == "code":
            text = _plain_text(block.get("code"))
            if text:
                lines.append(f"```\n{text}\n```")
        elif text:
            lines.append(_PREFIX[btype] + text)
        lines.extend(_render_blocks(block.get("children") or []))
    return lines


def _plain_text(content):
    if not isinstance(content, dict):
        return ""
    parts = [rt.get("plain_text", "") for rt in content.get("rich_text") or []]
    return "".join(parts).strip()
