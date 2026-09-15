from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

# डेटाबेस तयार करणे आणि टेबल सेट करणे
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL
            )
        ''')
        conn.commit()
    except sqlite3.OperationalError:
        # टेबल आधीच तयार असेल तर एरर दुर्लक्षित करा
        pass
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    conn.close()
    return render_template('index.html', users=users)

@app.route('/add', methods=['POST'])
def add_user():
    name = request.form.get('name')
    email = request.form.get('email')
    
    if name and email:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (name, email) VALUES (?, ?)', (name, email))
        conn.commit()
        conn.close()
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()  # ॲप सुरू होताना डेटाबेस तयार होईल
    app.run(debug=True, port=5000)
