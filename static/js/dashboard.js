
let performanceChart = null;
let healthChart = null;

const $ = id => document.getElementById(id);

const formatNumber = value =>
    Number(value || 0).toLocaleString("en-IN");

function statusClass(status) {
    return "status-" + String(status || "pending").toLowerCase();
}

function shortId(value) {
    return value ? String(value).slice(0, 8) + "..." : "—";
}

function formatDate(value) {
    if (!value) return "—";

    const date = new Date(value);

    return Number.isNaN(date.getTime())
        ? String(value)
        : date.toLocaleString("en-IN");
}

async function getAPI(endpoint) {
    const response = await fetch(endpoint, {
        cache: "no-store"
    });

    if (!response.ok) {
        throw new Error(`${endpoint}: HTTP ${response.status}`);
    }

    return response.json();
}


// ==========================================
// DASHBOARD OVERVIEW
// ==========================================

function updateOverview(data) {
    $("total-runs").textContent =
        formatNumber(data.total_runs);

    $("successful-runs").textContent =
        formatNumber(data.successful_runs);

    $("failed-runs").textContent =
        formatNumber(data.failed_runs);

    $("success-rate").textContent =
        `${Number(data.success_rate || 0).toFixed(2)}%`;

    $("input-records").textContent =
        formatNumber(data.total_input_records);

    $("accepted-records").textContent =
        formatNumber(data.total_accepted_records);

    $("rejected-records").textContent =
        formatNumber(data.total_rejected_records);

    $("published-records").textContent =
        formatNumber(data.total_published_records);

    $("donut-total").textContent =
        formatNumber(data.total_runs);

    $("legend-success").textContent =
        formatNumber(data.successful_runs);

    $("legend-failed").textContent =
        formatNumber(data.failed_runs);

    $("legend-running").textContent =
        formatNumber(data.running_runs);
}


// ==========================================
// PERFORMANCE CHART
// ==========================================

function updatePerformanceChart(runs) {
    if (typeof Chart === "undefined") {
        throw new Error(
            "Chart.js is not loaded. Check your internet connection."
        );
    }

    const ordered = [...runs].reverse();

    if (performanceChart) {
        performanceChart.destroy();
    }

    performanceChart = new Chart(
        $("performance-chart"),
        {
            type: "line",

            data: {
                labels: ordered.map(
                    (_, index) => `Run ${index + 1}`
                ),

                datasets: [
                    {
                        label: "Input records",

                        data: ordered.map(
                            run => Number(run.input_count || 0)
                        ),

                        borderColor: "#8b7cff",
                        backgroundColor: "rgba(139,124,255,.12)",
                        fill: true,
                        tension: 0.35
                    },

                    {
                        label: "Published records",

                        data: ordered.map(
                            run => Number(run.published_count || 0)
                        ),

                        borderColor: "#31d69b",
                        backgroundColor: "transparent",
                        tension: 0.35
                    }
                ]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        labels: {
                            color: "#a4b0c7"
                        }
                    }
                },

                scales: {
                    x: {
                        ticks: {
                            color: "#8290a9"
                        },

                        grid: {
                            display: false
                        }
                    },

                    y: {
                        beginAtZero: true,

                        ticks: {
                            color: "#8290a9"
                        },

                        grid: {
                            color: "rgba(148,163,184,.09)"
                        }
                    }
                }
            }
        }
    );
}


// ==========================================
// PIPELINE HEALTH CHART
// ==========================================

function updateHealthChart(data) {
    const context = $("health-chart");

    if (healthChart) {
        healthChart.destroy();
    }

    const successful = Number(data.successful_runs || 0);
    const failed = Number(data.failed_runs || 0);
    const running = Number(data.running_runs || 0);

    healthChart = new Chart(
        context,
        {
            type: "doughnut",

            data: {
                labels: [
                    "Successful",
                    "Failed",
                    "Running"
                ],

                datasets: [
                    {
                        data: [
                            successful,
                            failed,
                            running
                        ],

                        backgroundColor: [
                            "#31d69b",
                            "#ff6b7a",
                            "#4f9cff"
                        ],

                        borderColor: "#111a2b",
                        borderWidth: 4,
                        hoverOffset: 8
                    }
                ]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "72%",

                plugins: {
                    legend: {
                        display: false
                    },

                    tooltip: {
                        enabled: true
                    }
                }
            }
        }
    );
}


// ==========================================
// PIPELINE RUN HISTORY
// ==========================================

function updateRuns(runs) {
    $("runs-table").innerHTML = runs.length
        ? runs.map(run => `
            <tr>
                <td class="run-id" title="${run.run_id}">
                    ${shortId(run.run_id)}
                </td>

                <td>
                    <span class="status-pill ${statusClass(run.status)}">
                        ${run.status}
                    </span>
                </td>

                <td>${formatNumber(run.input_count)}</td>
                <td>${formatNumber(run.accepted_count)}</td>
                <td>${formatNumber(run.rejected_count)}</td>
                <td>${formatNumber(run.published_count)}</td>
                <td>${formatDate(run.started_at)}</td>
            </tr>
        `).join("")
        : `
            <tr>
                <td colspan="7" class="empty-state">
                    No runs available.
                </td>
            </tr>
        `;
}


// ==========================================
// TASK EXECUTION HISTORY
// ==========================================

function updateTasks(tasks) {
    $("tasks-table").innerHTML = tasks.length
        ? tasks.map(task => `
            <tr>
                <td>${task.task_name}</td>

                <td class="run-id">
                    ${shortId(task.run_id)}
                </td>

                <td>
                    ${formatNumber(task.attempt_number)}
                </td>

                <td>
                    <span class="status-pill ${statusClass(task.status)}">
                        ${task.status}
                    </span>
                </td>

                <td>
                    ${formatNumber(task.output_count)}
                </td>

                <td>
                    ${formatDate(task.started_at)}
                </td>
            </tr>
        `).join("")
        : `
            <tr>
                <td colspan="6" class="empty-state">
                    No tasks available.
                </td>
            </tr>
        `;
}


// ==========================================
// DATA QUALITY
// ==========================================

function updateQuality(items) {
    $("quality-list").innerHTML = items.length
        ? items.map(item => `
            <div class="quality-item">

                <div class="quality-symbol">
                    ◇
                </div>

                <div>
                    <strong>
                        Run ${shortId(item.run_id)}
                    </strong>

                    <small>
                        ${item.source_file || "Unknown file"}
                    </small>
                </div>

                <strong class="quality-count">
                    ${formatNumber(item.rejected_count)}
                </strong>

            </div>
        `).join("")
        : `
            <div class="empty-state">
                No rejected records.
            </div>
        `;
}


// ==========================================
// NOTIFICATIONS
// ==========================================

function updateNotifications(items) {
    const unread = items.filter(
        item => Number(item.is_read) === 0
    ).length;

    $("notification-count").textContent = unread;

    $("notification-list").innerHTML = items.length
        ? items.map(item => `
            <div class="notification-item">

                <div class="notification-symbol">
                    ♧
                </div>

                <div>
                    <strong>
                        ${item.notification_type}
                    </strong>

                    <p>
                        ${item.message}
                    </p>

                    <small>
                        ${formatDate(item.created_at)}
                    </small>
                </div>

            </div>
        `).join("")
        : `
            <div class="empty-state">
                No notifications.
            </div>
        `;
}


// ==========================================
// LOAD DASHBOARD DATA
// ==========================================

async function loadDashboard() {
    $("last-updated").textContent =
        "Refreshing dashboard...";

    let overview;

    try {
        overview = await getAPI("/api/overview");
        updateOverview(overview);

    } catch (error) {
        console.error("Overview error:", error);

        $("last-updated").textContent =
            "Overview API failed";

        return;
    }

    const endpoints = [
        {
            url: "/api/runs",
            update: updateRuns,
            name: "Pipeline runs"
        },

        {
            url: "/api/tasks",
            update: updateTasks,
            name: "Task history"
        },

        {
            url: "/api/quality",
            update: updateQuality,
            name: "Data quality"
        },

        {
            url: "/api/notifications",
            update: updateNotifications,
            name: "Notifications"
        }
    ];

    let runs = [];

    for (const endpoint of endpoints) {
        try {
            const result = await getAPI(endpoint.url);

            endpoint.update(result);

            if (endpoint.url === "/api/runs") {
                runs = result;
            }

        } catch (error) {
            console.error(endpoint.name, error);
        }
    }

    try {
        updatePerformanceChart(runs);
        updateHealthChart(overview);

    } catch (error) {
        console.error("Chart error:", error);
    }

    $("last-updated").textContent =
        "Updated " + new Date().toLocaleTimeString("en-IN");
}


// ==========================================
// LIVE PIPELINE MONITORING
// ==========================================

const LIVE_STAGES = [
    {
        name: "EXTRACT",
        key: "extract"
    },

    {
        name: "VALIDATE",
        key: "validate"
    },

    {
        name: "TRANSFORM",
        key: "transform"
    },

    {
        name: "PUBLISH",
        key: "publish"
    }
];


// ==========================================
// FIND LATEST TASK ATTEMPT
// ==========================================

function latestTaskByStage(tasks, stageName) {
    const matches = tasks.filter(
        task => task.task_name === stageName
    );

    if (!matches.length) {
        return null;
    }

    return matches.reduce((latest, task) =>
        Number(task.attempt_number || 0) >
        Number(latest.attempt_number || 0)
            ? task
            : latest
    );
}


// ==========================================
// SAFE TEXT UPDATE
// ==========================================

function setTextIfPresent(id, value) {
    const element = $(id);

    if (element) {
        element.textContent = value;
    }
}


// ==========================================
// UPDATE PIPELINE STAGE CARD
// ==========================================

function updateLiveStage(stage, task) {
    const card = $(`live-stage-${stage.key}`);

    if (!card) {
        return;
    }

    const status = task?.status || "PENDING";

    card.className =
        `live-stage status-${String(status).toLowerCase()}`;

    const statusElement = card.querySelector(
        ".live-stage-status"
    );

    if (statusElement) {
        statusElement.textContent = status;
    }

    setTextIfPresent(
        `${stage.key}-input`,
        task?.input_count == null
            ? "—"
            : formatNumber(task.input_count)
    );

    setTextIfPresent(
        `${stage.key}-output`,
        task?.output_count == null
            ? "—"
            : formatNumber(task.output_count)
    );

    setTextIfPresent(
        `${stage.key}-attempt`,
        task?.attempt_number == null
            ? "—"
            : `Attempt ${task.attempt_number}`
    );

    setTextIfPresent(
        `${stage.key}-duration`,
        task?.duration_seconds == null
            ? "—"
            : `${task.duration_seconds}s`
    );

    if (task?.error_message) {
        card.title = task.error_message;
    } else {
        card.removeAttribute("title");
    }
}


// ==========================================
// UPDATE TASK ATTEMPT HISTORY
// ==========================================

function updateLiveTaskHistory(tasks) {
    const body = $("live-task-history");

    if (!body) {
        return;
    }

    if (!tasks.length) {
        body.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    No task attempts recorded yet.
                </td>
            </tr>
        `;

        return;
    }

    body.innerHTML = tasks.map(task => `
        <tr>
            <td>${task.task_name || "—"}</td>

            <td>
                ${formatNumber(task.attempt_number)}
            </td>

            <td>
                <span class="status-pill ${statusClass(task.status)}">
                    ${task.status || "PENDING"}
                </span>
            </td>

            <td>
                ${formatNumber(task.input_count)}
            </td>

            <td>
                ${formatNumber(task.output_count)}
            </td>

            <td>
                ${task.duration_seconds == null
                    ? "—"
                    : `${task.duration_seconds}s`}
            </td>

            <td class="error-cell">
                ${task.error_message || "—"}
            </td>
        </tr>
    `).join("");
}


// ==========================================
// FETCH LIVE PIPELINE PROGRESS
// ==========================================

async function updateLiveProgress() {
    try {
        const data = await getAPI(
            "/api/pipeline/progress"
        );

        const monitor = $("live-monitor");

        if (monitor) {
            monitor.hidden = false;
        }

        const run = data.run || null;

        const tasks = Array.isArray(data.tasks)
            ? data.tasks
            : [];

        setTextIfPresent(
            "live-run-id",
            run?.run_id || "Waiting for pipeline run"
        );

        setTextIfPresent(
            "live-run-status",
            data.status || "IDLE"
        );

        const badge = $("live-monitor-badge");

        if (badge) {
            badge.textContent = data.status || "IDLE";

            badge.className =
                String(data.status || "idle").toLowerCase();
        }

        LIVE_STAGES.forEach(stage => {
            const latestTask = latestTaskByStage(
                tasks,
                stage.name
            );

            updateLiveStage(stage, latestTask);
        });

        updateLiveTaskHistory(tasks);

    } catch (error) {
        console.error(
            "Live pipeline progress error:",
            error
        );
    }
}


// ==========================================
// PIPELINE UPLOAD AND EXECUTION
// ==========================================

const uploadForm = $("pipeline-upload-form");
const csvInput = $("csv-file");
const startButton = $("start-pipeline-button");
const selectedFileName = $("selected-file-name");

let statusPolling = null;


// ==========================================
// SHOW EXECUTION STATUS
// ==========================================

function showExecutionStatus(
    status,
    message,
    result = null,
    error = null
) {
    const panel = $("pipeline-execution-status");
    const badge = $("execution-status-badge");
    const progress = $("execution-progress-bar");
    const resultBox = $("execution-result");

    panel.hidden = false;

    badge.textContent = status;
    badge.className = "";

    $("execution-status-title").textContent =
        "Pipeline execution";

    $("execution-status-message").textContent =
        message;

    progress.className = "";
    progress.style.width = "0";

    resultBox.replaceChildren();

    if (status === "RUNNING") {
        badge.textContent = "RUNNING";

        progress.classList.add("running");

        progress.style.width = "70%";
    }

    if (status === "SUCCEEDED") {
        badge.classList.add("success");

        progress.style.width = "100%";

        if (result) {
            const details = [
                `Run ID: ${result.run_id}`,
                `Input records: ${formatNumber(result.input_count)}`,
                `Accepted records: ${formatNumber(result.accepted_count)}`,
                `Rejected records: ${formatNumber(result.rejected_count)}`,
                `Transformed records: ${formatNumber(result.transformed_count)}`,
                `Published records: ${formatNumber(result.published_count)}`
            ];

            details.forEach(line => {
                const item = document.createElement("div");

                item.textContent = line;

                resultBox.appendChild(item);
            });
        }
    }

    if (status === "FAILED" || status === "ERROR") {
        badge.classList.add("failed");

        progress.style.width = "100%";

        progress.style.background = "#ff6b7a";

        resultBox.textContent = error || message;
    }

    startButton.disabled = status === "RUNNING";

    startButton.textContent =
        status === "RUNNING"
            ? "Pipeline Running..."
            : "▶  Start Pipeline";
}


// ==========================================
// CHECK PIPELINE STATUS
// ==========================================

async function checkPipelineStatus() {
    try {
        const state = await getAPI(
            "/api/pipeline/status"
        );

        await updateLiveProgress();

        showExecutionStatus(
            state.status,
            state.message,
            state.result,
            state.error
        );

        if (
            state.status === "SUCCEEDED" ||
            state.status === "FAILED"
        ) {
            clearInterval(statusPolling);

            statusPolling = null;

            await loadDashboard();
        }

        return state;

    } catch (error) {
        console.error(
            "Pipeline status error:",
            error
        );

        return null;
    }
}


// ==========================================
// CSV FILE SELECTION
// ==========================================

csvInput.addEventListener("change", () => {
    const file = csvInput.files[0];

    selectedFileName.textContent = file
        ? `${file.name} · ${formatNumber(file.size)} bytes`
        : "No file selected · Maximum 20 MB";
});


// ==========================================
// START PIPELINE
// ==========================================

uploadForm.addEventListener("submit", async event => {
    event.preventDefault();

    const file = csvInput.files[0];

    if (!file) {
        alert("Please select a CSV file.");
        return;
    }

    if (!file.name.toLowerCase().endsWith(".csv")) {
        alert("Only CSV files are allowed.");
        return;
    }

    if (file.size === 0) {
        alert("The selected file is empty.");
        return;
    }

    if (file.size > 20 * 1024 * 1024) {
        alert("Maximum upload size is 20 MB.");
        return;
    }

    startButton.disabled = true;

    showExecutionStatus(
        "RUNNING",
        "Uploading CSV and starting the pipeline..."
    );

    const formData = new FormData();

    formData.append("file", file);

    try {
        const response = await fetch(
            "/api/pipeline/start",
            {
                method: "POST",
                body: formData
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.message || "Pipeline could not start."
            );
        }

        showExecutionStatus(
            "RUNNING",
            data.message
        );

        if (statusPolling) {
            clearInterval(statusPolling);
        }

        await checkPipelineStatus();

        statusPolling = setInterval(
            checkPipelineStatus,
            2000
        );

    } catch (error) {
        showExecutionStatus(
            "ERROR",
            "Unable to start pipeline.",
            null,
            error.message
        );

        startButton.disabled = false;

        console.error(
            "Pipeline start error:",
            error
        );
    }
});


// ==========================================
// DASHBOARD INITIALIZATION
// ==========================================

$("refresh-button").addEventListener(
    "click",
    loadDashboard
);

$("refresh-main").addEventListener(
    "click",
    loadDashboard
);


async function initializeDashboard() {
    await loadDashboard();

    await updateLiveProgress();

    const state = await checkPipelineStatus();

    if (state && state.status === "RUNNING") {

        if (statusPolling) {
            clearInterval(statusPolling);
        }

        statusPolling = setInterval(
            checkPipelineStatus,
            2000
        );
    }
}

initializeDashboard();
