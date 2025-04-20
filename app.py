

import os
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
from flask import get_flashed_messages  # Add this import
import csv
from flask import Response
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import date, datetime
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
from datetime import datetime

now = datetime.now()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:parag@localhost:3306/Transtrack'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max per file
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(80), nullable=False)
    theme = db.Column(db.String(80), default="light")
    profile_photo = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(20), default='user')  # Add this line
    drivers = db.relationship('Driver', backref='user', lazy=True)
    vehicles = db.relationship('Vehicle', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'


class Driver(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(20), unique=True, nullable=False)
    salary = db.Column(db.Float, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    withdrawals = db.relationship('Withdrawal', backref='driver', lazy=True)
    status = db.Column(db.String(20), default='pending')  # Add this line
    self_photo = db.Column(db.String(100))  # Store filename of self-photo
    driving_license = db.Column(db.String(100))  # Store filename of driving license
    aadhaar_card = db.Column(db.String(100))  # Store filename of Aadhaar card

    def __repr__(self):
        return '<Driver %r>' % self.name

class Withdrawal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'), nullable=False)

    def __repr__(self):
        return '<Withdrawal %r>' % self.amount

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    trip_from = db.Column(db.String(100), nullable=False)
    trip_to = db.Column(db.String(100), nullable=False)
    income = db.Column(db.Float, nullable=False)
    expense = db.Column(db.Float, nullable=False)
    diesel_amount = db.Column(db.Float, nullable=False)
    expense_details = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return '<Expense %r>' % self.id

    @property
    def profit(self):
        return self.income - self.expense - self.diesel_amount

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    capacity = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rc_book_photo = db.Column(db.String(100))  # Store filename of RC book photo
    status = db.Column(db.String(20), default='pending')  # Status: pending, approved, rejected
    is_archived = db.Column(db.Boolean, default=False)  # New column for archiving vehicles

    def __repr__(self):
        return '<Vehicle %r>' % self.model



class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), default='general')  # Add this line

    def __repr__(self):
        return '<Notification %r>' % self.message
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    booking_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # Add this line

    # Define relationships
    user = db.relationship('User', backref='bookings')  # Add this line
    vehicle = db.relationship('Vehicle', backref='bookings')

    def __repr__(self):
        return '<Booking %r>' % self.id

with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier')  # Accept both username and email
        password = request.form.get('password')

        if not identifier or not password:
            flash('Both fields are required.', 'error')
            return redirect(url_for('login'))

        # Check if user exists (by username or email)
        user = User.query.filter((User.username == identifier) | (User.id == identifier)).first()

        if user and user.password == password:  # Consider hashing for security
            session['username'] = user.username
            flash('Login successful.', 'success')
            return redirect(url_for('profile', username=user.username))
        else:
            flash('Invalid username or password.', 'error')
            return redirect(url_for('login'))
        get_flashed_messages()


    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']       # Capture email
        phone = request.form['phone']       # Capture phone number
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists! Please choose a different one.', 'error')
            return redirect(url_for('register'))

        # Create new user with email and phone fields
        new_user = User(username=username, email=email, phone=phone, password=password)
        db.session.add(new_user)

        try:
            db.session.commit()
            flash('Registration successful. You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while registering. Try again.', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')




@app.route('/profile/<username>', methods=['GET', 'POST'])
def profile(username):
    if 'username' not in session or session['username'] != username:
        flash('You need to log in first.', 'error')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=username).first()

    if request.method == 'POST':
        theme = request.form['theme']
        user.theme = theme
        db.session.commit()
        flash('Theme changed successfully.', 'success')

        return redirect(url_for('profile', username=username))

    return render_template('profile.html', user=user)

@app.route('/manage_drivers', methods=['GET', 'POST'])
def manage_drivers():
    if 'username' not in session:
        flash('Please login to manage drivers.', 'error')
        return redirect(url_for('login'))

    user_id = User.query.filter_by(username=session['username']).first().id
    drivers = Driver.query.filter_by(user_id=user_id, status='approved').all()  # Only show approved drivers

    # Rest of the code remains the same...

    if request.method == 'POST':
        selected_driver_id = session.get('selected_driver_id')
        if 'select_driver' in request.form:
            driver_id = request.form.get('driver_id')
            if driver_id:
                selected_driver = Driver.query.get(driver_id)
                if selected_driver:
                    session['selected_driver_id'] = selected_driver.id
                else:
                    flash('Driver not found.', 'error')
            else:
                flash('Please select a driver first.', 'error')
        
        elif 'add_salary' in request.form:
            if selected_driver_id:
                selected_driver = Driver.query.get(selected_driver_id)
                if selected_driver:
                    salary_amount = float(request.form['salary_amount'])
                    selected_driver.salary += salary_amount
                    db.session.commit()
                    flash(f'Salary added successfully for {selected_driver.name}.', 'success')
                else:
                    flash('Selected driver not found.', 'error')
            else:
                flash('Please select a driver first.', 'error')

        elif 'add_withdrawal' in request.form:
            if selected_driver_id:
                selected_driver = Driver.query.get(selected_driver_id)
                if selected_driver:
                    withdrawal_amount = float(request.form['withdrawal_amount'])
                    withdrawal_date = request.form['withdrawal_date']
                    new_withdrawal = Withdrawal(amount=withdrawal_amount, date=withdrawal_date, driver_id=selected_driver.id)
                    db.session.add(new_withdrawal)
                    db.session.commit()
                    flash(f'Withdrawal of {withdrawal_amount} added successfully for {selected_driver.name} on {withdrawal_date}.', 'success')
                else:
                    flash('Selected driver not found.', 'error')
            else:
                flash('Please select a driver first.', 'error')

        elif 'remaining_salary' in request.form:
            if selected_driver_id:
                selected_driver = Driver.query.get(selected_driver_id)
                if selected_driver:
                    total_withdrawals = sum(w.amount for w in selected_driver.withdrawals)
                    remaining_salary = selected_driver.salary - total_withdrawals
                    flash(f'The remaining salary for {selected_driver.name} is {remaining_salary}.', 'success')
                    session['remaining_salary'] = remaining_salary
                else:
                    flash('Selected driver not found.', 'error')
            else:
                flash('Please select a driver first.', 'error')

    selected_driver_id = session.get('selected_driver_id')
    selected_driver = Driver.query.get(selected_driver_id) if selected_driver_id else None
    remaining_salary = session.get('remaining_salary')

    return render_template('manage_drivers.html', drivers=drivers, selected_driver=selected_driver, remaining_salary=remaining_salary)

@app.route('/register_driver', methods=['GET', 'POST'])
def register_driver():
    if 'username' not in session:
        flash('Please login to register a driver.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        license_number = request.form['license_number']
        user_id = User.query.filter_by(username=session['username']).first().id

        # Handle File Uploads
        self_photo = request.files['self_photo']
        driving_license = request.files['driving_license']
        aadhaar_card = request.files['aadhaar_card']

        if not (self_photo and driving_license and aadhaar_card):
            flash('All files must be uploaded!', 'error')
            return redirect(url_for('register_driver'))

        # Secure filenames
        self_photo_filename = secure_filename(f"{name}_self_photo.jpg")
        driving_license_filename = secure_filename(f"{name}_driving_license.jpg")
        aadhaar_card_filename = secure_filename(f"{name}_aadhaar_card.jpg")

        # Save files
        self_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], self_photo_filename))
        driving_license.save(os.path.join(app.config['UPLOAD_FOLDER'], driving_license_filename))
        aadhaar_card.save(os.path.join(app.config['UPLOAD_FOLDER'], aadhaar_card_filename))

        # Store in database with 'pending' status and document filenames
        driver = Driver(
            name=name,
            license_number=license_number,
            user_id=user_id,
            status='pending',  # Set status to pending
            self_photo=self_photo_filename,  # Store self-photo filename
            driving_license=driving_license_filename,  # Store driving license filename
            aadhaar_card=aadhaar_card_filename  # Store Aadhaar card filename
        )
        db.session.add(driver)
        db.session.commit()

        # Notify the admin
        admin = User.query.filter_by(username='Admin@123').first()
        if admin:
            notification = Notification(
                message=f"New driver registration pending: {name} (License: {license_number}).",
                user_id=admin.id
            )
            db.session.add(notification)
            db.session.commit()

        flash('Driver registration submitted for admin approval.', 'success')
        return redirect(url_for('manage_drivers'))

    return render_template('register_driver.html')

@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/expense_tracker', methods=['GET', 'POST'])
def expense_tracker():
    if 'username' not in session:
        flash('Please login to track expenses.', 'error')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()

    if request.method == 'POST':
        trip_from = request.form['trip_from']
        trip_to = request.form['trip_to']
        income = float(request.form['income'])
        expense = float(request.form['expense'])
        diesel_amount = float(request.form['diesel_amount'])
        expense_details = request.form['expense_details']
        expense_date = request.form['date']

        new_expense = Expense(
            date=expense_date,
            trip_from=trip_from,
            trip_to=trip_to,
            income=income,
            expense=expense,
            diesel_amount=diesel_amount,
            expense_details=expense_details,
            user_id=user.id
        )
        db.session.add(new_expense)
        db.session.commit()
        flash('Expense added successfully.', 'success')
        return redirect(url_for('expense_tracker'))

    return render_template('expense_tracker.html', user=user)

@app.route('/show_expenses')
def show_expenses():
    if 'username' not in session:
        flash('Please login to view expenses.', 'error')
        return redirect(url_for('login'))

    user_id = User.query.filter_by(username=session['username']).first().id
    expenses = Expense.query.filter_by(user_id=user_id).all()
    return render_template('show_expenses.html', expenses=expenses)

@app.route('/profit_of_trip/<int:expense_id>', methods=['GET'])
def profit_of_trip(expense_id):
    if 'username' not in session:
        flash('Please login to view the profit of a trip.', 'error')
        return redirect(url_for('login'))

    expense = Expense.query.get(expense_id)
    if expense is None:
        flash('Expense not found.', 'error')
        return redirect(url_for('show_expenses'))

    profit = expense.profit
    if profit < 0:
        message = "You got a loss"
        profit_style = "color: tomato;"
    else:
        message = ""
        profit_style = "color: black;"

    return render_template('profit_of_trip.html', expense=expense, profit=profit, message=message, profit_style=profit_style)

@app.route('/get_expense_data')
def get_expense_data():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized access"}), 401

    user_id = User.query.filter_by(username=session['username']).first().id
    expenses = Expense.query.filter_by(user_id=user_id).all()

    data = {
        "labels": [expense.date.strftime('%Y-%m-%d') for expense in expenses],
        "income": [expense.income for expense in expenses],
        "expense": [expense.expense + expense.diesel_amount for expense in expenses],
        "profit": [expense.profit for expense in expenses]
    }

    return jsonify(data)

@app.route('/add_vehicle', methods=['GET', 'POST'])
def add_vehicle():
    if 'username' not in session:
        flash('Please login to add a vehicle.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        type = request.form['type']
        model = request.form['model']
        registration_number = request.form['registration_number']
        capacity = float(request.form['capacity'])
        user_id = User.query.filter_by(username=session['username']).first().id

        # Check if vehicle with this registration number already exists
        existing_vehicle = Vehicle.query.filter_by(registration_number=registration_number).first()
        if existing_vehicle:
            flash('This vehicle number is already registered in our database.', 'error')
            return redirect(url_for('add_vehicle'))

        # Handle RC Book Photo Upload
        if 'rc_book_photo' not in request.files:
            flash('RC Book Photo is required.', 'error')
            return redirect(url_for('add_vehicle'))

        rc_book_photo = request.files['rc_book_photo']
        if rc_book_photo.filename == '':
            flash('No file selected for RC Book Photo.', 'error')
            return redirect(url_for('add_vehicle'))

        # Secure filename
        rc_book_photo_filename = secure_filename(f"{registration_number}_rc_book.jpg")
        rc_book_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], rc_book_photo_filename))

        # Create new vehicle with 'pending' status
        vehicle = Vehicle(
            type=type,
            model=model,
            registration_number=registration_number,
            capacity=capacity,
            user_id=user_id,
            rc_book_photo=rc_book_photo_filename,
            status='pending'
        )
        db.session.add(vehicle)
        db.session.commit()

        # Notify the admin
        admin = User.query.filter_by(username='Admin@123').first()
        if admin:
            notification = Notification(
                message=f"New vehicle registration pending: {model} (Registration: {registration_number}).",
                user_id=admin.id
            )
            db.session.add(notification)
            db.session.commit()

        flash('Vehicle registration submitted for admin approval.', 'success')
        return redirect(url_for('profile', username=session['username']))

    return render_template('add_vehicle.html')

# @app.route('/api/vehicles', methods=['GET'])
# def get_vehicles():
#     vehicles = Vehicle.query.all()
#     return jsonify([{
#         'id': vehicle.id,
#         'type': vehicle.type,
#         'model': vehicle.model,
#         'registration_number': vehicle.registration_number,
#         'capacity': vehicle.capacity
#     } for vehicle in vehicles])
@app.route('/api/request_booking/<int:vehicle_id>', methods=['POST'])
def request_booking(vehicle_id):
    if 'username' not in session:
        return jsonify({'message': 'You must log in to request a booking.', 'status': 'error'})

    vehicle = Vehicle.query.get_or_404(vehicle_id)
    owner = User.query.get(vehicle.user_id)
    user = User.query.filter_by(username=session['username']).first()

    notification = Notification(
        message=f"{user.username} wants to book your vehicle ({vehicle.model}). Confirm?",
        user_id=owner.id,
        type='booking_request'  # Ensure the type is set correctly
    )
    db.session.add(notification)
    db.session.commit()

    return jsonify({'message': 'Booking request sent to the owner for confirmation.', 'status': 'info'})

@app.route('/api/confirm_booking/<int:notification_id>', methods=['POST'])
def confirm_booking(notification_id):
    if 'username' not in session:
        return jsonify({'message': 'Unauthorized action.', 'status': 'error'}), 401

    notification = Notification.query.get_or_404(notification_id)
    owner = User.query.get(notification.user_id)

    if session['username'] != owner.username:
        return jsonify({'message': 'Unauthorized action.', 'status': 'error'}), 403

    try:
        # Extract username from message (first word before "wants")
        requesting_username = notification.message.split(' ')[0]
        requesting_user = User.query.filter_by(username=requesting_username).first()
        
        if not requesting_user:
            return jsonify({'message': 'Requesting user not found.', 'status': 'error'}), 404

        # Find the first available vehicle owned by the notification recipient
        vehicle = Vehicle.query.filter_by(user_id=owner.id, is_archived=False).first()
        
        if vehicle:
            # Create booking
            booking = Booking(
                user_id=requesting_user.id,
                vehicle_id=vehicle.id,
                booking_date=datetime.now(),
                status='approved'
            )
            db.session.add(booking)
            
            # Archive the vehicle
            vehicle.is_archived = True
            
            # Create confirmation notification
            confirmation_notification = Notification(
                message=f"Your booking for {vehicle.model} has been confirmed by {owner.username}.",
                user_id=requesting_user.id,
                type='booking_confirmation'
            )
            db.session.add(confirmation_notification)
            
            # Remove the original request
            db.session.delete(notification)
            db.session.commit()
            
            return jsonify({'message': 'Booking confirmed successfully!', 'status': 'success'})
        
        return jsonify({'message': 'No available vehicle found.', 'status': 'error'}), 404
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}', 'status': 'error'}), 500

@app.route('/api/reject_booking/<int:notification_id>', methods=['POST'])
def reject_booking(notification_id):
    if 'username' not in session:
        return jsonify({'message': 'Unauthorized action.', 'status': 'error'}), 401

    notification = Notification.query.get_or_404(notification_id)
    owner = User.query.get(notification.user_id)

    if session['username'] != owner.username:
        return jsonify({'message': 'Unauthorized action.', 'status': 'error'}), 403

    try:
        # Extract username from message (first word before "wants")
        requesting_username = notification.message.split(' ')[0]
        requesting_user = User.query.filter_by(username=requesting_username).first()
        
        if requesting_user:
            # Find the vehicle mentioned in the notification
            vehicle_model = notification.message.split('(')[1].split(')')[0]
            vehicle = Vehicle.query.filter_by(model=vehicle_model, user_id=owner.id).first()
            
            if vehicle:
                # Create rejection notification
                rejection_notification = Notification(
                    message=f"Your booking for {vehicle.model} has been rejected by {owner.username}.",
                    user_id=requesting_user.id,
                    type='booking_rejection'
                )
                db.session.add(rejection_notification)
            
            # Remove the original request
            db.session.delete(notification)
            db.session.commit()
            
            return jsonify({'message': 'Booking rejected successfully!', 'status': 'success'})
        
        return jsonify({'message': 'Requesting user not found.', 'status': 'error'}), 404
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}', 'status': 'error'}), 500
@app.route('/api/user_notifications')
def user_notifications():
    if 'username' not in session:
        return jsonify([])  # Return an empty list if not logged in

    user = User.query.filter_by(username=session['username']).first()
    notifications = Notification.query.filter_by(user_id=user.id, type='vehicle_approval').all()  # Filter by type

    return jsonify([{"id": n.id, "message": n.message} for n in notifications])

@app.route('/pending_requests')
def pending_requests():
    if 'username' not in session:
        flash('You must log in to view pending requests.', 'error')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    notifications = Notification.query.filter_by(user_id=user.id, type='booking_request').all()

    return render_template('pending_requests.html', notifications=notifications)

@app.route('/api/pending_requests')
def api_pending_requests():
    if 'username' not in session:
        return jsonify([])

    user = User.query.filter_by(username=session['username']).first()
    notifications = Notification.query.filter_by(user_id=user.id, type='booking_request').all()
    
    return jsonify([{
        "id": n.id,
        "message": n.message
    } for n in notifications])

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': notification.id,
        'message': notification.message
    } for notification in notifications])

@app.route('/book/<int:vehicle_id>', methods=['GET', 'POST'])
def book_vehicle(vehicle_id):
    if 'username' not in session:
        flash('You must log in to book a vehicle.', 'danger')
        return redirect(url_for('login'))

    vehicle = Vehicle.query.get_or_404(vehicle_id)
    owner = User.query.get(vehicle.user_id)
    user = User.query.filter_by(username=session['username']).first()

    if request.method == 'POST':
        # Get all form data
        pickup_date = request.form.get('pickup_date')
        pickup_location = request.form.get('pickup_location')
        destination = request.form.get('destination')
        cargo_details = request.form.get('cargo_details')
        special_requirements = request.form.get('special_requirements')

        # Create detailed message
        message = (
            f"{user.username} wants to book your vehicle ({vehicle.model}).\n"
            f"Pickup Date: {pickup_date}\n"
            f"Pickup Location: {pickup_location}\n"
            f"Destination: {destination}\n"
            f"Cargo Details: {cargo_details}\n"
            f"Special Requirements: {special_requirements or 'None'}"
        )

        notification = Notification(
            message=message,
            user_id=owner.id,
            type='booking_request'
        )
        db.session.add(notification)
        db.session.commit()

        flash('Booking request sent to the owner for confirmation.', 'info')
        return redirect(url_for('profile', username=user.username))

    return render_template('book_vehicle.html', vehicle=vehicle, owner=owner, now=datetime.now())


@app.route('/api/book/<int:vehicle_id>', methods=['POST'])
def book_vehicle_api(vehicle_id):
    if 'username' not in session:
        return {'message': 'You must log in to book a vehicle.', 'status': 'error'}

    vehicle = Vehicle.query.get_or_404(vehicle_id)
    user = User.query.filter_by(username=session['username']).first()

    booking_date = datetime.now()
    booking = Booking(user_id=user.id, vehicle_id=vehicle.id, booking_date=booking_date)
    db.session.add(booking)
    db.session.commit()
    return {'message': 'Vehicle booked successfully!', 'status': 'success'}

@app.route('/api/vehicles')
def get_vehicles():
    if 'username' not in session:
        return jsonify([])  # Return empty list if not logged in

    # Fetch all approved vehicles that are not archived
    vehicles = Vehicle.query.filter_by(status='approved', is_archived=False).all()
    
    vehicle_list = []
    for vehicle in vehicles:
        vehicle_list.append({
            'id': vehicle.id,
            'type': vehicle.type,
            'model': vehicle.model,
            'registration_number': vehicle.registration_number,
            'capacity': vehicle.capacity,
            'owner': vehicle.user.username  # Access the owner's username via the relationship
        })
    
    return jsonify(vehicle_list)  # Ensure the response is JSON

@app.route('/view_vehicles')
def view_vehicles():
    if 'username' not in session:
        flash('Please login to view vehicles.', 'error')
        return redirect(url_for('login'))

    user_id = User.query.filter_by(username=session['username']).first().id
    vehicles = Vehicle.query.filter_by(user_id=user_id, status='approved').all()
    return render_template('view_vehicles.html', vehicles=vehicles)

@app.route('/notifications')
def notifications():
    if 'username' not in session:
        flash('You must log in to view notifications.', 'danger')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()

    return render_template('notifications.html', user=user)

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Query the database for the admin user
        admin_user = User.query.filter_by(username=username, role='admin').first()

        # Check if the user exists and the password matches
        if admin_user and admin_user.password == password:
            # Set the admin session
            session['admin'] = True
            flash('Admin login successful.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Incorrect username or password', 'error')
            return redirect(url_for('admin_login'))

    # Clear any existing flash messages when rendering the login page
    get_flashed_messages()
    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin' not in session:
        flash('You must log in as admin.', 'danger')
        return redirect(url_for('admin_login'))
    
    return render_template('admin_dashboard.html')
@app.route('/api/get_users')
def get_users():
    if 'admin' not in session:
        return jsonify({'message': 'Unauthorized access'}), 403

    users = User.query.all()
    return jsonify([{'id': user.id, 'username': user.username} for user in users])
# @app.route('/api/delete_user/<int:user_id>', methods=['DELETE'])
@app.route('/api/delete_user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    if 'admin' not in session:
        return jsonify({'message': 'Unauthorized access', 'status': 'error'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found', 'status': 'error'}), 404

    try:
        # Step 1: Delete all related notifications
        Notification.query.filter_by(user_id=user.id).delete()

        # Step 2: Delete all bookings related to the user
        Booking.query.filter_by(user_id=user.id).delete()

        # Step 3: Delete all expenses related to the user
        Expense.query.filter_by(user_id=user.id).delete()

        # Step 4: Get all vehicles owned by the user
        vehicles = Vehicle.query.filter_by(user_id=user.id).all()
        for vehicle in vehicles:
            # Step 5: Delete bookings linked to each vehicle
            Booking.query.filter_by(vehicle_id=vehicle.id).delete()

        # Step 6: Delete withdrawals linked to drivers under this user
        drivers = Driver.query.filter_by(user_id=user.id).all()
        for driver in drivers:
            Withdrawal.query.filter_by(driver_id=driver.id).delete()

        # Step 7: Delete drivers
        Driver.query.filter_by(user_id=user.id).delete()

        # Step 8: Delete vehicles
        Vehicle.query.filter_by(user_id=user.id).delete()

        # Step 9: Finally, delete the user
        db.session.delete(user)
        db.session.commit()

        return jsonify({'message': 'User deleted successfully', 'status': 'success'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}', 'status': 'error'}), 500

    
@app.route('/api/generate_report')
def generate_report():
    if 'admin' not in session:
        return jsonify({'message': 'Unauthorized access', 'status': 'error'}), 403

    report_type = request.args.get('type', 'users')
    
    try:
        # Create a buffer for the PDF
        buffer = BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Add TransTrack header
        elements.append(Paragraph("TransTrack Official Report", styles['Title']))
        elements.append(Paragraph(f"Report Type: {report_type.capitalize()} Report", styles['Heading2']))
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        elements.append(Spacer(1, 0.25 * inch))
        
        # Prepare data based on report type
        if report_type == 'users':
            data = [["ID", "Username", "Email", "Phone", "Vehicles", "Drivers"]]
            users = User.query.all()
            for user in users:
                vehicles = Vehicle.query.filter_by(user_id=user.id).all()
                drivers = Driver.query.filter_by(user_id=user.id).all()
                
                vehicle_info = "\n".join([f"{v.model} ({v.registration_number})" for v in vehicles])
                driver_info = "\n".join([f"{d.name} ({d.license_number})" for d in drivers])
                
                data.append([
                    str(user.id),
                    user.username,
                    user.email,
                    user.phone,
                    vehicle_info if vehicle_info else "None",
                    driver_info if driver_info else "None"
                ])
                
        elif report_type == 'drivers':
            data = [["ID", "Name", "License", "Status", "User", "Salary", "Withdrawals"]]
            drivers = Driver.query.all()
            for driver in drivers:
                user = User.query.get(driver.user_id)
                withdrawals = sum(w.amount for w in driver.withdrawals)
                
                data.append([
                    str(driver.id),
                    driver.name,
                    driver.license_number,
                    driver.status,
                    f"{user.username} (ID: {user.id})",
                    f"₹{driver.salary:,.2f}",
                    f"₹{withdrawals:,.2f}"
                ])
                
        elif report_type == 'vehicles':
            data = [["ID", "Model", "Type", "Reg No.", "Capacity", "Status", "Owner", "Availability"]]
            vehicles = Vehicle.query.all()
            for vehicle in vehicles:
                user = User.query.get(vehicle.user_id)
                
                data.append([
                    str(vehicle.id),
                    vehicle.model,
                    vehicle.type,
                    vehicle.registration_number,
                    f"{vehicle.capacity} tons",
                    vehicle.status,
                    f"{user.username} (ID: {user.id})",
                    "Booked" if vehicle.is_archived else "Available"
                ])
        else:
            return jsonify({'message': 'Invalid report type', 'status': 'error'}), 400

        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(table)
        doc.build(elements)
        
        # Get PDF content from buffer
        pdf = buffer.getvalue()
        buffer.close()
        
        # Create response
        response = Response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=TransTrack_{report_type}_report.pdf'
        return response
        
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}', 'status': 'error'}), 500
    
@app.route('/admin/verify_drivers', methods=['GET', 'POST'])
def verify_drivers():
    if 'admin' not in session:
        flash('You must log in as admin.', 'danger')
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        driver_id = request.form.get('driver_id')
        action = request.form.get('action')  # 'approve' or 'reject'

        driver = Driver.query.get(driver_id)
        if driver:
            if action == 'approve':
                driver.status = 'approved'
                message = f"Your driver registration for {driver.name} has been approved."
            elif action == 'reject':
                driver.status = 'rejected'
                message = f"Your driver registration for {driver.name} has been rejected."
            
            # Notify the user
            notification = Notification(
                message=message,
                user_id=driver.user_id
            )
            db.session.add(notification)
            db.session.commit()

            flash(message, 'success' if action == 'approve' else 'warning')
        else:
            flash('Driver not found.', 'error')

    pending_drivers = Driver.query.filter_by(status='pending').all()
    return render_template('verify_drivers.html', pending_drivers=pending_drivers)


@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        flash('You need to log in first.', 'error')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()

    if request.method == 'POST':
        # Update username, email, and phone
        new_username = request.form.get('username')
        new_email = request.form.get('email')
        new_phone = request.form.get('phone')

        # Check if the new username is already taken (if changed)
        if new_username != user.username:
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user:
                flash('Username already exists! Please choose a different one.', 'error')
                return redirect(url_for('edit_profile'))

        # Update profile photo if uploaded
        if 'profile_photo' in request.files:
            profile_photo = request.files['profile_photo']
            if profile_photo.filename != '':
                # Secure the filename
                profile_photo_filename = secure_filename(f"{new_username}_profile_photo.jpg")
                profile_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], profile_photo_filename))
                user.profile_photo = profile_photo_filename
            else:
                # If no file is uploaded, keep the existing profile photo (or set to NULL if none exists)
                pass
        else:
            # If no file input is provided, keep the existing profile photo (or set to NULL if none exists)
            pass

        # Update user details
        user.username = new_username
        user.email = new_email
        user.phone = new_phone

        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profile', username=user.username))

    return render_template('edit_profile.html', user=user)
@app.route('/api/user_profile')
def user_profile():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized access"}), 401

    user = User.query.filter_by(username=session['username']).first()
    return jsonify({
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "profile_photo": url_for('static', filename='uploads/' + user.profile_photo) if user.profile_photo else None
    })

@app.route('/admin/verify_vehicles', methods=['GET', 'POST'])
def verify_vehicles():
    if 'admin' not in session:
        flash('You must log in as admin.', 'danger')
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        action = request.form.get('action')  # 'approve' or 'reject'

        vehicle = Vehicle.query.get(vehicle_id)
        if vehicle:
            if action == 'approve':
                vehicle.status = 'approved'
                message = f"Your vehicle registration for {vehicle.model} has been approved."
            elif action == 'reject':
                vehicle.status = 'rejected'
                message = f"Your vehicle registration for {vehicle.model} has been rejected."
            
            # Notify the user with a specific type
            notification = Notification(
                message=message,
                user_id=vehicle.user_id,
                type='vehicle_approval'  # Set the type
            )
            db.session.add(notification)
            db.session.commit()

            flash(message, 'success' if action == 'approve' else 'warning')
        else:
            flash('Vehicle not found.', 'error')

    pending_vehicles = Vehicle.query.filter_by(status='pending').all()
    return render_template('verify_vehicles.html', pending_vehicles=pending_vehicles)


# @app.route('/delete_vehicle/<int:vehicle_id>', methods=['POST'])
# def delete_vehicle(vehicle_id):
#     if 'username' not in session:
#         flash('You must log in to delete a vehicle.', 'error')
#         return redirect(url_for('login'))

#     vehicle = Vehicle.query.get(vehicle_id)
#     if not vehicle:
#         flash('Vehicle not found.', 'error')
#         return redirect(url_for('view_vehicles'))

#     # Check if the vehicle belongs to the logged-in user
#     user = User.query.filter_by(username=session['username']).first()
#     if vehicle.user_id != user.id:
#         flash('You do not have permission to delete this vehicle.', 'error')
#         return redirect(url_for('view_vehicles'))

#     try:
#         # Delete the vehicle
#         db.session.delete(vehicle)
#         db.session.commit()
#         flash('Vehicle deleted successfully.', 'success')
#     except Exception as e:
#         db.session.rollback()
#         flash('An error occurred while deleting the vehicle.', 'error')

#     return redirect(url_for('view_vehicles'))

@app.route('/archive_vehicle/<int:vehicle_id>', methods=['POST'])
def archive_vehicle(vehicle_id):
    if 'username' not in session:
        flash('You must log in to archive a vehicle.', 'error')
        return redirect(url_for('login'))

    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        flash('Vehicle not found.', 'error')
        return redirect(url_for('view_vehicles'))

    # Check if the vehicle belongs to the logged-in user
    user = User.query.filter_by(username=session['username']).first()
    if vehicle.user_id != user.id:
        flash('You do not have permission to archive this vehicle.', 'error')
        return redirect(url_for('view_vehicles'))

    try:
        # Archive the vehicle
        vehicle.is_archived = True
        db.session.commit()
        flash('Vehicle archived successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while archiving the vehicle.', 'error')

    return redirect(url_for('view_vehicles'))


@app.route('/unarchive_vehicle/<int:vehicle_id>', methods=['POST'])
def unarchive_vehicle(vehicle_id):
    if 'username' not in session:
        flash('You must log in to unarchive a vehicle.', 'error')
        return redirect(url_for('login'))

    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        flash('Vehicle not found.', 'error')
        return redirect(url_for('view_vehicles'))

    # Check if the vehicle belongs to the logged-in user
    user = User.query.filter_by(username=session['username']).first()
    if vehicle.user_id != user.id:
        flash('You do not have permission to unarchive this vehicle.', 'error')
        return redirect(url_for('view_vehicles'))

    try:
        # Unarchive the vehicle
        vehicle.is_archived = False
        db.session.commit()
        flash('Vehicle unarchived successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while unarchiving the vehicle.', 'error')

    return redirect(url_for('view_vehicles'))

@app.route('/report_options')
def report_options():
    if 'admin' not in session:
        flash('You must log in as admin.', 'danger')
        return redirect(url_for('admin_login'))
    return render_template('report_options.html')

with app.app_context():
    admin_user = User.query.filter_by(username='Admin@123').first()
    if not admin_user:
        admin_user = User(
            username='Admin@123',
            email='admin@example.com',
            phone='1234567890',
            password='Admin@123',  # Use a secure password
            role='admin'  # Set the role to 'admin'
        )
        db.session.add(admin_user)
        db.session.commit()

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'username' not in session:
        flash('You need to log in first.', 'error')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()

    if request.method == 'POST':
        # Handle form submission for updating settings
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Validate old password
        if old_password and new_password and confirm_password:
            if user.password == old_password:  # Check if the old password matches
                if new_password == confirm_password:
                    user.password = new_password  # Update the password (consider hashing in production)
                    db.session.commit()
                    flash('Password updated successfully.', 'success')
                else:
                    flash('New passwords do not match.', 'error')
            else:
                flash('Old password is incorrect.', 'error')

        # Handle profile photo update
        if 'profile_photo' in request.files:
            profile_photo = request.files['profile_photo']
            if profile_photo.filename != '':
                # Secure the filename
                profile_photo_filename = secure_filename(f"{user.username}_profile_photo.jpg")
                profile_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], profile_photo_filename))
                user.profile_photo = profile_photo_filename
                db.session.commit()
                flash('Profile photo updated successfully.', 'success')

        return redirect(url_for('settings'))

    return render_template('settings.html', user=user)
@app.route('/booking_history')
def booking_history():
    if 'username' not in session:
        flash('You must log in to view booking history.', 'error')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()

    # Get all vehicles owned by the user
    vehicles = Vehicle.query.filter_by(user_id=user.id).all()

    # Extract vehicle IDs
    vehicle_ids = [vehicle.id for vehicle in vehicles]

    # Get all bookings for the user's vehicles
    bookings = Booking.query.filter(Booking.vehicle_id.in_(vehicle_ids)).all()

    return render_template('booking_history.html', bookings=bookings)

# Add these new routes to your app.py

@app.route('/api/get_user_vehicles/<int:user_id>')
def get_user_vehicles(user_id):
    if 'admin' not in session:
        return jsonify({'message': 'Unauthorized access', 'status': 'error'}), 403
    
    vehicles = Vehicle.query.filter_by(user_id=user_id).all()
    return jsonify([{
        'id': vehicle.id,
        'type': vehicle.type,
        'model': vehicle.model,
        'registration_number': vehicle.registration_number,
        'status': vehicle.status
    } for vehicle in vehicles])

@app.route('/api/get_user_drivers/<int:user_id>')
def get_user_drivers(user_id):
    if 'admin' not in session:
        return jsonify({'message': 'Unauthorized access', 'status': 'error'}), 403
    
    drivers = Driver.query.filter_by(user_id=user_id).all()
    return jsonify([{
        'id': driver.id,
        'name': driver.name,
        'license_number': driver.license_number,
        'status': driver.status
    } for driver in drivers])

@app.route('/api/delete_vehicle/<int:vehicle_id>', methods=['DELETE'])
def delete_vehicle(vehicle_id):
    if 'admin' not in session:
        return jsonify({'message': 'Unauthorized access', 'status': 'error'}), 403
    
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return jsonify({'message': 'Vehicle not found', 'status': 'error'}), 404
    
    try:
        # Delete any bookings associated with this vehicle
        Booking.query.filter_by(vehicle_id=vehicle_id).delete()
        
        # Delete the vehicle
        db.session.delete(vehicle)
        db.session.commit()
        
        return jsonify({'message': 'Vehicle deleted successfully', 'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}', 'status': 'error'}), 500

@app.route('/api/delete_driver/<int:driver_id>', methods=['DELETE'])
def delete_driver(driver_id):
    if 'admin' not in session:
        return jsonify({'message': 'Unauthorized access', 'status': 'error'}), 403
    
    driver = Driver.query.get(driver_id)
    if not driver:
        return jsonify({'message': 'Driver not found', 'status': 'error'}), 404
    
    try:
        # Delete any withdrawals associated with this driver
        Withdrawal.query.filter_by(driver_id=driver_id).delete()
        
        # Delete the driver
        db.session.delete(driver)
        db.session.commit()
        
        return jsonify({'message': 'Driver deleted successfully', 'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}', 'status': 'error'}), 500
@app.route('/profit_analysis')
@app.route('/profit_analysis')
def profit_analysis():
    return render_template('profit_analysis.html')

if __name__ == '__main__':
    app.run(debug=True)











