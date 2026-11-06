-- Forecasted consumption: same column names as the actual data, so they are easy to compare.
with source as (

    select * from {{ source('smard', 'forecasted_consumption') }}

)

select
    start_ts,
    end_ts,
    grid_load      as grid_load_mwh,
    residual_load  as residual_load_mwh,
    source_file,
    loaded_at
from source