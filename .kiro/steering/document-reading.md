# Document Reading via Markdown

For document-reading tasks, prefer MarkItDown over heavy format-specific tools.

## Default Behavior

For `.pdf`, `.docx`, `.xlsx`, `.pptx` and similar files:
1. Convert to markdown using the `markitdown` MCP server or CLI
2. Work from the markdown output for summarization, extraction, and analysis
3. Only use format-specific tools if the task requires low-level editing

## CLI Fallback

```bash
uvx --from markitdown markitdown <file>
uvx --from markitdown markitdown <file> -o <file>.md
```
