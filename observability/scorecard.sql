-- ShopAnalysis historical observability scorecard
-- Source: dedicated observability DuckDB database
-- Grain: one row per pipeline run

CREATE OR REPLACE VIEW audit.v_pipeline_run_scorecard AS
WITH stage_metrics AS (
    SELECT
        run_id,
        COUNT(*) AS stage_attempts,
        COUNT(*) FILTER (
            WHERE status = 'SUCCESS'
        ) AS successful_stage_attempts,
        COUNT(*) FILTER (
            WHERE status = 'FAILED'
        ) AS failed_stage_attempts,
        COUNT(*) FILTER (
            WHERE status IN ('SUCCESS', 'FAILED')
        ) AS completed_stage_attempts,
        SUM(attempt_number - 1) AS retry_count
    FROM audit.stage_runs
    GROUP BY run_id
),
quality_metrics AS (
    SELECT
        run_id,
        COUNT(*) AS quality_results,
        COUNT(*) FILTER (
            WHERE status = 'PASS'
        ) AS quality_passes,
        COUNT(*) FILTER (
            WHERE status IN ('PASS', 'WARN', 'FAIL')
        ) AS evaluated_quality_results
    FROM audit.data_quality_results
    GROUP BY run_id
),
reconciliation_metrics AS (
    SELECT
        run_id,
        COUNT(*) AS reconciliation_results,
        COUNT(*) FILTER (
            WHERE status = 'PASS'
        ) AS reconciliation_passes,
        SUM(ABS(difference_rows)) AS absolute_row_difference
    FROM audit.reconciliation_results
    GROUP BY run_id
),
fault_metrics AS (
    SELECT
        run_id,
        COUNT(*) AS fault_injections,
        COUNT(*) FILTER (
            WHERE detected
        ) AS detected_faults
    FROM audit.fault_injection_results
    GROUP BY run_id
)
SELECT
    p.run_id,
    p.pipeline_name,
    p.environment,
    p.batch_id,
    p.status,
    p.started_at,
    p.ended_at,
    CASE
        WHEN p.ended_at IS NOT NULL
        THEN date_diff('millisecond', p.started_at, p.ended_at)
             / 1000.0
    END AS duration_seconds,
    COALESCE(s.stage_attempts, 0) AS stage_attempts,
    COALESCE(s.successful_stage_attempts, 0)
        AS successful_stage_attempts,
    COALESCE(s.failed_stage_attempts, 0)
        AS failed_stage_attempts,
    COALESCE(s.completed_stage_attempts, 0)
        AS completed_stage_attempts,
    COALESCE(s.retry_count, 0) AS retry_count,
    COALESCE(q.quality_results, 0) AS quality_results,
    COALESCE(q.quality_passes, 0) AS quality_passes,
    COALESCE(q.evaluated_quality_results, 0)
        AS evaluated_quality_results,
    COALESCE(r.reconciliation_results, 0)
        AS reconciliation_results,
    COALESCE(r.reconciliation_passes, 0)
        AS reconciliation_passes,
    COALESCE(r.absolute_row_difference, 0)
        AS absolute_row_difference,
    COALESCE(f.fault_injections, 0) AS fault_injections,
    COALESCE(f.detected_faults, 0) AS detected_faults
FROM audit.pipeline_runs AS p
LEFT JOIN stage_metrics AS s USING (run_id)
LEFT JOIN quality_metrics AS q USING (run_id)
LEFT JOIN reconciliation_metrics AS r USING (run_id)
LEFT JOIN fault_metrics AS f USING (run_id);

-- Historical aggregation: one row per pipeline and environment

CREATE OR REPLACE VIEW audit.v_historical_scorecard AS
SELECT
    pipeline_name,
    environment,
    COUNT(*) AS total_runs,
    COUNT(*) FILTER (
        WHERE status IN ('SUCCESS', 'FAILED')
    ) AS completed_runs,
    COUNT(*) FILTER (
        WHERE status = 'SUCCESS'
    ) AS successful_runs,
    COUNT(*) FILTER (
        WHERE status = 'FAILED'
    ) AS failed_runs,

    COUNT(*) FILTER (
        WHERE status = 'SUCCESS'
    )::DOUBLE
    / NULLIF(
        COUNT(*) FILTER (
            WHERE status IN ('SUCCESS', 'FAILED')
        ), 0
    ) AS pipeline_success_rate,

    SUM(stage_attempts) AS stage_attempts,
    SUM(failed_stage_attempts) AS failed_stage_attempts,
    SUM(completed_stage_attempts) AS completed_stage_attempts,
    SUM(retry_count) AS retry_count,

    SUM(failed_stage_attempts)::DOUBLE
    / NULLIF(SUM(completed_stage_attempts), 0)
        AS stage_failure_rate,

    SUM(quality_results) AS quality_results,
    SUM(quality_passes) AS quality_passes,

    SUM(quality_passes)::DOUBLE
    / NULLIF(SUM(evaluated_quality_results), 0)
        AS quality_pass_rate,

    SUM(reconciliation_results) AS reconciliation_results,
    SUM(reconciliation_passes) AS reconciliation_passes,

    SUM(reconciliation_passes)::DOUBLE
    / NULLIF(SUM(reconciliation_results), 0)
        AS reconciliation_pass_rate,

    SUM(absolute_row_difference)
        AS absolute_row_difference,

    SUM(fault_injections) AS fault_injections,
    SUM(detected_faults) AS detected_faults,

    SUM(detected_faults)::DOUBLE
    / NULLIF(SUM(fault_injections), 0)
        AS fault_detection_rate,

    AVG(duration_seconds) FILTER (
        WHERE status IN ('SUCCESS', 'FAILED')
    ) AS average_duration_seconds

FROM audit.v_pipeline_run_scorecard
GROUP BY pipeline_name, environment;
