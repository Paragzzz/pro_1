from flask import Flask, render_template, request, redirect
import pymysql

app = Flask(__name__)

# Database connection details
DB_HOST = "sql12.freesqldatabase.com"
DB_USER = "sql12757212"
DB_PASSWORD = "lFjVTrpNZG"
DB_NAME = "sql12757212"

# Function to create the table if it doesn't exist
def create_table():
    connection = pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )
    cursor = connection.cursor()
    # SQL to create table if it doesn't exist
    create_table_query = """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL
    )
    """
    cursor.execute(create_table_query)
    connection.commit()
    cursor.close()
    connection.close()

# Route: Homepage with Form
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]

        # Insert data into database
        connection = pymysql.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
        )
        cursor = connection.cursor()
        query = "INSERT INTO users (name, email) VALUES (%s, %s)"
        cursor.execute(query, (name, email))
        connection.commit()
        cursor.close()
        connection.close()

        return redirect("/data")

    return render_template("index.html")

# Route: Display Data
@app.route("/data")
def display_data():
    # Fetch data from database
    connection = pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )
    cursor = connection.cursor()
    query = "SELECT * FROM users"
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template("display.html", data=data)

if __name__ == "__main__":
    # Ensure the table exists before starting the app
    create_table()
    app.run(debug=True)
