import tkinter as tk
from tkinter import messagebox, simpledialog
import mysql.connector
import cv2  # For camera access
import speech_recognition as sr  # For microphone access
import requests
from twilio.rest import Client
import geocoder  # For real-time location access
from datetime import datetime
import threading
import time
import geocoder
from geopy.distance import geodesic
import mysql.connector

# Database connection
def connect_db():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',  # Replace with your MySQL password
            database=''#database name
        )
        return conn
    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", f"Error connecting to the database: {err}")
        return None
# Function to validate Aadhar number
def validate_aadhar(aadhar_number):
    if len(aadhar_number) != 12 or not aadhar_number.isdigit():
        return False
    return True


# Define a global variable to store the Aadhar number
aadhar_number_global = ""


# Function to request microphone access
def microphone_access():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Microphone access granted, you can say something...")
        audio = recognizer.listen(source)
        try:
            print(f"You said: {recognizer.recognize_google(audio)}")
        except sr.UnknownValueError:
            print("Could not understand audio")
        except sr.RequestError:
            print("Microphone error")

# Continuous image capture function
def capture_images_continuously():
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("Could not open webcam.")
        return

    cv2.namedWindow("Continuous Capture")

    try:
        while True:
            ret, frame = cam.read()
            if not ret:
                print("Failed to grab frame.")
                break

            # Display the current frame
            cv2.imshow("Continuous Capture", frame)

            # Save the current frame as an image
            img_name = f"captured_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            cv2.imwrite(img_name, frame)
            print(f"{img_name} saved!")

            # Wait for 1 second before capturing the next frame
            time.sleep(1)

            # Check for ESC key to stop the capture
            if cv2.waitKey(1) & 0xFF == 27:  # ESC key
                print("Closing...")
                break

    except KeyboardInterrupt:
        print("Continuous capture interrupted.")

    finally:
        cam.release()
        cv2.destroyAllWindows()

# Function to start continuous image capture in a separate thread
def start_continuous_capture():
    capture_thread = threading.Thread(target=capture_images_continuously, daemon=True)
    capture_thread.start()

# Function to get real-time location
def get_location():
    g = geocoder.ip('me')  # Get location based on the user's IP address
    if g.ok:
        latitude, longitude = g.latlng
        maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"
        return f"Latitude: {latitude}, Longitude: {longitude}\nGoogle Maps Link: {maps_link}"
    else:
        return "Unable to get real-time location."

# Function to send emergency SMS using Twilio
def send_emergency_sms(emergency_contacts):
    account_sid = ''  # Replace with your Twilio account SID
    auth_token = ''    # Replace with your Twilio auth token
    client = Client(account_sid, auth_token)

    message_body = "Emergency! Help needed. This is an SOS alert."
    location = get_location()  # Get real-time location

    for contact in emergency_contacts:
        message = client.messages.create(
            body=f"{message_body} Current location: {location}",
            from_='+14156500429',  # Your Twilio number
            to=contact
        )
        print(f"SOS sent to {contact}")

# Function to handle SOS feature
def open_sos_page():
    conn = connect_db()
    if conn:
        cursor = conn.cursor()

        # Assuming aadhar_number_global is the unique identifier for the user logged in
        global aadhar_number_global

        cursor.execute("SELECT contact1, contact2, contact3, contact4, contact5 FROM emergency_contacts WHERE aadhar=%s", (aadhar_number_global,))
        contacts = cursor.fetchone()

        if contacts:
            emergency_contacts = list(contacts)

            sos_window = tk.Toplevel(root)
            sos_window.title("SheShield - SOS")
            sos_window.geometry("400x400")

            tk.Label(sos_window, text="SOS Feature Activated", font=("Arial", 18), fg="red").pack(pady=20)

            # Emergency alert button functionality
            def emergency_alert():
                send_emergency_sms(emergency_contacts)
                print("Starting continuous image capture...")
                # Start continuous image capture when the emergency alert is triggered
                start_continuous_capture()

            # Request for microphone access
            microphone_access()  # Microphone access

            # Emergency alert button
            sos_button = tk.Button(sos_window, text="Press for Emergency Alert", command=emergency_alert, bg="red", fg="white", font=("Arial", 16))
            sos_button.pack(pady=20)

            sos_window.mainloop()

        else:
            messagebox.showerror("Error", "No emergency contacts found.")
        cursor.close()
        conn.close()

# Define safe zones (these can also be fetched from the database if needed)
safe_zones = [
    (28.6139, 77.2090),  # Example safe zone 1
    (28.7041, 77.1025)   # Example safe zone 2
]

# Function to fetch red zones from the MySQL database
def fetch_red_zones_from_db():
    try:
        # Establish connection to the MySQL database
        connection = mysql.connector.connect(
            host='localhost',
            user='root',  # Replace with your MySQL username
            password='SOMYA@2004',  # Replace with your MySQL password
            database='sheshield_db'  # Replace with your database name
        )
        
        cursor = connection.cursor()
        # SQL query to fetch latitude and longitude of red zones
        cursor.execute("SELECT latitude, longitude FROM red_zones")
        
        # Fetch all rows
        red_zones = cursor.fetchall()
        
        # Close the cursor and connection
        cursor.close()
        connection.close()

        # Convert the fetched data into a list of tuples
        return [(zone[0], zone[1]) for zone in red_zones]

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return []

# Function to check if the user is inside any of the safe or red zones
def check_geofence(current_location):
    # Check if inside a safe zone
    for zone in safe_zones:
        distance = geodesic(current_location, zone).meters
        if distance <= 500:  # 500 meters radius for safe zone
            print(f"You are in a safe zone near {zone}.")
            return
    
    # Fetch red zones from the database
    red_zones = fetch_red_zones_from_db()
    
    # Check if near a red zone (based on incident reports)
    for zone in red_zones:
        distance = geodesic(current_location, zone).meters
        if distance <= 500:  # 500 meters radius for red zone
            print(f"Warning! You are near a red zone around {zone}.")
            return
    
    print("You are outside both safe and red zones.")

# Function to get the user's current location without Google Maps API
def get_current_location():
    g = geocoder.ip('me')  # Get location based on IP
    if g.ok:
        return (g.latlng[0], g.latlng[1])  # Return latitude and longitude
    else:
        print("Unable to retrieve current location.")
        return None

# Main execution
user_location = get_current_location()  # Get the user's current location
if user_location:
    check_geofence(user_location)
else:
    print("Could not determine current location.")






def create_account():
    def save_account():
        global aadhar_number_global
        name = entry_name.get()
        dob = entry_dob.get()
        mobile = entry_mobile.get()
        aadhar = entry_aadhar.get()

        # Aadhar validation
        if not validate_aadhar(aadhar):
            messagebox.showerror("Input Error", "Aadhar card number must be exactly 12 digits.")
            return

        # Save the Aadhar number to the global variable
        aadhar_number_global = aadhar
        
        # Save user data into the database
        conn = connect_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (name, dob, mobile, aadhar , username , password) VALUES (%s, %s, %s, %s , %s , %s)",
                           (name, dob, mobile, aadhar))
            conn.commit()
            cursor.close()
            conn.close()
            messagebox.showinfo("Success", "Account created successfully!")
            create_credentials()
    
    # Creating account page
    account_window = tk.Toplevel(root)
    account_window.title("Create Your Account")
    account_window.geometry("400x400")
    
    tk.Label(account_window, text="Name", font=("Arial", 14)).pack(pady=10)
    entry_name = tk.Entry(account_window, font=("Arial", 12))
    entry_name.pack()
    
    tk.Label(account_window, text="Date of Birth (YYYY-MM-DD)", font=("Arial", 14)).pack(pady=10)
    entry_dob = tk.Entry(account_window, font=("Arial", 12))
    entry_dob.pack()
    tk.Label(account_window, text="Format: YYYY-MM-DD", font=("Arial", 10), fg="red").pack(pady=5)

    tk.Label(account_window, text="Mobile Number", font=("Arial", 14)).pack(pady=10)
    entry_mobile = tk.Entry(account_window, font=("Arial", 12))
    entry_mobile.pack()

    tk.Label(account_window, text="Aadhar Card Number", font=("Arial", 14)).pack(pady=10)
    entry_aadhar = tk.Entry(account_window, font=("Arial", 12))
    entry_aadhar.pack()

    tk.Button(account_window, text="Submit", command=save_account, font=("Arial", 14), bg="green", fg="white").pack(pady=20)

    
'''entry_username = tk.Entry(account_window)
entry_username.grid(row=1, column=1)
def save_account():
    username = entry_username.get()  # Consistent reference'''


# Function to create username and password
def create_credentials():
    def save_credentials():
        global aadhar_number_global
        username = entry_username.get()
        password = entry_password.get()

        # Save credentials into the database
        conn = connect_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET username=%s, password=%s WHERE aadhar=%s", 
                           (username, password, aadhar_number_global))
            conn.commit()
            cursor.close()
            conn.close()
            messagebox.showinfo("Success", "Account credentials saved successfully!")
            add_emergency_contacts()

    credentials_window = tk.Toplevel(root)
    credentials_window.title("Set Username and Password")
    credentials_window.geometry("400x300")

    tk.Label(credentials_window, text="Create Username", font=("Arial", 14)).pack(pady=10)
    entry_username = tk.Entry(credentials_window, font=("Arial", 12))
    entry_username.pack()

    tk.Label(credentials_window, text="Create Password", font=("Arial", 14)).pack(pady=10)
    entry_password = tk.Entry(credentials_window, show="*", font=("Arial", 12))
    entry_password.pack()

    tk.Button(credentials_window, text="Save Credentials", command=save_credentials, font=("Arial", 14), bg="blue", fg="white").pack(pady=20)





# Function for login
def login():
    def check_login():
        username = entry_login_username.get()
        password = entry_login_password.get()

        # Assuming a connection function like connect_db() exists for your database
        conn = connect_db()  
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
            result = cursor.fetchone()
            if result:
                global aadhar_number_global
                aadhar_number_global = result[0]
                messagebox.showinfo("Login Success", "Welcome to SheShield!")
                login_window.destroy()  # Close the login window
                open_feature_page()  # Open the feature page after successful login
            else:
                messagebox.showerror("Login Failed", "Invalid username or password.")
            cursor.close()
            conn.close()

    login_window = tk.Toplevel(root)
    login_window.title("Login")
    login_window.geometry("400x300")

    tk.Label(login_window, text="Enter Username", font=("Arial", 14)).pack(pady=10)
    entry_login_username = tk.Entry(login_window, font=("Arial", 12))
    entry_login_username.pack()

    tk.Label(login_window, text="Enter Password", font=("Arial", 14)).pack(pady=10)
    entry_login_password = tk.Entry(login_window, show="*", font=("Arial", 12))
    entry_login_password.pack()

    tk.Button(login_window, text="Login", command=check_login, font=("Arial", 14), bg="purple", fg="white").pack(pady=20)

# Function to open the feature page after successful login
def open_feature_page():
    feature_window = tk.Toplevel(root)
    feature_window.title("SheShield Features")
    feature_window.geometry("600x500")

    tk.Label(feature_window, text="Welcome to SheShield", font=("Arial", 20, "bold"), fg="purple").pack(pady=20)

    # Display the key features of the app
    tk.Label(feature_window, text="Key Features:", font=("Arial", 18), fg="blue").pack(pady=10)

    # Emergency alert with voice assistant
    tk.Label(feature_window, text="• Emergency Alert", font=("Arial", 14)).pack(anchor='w', padx=20)
    tk.Button(feature_window, text="Activate Emergency Alert", font=("Arial", 14), bg="red", fg="white", command=activate_emergency_alert).pack(pady=5)

    # Geofencing with safe zones and red zones
    tk.Label(feature_window, text="• Geofencing: Safe Zones & Red Zones", font=("Arial", 14)).pack(anchor='w', padx=20)
    tk.Button(feature_window, text="Enable Geofencing", font=("Arial", 14), bg="green", fg="white", command=enable_geofencing).pack(pady=5)

    # Local volunteer SMS alert
    tk.Label(feature_window, text="• Emergency SMS to Local Volunteer", font=("Arial", 14)).pack(anchor='w', padx=20)
    tk.Button(feature_window, text="Send Emergency SMS", font=("Arial", 14), bg="purple", fg="white", command=open_sos_page).pack(pady=5)

# Button Function Definitions
''''def activate_emergency_alert():
    # Connect to the database
    conn = connect_db()
    if conn:
        cursor = conn.cursor()
        
        # Assuming aadhar_number_global is the unique identifier for the user logged in
        global aadhar_number_global

        # Fetch emergency contacts from the 'emergency_contacts' table based on user's aadhar number
        cursor.execute("SELECT contact1, contact2, contact3, contact4, contact5 FROM emergency_contacts WHERE aadhar=%s", (aadhar_number_global,))
        contacts = cursor.fetchone()

        if contacts:
            emergency_contacts = [contact for contact in contacts if contact]  # Filter out None values

            if emergency_contacts:
                # Trigger the emergency alert
                messagebox.showinfo("Alert", "Emergency Alert activated!")

                # Send SMS to all emergency contacts
                send_emergency_sms(emergency_contacts)

                # Request microphone access
                microphone_access()

                # Start continuous image capture
                capture_images_continuously()
            else:
                messagebox.showerror("Error", "No emergency contacts found.")
        else:
            messagebox.showerror("Error", "No emergency contacts found for the user.")
        
        # Close the database connection
        cursor.close()
        conn.close()'''

def activate_emergency_alert():
    # Logic to trigger the emergency alert
    messagebox.showinfo("Alert", "Emergency Alert activated!")
    send_emergency_sms(['+919829088642'])
    microphone_access()
    capture_images_continuously()
    

def enable_geofencing():
    # Logic to enable geofencing

    messagebox.showinfo("Geofencing", "Geofencing enabled with Safe and Red zones.")
def 

# Function to create a new account
''''def create_account():
    create_window = tk.Toplevel(root)
    create_window.title("Create Account")
    create_window.geometry("400x300")

    tk.Label(create_window, text="Create Username", font=("Arial", 14)).pack(pady=10)
    entry_create_username = tk.Entry(create_window, font=("Arial", 12))
    entry_create_username.pack()

    tk.Label(create_window, text="Create Password", font=("Arial", 14)).pack(pady=10)
    entry_create_password = tk.Entry(create_window, show="*", font=("Arial", 12))
    entry_create_password.pack()

    def submit_account():
        username = entry_create_username.get()
        password = entry_create_password.get()
        conn = connect_db()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
                conn.commit()
                messagebox.showinfo("Success", "Account created successfully.")
                create_window.destroy()  # Close create account window
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"Error creating account: {err}")
            cursor.close()
            conn.close()

    tk.Button(create_window, text="Submit", command=submit_account, font=("Arial", 14), bg="green", fg="white").pack(pady=20)''
    '''
def create_account():
    def save_account():
        global aadhar_number_global
        name = entry_name.get()
        dob = entry_dob.get()
        mobile = entry_mobile.get()
        aadhar = entry_aadhar.get()
        username = entry_username.get()
        password = entry_password.get()

        # Aadhar validation
        if not validate_aadhar(aadhar):
            messagebox.showerror("Input Error", "Aadhar card number must be exactly 12 digits.")
            return

        # Save the Aadhar number to the global variable
        aadhar_number_global = aadhar
        
        # Save user data into the database
        conn = connect_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (name, dob, mobile, aadhar) VALUES (%s, %s, %s, %s)",
                           (name, dob, mobile, aadhar))
            conn.commit()
            cursor.close()
            conn.close()
            messagebox.showinfo("Success", "Account created successfully!")
            create_credentials()
    
    # Creating account page
    account_window = tk.Toplevel(root)
    account_window.title("Create Your Account")
    account_window.geometry("400x400")
    
    tk.Label(account_window, text="Name", font=("Arial", 14)).pack(pady=10)
    entry_name = tk.Entry(account_window, font=("Arial", 12))
    entry_name.pack()
    
    tk.Label(account_window, text="Date of Birth (YYYY-MM-DD)", font=("Arial", 14)).pack(pady=10)
    entry_dob = tk.Entry(account_window, font=("Arial", 12))
    entry_dob.pack()
    tk.Label(account_window, text="Format: YYYY-MM-DD", font=("Arial", 10), fg="red").pack(pady=5)

    tk.Label(account_window, text="Mobile Number", font=("Arial", 14)).pack(pady=10)
    entry_mobile = tk.Entry(account_window, font=("Arial", 12))
    entry_mobile.pack()

    tk.Label(account_window, text="Aadhar Card Number", font=("Arial", 14)).pack(pady=10)
    entry_aadhar = tk.Entry(account_window, font=("Arial", 12))
    entry_aadhar.pack()

    tk.Button(account_window, text="Submit", command=save_account, font=("Arial", 14), bg="green", fg="white").pack(pady=20)

# Function to create username and password
def create_credentials():
    def save_credentials():
        global aadhar_number_global
        username = entry_username.get()
        password = entry_password.get()

        # Save credentials into the database
        conn = connect_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET username=%s, password=%s WHERE aadhar=%s", 
                           (username, password, aadhar_number_global))
            conn.commit()
            cursor.close()
            conn.close()
            messagebox.showinfo("Success", "Account credentials saved successfully!")
            add_emergency_contacts()

    credentials_window = tk.Toplevel(root)
    credentials_window.title("Set Username and Password")
    credentials_window.geometry("400x300")

    tk.Label(credentials_window, text="Create Username", font=("Arial", 14)).pack(pady=10)
    entry_username = tk.Entry(credentials_window, font=("Arial", 12))
    entry_username.pack()

    tk.Label(credentials_window, text="Create Password", font=("Arial", 14)).pack(pady=10)
    entry_password = tk.Entry(credentials_window, show="*", font=("Arial", 12))
    entry_password.pack()

    tk.Button(credentials_window, text="Save Credentials", command=save_credentials, font=("Arial", 14), bg="blue", fg="white").pack(pady=20)



# Main application
root = tk.Tk()
root.title("SheShield - Women Safety App")
root.geometry("400x400")

tk.Label(root, text="SheShield", font=("Arial", 24, "bold"), fg="purple").pack(pady=20)
tk.Label(root, text="Welcome to the Women Safety App", font=("Arial", 16)).pack(pady=10)

# Buttons for login and account creation
tk.Button(root, text="Login", command=login, font=("Arial", 14), bg="purple", fg="white").pack(pady=10)
tk.Button(root, text="Create New Account", command=create_account, font=("Arial", 14), bg="green", fg="white").pack(pady=10)

root.mainloop()