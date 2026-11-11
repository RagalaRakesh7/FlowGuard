
import csv
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from app.db import get_connection
from app.extractor import REQUIRED_COLUMNS


# ==========================================
# PROJECT CONFIGURATION
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

UPLOAD_FOLDER = PROJECT_ROOT / "data" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "templates"),
    static_folder=str(PROJECT_ROOT / "static")
)

app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024


# ==========================================
# PIPELINE EXECUTION STATE
# ==========================================

execution_lock = threading.Lock()
state_lock = threading.Lock()

pipeline_state = {
    "job_id": None,
    "source_file": None,
    "status": "IDLE",
    "message": "No pipeline is running.",
    "result": None,
    "error": None
}


# ==========================================
# DATABASE FUNCTIONS
# ==========================================

def fetch_all(query, params=None):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchall()

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


def fetch_one(query, params=None):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchone()

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


def serialize_rows(rows):
    result = []

    for row in rows:
        result.append({
            key: (
                str(value)
                if value is not None and not isinstance(
                    value, (str, int, float, bool)
                )
                else value
            )
            for key, value in row.items()
        })

    return result


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def home():
    return render_template("dashboard.html")


# ==========================================
# DATABASE HEALTH
# ==========================================

@app.route("/health")
def health():

    try:
        result = fetch_one(
            "SELECT VERSION() AS mysql_version"
        )

        return jsonify({
            "status": "HEALTHY",
            "database": "CONNECTED",
            "mysql_version": result["mysql_version"]
        })

    except Exception as error:
        app.logger.exception("Database health check failed")

        return jsonify({
            "status": "UNHEALTHY",
            "database": "DISCONNECTED",
            "error": str(error)
        }), 500


# ==========================================
# DASHBOARD OVERVIEW
# ==========================================

@app.route("/api/overview")
def overview():

    query = """
        SELECT
            COUNT(*) AS total_runs,
            COALESCE(SUM(status = 'SUCCEEDED'), 0)
                AS successful_runs,
            COALESCE(SUM(status = 'FAILED'), 0)
                AS failed_runs,
            COALESCE(SUM(status = 'RUNNING'), 0)
                AS running_runs,
            COALESCE(SUM(input_count), 0)
                AS total_input_records,
            COALESCE(SUM(accepted_count), 0)
                AS total_accepted_records,
            COALESCE(SUM(rejected_count), 0)
                AS total_rejected_records,
            COALESCE(SUM(published_count), 0)
                AS total_published_records
        FROM pipeline_runs
    """

    data = fetch_one(query)

    total = int(data["total_runs"])
    successful = int(data["successful_runs"])

    data["success_rate"] = round(
        (successful / total) * 100, 2
    ) if total else 0

    return jsonify(data)


# ==========================================
# PIPELINE RUN HISTORY
# ==========================================

@app.route("/api/runs")
def runs():

    query = """
        SELECT
            run_id,
            source_file,
            status,
            started_at,
            completed_at,
            input_count,
            accepted_count,
            transformed_count,
            published_count,
            rejected_count,
            error_message
        FROM pipeline_runs
        ORDER BY started_at DESC
        LIMIT 50
    """

    return jsonify(serialize_rows(fetch_all(query)))


# ==========================================
# TASK EXECUTION HISTORY
# ==========================================

@app.route("/api/tasks")
def tasks():

    query = """
        SELECT
            task_run_id,
            run_id,
            task_name,
            attempt_number,
            status,
            started_at,
            ended_at,
            input_count,
            output_count,
            error_message
        FROM task_runs
        ORDER BY task_run_id DESC
        LIMIT 100
    """

    return jsonify(serialize_rows(fetch_all(query)))


# ==========================================
# NOTIFICATIONS
# ==========================================

@app.route("/api/notifications")
def notifications():

    query = """
        SELECT
            notification_id,
            run_id,
            notification_type,
            message,
            is_read,
            created_at
        FROM notifications
        ORDER BY created_at DESC
        LIMIT 50
    """

    return jsonify(serialize_rows(fetch_all(query)))


# ==========================================
# DATA QUALITY
# ==========================================

@app.route("/api/quality")
def quality():

    query = """
        SELECT
            run_id,
            source_file,
            COUNT(*) AS rejected_count
        FROM rejected_records
        GROUP BY run_id, source_file
        ORDER BY MAX(reject_id) DESC
        LIMIT 50
    """

    return jsonify(serialize_rows(fetch_all(query)))


# ==========================================
# PIPELINE WORKER
# ==========================================

def execute_uploaded_pipeline(job_id, file_path):
    """Execute pipeline and synchronize final status from MySQL."""

    try:
        from app.orchestrator import run_pipeline

        # Execute the complete pipeline.
        run_pipeline(str(file_path))

        # Read the final result from MySQL.
        run_query = """
            SELECT
                run_id,
                status,
                input_count,
                accepted_count,
                rejected_count,
                transformed_count,
                published_count,
                error_message
            FROM pipeline_runs
            WHERE source_file = %s
            ORDER BY started_at DESC
            LIMIT 1
        """

        runs = fetch_all(run_query, (file_path.name,))

        if not runs:
            raise RuntimeError(
                "Pipeline returned, but no matching database run was found."
            )

        run = runs[0]
        final_status = run["status"]

        result = {
            "run_id": run["run_id"],
            "status": final_status,
            "input_count": run["input_count"],
            "accepted_count": run["accepted_count"],
            "rejected_count": run["rejected_count"],
            "transformed_count": run["transformed_count"],
            "published_count": run["published_count"]
        }

        if final_status == "SUCCEEDED":
            message = "Pipeline completed successfully."
            error_message = None

        elif final_status == "FAILED":
            message = "Pipeline execution failed."
            error_message = (
                run.get("error_message") or "Pipeline failed."
            )

        else:
            message = f"Pipeline status: {final_status}"
            error_message = None

        with state_lock:
            if pipeline_state["job_id"] == job_id:
                pipeline_state.update({
                    "status": final_status,
                    "message": message,
                    "result": result,
                    "error": error_message
                })

    except Exception as error:

        app.logger.exception(
            "Pipeline execution failed: %s",
            job_id
        )

        with state_lock:
            if pipeline_state["job_id"] == job_id:
                pipeline_state.update({
                    "status": "FAILED",
                    "message": "Pipeline execution failed.",
                    "result": None,
                    "error": str(error)
                })

    finally:
        execution_lock.release()


# ==========================================
# START PIPELINE API
# ==========================================

@app.route("/api/pipeline/start", methods=["POST"])
def start_pipeline():

    if "file" not in request.files:
        return jsonify({
            "status": "ERROR",
            "message": "Please select a CSV file."
        }), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({
            "status": "ERROR",
            "message": "No file selected."
        }), 400

    filename = secure_filename(uploaded_file.filename)

    if not filename or not filename.lower().endswith(".csv"):
        return jsonify({
            "status": "ERROR",
            "message": "Only CSV files are allowed."
        }), 400

    # Prevent simultaneous pipeline execution.
    if not execution_lock.acquire(blocking=False):
        return jsonify({
            "status": "RUNNING",
            "message": "Another pipeline is already running."
        }), 409

    job_id = str(uuid.uuid4())
    file_path = UPLOAD_FOLDER / f"{job_id}_{filename}"

    try:
        uploaded_file.save(file_path)

        if file_path.stat().st_size == 0:
            raise ValueError("Uploaded CSV file is empty.")

        # Validate CSV headers.
        with file_path.open(
            "r",
            newline="",
            encoding="utf-8-sig"
        ) as csv_file:

            reader = csv.DictReader(csv_file)

            if not reader.fieldnames:
                raise ValueError(
                    "CSV file is empty or has no header."
                )

            missing = [
                column
                for column in REQUIRED_COLUMNS
                if column not in reader.fieldnames
            ]

            if missing:
                raise ValueError(
                    f"CSV missing required columns: {missing}"
                )

        # Store the uploaded filename for status and progress APIs.
        with state_lock:
            pipeline_state.update({
                "job_id": job_id,
                "source_file": file_path.name,
                "status": "RUNNING",
                "message": "Pipeline execution started.",
                "result": None,
                "error": None
            })

        worker = threading.Thread(
            target=execute_uploaded_pipeline,
            args=(job_id, file_path),
            daemon=True
        )

        worker.start()

        return jsonify({
            "status": "RUNNING",
            "job_id": job_id,
            "message": "Pipeline started successfully."
        }), 202

    except Exception as error:

        file_path.unlink(missing_ok=True)

        with state_lock:
            if pipeline_state["job_id"] == job_id:
                pipeline_state.update({
                    "status": "FAILED",
                    "message": "Could not start pipeline.",
                    "result": None,
                    "error": str(error)
                })

        execution_lock.release()

        app.logger.exception("Could not start pipeline")

        return jsonify({
            "status": "ERROR",
            "message": str(error)
        }), 400


# ==========================================
# PIPELINE EXECUTION STATUS API
# ==========================================

@app.route("/api/pipeline/status")
def pipeline_status():

    with state_lock:
        current_state = pipeline_state.copy()

    source_file = current_state.get("source_file")

    if source_file:

        query = """
            SELECT
                run_id,
                status,
                input_count,
                accepted_count,
                rejected_count,
                transformed_count,
                published_count
            FROM pipeline_runs
            WHERE source_file = %s
            ORDER BY started_at DESC
            LIMIT 1
        """

        runs = fetch_all(query, (source_file,))

        if runs:
            run = runs[0]

            if run["status"] in ("SUCCEEDED", "FAILED"):

                result = {
                    "run_id": run["run_id"],
                    "status": run["status"],
                    "input_count": run["input_count"],
                    "accepted_count": run["accepted_count"],
                    "rejected_count": run["rejected_count"],
                    "transformed_count": run["transformed_count"],
                    "published_count": run["published_count"]
                }

                message = (
                    "Pipeline completed successfully."
                    if run["status"] == "SUCCEEDED"
                    else "Pipeline execution failed."
                )

                with state_lock:
                    if pipeline_state["job_id"] == current_state["job_id"]:
                        pipeline_state.update({
                            "status": run["status"],
                            "message": message,
                            "result": result,
                            "error": None
                        })

                current_state.update({
                    "status": run["status"],
                    "result": result,
                    "message": message,
                    "error": None
                })

    return jsonify(current_state)


# ==========================================
# LIVE PIPELINE TASK PROGRESS API
# ==========================================

@app.route("/api/pipeline/progress")
def pipeline_progress():

    with state_lock:
        current_state = pipeline_state.copy()

    source_file = current_state.get("source_file")

    if not source_file:
        return jsonify({
            "status": current_state["status"],
            "run_id": None,
            "tasks": []
        })

    # Get the database run for this uploaded file.
    run_query = """
        SELECT
            run_id,
            source_file,
            status,
            started_at,
            completed_at,
            input_count,
            accepted_count,
            transformed_count,
            published_count,
            rejected_count
        FROM pipeline_runs
        WHERE source_file = %s
        ORDER BY started_at DESC
        LIMIT 1
    """

    runs = fetch_all(run_query, (source_file,))

    if not runs:
        return jsonify({
            "status": current_state["status"],
            "run_id": None,
            "tasks": []
        })

    run = runs[0]

    # Retrieve every attempt for each pipeline stage.
    task_query = """
        SELECT
            task_run_id,
            task_name,
            attempt_number,
            status,
            started_at,
            ended_at,
            input_count,
            output_count,
            error_message,
            ROUND(
                TIMESTAMPDIFF(
                    MICROSECOND,
                    started_at,
                    COALESCE(ended_at, NOW())
                ) / 1000000,
                2
            ) AS duration_seconds
        FROM task_runs
        WHERE run_id = %s
        ORDER BY
            FIELD(
                task_name,
                'EXTRACT',
                'VALIDATE',
                'TRANSFORM',
                'PUBLISH'
            ),
            attempt_number
    """

    tasks = fetch_all(task_query, (run["run_id"],))

    return jsonify({
        "status": run["status"],
        "run": serialize_rows([run])[0],
        "tasks": serialize_rows(tasks)
    })


# ==========================================
# FILE SIZE ERROR HANDLER
# ==========================================

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "status": "ERROR",
        "message": "File exceeds the 20 MB upload limit."
    }), 413


# ==========================================
# DIRECT EXECUTION
# ==========================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True
    )
