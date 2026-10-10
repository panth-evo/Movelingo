# Exam Specification Format

MoveLingo uses JSON specifications to define the format of all exams. Code should never hardcode an exam structure.

## Schema Details
The schema is defined in `services/api/ai/schemas/exam_spec.schema.json`.

Key models:
- **Spec**: Defines `spec_id`, `language`, `cefr`, etc. and holds `sections`.
- **Section**: Defines a `skill` (reading, listening, writing, speaking), duration, and holds `parts`.
- **Part**: Defines specific `task_type`, `item_type`, counts, and holds configuration for `text`, `audio`, `writing`, or `speaking` depending on the skill.
- **Criteria**: Defines rubric bands and points for writing/speaking evaluation.

## Derivation
Specs marked `derived: true` are algorithmic adaptations (scaled lengths and timings) of B1 specs to cover A1, A2, B2, and C1. The UI labels these as practice formats, not official timings.
