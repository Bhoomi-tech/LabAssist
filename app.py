from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'BB2705'  # Needed for sessions
DB_FILE = 'requests.db'

# ---------- DATABASE INITIALIZATION ----------
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_name TEXT,
                        benchnum TEXT,
                        status TEXT,
                        timestamp TEXT
                    )''')
        conn.commit()

# ---------- SITE PIN CHECK ----------
@app.before_request
def require_site_pin():
    allowed_routes = ['pin', 'static']
    if request.endpoint not in allowed_routes and not session.get('site_access'):
        return redirect(url_for('pin'))

@app.route('/pin', methods=['GET', 'POST'])
def pin():
    if request.method == 'POST':
        entered_pin = request.form['pin']
        if entered_pin == '1234':  # Example site PIN
            session['site_access'] = True
            return redirect(url_for('home'))
        else:
            return render_template('pin.html', error="Incorrect PIN.")
    return render_template('pin.html')

# ---------- ROUTES ----------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/student')
def student_page():
    return render_template('student.html')

@app.route('/request_help', methods=['POST'])
def request_help():
    name = request.form['student_name'].strip()
    bench = request.form['benchnum'].strip()

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM requests WHERE student_name=? AND status='Pending'", (name,))
        existing_request = c.fetchone()

        if existing_request:
            return render_template('student.html', error="You already have a pending request.")

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute(
            "INSERT INTO requests (student_name, benchnum, status, timestamp) VALUES (?, ?, 'Pending', ?)",
            (name, bench, timestamp)
        )
        conn.commit()

    return redirect(url_for('student_page'))

# ---------- TECHNICIAN LOGIN ----------
@app.route('/tech_login', methods=['GET', 'POST'])
def tech_login():
    if request.method == 'POST':
        password = request.form['password']
        if password == 'labtech123':  # Technician password
            session['role'] = 'technician'
            return redirect(url_for('dashboard'))
        else:
            return render_template('tech_login.html', error="Incorrect password.")
    return render_template('tech_login.html')

@app.route('/logout')
def logout():
    # Only logs out technician, site PIN session remains
    session.pop('role', None)
    return redirect(url_for('dashboard'))

# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM requests WHERE status='Pending'")
        requests_data = c.fetchall()

    requests_list = [
        {"id": r[0], "student_name": r[1], "benchnum": r[2], "timestamp": r[4]}
        for r in requests_data
    ]

    return render_template('dashboard.html', requests=requests_list)

# ---------- RESOLVE REQUEST ----------
@app.route('/resolve/<int:request_id>')
def resolve(request_id):
    # Redirect unauthorized users to technician login
    if session.get('role') != 'technician':
        return redirect(url_for('tech_login'))

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("UPDATE requests SET status='Resolved' WHERE id=?", (request_id,))
        conn.commit()

    return redirect(url_for('dashboard'))

# ---------- RUN APP ----------
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
