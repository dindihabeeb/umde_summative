import pandas as pd
import numpy as np
from datetime import datetime
import json
import os

class NYCTaxiDataCleaner:
    def __init__(self, input_file):
        self.input_file = input_file
        self.df = None
        self.excluded_records = []
        self.cleaning_stats = {}
        
    def load_data(self):
        """Load the raw CSV data"""
        print("Loading data...")
        self.df = pd.read_csv(self.input_file)
        self.cleaning_stats['original_count'] = len(self.df)
        print(f"Loaded {len(self.df)} records")
        return self
    
    def handle_missing_values(self):
        """Identify and handle missing values"""
        print("\nHandling missing values...")
        initial_count = len(self.df)
        
        critical_fields = ['pickup_datetime', 'dropoff_datetime', 
                          'pickup_longitude', 'pickup_latitude',
                          'dropoff_longitude', 'dropoff_latitude']
        
        missing_mask = self.df[critical_fields].isnull().any(axis=1)
        self.excluded_records.extend(
            self.df[missing_mask].to_dict('records')
        )
        
        self.df = self.df.dropna(subset=critical_fields)
        
        if 'passenger_count' in self.df.columns:
            self.df['passenger_count'].fillna(1, inplace=True)
        
        self.cleaning_stats['missing_values_removed'] = initial_count - len(self.df)
        print(f"Removed {initial_count - len(self.df)} records with missing values")
        return self
    
    def remove_duplicates(self):
        """Remove duplicate records"""
        print("\nRemoving duplicates...")
        initial_count = len(self.df)
        
        duplicate_cols = ['pickup_datetime', 'dropoff_datetime', 
                         'pickup_longitude', 'pickup_latitude']
        
        duplicates = self.df[self.df.duplicated(subset=duplicate_cols, keep='first')]
        self.excluded_records.extend(duplicates.to_dict('records'))
        
        self.df = self.df.drop_duplicates(subset=duplicate_cols, keep='first')
        
        self.cleaning_stats['duplicates_removed'] = initial_count - len(self.df)
        print(f"Removed {initial_count - len(self.df)} duplicate records")
        return self
    
    def handle_outliers_and_invalid_records(self):
        """Remove outliers and invalid records"""
        print("\nHandling outliers and invalid records...")
        initial_count = len(self.df)
        
        self.df['pickup_datetime'] = pd.to_datetime(self.df['pickup_datetime'])
        self.df['dropoff_datetime'] = pd.to_datetime(self.df['dropoff_datetime'])
        
        self.df['trip_duration_seconds'] = (
            self.df['dropoff_datetime'] - self.df['pickup_datetime']
        ).dt.total_seconds()
        
        invalid_conditions = (
            (self.df['trip_duration_seconds'] <= 0) |
            (self.df['trip_duration_seconds'] > 86400) |
            (self.df['pickup_latitude'] < 40.5) | (self.df['pickup_latitude'] > 41.0) |
            (self.df['pickup_longitude'] < -74.3) | (self.df['pickup_longitude'] > -73.7) |
            (self.df['dropoff_latitude'] < 40.5) | (self.df['dropoff_latitude'] > 41.0) |
            (self.df['dropoff_longitude'] < -74.3) | (self.df['dropoff_longitude'] > -73.7) |
            (self.df['pickup_latitude'] == 0) | (self.df['pickup_longitude'] == 0) |
            (self.df['dropoff_latitude'] == 0) | (self.df['dropoff_longitude'] == 0)
        )
        
        if 'trip_distance' in self.df.columns:
            invalid_conditions |= (
                (self.df['trip_distance'] <= 0) |
                (self.df['trip_distance'] > 100)
            )
        
        if 'fare_amount' in self.df.columns:
            invalid_conditions |= (
                (self.df['fare_amount'] < 0) |
                (self.df['fare_amount'] > 500)
            )
        
        if 'passenger_count' in self.df.columns:
            invalid_conditions |= (
                (self.df['passenger_count'] <= 0) |
                (self.df['passenger_count'] > 7)
            )
        
        excluded = self.df[invalid_conditions]
        self.excluded_records.extend(excluded.to_dict('records'))
        
        self.df = self.df[~invalid_conditions]
        
        self.cleaning_stats['outliers_removed'] = initial_count - len(self.df)
        print(f"Removed {initial_count - len(self.df)} outlier/invalid records")
        return self
    
    def create_derived_features(self):
        """Create derived features for analysis"""
        print("\nCreating derived features...")
        
        if 'trip_distance' in self.df.columns:
            self.df['trip_distance_km'] = self.df['trip_distance'] * 1.60934
            trip_duration_hours = self.df['trip_duration_seconds'] / 3600
            self.df['trip_speed_kmh'] = self.df['trip_distance_km'] / trip_duration_hours
            
            self.df.loc[self.df['trip_speed_kmh'] > 120, 'trip_speed_kmh'] = None
            self.df.loc[self.df['trip_speed_kmh'] < 0, 'trip_speed_kmh'] = None
        
        if 'fare_amount' in self.df.columns and 'trip_distance_km' in self.df.columns:
            self.df['fare_per_km'] = self.df['fare_amount'] / self.df['trip_distance_km']
            self.df.loc[self.df['trip_distance_km'] == 0, 'fare_per_km'] = None
        
        self.df['hour_of_day'] = self.df['pickup_datetime'].dt.hour
        self.df['day_of_week'] = self.df['pickup_datetime'].dt.dayofweek
        
        def get_time_period(hour):
            if 6 <= hour < 12:
                return 'morning'
            elif 12 <= hour < 18:
                return 'afternoon'
            elif 18 <= hour < 22:
                return 'evening'
            else:
                return 'night'
        
        self.df['time_period'] = self.df['hour_of_day'].apply(get_time_period)
        
        if 'trip_distance' in self.df.columns:
            def categorize_distance(dist):
                if dist < 1:
                    return 'very_short'
                elif dist < 3:
                    return 'short'
                elif dist < 10:
                    return 'medium'
                else:
                    return 'long'
            
            self.df['distance_category'] = self.df['trip_distance'].apply(categorize_distance)
        
        if 'tip_amount' in self.df.columns and 'fare_amount' in self.df.columns:
            self.df['tip_percentage'] = (
                (self.df['tip_amount'] / self.df['fare_amount']) * 100
            ).round(2)
            self.df.loc[self.df['fare_amount'] == 0, 'tip_percentage'] = 0
        
        print("Created derived features: trip_speed_kmh, fare_per_km, time_period")
        return self
    
    def normalize_and_format(self):
        """Normalize and format all fields"""
        print("\nNormalizing and formatting data...")
        
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col not in ['passenger_count']:
                self.df[col] = self.df[col].round(4)
        
        if 'passenger_count' in self.df.columns:
            self.df['passenger_count'] = self.df['passenger_count'].astype(int)
        
        self.df = self.df.sort_values('pickup_datetime').reset_index(drop=True)
        
        self.cleaning_stats['final_count'] = len(self.df)
        print(f"Final cleaned dataset: {len(self.df)} records")
        return self
    
    def save_cleaned_data(self, output_file='cleaned_train_data.csv'):
        """Save cleaned data to CSV"""
        print(f"\nSaving cleaned data to {output_file}...")
        self.df.to_csv(output_file, index=False)
        print(f"Saved {len(self.df)} records")
        return self
    
    def save_excluded_records(self, output_file='excluded_records.json'):
        """Save excluded records for transparency"""
        print(f"\nSaving excluded records to {output_file}...")
        with open(output_file, 'w') as f:
            json.dump({
                'count': len(self.excluded_records),
                'records': self.excluded_records[:1000]
            }, f, default=str, indent=2)
        print(f"Logged {len(self.excluded_records)} excluded records")
        return self
    
    def generate_cleaning_report(self, output_file='cleaning_report.json'):
        """Generate a summary report of the cleaning process"""
        print("\nGenerating cleaning report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'statistics': self.cleaning_stats,
            'retention_rate': f"{(self.cleaning_stats['final_count'] / self.cleaning_stats['original_count'] * 100):.2f}%",
            'columns': list(self.df.columns),
            'data_types': self.df.dtypes.astype(str).to_dict()
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print("Cleaning Summary:")
        print(f"  Original records: {report['statistics']['original_count']}")
        print(f"  Final records: {report['statistics']['final_count']}")
        print(f"  Retention rate: {report['retention_rate']}")
        return self

    def process_all(self, output_csv='cleaned_train_data.csv'):
        """Run complete cleaning pipeline"""
        return (self
                .load_data()
                .handle_missing_values()
                .remove_duplicates()
                .handle_outliers_and_invalid_records()
                .create_derived_features()
                .normalize_and_format()
                .save_cleaned_data(output_csv)
                .save_excluded_records()
                .generate_cleaning_report())

if __name__ == "__main__":
    cleaner = NYCTaxiDataCleaner('train.csv')
    cleaner.process_all('cleaned_train_data.csv')