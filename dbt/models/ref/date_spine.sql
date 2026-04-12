-- Date spine covering a fixed range defined in dbt_project.yml vars.
-- Extend date_spine_start/date_spine_end in dbt_project.yml as needed.
SELECT
    CAST(d AS DATE)                             AS full_date,
    CAST(EXTRACT(YEAR    FROM d) AS INTEGER)    AS year,
    CAST(EXTRACT(QUARTER FROM d) AS INTEGER)    AS quarter,
    CAST(EXTRACT(MONTH   FROM d) AS INTEGER)    AS month,
    monthname(d)                                AS month_name,
    CAST(EXTRACT(WEEK    FROM d) AS INTEGER)    AS week_of_year,
    CAST(EXTRACT(ISODOW  FROM d) AS INTEGER)    AS day_of_week,
    dayname(d)                                  AS day_name
FROM generate_series(
    CAST('{{ var("date_spine_start") }}' AS TIMESTAMP),
    CAST('{{ var("date_spine_end") }}'   AS TIMESTAMP),
    INTERVAL '1 day'
) t(d)
