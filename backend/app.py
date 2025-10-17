"""
NYC Taxi Trip Analysis - Backend API Server 
Flask based API, includes endpoints for trip data retrieval, statistical analysis, and location insights.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
# replaced psycopg2 with pymysql for MySQL
import pymysql
from pymysql.cursors import DictCursor
import os
from dotenv import load_dotenv
from datetime import datetime
import logging

# Load environment variables from .env file
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Enable Cross-Origin Resource Sharing (CORS) to allow frontend requests
CORS(app)

# Configure logging for debugging and monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# DATABASE CONFIGURATION

# Database connection parameters loaded from environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'nyc_taxi'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', '3306'))  # MySQL default port
}


def get_db_connection():
    """
    Establishes and returns a connection to the MySQL database using PyMySQL.
    """
    try:
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port'],
            cursorclass=DictCursor,
            autocommit=False,
            charset='utf8mb4'
        )
        logger.info("Database connection (MySQL) established successfully")
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise


def serialize_datetime(obj):
    """
    Custom JSON serializer for datetime objects.
    Converts Python datetime objects to ISO 8601 format strings.
    
    Args:
        obj: Object to serialize
        
    Returns:
        str: ISO formatted datetime string
        
    Raises:
        TypeError: If object type is not serializable
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


# UTILITY ENDPOINTS

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify API and database connectivity.
    Used for monitoring and ensuring the service is operational.
    
    Returns:
        JSON response with status, database connectivity, and timestamp
        
    Status Codes:
        200: Service is healthy
        500: Service is unhealthy (database connection failed)
    """
    try:
        # Attempt to connect to database to verify it's accessible
        conn = get_db_connection()
        conn.close()
        
        logger.info("Health check passed")
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


# ============= TRIP DATA ENDPOINTS =============

@app.route('/api/trips', methods=['GET'])
def get_trips():
    """
    Retrieves trip data (from view trip_details) with optional filtering and pagination.
    
    Query Parameters:
        page (int): Page number for pagination (default: 1)
        limit (int): Number of records per page (default: 100, max: 1000)
        vendor_id (int): Filter by vendor ID
        min_duration (int): Minimum trip duration in seconds
        max_duration (int): Maximum trip duration in seconds
        start_date (str): Start date filter (ISO format)
        end_date (str): End date filter (ISO format)
        
    Returns:
        JSON object containing:
            - trips: Array of trip records
            - pagination: Metadata (page, limit, total, pages)
            - filters_applied: Dictionary of active filters
            
    Status Codes:
        200: Success
        400: Invalid parameters
        500: Server error
    """
    try:
        page = max(1, int(request.args.get('page', 1)))
        limit = min(1000, max(1, int(request.args.get('limit', 100))))
        offset = (page - 1) * limit

        vendor_id = request.args.get('vendor_id', type=int)
        min_duration = request.args.get('min_duration', type=int)
        max_duration = request.args.get('max_duration', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        passenger_count = request.args.get('passenger_count', type=int)

        base_select = """
            SELECT 
                trip_id,
                vendor_id,
                pickup_datetime,
                dropoff_datetime,
                pickup_longitude,
                pickup_latitude,
                dropoff_longitude,
                dropoff_latitude,
                passenger_count,
                store_and_fwd_flag,
                trip_duration
            FROM trip_details
            WHERE 1=1
        """

        where_clauses = []
        params = []
        filters_applied = {}

        if vendor_id is not None:
            where_clauses.append("vendor_id = %s")
            params.append(vendor_id)
            filters_applied['vendor_id'] = vendor_id

        if min_duration is not None:
            where_clauses.append("trip_duration >= %s")
            params.append(min_duration)
            filters_applied['min_duration'] = min_duration

        if max_duration is not None:
            where_clauses.append("trip_duration <= %s")
            params.append(max_duration)
            filters_applied['max_duration'] = max_duration

        if start_date:
            where_clauses.append("pickup_datetime >= %s")
            params.append(start_date)
            filters_applied['start_date'] = start_date

        if end_date:
            where_clauses.append("pickup_datetime <= %s")
            params.append(end_date)
            filters_applied['end_date'] = end_date

        if passenger_count is not None:
            where_clauses.append("passenger_count = %s")
            params.append(passenger_count)
            filters_applied['passenger_count'] = passenger_count

        where_clause_sql = (" AND " + " AND ".join(where_clauses)) if where_clauses else ""

        query = base_select + where_clause_sql + " ORDER BY pickup_datetime DESC LIMIT %s OFFSET %s"
        query_params = params + [limit, offset]

        count_query = "SELECT COUNT(*) as total FROM trip_details WHERE 1=1" + where_clause_sql

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, query_params)
        trips = cursor.fetchall()

        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['total']

        cursor.close()
        conn.close()

        logger.info(f"Retrieved {len(trips)} trips (page {page}, total {total_count})")

        return jsonify({
            'success': True,
            'trips': trips,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            },
            'filters_applied': filters_applied
        }), 200

    except ValueError as e:
        logger.error(f"Invalid parameter: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Invalid parameter value',
            'message': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error retrieving trips: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve trips',
            'message': str(e)
        }), 500


@app.route('/api/trips/<trip_id>', methods=['GET'])
def get_trip_by_id(trip_id):
    """
    Retrieves detailed information for a specific trip.
    
    Args:
        trip_id (str): Unique trip identifier
        
    Returns:
        JSON object with complete trip details
        
    Status Codes:
        200: Trip found
        404: Trip not found
        500: Server error
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT * FROM trip_details
            WHERE trip_id = %s
        """

        cursor.execute(query, (trip_id,))
        trip = cursor.fetchone()

        cursor.close()
        conn.close()
        
        if trip:
            logger.info(f"Retrieved trip {trip_id}")
            return jsonify({
                'success': True,
                'trip': trip
            }), 200
        else:
            logger.warning(f"Trip {trip_id} not found")
            return jsonify({
                'success': False,
                'error': 'Trip not found',
                'trip_id': trip_id
            }), 404
    
    except Exception as e:
        logger.error(f"Error retrieving trip {trip_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve trip',
            'message': str(e)
        }), 500


#STATISTICAL ANALYSIS ENDPOINTS

@app.route('/api/statistics/overview', methods=['GET'])
def get_overview_statistics():
    """
    Retrieves overall aggregate statistics across all trips.
    Provides high-level metrics for dashboard summary views.
    
    Returns:
        JSON object containing:
            - total_trips: Total number of trips
            - avg_distance: Average trip distance (miles)
            - avg_duration: Average trip duration (seconds)
            - avg_speed: Average trip speed (km/h)
            - total_passengers: Total passengers transported
            - earliest_trip: Timestamp of first trip
            - latest_trip: Timestamp of most recent trip
            
    Status Codes:
        200: Success
        500: Server error
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Optional filters: start_date, end_date, passenger_count
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        passenger_count = request.args.get('passenger_count', type=int)

        base = (
            "SELECT COUNT(*) as total_trips, "
            "ROUND(AVG(t.trip_duration), 0) as avg_duration, "
            "SUM(t.passenger_count) as total_passengers, "
            "MIN(t.pickup_time) as earliest_trip, "
            "MAX(t.pickup_time) as latest_trip "
            "FROM trips t WHERE 1=1"
        )

        where_clauses = []
        params = []
        if start_date:
            where_clauses.append(" AND t.pickup_time >= %s")
            params.append(start_date)
        if end_date:
            where_clauses.append(" AND t.pickup_time <= %s")
            params.append(end_date)
        if passenger_count is not None:
            where_clauses.append(" AND t.passenger_count = %s")
            params.append(passenger_count)

        query = base + "".join(where_clauses)

        cursor.execute(query, params)
        stats = cursor.fetchone()

        cursor.close()
        conn.close()

        logger.info("Retrieved overview statistics")

        return jsonify({
            'success': True,
            'statistics': stats
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving overview statistics: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve statistics',
            'message': str(e)
        }), 500


@app.route('/api/statistics/by-hour', methods=['GET'])
def get_hourly_statistics():
    """
    Retrieves trip statistics grouped by hour of day (0-23).
    Useful for identifying peak hours and demand patterns.
    
    Returns:
        JSON array of objects, each containing:
            - hour: Hour of day (0-23)
            - trip_count: Number of trips
            - avg_distance: Average distance
            - avg_duration: Average duration
            - avg_speed: Average speed
            
    Status Codes:
        200: Success
        500: Server error
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Optional filters: start_date, end_date, passenger_count
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        passenger_count = request.args.get('passenger_count', type=int)

        base = (
            "SELECT HOUR(t.pickup_time) as hour, "
            "COUNT(*) as trip_count, "
            "ROUND(AVG(t.trip_duration), 0) as avg_duration, "
            "ROUND(AVG(t.passenger_count), 1) as avg_passengers "
            "FROM trips t WHERE 1=1"
        )
        where_clauses = []
        params = []
        if start_date:
            where_clauses.append(" AND t.pickup_time >= %s")
            params.append(start_date)
        if end_date:
            where_clauses.append(" AND t.pickup_time <= %s")
            params.append(end_date)
        if passenger_count is not None:
            where_clauses.append(" AND t.passenger_count = %s")
            params.append(passenger_count)

        group_order = " GROUP BY HOUR(t.pickup_time) ORDER BY hour"
        query = base + "".join(where_clauses) + group_order

        cursor.execute(query, params)
        stats = cursor.fetchall()

        cursor.close()
        conn.close()

        logger.info("Retrieved hourly statistics")

        return jsonify({
            'success': True,
            'statistics': stats
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving hourly statistics: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve hourly statistics',
            'message': str(e)
        }), 500


@app.route('/api/statistics/by-day-of-week', methods=['GET'])
def get_daily_statistics():
    """
    Retrieves trip statistics grouped by day of week.
    Helps identify weekday vs weekend patterns.
    
    Returns:
        JSON array with statistics for each day (Monday=0 to Sunday=6)
        
    Status Codes:
        200: Success
        500: Server error
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                DAYOFWEEK(t.pickup_time) as day_of_week,
                CASE DAYOFWEEK(t.pickup_time)
                    WHEN 1 THEN 'Sunday'
                    WHEN 2 THEN 'Monday'
                    WHEN 3 THEN 'Tuesday'
                    WHEN 4 THEN 'Wednesday'
                    WHEN 5 THEN 'Thursday'
                    WHEN 6 THEN 'Friday'
                    WHEN 7 THEN 'Saturday'
                END as day_name,
                COUNT(*) as trip_count,
                ROUND(AVG(t.trip_duration), 0) as avg_duration,
                ROUND(AVG(t.passenger_count), 2) as avg_passengers
            FROM trips t
            GROUP BY DAYOFWEEK(t.pickup_time)
            ORDER BY day_of_week
        """

        cursor.execute(query)
        stats = cursor.fetchall()

        cursor.close()
        conn.close()

        logger.info("Retrieved daily statistics")

        return jsonify({
            'success': True,
            'statistics': stats
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving daily statistics: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve daily statistics',
            'message': str(e)
        }), 500


@app.route('/api/statistics/rush-hour-analysis', methods=['GET'])
def get_rush_hour_analysis():
    """
    Compares rush hour vs non-rush hour trip characteristics.
    Rush hours defined as: 7-9 AM and 5-7 PM on weekdays.
    
    Returns:
        JSON object with separate statistics for rush hour and non-rush hour periods
        
    Status Codes:
        200: Success
        500: Server error
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                CASE WHEN HOUR(t.pickup_time) IN (7,8,17,18) THEN 1 ELSE 0 END as is_rush_hour,
                COUNT(*) as trip_count,
                ROUND(AVG(t.trip_duration), 0) as avg_duration,
                ROUND(AVG(t.passenger_count), 2) as avg_passengers
            FROM trips t
            GROUP BY is_rush_hour
            ORDER BY is_rush_hour
        """

        cursor.execute(query)
        stats = cursor.fetchall()

        cursor.close()
        conn.close()

        logger.info("Retrieved rush hour analysis")

        return jsonify({
            'success': True,
            'statistics': stats
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving rush hour analysis: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve rush hour analysis',
            'message': str(e)
        }), 500


@app.route('/api/statistics/weekend-analysis', methods=['GET'])
def get_weekend_analysis():
    """
    Compares weekend vs weekday trip patterns.
    
    Returns:
        JSON object with statistics for weekends and weekdays
        
    Status Codes:
        200: Success
        500: Server error
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                CASE WHEN DAYOFWEEK(t.pickup_time) IN (1,7) THEN 1 ELSE 0 END as is_weekend,
                CASE WHEN DAYOFWEEK(t.pickup_time) IN (1,7) THEN 'Weekend' ELSE 'Weekday' END as period,
                COUNT(*) as trip_count,
                ROUND(AVG(t.trip_duration), 0) as avg_duration,
                ROUND(AVG(t.passenger_count), 2) as avg_passengers
            FROM trips t
            GROUP BY is_weekend
            ORDER BY is_weekend
        """

        cursor.execute(query)
        stats = cursor.fetchall()

        cursor.close()
        conn.close()

        logger.info("Retrieved weekend analysis")

        return jsonify({
            'success': True,
            'statistics': stats
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving weekend analysis: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve weekend analysis',
            'message': str(e)
        }), 500


# LOCATION ANALYSIS ENDPOINTS

@app.route('/api/locations/popular-pickups', methods=['GET'])
def get_popular_pickups():
    """
    Identifies the most frequently used pickup locations.
    Useful for understanding demand hotspots.
    
    Query Parameters:
        limit (int): Number of locations to return (default: 20, max: 100)
        
    Returns:
        JSON array of pickup locations with coordinates and trip counts
        
    Status Codes:
        200: Success
        500: Server error
    """
    try:
        limit = min(100, max(1, int(request.args.get('limit', 20))))

        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                pl.longitude as pickup_longitude,
                pl.latitude as pickup_latitude,
                COUNT(*) as pickup_count,
                ROUND(AVG(t.trip_duration), 0) as avg_duration,
                ROUND(AVG(t.passenger_count), 1) as avg_passengers
            FROM trips t
            JOIN locations pl ON t.pickup_location_id = pl.location_id
            GROUP BY pl.longitude, pl.latitude
            ORDER BY pickup_count DESC
            LIMIT %s
        """

        cursor.execute(query, (limit,))
        locations = cursor.fetchall()

        cursor.close()
        conn.close()

        logger.info(f"Retrieved {len(locations)} popular pickup locations")

        return jsonify({
            'success': True,
            'locations': locations,
            'count': len(locations)
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving popular pickups: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve popular pickups',
            'message': str(e)
        }), 500


@app.route('/api/locations/popular-dropoffs', methods=['GET'])
def get_popular_dropoffs():
    """
    Identifies the most frequently used dropoff locations.
    Helps understand destination patterns and popular areas.
    
    Query Parameters:
        limit (int): Number of locations to return (default: 20, max: 100)
        
    Returns:
        JSON array of dropoff locations with coordinates and trip counts
        
    Status Codes:
        200: Success
        500: Server error
    """
    try:
        limit = min(100, max(1, int(request.args.get('limit', 20))))

        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                dl.longitude as dropoff_longitude,
                dl.latitude as dropoff_latitude,
                COUNT(*) as dropoff_count,
                ROUND(AVG(t.trip_duration), 0) as avg_duration,
                ROUND(AVG(t.passenger_count), 1) as avg_passengers
            FROM trips t
            JOIN locations dl ON t.dropoff_location_id = dl.location_id
            GROUP BY dl.longitude, dl.latitude
            ORDER BY dropoff_count DESC
            LIMIT %s
        """

        cursor.execute(query, (limit,))
        locations = cursor.fetchall()

        cursor.close()
        conn.close()

        logger.info(f"Retrieved {len(locations)} popular dropoff locations")

        return jsonify({
            'success': True,
            'locations': locations,
            'count': len(locations)
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving popular dropoffs: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve popular dropoffs',
            'message': str(e)
        }), 500


@app.route('/api/locations/routes', methods=['GET'])
def get_popular_routes():
    """
    Identifies the most common pickup-dropoff route pairs.
    
    Query Parameters:
        limit (int): Number of routes to return (default: 20, max: 50)
        
    Returns:
        JSON array of route pairs with trip counts
        
    Status Codes:
        200: Success
        500: Server error
    """
    try:
        limit = min(50, max(1, int(request.args.get('limit', 20))))

        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                pl.longitude as pickup_longitude,
                pl.latitude as pickup_latitude,
                dl.longitude as dropoff_longitude,
                dl.latitude as dropoff_latitude,
                COUNT(*) as route_count,
                ROUND(AVG(t.trip_duration), 0) as avg_duration,
                ROUND(AVG(t.passenger_count), 1) as avg_passengers
            FROM trips t
            JOIN locations pl ON t.pickup_location_id = pl.location_id
            JOIN locations dl ON t.dropoff_location_id = dl.location_id
            GROUP BY pl.longitude, pl.latitude, dl.longitude, dl.latitude
            ORDER BY route_count DESC
            LIMIT %s
        """

        cursor.execute(query, (limit,))
        routes = cursor.fetchall()

        cursor.close()
        conn.close()

        logger.info(f"Retrieved {len(routes)} popular routes")

        return jsonify({
            'success': True,
            'routes': routes,
            'count': len(routes)
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving popular routes: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve popular routes',
            'message': str(e)
        }), 500


# VENDOR ANALYSIS ENDPOINTS

@app.route('/api/vendors/comparison', methods=['GET'])
def get_vendor_comparison():
    """
    Compares performance metrics between different taxi vendors.
    
    Returns:
        JSON array with statistics for each vendor
        
    Status Codes:
        200: Success
        500: Server error
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                v.vendor_id,
                COUNT(*) as trip_count,
                ROUND(AVG(t.trip_duration), 0) as avg_duration,
                ROUND(AVG(t.passenger_count), 2) as avg_passengers
            FROM trips t
            JOIN vendors v ON t.vendor_id = v.vendor_id
            GROUP BY v.vendor_id
            ORDER BY trip_count DESC
        """

        cursor.execute(query)
        vendors = cursor.fetchall()

        cursor.close()
        conn.close()

        logger.info("Retrieved vendor comparison")

        return jsonify({
            'success': True,
            'vendors': vendors
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving vendor comparison: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve vendor comparison',
            'message': str(e)
        }), 500


# ERROR HANDLERS 

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors - endpoint not found"""
    logger.warning(f"404 error: {request.url}")
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'message': f'The requested URL {request.path} was not found on this server'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors - internal server error"""
    logger.error(f"500 error: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred. Please try again later.'
    }), 500


@app.errorhandler(400)
def bad_request(error):
    """Handle 400 errors - bad request"""
    logger.warning(f"400 error: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'message': 'The request could not be understood or was missing required parameters'
    }), 400


# MAIN APPLICATION ENTRY POINT 

if __name__ == '__main__':
    """
    Start the Flask development server.
    
    Configuration:
        - Debug mode: Enabled (disable in production)
        - Host: 0.0.0.0 (accessible from all network interfaces)
        - Port: 5000 (default Flask port)
        
    Note: For production deployment, use a WSGI server like Gunicorn or uWSGI
    Example: gunicorn -w 4 -b 0.0.0.0:5000 app:app
    """
    print("=" * 50)
    print("NYC Taxi Trip Analysis - Backend API Server")
    print("=" * 50)
    print(f"Server starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Base URL: http://localhost:5000")
    print(f"Database: {DB_CONFIG['database']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print("=" * 50)
    print("\nAvailable Endpoints:")
    print("  - GET  /api/health - Health check")
    print("  - GET  /api/trips - Get trips with filters")
    print("  - GET  /api/trips/<id> - Get specific trip")
    print("  - GET  /api/statistics/overview - Overall stats")
    print("  - GET  /api/statistics/by-hour - Hourly distribution")
    print("  - GET  /api/statistics/by-day-of-week - Daily distribution")
    print("  - GET  /api/statistics/rush-hour-analysis - Rush hour comparison")
    print("  - GET  /api/statistics/weekend-analysis - Weekend vs weekday")
    print("  - GET  /api/locations/popular-pickups - Top pickup locations")
    print("  - GET  /api/locations/popular-dropoffs - Top dropoff locations")
    print("  - GET  /api/locations/routes - Popular routes")
    print("  - GET  /api/vendors/comparison - Vendor comparison")
    print("=" * 50)
    print("\nServer is ready to accept requests...")
    print("Press CTRL+C to stop the server\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)