from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import logging
import random
import string
from flask_migrate import Migrate
from datetime import datetime, timedelta
import io
import csv

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

# Location model
class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    total_spaces = db.Column(db.Integer, nullable=False)
    available_spaces = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    sites = db.relationship('Site', backref='location', lazy=True)

# Site model
class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    total_spaces = db.Column(db.Integer, nullable=False)
    available_spaces = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='active')
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    devices = db.relationship('Device', backref='site', lazy=True)

# Device model
class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(3), unique=True, nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    device_type = db.Column(db.String(20), nullable=False)  # entry_paid or exit_paid
    upi_id = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='active')
    printer_header = db.Column(db.Text, default='')
    printer_footer = db.Column(db.Text, default='')
    vehicle_in_start_time = db.Column(db.String(5), default='00:00')  # Format: HH:MM
    vehicle_in_end_time = db.Column(db.String(5), default='23:59')    # Format: HH:MM
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return f'<Device {self.device_id}>'

# VehicleCategory model
class VehicleCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_monthly_pass = db.Column(db.Boolean, default=False)
    amount = db.Column(db.Float, nullable=False)  # Amount in INR
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    location = db.relationship('Location', backref='vehicle_categories')
    site = db.relationship('Site', backref='vehicle_categories')
    device = db.relationship('Device', backref='vehicle_categories')

# TariffInterval model
class TariffInterval(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tariff_id = db.Column(db.Integer, db.ForeignKey('tariff.id'), nullable=False)
    from_time = db.Column(db.Integer, nullable=False)  # in minutes
    to_time = db.Column(db.Integer, nullable=False)    # in minutes
    amount = db.Column(db.Float, nullable=False)

# Tariff model
class Tariff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')
    grace_time = db.Column(db.Integer, nullable=False, default=15)  # in minutes
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    vehicle_category_id = db.Column(db.Integer, db.ForeignKey('vehicle_category.id'), nullable=False)
    
    # Relationships
    location = db.relationship('Location', backref='tariffs')
    site = db.relationship('Site', backref='tariffs')
    device = db.relationship('Device', backref='tariffs')
    vehicle_category = db.relationship('VehicleCategory', backref='tariffs')
    intervals = db.relationship('TariffInterval', backref='tariff', cascade='all, delete-orphan')

# Transaction model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(50), unique=True, nullable=False)
    device_id = db.Column(db.String(50), nullable=False)
    vehicle_number = db.Column(db.String(20), nullable=False)
    vehicle_category_id = db.Column(db.Integer, nullable=False)
    entry_time = db.Column(db.DateTime, nullable=False)
    exit_time = db.Column(db.DateTime, nullable=True)
    amount_paid = db.Column(db.Float, nullable=True)
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, failed
    payment_method = db.Column(db.String(20), nullable=True)  # cash, upi, card
    payment_reference = db.Column(db.String(100), nullable=True)  # UPI reference, card number, etc.
    operator_id = db.Column(db.String(50), nullable=False)  # ID of the operator who processed the transaction
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

# VehicleEntry model
class VehicleEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_number = db.Column(db.String(20), nullable=False)
    vehicle_type = db.Column(db.String(50), nullable=False)
    transaction_id = db.Column(db.String(50), unique=True, nullable=False)
    entry_time = db.Column(db.DateTime, nullable=False)
    exit_time = db.Column(db.DateTime)
    qr_code = db.Column(db.String(100))
    amount_paid = db.Column(db.Float)
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, failed
    payment_method = db.Column(db.String(20))  # cash, upi, card
    payment_reference = db.Column(db.String(100))  # UPI reference, card number, etc.
    device_id = db.Column(db.String(3))  # Device ID from the entry
    location = db.Column(db.String(100))  # Location from the entry
    site = db.Column(db.String(100))  # Site from the entry
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

# OvernightVehicle model
class OvernightVehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_category_id = db.Column(db.Integer, db.ForeignKey('vehicle_category.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    vehicle_category = db.relationship('VehicleCategory', backref='overnight_vehicles')

# OvernightPass model
class OvernightPass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    validity_days = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='active')
    vehicle_category_id = db.Column(db.Integer, db.ForeignKey('vehicle_category.id'), nullable=False)
    transaction_id = db.Column(db.String(50), unique=True, nullable=False)
    device_id = db.Column(db.String(3), nullable=False)  # Device ID from the entry
    location = db.Column(db.String(100), nullable=False)  # Location from the entry
    site = db.Column(db.String(100), nullable=False)  # Site from the entry
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    vehicle_category = db.relationship('VehicleCategory', backref='overnight_passes')

# Create database tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user'] = email
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('index.html', active_tab='login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
        elif password != confirm_password:
            flash('Passwords do not match', 'error')
        else:
            new_user = User(
                email=email,
                password=generate_password_hash(password)
            )
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
    
    return render_template('index.html', active_tab='signup')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Get filter parameters from request
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    device_id = request.args.get('device_id')
    site = request.args.get('site')

    # Parse dates if provided, otherwise use today's date
    if from_date and to_date:
        try:
            from_date = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            to_date = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
        except ValueError:
            # If date parsing fails, use today's date
            today = datetime.now().date()
            from_date = datetime.combine(today, datetime.min.time())
            to_date = datetime.combine(today, datetime.max.time())
    else:
        # Use today's date if no parameters provided
        today = datetime.now().date()
        from_date = datetime.combine(today, datetime.min.time())
        to_date = datetime.combine(today, datetime.max.time())

    # Base query for entries
    entries_query = VehicleEntry.query.filter(
        VehicleEntry.entry_time >= from_date,
        VehicleEntry.entry_time <= to_date
    )

    # Apply device ID filter if provided
    if device_id:
        entries_query = entries_query.filter(VehicleEntry.device_id == device_id)

    # Apply site filter if provided
    if site:
        entries_query = entries_query.filter(VehicleEntry.site == site)

    # Get entries within date range and filters
    entries = entries_query.all()

    # Calculate statistics
    today_entries = len(entries)
    active_vehicles = len([e for e in entries if e.exit_time is None])
    today_revenue = sum(e.amount_paid or 0 for e in entries)
    today_exits = len([e for e in entries if e.exit_time is not None])

    # Get overnight passes within date range and filters
    overnight_query = OvernightPass.query.filter(
        OvernightPass.created_at >= from_date,
        OvernightPass.created_at <= to_date,
        OvernightPass.status == 'active'
    )

    # Apply device ID filter to overnight passes if provided
    if device_id:
        overnight_query = overnight_query.filter(OvernightPass.device_id == device_id)

    # Apply site filter to overnight passes if provided
    if site:
        overnight_query = overnight_query.filter(OvernightPass.site == site)

    overnight_passes = overnight_query.all()
    overnight_vehicles = len(overnight_passes)

    # Get recent entries (last 10) with filters and convert to dictionaries
    recent_entries = entries_query.order_by(VehicleEntry.entry_time.desc()).limit(10).all()
    recent_entries_dict = [{
        'vehicle_number': entry.vehicle_number,
        'vehicle_type': entry.vehicle_type,
        'entry_time': entry.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
        'location': entry.location,
        'site': entry.site,
        'device_id': entry.device_id,
        'exit_time': entry.exit_time.strftime('%Y-%m-%d %H:%M:%S') if entry.exit_time else None,
        'amount_paid': entry.amount_paid,
        'payment_method': entry.payment_method,
        'payment_status': entry.payment_status
    } for entry in recent_entries]

    # Get unique device IDs and sites for filter dropdowns
    device_ids = db.session.query(VehicleEntry.device_id).distinct().all()
    device_ids = [d[0] for d in device_ids if d[0]]  # Remove None values

    sites = db.session.query(VehicleEntry.site).distinct().all()
    sites = [s[0] for s in sites if s[0]]  # Remove None values

    # Prepare data for entry distribution chart
    entry_hours = []
    entry_counts = []
    hourly_revenue = []
    
    # Group entries by hour
    for hour in range(24):
        hour_start = datetime.combine(from_date.date(), datetime.min.time()) + timedelta(hours=hour)
        hour_end = hour_start + timedelta(hours=1)
        
        hour_entries = [e for e in entries if hour_start <= e.entry_time < hour_end]
        count = len(hour_entries)
        revenue = sum(e.amount_paid or 0 for e in hour_entries)
        
        entry_hours.append(f"{hour:02d}:00")
        entry_counts.append(count)
        hourly_revenue.append(revenue)

    # Calculate payment method distribution
    payment_methods = {}
    for entry in entries:
        if entry.amount_paid:
            method = entry.payment_method or 'unknown'
            payment_methods[method] = payment_methods.get(method, 0) + entry.amount_paid

    # Calculate vehicle type distribution
    vehicle_types = {}
    for entry in entries:
        vehicle_type = entry.vehicle_type
        vehicle_types[vehicle_type] = vehicle_types.get(vehicle_type, 0) + 1

    return render_template('dashboard.html',
                         today_entries=today_entries,
                         active_vehicles=active_vehicles,
                         today_revenue=today_revenue,
                         overnight_vehicles=overnight_vehicles,
                         today_exits=today_exits,
                         recent_entries=recent_entries_dict,
                         entry_hours=entry_hours,
                         entry_counts=entry_counts,
                         hourly_revenue=hourly_revenue,
                         payment_methods=list(payment_methods.keys()),
                         payment_amounts=list(payment_methods.values()),
                         vehicle_types=list(vehicle_types.keys()),
                         vehicle_type_counts=list(vehicle_types.values()),
                         from_date=from_date.strftime('%Y-%m-%dT%H:%M'),
                         to_date=to_date.strftime('%Y-%m-%dT%H:%M'),
                         device_ids=device_ids,
                         sites=sites,
                         selected_device_id=device_id,
                         selected_site=site)

@app.route('/locations')
def locations():
    if 'user' not in session:
        return redirect(url_for('login'))
    try:
        locations = Location.query.all()
        return render_template('locations.html', locations=locations)
    except Exception as e:
        flash('Error loading locations. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/locations/add', methods=['GET', 'POST'])
def add_location():
    if 'user' not in session:
        logger.warning("User not in session, redirecting to login")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            address = request.form.get('address')
            city = request.form.get('city')
            state = request.form.get('state')
            country = request.form.get('country')
            postal_code = request.form.get('postal_code')
            total_spaces = int(request.form.get('total_spaces'))
            
            new_location = Location(
                name=name,
                address=address,
                city=city,
                state=state,
                country=country,
                postal_code=postal_code,
                total_spaces=total_spaces,
                available_spaces=total_spaces
            )
            
            db.session.add(new_location)
            db.session.commit()
            logger.info(f"New location added: {name}")
            flash('Location added successfully!', 'success')
            return redirect(url_for('locations'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding location: {str(e)}")
            flash('Error adding location. Please try again.', 'error')
    
    return render_template('location_form.html')

@app.route('/locations/edit/<int:id>', methods=['GET', 'POST'])
def edit_location(id):
    if 'user' not in session:
        logger.warning("User not in session, redirecting to login")
        return redirect(url_for('login'))
    
    try:
        location = Location.query.get_or_404(id)
        
        if request.method == 'POST':
            location.name = request.form.get('name')
            location.address = request.form.get('address')
            location.city = request.form.get('city')
            location.state = request.form.get('state')
            location.country = request.form.get('country')
            location.postal_code = request.form.get('postal_code')
            location.total_spaces = int(request.form.get('total_spaces'))
            location.status = request.form.get('status')
            
            db.session.commit()
            logger.info(f"Location updated: {location.name}")
            flash('Location updated successfully!', 'success')
            return redirect(url_for('locations'))
        
        return render_template('location_form.html', location=location)
    except Exception as e:
        logger.error(f"Error in edit_location route: {str(e)}")
        flash('Error updating location. Please try again.', 'error')
        return redirect(url_for('locations'))

@app.route('/locations/delete/<int:id>', methods=['POST'])
def delete_location(id):
    if 'user' not in session:
        logger.warning("User not in session, redirecting to login")
        return redirect(url_for('login'))
    
    try:
        location = Location.query.get_or_404(id)
        db.session.delete(location)
        db.session.commit()
        logger.info(f"Location deleted: {location.name}")
        flash('Location deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting location: {str(e)}")
        flash('Error deleting location. Please try again.', 'error')
    
    return redirect(url_for('locations'))

@app.route('/sites')
def sites():
    if 'user' not in session:
        return redirect(url_for('login'))
    try:
        sites = Site.query.all()
        return render_template('sites.html', sites=sites)
    except Exception as e:
        flash('Error loading sites. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/sites/add', methods=['GET', 'POST'])
def add_site():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            location_id = request.form.get('location_id')
            total_spaces = int(request.form.get('total_spaces'))
            description = request.form.get('description')
            
            new_site = Site(
                name=name,
                location_id=location_id,
                total_spaces=total_spaces,
                available_spaces=total_spaces,
                description=description
            )
            
            db.session.add(new_site)
            db.session.commit()
            flash('Site added successfully!', 'success')
            return redirect(url_for('sites'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding site. Please try again.', 'error')
    
    locations = Location.query.all()
    return render_template('site_form.html', locations=locations)

@app.route('/sites/edit/<int:id>', methods=['GET', 'POST'])
def edit_site(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        site = Site.query.get_or_404(id)
        
        if request.method == 'POST':
            site.name = request.form.get('name')
            site.location_id = request.form.get('location_id')
            site.total_spaces = int(request.form.get('total_spaces'))
            site.status = request.form.get('status')
            site.description = request.form.get('description')
            
            db.session.commit()
            flash('Site updated successfully!', 'success')
            return redirect(url_for('sites'))
        
        locations = Location.query.all()
        return render_template('site_form.html', site=site, locations=locations)
    except Exception as e:
        flash('Error updating site. Please try again.', 'error')
        return redirect(url_for('sites'))

@app.route('/sites/delete/<int:id>', methods=['POST'])
def delete_site(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        site = Site.query.get_or_404(id)
        db.session.delete(site)
        db.session.commit()
        flash('Site deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting site. Please try again.', 'error')
    
    return redirect(url_for('sites'))

@app.route('/devices')
def devices():
    if 'user' not in session:
        return redirect(url_for('login'))
    try:
        devices = Device.query.all()
        return render_template('devices.html', devices=devices)
    except Exception as e:
        flash('Error loading devices. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/devices/add', methods=['GET', 'POST'])
def add_device():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            site_id = request.form.get('site_id')
            device_type = request.form.get('device_type')
            upi_id = request.form.get('upi_id')
            printer_header = request.form.get('printer_header', '')
            printer_footer = request.form.get('printer_footer', '')
            vehicle_in_start_time = request.form.get('vehicleInStartTime', '00:00')
            vehicle_in_end_time = request.form.get('vehicleInEndTime', '23:59')
            
            # Generate a unique 3-digit device ID
            while True:
                device_id = ''.join(random.choices(string.digits, k=3))
                if not Device.query.filter_by(device_id=device_id).first():
                    break
            
            new_device = Device(
                device_id=device_id,
                site_id=site_id,
                device_type=device_type,
                upi_id=upi_id,
                printer_header=printer_header,
                printer_footer=printer_footer,
                vehicle_in_start_time=vehicle_in_start_time,
                vehicle_in_end_time=vehicle_in_end_time
            )
            
            db.session.add(new_device)
            db.session.commit()
            flash('Device added successfully!', 'success')
            return redirect(url_for('devices'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding device. Please try again.', 'error')
    
    sites = Site.query.all()
    return render_template('device_form.html', sites=sites)

@app.route('/devices/edit/<int:id>', methods=['GET', 'POST'])
def edit_device(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        device = Device.query.get_or_404(id)
        
        if request.method == 'POST':
            device.site_id = request.form.get('site_id')
            device.device_type = request.form.get('device_type')
            device.upi_id = request.form.get('upi_id')
            device.status = request.form.get('status')
            device.printer_header = request.form.get('printer_header', '')
            device.printer_footer = request.form.get('printer_footer', '')
            device.vehicle_in_start_time = request.form.get('vehicleInStartTime', '00:00')
            device.vehicle_in_end_time = request.form.get('vehicleInEndTime', '23:59')
            
            db.session.commit()
            flash('Device updated successfully!', 'success')
            return redirect(url_for('devices'))
        
        sites = Site.query.all()
        return render_template('device_form.html', device=device, sites=sites)
    except Exception as e:
        flash('Error updating device. Please try again.', 'error')
        return redirect(url_for('devices'))

@app.route('/devices/delete/<int:id>', methods=['POST'])
def delete_device(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        device = Device.query.get_or_404(id)
        db.session.delete(device)
        db.session.commit()
        flash('Device deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting device. Please try again.', 'error')
    
    return redirect(url_for('devices'))

@app.route('/vehicle_categories')
def vehicle_categories():
    if 'user' not in session:
        return redirect(url_for('login'))
    try:
        categories = VehicleCategory.query.all()
        return render_template('vehicle_categories.html', categories=categories)
    except Exception as e:
        flash('Error loading vehicle categories. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/vehicle_categories/add', methods=['GET', 'POST'])
def add_vehicle_category():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            is_monthly_pass = 'is_monthly_pass' in request.form
            amount = float(request.form.get('amount'))
            location_id = request.form.get('location_id')
            site_id = request.form.get('site_id')
            device_id = request.form.get('device_id')
            status = request.form.get('status')
            
            new_category = VehicleCategory(
                name=name,
                description=description,
                is_monthly_pass=is_monthly_pass,
                amount=amount,
                location_id=location_id,
                site_id=site_id,
                device_id=device_id,
                status=status
            )
            
            db.session.add(new_category)
            db.session.flush()  # Get the category ID
            
            # Add overnight vehicle settings if provided
            overnight_amount = request.form.get('overnight_amount')
            overnight_status = request.form.get('overnight_status')
            
            if overnight_amount and overnight_status:
                overnight_vehicle = OvernightVehicle(
                    vehicle_category_id=new_category.id,
                    amount=float(overnight_amount),
                    status=overnight_status
                )
                db.session.add(overnight_vehicle)
            
            db.session.commit()
            flash('Vehicle category added successfully!', 'success')
            return redirect(url_for('vehicle_categories'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding vehicle category. Please try again.', 'error')
    
    locations = Location.query.all()
    sites = Site.query.all()
    devices = Device.query.all()
    return render_template('vehicle_category_form.html', 
                         locations=locations, 
                         sites=sites, 
                         devices=devices)

@app.route('/vehicle_categories/edit/<int:id>', methods=['GET', 'POST'])
def edit_vehicle_category(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        category = VehicleCategory.query.get_or_404(id)
        overnight_vehicle = OvernightVehicle.query.filter_by(vehicle_category_id=id).first()
        
        if request.method == 'POST':
            category.name = request.form.get('name')
            category.description = request.form.get('description')
            category.is_monthly_pass = 'is_monthly_pass' in request.form
            category.amount = float(request.form.get('amount'))
            category.location_id = request.form.get('location_id')
            category.site_id = request.form.get('site_id')
            category.device_id = request.form.get('device_id')
            category.status = request.form.get('status')
            
            # Update or create overnight vehicle settings
            overnight_amount = request.form.get('overnight_amount')
            overnight_status = request.form.get('overnight_status')
            
            if overnight_amount and overnight_status:
                if overnight_vehicle:
                    overnight_vehicle.amount = float(overnight_amount)
                    overnight_vehicle.status = overnight_status
                else:
                    overnight_vehicle = OvernightVehicle(
                        vehicle_category_id=category.id,
                        amount=float(overnight_amount),
                        status=overnight_status
                    )
                    db.session.add(overnight_vehicle)
            
            db.session.commit()
            flash('Vehicle category updated successfully!', 'success')
            return redirect(url_for('vehicle_categories'))
        
        locations = Location.query.all()
        sites = Site.query.all()
        devices = Device.query.all()
        return render_template('vehicle_category_form.html', 
                             category=category,
                             overnight_vehicle=overnight_vehicle,
                             locations=locations,
                             sites=sites,
                             devices=devices)
    except Exception as e:
        flash('Error updating vehicle category. Please try again.', 'error')
        return redirect(url_for('vehicle_categories'))

@app.route('/vehicle_categories/delete/<int:id>', methods=['POST'])
def delete_vehicle_category(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        category = VehicleCategory.query.get_or_404(id)
        db.session.delete(category)
        db.session.commit()
        flash('Vehicle category deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting vehicle category. Please try again.', 'error')
    
    return redirect(url_for('vehicle_categories'))

@app.route('/tariffs')
def tariffs():
    tariffs = Tariff.query.all()
    return render_template('tariffs.html', tariffs=tariffs)

@app.route('/tariffs/add', methods=['GET', 'POST'])
def add_tariff():
    if request.method == 'POST':
        try:
            # Create tariff
            tariff = Tariff(
                name=request.form['name'],
                status=request.form['status'],
                grace_time=int(request.form['grace_time']),
                location_id=int(request.form['location_id']),
                site_id=int(request.form['site_id']),
                device_id=int(request.form['device_id']),
                vehicle_category_id=int(request.form['vehicle_category_id'])
            )
            db.session.add(tariff)
            db.session.flush()  # Get the tariff ID

            # Add intervals
            from_times = request.form.getlist('interval_from[]')
            to_times = request.form.getlist('interval_to[]')
            amounts = request.form.getlist('interval_amount[]')

            for from_time, to_time, amount in zip(from_times, to_times, amounts):
                interval = TariffInterval(
                    tariff_id=tariff.id,
                    from_time=int(from_time),
                    to_time=int(to_time),
                    amount=float(amount)
                )
                db.session.add(interval)

            db.session.commit()
            flash('Tariff added successfully!', 'success')
            return redirect(url_for('tariffs'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding tariff: {str(e)}', 'error')
            return redirect(url_for('add_tariff'))

    locations = Location.query.all()
    sites = Site.query.all()
    devices = Device.query.all()
    vehicle_categories = VehicleCategory.query.all()
    return render_template('tariff_form.html', 
                         locations=locations,
                         sites=sites,
                         devices=devices,
                         vehicle_categories=vehicle_categories)

@app.route('/tariffs/edit/<int:id>', methods=['GET', 'POST'])
def edit_tariff(id):
    tariff = Tariff.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Update tariff
            tariff.name = request.form['name']
            tariff.status = request.form['status']
            tariff.grace_time = int(request.form['grace_time'])
            tariff.location_id = int(request.form['location_id'])
            tariff.site_id = int(request.form['site_id'])
            tariff.device_id = int(request.form['device_id'])
            tariff.vehicle_category_id = int(request.form['vehicle_category_id'])

            # Delete existing intervals
            TariffInterval.query.filter_by(tariff_id=tariff.id).delete()

            # Add new intervals
            from_times = request.form.getlist('interval_from[]')
            to_times = request.form.getlist('interval_to[]')
            amounts = request.form.getlist('interval_amount[]')

            for from_time, to_time, amount in zip(from_times, to_times, amounts):
                interval = TariffInterval(
                    tariff_id=tariff.id,
                    from_time=int(from_time),
                    to_time=int(to_time),
                    amount=float(amount)
                )
                db.session.add(interval)

            db.session.commit()
            flash('Tariff updated successfully!', 'success')
            return redirect(url_for('tariffs'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating tariff: {str(e)}', 'error')
            return redirect(url_for('edit_tariff', id=id))

    locations = Location.query.all()
    sites = Site.query.all()
    devices = Device.query.all()
    vehicle_categories = VehicleCategory.query.all()
    return render_template('tariff_form.html', 
                         tariff=tariff,
                         locations=locations,
                         sites=sites,
                         devices=devices,
                         vehicle_categories=vehicle_categories)

@app.route('/tariffs/delete/<int:id>')
def delete_tariff(id):
    tariff = Tariff.query.get_or_404(id)
    try:
        db.session.delete(tariff)
        db.session.commit()
        flash('Tariff deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting tariff: {str(e)}', 'error')
    return redirect(url_for('tariffs'))

@app.route('/logout')
def logout():
    if 'user' in session:
        session.pop('user', None)
        flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/api/device/config/<device_id>', methods=['GET'])
def get_device_config(device_id):
    try:
        # Get device details
        device = Device.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({'error': 'Device not found'}), 404

        # Get site details
        site = Site.query.get(device.site_id)
        if not site:
            return jsonify({'error': 'Site not found'}), 404

        # Get location details
        location = Location.query.get(site.location_id)
        if not location:
            return jsonify({'error': 'Location not found'}), 404

        # Get all vehicle categories for this location
        vehicle_categories = VehicleCategory.query.filter_by(location_id=location.id).all()
        categories_data = [{
            'id': cat.id,
            'name': cat.name,
            'description': cat.description,
            'status': cat.status
        } for cat in vehicle_categories]

        # Get all tariffs for this location
        tariffs = Tariff.query.filter_by(location_id=location.id).all()
        tariffs_data = []
        for tariff in tariffs:
            # Get time intervals for each tariff
            intervals = TariffInterval.query.filter_by(tariff_id=tariff.id).all()
            intervals_data = [{
                'startTime': interval.from_time,
                'endTime': interval.to_time,
                'amount': interval.amount
            } for interval in intervals]

            tariffs_data.append({
                'id': tariff.id,
                'name': tariff.name,
                'deviceId': tariff.device_id,
                'locationId': tariff.location_id,
                'siteId': tariff.site_id,
                'vehicleCategoryId': tariff.vehicle_category_id,
                'graceTime': tariff.grace_time,
                'status': tariff.status,
                'timeIntervals': intervals_data
            })

        # Get all monthly passes for this location
        monthly_passes = VehicleCategory.query.filter_by(location_id=location.id, is_monthly_pass=True).all()
        passes_data = [{
            'id': cat.id,
            'name': cat.name,
            'amount': cat.amount,
            'validityDays': 30,  # Assuming a default validity of 30 days
            'status': cat.status,
            'vehicleCategoryId': cat.id,
            'transactionId': f"TXN{random.randint(100000000, 999999999)}"  # Generate a random transaction ID
        } for cat in monthly_passes]

        # Get all overnight vehicles for this location
        overnight_vehicles = OvernightVehicle.query.join(VehicleCategory).filter(
            VehicleCategory.location_id == location.id
        ).all()
        overnight_data = [{
            'id': ov.id,
            'vehicleCategoryId': ov.vehicle_category_id,
            'amount': ov.amount,
            'status': ov.status
        } for ov in overnight_vehicles]

        # Prepare response data
        response_data = {
            'device': {
                'id': device.id,
                'deviceId': device.device_id,
                'deviceType': device.device_type,
                'status': device.status,
                'upiId': device.upi_id,
                'printerHeader': device.printer_header,
                'printerFooter': device.printer_footer
            },
            'location': {
                'id': location.id,
                'name': location.name,
                'status': location.status
            },
            'site': {
                'id': site.id,
                'name': site.name,
                'description': site.description,
                'status': site.status
            },
            'vehicleCategories': categories_data,
            'tariffs': tariffs_data,
            'monthlyPasses': passes_data,
            'overnightVehicles': overnight_data,
            'vehicleInStartTime': device.vehicle_in_start_time,
            'vehicleInEndTime': device.vehicle_in_end_time
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/device/transaction', methods=['POST'])
def receive_transaction():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['transaction_id', 'device_id', 'vehicle_number', 
                         'vehicle_category_id', 'entry_time', 'operator_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Check if transaction already exists
        existing_transaction = Transaction.query.filter_by(transaction_id=data['transaction_id']).first()
        if existing_transaction:
            return jsonify({
                'error': 'Transaction already exists',
                'transaction_id': data['transaction_id']
            }), 409

        # Create new transaction
        transaction = Transaction(
            transaction_id=data['transaction_id'],
            device_id=data['device_id'],
            vehicle_number=data['vehicle_number'],
            vehicle_category_id=data['vehicle_category_id'],
            entry_time=datetime.fromisoformat(data['entry_time']),
            operator_id=data['operator_id']
        )

        # If this is an exit transaction, update exit details
        if 'exit_time' in data:
            transaction.exit_time = datetime.fromisoformat(data['exit_time'])
            transaction.amount_paid = data.get('amount_paid')
            transaction.payment_status = data.get('payment_status', 'paid')
            transaction.payment_method = data.get('payment_method')
            transaction.payment_reference = data.get('payment_reference')

        db.session.add(transaction)
        db.session.commit()

        return jsonify({
            'message': 'Transaction received successfully',
            'transaction_id': transaction.transaction_id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/reports')
def reports():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('reports.html')

@app.route('/api/reports')
def get_reports():
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')
    location_id = request.args.get('location')

    # Convert dates to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
    end_date = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None

    # Base query for transactions
    query = Transaction.query

    # Apply filters
    if start_date:
        query = query.filter(Transaction.entry_time >= start_date)
    if end_date:
        query = query.filter(Transaction.entry_time <= end_date)
    if location_id:
        query = query.join(Device).join(Site).filter(Site.location_id == location_id)

    # Get all transactions
    transactions = query.all()

    # Calculate summary statistics
    summary = {
        'totalRevenue': sum(t.amount_paid or 0 for t in transactions),
        'totalTransactions': len(transactions),
        'avgStayDuration': calculate_avg_stay_duration(transactions),
        'occupancyRate': calculate_occupancy_rate(transactions, location_id)
    }

    # Generate chart data
    charts = {
        'revenueByCategoryChart': generate_revenue_by_category_chart(transactions),
        'revenueByPaymentChart': generate_revenue_by_payment_chart(transactions),
        'transactionsByHourChart': generate_transactions_by_hour_chart(transactions),
        'transactionsByDayChart': generate_transactions_by_day_chart(transactions),
        'vehicleCategoryChart': generate_vehicle_category_chart(transactions),
        'topVehiclesChart': generate_top_vehicles_chart(transactions),
        'revenueByLocationChart': generate_revenue_by_location_chart(transactions),
        'occupancyByLocationChart': generate_occupancy_by_location_chart(transactions),
        'transactionsByDeviceChart': generate_transactions_by_device_chart(transactions),
        'deviceStatusChart': generate_device_status_chart(),
        'transactionsByOperatorChart': generate_transactions_by_operator_chart(transactions),
        'revenueByOperatorChart': generate_revenue_by_operator_chart(transactions)
    }

    return jsonify({
        'summary': summary,
        'charts': charts
    })

@app.route('/api/reports/export')
def export_reports():
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')
    location_id = request.args.get('location')

    # Convert dates to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
    end_date = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None

    # Generate CSV data
    csv_data = generate_csv_report(start_date, end_date, location_id)

    # Create response
    response = make_response(csv_data)
    response.headers['Content-Disposition'] = 'attachment; filename=parking_reports.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response

@app.route('/api/vehicle-in', methods=['POST'])
def vehicle_entry():
    try:
        data = request.get_json()
        
        # Log the incoming data
        logger.info("Received vehicle entry data:")
        logger.info(f"Vehicle Number: {data.get('vehicleNumber')}")
        logger.info(f"Vehicle Type: {data.get('vehicleType')}")
        logger.info(f"Transaction ID: {data.get('transactionId')}")
        logger.info(f"Entry Time: {data.get('entryTime')}")
        logger.info(f"Device ID: {data.get('deviceId')}")
        logger.info(f"Location: {data.get('location')}")
        logger.info(f"Site: {data.get('site')}")
        logger.info(f"Status: {data.get('status')}")
        logger.info(f"Is Synced: {data.get('isSynced')}")
        
        # Validate required fields
        required_fields = ['vehicleNumber', 'vehicleType', 'transactionId', 'entryTime', 'deviceId']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400

        # Check if transaction already exists
        existing_entry = VehicleEntry.query.filter_by(transaction_id=data['transactionId']).first()
        if existing_entry:
            return jsonify({
                'status': 'error',
                'message': 'Transaction ID already exists'
            }), 409

        # Parse entry time with multiple format support
        entry_time = None
        try:
            # Try parsing as ISO format first
            entry_time_str = data['entryTime']
            if 'Z' in entry_time_str:
                entry_time = datetime.fromisoformat(entry_time_str.replace('Z', '+00:00'))
            elif '+' in entry_time_str or '-' in entry_time_str[-6:]:
                entry_time = datetime.fromisoformat(entry_time_str)
            else:
                # If no timezone indicator, assume local timezone
                entry_time = datetime.strptime(entry_time_str, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            try:
                # Try parsing as "MMM DD, YYYY HH:MM:SS AM/PM" format
                entry_time = datetime.strptime(data['entryTime'], '%b %d, %Y %I:%M:%S %p')
            except ValueError:
                try:
                    # Try parsing as "YYYY-MM-DD HH:MM:SS" format
                    entry_time = datetime.strptime(data['entryTime'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    return jsonify({
                        'status': 'error',
                        'message': f'Invalid date format: {data["entryTime"]}. Supported formats: ISO (with or without timezone), "MMM DD, YYYY HH:MM:SS AM/PM", "YYYY-MM-DD HH:MM:SS"'
                    }), 400

        # Create new vehicle entry
        new_entry = VehicleEntry(
            vehicle_number=data['vehicleNumber'],
            vehicle_type=data['vehicleType'],
            transaction_id=data['transactionId'],
            entry_time=entry_time,
            qr_code=data.get('qrCode'),
            device_id=data['deviceId'],
            location=data.get('location', 'Kodaikanal'),
            site=data.get('site', 'Main Parking')
        )

        db.session.add(new_entry)
        db.session.commit()

        # Log the created entry
        logger.info("Created new vehicle entry:")
        logger.info(f"ID: {new_entry.id}")
        logger.info(f"Vehicle Number: {new_entry.vehicle_number}")
        logger.info(f"Device ID: {new_entry.device_id}")
        logger.info(f"Location: {new_entry.location}")
        logger.info(f"Site: {new_entry.site}")

        # Return response with ISO format date including timezone
        return jsonify({
            'status': 'success',
            'message': 'Vehicle entry recorded successfully',
            'data': {
                'id': new_entry.id,
                'vehicleNumber': new_entry.vehicle_number,
                'vehicleType': new_entry.vehicle_type,
                'transactionId': new_entry.transaction_id,
                'entryTime': new_entry.entry_time.isoformat() + 'Z',
                'qrCode': new_entry.qr_code,
                'deviceId': new_entry.device_id,
                'location': new_entry.location,
                'site': new_entry.site
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing vehicle entry: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error processing vehicle entry: {str(e)}'
        }), 500

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

@app.route('/api/analytics/summary')
def analytics_summary():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    
    # Get transactions within date range
    transactions = Transaction.query.filter(
        Transaction.entry_time >= start_date,
        Transaction.entry_time < end_date
    ).all()
    
    # Calculate summary statistics
    total_revenue = sum(t.amount_paid or 0 for t in transactions)
    total_vehicles = len(transactions)
    
    # Calculate overnight vehicles
    overnight_vehicles = sum(1 for t in transactions if t.exit_time and (t.exit_time - t.entry_time).total_seconds() > 12 * 3600)
    
    # Calculate average stay duration - handle division by zero
    stay_durations = [(t.exit_time - t.entry_time).total_seconds() / 3600 for t in transactions if t.exit_time]
    avg_stay_duration = sum(stay_durations) / len(stay_durations) if stay_durations else 0
    
    return jsonify({
        'total_revenue': total_revenue,
        'total_vehicles': total_vehicles,
        'overnight_vehicles': overnight_vehicles,
        'avg_stay_duration': avg_stay_duration
    })

@app.route('/api/analytics/vehicle-in')
def analytics_vehicle_in():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        logger.info(f"Received date range: start_date={start_date}, end_date={end_date}")
        
        # If no dates provided, use last 24 hours
        if not start_date or not end_date:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)
            logger.info(f"Using default date range: start_date={start_date}, end_date={end_date}")
        else:
            # Convert string dates to datetime objects
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError as e:
                logger.error(f"Error parsing dates: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid date format: {str(e)}'
                }), 400
        
        logger.info(f"Querying vehicle entries between {start_date} and {end_date}")
        
        # Get vehicle entries within date range
        entries = VehicleEntry.query.filter(
            VehicleEntry.entry_time >= start_date,
            VehicleEntry.entry_time < end_date
        ).all()
        
        logger.info(f"Found {len(entries)} vehicle entries in the date range")
        
        # If no entries found, return empty list with message
        if not entries:
            logger.info("No vehicle entries found in the date range")
            return jsonify({
                'status': 'success',
                'message': 'No vehicle entries found in the selected date range',
                'data': []
            })
        
        # Format data for response
        data = [{
            'vehicle_number': entry.vehicle_number,
            'vehicle_type': entry.vehicle_type,
            'entry_time': entry.entry_time.isoformat(),
            'location': entry.location,
            'site': entry.site
        } for entry in entries]
        
        logger.info(f"Returning {len(data)} vehicle entries")
        return jsonify({
            'status': 'success',
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Exception in analytics_vehicle_in: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error fetching vehicle entries: {str(e)}'
        }), 500

@app.route('/api/vehicle-out', methods=['POST'])
def vehicle_exit():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['transactionId', 'exitTime', 'amountPaid']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400

        # Find the vehicle entry
        vehicle_entry = VehicleEntry.query.filter_by(transaction_id=data['transactionId']).first()
        if not vehicle_entry:
            return jsonify({
                'status': 'error',
                'message': 'Transaction ID not found'
            }), 404

        # Check if vehicle has already exited
        if vehicle_entry.exit_time:
            return jsonify({
                'status': 'error',
                'message': 'Vehicle has already exited'
            }), 409

        # Parse exit time with multiple format support
        exit_time = None
        try:
            # Try parsing as ISO format first
            exit_time_str = data['exitTime']
            if 'Z' in exit_time_str:
                exit_time = datetime.fromisoformat(exit_time_str.replace('Z', '+00:00'))
            elif '+' in exit_time_str or '-' in exit_time_str[-6:]:
                exit_time = datetime.fromisoformat(exit_time_str)
            else:
                # If no timezone indicator, assume local timezone
                exit_time = datetime.strptime(exit_time_str, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            try:
                # Try parsing as "MMM DD, YYYY HH:MM:SS AM/PM" format
                exit_time = datetime.strptime(data['exitTime'], '%b %d, %Y %I:%M:%S %p')
            except ValueError:
                try:
                    # Try parsing as "YYYY-MM-DD HH:MM:SS" format
                    exit_time = datetime.strptime(data['exitTime'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    return jsonify({
                        'status': 'error',
                        'message': f'Invalid date format: {data["exitTime"]}. Supported formats: ISO (with or without timezone), "MMM DD, YYYY HH:MM:SS AM/PM", "YYYY-MM-DD HH:MM:SS"'
                    }), 400

        # Update vehicle entry with exit information
        vehicle_entry.exit_time = exit_time
        vehicle_entry.amount_paid = float(data['amountPaid'])
        vehicle_entry.payment_status = data.get('status', 'completed')
        vehicle_entry.payment_method = data.get('paymentMethod')
        vehicle_entry.payment_reference = data.get('paymentReference')
        vehicle_entry.device_id = data.get('deviceId')  # Update device_id from exit device

        db.session.commit()

        # Return response with ISO format dates including timezone
        return jsonify({
            'status': 'success',
            'message': 'Vehicle exit recorded successfully',
            'data': {
                'id': vehicle_entry.id,
                'vehicleNumber': vehicle_entry.vehicle_number,
                'vehicleType': vehicle_entry.vehicle_type,
                'transactionId': vehicle_entry.transaction_id,
                'entryTime': vehicle_entry.entry_time.isoformat() + 'Z',
                'exitTime': vehicle_entry.exit_time.isoformat() + 'Z',
                'amountPaid': vehicle_entry.amount_paid,
                'paymentStatus': vehicle_entry.payment_status,
                'paymentMethod': vehicle_entry.payment_method,
                'paymentReference': vehicle_entry.payment_reference,
                'duration': str(vehicle_entry.exit_time - vehicle_entry.entry_time)
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Error processing vehicle exit: {str(e)}'
        }), 500

@app.route('/api/analytics/vehicle-out')
def analytics_vehicle_out():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    
    # Get vehicle exits within date range
    exits = VehicleEntry.query.filter(
        VehicleEntry.exit_time >= start_date,
        VehicleEntry.exit_time < end_date
    ).all()
    
    # Format data for response
    data = [{
        'vehicle_number': exit.vehicle_number,
        'category': exit.vehicle_type,
        'exit_time': exit.exit_time.isoformat(),
        'amount': exit.amount_paid or 0
    } for exit in exits]
    
    return jsonify(data)

@app.route('/api/analytics/overnight')
def analytics_overnight():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    
    # Get overnight vehicles within date range
    overnight_vehicles = VehicleEntry.query.filter(
        VehicleEntry.entry_time >= start_date,
        VehicleEntry.entry_time < end_date,
        VehicleEntry.exit_time != None,
        db.func.extract('epoch', VehicleEntry.exit_time - VehicleEntry.entry_time) > 12 * 3600
    ).all()
    
    # Format data for response
    data = [{
        'vehicle_number': vehicle.vehicle_number,
        'category': vehicle.vehicle_type,
        'entry_time': vehicle.entry_time.isoformat(),
        'exit_time': vehicle.exit_time.isoformat(),
        'amount': vehicle.amount_paid or 0
    } for vehicle in overnight_vehicles]
    
    return jsonify(data)

@app.route('/api/analytics/revenue-by-category')
def analytics_revenue_by_category():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    
    # Get transactions within date range
    transactions = Transaction.query.filter(
        Transaction.entry_time >= start_date,
        Transaction.entry_time < end_date
    ).all()
    
    # Group by vehicle category and calculate total revenue
    revenue_by_category = {}
    for transaction in transactions:
        category = transaction.vehicle_category_id
        amount = transaction.amount_paid or 0
        revenue_by_category[category] = revenue_by_category.get(category, 0) + amount
    
    # Format data for chart
    labels = list(revenue_by_category.keys())
    values = list(revenue_by_category.values())
    
    return jsonify({
        'labels': labels,
        'values': values
    })

@app.route('/api/analytics/vehicle-count-by-category')
def analytics_vehicle_count_by_category():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    
    # Get transactions within date range
    transactions = Transaction.query.filter(
        Transaction.entry_time >= start_date,
        Transaction.entry_time < end_date
    ).all()
    
    # Group by vehicle category and count vehicles
    count_by_category = {}
    for transaction in transactions:
        category = transaction.vehicle_category_id
        count_by_category[category] = count_by_category.get(category, 0) + 1
    
    # Format data for chart
    labels = list(count_by_category.keys())
    values = list(count_by_category.values())
    
    return jsonify({
        'labels': labels,
        'values': values
    })

@app.route('/api/overnight-passes', methods=['POST'])
def create_overnight_pass():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['id', 'name', 'amount', 'validityDays', 'status', 'vehicleCategoryId', 
                         'transactionId', 'deviceId', 'location', 'site', 'createdAt']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400

        # Check if transaction ID already exists
        existing_pass = OvernightPass.query.filter_by(transaction_id=data['transactionId']).first()
        if existing_pass:
            return jsonify({
                'status': 'error',
                'message': 'Transaction ID already exists'
            }), 409

        # Check if ID already exists
        existing_id = OvernightPass.query.filter_by(id=data['id']).first()
        if existing_id:
            return jsonify({
                'status': 'error',
                'message': 'ID already exists'
            }), 409

        # Convert createdAt to datetime
        created_at = datetime.fromisoformat(data['createdAt'].replace('Z', '+00:00'))

        # Create new overnight pass
        new_pass = OvernightPass(
            id=data['id'],  # Using the timestamp-based ID
            name=data['name'],
            amount=float(data['amount']),  # Ensure amount is float
            validity_days=int(data['validityDays']),  # Ensure validity_days is integer
            status=data['status'],
            vehicle_category_id=int(data['vehicleCategoryId']),  # Ensure vehicle_category_id is integer
            transaction_id=data['transactionId'],
            device_id=data['deviceId'],
            location=data['location'],
            site=data['site'],
            created_at=created_at
        )

        db.session.add(new_pass)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Overnight pass created successfully',
            'data': {
                'id': new_pass.id,
                'name': new_pass.name,
                'amount': new_pass.amount,
                'validityDays': new_pass.validity_days,
                'status': new_pass.status,
                'vehicleCategoryId': new_pass.vehicle_category_id,
                'transactionId': new_pass.transaction_id,
                'deviceId': new_pass.device_id,
                'location': new_pass.location,
                'site': new_pass.site,
                'createdAt': new_pass.created_at.isoformat()
            }
        }), 201

    except ValueError as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Invalid data format: {str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Error creating overnight pass: {str(e)}'
        }), 500

@app.route('/api/analytics/overnight-passes')
def analytics_overnight_passes():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        logger.info(f"Received date range: start_date={start_date}, end_date={end_date}")
        
        # Convert string dates to datetime objects
        if start_date:
            try:
                # Try parsing as date-only format first
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                try:
                    # Try parsing as ISO format with timezone
                    start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                except ValueError:
                    # Try parsing as ISO format with milliseconds
                    start_date = datetime.strptime(start_date, '%Y-%m-%dT%H:%M:%S.%fZ')
            logger.info(f"Parsed start_date: {start_date}")
            
        if end_date:
            try:
                # Try parsing as date-only format first
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                try:
                    # Try parsing as ISO format with timezone
                    end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                except ValueError:
                    # Try parsing as ISO format with milliseconds
                    end_date = datetime.strptime(end_date, '%Y-%m-%dT%H:%M:%S.%fZ')
            logger.info(f"Parsed end_date: {end_date}")
            # Add one day to include the entire end date
            end_date = end_date + timedelta(days=1)
            logger.info(f"Adjusted end_date: {end_date}")
        
        # Get all overnight passes first to check total count
        all_passes = OvernightPass.query.all()
        logger.info(f"Total passes in database: {len(all_passes)}")
        
        # Calculate time periods
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        yesterday_start = today_start - timedelta(days=1)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)
        
        # Calculate summary statistics for different time periods
        today_passes = [p for p in all_passes if p.created_at >= today_start]
        yesterday_passes = [p for p in all_passes if yesterday_start <= p.created_at < today_start]
        week_passes = [p for p in all_passes if p.created_at >= week_start]
        month_passes = [p for p in all_passes if p.created_at >= month_start]
        
        # Calculate summary data
        summary = {
            'today': {
                'count': len(today_passes),
                'amount': sum(p.amount for p in today_passes)
            },
            'yesterday': {
                'count': len(yesterday_passes),
                'amount': sum(p.amount for p in yesterday_passes)
            },
            'week': {
                'count': len(week_passes),
                'amount': sum(p.amount for p in week_passes)
            },
            'month': {
                'count': len(month_passes),
                'amount': sum(p.amount for p in month_passes)
            },
            'total_passes': len(all_passes),
            'total_revenue': sum(p.amount for p in all_passes),
            'active_passes': sum(1 for p in all_passes if p.status == 'active')
        }
        
        # Base query for filtered passes
        query = OvernightPass.query
        
        # Apply date filters if provided
        if start_date:
            query = query.filter(OvernightPass.created_at >= start_date)
        if end_date:
            query = query.filter(OvernightPass.created_at < end_date)
        
        # Get filtered passes
        passes = query.all()
        logger.info(f"Found {len(passes)} passes in the date range")
        
        # Group by vehicle category
        category_stats = {}
        for pass_item in passes:
            category = pass_item.vehicle_category.name if pass_item.vehicle_category else 'Unknown'
            if category not in category_stats:
                category_stats[category] = {
                    'count': 0,
                    'revenue': 0
                }
            category_stats[category]['count'] += 1
            category_stats[category]['revenue'] += pass_item.amount
        
        # Format data for response
        data = {
            'summary': summary,
            'category_stats': category_stats,
            'passes': [{
                'id': pass_item.id,
                'name': pass_item.name,
                'amount': pass_item.amount,
                'validity_days': pass_item.validity_days,
                'status': pass_item.status,
                'vehicle_category': pass_item.vehicle_category.name if pass_item.vehicle_category else 'Unknown',
                'transaction_id': pass_item.transaction_id,
                'device_id': pass_item.device_id,
                'location': pass_item.location,
                'site': pass_item.site,
                'created_at': pass_item.created_at.isoformat()
            } for pass_item in passes]
        }
        
        logger.info("Sending response with data")
        return jsonify(data)
        
    except ValueError as e:
        logger.error(f"ValueError in analytics_overnight_passes: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Invalid date format: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"Exception in analytics_overnight_passes: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error fetching overnight passes: {str(e)}'
        }), 500

@app.route('/entries/detail')
def entries_detail():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Get date parameters from request
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    # Parse dates if provided, otherwise use today's date
    if from_date and to_date:
        try:
            from_date = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            to_date = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
        except ValueError:
            # If date parsing fails, use today's date
            today = datetime.now().date()
            from_date = datetime.combine(today, datetime.min.time())
            to_date = datetime.combine(today, datetime.max.time())
    else:
        # Use today's date if no parameters provided
        today = datetime.now().date()
        from_date = datetime.combine(today, datetime.min.time())
        to_date = datetime.combine(today, datetime.max.time())

    # Get entries within date range
    entries = VehicleEntry.query.filter(
        VehicleEntry.entry_time >= from_date,
        VehicleEntry.entry_time <= to_date
    ).order_by(VehicleEntry.entry_time.desc()).all()

    # Format entries for display
    formatted_entries = []
    for entry in entries:
        # Get device ID from the entry's device_id field
        device_id = entry.device_id if hasattr(entry, 'device_id') else 'N/A'
        
        formatted_entries.append({
            'vehicle_number': entry.vehicle_number,
            'vehicle_type': entry.vehicle_type,
            'entry_time': entry.entry_time,
            'exit_time': entry.exit_time,
            'amount_paid': entry.amount_paid,
            'payment_status': entry.payment_status,
            'payment_method': entry.payment_method,
            'device_id': device_id,
            'location': entry.location if hasattr(entry, 'location') else 'Kodaikanal',
            'site': entry.site if hasattr(entry, 'site') else 'Main Parking'
        })

    return render_template('entries_detail.html',
                         entries=formatted_entries,
                         from_date=from_date.strftime('%Y-%m-%dT%H:%M'),
                         to_date=to_date.strftime('%Y-%m-%dT%H:%M'))

@app.route('/active-vehicles/detail')
def active_vehicles_detail():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Get date parameters from request
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    # Parse dates if provided, otherwise use today's date
    if from_date and to_date:
        try:
            from_date = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            to_date = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
        except ValueError:
            # If date parsing fails, use today's date
            today = datetime.now().date()
            from_date = datetime.combine(today, datetime.min.time())
            to_date = datetime.combine(today, datetime.max.time())
    else:
        # Use today's date if no parameters provided
        today = datetime.now().date()
        from_date = datetime.combine(today, datetime.min.time())
        to_date = datetime.combine(today, datetime.max.time())

    # Get active vehicles within date range
    active_vehicles = VehicleEntry.query.filter(
        VehicleEntry.entry_time >= from_date,
        VehicleEntry.entry_time <= to_date,
        VehicleEntry.exit_time.is_(None)
    ).order_by(VehicleEntry.entry_time.desc()).all()

    # Calculate duration for each vehicle
    for vehicle in active_vehicles:
        duration = datetime.now() - vehicle.entry_time
        hours = duration.total_seconds() / 3600
        vehicle.duration = f"{int(hours)}h {int((hours % 1) * 60)}m"

    return render_template('active_vehicles_detail.html',
                         active_vehicles=active_vehicles,
                         from_date=from_date.strftime('%Y-%m-%dT%H:%M'),
                         to_date=to_date.strftime('%Y-%m-%dT%H:%M'))

@app.route('/revenue/detail')
def revenue_detail():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Get date parameters from request
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    # Parse dates if provided, otherwise use today's date
    if from_date and to_date:
        try:
            from_date = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            to_date = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
        except ValueError:
            # If date parsing fails, use today's date
            today = datetime.now().date()
            from_date = datetime.combine(today, datetime.min.time())
            to_date = datetime.combine(today, datetime.max.time())
    else:
        # Use today's date if no parameters provided
        today = datetime.now().date()
        from_date = datetime.combine(today, datetime.min.time())
        to_date = datetime.combine(today, datetime.max.time())

    # Get regular vehicle entries within date range
    regular_entries = VehicleEntry.query.filter(
        VehicleEntry.entry_time >= from_date,
        VehicleEntry.entry_time <= to_date,
        VehicleEntry.amount_paid.isnot(None)
    ).order_by(VehicleEntry.entry_time.desc()).all()

    # Get overnight passes within date range
    overnight_passes = OvernightPass.query.filter(
        OvernightPass.created_at >= from_date,
        OvernightPass.created_at <= to_date
    ).all()

    # Calculate revenue metrics
    regular_revenue = sum(e.amount_paid or 0 for e in regular_entries)
    overnight_revenue = sum(p.amount for p in overnight_passes)
    total_revenue = regular_revenue + overnight_revenue
    
    # Calculate revenue by payment method for regular entries
    revenue_by_payment = {}
    for t in regular_entries:
        method = t.payment_method or 'unknown'
        revenue_by_payment[method] = revenue_by_payment.get(method, 0) + (t.amount_paid or 0)
    
    # Calculate average transaction amount - handle division by zero
    total_transactions = len(regular_entries) + len(overnight_passes)
    avg_transaction = total_revenue / total_transactions if total_transactions > 0 else 0
    
    # Calculate revenue by hour for regular entries
    revenue_by_hour = {}
    for t in regular_entries:
        hour = t.entry_time.hour
        revenue_by_hour[hour] = revenue_by_hour.get(hour, 0) + (t.amount_paid or 0)

    return render_template('revenue_detail.html',
                         transactions=regular_entries,
                         overnight_passes=overnight_passes,
                         from_date=from_date.strftime('%Y-%m-%dT%H:%M'),
                         to_date=to_date.strftime('%Y-%m-%dT%H:%M'),
                         total_revenue=total_revenue,
                         regular_revenue=regular_revenue,
                         overnight_revenue=overnight_revenue,
                         revenue_by_payment=revenue_by_payment,
                         avg_transaction=avg_transaction,
                         revenue_by_hour=revenue_by_hour)

@app.route('/overnight-vehicles/detail')
def overnight_vehicles_detail():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Get date parameters from request
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    # Parse dates if provided, otherwise use today's date
    if from_date and to_date:
        try:
            from_date = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            to_date = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
        except ValueError:
            # If date parsing fails, use today's date
            today = datetime.now().date()
            from_date = datetime.combine(today, datetime.min.time())
            to_date = datetime.combine(today, datetime.max.time())
    else:
        # Use today's date if no parameters provided
        today = datetime.now().date()
        from_date = datetime.combine(today, datetime.min.time())
        to_date = datetime.combine(today, datetime.max.time())

    # Get overnight passes within date range
    overnight_passes = OvernightPass.query.filter(
        OvernightPass.created_at >= from_date,
        OvernightPass.created_at <= to_date,
        OvernightPass.status == 'active'
    ).order_by(OvernightPass.created_at.desc()).all()

    # Format data for display
    for pass_item in overnight_passes:
        # Calculate duration based on validity days
        pass_item.duration = f"{pass_item.validity_days} days"
        # Get vehicle category name
        vehicle_category = VehicleCategory.query.get(pass_item.vehicle_category_id)
        pass_item.vehicle_type = vehicle_category.name if vehicle_category else 'Unknown'

    return render_template('overnight_vehicles_detail.html',
                         overnight_vehicles=overnight_passes,
                         from_date=from_date.strftime('%Y-%m-%dT%H:%M'),
                         to_date=to_date.strftime('%Y-%m-%dT%H:%M'))

@app.route('/api/clear-data', methods=['POST'])
def clear_data():
    try:
        # Delete all records from VehicleEntry
        VehicleEntry.query.delete()
        
        # Delete all records from OvernightPass
        OvernightPass.query.delete()
        
        # Commit the changes
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'All data cleared successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Error clearing data: {str(e)}'
        }), 500

@app.route('/api/entries/export')
def export_entries():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Get filter parameters
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    device_id = request.args.get('device_id')
    site = request.args.get('site')
    export_type = request.args.get('type', 'all')  # 'all', 'entries', or 'exits'

    # Convert string dates to datetime objects
    from_date = datetime.strptime(from_date, '%Y-%m-%dT%H:%M') if from_date else datetime.now() - timedelta(days=7)
    to_date = datetime.strptime(to_date, '%Y-%m-%dT%H:%M') if to_date else datetime.now()

    # Query the database with filters
    query = VehicleEntry.query.filter(
        VehicleEntry.entry_time >= from_date,
        VehicleEntry.entry_time <= to_date
    )

    # Apply device and site filters
    if device_id:
        query = query.filter(VehicleEntry.device_id == device_id)
    if site:
        query = query.filter(VehicleEntry.site == site)

    # Apply type filter
    if export_type == 'exits':
        query = query.filter(VehicleEntry.exit_time.isnot(None))
    elif export_type == 'entries':
        query = query.filter(VehicleEntry.exit_time.is_(None))

    entries = query.all()

    # Create CSV data
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Vehicle Number', 'Vehicle Type', 'Entry Time', 'Exit Time', 'Status', 'Amount Paid', 'Device', 'Location', 'Site'])
    
    # Write data rows
    for entry in entries:
        writer.writerow([
            entry.vehicle_number,
            entry.vehicle_type,
            entry.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            entry.exit_time.strftime('%Y-%m-%d %H:%M:%S') if entry.exit_time else '-',
            'Active' if not entry.exit_time else 'Exited',
            entry.amount_paid or 0,
            entry.device_id,
            entry.location,
            entry.site
        ])

    # Create the response
    output.seek(0)
    response = make_response(output.getvalue())
    filename = f"{export_type}_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}.csv"
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-type'] = 'text/csv'
    
    return response

@app.route('/api/overnight-passes/export')
def export_overnight_passes():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Get filter parameters
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    # Convert string dates to datetime objects
    from_date = datetime.strptime(from_date, '%Y-%m-%dT%H:%M') if from_date else datetime.now() - timedelta(days=7)
    to_date = datetime.strptime(to_date, '%Y-%m-%dT%H:%M') if to_date else datetime.now()

    # Query the database with filters
    query = OvernightPass.query.filter(
        OvernightPass.created_at >= from_date,
        OvernightPass.created_at <= to_date
    )

    passes = query.all()

    # Create CSV data
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Pass Name', 'Vehicle Type', 'Created At', 'Validity Days', 'Amount', 'Device', 'Location', 'Site', 'Status'])
    
    # Write data rows
    for pass_item in passes:
        vehicle_category = VehicleCategory.query.get(pass_item.vehicle_category_id)
        vehicle_type = vehicle_category.name if vehicle_category else 'Unknown'
        
        writer.writerow([
            pass_item.name,
            vehicle_type,
            pass_item.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            pass_item.validity_days,
            pass_item.amount,
            pass_item.device_id,
            pass_item.location,
            pass_item.site,
            pass_item.status
        ])

    # Create the response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename=overnight_passes_{from_date.strftime("%Y%m%d")}_{to_date.strftime("%Y%m%d")}.csv'
    response.headers['Content-type'] = 'text/csv'
    
    return response

@app.route('/vehicle-type-summary')
def vehicle_type_summary():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Get date parameters from request
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    device_id = request.args.get('device_id')
    site = request.args.get('site')

    # Parse dates if provided, otherwise use today's date
    if from_date and to_date:
        try:
            from_date = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            to_date = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
        except ValueError:
            # If date parsing fails, use today's date
            today = datetime.now().date()
            from_date = datetime.combine(today, datetime.min.time())
            to_date = datetime.combine(today, datetime.max.time())
    else:
        # Use today's date if no parameters provided
        today = datetime.now().date()
        from_date = datetime.combine(today, datetime.min.time())
        to_date = datetime.combine(today, datetime.max.time())

    # Get all unique vehicle types from entries
    vehicle_types = db.session.query(VehicleEntry.vehicle_type).distinct().all()
    vehicle_types = [v[0] for v in vehicle_types if v[0]]  # Remove None values
    
    # Prepare summary data for each vehicle type
    type_summary = []
    for vtype in vehicle_types:
        # Get entries for this vehicle type
        entries_query = VehicleEntry.query.filter(
            VehicleEntry.vehicle_type == vtype,
            VehicleEntry.entry_time >= from_date,
            VehicleEntry.entry_time <= to_date
        )

        if device_id:
            entries_query = entries_query.filter(VehicleEntry.device_id == device_id)
        if site:
            entries_query = entries_query.filter(VehicleEntry.site == site)

        entries = entries_query.all()
        
        # Calculate statistics
        total_entries = len(entries)
        active_vehicles = len([e for e in entries if e.exit_time is None])
        exited_vehicles = len([e for e in entries if e.exit_time is not None])
        total_revenue = sum(e.amount_paid or 0 for e in entries)

        # Get device and site information from the first entry
        device_id = entries[0].device_id if entries else 'N/A'
        location = entries[0].location if entries else 'N/A'
        site_name = entries[0].site if entries else 'N/A'

        type_summary.append({
            'name': vtype,
            'device_id': device_id,
            'location': location,
            'site': site_name,
            'total_entries': total_entries,
            'active_vehicles': active_vehicles,
            'exited_vehicles': exited_vehicles,
            'total_revenue': total_revenue
        })

    return render_template('vehicle_type_summary.html',
                         vehicle_types=type_summary,
                         from_date=from_date.strftime('%Y-%m-%dT%H:%M'),
                         to_date=to_date.strftime('%Y-%m-%dT%H:%M'))

@app.route('/api/vehicle-type-summary/export')
def export_vehicle_type_summary():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Get filter parameters
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    device_id = request.args.get('device_id')
    site = request.args.get('site')

    # Convert string dates to datetime objects
    from_date = datetime.strptime(from_date, '%Y-%m-%dT%H:%M') if from_date else datetime.now() - timedelta(days=7)
    to_date = datetime.strptime(to_date, '%Y-%m-%dT%H:%M') if to_date else datetime.now()

    # Get all vehicle types
    vehicle_types = VehicleCategory.query.all()
    
    # Create CSV data
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Vehicle Type', 'Total Entries', 'Active Vehicles', 'Exited Vehicles', 'Total Revenue'])
    
    # Write data rows
    for vtype in vehicle_types:
        # Get entries for this vehicle type
        entries_query = VehicleEntry.query.filter(
            VehicleEntry.vehicle_type == vtype.name,
            VehicleEntry.entry_time >= from_date,
            VehicleEntry.entry_time <= to_date
        )

        if device_id:
            entries_query = entries_query.filter(VehicleEntry.device_id == device_id)
        if site:
            entries_query = entries_query.filter(VehicleEntry.site == site)

        entries = entries_query.all()
        
        # Calculate statistics
        total_entries = len(entries)
        active_vehicles = len([e for e in entries if e.exit_time is None])
        exited_vehicles = len([e for e in entries if e.exit_time is not None])
        total_revenue = sum(e.amount_paid or 0 for e in entries)

        writer.writerow([
            vtype.name,
            total_entries,
            active_vehicles,
            exited_vehicles,
            total_revenue
        ])

    # Create the response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename=vehicle_type_summary_{from_date.strftime("%Y%m%d")}_{to_date.strftime("%Y%m%d")}.csv'
    response.headers['Content-type'] = 'text/csv'
    
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 