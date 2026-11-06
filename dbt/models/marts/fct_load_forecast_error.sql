-- One row per quarter hour: forecast vs. actual, and the error.
-- error = forecast - actual  ->  positive = forecast too high, negative = too low
with actual as (

    select * from {{ ref('stg_smard__actual_consumption') }}

),

forecast as (

    select * from {{ ref('stg_smard__forecasted_consumption') }}

)

select
    a.start_ts,
    a.end_ts,

    -- German local time, for questions like "which hour of the day?"
    a.start_ts at time zone 'Europe/Berlin'                        as start_local,
    (a.start_ts at time zone 'Europe/Berlin')::date                as date_local,
    extract(hour from a.start_ts at time zone 'Europe/Berlin')::int as hour_local,

    -- grid load
    a.grid_load_mwh                                   as grid_load_actual_mwh,
    f.grid_load_mwh                                   as grid_load_forecast_mwh,
    f.grid_load_mwh - a.grid_load_mwh                 as grid_load_error_mwh,
    abs(f.grid_load_mwh - a.grid_load_mwh)            as grid_load_abs_error_mwh,

    -- residual load (= grid load - wind - solar)
    a.residual_load_mwh                               as residual_load_actual_mwh,
    f.residual_load_mwh                               as residual_load_forecast_mwh,
    f.residual_load_mwh - a.residual_load_mwh         as residual_load_error_mwh,
    abs(f.residual_load_mwh - a.residual_load_mwh)    as residual_load_abs_error_mwh

from actual a
inner join forecast f
    on a.start_ts = f.start_ts