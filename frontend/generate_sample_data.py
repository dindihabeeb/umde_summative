"""
Generate sample JSON data files for frontend testing
This simulates what your backend API would return
"""

import json
import random
from datetime import datetime, timedelta

def generate_summary_data():
    """Generate summary metrics (KPIs)"""
    return {
        "total_trips": 1247832,
        "avg_duration": 18.4,
        "total_distance": 8347281,
        "avg_fare": 16.82,
        "changes": {
            "trips": 12.5,
            "duration": -3.2,
            "distance": 8.7,
            "fare": 5.1
        }
    }

def generate_hourly_trips():
    """Generate hourly trip data"""
    hours = ['12AM', '1AM', '2AM', '3AM', '4AM', '5AM', 
             '6AM', '7AM', '8AM', '9AM', '10AM', '11AM',
             '12PM', '1PM', '2PM', '3PM', '4PM', '5PM', 
             '6PM', '7PM', '8PM', '9PM', '10PM', '11PM']
    
    # Realistic pattern: low at night, peak at rush hours
    base_counts = [
        3200, 2100, 1500, 1200, 1800, 3500,  # 12AM-5AM (night)
        5200, 7800, 9500, 8200, 7100, 6800,  # 6AM-11AM (morning rush)
        6500, 6200, 6800, 7100, 8200, 10200, # 12PM-5PM (afternoon)
        9800, 8900, 7800, 6500, 5200, 4100   # 6PM-11PM (evening rush)
    ]
    
    return {
        "hours": hours,
        "counts": base_counts
    }

def generate_speed_by_time():
    """Generate average speed by time of day"""
    return {
        "labels": ["Morning", "Afternoon", "Evening", "Night"],
        "speeds": [12.5, 14.2, 9.8, 18.5]
    }

def generate_passenger_distribution():
    """Generate passenger count distribution"""
    return {
        "labels": ["1 Passenger", "2 Passengers", "3 Passengers", "4+ Passengers"],
        "counts": [896988, 224247, 89699, 37498]  # Realistic percentages: 72%, 18%, 7%, 3%
    }

def generate_duration_distribution():
    """Generate trip duration distribution"""
    return {
        "ranges": ["0-10m", "10-20m", "20-30m", "30-40m", "40-50m", "50m+"],
        "counts": [287088, 424271, 311956, 124783, 56194, 43540]
    }

def generate_scatter_data(num_points=200):
    """Generate distance vs duration scatter plot data"""
    data = []
    
    for i in range(num_points):
        # Distance between 0.5 and 30 miles
        distance = random.uniform(0.5, 30)
        
        # Duration roughly proportional to distance with some variance
        # Average speed around 15 mph in city
        base_duration = (distance / 15) * 60  # Convert to minutes
        
        # Add realistic variance
        duration = base_duration * random.uniform(0.7, 1.5)
        
        # Add some traffic effect for shorter distances
        if distance < 5:
            duration *= random.uniform(1.0, 1.8)
        
        data.append({
            "x": round(distance, 2),
            "y": round(duration, 2)
        })
    
    return {"data": data}

def generate_insights():
    """Generate key insights"""
    return {
        "insights": [
            {
                "title": "🕐 Peak Rush Hour Pattern",
                "description": "Trip volume peaks at 8-9 AM and 5-7 PM on weekdays, with 45% higher demand during evening rush hours. Average trip duration increases by 28% during these periods due to traffic congestion."
            },
            {
                "title": "💰 Fare Efficiency Analysis",
                "description": "Trips under 5 miles show the highest fare-per-mile ratio ($4.20/mi), while longer trips (15+ miles) average $2.10/mi. Night trips (12AM-6AM) command 15% higher fares on average."
            },
            {
                "title": "🚦 Speed Anomaly Detection",
                "description": "Average speed drops to 8.2 mph during weekday rush hours in Manhattan, compared to 18.5 mph during off-peak hours. Weekend speeds are 32% faster on average, indicating reduced congestion."
            },
            {
                "title": "👥 Solo Travelers Dominate",
                "description": "72% of all trips have only 1 passenger, suggesting most taxi usage is for individual commuting rather than group travel. This pattern is consistent across all time periods."
            }
        ]
    }

def save_all_sample_data():
    """Generate and save all sample data files"""
    
    # Create data directory if it doesn't exist
    import os
    if not os.path.exists('data'):
        os.makedirs('data')
    
    data_files = {
        'data/summary.json': generate_summary_data(),
        'data/trips_hourly.json': generate_hourly_trips(),
        'data/speed_by_time.json': generate_speed_by_time(),
        'data/passenger_distribution.json': generate_passenger_distribution(),
        'data/duration_distribution.json': generate_duration_distribution(),
        'data/scatter_data.json': generate_scatter_data(),
        'data/insights.json': generate_insights()
    }
    
    print("Generating sample data files...")
    for filename, data in data_files.items():
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Created {filename}")
    
    print("\n✅ All sample data files generated successfully!")
    print("\nThese files simulate what your backend API would return.")
    print("You can use them to test your frontend locally.\n")
    print("Generated files:")
    print("  - data/summary.json")
    print("  - data/trips_hourly.json")
    print("  - data/speed_by_time.json")
    print("  - data/passenger_distribution.json")
    print("  - data/duration_distribution.json")
    print("  - data/scatter_data.json")
    print("  - data/insights.json")
    print("\nTo view the dashboard:")
    print("  1. Run: python -m http.server 8000")
    print("  2. Open: http://localhost:8000/dashboard_standalone.html")

if __name__ == "__main__":
    save_all_sample_data()
