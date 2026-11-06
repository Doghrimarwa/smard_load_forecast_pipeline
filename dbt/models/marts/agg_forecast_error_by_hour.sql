-- How good is the forecast at each hour of the day (German time)?
-- bias = average error (sign shows the direction), MAE = average size of the error,
-- WAPE = total absolute error as % of total actual load.
select
    hour_local,
    count(grid_load_error_mwh)                                as quarter_hours,

    round(avg(grid_load_error_mwh), 1)                        as grid_load_bias_mwh,
    round(avg(grid_load_abs_error_mwh), 1)                    as grid_load_mae_mwh,
    round(100 * sum(grid_load_abs_error_mwh)
              / sum(grid_load_actual_mwh) filter (where grid_load_abs_error_mwh is not null), 2)
                                                              as grid_load_wape_pct,

    round(avg(residual_load_error_mwh), 1)                    as residual_load_bias_mwh,
    round(avg(residual_load_abs_error_mwh), 1)                as residual_load_mae_mwh

from {{ ref('fct_load_forecast_error') }}
group by hour_local
order by hour_local