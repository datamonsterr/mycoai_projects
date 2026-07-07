---
inclusion: fileMatch
fileMatchPattern: "**/results/autoresearch/**"
---

# Experiment Visualization — Staircase Chart

## Core Principle

Plot every individual experiment as a single dot on a staircase chart.
X-axis = experiment index (not attempt number). Y-axis = F1 score.

## Staircase Chart Rules

1. **X axis**: experiment index (0, 1, 2, ..., N-1)
2. **Gray dots**: experiments at or below running best
3. **Green dots**: experiments that set a new running best
4. **Green staircase line**: horizontal-only segments connecting green dots
5. **Label format**: `{formula}_{algorithm}` on green dots (< 25 chars)
6. **Legend**: "discarded" (gray, size 15) and "new best" (green, size 60)
7. **Y axis**: F1 0.0-1.0, formatted as decimal
8. **Y limit**: starts at 0, upper bound = max_f1 x 1.15

## For Threshold Experiments (many experiments per attempt)

Each `formula x algorithm` pair = one dot. The chart accumulates ALL experiments across all attempts.

## Do NOT

- Connect gray dots with any line
- Use diagonal segments in the staircase
- Show colored lines for multiple strategies on same chart
- Auto-generate experiment names
- Plot attempt number on x-axis for threshold experiments
