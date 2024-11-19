from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dbconnect import conn
import matplotlib.pyplot as plt
import io, base64

app = Flask(__name__)
app.secret_key = 'priya12' # Necessary for using sessions and flash messages

# Login route set as the default homepage
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        # Query to check if user exists with the given credentials and role
        my_cursor = conn.cursor()
        query = "SELECT * FROM Users WHERE username = %s AND password_hash = %s AND role = %s"
        my_cursor.execute(query, (username, password, role))
        user = my_cursor.fetchone()
        my_cursor.close()

        if user:
            # Store user info in session
            session['loggedin'] = True
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            flash('Login successful!', 'success')

            # Redirect based on role
            if role == 'Employee':
                return redirect(url_for('employee_dashboard'))
            elif role == 'Admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'Analyst':
                return redirect(url_for('analyst_dashboard'))
            else:
                flash('Role not recognized. Please contact support.', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Invalid username, password, or role', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        # Insert data into Users table
        try:
            my_cursor = conn.cursor()
            query = "INSERT INTO Users (username, password_hash, role) VALUES (%s, %s, %s)"
            my_cursor.execute(query, (username, password, role))
            conn.commit()
            my_cursor.close()
            flash('Signup successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Error: {e}")
            flash("Error creating user.", 'danger')
            return redirect(url_for('signup'))

    return render_template('signup.html')

# Route for signup success page
@app.route('/signup_success')
def signup_success():
    return render_template('login.html')

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'Admin':
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('login'))
    
    try:
        # Query to get sales data grouped by employee
        my_cursor = conn.cursor()
        query = """
            SELECT 
                Users.user_id,
                Users.username,
                Product.Prod_Name, 
                Customer.Name AS Customer_Name, 
                Sales.Quantity, 
                Sales.Total_Amount, 
                Sales.Sale_Date
            FROM Sales
            JOIN Product ON Sales.Prod_ID = Product.Prod_ID
            JOIN Customer ON Sales.Custom_ID = Customer.Custom_ID
            JOIN Users ON Sales.user_id = Users.user_id
            ORDER BY Users.username, Sales.Sale_Date;
        """
        my_cursor.execute(query)
        sales_data = my_cursor.fetchall()
        my_cursor.close()

        # Organize sales data by employee
        sales_by_user = {}
        for sale in sales_data:
            user_id = sale[0]
            username = sale[1]
            if username not in sales_by_user:
                sales_by_user[username] = []
            sales_by_user[username].append({
                'product': sale[2],
                'customer': sale[3],
                'quantity': sale[4],
                'total_amount': sale[5],
                'sale_date': sale[6]
            })

        # Handle adding new employee
        if request.method == 'POST' and 'add_employee' in request.form:
            emp_name = request.form['emp_name']
            phone_no = request.form['phone_no']
            email = request.form['email']
            password = request.form['password']
            
            

            try:
                # Insert new employee into the Employee table
                my_cursor = conn.cursor()
                query = "INSERT INTO Employee (Employee_Name, Phone_No, Email, Password) VALUES (%s, %s, %s, %s)"
                my_cursor.execute(query, (emp_name, phone_no, email, password))
                conn.commit()
                my_cursor.close()
                flash('New employee added successfully!', 'success')
                return redirect(url_for('admin_dashboard'))
            except Exception as e:
                flash(f"Error adding employee: {e}", 'danger')
        
        # Handling adding new product
        if request.method == 'POST' and 'add_product' in request.form:
            prod_name = request.form['prod_name']
            unit_price = request.form['unit_price']

            try:
                my_cursor = conn.cursor()
                query = "INSERT INTO Product (Prod_Name, Unit_Price) VALUES (%s, %s)"
                my_cursor.execute(query, (prod_name, unit_price))
                conn.commit()
                my_cursor.close()
                flash('New product added successfully!', 'success')
                return redirect(url_for('admin_dashboard'))
            except Exception as e:
                flash(f"Error adding product: {e}", 'danger')

        return render_template('admin_dashboard.html', sales_by_user=sales_by_user)

    except Exception as e:
        flash(f"Error fetching sales data: {e}", 'danger')
        return redirect(url_for('login'))
    

    
@app.route('/analyst_dashboard')
def analyst_dashboard():
    # Ensure only logged-in analysts can access this page
    if 'role' not in session or session['role'] != 'Analyst':
        flash('Unauthorized access!')
        return redirect(url_for('login'))
    
    # Fetch data from the database
    cursor = conn.cursor()
    
    # Get Total Sales
    cursor.execute("SELECT SUM(Total_Amount) FROM Sales")
    total_sales = cursor.fetchone()[0] or 0
    
    # Get Total Customers
    cursor.execute("SELECT COUNT(DISTINCT Custom_ID) FROM Sales")
    total_customers = cursor.fetchone()[0] or 0
    
    # Get Total Products Sold
    cursor.execute("SELECT SUM(Quantity) FROM Sales")
    total_products_sold = cursor.fetchone()[0] or 0
    
    # Calculate Average Order Value (AOV)
    cursor.execute("SELECT AVG(Total_Amount) FROM Sales")
    avg_order_value = cursor.fetchone()[0] or 0
    
    # Close the database connection
    cursor.close()
    
    # Pass the metrics to the template
    return render_template(
        'analyst_dashboard.html',
        total_sales=total_sales,
        total_customers=total_customers,
        total_products_sold=total_products_sold,
        avg_order_value=avg_order_value
    )
@app.route('/execute_query', methods=['POST'])
def execute_query():
    query_type = request.json.get('query_type')
    query_option = request.json.get('query_option')
    chart_type = request.json.get('chart_type', 'bar')
    cursor = conn.cursor()

    # Query execution based on query type and option selected
    if query_type == "sales_analysis":
        if query_option == "total_sales_by_month":
            cursor.callproc('GetTotalSalesByMonth1')  # Call the stored procedure
            cursor.nextset()  
            results = None
            for result in cursor.stored_results():  # Fetch the results of the procedure
                results = result.fetchall()  # Get all rows of the result set
        elif query_option == "average_sales_by_customer":
            cursor.execute("SELECT Custom_ID, AVG(Total_Amount) FROM Sales GROUP BY Custom_ID")
            results = cursor.fetchall()
        elif query_option == "monthly_quantity_sold":
            cursor.execute("SELECT MONTH(Sale_Date) AS Month, SUM(Quantity) FROM Sales GROUP BY Month")
            results = cursor.fetchall()
        elif query_option == "top_customers_by_sales":
            cursor.execute("SELECT Custom_ID, SUM(Total_Amount) FROM Sales GROUP BY Custom_ID ORDER BY SUM(Total_Amount) DESC LIMIT 5")
            results = cursor.fetchall()
        elif query_option == "sales_by_day":
            cursor.execute("SELECT DATE(Sale_Date) AS Day, SUM(Total_Amount) FROM Sales GROUP BY Day")
            results = cursor.fetchall()
        elif query_option == "total_sales_join_customers":
            cursor.execute("SELECT Sales.Invoice_ID, Customer.Custom_ID, Sales.Total_Amount "
                           "FROM Sales INNER JOIN Customer ON Sales.Custom_ID = Customer.Custom_ID")
            results = cursor.fetchall()
        elif query_option == "average_sales_all_customers":
            cursor.execute("SELECT AVG(Total_Amount) AS AverageSales FROM Sales")
            results = cursor.fetchall()
        elif query_option == "sales_above_avg_by_customer":
            cursor.execute("SELECT Custom_ID, Total_Amount FROM Sales "
                           "WHERE Total_Amount > (SELECT AVG(Total_Amount) FROM Sales)")
            results = cursor.fetchall()

    elif query_type == "customer_insights":
        if query_option == "total_customers_by_type":
            cursor.execute("SELECT custom_type, COUNT(*) FROM Customer GROUP BY custom_type")
            results = cursor.fetchall()
        elif query_option == "customer_purchase_frequency":
            cursor.execute("SELECT Custom_ID, COUNT(Invoice_ID) AS PurchaseFrequency FROM Sales GROUP BY Custom_ID")
            results = cursor.fetchall()
        elif query_option == "average_spent_per_customer_type":
            cursor.execute("SELECT custom_type, AVG(Total_Amount) FROM Sales "
                           "JOIN Customer ON Sales.Custom_ID = Customer.Custom_ID GROUP BY custom_type")
            results = cursor.fetchall()
        elif query_option == "recent_active_customers":
            cursor.execute("SELECT Custom_ID, MAX(Sale_Date) FROM Sales GROUP BY Custom_ID HAVING MAX(Sale_Date) > DATE_SUB(NOW(), INTERVAL 1 MONTH)")
            results = cursor.fetchall()
        elif query_option == "customer_join_sales":
            cursor.execute("SELECT Customer.Custom_ID, Customer.custom_type, SUM(Sales.Total_Amount) AS TotalSales "
                           "FROM Customer INNER JOIN Sales ON Customer.Custom_ID = Sales.Custom_ID GROUP BY Customer.Custom_ID")
            results = cursor.fetchall()
        elif query_option == "highest_spending_customers":
            cursor.execute("SELECT Custom_ID, MAX(Total_Amount) FROM Sales GROUP BY Custom_ID")
            results = cursor.fetchall()
        elif query_option == "customers_above_avg_spent":
            cursor.execute("SELECT Custom_ID FROM Sales "
                           "WHERE Total_Amount > (SELECT AVG(Total_Amount) FROM Sales)")
            results = cursor.fetchall()

    elif query_type == "product_performance":
        if query_option == "total_sales_by_product":
            cursor.execute("SELECT Prod_ID, SUM(Quantity) FROM Sales GROUP BY Prod_ID")
            results = cursor.fetchall()
        elif query_option == "top_5_selling_products":
            cursor.callproc('GetTopSellingProducts')  # Call the new stored procedure
            cursor.nextset()  # Move to the first result set returned by the procedure
            results = None
            for result in cursor.stored_results():  # Fetch the results of the procedure
                results = result.fetchall()
        elif query_option == "revenue_per_product":
            cursor.execute("SELECT Prod_ID, SUM(Total_Amount) FROM Sales GROUP BY Prod_ID")
            results = cursor.fetchall()
        elif query_option == "average_quantity_sold_per_product":
            cursor.execute("SELECT Prod_ID, AVG(Quantity) FROM Sales GROUP BY Prod_ID")
            results = cursor.fetchall()
        elif query_option == "daily_sales_per_product":
            cursor.execute("SELECT DATE(Sale_Date) AS Day, SUM(Quantity) FROM Sales GROUP BY Day")
            results = cursor.fetchall()
        elif query_option == "product_sales_join_customer":
            cursor.execute("SELECT Sales.Prod_ID, Sales.Quantity, Customer.Custom_ID "
                           "FROM Sales INNER JOIN Customer ON Sales.Custom_ID = Customer.Custom_ID")
            results = cursor.fetchall()
        elif query_option == "total_quantity_sold":
            cursor.execute("SELECT SUM(Quantity) FROM Sales")
            results = cursor.fetchall()
        elif query_option == "products_above_avg_sales":
            cursor.execute("SELECT Prod_ID FROM Sales "
                           "WHERE Quantity > (SELECT AVG(Quantity) FROM Sales)")
            results = cursor.fetchall()

    # If no results are found, return an error response
    if not results:
        return jsonify({"error": "No data returned from the procedure or query"})

    # Process the results for charting
    labels = [f"Month {row[0]}" for row in results] if query_option == "total_sales_by_month" else [row[0] for row in results]
    data = [row[1] for row in results]  # Extract second column as data for the chart

    # Generate the chart as a base64-encoded image
    img = io.BytesIO()
    plt.figure(figsize=(8, 4))
    # Render chart based on the selected chart type
    if chart_type == "bar":
        plt.bar(labels, data, color="skyblue", label="Sales Data")
    elif chart_type == "line":
        plt.plot(labels, data, marker="o", color="green", label="Sales Trend")
    elif chart_type == "pie":
        plt.pie(data, labels=labels, autopct='%1.1f%%', startangle=140)

    # Customize chart with labels, legends, and title
    if chart_type != "pie":  # Legends are shown differently for pie charts
        plt.legend(title="Data Categories", loc="best")
    plt.xlabel("Category")
    plt.ylabel("Value")
    plt.title(query_option.replace('_', ' ').title())
    plt.tight_layout()
    plt.savefig(img, format="png")
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()

    cursor.close()
    return jsonify({'plot_url': plot_url})
    

# Employee Dashboard - Show Sales Data
# Employee Dashboard - Show Sales Data
@app.route('/employee_dashboard')
def employee_dashboard():
    
    if 'loggedin' in session and session['role'] == 'Employee':
        cursor = conn.cursor(dictionary=True)
        # Joining Sales with Users, Customer, and Product tables to fetch names instead of IDs
        query = '''
            SELECT 
                Sales.Invoice_ID, 
                Users.username AS Employee_Name,
                Customer.Name AS Customer_Name,
                Customer.Custom_Type AS Customer_Type,
                Product.Prod_Name AS Product_Name,
                Sales.Quantity,
                Sales.Total_Amount,
                Sales.Sale_Date
            FROM Sales
            JOIN Users ON Sales.user_id = Users.user_id
            JOIN Customer ON Sales.Custom_ID = Customer.Custom_ID
            JOIN Product ON Sales.Prod_ID = Product.Prod_ID
        '''
        cursor.execute(query)
        sales_data = cursor.fetchall()
        cursor.close()
        return render_template('employee_dashboard.html', sales_data=sales_data)
    flash('Please log in as an employee to access this page.', 'danger')
    return redirect(url_for('login'))
@app.route('/employee')
def employee():
    if 'loggedin' in session and session['role'] == 'Employee':
        # Fetch product list to display in the dropdown
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT Prod_ID, Prod_Name FROM Product')
        products = cursor.fetchall()
        cursor.close()
        
        return render_template('employee.html', products=products)
    flash('Please log in as an employee to access this page.', 'danger')
    return redirect(url_for('login'))

@app.route('/add_existing_customer_purchase', methods=['POST'])
def add_existing_customer_purchase():
    data = request.form
    customer_name = data['customer_name']
    product_id = data['product_id']
    quantity = int(data['quantity'])
    sale_date = data['date']

    cursor = conn.cursor()
    user_id = session.get('user_id')  # Get the logged-in user's ID from the session

    if not user_id:
        flash("Please log in to add a purchase.", "error")
        return redirect(url_for('login'))

    # Step 1: Look up the customer by name
    cursor.execute("SELECT Custom_ID FROM Customer WHERE Name = %s", (customer_name,))
    customer = cursor.fetchone()

    if customer:
        custom_id = customer[0]
        cursor.execute("SELECT Unit_Price FROM Product WHERE Prod_ID = %s", (product_id,))
        product = cursor.fetchone()

        if product:
            unit_price = float(product[0])
            total_amount = unit_price * quantity

            cursor.execute("""
                INSERT INTO Sales (user_id, Custom_ID, Prod_ID, Quantity, Total_Amount, Sale_Date) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, custom_id, product_id, quantity, total_amount, sale_date))

            conn.commit()
            flash("Sale successfully added!", "success")
        else:
            flash("Product not found.", "error")
    else:
        flash("Customer not found. Please add them as a new customer first.", "error")

    cursor.close()
    return redirect(url_for('employee'))

@app.route('/add_new_customer_purchase', methods=['POST'])
def add_new_customer_purchase():
    data = request.form

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Customer (Name, Gender, Phone_No, Email, Custom_Type) 
        VALUES (%s, %s, %s, %s, %s)
    """, (data['name'], data['gender'], data['phone'], data['email'], data['custom_type']))
    
    conn.commit()
    customer_id = cursor.lastrowid

    product_id = data['product_id']
    cursor.execute("SELECT Unit_Price FROM Product WHERE Prod_ID = %s", (product_id,))
    product = cursor.fetchone()
    
    if product:
        unit_price = float(product[0])
        quantity = int(data['quantity'])
        total_amount = unit_price * quantity

        user_id = session.get('user_id')  # Get the logged-in user's ID from the session

        if not user_id:
            flash("Please log in to add a purchase.", "error")
            return redirect(url_for('login'))

        cursor.execute("""
            INSERT INTO Sales (user_id, Custom_ID, Prod_ID, Quantity, Total_Amount, Sale_Date) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, customer_id, product_id, quantity, total_amount, data['date']))

        conn.commit()
        flash("New customer and sale successfully added!", "success")
    else:
        flash("Product not found. Sale not added.", "error")
    
    cursor.close()
    return redirect(url_for('employee'))

@app.route('/delete_sale/<int:invoice_id>', methods=['POST'])
def delete_sale(invoice_id):
    if 'loggedin' in session and session['role'] == 'Employee':
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM Sales WHERE Invoice_ID = %s', (invoice_id,))
            conn.commit()
            cursor.close()
            return jsonify({"success": True})
        except Exception as e:
            print(f"Error deleting sale: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": False, "error": "Unauthorized access"}), 403

@app.route('/update_sale/<int:invoice_id>', methods=['GET'])
def update_sale(invoice_id):
    if 'loggedin' in session and session['role'] == 'Employee':
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM Sales WHERE Invoice_ID = %s', (invoice_id,))
        sale = cursor.fetchone()
        cursor.close()
        if sale:
            return render_template('update_sale.html', sale=sale)
        else:
            return "Sale not found", 404
    return redirect(url_for('login'))

@app.route('/update_sale/<int:invoice_id>', methods=['POST'])
def update_sale_submit(invoice_id):
    if 'loggedin' in session and session['role'] == 'Employee':
        Custom_ID = request.form['Custom_ID']
        Prod_ID = request.form['Prod_ID']
        Quantity = request.form['Quantity']
        Total_Amount = request.form['Total_Amount']
        Sale_Date = request.form['Sale_Date']

        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE Sales
                SET Custom_ID = %s, Prod_ID = %s, Quantity = %s, Total_Amount = %s, Sale_Date = %s
                WHERE Invoice_ID = %s
            ''', (Custom_ID, Prod_ID, Quantity, Total_Amount, Sale_Date, invoice_id))
            conn.commit()
            cursor.close()
            return redirect(url_for('employee_dashboard'))
        except Exception as e:
            print(f"Error updating sale: {e}")
            return "An error occurred while updating the sale.", 500
    return redirect(url_for('login'))


# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))
    
    return f"Welcome to the dashboard, {session['username']}! Your role is {session['role']}."

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
