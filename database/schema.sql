CREATE TABLE vendors (
    vendor_id INTEGER PRIMARY KEY,
    vendor_name VARCHAR(100)
);

CREATE TABLE time_dimensions (
    time_id SERIAL PRIMARY KEY,
    datetime TIMESTAMP NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    hour INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    time_of_day VARCHAR(20),
    UNIQUE(datetime)
);

CREATE TABLE locations (
    location_id SERIAL PRIMARY KEY,
    longitude DECIMAL(10, 7) NOT NULL,
    latitude DECIMAL(10, 7) NOT NULL,
    UNIQUE(longitude, latitude)
);

CREATE TABLE trips (
    trip_id VARCHAR(20) PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    pickup_time_id INTEGER NOT NULL,
    dropoff_time_id INTEGER NOT NULL,
    pickup_location_id INTEGER NOT NULL,
    dropoff_location_id INTEGER NOT NULL,
    passenger_count INTEGER NOT NULL,
    store_and_fwd_flag CHAR(1) NOT NULL,
    trip_duration INTEGER NOT NULL,
    
    CONSTRAINT fk_vendor FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id),
    CONSTRAINT fk_pickup_time FOREIGN KEY (pickup_time_id) REFERENCES time_dimensions(time_id),
    CONSTRAINT fk_dropoff_time FOREIGN KEY (dropoff_time_id) REFERENCES time_dimensions(time_id),
    CONSTRAINT fk_pickup_location FOREIGN KEY (pickup_location_id) REFERENCES locations(location_id),
    CONSTRAINT fk_dropoff_location FOREIGN KEY (dropoff_location_id) REFERENCES locations(location_id),
    
    CONSTRAINT chk_passenger_count CHECK (passenger_count > 0 AND passenger_count <= 9),
    CONSTRAINT chk_trip_duration CHECK (trip_duration > 0),
    CONSTRAINT chk_store_flag CHECK (store_and_fwd_flag IN ('Y', 'N'))
);

CREATE TABLE trip_facts (
    trip_id VARCHAR(20) PRIMARY KEY,
    trip_distance DECIMAL(10, 4),
    trip_speed DECIMAL(8, 4),
    manhattan_distance DECIMAL(10, 4),
    haversine_distance DECIMAL(10, 4),
    trip_efficiency DECIMAL(5, 4),
    hour_of_day INTEGER,
    is_rush_hour BOOLEAN,
    is_weekend BOOLEAN,
    
    CONSTRAINT fk_trip FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE CASCADE
);

-- Indexes for efficient querying
CREATE INDEX idx_trips_vendor ON trips(vendor_id);
CREATE INDEX idx_trips_pickup_time ON trips(pickup_time_id);
CREATE INDEX idx_trips_dropoff_time ON trips(dropoff_time_id);
CREATE INDEX idx_trips_pickup_location ON trips(pickup_location_id);
CREATE INDEX idx_trips_dropoff_location ON trips(dropoff_location_id);
CREATE INDEX idx_trips_duration ON trips(trip_duration);
CREATE INDEX idx_trips_passenger_count ON trips(passenger_count);

-- Composite indexes for common queries
CREATE INDEX idx_trips_time_vendor ON trips(pickup_time_id, vendor_id);
CREATE INDEX idx_trips_location_time ON trips(pickup_location_id, pickup_time_id);

-- Indexes on time dimensions
CREATE INDEX idx_time_hour ON time_dimensions(hour);
CREATE INDEX idx_time_day_of_week ON time_dimensions(day_of_week);
CREATE INDEX idx_time_date ON time_dimensions(year, month, day);
CREATE INDEX idx_time_weekend ON time_dimensions(is_weekend);

-- Indexes on derived features
CREATE INDEX idx_facts_speed ON trip_facts(trip_speed);
CREATE INDEX idx_facts_distance ON trip_facts(trip_distance);
CREATE INDEX idx_facts_rush_hour ON trip_facts(is_rush_hour);

-- Insert vendor data
INSERT INTO vendors (vendor_id, vendor_name) VALUES
(1, 'Creative Mobile Technologies'),
(2, 'VeriFone Inc.');

-- View for easy querying with all denormalized data
CREATE VIEW trip_details AS
SELECT 
    t.trip_id,
    v.vendor_name,
    pt.datetime AS pickup_datetime,
    dt.datetime AS dropoff_datetime,
    pt.hour AS pickup_hour,
    pt.day_of_week AS pickup_day_of_week,
    pt.is_weekend,
    pl.longitude AS pickup_longitude,
    pl.latitude AS pickup_latitude,
    dl.longitude AS dropoff_longitude,
    dl.latitude AS dropoff_latitude,
    t.passenger_count,
    t.store_and_fwd_flag,
    t.trip_duration,
    tf.trip_distance,
    tf.trip_speed,
    tf.manhattan_distance,
    tf.trip_efficiency,
    tf.is_rush_hour
FROM trips t
JOIN vendors v ON t.vendor_id = v.vendor_id
JOIN time_dimensions pt ON t.pickup_time_id = pt.time_id
JOIN time_dimensions dt ON t.dropoff_time_id = dt.time_id
JOIN locations pl ON t.pickup_location_id = pl.location_id
JOIN locations dl ON t.dropoff_location_id = dl.location_id
LEFT JOIN trip_facts tf ON t.trip_id = tf.trip_id;

-- Comments for documentation
COMMENT ON TABLE trips IS 'Main fact table containing trip records';
COMMENT ON TABLE time_dimensions IS 'Time dimension for efficient temporal queries';
COMMENT ON TABLE locations IS 'Location dimension for normalized coordinate storage';
COMMENT ON TABLE trip_facts IS 'Derived features and analytical metrics for each trip';
COMMENT ON VIEW trip_details IS 'Denormalized view for easy querying and reporting';