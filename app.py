# Import required libraries
from flask import Flask , render_template , url_for , request , redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash , check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
import pickle
import sys

# Add the main project folder to path (so we can import prediction file)
sys.path.append(os.path.join(os.getcwd(), 'bird_classification-main'))

# Import prediction functions
from predict_bird_species import predict_species, log_debug

# Create Flask app
app = Flask(__name__)

# File upload configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'wav', 'mp3', 'flac'}

# Create uploads folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Load trained ML model from pickle file
MODEL_PATH = os.path.join('bird_classification-main', 'bird_classifier_model.pkl')
with open(MODEL_PATH, 'rb') as f:
    model = pickle.load(f)

# Function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.secret_key = 'secret_key'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User model (table)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))

# Create database tables
with app.app_context():
    db.create_all()

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Login required decorator (protect routes)
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# Login route
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if user exists
        user = User.query.filter_by(email=email).first()

        # Verify password
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash('Signin successful', 'success')
            return redirect(url_for('index'))

    return render_template('login.html')

# Register route
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Basic validations
        if not name or len(name.strip()) < 2:
            flash('name must be atleast 2 character long','error')
            return redirect(url_for('register'))

        if not email or '@' not in email:
            flash('Invalid email','error')
            return redirect(url_for('register'))

        # Password validation
        if (not password or len(password) < 8 or 
            not any(char.isalpha() for char in password) or 
            not any(char.isdigit() for char in password) or 
            not any(not char.isalnum() for char in password)):
            flash('Password must be strong','error')
            return redirect(url_for('register'))

        if confirm_password != password:
            flash('Passwords do not match','error')
            return redirect(url_for('register'))

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists. Please login.','error')
            return redirect(url_for('register'))

        # Hash password for security
        hashed_password = generate_password_hash(password)

        # Create new user
        new_user = User(
            name=name.strip(),
            email=email.strip(),
            password=hashed_password
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful. Proceed to login','success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Error during registration','error')
            return redirect(url_for('register'))

    return render_template('register.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('Logout successful','success')
    return redirect(url_for('index'))

# Serve uploaded audio files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Bird classification route (main feature)
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    results = None

    if request.method == 'POST':

        # Check file exists in request
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)

        file = request.files['file']

        # Check file selected
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)

        # Check file type
        if file and allowed_file(file.filename):

            # Save file
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                log_debug(f"Starting analysis for: {filename}")

                # Predict bird species
                prediction_results = predict_species(model, filepath)

                log_debug(f"Analysis successful for: {filename}")

                # Format results for frontend
                results = {
                    'predicted_species': prediction_results['predicted_species'],
                    'confidence': float(prediction_results['confidence']),
                    'num_windows': int(prediction_results['num_windows']),
                    'audio_url': url_for('uploaded_file', filename=filename),

                    # Top 5 probabilities
                    'top_probabilities': sorted(
                        [(species, float(prob)) for species, prob in prediction_results['class_probabilities'].items()],
                        key=lambda x: x[1],
                        reverse=True
                    )[:5]
                }

                flash('Analysis complete!', 'success')

            except Exception as e:
                flash(f'Error analyzing audio: {str(e)}', 'error')

    return render_template('dashboard.html', results=results)

# Run app
if __name__ == '__main__':
    app.run(debug=True, port=5000)