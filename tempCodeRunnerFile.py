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

        # Check if user exists
        if not user:
            return render_template('login.html', error="User not found")

        # Validate password directly (no hashing)
        if user['password'] == password:
            session['user_id'] = user['id']  # Store user ID in session
            return redirect(url_for('dashboard'))

        return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')


# Route: Dashboard
@app.route('/')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Fetch user data from the users table
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    # Fetch the account information of the user (if applicable)
    cursor.execute("SELECT * FROM accounts WHERE user_id = %s", (user_id,))
    account = cursor.fetchone()

    cursor.close()
    connection.close()

    return render_template('dashboard.html', user=user, account=account)


# Route to fetch transaction data for the line chart
@app.route('/get_user_transactions')
def get_user_transactions():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Fetch all transactions for the logged-in user's account(s)
    cursor.execute("""
        SELECT t.date, t.amount, t.description, c.category_name
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.account_id IN (SELECT account_id FROM accounts WHERE user_id = %s)
        ORDER BY t.date ASC
    """, (user_id,))
    rows = cursor.fetchall()

    # Prepare data for the graph
    dates = [row['date'].strftime('%Y-%m-%d') for row in rows]
    amounts = [row['amount'] for row in rows]

    cursor.close()
    connection.close()

    return jsonify({'dates': dates, 'amounts': amounts})


# Route to fetch expense category data for the pie chart
@app.route('/get_expense_data')
def get_expense_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Fetch category-wise spending for the logged-in user's account(s)
    cursor.execute("""
        SELECT c.category_name, SUM(t.amount) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.account_id IN (SELECT account_id FROM accounts WHERE user_id = %s) AND t.amount < 0
        GROUP BY c.category_name
    """, (user_id,))
    rows = cursor.fetchall()

    categories = [row['category_name'] for row in rows]
    amounts = [abs(row['total']) for row in rows]  # Absolute values for spending

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
