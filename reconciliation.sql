-- Run after a pipeline execution. Replace the run_id as needed.

-- Source-to-target counts for the latest run.
SELECT
    run_id,
    source_file,
    status,
    input_count,
    accepted_count,
    rejected_count,
    transformed_count,
    published_count,
    input_count - (accepted_count + rejected_count) AS validation_count_gap,
    accepted_count - transformed_count AS transform_count_gap,
    transformed_count - published_count AS publish_count_gap
FROM pipeline_runs
ORDER BY started_at DESC
LIMIT 1;

-- Rejected records by reason.
SELECT
    rejection_reason,
    COUNT(*) AS rejected_count
FROM rejected_records
WHERE run_id = (SELECT run_id FROM pipeline_runs ORDER BY started_at DESC LIMIT 1)
GROUP BY rejection_reason
ORDER BY rejected_count DESC;

-- Published orders should not include rejected source records.
SELECT COUNT(*) AS rejected_records_published
FROM transformed_orders t
INNER JOIN rejected_records r
    ON t.source_record_id = r.source_record_id
    AND t.run_id = r.run_id
WHERE t.run_id = (SELECT run_id FROM pipeline_runs ORDER BY started_at DESC LIMIT 1);
