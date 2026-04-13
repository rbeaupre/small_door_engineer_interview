-- No-show rate segmented by lead-time bucket and SMS reminder status.
--
-- Lead time = days between scheduling and appointment date.
-- Rows where lead_time_valid = FALSE are excluded — these are timezone-artifact rows
-- where ScheduledDay (with time component) appears to fall after AppointmentDay (always midnight UTC).
-- Including them would contaminate the same-day bucket.
-- See NOTES.md Assumption 3 for full rationale.
--
-- The SMS breakdown within each bucket surfaces the confounding: EDA shows SMS appointments have higher overall no-show rates
-- But that is partly explained by longer lead times (higher-risk appointments are preferentially reminded).
-- Comparing sms_sent = true vs false within the same lead-time bucket isolates the SMS effect from the lead-time effect.
-- The overall trend is that sending SMS reminders does in fact lower no-show rates by 6-7% per lead-time bucket
SELECT
    CASE
        WHEN lead_time_days = 0          THEN '1. Same day'
        WHEN lead_time_days <= 7         THEN '2. 1–7 days'
        WHEN lead_time_days <= 30        THEN '3. 8–30 days'
        WHEN lead_time_days <= 60        THEN '4. 31–60 days'
        ELSE                                  '5. 60+ days'
    END                                                         AS lead_time_bucket,
    sms_sent,
    COUNT(*)                                                    AS total_appointments,
    SUM(CAST(no_show AS INTEGER))                               AS no_show_count,
    ROUND(SUM(CAST(no_show AS INTEGER)) * 100.0 / COUNT(*), 1)  AS no_show_rate_pct,
    ROUND(AVG(lead_time_days), 1)                               AS avg_lead_time_days
FROM {{ ref('appointments') }}
WHERE lead_time_valid = TRUE
GROUP BY 1, 2
ORDER BY 1, 2
