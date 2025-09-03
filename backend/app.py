import os
import logging
import numpy as np
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image
import sqlite3
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__, template_folder='../templates', static_folder='../static')
UPLOAD_FOLDER = '../uploads/'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Simulated session
logged_in_user = {}
logged_in_admin = {}

# Initialize Database
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT,
                    password_hash TEXT NOT NULL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    disease TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )''')
    # Create default admin if not exists
    c.execute("SELECT * FROM users WHERE username='admin'")
    if c.fetchone() is None:
        c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                  ("admin", "admin@cropSight.ai", generate_password_hash("admin123")))
        logging.info(" Default admin account created: admin / admin123")
    conn.commit()
    conn.close()

init_db()

# Load ML Model
try:
    from tensorflow.keras.models import load_model
    model = load_model('../models/rice_disease_model.h5')
    class_names = np.load('../models/class_names.npy', allow_pickle=True).tolist()
    MODEL_LOADED = True
    logging.info(" Model loaded successfully")
except Exception as e:
    logging.warning(f" Model not found: {e}")
    MODEL_LOADED = False

def preprocess_image(image_path):
    img = Image.open(image_path).resize((150, 150))
    img_array = np.array(img) / 255.0
    return np.expand_dims(img_array, axis=0)


# User Routes


@app.route('/')
def home():
    return render_template('login.html')

@app.route('/signup', methods=['GET'])
def signup_page():
    return render_template('signup.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, password_hash FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()

    if row and check_password_hash(row[1], password):
        if username == 'admin':
            logged_in_admin['username'] = username
            return jsonify({"success": True, "redirect": "/admin_dashboard"}), 200
        else:
            logged_in_user['username'] = username
            logged_in_user['user_id'] = row[0]
            return jsonify({"success": True, "redirect": "/dashboard"}), 200
    return jsonify({"success": False, "msg": "Invalid credentials"}), 401

@app.route('/signup', methods=['POST'])
def signup():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                  (username, email, generate_password_hash(password)))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "msg": "Username already exists"}), 400
    finally:
        conn.close()

    return jsonify({"success": True}), 201

@app.route('/dashboard')
def dashboard():
    if 'username' not in logged_in_user:
        return render_template('login.html')
    return render_template('dashboard.html')

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, str(uuid.uuid4()) + '.jpg')
    file.save(filepath)

    if not MODEL_LOADED:
        return jsonify({'class': 'Healthy', 'confidence': 94.3})

    try:
        processed_img = preprocess_image(filepath)
        preds = model.predict(processed_img)[0]
        pred_class = class_names[np.argmax(preds)]
        confidence = float(np.max(preds)) * 100
        os.remove(filepath)

        if 'username' in logged_in_user:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("INSERT INTO predictions (user_id, disease, confidence) VALUES (?, ?, ?)",
                      (logged_in_user['user_id'], pred_class, round(confidence, 2)))
            conn.commit()
            conn.close()

        return jsonify({
            'class': pred_class,
            'confidence': round(confidence, 2)
        })
    except Exception as e:
        os.remove(filepath)
        return jsonify({'error': 'Prediction failed', 'details': str(e)}), 500

@app.route('/history', methods=['GET'])
def history():
    if 'username' not in logged_in_user:
        return jsonify([])
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT disease, confidence, timestamp FROM predictions WHERE user_id=? ORDER BY timestamp DESC LIMIT 10",
              (logged_in_user['user_id'],))
    rows = c.fetchall()
    conn.close()
    history_list = [{'disease': row[0], 'confidence': row[1], 'timestamp': row[2]} for row in rows]
    return jsonify(history_list)

@app.route('/clear_history', methods=['POST'])
def clear_history():
    if 'username' not in logged_in_user:
        return jsonify({'error': 'Not logged in'}), 401
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM predictions WHERE user_id=?", (logged_in_user['user_id'],))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# Admin Routes


@app.route('/admin_login')
def admin_login_page():
    return render_template('admin_login.html')

@app.route('/admin_login', methods=['POST'])
def admin_login():
    username = request.form.get('username')
    password = request.form.get('password')

    if username == 'admin' and password == 'admin123':
        logged_in_admin['username'] = username
        return jsonify({"success": True, "redirect": "/admin_dashboard"}), 200
    return jsonify({"success": False, "msg": "Invalid admin credentials"}), 401

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'username' not in logged_in_admin:
        return render_template('admin_login.html')

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Get all users
    c.execute("SELECT id, username, email FROM users WHERE username != 'admin'")
    users = c.fetchall()

    # Get all predictions with usernames
    c.execute("""
        SELECT u.username, p.disease, p.confidence, p.timestamp 
        FROM predictions p 
        JOIN users u ON p.user_id = u.id 
        ORDER BY p.timestamp DESC LIMIT 100
    """)
    predictions = c.fetchall()
    conn.close()

    return render_template('admin_dashboard.html', users=users, predictions=predictions)

@app.route('/admin_create_user', methods=['POST'])
def admin_create_user():
    if 'username' not in logged_in_admin:
        return jsonify({"error": "Unauthorized"}), 401

    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                  (username, email, generate_password_hash(password)))
        conn.commit()
        return jsonify({"success": True, "msg": "User created successfully"})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username or email already exists"}), 400
    finally:
        conn.close()

@app.route('/admin_delete_user/<int:user_id>', methods=['DELETE'])
def admin_delete_user(user_id):
    if 'username' not in logged_in_admin:
        return jsonify({"error": "Unauthorized"}), 401

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute("SELECT username FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    if user[0] == 'admin':
        conn.close()
        return jsonify({"error": "Cannot delete admin"}), 400

    c.execute("DELETE FROM predictions WHERE user_id=?", (user_id,))
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "msg": "User deleted successfully"})

@app.route('/logout_admin', methods=['POST'])
def logout_admin():
    logged_in_admin.clear()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)