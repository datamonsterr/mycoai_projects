# Rule: Document Reading via Markdown

For document-reading tasks in this project, prefer MarkItDown over heavy
format-specific skills.

Default behavior:

- For `.pdf`, `.docx`, `.xlsx`, `.pptx`, and similar office-style files, first
  convert the file to markdown using the local `markitdown` CLI or the
  `markitdown` MCP server.
- Work from the markdown output unless the user explicitly asks to edit file
  internals, preserve advanced formatting, or manipulate XML/package contents.
- Avoid unpacking Office archives or using format-specific workflow docs unless
  the task requires low-level editing rather than content extraction.

Practical guidance:

- CLI fallback: `uvx --from markitdown markitdown <file>`
- Save markdown when needed: `uvx --from markitdown markitdown <file> -o <file>.md`
- Treat the markdown as the primary analysis surface for summarization,
  extraction, and transformation tasks.
