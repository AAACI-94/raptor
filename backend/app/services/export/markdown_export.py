"""Generate Markdown export from production output."""


def generate_markdown(payload: dict, title: str) -> str:
    """Convert production payload to a clean Markdown document."""
    doc = payload.get("document", {})
    lines = [f"# {title}", ""]

    # Abstract
    if doc.get("abstract"):
        lines.append("## Abstract")
        lines.append("")
        lines.append(doc["abstract"])
        lines.append("")

    # Sections
    for section in doc.get("sections", []):
        level = section.get("level", 1)
        heading = "#" * (level + 1)
        lines.append(f"{heading} {section.get('heading', 'Untitled')}")
        lines.append("")
        lines.append(section.get("content", ""))
        lines.append("")

    # References
    references = doc.get("references", [])
    if references:
        lines.append("## References")
        lines.append("")
        for ref in references:
            lines.append(ref.get("formatted", ""))
        lines.append("")

    return "\n".join(lines)
