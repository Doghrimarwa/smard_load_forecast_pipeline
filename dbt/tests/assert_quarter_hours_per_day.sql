-- A day in German time has 96 quarter hours (24 h x 4).
-- Exceptions: the spring time change (23 h = 92) and the autumn change (25 h = 100).
-- The test FAILS if it returns rows: days with any other count are incomplete.
select
    date_local,
    count(*) as quarter_hours
from {{ ref('fct_load_forecast_error') }}
group by date_local
having count(*) not in (92, 96, 100)