from flask import Flask, render_template, session, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'chirps_analytics_secret_2026' # Security ke liye zaroori hai

# --- 1. HOME PAGE ---
@app.route('/')
def index():
    return render_template('home.html')

# --- 2. ABOUT PAGE ---
@app.route('/about')
def about():
    return render_template('about.html')

# --- 3. DASHBOARD (Only for Logged-in Users) ---
@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        return render_template('dashboard.html')
    flash('Please login first to access the dashboard.', 'error')
    return redirect(url_for('login'))

# --- 4. LOGIN PAGE ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Yahan baad mein hum database check dalenge
        # Abhi ke liye testing ke liye direct login kar rahe hain
        session['user_id'] = 1 
        flash('Successfully logged in!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# --- 5. REGISTER PAGE ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        
        # --- ADDED LOGIC START ---
        # Note: Abhi database nahi hai, isliye hum ek dummy check kar rahe hain.
        # Agar aap 'test@gmail.com' se register karne ki koshish karenge toh ye error dega.
        # Future mein yahan 'User.query.filter_by(email=email).first()' aayega.
        
        existing_user_dummy = "test@gmail.com" 
        
        if email == existing_user_dummy:
            flash('This user already exists. Go and login.', 'error')
            return redirect(url_for('login'))
        # --- ADDED LOGIC END ---

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# --- 6. LOGOUT ---
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

# --- 7. BIRDS LIST (Optional Page) ---
@app.route('/birds')
def birds():
    return render_template('birds.html')

# --- 8. CONTACT ---
@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    # debug=True se error terminal mein dikhte hain
    app.run(debug=True)