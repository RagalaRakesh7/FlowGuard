# FlowGuard Performance Benchmark Report

**Project:** FlowGuard — Data Pipeline Orchestration & Monitoring Platform  
**Environment:** Windows, Python 3.13, MySQL 8, Flask  
**Report status:** Draft — measured durations must be filled from the actual run logs.

## 1. Purpose

This report records the currently available execution evidence for FlowGuard. It separates confirmed record counts from performance measurements that still need to be copied from the actual run output.

## 2. Test environment

| Item | Recorded environment |
|---|---|
| Operating system | Windows |
| Python | 3.13 |
| Database | MySQL 8 |
| Backend/dashboard | Flask |
| Test framework | pytest |
| Local development tool | VS Code |

Machine CPU, RAM, storage type, MySQL configuration and exact Python patch version should be added before presenting a formal benchmark comparison.

## 3. Dataset and execution results

### 3.1 Generated CSV pipeline

The sample CSV generator is designed to produce 10,000 order rows with five intentional data-quality issues.

| Metric | Expected / recorded sample result |
|---|---:|
| Input records | 10,000 |
| Accepted records | 9,995 |
| Rejected records | 5 |
| Transformed records | 9,995 |
| Published records | 9,995 |
| Pipeline status | SUCCEEDED |

A successful run recorded on 11 November 2026 had run ID:

`92042c81-652d-4408-8374-df52f58c48e5`

The recorded stage counts were Extract: 10,000; Validate: 9,995; Transform: 9,995; Publish: 9,995.

### 3.2 Large CDC event run

A previous 100,000-event execution produced the following recorded counts:

| Metric | Recorded result |
|---|---:|
| Input events | 100,000 |
| Accepted events | 100,000 |
| Applied events | 100,000 |
| Duplicate events | 0 |
| Stale events | 0 |
| Rejected events | 0 |
| Run status | SUCCEEDED |

This is evidence from the separate CDC challenge execution. Do not describe it as a FlowGuard CSV pipeline benchmark unless that run was performed by this FlowGuard project.

## 4. Performance measurements

The exact elapsed time for the runs is not available in the project notes used to prepare this report. Enter the values from the terminal output or run logs; do not estimate them.

| Test | Records/events | Elapsed time (seconds) | Throughput (records/events per second) |
|---|---:|---:|---:|
| FlowGuard sample CSV | 10,000 input rows | To be filled | To be calculated |
| CDC large-event run | 100,000 input events | To be filled | To be calculated |

Calculate throughput using:

`Throughput = processed records or events / elapsed seconds`

Use the same definition of “processed” when comparing runs. State whether the numerator is input, accepted, transformed, published, or applied records.

## 5. Test-suite evidence

Previously recorded test results:

- `python -m pytest tests/test_orchestrator.py -v` — 4 tests passed.
- `python -m pytest -v` — 5 tests passed.

Re-run the current test suite before the final submission and update the result if the test count has changed:

```cmd
python -m pytest -v
```

## 6. Reliability features implemented

The current project notes record these behaviours:

- Ordered execution of EXTRACT, VALIDATE, TRANSFORM and PUBLISH.
- Task attempt history stored in MySQL.
- Up to three attempts for protected stages.
- Timeout handling for VALIDATE, TRANSFORM and PUBLISH.
- Downstream tasks are skipped after a critical upstream failure.
- Invalid records are stored in a rejection table.
- Transformation and publishing are designed to be safe to rerun.
- Pipeline and task outcomes are exposed through the Flask dashboard APIs.

**Known limitation:** EXTRACT does not currently have the same worker timeout/retry protection as VALIDATE, TRANSFORM and PUBLISH.

## 7. How to complete the benchmark

For each benchmark run, record:

1. Dataset or event generator used.
2. Input row/event count.
3. Start and finish timestamps, or the exact elapsed duration printed by the application.
4. Accepted, rejected, transformed, published or applied counts as appropriate.
5. Run status and run ID.
6. Machine configuration (CPU, RAM and storage).
7. Whether the database was empty or already contained prior records.

Then calculate throughput with the formula in Section 4.

## 8. Presentation-ready conclusion

FlowGuard has demonstrated successful processing of a 10,000-row sample CSV with five intentionally injected data-quality issues, resulting in 9,995 accepted and published records. The project also has recorded automated test results and task-level orchestration features for retries, timeout handling and downstream failure protection.

A separate CDC challenge run processed 100,000 events with 100,000 accepted and applied, and zero duplicates, stale events or rejected events. Exact elapsed-time measurements must be added before making quantitative throughput or speed claims.

---

**Accuracy note:** This report intentionally leaves unavailable durations and throughput values blank rather than inventing benchmark results. The 100,000-event CDC result is kept separate from the FlowGuard CSV result.
