# LeanRepair Trace Taxonomy

- Root: `results\real_paper_v2`
- Policies: `heuristic, research`

## Aggregate

| Policy | Records | Solve Rate | Exact Rate | Lean-OK Rate | Rejected Lean-OK Records | Accepted After Rejection | Avg Steps | Median Solve Step | Timeouts |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| heuristic | 900 | 10.0% | 0.0% | 10.0% | 0 | 0 | 1.32 | 2.0 | 0 |
| research | 900 | 84.0% | 27.7% | 84.0% | 0 | 0 | 2.55 | 2.0 | 0 |

## Terminal Outcomes

### heuristic

| Terminal kind | Count |
|---|---:|
| parse_error | 315 |
| type_mismatch | 288 |
| failed_typeclass | 143 |
| solved | 90 |
| other | 52 |
| unknown_identifier | 12 |

### research

| Terminal kind | Count |
|---|---:|
| solved | 756 |
| parse_error | 59 |
| other | 34 |
| failed_typeclass | 28 |
| type_mismatch | 16 |
| unknown_identifier | 7 |

## Acceptance Rejections

### heuristic

| Reason | Count |
|---|---:|
| - | 0 |

### research

| Reason | Count |
|---|---:|
| - | 0 |

## Failure Transitions

### heuristic

| First -> terminal | Count |
|---|---:|
| parse_error->parse_error | 315 |
| type_mismatch->type_mismatch | 276 |
| failed_typeclass->failed_typeclass | 141 |
| other->other | 51 |
| parse_error->type_mismatch | 12 |
| unknown_identifier->unknown_identifier | 12 |
| type_mismatch->failed_typeclass | 2 |
| unknown_identifier->other | 1 |

### research

| First -> terminal | Count |
|---|---:|
| parse_error->parse_error | 59 |
| failed_typeclass->failed_typeclass | 27 |
| other->other | 16 |
| type_mismatch->type_mismatch | 15 |
| parse_error->other | 10 |
| unknown_identifier->unknown_identifier | 7 |
| failed_typeclass->other | 5 |
| type_mismatch->other | 3 |
| parse_error->type_mismatch | 1 |
| type_mismatch->failed_typeclass | 1 |

## By Corruption

### heuristic

| Corruption | N | Solve Rate | Lean-OK Rate | Rejected Lean-OK | Exact Rate | Top terminal failure |
|---|---:|---:|---:|---:|---:|---|
| lowercase_type | 118 | 0.0% | 0.0% | 0 | 0.0% | failed_typeclass (65) |
| not_proposition | 194 | 44.3% | 44.3% | 0 | 0.0% | type_mismatch (101) |
| parse_missing_colon | 176 | 0.0% | 0.0% | 0 | 0.0% | parse_error (176) |
| parse_unbalanced_paren | 143 | 1.4% | 1.4% | 0 | 0.0% | parse_error (129) |
| type_mismatch | 140 | 1.4% | 1.4% | 0 | 0.0% | type_mismatch (112) |
| unknown_type_symbol | 129 | 0.0% | 0.0% | 0 | 0.0% | failed_typeclass (62) |

### research

| Corruption | N | Solve Rate | Lean-OK Rate | Rejected Lean-OK | Exact Rate | Top terminal failure |
|---|---:|---:|---:|---:|---:|---|
| lowercase_type | 118 | 90.7% | 90.7% | 0 | 71.2% | other (5) |
| not_proposition | 194 | 95.4% | 95.4% | 0 | 0.0% | other (8) |
| parse_missing_colon | 176 | 69.3% | 69.3% | 0 | 50.6% | parse_error (46) |
| parse_unbalanced_paren | 143 | 88.8% | 88.8% | 0 | 49.7% | parse_error (13) |
| type_mismatch | 140 | 97.1% | 97.1% | 0 | 0.0% | other (3) |
| unknown_type_symbol | 129 | 61.2% | 61.2% | 0 | 3.9% | failed_typeclass (26) |

