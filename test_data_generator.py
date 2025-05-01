import requests
import random
from datetime import datetime, timedelta
import json
import time

# Base URL for your API
BASE_URL = "http://localhost:5000"  # Change this to your actual server URL

# Authentication credentials
AUTH_EMAIL = "admin@example.com"  # Change this to your admin email
AUTH_PASSWORD = "admin123"  # Change this to your admin password

# Session to maintain cookies
session = requests.Session()

# Sample data for locations
locations = [
    {
        "name": "Main Parking",
        "address": "123 Main Street",
        "city": "Mumbai",
        "state": "Maharashtra",
        "country": "India",
        "postal_code": "400001",
        "total_spaces": 100,
        "available_spaces": 100,
        "status": "active"
    },
    {
        "name": "Shopping Mall Parking",
        "address": "456 Market Road",
        "city": "Mumbai",
        "state": "Maharashtra",
        "country": "India",
        "postal_code": "400002",
        "total_spaces": 200,
        "available_spaces": 200,
        "status": "active"
    }
]

# Sample data for sites
sites = [
    {
        "name": "Ground Floor",
        "total_spaces": 50,
        "available_spaces": 50,
        "status": "active",
        "description": "Ground floor parking area",
        "location_id": 1  # This will be updated after location is created
    },
    {
        "name": "First Floor",
        "total_spaces": 50,
        "available_spaces": 50,
        "status": "active",
        "description": "First floor parking area",
        "location_id": 1  # This will be updated after location is created
    }
]

# Sample data for devices
devices = [
    {
        "site_id": 1,  # This will be updated after site is created
        "device_type": "entry_paid",
        "upi_id": "parking@upi",
        "status": "active",
        "printer_header": "Main Parking",
        "printer_footer": "Thank you for parking with us",
        "vehicle_in_start_time": "00:00",
        "vehicle_in_end_time": "23:59"
    },
    {
        "site_id": 1,  # This will be updated after site is created
        "device_type": "exit_paid",
        "upi_id": "parking@upi",
        "status": "active",
        "printer_header": "Main Parking",
        "printer_footer": "Thank you for parking with us",
        "vehicle_in_start_time": "00:00",
        "vehicle_in_end_time": "23:59"
    }
]

# Sample data for vehicle categories
vehicle_categories = [
    {
        "name": "Two Wheeler",
        "description": "Motorcycles and scooters",
        "is_monthly_pass": False,
        "amount": 20.0,
        "location_id": 1,  # This will be updated after location is created
        "site_id": 1,  # This will be updated after site is created
        "device_id": 1,  # This will be updated after device is created
        "status": "active"
    },
    {
        "name": "Car",
        "description": "Sedan and hatchback",
        "is_monthly_pass": False,
        "amount": 50.0,
        "location_id": 1,  # This will be updated after location is created
        "site_id": 1,  # This will be updated after site is created
        "device_id": 1,  # This will be updated after device is created
        "status": "active"
    },
    {
        "name": "SUV",
        "description": "Sports Utility Vehicle",
        "is_monthly_pass": False,
        "amount": 70.0,
        "location_id": 1,  # This will be updated after location is created
        "site_id": 1,  # This will be updated after site is created
        "device_id": 1,  # This will be updated after device is created
        "status": "active"
    }
]

# Sample data for tariffs
tariffs = [
    {
        "name": "Standard Rate",
        "status": "active",
        "grace_time": 15,
        "location_id": 1,  # This will be updated after location is created
        "site_id": 1,  # This will be updated after site is created
        "device_id": 1,  # This will be updated after device is created
        "vehicle_category_id": 1,  # This will be updated after vehicle category is created
        "intervals": [
            {"from_time": 0, "to_time": 60, "amount": 20.0},
            {"from_time": 60, "to_time": 120, "amount": 40.0},
            {"from_time": 120, "to_time": 180, "amount": 60.0}
        ]
    },
    {
        "name": "Premium Rate",
        "status": "active",
        "grace_time": 15,
        "location_id": 1,  # This will be updated after location is created
        "site_id": 1,  # This will be updated after site is created
        "device_id": 1,  # This will be updated after device is created
        "vehicle_category_id": 1,  # This will be updated after vehicle category is created
        "intervals": [
            {"from_time": 0, "to_time": 60, "amount": 30.0},
            {"from_time": 60, "to_time": 120, "amount": 60.0},
            {"from_time": 120, "to_time": 180, "amount": 90.0}
        ]
    }
]

def check_session():
    """Check if the session is still valid"""
    try:
        response = session.get(f"{BASE_URL}/dashboard")
        return response.status_code == 200
    except Exception as e:
        print(f"Error checking session: {str(e)}")
        return False

def login():
    """Login to get session cookie"""
    try:
        login_data = {
            "email": AUTH_EMAIL,
            "password": AUTH_PASSWORD
        }
        response = session.post(f"{BASE_URL}/login", data=login_data)
        if response.status_code == 200:
            print("Successfully logged in")
            return True
        else:
            print(f"Login failed. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error during login: {str(e)}")
        return False

def generate_vehicle_number():
    """Generate a random vehicle number"""
    states = ["MH", "KA", "TN", "DL", "GJ"]
    numbers = "".join([str(random.randint(0, 9)) for _ in range(2)])
    letters = "".join([chr(random.randint(65, 90)) for _ in range(2)])
    final_numbers = "".join([str(random.randint(0, 9)) for _ in range(4)])
    return f"{random.choice(states)}{numbers}{letters}{final_numbers}"

def generate_transaction_data(num_entries=50, num_exits=40, num_overnight=10):
    """Generate sample transaction data"""
    entries = []
    exits = []
    overnight_vehicles = []
    
    # Generate entry data
    for _ in range(num_entries):
        entry_time = datetime.now() - timedelta(hours=random.randint(1, 24))
        vehicle_number = generate_vehicle_number()
        entries.append({
            "vehicleNumber": vehicle_number,
            "vehicleType": random.choice(["Two Wheeler", "Car", "SUV"]),
            "transactionId": f"TXN{random.randint(100000, 999999)}",
            "entryTime": entry_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "deviceId": random.choice(["001", "002"]),
            "location": random.choice(["Main Parking", "Shopping Mall Parking"]),
            "site": random.choice(["Ground Floor", "First Floor"]),
            "status": "active",
            "isSynced": True
        })
    
    # Generate exit data
    for entry in random.sample(entries, num_exits):
        exit_time = datetime.strptime(entry["entryTime"], "%Y-%m-%dT%H:%M:%S") + timedelta(hours=random.randint(1, 5))
        exits.append({
            "transactionId": entry["transactionId"],
            "exitTime": exit_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "amountPaid": random.randint(20, 100),
            "status": "completed",
            "paymentMethod": random.choice(["cash", "upi", "card"]),
            "paymentReference": f"REF{random.randint(100000, 999999)}",
            "deviceId": random.choice(["001", "002"]),
            "location": entry["location"],
            "site": entry["site"]
        })
    
    # Generate overnight vehicle data
    for entry in random.sample(entries, num_overnight):
        if entry["transactionId"] not in [exit["transactionId"] for exit in exits]:
            overnight_vehicles.append({
                "vehicleNumber": entry["vehicleNumber"],
                "vehicleType": entry["vehicleType"],
                "entryTime": entry["entryTime"],
                "location": entry["location"],
                "site": entry["site"]
            })
    
    return entries, exits, overnight_vehicles

def post_data(endpoint, data):
    """Post data to the specified endpoint"""
    try:
        # Check session before each request
        if not check_session():
            print("Session expired, logging in again...")
            if not login():
                print("Failed to login. Exiting...")
                return None
        
        # Add delay to prevent rate limiting
        time.sleep(0.5)
        
        print(f"\nAttempting to post to {endpoint}")
        print(f"Data: {json.dumps(data, indent=2)}")
        
        # Determine if this is an API endpoint
        is_api_endpoint = endpoint.startswith('/api/')
        
        if is_api_endpoint:
            # For API endpoints, send JSON data
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            response = session.post(f"{BASE_URL}{endpoint}", json=data, headers=headers)
        else:
            # For regular endpoints, send form data
            form_data = {}
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    form_data[key] = json.dumps(value)
                else:
                    form_data[key] = str(value)
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            response = session.post(f"{BASE_URL}{endpoint}", data=form_data, headers=headers)
        
        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response content: {response.text}")
        
        if response.status_code == 200:
            # Check if response is HTML (indicating a redirect to login)
            if 'text/html' in response.headers.get('Content-Type', ''):
                print("Received HTML response, session might have expired")
                if login():
                    # Retry the request after successful login
                    return post_data(endpoint, data)
                else:
                    print("Failed to login after receiving HTML response")
                    return None
            
            try:
                response_data = response.json()
                print(f"Successfully posted data to {endpoint}")
                return response_data
            except json.JSONDecodeError:
                print(f"Warning: Response is not JSON but status code is 200")
                # For non-JSON responses, try to extract ID from HTML if possible
                if 'id' in response.text:
                    try:
                        import re
                        id_match = re.search(r'id["\']:\s*(\d+)', response.text)
                        if id_match:
                            return {'id': int(id_match.group(1))}
                    except Exception as e:
                        print(f"Error extracting ID from HTML: {str(e)}")
                return None
        else:
            print(f"Failed to post data to {endpoint}. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Error posting data to {endpoint}: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def main():
    # First login
    if not login():
        print("Failed to login. Exiting...")
        return

    # Post locations
    print("\n=== Posting Locations ===")
    location_ids = []
    for location in locations:
        response = post_data("/locations/add", location)
        if response and 'id' in response:
            location_ids.append(response['id'])
    
    if not location_ids:
        print("Failed to create any locations. Exiting...")
        return
    
    # Update site location_ids
    for site in sites:
        site['location_id'] = location_ids[0]  # Use first location for all sites
    
    # Post sites
    print("\n=== Posting Sites ===")
    site_ids = []
    for site in sites:
        response = post_data("/sites/add", site)
        if response and 'id' in response:
            site_ids.append(response['id'])
    
    if not site_ids:
        print("Failed to create any sites. Exiting...")
        return
    
    # Update device site_ids
    for device in devices:
        device['site_id'] = site_ids[0]  # Use first site for all devices
    
    # Post devices
    print("\n=== Posting Devices ===")
    device_ids = []
    for device in devices:
        response = post_data("/devices/add", device)
        if response and 'id' in response:
            device_ids.append(response['id'])
    
    if not device_ids:
        print("Failed to create any devices. Exiting...")
        return
    
    # Update vehicle category IDs
    for category in vehicle_categories:
        category['location_id'] = location_ids[0]
        category['site_id'] = site_ids[0]
        category['device_id'] = device_ids[0]
    
    # Post vehicle categories
    print("\n=== Posting Vehicle Categories ===")
    category_ids = []
    for category in vehicle_categories:
        response = post_data("/vehicle_categories/add", category)
        if response and 'id' in response:
            category_ids.append(response['id'])
    
    if not category_ids:
        print("Failed to create any vehicle categories. Exiting...")
        return
    
    # Update tariff IDs
    for tariff in tariffs:
        tariff['location_id'] = location_ids[0]
        tariff['site_id'] = site_ids[0]
        tariff['device_id'] = device_ids[0]
        tariff['vehicle_category_id'] = category_ids[0]
    
    # Post tariffs
    print("\n=== Posting Tariffs ===")
    for tariff in tariffs:
        post_data("/tariffs/add", tariff)
    
    # Generate and post transaction data
    print("\n=== Generating Transaction Data ===")
    entries, exits, overnight_vehicles = generate_transaction_data()
    
    # Post entries
    print("\n=== Posting Vehicle Entries ===")
    for entry in entries:
        post_data("/api/vehicle-in", entry)
    
    # Post exits
    print("\n=== Posting Vehicle Exits ===")
    for exit_data in exits:
        post_data("/api/vehicle-out", exit_data)
    
    # Post overnight vehicles
    print("\n=== Posting Overnight Vehicles ===")
    for vehicle in overnight_vehicles:
        post_data("/api/overnight-passes", vehicle)

if __name__ == "__main__":
    main() 