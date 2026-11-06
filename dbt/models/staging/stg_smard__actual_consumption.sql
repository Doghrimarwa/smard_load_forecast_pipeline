-- Actual consumption: clear column names with units. No business logic here.
with source as (

    select * from {{ source('smard', 'actual_consumption') }}

)

select
    start_ts,
    end_ts,
    grid_load                            as grid_load_mwh,
    grid_load_incl_hydro_pumped_storage  as grid_load_incl_pumped_storage_mwh,
    hydro_pumped_storage                 as pumped_storage_mwh,
    residual_load                        as residual_load_mwh,
    source_file,
    loaded_at
from source