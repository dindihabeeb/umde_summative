CREATE TABLE vendors (
    vendor_id INTEGER PRIMARY KEY,
    vendor_name VARCHAR(100)
);
s
CREATE TABLE locations (
    location_id SERIAL PRIMARY KEY,
    longitude DECIMAL(10, 7) NOT NULL,
    latitude DECIMAL(10, 7) NOT NULL,
    UNIQUE(longitude, latitude)
);

CREATE TABLE trips (
    trip_id VARCHAR(20) PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    pickup_time TIMESTAMP NOT NULL,
    dropoff_time TIMESTAMP NOT NULL,
    pickup_location_id INTEGER NOT NULL,
    dropoff_location_id INTEGER NOT NULL,
    passenger_count INTEGER NOT NULL,
    store_and_fwd_flag CHAR(1) NOT NULL,
    trip_duration INTEGER NOT NULL,
    
    CONSTRAINT fk_vendor FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id),
    CONSTRAINT fk_pickup_location FOREIGN KEY (pickup_location_id) REFERENCES locations(location_id),
    CONSTRAINT fk_dropoff_location FOREIGN KEY (dropoff_location_id) REFERENCES locations(location_id),
    
    CONSTRAINT chk_passenger_count CHECK (passenger_count > 0 AND passenger_count <= 9),
    CONSTRAINT chk_trip_duration CHECK (trip_duration > 0)
);


-- Indexes for efficient querying
CREATE INDEX idx_trips_vendor ON trips(vendor_id);
CREATE INDEX idx_trips_pickup_location ON trips(pickup_location_id);
CREATE INDEX idx_trips_dropoff_location ON trips(dropoff_location_id);
CREATE INDEX idx_trips_passenger_count ON trips(passenger_count);

-- Insert vendor data
INSERT INTO vendors (vendor_id, vendor_name) VALUES
(1, 'Creative Mobile Technologies'),
(2, 'VeriFone Inc.');

-- View for easy querying with all denormalized data
CREATE VIEW trip_details AS
SELECT 
    t.trip_id,
    v.vendor_name,
    t.pickup_time AS pickup_datetime,
    t.dropoff_time AS dropoff_datetime,
    pl.longitude AS pickup_longitude,
    pl.latitude AS pickup_latitude,
    dl.longitude AS dropoff_longitude,
    dl.latitude AS dropoff_latitude,
    t.passenger_count,
    t.store_and_fwd_flag,
    t.trip_duration,
FROM trips t
JOIN vendors v ON t.vendor_id = v.vendor_id
JOIN locations pl ON t.pickup_location_id = pl.location_id
JOIN locations dl ON t.dropoff_location_id = dl.location_id;

-- Comments for documentation
COMMENT ON TABLE trips IS 'Main fact table containing trip records';
COMMENT ON TABLE locations IS 'Location dimension for normalized coordinate storage';
COMMENT ON VIEW trip_details IS 'Denormalized view for easy querying and reporting';