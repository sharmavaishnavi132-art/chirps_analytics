from flask import Flask , render_template , url_for , request , redirect,flash,session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash , check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
import pickle
import sys

# Add the main folder to path to import the prediction script
sys.path.append(os.path.join(os.getcwd(), 'bird_classification-main'))
from predict_bird_species import predict_species

app=Flask(__name__)     
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'wav', 'mp3', 'flac'}

# Ensure the uploads folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Load the trained model
MODEL_PATH = os.path.join('bird_classification-main', 'bird_classifier_model.pkl')
with open(MODEL_PATH, 'rb') as f:
    model = pickle.load(f)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///users.db'
app.secret_key='secret_key'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
db=SQLAlchemy(app)

class User(db.Model):
        id=db.Column(db.Integer,primary_key=True)
        name=db.Column(db.String(100))
        email=db.Column(db.String(50),unique=True)
        password=db.Column(db.String(100))
with app.app_context():
        db.create_all()


@app.route('/')
def index():
        return render_template('index.html') 

def login_required(f):
        @wraps(f)
        def decorated(*args,**kwargs):
                if 'user_id' not in session:
                        flash('Please login to access this page','error')
                        return redirect(url_for('login'))
                return f(*args,**kwargs)
        return decorated
@app.route('/login',methods=['GET','POST'])    #login page
def login():
        if request.method=='POST':
                email=request.form['email']
                password=request.form['password']
                user=User.query.filter_by(email=email).first()
                if user and check_password_hash(user.password,password):
                        session['user_id']=user.id
                        session['user_name']=user.name
                        flash('Signin successful','success')
                        return redirect(url_for('index'))
        return render_template('login.html')


@app.route('/register',methods=['GET','POST'])    #register page
def register():
        if request.method=='POST':
                name=request.form['name']
                email=request.form['email']
                password=request.form['password']
                confirm_password=request.form['confirm_password']

                if not name or len(name.strip())<2:
                        flash('name must be atleast 2 character long','error')
                        return redirect(url_for('register'))
                if not email or '@' not in email :
                        flash('Invalid email','error')
                        return redirect(url_for('register'))
                if not password or len(password)<8 or not any(char.isalpha() for char in password ) or not any(char.isdigit() for char in password) or not any (not char.isalnum() for char in password):
                        flash('pass must be atleast 8 char long and contain letters and contain numbers and special characters','error')
                        return redirect(url_for('register'))
                if confirm_password!=password:
                        flash('Confirm password should match password','error')
                        return redirect(url_for('register'))
                #check if user already exists
                existing_user=User.query.filter_by(email=email).first()
                if existing_user:
                        flash('Email already exists.Please login. ','error')
                        return redirect(url_for('register'))
                # generate hash password
                hashed_password=generate_password_hash(password)
                new_user=User(
                        name=name.strip(),
                        email=email.strip(),
                        password=hashed_password
                )
                try:
                        db.session.add(new_user)
                        db.session.commit()
                        flash('Registration successful .Proceed to signin','success')
                        return redirect(url_for('login'))
                except Exception as e:
                        db.session.rollback()
                        flash('Some error occured while registering','error')
                        return redirect(url_for('register'))

        return render_template('register.html')

@app.route('/logout')
def logout():
        session.pop('user_id',None)
        session.pop('user_name',None)
        flash('Logout successful','success')
        return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/classification', methods=['GET', 'POST'])
@login_required
def classification():
    results = None
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                # Run prediction
                prediction_results = predict_species(model, filepath)
                
                # Pre-process results for the template
                # Convert numpy floats to standard floats and sort probabilities
                results = {
                    'predicted_species': prediction_results['predicted_species'],
                    'confidence': float(prediction_results['confidence']),
                    'num_windows': int(prediction_results['num_windows']),
                    'audio_url': url_for('uploaded_file', filename=filename),
                    'top_probabilities': sorted(
                        [(species, float(prob)) for species, prob in prediction_results['class_probabilities'].items()],
                        key=lambda x: x[1],
                        reverse=True
                    )[:5]
                }
                flash('Analysis complete!', 'success')
            except Exception as e:
                flash(f'Error analyzing audio: {str(e)}', 'error')
            finally:
                # Optionally delete file after processing
                # os.remove(filepath)
                pass

    return render_template('classification.html', results=results)
if __name__=='__main__':
        app.run(debug=True ,port=5000)