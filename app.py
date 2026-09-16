from flask import Flask, render_template, request, redirect, url_for
import os
import sqlite3

app = Flask(__name__)

DB_PATH = os.path.join('/data', 'database.db') if os.path.exists('/data') else 'database.db'


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()


with app.app_context():
    init_db()


@app.route('/')
def index():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, entry_date, symbol, setup, profit_loss, mistakes, lesson, mindset, notes
        FROM trading_journal
        ORDER BY entry_date DESC, id DESC
    ''')
    entries = cursor.fetchall()
    conn.close()

    total_pl = sum(float(row[4]) for row in entries)
    positive_days = sum(1 for row in entries if float(row[4]) > 0)
    negative_days = sum(1 for row in entries if float(row[4]) < 0)

    return render_template(
        'index.html',
        entries=entries,
        total_pl=total_pl,
        positive_days=positive_days,
        negative_days=negative_days,
    )


@app.route('/add', methods=['POST'])
def add_entry():
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

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trading_journal (entry_date, symbol, setup, profit_loss, mistakes, lesson, mindset, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (entry_date, symbol, setup, profit_value, mistakes, lesson, mindset, notes))
        conn.commit()
        conn.close()

    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
