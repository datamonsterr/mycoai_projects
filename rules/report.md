# Report Terminology Rule

Context: Research reports, analytics artifacts, and thesis figures describe retrieval filter dimensions.
Mistake: Using `environment` in report-facing or analytics-facing labels when project terminology expects `media` for same concept.
Correct rule: Keep storage/query internals unchanged if needed, but all report outputs, result schemas, charts, tables, and public summaries must use `media` terminology.
Example fix: Rename `env_strategy` display labels to `media_strategy`, `environment_strategy` JSON fields to `media_strategy`, and chart captions like `same environment` to `same media`.
