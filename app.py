from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import mysql.connector
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  

# Database Connection Function
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',  
        password='$!faT1205581908',  
        database='finance_db'
    )

# Route: Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        password = request.form['password']

        # Fetch user from the database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()

        # Check
        if not user:
            return render_template('login.html', error="User not found")

        # Validate password directly (no hashing)
        if user['password'] == password:
            session['user_id'] = user['id']  # Store user ID in session
            return redirect(url_for('dashboard'))

        return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')

@app.route('/')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Fetch user data (username, balance, etc.)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    # Fetch the recent transactions
    cursor.execute("""
        SELECT t.date, t.description, t.amount, c.category_name
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        JOIN accounts a ON t.account_id = a.account_id
        WHERE a.user_id = %s
        ORDER BY t.date DESC
        LIMIT 10
    """, (user_id,))
    transactions = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('dashboard.html', user=user, transactions=transactions)

# Route to fetch daily transaction data for the line chart
@app.route('/get_user_daily_transactions')
def get_user_daily_transactions():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT DATE(t.date) as date, SUM(t.amount) as total
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        WHERE a.user_id = %s
        GROUP BY DATE(t.date)
        ORDER BY DATE(t.date) ASC
    """, (user_id,))
    rows = cursor.fetchall()

    dates = [row['date'].strftime('%Y-%m-%d') for row in rows]
    amounts = [abs(row['total']) for row in rows] 

    cursor.close()
    connection.close()

    return jsonify({'dates': dates, 'amounts': amounts})


@app.route('/get_expense_data')
def get_expense_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT c.category_name, SUM(t.amount) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.account_id = %s AND t.amount < 0
        GROUP BY c.category_name
    """, (user_id,))
    rows = cursor.fetchall()

    categories = [row['category_name'] for row in rows]
    amounts = [abs(row['total']) for row in rows]

    cursor.close()
    connection.close()

    return jsonify({'categories': categories, 'amounts': amounts})


# Route: Logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Clear session
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
