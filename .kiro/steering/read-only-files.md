# READ-ONLY Files

## Files marked with `# READ-ONLY` at the top MUST NOT be edited.

Any file beginning with `# READ-ONLY` must not be modified under any circumstances. These files represent immutable contracts or reference data.

## If a READ-ONLY file needs to change:

1. Do NOT edit it directly
2. Discuss with the user — it may need to be regenerated from source
3. The `# READ-ONLY` marker indicates machine-generated output or an immutable data contract

## How to find READ-ONLY files:

```bash
grep -r "^# READ-ONLY" --include="*.py" src/
```
