from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import logging
import random
import string
from flask_migrate import Migrate
from datetime import datetime
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
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

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
    # Get counts from database
    locations_count = Location.query.count()
    sites_count = Site.query.count()
    devices_count = Device.query.count()
    vehicle_categories_count = VehicleCategory.query.count()

    # Get recent activities
    recent_activities = []
    
    # Add recent locations
    recent_locations = Location.query.order_by(Location.created_at.desc()).limit(3).all()
    for loc in recent_locations:
        recent_activities.append({
            'icon': 'fas fa-map-marker-alt',
            'icon_bg': 'rgba(26, 35, 126, 0.1)',
            'icon_color': '#1a237e',
            'title': f'New location added: {loc.name}',
            'time': loc.created_at.strftime('%b %d, %Y %I:%M %p')
        })

    # Add recent sites
    recent_sites = Site.query.order_by(Site.created_at.desc()).limit(3).all()
    for site in recent_sites:
        recent_activities.append({
            'icon': 'fas fa-building',
            'icon_bg': 'rgba(33, 150, 243, 0.1)',
            'icon_color': '#2196f3',
            'title': f'New site added: {site.name} at {site.location.name}',
            'time': site.created_at.strftime('%b %d, %Y %I:%M %p')
        })

    # Add recent devices
    recent_devices = Device.query.order_by(Device.created_at.desc()).limit(3).all()
    for device in recent_devices:
        recent_activities.append({
            'icon': 'fas fa-microchip',
            'icon_bg': 'rgba(76, 175, 80, 0.1)',
            'icon_color': '#4caf50',
            'title': f'New device added: {device.device_id} at {device.site.name}',
            'time': device.created_at.strftime('%b %d, %Y %I:%M %p')
        })

    # Add recent vehicle categories
    recent_categories = VehicleCategory.query.order_by(VehicleCategory.created_at.desc()).limit(3).all()
    for category in recent_categories:
        recent_activities.append({
            'icon': 'fas fa-car',
            'icon_bg': 'rgba(255, 152, 0, 0.1)',
            'icon_color': '#ff9800',
            'title': f'New vehicle category added: {category.name}',
            'time': category.created_at.strftime('%b %d, %Y %I:%M %p')
        })

    # Sort activities by time
    recent_activities.sort(key=lambda x: x['time'], reverse=True)
    recent_activities = recent_activities[:5]  # Show only 5 most recent activities

    return render_template('dashboard.html',
                         locations_count=locations_count,
                         sites_count=sites_count,
                         devices_count=devices_count,
                         vehicle_categories_count=vehicle_categories_count,
                         recent_activities=recent_activities)

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
                printer_footer=printer_footer
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
            
            new_category = VehicleCategory(
                name=name,
                description=description,
                is_monthly_pass=is_monthly_pass,
                amount=amount,
                location_id=location_id,
                site_id=site_id,
                device_id=device_id
            )
            
            db.session.add(new_category)
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
        
        if request.method == 'POST':
            category.name = request.form.get('name')
            category.description = request.form.get('description')
            category.is_monthly_pass = 'is_monthly_pass' in request.form
            category.amount = float(request.form.get('amount'))
            category.location_id = request.form.get('location_id')
            category.site_id = request.form.get('site_id')
            category.device_id = request.form.get('device_id')
            category.status = request.form.get('status')
            
            db.session.commit()
            flash('Vehicle category updated successfully!', 'success')
            return redirect(url_for('vehicle_categories'))
        
        locations = Location.query.all()
        sites = Site.query.all()
        devices = Device.query.all()
        return render_template('vehicle_category_form.html', 
                             category=category,
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
                'start_time': interval.from_time,
                'end_time': interval.to_time,
                'amount': interval.amount
            } for interval in intervals]

            tariffs_data.append({
                'id': tariff.id,
                'name': tariff.name,
                'location_id': tariff.location_id,
                'site_id': tariff.site_id,
                'device_id': tariff.device_id,
                'vehicle_category_id': tariff.vehicle_category_id,
                'grace_time': tariff.grace_time,
                'status': tariff.status,
                'time_intervals': intervals_data
            })

        # Get all monthly passes for this location
        monthly_passes = VehicleCategory.query.filter_by(location_id=location.id, is_monthly_pass=True).all()
        passes_data = [{
            'id': cat.id,
            'name': cat.name,
            'vehicle_category_id': cat.id,
            'amount': cat.amount,
            'validity_days': 30,  # Assuming a default validity of 30 days
            'status': cat.status
        } for cat in monthly_passes]

        # Prepare response data
        response_data = {
            'device': {
                'id': device.id,
                'device_id': device.device_id,
                'device_type': device.device_type,
                'upi_id': device.upi_id,
                'status': device.status,
                'printer_header': device.printer_header,
                'printer_footer': device.printer_footer
            },
            'site': {
                'id': site.id,
                'name': site.name,
                'description': site.description,
                'status': site.status
            },
            'location': {
                'id': location.id,
                'name': location.name,
                'status': location.status
            },
            'vehicle_categories': categories_data,
            'tariffs': tariffs_data,
            'monthly_passes': passes_data
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
    locations = Location.query.all()
    return render_template('reports.html', locations=locations)

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
        
        # Validate required fields
        required_fields = ['vehicleNumber', 'vehicleType', 'transactionId', 'entryTime']
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

        # Create new vehicle entry
        new_entry = VehicleEntry(
            vehicle_number=data['vehicleNumber'],
            vehicle_type=data['vehicleType'],
            transaction_id=data['transactionId'],
            entry_time=datetime.fromisoformat(data['entryTime'].replace('Z', '+00:00')),
            qr_code=data.get('qrCode')
        )

        db.session.add(new_entry)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Vehicle entry recorded successfully',
            'data': {
                'id': new_entry.id,
                'vehicleNumber': new_entry.vehicle_number,
                'vehicleType': new_entry.vehicle_type,
                'transactionId': new_entry.transaction_id,
                'entryTime': new_entry.entry_time.isoformat(),
                'qrCode': new_entry.qr_code
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Error processing vehicle entry: {str(e)}'
        }), 500

@app.route('/api/vehicle-out', methods=['POST'])
def vehicle_exit():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['transactionId', 'exitTime']
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

        # Update vehicle entry with exit information
        vehicle_entry.exit_time = datetime.fromisoformat(data['exitTime'].replace('Z', '+00:00'))
        
        # Update payment information if provided
        if 'amountPaid' in data:
            vehicle_entry.amount_paid = data['amountPaid']
        if 'paymentStatus' in data:
            vehicle_entry.payment_status = data['paymentStatus']
        if 'paymentMethod' in data:
            vehicle_entry.payment_method = data['paymentMethod']
        if 'paymentReference' in data:
            vehicle_entry.payment_reference = data['paymentReference']

        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Vehicle exit recorded successfully',
            'data': {
                'id': vehicle_entry.id,
                'vehicleNumber': vehicle_entry.vehicle_number,
                'vehicleType': vehicle_entry.vehicle_type,
                'transactionId': vehicle_entry.transaction_id,
                'entryTime': vehicle_entry.entry_time.isoformat(),
                'exitTime': vehicle_entry.exit_time.isoformat(),
                'amountPaid': vehicle_entry.amount_paid,
                'paymentStatus': vehicle_entry.payment_status,
                'paymentMethod': vehicle_entry.payment_method,
                'paymentReference': vehicle_entry.payment_reference
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Error processing vehicle exit: {str(e)}'
        }), 500

def calculate_avg_stay_duration(transactions):
    if not transactions:
        return 0
    
    total_duration = sum(
        ((t.exit_time or datetime.now()) - t.entry_time).total_seconds() / 60
        for t in transactions
    )
    return round(total_duration / len(transactions), 2)

def calculate_occupancy_rate(transactions, location_id):
    if not location_id:
        return 0
    
    location = Location.query.get(location_id)
    if not location:
        return 0
    
    total_spaces = location.total_spaces
    if total_spaces == 0:
        return 0
    
    # Calculate average occupancy for the time period
    occupied_spaces = len(transactions)
    return round((occupied_spaces / total_spaces) * 100, 2)

def generate_revenue_by_category_chart(transactions):
    # Group transactions by vehicle category and calculate total revenue
    category_revenue = {}
    for t in transactions:
        category = VehicleCategory.query.get(t.vehicle_category_id)
        if category:
            category_name = category.name
            category_revenue[category_name] = category_revenue.get(category_name, 0) + (t.amount_paid or 0)

    return {
        'type': 'pie',
        'data': {
            'labels': list(category_revenue.keys()),
            'datasets': [{
                'data': list(category_revenue.values()),
                'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']
            }]
        }
    }

def generate_revenue_by_payment_chart(transactions):
    # Group transactions by payment method and calculate total revenue
    payment_revenue = {}
    for t in transactions:
        if t.payment_method:
            payment_revenue[t.payment_method] = payment_revenue.get(t.payment_method, 0) + (t.amount_paid or 0)

    return {
        'type': 'doughnut',
        'data': {
            'labels': list(payment_revenue.keys()),
            'datasets': [{
                'data': list(payment_revenue.values()),
                'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56']
            }]
        }
    }

def generate_transactions_by_hour_chart(transactions):
    # Group transactions by hour
    hourly_transactions = [0] * 24
    for t in transactions:
        hour = t.entry_time.hour
        hourly_transactions[hour] += 1

    return {
        'type': 'line',
        'data': {
            'labels': [f'{i}:00' for i in range(24)],
            'datasets': [{
                'label': 'Transactions',
                'data': hourly_transactions,
                'borderColor': '#36A2EB',
                'tension': 0.1
            }]
        }
    }

def generate_transactions_by_day_chart(transactions):
    # Group transactions by day of week
    daily_transactions = [0] * 7
    for t in transactions:
        day = t.entry_time.weekday()
        daily_transactions[day] += 1

    return {
        'type': 'bar',
        'data': {
            'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'datasets': [{
                'label': 'Transactions',
                'data': daily_transactions,
                'backgroundColor': '#36A2EB'
            }]
        }
    }

def generate_vehicle_category_chart(transactions):
    # Count transactions by vehicle category
    category_counts = {}
    for t in transactions:
        category = VehicleCategory.query.get(t.vehicle_category_id)
        if category:
            category_name = category.name
            category_counts[category_name] = category_counts.get(category_name, 0) + 1

    return {
        'type': 'pie',
        'data': {
            'labels': list(category_counts.keys()),
            'datasets': [{
                'data': list(category_counts.values()),
                'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']
            }]
        }
    }

def generate_top_vehicles_chart(transactions):
    # Count transactions by vehicle number
    vehicle_counts = {}
    for t in transactions:
        vehicle_counts[t.vehicle_number] = vehicle_counts.get(t.vehicle_number, 0) + 1

    # Get top 10 vehicles
    top_vehicles = sorted(vehicle_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        'type': 'bar',
        'data': {
            'labels': [v[0] for v in top_vehicles],
            'datasets': [{
                'label': 'Number of Visits',
                'data': [v[1] for v in top_vehicles],
                'backgroundColor': '#36A2EB'
            }]
        }
    }

def generate_revenue_by_location_chart(transactions):
    # Group transactions by location and calculate total revenue
    location_revenue = {}
    for t in transactions:
        device = Device.query.filter_by(device_id=t.device_id).first()
        if device and device.site and device.site.location:
            location_name = device.site.location.name
            location_revenue[location_name] = location_revenue.get(location_name, 0) + (t.amount_paid or 0)

    return {
        'type': 'bar',
        'data': {
            'labels': list(location_revenue.keys()),
            'datasets': [{
                'label': 'Revenue',
                'data': list(location_revenue.values()),
                'backgroundColor': '#36A2EB'
            }]
        }
    }

def generate_occupancy_by_location_chart(transactions):
    # Calculate occupancy rate for each location
    location_occupancy = {}
    for location in Location.query.all():
        location_transactions = [t for t in transactions if 
                               Device.query.filter_by(device_id=t.device_id).first() and
                               Device.query.filter_by(device_id=t.device_id).first().site and
                               Device.query.filter_by(device_id=t.device_id).first().site.location_id == location.id]
        
        if location.total_spaces > 0:
            occupancy_rate = (len(location_transactions) / location.total_spaces) * 100
            location_occupancy[location.name] = round(occupancy_rate, 2)

    return {
        'type': 'bar',
        'data': {
            'labels': list(location_occupancy.keys()),
            'datasets': [{
                'label': 'Occupancy Rate (%)',
                'data': list(location_occupancy.values()),
                'backgroundColor': '#36A2EB'
            }]
        }
    }

def generate_transactions_by_device_chart(transactions):
    # Group transactions by device
    device_transactions = {}
    for t in transactions:
        device = Device.query.filter_by(device_id=t.device_id).first()
        if device:
            device_name = f"Device {device.device_id}"
            device_transactions[device_name] = device_transactions.get(device_name, 0) + 1

    return {
        'type': 'bar',
        'data': {
            'labels': list(device_transactions.keys()),
            'datasets': [{
                'label': 'Transactions',
                'data': list(device_transactions.values()),
                'backgroundColor': '#36A2EB'
            }]
        }
    }

def generate_device_status_chart():
    # Get device status counts
    devices = Device.query.all()
    status_counts = {}
    for device in devices:
        status_counts[device.status] = status_counts.get(device.status, 0) + 1

    return {
        'type': 'doughnut',
        'data': {
            'labels': list(status_counts.keys()),
            'datasets': [{
                'data': list(status_counts.values()),
                'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56']
            }]
        }
    }

def generate_transactions_by_operator_chart(transactions):
    # Group transactions by operator
    operator_transactions = {}
    for t in transactions:
        operator_transactions[t.operator_id] = operator_transactions.get(t.operator_id, 0) + 1

    return {
        'type': 'bar',
        'data': {
            'labels': list(operator_transactions.keys()),
            'datasets': [{
                'label': 'Transactions',
                'data': list(operator_transactions.values()),
                'backgroundColor': '#36A2EB'
            }]
        }
    }

def generate_revenue_by_operator_chart(transactions):
    # Group transactions by operator and calculate total revenue
    operator_revenue = {}
    for t in transactions:
        operator_revenue[t.operator_id] = operator_revenue.get(t.operator_id, 0) + (t.amount_paid or 0)

    return {
        'type': 'bar',
        'data': {
            'labels': list(operator_revenue.keys()),
            'datasets': [{
                'label': 'Revenue',
                'data': list(operator_revenue.values()),
                'backgroundColor': '#36A2EB'
            }]
        }
    }

def generate_csv_report(start_date, end_date, location_id):
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

    # Create CSV data
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Transaction ID',
        'Vehicle Number',
        'Vehicle Category',
        'Entry Time',
        'Exit Time',
        'Duration (minutes)',
        'Amount Paid',
        'Payment Method',
        'Payment Status',
        'Location',
        'Site',
        'Device',
        'Operator'
    ])

    # Write data rows
    for t in transactions:
        device = Device.query.filter_by(device_id=t.device_id).first()
        site = device.site if device else None
        location = site.location if site else None
        category = VehicleCategory.query.get(t.vehicle_category_id)
        
        duration = ((t.exit_time or datetime.now()) - t.entry_time).total_seconds() / 60 if t.exit_time else None
        
        writer.writerow([
            t.transaction_id,
            t.vehicle_number,
            category.name if category else 'Unknown',
            t.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            t.exit_time.strftime('%Y-%m-%d %H:%M:%S') if t.exit_time else '',
            round(duration, 2) if duration else '',
            t.amount_paid or 0,
            t.payment_method or '',
            t.payment_status,
            location.name if location else 'Unknown',
            site.name if site else 'Unknown',
            device.device_id if device else 'Unknown',
            t.operator_id
        ])

    return output.getvalue()

@app.route('/api/reports/vehicle', methods=['GET'])
def vehicle_reports():
    try:
        # Get query parameters
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')
        vehicle_type = request.args.get('vehicleType')
        payment_status = request.args.get('paymentStatus')
        
        # Base query
        query = VehicleEntry.query
        
        # Apply filters
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(VehicleEntry.entry_time >= start_date)
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(VehicleEntry.entry_time <= end_date)
        if vehicle_type:
            query = query.filter(VehicleEntry.vehicle_type == vehicle_type)
        if payment_status:
            query = query.filter(VehicleEntry.payment_status == payment_status)
        
        # Get all matching records
        entries = query.all()
        
        # Calculate statistics
        total_entries = len(entries)
        total_exits = len([e for e in entries if e.exit_time])
        total_revenue = sum(e.amount_paid or 0 for e in entries)
        
        # Group by vehicle type
        vehicle_type_stats = {}
        for entry in entries:
            if entry.vehicle_type not in vehicle_type_stats:
                vehicle_type_stats[entry.vehicle_type] = {
                    'count': 0,
                    'revenue': 0
                }
            vehicle_type_stats[entry.vehicle_type]['count'] += 1
            vehicle_type_stats[entry.vehicle_type]['revenue'] += entry.amount_paid or 0
        
        # Group by payment method
        payment_method_stats = {}
        for entry in entries:
            if entry.payment_method:
                if entry.payment_method not in payment_method_stats:
                    payment_method_stats[entry.payment_method] = {
                        'count': 0,
                        'revenue': 0
                    }
                payment_method_stats[entry.payment_method]['count'] += 1
                payment_method_stats[entry.payment_method]['revenue'] += entry.amount_paid or 0
        
        # Calculate average stay duration
        completed_entries = [e for e in entries if e.exit_time]
        if completed_entries:
            total_duration = sum((e.exit_time - e.entry_time).total_seconds() / 3600 for e in completed_entries)
            avg_stay_duration = total_duration / len(completed_entries)
        else:
            avg_stay_duration = 0
        
        # Prepare response
        response_data = {
            'summary': {
                'totalEntries': total_entries,
                'totalExits': total_exits,
                'totalRevenue': total_revenue,
                'averageStayDuration': round(avg_stay_duration, 2)
            },
            'vehicleTypeStats': vehicle_type_stats,
            'paymentMethodStats': payment_method_stats,
            'transactions': [{
                'id': entry.id,
                'vehicleNumber': entry.vehicle_number,
                'vehicleType': entry.vehicle_type,
                'transactionId': entry.transaction_id,
                'entryTime': entry.entry_time.isoformat(),
                'exitTime': entry.exit_time.isoformat() if entry.exit_time else None,
                'amountPaid': entry.amount_paid,
                'paymentStatus': entry.payment_status,
                'paymentMethod': entry.payment_method,
                'paymentReference': entry.payment_reference
            } for entry in entries]
        }
        
        return jsonify({
            'status': 'success',
            'data': response_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error generating report: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(host = '0.0.0.0' ,port = 5000, debug=True) 