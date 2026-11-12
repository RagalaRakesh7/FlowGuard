# FlowGuard Data Dictionary

## Source CSV (`sample_orders.csv`)

| Column | Type | Required | Description |
|---|---|---|---|
| `order_id` | string | yes | Business key for an order. Must be non-empty and unique within a run. |
| `customer_id` | string | yes | Customer identifier. Must be non-empty. |
| `order_date` | ISO-8601 date | yes | Order date in `YYYY-MM-DD` format. |
| `amount` | decimal | yes | Order amount. Must be finite and greater than zero. |
| `order_status` | string | yes | One of `PENDING`, `PAID`, `SHIPPED`, `CANCELLED`. |

## MySQL tables

### `pipeline_runs`
One row per pipeline execution. Tracks source file, status, timestamps, and counts.

### `task_runs`
One row per task attempt. Tracks task name, attempt number, status, timestamps, input/output counts, and errors.

### `source_orders`
Raw extracted source records for a run, including the original JSON payload.

### `rejected_records`
Records that failed validation, with source traceability and rejection reason.

### `transformed_orders`
Accepted records after normalization (trimmed IDs, uppercase status).

### `published_orders`
Current published state of orders, keyed by `order_id` for idempotent upserts.

### `notifications`
Pipeline events, including failure notifications.
