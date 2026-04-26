# Import required libraries
from flask import Flask , render_template , url_for , request , redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from  datetime import datetime
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

class Classification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    predicted_species = db.Column(db.String(100), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('classifications', lazy=True))

# Create database tables
with app.app_context():
    db.create_all()

# Home page
@app.route('/')
def home():
    return render_template('home.html')

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
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))
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
    return redirect(url_for('home'))

# Serve uploaded audio files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Bird classification route (main feature)
@app.route('/classification', methods=['GET', 'POST'])
@login_required
def classification():
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
                # Save to database
                try:
                    user_id = session.get('user_id')
                    if user_id:
                        new_classification = Classification(
                            user_id=user_id,
                            filename=filename,
                            predicted_species=results['predicted_species'],
                            confidence=results['confidence']
                        )
                        db.session.add(new_classification)
                        db.session.commit()
                        log_debug(f"SUCCESS: Saved classification to DB for user {user_id}: {filename}")
                    else:
                        log_debug("WARNING: No user_id in session, skipping DB save")
                except Exception as db_e:
                    log_debug(f"DATABASE ERROR: {str(db_e)}")
                    db.session.rollback()


                flash('Analysis complete!', 'success')

            except Exception as e:
                flash(f'Error analyzing audio: {str(e)}', 'error')

    return render_template('classification.html', results=results)

@app.route('/about')
def about():
    return render_template('about.html')
@app.route('/contact')
def contact():
    return render_template('contact.html')
# Detailed bird data
BIRD_DETAILS = {
    'european robin': {
        'name': 'European Robin',
        'scientific_name': 'Erithacus rubecula',
        'tag': 'Common Forest Bird',
        'description': 'Famous for its vibrant orange breast and complex, flute-like melodic songs. It is a friendly garden visitor across Europe.',
        'habitat': 'Woodlands, gardens, and hedgerows.',
        'diet': 'Insects, worms, and berries.',
        'fun_fact': 'Robins are highly territorial and will defend their area aggressively against other robins.',
        'image': 'https://images.unsplash.com/photo-1552728089-57bdde30eba3?q=80&w=1000',
        'frequency': '2.0-8.5 kHz'
    },
    'song thrush': {
        'name': 'Song Thrush',
        'scientific_name': 'Turdus philomelos',
        'tag': 'Songbird',
        'description': 'Known for repeating musical phrases, often heard in gardens and woodlands. Its song is one of the most beautiful in the avian world.',
        'habitat': 'Forests, gardens, and parks.',
        'diet': 'Snails, earthworms, and fruit.',
        'fun_fact': 'The Song Thrush is famous for using a stone as an "anvil" to break open snail shells.',
        'image': 'https://images.unsplash.com/photo-1444464666168-49d633b86797?q=80&w=1000',
        'frequency': '1.5-6.0 kHz'
    },
    'common nightingale': {
        'name': 'Common Nightingale',
        'scientific_name': 'Luscinia megarhynchos',
        'tag': 'Rare Species',
        'description': 'Renowned for being one of the most beautiful and complex singers in nature. They are often heard singing at night.',
        'habitat': 'Dense bushes and thickets.',
        'diet': 'Insects and berries.',
        'fun_fact': 'A male nightingale can have a repertoire of over 200 different phrases and songs.',
        'image': 'https://images.unsplash.com/photo-1522926126624-3ef711a5a827?q=80&w=1000',
        'frequency': '1.0-5.5 kHz'
    },
    'great tit': {
        'name': 'Great Tit',
        'scientific_name': 'Parus major',
        'tag': 'Active Garden Bird',
        'description': 'A large tit with a black head and white cheeks. It has a distinctive "teacher-teacher" song.',
        'habitat': 'Woodlands, parks, and gardens.',
        'diet': 'Seeds, nuts, and insects.',
        'fun_fact': 'Great Tits are known for their intelligence and ability to learn new behaviors, like opening milk bottles.',
        'image': 'https://images.unsplash.com/photo-1591584250171-0414592358fb?q=80&w=1000',
        'frequency': '2.0-7.0 kHz'
    },
    'common starling': {
        'name': 'Common Starling',
        'scientific_name': 'Sturnus vulgaris',
        'tag': 'Mimicry Specialist',
        'description': 'Highly social birds known for their stunning murmurations and ability to mimic sounds, including other birds and even car alarms.',
        'habitat': 'Urban areas, grasslands, and woodlands.',
        'diet': 'Insects, fruits, and seeds.',
        'fun_fact': 'Starlings can mimic the songs of over 20 other bird species.',
        'image': 'https://images.unsplash.com/photo-1612170153139-6f881ff067e0?q=80&w=1000',
        'frequency': '0.5-8.0 kHz'
    }
}

@app.route('/birds')
def birds():
    query = request.args.get('q', '').lower().strip()
    results = []
    
    if query:
        # Search in our detailed data
        for key, details in BIRD_DETAILS.items():
            if query in key or query in details['name'].lower() or query in details['scientific_name'].lower():
                results.append(details)
    else:
        # Show all featured birds if no query
        results = list(BIRD_DETAILS.values())
        
    return render_template('birds.html', results=results, query=query)
@app.route('/dashboard')
@login_required
def dashboard():
    # Get all classifications for the current user
    user_classifications = Classification.query.filter_by(user_id=session['user_id']).order_by(Classification.timestamp.desc()).all()
    
    # Calculate some stats
    total_count = len(user_classifications)
    unique_species = len(set(c.predicted_species for c in user_classifications))
    avg_confidence = sum(c.confidence for c in user_classifications) / total_count if total_count > 0 else 0
    
    # Get species distribution for chart
    species_counts = {}
    for c in user_classifications:
        species_counts[c.predicted_species] = species_counts.get(c.predicted_species, 0) + 1
    
    return render_template('dashboard.html', 
                           classifications=user_classifications,
                           total_count=total_count,
                           unique_species=unique_species,
                           avg_confidence=round(avg_confidence, 1),
                           species_counts=species_counts)
# Run app
if __name__ == '__main__':
    app.run(debug=True, port=5000)