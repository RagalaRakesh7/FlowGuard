# FlowGuard Architecture Diagram

This diagram shows the main components and data flow in the current FlowGuard project.

```mermaid
flowchart TB
    A[CSV Dataset / Dashboard Upload] --> B[Flask Dashboard API]
    B --> C[Pipeline Orchestrator]

    C --> D[EXTRACT]
    D --> E[VALIDATE]

    E -->|Accepted records| F[TRANSFORM]
    E -->|Invalid records| Q[(rejected_records)]

    F --> G[PUBLISH]
    G --> H[(published_orders)]

    D --> S[(source_orders)]
    F --> T[(transformed_orders)]

    C --> R[(pipeline_runs)]
    C --> TR[(task_runs)]
    C --> N[(notifications)]

    B --> O[Dashboard UI]
    O --> K[KPI Cards and Charts]
    O --> L[Live Stage Monitor]
    O --> M[Run and Task History]
    O --> J[Data Quality and Notifications]

    R --> B
    TR --> B
    N --> B
    Q --> B
    H --> B

    classDef frontend fill:#e8e5ff,stroke:#7566d8,color:#211b4b
    classDef process fill:#e4f5ff,stroke:#3996c8,color:#12344a
    classDef storage fill:#e6f7ed,stroke:#329b65,color:#123d29
    class O,K,L,M,J frontend
    class B,C,D,E,F,G process
    class R,TR,N,S,T,Q,H storage
```

## Component responsibilities

| Component | Responsibility |
|---|---|
| CSV dataset | Supplies order records for processing |
| Flask Dashboard API | Accepts uploads and serves dashboard data |
| Pipeline Orchestrator | Runs stages in order, manages retries, timeouts and task status |
| EXTRACT | Reads CSV input and stores source records |
| VALIDATE | Checks data quality and separates invalid records |
| TRANSFORM | Normalizes accepted records |
| PUBLISH | Reconciles and publishes transformed records |
| MySQL tables | Store source, transformed, rejected, published, run, task and notification data |
| Dashboard UI | Displays KPIs, charts, run history, task history and live progress |

## Important execution behaviour

- The normal execution order is EXTRACT → VALIDATE → TRANSFORM → PUBLISH.
- Invalid records are stored separately in `rejected_records`.
- A critical task failure prevents downstream stages from running.
- Task attempts and pipeline outcomes are recorded for audit and troubleshooting.
- The dashboard reads pipeline status and metrics through Flask API routes.

## Notes

This is a logical architecture diagram based on the current project structure and implemented features. It does not imply that FlowGuard currently uses a message broker, cloud orchestration service, distributed workers, or a separate frontend server.
