import mysql.connector

# Database connection setup
conn = mysql.connector.connect(
    host='localhost',
    username='root',
    password='priya12',
    database='sales_data4'
)

# Ensure connection is working
try:
    my_cursor = conn.cursor()
    print("Connection successfully created")
except mysql.connector.Error as err:
    print(f"Error: {err}")