# FlowGuard --- Data Pipeline Orchestration & Monitoring Platform

FlowGuard is a Python-based data pipeline orchestration and monitoring
application. It ingests CSV order data, validates records, transforms
accepted data, publishes the results to MySQL, and records execution
history for monitoring and troubleshooting.

## 1. Project objectives

-   Run a four-stage data workflow: **EXTRACT → VALIDATE → TRANSFORM →
    PUBLISH**.
-   Track pipeline runs and individual task attempts.
-   Retry failed tasks and record their outcomes.
-   Apply task timeouts and prevent downstream execution after a
    critical upstream failure.
-   Separate invalid records into a rejection/quarantine table.
-   Make transformation and publishing safe to rerun.
-   Expose pipeline metrics and execution details through a Flask
    dashboard and JSON APIs.

## 2. Technology stack

  Area       Technology
  ---------- -----------------------
  Language   Python 3.13
  Backend    Flask
  Database   MySQL 8
  Frontend   HTML, CSS, JavaScript
  Charts     Chart.js
  Testing    pytest

## 3. Pipeline architecture

``` text
CSV input
   |
   v
EXTRACT  -> Read source file and store source records
   |
   v
VALIDATE -> Check required fields, dates, amounts, statuses and duplicates
   |                         |
   | valid records           +--> REJECTED RECORDS
   v
TRANSFORM -> Normalize accepted records
   |
   v
PUBLISH   -> Reconcile and publish records to MySQL
   |
   v
Current published data + audit and run history
```

The orchestration layer manages task order, attempts, timeouts, task
status, and downstream blocking.

## 4. Main components

-   `app/extractor.py` --- reads the CSV input and records source data.
-   `app/validator.py` --- validates records and stores rejected
    records.
-   `app/transformer.py` --- transforms accepted records.
-   `app/publisher.py` --- reconciles and publishes transformed records.
-   `app/orchestrator.py` --- coordinates task execution, retries,
    timeouts and failure handling.
-   `app/dashboard.py` --- Flask routes and dashboard APIs.
-   `run_pipeline.py` --- command-line pipeline entry point.
-   `run_dashboard.py` --- starts the Flask dashboard.
-   `data/generate_data.py` --- generates sample order data.
-   `schema.sql` --- MySQL schema for all seven tables.
-   `DATA_DICTIONARY.md` --- source and table data dictionary.
-   `reconciliation.sql` --- post-run reconciliation queries.
-   `tests/` --- automated tests.

## 5. Database design

The application uses these core MySQL tables:

-   `pipeline_runs` --- one record per pipeline execution, including
    status and row counts.
-   `task_runs` --- task-level execution attempts and outcomes.
-   `source_orders` --- ingested source records.
-   `transformed_orders` --- accepted and transformed records.
-   `rejected_records` --- records that fail data-quality checks.
-   `published_orders` --- published current-state order records.
-   `notifications` --- pipeline events and failure notifications.

## 6. Local setup

### Prerequisites

-   Python 3.13
-   MySQL 8
-   Git (optional, for version control)

### Create and activate a virtual environment

From the project directory in Windows CMD:

``` cmd
python -m venv myenv
myenv\Scripts\activate
```

If your existing virtual environment is stored outside the project,
activate that environment instead.

### Install dependencies

Install the packages listed in your project's `requirements.txt`, if
present:

``` cmd
python -m pip install -r requirements.txt
```

If there is no `requirements.txt`, install the dependencies already used
by the project and create one before sharing the repository.

### Configure environment variables

Create or update `.env` using your local database settings. Do not
commit passwords or secret keys.

Example configuration names (use the exact names expected by your
`app/db.py`):

``` text
DB_HOST=localhost
DB_PORT=3306
DB_NAME=flowguard_db
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
```

### Prepare the database

Create the `flowguard_db` database and apply the included schema:

``` cmd
mysql -u root -p flowguard_db < schema.sql
```

The schema creates the seven tables listed above. `schema.sql` is included in
the project root.

## 7. Run the application

### Start the dashboard

``` cmd
python run_dashboard.py
```

Open:

``` text
http://127.0.0.1:5000/
```

### Run the pipeline

Use the command and arguments supported by your current
`run_pipeline.py`. For example, if the script accepts a source CSV path:

``` cmd
python run_pipeline.py data\sample_orders.csv
```

The Flask dashboard also provides a CSV upload control for starting a
pipeline run.

## 8. Dashboard and API

The dashboard provides pipeline KPIs, execution charts, recent runs,
task history, data-quality information, notifications, CSV upload, and a
live execution monitor.

Available API routes in the current application:

  Route                      Purpose
  -------------------------- ---------------------------------------
  `/health`                  Backend health check
  `/api/overview`            Aggregate pipeline metrics
  `/api/runs`                Recent pipeline runs
  `/api/tasks`               Task execution history
  `/api/notifications`       System notifications
  `/api/quality`             Data-quality summary
  `/api/pipeline/start`      Start a pipeline from an uploaded CSV
  `/api/pipeline/status`     Current pipeline execution status
  `/api/pipeline/progress`   Current run and task progress

## 9. Testing

Run the automated test suite:

``` cmd
python -m pytest -v
```

Additional project scripts available for targeted checks include:

``` cmd
python test_failure.py
python test_timeout.py
```

Run these targeted scripts only after confirming their current contents
and expected database effects. Use a test database or disposable test
data for destructive failure scenarios.

## 10. Sample data expectations

The sample generator has been designed to produce 10,000 order rows with
five intentionally injected data-quality issues. For that specific
generated dataset, the expected validation and publishing counts are:

  Metric                  Expected
  --------------------- ----------
  Input records             10,000
  Accepted records           9,995
  Rejected records               5
  Transformed records        9,995
  Published records          9,995

These are expected sample-data results, not a guarantee for every
uploaded CSV.

## 11. Reliability and operational notes

-   Keep database credentials in `.env`; never publish secrets.
-   Use a separate test database for failure and timeout demonstrations.
-   Preserve run and task history when investigating failures.
-   Verify actual database counts after each demo run.
-   Record benchmark dataset size, runtime, machine configuration and
    measured throughput before reporting performance claims.
-   The current orchestrator's timeout/retry protection applies to
    VALIDATE, TRANSFORM and PUBLISH; EXTRACT does not currently have the
    same worker timeout/retry protection.

## 12. Future improvements

-   Add configurable retry policies and backoff.
-   Add extraction-stage timeout and retry support.
-   Add authentication and role-based dashboard access.
-   Add structured application logging and downloadable run reports.
-   Add benchmark reporting for throughput, latency and resource usage.
-   Add deployment configuration and automated CI checks.

------------------------------------------------------------------------

**Project:** FlowGuard\
**Category:** Data Engineering / Pipeline Orchestration / Monitoring\
**Purpose:** Demonstrate reliable CSV ingestion, data-quality
processing, publishing, audit history and operational monitoring.
