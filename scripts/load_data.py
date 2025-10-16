#!/usr/bin/env python3
"""
Load cleaned NYC taxi trips from data/cleaned_train_data.csv into MySQL schema defined in database/schema.sql.

"""

import os
import sys
import csv
import math
import argparse
from typing import Dict, Tuple, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import pymysql
from pymysql.cursors import DictCursor


def get_db_connection():
    host = os.getenv('DB_HOST', 'localhost')
    database = os.getenv('DB_NAME', 'nyc_taxi')
    user = os.getenv('DB_USER', 'root')
    password = os.getenv('DB_PASSWORD', '')
    port = int(os.getenv('DB_PORT', '3306'))

    return pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        cursorclass=DictCursor,
        autocommit=False,
        charset='utf8mb4'
    )


def round_coord(value: str) -> Optional[float]:
    if value is None or value == '':
        return None
    try:
        # round to 7 decimals to align with DECIMAL(10,7)
        return round(float(value), 7)
    except ValueError:
        return None


def ensure_vendor(cursor, vendor_id: int):
    cursor.execute("INSERT IGNORE INTO vendors (vendor_id) VALUES (%s)", (vendor_id,))


def get_or_create_location(cursor, lon: float, lat: float) -> int:
    cursor.execute(
        "SELECT location_id FROM locations WHERE longitude=%s AND latitude=%s",
        (lon, lat)
    )
    row = cursor.fetchone()
    if row:
        return int(row['location_id'])

    cursor.execute(
        "INSERT INTO locations (longitude, latitude) VALUES (%s, %s)",
        (lon, lat)
    )
    return cursor.lastrowid


def parse_datetime(value: str) -> datetime:
    # incoming format like '2016-01-01 00:00:17'
    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')


def load_data(csv_path: str, batch_size: int = 2000, limit: Optional[int] = None):
    if not os.path.isfile(csv_path):
        print(f"CSV not found: {csv_path}")
        sys.exit(1)

    conn = get_db_connection()
    inserted_trips = 0

    try:
        with conn.cursor() as cursor, open(csv_path, 'r', newline='') as f:
            reader = csv.DictReader(f)

            batch_params = []
            total_seen = 0

            for row in reader:
                total_seen += 1
                if limit is not None and total_seen > limit:
                    break

                trip_id = row.get('id')
                if not trip_id:
                    continue

                # vendor_id may be string in CSV; coerce to int if possible
                vendor_raw = row.get('vendor_id')
                try:
                    vendor_id = int(vendor_raw) if vendor_raw is not None and vendor_raw != '' else None
                except ValueError:
                    vendor_id = None

                pickup_time_str = row.get('pickup_datetime')
                dropoff_time_str = row.get('dropoff_datetime')
                passenger_count_raw = row.get('passenger_count')
                store_flag = (row.get('store_and_fwd_flag') or 'N')[:1]
                trip_duration_raw = row.get('trip_duration')

                pickup_lon = round_coord(row.get('pickup_longitude'))
                pickup_lat = round_coord(row.get('pickup_latitude'))
                dropoff_lon = round_coord(row.get('dropoff_longitude'))
                dropoff_lat = round_coord(row.get('dropoff_latitude'))

                # basic validations to align with schema constraints
                if vendor_id is None:
                    continue
                if not pickup_time_str or not dropoff_time_str:
                    continue
                try:
                    pickup_dt = parse_datetime(pickup_time_str)
                    dropoff_dt = parse_datetime(dropoff_time_str)
                except ValueError:
                    continue

                try:
                    passenger_count = int(passenger_count_raw) if passenger_count_raw not in (None, '') else 1
                except ValueError:
                    passenger_count = 1

                try:
                    trip_duration = int(float(trip_duration_raw)) if trip_duration_raw not in (None, '') else None
                except ValueError:
                    trip_duration = None

                if trip_duration is None or trip_duration <= 0:
                    continue
                if pickup_lon is None or pickup_lat is None or dropoff_lon is None or dropoff_lat is None:
                    continue

                # ensure vendor and locations exist; we rely on transactional batches
                ensure_vendor(cursor, vendor_id)
                pickup_loc_id = get_or_create_location(cursor, pickup_lon, pickup_lat)
                dropoff_loc_id = get_or_create_location(cursor, dropoff_lon, dropoff_lat)

                batch_params.append((
                    trip_id,
                    vendor_id,
                    pickup_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    dropoff_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    pickup_loc_id,
                    dropoff_loc_id,
                    passenger_count,
                    store_flag,
                    trip_duration
                ))

                if len(batch_params) >= batch_size:
                    cursor.executemany(
                        """
                        INSERT INTO trips (
                            trip_id, vendor_id, pickup_time, dropoff_time,
                            pickup_location_id, dropoff_location_id,
                            passenger_count, store_and_fwd_flag, trip_duration
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON DUPLICATE KEY UPDATE
                          vendor_id=VALUES(vendor_id),
                          pickup_time=VALUES(pickup_time),
                          dropoff_time=VALUES(dropoff_time),
                          pickup_location_id=VALUES(pickup_location_id),
                          dropoff_location_id=VALUES(dropoff_location_id),
                          passenger_count=VALUES(passenger_count),
                          store_and_fwd_flag=VALUES(store_and_fwd_flag),
                          trip_duration=VALUES(trip_duration)
                        """,
                        batch_params
                    )
                    conn.commit()
                    inserted_trips += len(batch_params)
                    print(f"Inserted/updated {inserted_trips} trips...")
                    batch_params = []

            if batch_params:
                cursor.executemany(
                    """
                    INSERT INTO trips (
                        trip_id, vendor_id, pickup_time, dropoff_time,
                        pickup_location_id, dropoff_location_id,
                        passenger_count, store_and_fwd_flag, trip_duration
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                      vendor_id=VALUES(vendor_id),
                      pickup_time=VALUES(pickup_time),
                      dropoff_time=VALUES(dropoff_time),
                      pickup_location_id=VALUES(pickup_location_id),
                      dropoff_location_id=VALUES(dropoff_location_id),
                      passenger_count=VALUES(passenger_count),
                      store_and_fwd_flag=VALUES(store_and_fwd_flag),
                      trip_duration=VALUES(trip_duration)
                    """,
                    batch_params
                )
                conn.commit()
                inserted_trips += len(batch_params)
                print(f"Inserted/updated {inserted_trips} trips (final batch)")

        print(f"Done. Total trips processed: {inserted_trips}")
    except Exception as e:
        conn.rollback()
        print(f"Error during load, transaction rolled back: {e}")
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Load cleaned NYC taxi data to MySQL')
    parser.add_argument('--csv', default=os.path.join(os.path.dirname(__file__), '..', 'data', 'cleaned_train_data.csv'))
    parser.add_argument('--batch-size', type=int, default=2000)
    parser.add_argument('--limit', type=int, default=None, help='For testing, only load first N rows')
    args = parser.parse_args()

    csv_path = os.path.abspath(args.csv)
    load_data(csv_path, batch_size=args.batch_size, limit=args.limit)


if __name__ == '__main__':
    main()


