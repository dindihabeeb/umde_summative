### Data Dictionary

This document describes the relational schema implemented in `database/schema.sql` and the cleaned CSV expected by the loader.

#### Table `vendors`
- vendor_id: INT, PK — Source vendor identifier from TLC feed.

#### Table `locations`
- location_id: INT, PK, auto-increment — Surrogate key for a coordinate pair.
- longitude: DECIMAL(10,7), NOT NULL — Longitude in WGS84.
- latitude: DECIMAL(10,7), NOT NULL — Latitude in WGS84.
- uq_long_lat: UNIQUE(longitude, latitude) — Prevents duplicates.

#### Table `trips`
- trip_id: VARCHAR(20), PK — Unique trip identifier from dataset.
- vendor_id: INT, FK → vendors.vendor_id, NOT NULL.
- pickup_time: DATETIME, NOT NULL — Normalized pickup timestamp.
- dropoff_time: DATETIME, NOT NULL — Normalized dropoff timestamp.
- pickup_location_id: INT, FK → locations.location_id, NOT NULL.
- dropoff_location_id: INT, FK → locations.location_id, NOT NULL.
- passenger_count: INT, NOT NULL — [1..9] enforced by CHECK.
- store_and_fwd_flag: CHAR(1), NOT NULL — 'Y' or 'N'.
- trip_duration: INT, NOT NULL — Seconds, > 0 enforced by CHECK.

Indexes:
- idx_trips_vendor(vendor_id)
- idx_trips_pickup_location(pickup_location_id)
- idx_trips_dropoff_location(dropoff_location_id)
- idx_trips_passenger_count(passenger_count)

#### View `trip_details`
A denormalized projection to simplify API reads.
- trip_id, vendor_id
- pickup_datetime, dropoff_datetime
- pickup_longitude, pickup_latitude
- dropoff_longitude, dropoff_latitude
- passenger_count, store_and_fwd_flag, trip_duration

#### Cleaned CSV `data/cleaned_train_data.csv`
Selected columns (post-cleaning) expected by the loader (`scripts/load_data.py`):
- id, vendor_id, pickup_datetime, dropoff_datetime
- pickup_longitude, pickup_latitude, dropoff_longitude, dropoff_latitude
- passenger_count, store_and_fwd_flag, trip_duration
- Optional if present: trip_distance, fare_amount, tip_amount (used in analytics, not loaded to base tables in current schema)

#### Derived Features (in `scripts/data_cleaner.py`)
- trip_distance_km = trip_distance × 1.60934
- trip_speed_kmh = trip_distance_km ÷ (trip_duration_seconds/3600), clipped to [0,120]
- fare_per_km = fare_amount ÷ trip_distance_km (guarded for zero)
- hour_of_day, day_of_week, time_period ∈ {morning, afternoon, evening, night}
- distance_category ∈ {very_short, short, medium, long}

#### Validation Rules (cleaning)
- Timestamps must be parseable; duration in (0, 86,400] seconds.
- NYC bounding box: lon ∈ [-74.3, -73.7], lat ∈ [40.5, 41.0].
- trip_distance ∈ (0, 100]; fare_amount ∈ [0, 500].
- passenger_count ∈ [1, 7] during cleaning; DB allows up to 9.
