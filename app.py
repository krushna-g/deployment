from flask import Flask, render_template, request, redirect, url_for, session
import os
import time
import sqlite3

try:
    import psycopg2
    import psycopg2.extras
except ModuleNotFoundError:
    psycopg2 = None
    psycopg2_extras = None

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'trading-mindset-secret-key')

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_NAME = os.environ.get('DB_NAME', 'trading_db')
DB_USER = os.environ.get('DB_USER', 'trading_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'trading_pass')
USE_SQLITE = True
if os.environ.get('USE_SQLITE') is not None:
    USE_SQLITE = os.environ.get('USE_SQLITE', '1').lower() in {'1', 'true', 'yes', 'on'}


def get_db_connection():
    if USE_SQLITE:
        conn = sqlite3.connect(os.environ.get('SQLITE_DB_PATH', 'trading_app.db'))
        conn.row_factory = sqlite3.Row
        return conn

    if psycopg2 is None:
        raise RuntimeError('psycopg2 is not installed. Set USE_SQLITE=1 to use the local fallback database.')

    last_error = None
    for attempt in range(15):
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=5432,
            )
            conn.autocommit = True
            return conn
        except psycopg2.OperationalError as exc:
            last_error = exc
            time.sleep(2)

    raise last_error


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    if USE_SQLITE:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                setup TEXT NOT NULL,
                profit_loss REAL NOT NULL,
                mistakes TEXT,
                lesson TEXT,
                mindset TEXT,
                notes TEXT,
                user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id)
            )
        ''')

        cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
        admin_user = cursor.fetchone()
        if admin_user is None:
            cursor.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                ('admin', generate_password_hash('admin123')),
            )
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_journal (
                id SERIAL PRIMARY KEY,
                entry_date DATE NOT NULL,
                symbol VARCHAR(50) NOT NULL,
                setup TEXT NOT NULL,
                profit_loss NUMERIC(10,2) NOT NULL,
                mistakes TEXT,
                lesson TEXT,
                mindset TEXT,
                notes TEXT,
                user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id)
            )
        ''')

        cursor.execute("SELECT id FROM users WHERE username = %s", ('admin',))
        admin_user = cursor.fetchone()
        if admin_user is None:
            cursor.execute(
                'INSERT INTO users (username, password_hash) VALUES (%s, %s)',
                ('admin', generate_password_hash('admin123')),
            )

    conn.commit()
    conn.close()


with app.app_context():
    init_db()


@app.route('/')
def root():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if username and password:
            conn = get_db_connection()
            if USE_SQLITE:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
                user = cursor.fetchone()
            else:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute('SELECT id, password_hash FROM users WHERE username = %s', (username,))
                user = cursor.fetchone()
            conn.close()

            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = username
                return redirect(url_for('dashboard'))

        error = 'Invalid username or password.'

    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    success = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            error = 'Username and password are required.'
        elif len(password) < 4:
            error = 'Password must be at least 4 characters.'
        else:
            conn = get_db_connection()
            if USE_SQLITE:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
                existing = cursor.fetchone()
                if existing:
                    error = 'This username already exists.'
                else:
                    cursor.execute(
                        'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                        (username, generate_password_hash(password)),
                    )
                    conn.commit()
                    conn.close()
                    success = 'Account created successfully. You can log in now.'
                    return render_template('login.html', success=success)
            else:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
                existing = cursor.fetchone()
                if existing:
                    error = 'This username already exists.'
                else:
                    cursor.execute(
                        'INSERT INTO users (username, password_hash) VALUES (%s, %s)',
                        (username, generate_password_hash(password)),
                    )
                    conn.close()
                    success = 'Account created successfully. You can log in now.'
                    return render_template('login.html', success=success)
            conn.close()

    return render_template('register.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if USE_SQLITE:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, entry_date, symbol, setup, profit_loss, mistakes, lesson, mindset, notes
            FROM trading_journal
            WHERE user_id = ?
            ORDER BY entry_date DESC, id DESC
        ''', (session['user_id'],))
    else:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute('''
            SELECT id, entry_date, symbol, setup, profit_loss, mistakes, lesson, mindset, notes
            FROM trading_journal
            WHERE user_id = %s
            ORDER BY entry_date DESC, id DESC
        ''', (session['user_id'],))
    entries = cursor.fetchall()
    conn.close()

    total_pl = sum(float(row['profit_loss']) for row in entries)
    positive_days = sum(1 for row in entries if float(row['profit_loss']) > 0)
    negative_days = sum(1 for row in entries if float(row['profit_loss']) < 0)

    return render_template(
        'index.html',
        entries=entries,
        total_pl=total_pl,
        positive_days=positive_days,
        negative_days=negative_days,
        username=session.get('username', 'Trader'),
    )


@app.route('/add', methods=['POST'])
def add_entry():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    entry_date = request.form.get('entry_date')
    symbol = request.form.get('symbol', '').strip()
    setup = request.form.get('setup', '').strip()
    profit_loss = request.form.get('profit_loss', '0')
    mistakes = request.form.get('mistakes', '').strip()
    lesson = request.form.get('lesson', '').strip()
    mindset = request.form.get('mindset', '').strip()
    notes = request.form.get('notes', '').strip()

    if entry_date and symbol and setup:
        try:
            profit_value = float(profit_loss)
        except ValueError:
            profit_value = 0.0

        conn = get_db_connection()
        cursor = conn.cursor()
        if USE_SQLITE:
            cursor.execute('''
                INSERT INTO trading_journal (entry_date, symbol, setup, profit_loss, mistakes, lesson, mindset, notes, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (entry_date, symbol, setup, profit_value, mistakes, lesson, mindset, notes, session['user_id']))
            conn.commit()
        else:
            cursor.execute('''
                INSERT INTO trading_journal (entry_date, symbol, setup, profit_loss, mistakes, lesson, mindset, notes, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (entry_date, symbol, setup, profit_value, mistakes, lesson, mindset, notes, session['user_id']))
        conn.close()

    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
