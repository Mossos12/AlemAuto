import streamlit as st
import pandas as pd
import os
from datetime import datetime
import shutil
import re
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import requests
from bs4 import BeautifulSoup

# Set page configuration
st.set_page_config(
    page_title="Automotive Sales Management",
    page_icon="🚗",
    layout="wide"
)

# Initialize Firebase
def initialize_firebase():
    # Check if Firebase is already initialized
    if not firebase_admin._apps:
        # Define the absolute path to the key file
        key_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'firebase-key.json')
        
        try:
            # Check if the key file exists
            if os.path.exists(key_file_path):
                # Print debug info
                st.sidebar.success(f"Found key file at: {key_file_path}")
                
                # Initialize Firebase with the key file
                cred = credentials.Certificate(key_file_path)
                firebase_admin.initialize_app(cred)
                st.sidebar.success("Connected to Firebase successfully!")
                return True
            else:
                st.error(f"Firebase key file not found at: {key_file_path}")
                return False
        except Exception as e:
            st.error(f"Error initializing Firebase: {e}")
            return False
    return True

# Function to load data from Firestore
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data():
    if not initialize_firebase():
        return pd.DataFrame(columns=[
            "Make", "Mode", "Model Year", "VIN", "Mileage", "VEHCLE COST", 
            "Parts Cost", "Labour Cost", "Title State", "Status", 
            "Cost", "Mark Up", "Price", "Market Value", "Calling", "Remark",
            "Sold_Date", "Sold_Price"
        ])
    
    try:
        # Connect to Firestore
        db = firestore.client()
        # Get all vehicles from the collection
        vehicles_ref = db.collection('vehicles')
        vehicles = vehicles_ref.stream()
        
        # Convert to list of dictionaries
        vehicles_data = []
        for vehicle in vehicles:
            data = vehicle.to_dict()
            # Add document ID as a field (will be useful for updates)
            data['document_id'] = vehicle.id
            vehicles_data.append(data)
        
        # Convert to DataFrame
        if vehicles_data:
            df = pd.DataFrame(vehicles_data)
            return df
        else:
            return pd.DataFrame(columns=[
                "Make", "Mode", "Model Year", "VIN", "Mileage", "VEHCLE COST", 
                "Parts Cost", "Labour Cost", "Title State", "Status", 
                "Cost", "Mark Up", "Price", "Market Value", "Calling", "Remark",
                "Sold_Date", "Sold_Price"
            ])
    except Exception as e:
        st.error(f"Error loading data from Firebase: {e}")
        return pd.DataFrame(columns=[
            "Make", "Mode", "Model Year", "VIN", "Mileage", "VEHCLE COST", 
            "Parts Cost", "Labour Cost", "Title State", "Status", 
            "Cost", "Mark Up", "Price", "Market Value", "Calling", "Remark",
            "Sold_Date", "Sold_Price"
        ])

# Function to create backup in Firestore
def create_backup(df):
    if not initialize_firebase():
        return None
    
    try:
        # Connect to Firestore
        db = firestore.client()
        
        # Create a timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create a backup collection
        backup_ref = db.collection('backups').document(timestamp)
        
        # Convert DataFrame to list of dictionaries (excluding document_id)
        df_copy = df.copy()
        if 'document_id' in df_copy.columns:
            df_copy = df_copy.drop(columns=['document_id'])
        vehicles_data = df_copy.to_dict('records')
        
        # Save to Firestore
        backup_ref.set({
            'timestamp': timestamp,
            'vehicles': vehicles_data
        })
        
        return timestamp
    except Exception as e:
        st.error(f"Error creating backup: {e}")
        return None

# Function to add a single vehicle to Firestore
def add_vehicle(vehicle_data):
    if not initialize_firebase():
        return False
    
    try:
        # Connect to Firestore
        db = firestore.client()
        
        # Check if VIN already exists
        vin = vehicle_data.get('VIN')
        if vin:
            existing = db.collection('vehicles').where('VIN', '==', vin).limit(1).get()
            if len(existing) > 0:
                st.error(f"Vehicle with VIN {vin} already exists.")
                return False
        
        # Add the vehicle to Firestore
        db.collection('vehicles').add(vehicle_data)
        return True
    except Exception as e:
        st.error(f"Error adding vehicle: {e}")
        return False

# Function to update a vehicle in Firestore
def update_vehicle(vin, vehicle_data):
    if not initialize_firebase():
        return False
    
    try:
        # Connect to Firestore
        db = firestore.client()
        
        # Find the document with this VIN
        docs = db.collection('vehicles').where('VIN', '==', vin).limit(1).get()
        
        if not docs:
            st.error(f"Vehicle with VIN {vin} not found.")
            return False
        
        # Convert any field names with spaces to use Firestore's field path syntax
        sanitized_data = {}
        for key, value in vehicle_data.items():
            # Replace field names with spaces to use dot notation or prevent such fields
            sanitized_key = key.replace(" ", "_")
            sanitized_data[sanitized_key] = value
        
        # Update the vehicle
        for doc in docs:
            doc_ref = db.collection('vehicles').document(doc.id)
            doc_ref.update(sanitized_data)
            return True
        
        return False
    except Exception as e:
        st.error(f"Error updating vehicle: {e}")
        return False

# Function to mark a vehicle as sold
def mark_vehicle_as_sold(vin, sold_price, sold_date=None):
    if not initialize_firebase():
        return False
    
    try:
        # Connect to Firestore
        db = firestore.client()
        
        # Find the document with this VIN
        docs = db.collection('vehicles').where('VIN', '==', vin).limit(1).get()
        
        if not docs:
            st.error(f"Vehicle with VIN {vin} not found.")
            return False
        
        # Use today's date if not provided
        if not sold_date:
            sold_date = datetime.now().strftime("%Y-%m-%d")
        
        # Update the vehicle to mark as sold
        for doc in docs:
            doc_ref = db.collection('vehicles').document(doc.id)
            doc_ref.update({
                "Status": "Sold",
                "Sold_Date": sold_date,
                "Sold_Price": sold_price
            })
            return True
        
        return False
    except Exception as e:
        st.error(f"Error marking vehicle as sold: {e}")
        return False

# Function to validate VIN
def validate_vin(vin):
    # Basic VIN validation - 17 alphanumeric characters (excluding I, O, Q)
    if not vin:
        return False
    pattern = re.compile(r'^[A-HJ-NPR-Z0-9]{17}$')
    return bool(pattern.match(vin))

# Function to fetch vehicle details from VIN
def fetch_vehicle_details(vin):
    """
    Get vehicle details from NHTSA VIN Decoder API
    """
    try:
        # Call the NHTSA API to decode the VIN
        url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract relevant vehicle details
            results = data.get('Results', [])
            vehicle_details = {}
            
            for item in results:
                variable = item.get('Variable')
                value = item.get('Value')
                
                if variable == 'Make':
                    vehicle_details['make'] = value
                elif variable == 'Model':
                    vehicle_details['model'] = value
                elif variable == 'Model Year':
                    vehicle_details['year'] = value
                elif variable == 'Trim':
                    vehicle_details['trim'] = value
                elif variable == 'Engine Model':
                    vehicle_details['engine'] = value
                
            return vehicle_details
        else:
            return None
    except Exception as e:
        st.error(f"Error fetching vehicle details: {e}")
        return None

# Calculate market value with user input option
def calculate_market_value(vehicle_cost, parts_cost, labour_cost, markup, manual_market_value=None):
    try:
        vehicle_cost = float(vehicle_cost) if vehicle_cost else 0
        parts_cost = float(parts_cost) if parts_cost else 0
        labour_cost = float(labour_cost) if labour_cost else 0
        markup = float(markup) if markup else 0
        
        # Calculate cost and price
        cost = vehicle_cost + parts_cost + labour_cost
        price = cost * (1 + markup/100)
        
        # Use manual market value if provided, otherwise calculate
        if manual_market_value is not None and manual_market_value != "":
            try:
                market_value = float(manual_market_value)
            except ValueError:
                st.warning("Invalid market value input. Using calculated value instead.")
                market_value = price * 1.1  # Default calculation
        else:
            market_value = price * 1.1  # Default: 10% above price
        
        return cost, price, market_value
    except ValueError:
        return None, None, None

# Main application
def main():
    st.title("Automotive Sales Management")
    
    # Sidebar navigation
    page = st.sidebar.radio("Navigation", ["View Inventory", "Sold Vehicles", "Add New Vehicle", "Edit Vehicle", "Mark as Sold"])
    
    # Load data
    df = load_data()
    display_df = df.copy()
    
    # Remove document_id from display DataFrame if it exists
    if 'document_id' in display_df.columns:
        display_df = display_df.drop(columns=['document_id'])
    
    if page == "View Inventory":
        st.header("Current Inventory")
        
        # Search filters
        st.subheader("Search Filters")
        col1, col2, col3 = st.columns(3)
        
        all_makes = ["All"] + sorted(df["Make"].dropna().unique().tolist())
        selected_make = col1.selectbox("Make", all_makes)
        
        all_statuses = ["All", "Available", "In Process", "Hold"]
        selected_status = col2.selectbox("Status", all_statuses)
        
        # Filter by Make if not "All"
        filtered_df = display_df
        if selected_make != "All":
            filtered_df = filtered_df[filtered_df["Make"] == selected_make]
        
        # Filter by Status if not "All"
        if selected_status != "All":
            filtered_df = filtered_df[filtered_df["Status"] == selected_status]
        
        # Only show non-sold vehicles in the main inventory
        filtered_df = filtered_df[filtered_df["Status"] != "Sold"]
        
        # Display data
        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True)
            st.write(f"Total Vehicles: {len(filtered_df)}")
        else:
            st.info("No vehicles found with the selected filters. Add a vehicle to get started.")
    
    elif page == "Sold Vehicles":
        st.header("Sold Vehicles")
        
        # Filter to show only sold vehicles
        sold_df = display_df[display_df["Status"] == "Sold"]
        
        if not sold_df.empty:
            st.dataframe(sold_df, use_container_width=True)
            
            # Calculate total profit
            # Make sure columns exist and handle potential missing data
            if "Sold_Price" in sold_df.columns and "Cost" in sold_df.columns:
                # Convert to numeric, coercing errors to NaN
                sold_df["Sold_Price"] = pd.to_numeric(sold_df["Sold_Price"], errors='coerce')
                sold_df["Cost"] = pd.to_numeric(sold_df["Cost"], errors='coerce')
                
                # Calculate total profit, dropping NaN values
                total_profit = (sold_df["Sold_Price"].fillna(0) - sold_df["Cost"].fillna(0)).sum()
                avg_markup = sold_df["Mark Up"].mean() if "Mark Up" in sold_df.columns else 0
                
                # Display summary statistics
                st.subheader("Sold Vehicle Statistics")
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Vehicles Sold", len(sold_df))
                col2.metric("Total Profit", f"${total_profit:,.2f}")
                col3.metric("Average Markup", f"{avg_markup:.2f}%")
                
                # If we have sold dates, add a chart for sales over time
                if "Sold_Date" in sold_df.columns:
                    st.subheader("Sales Over Time")
                    sold_df["Sold_Date"] = pd.to_datetime(sold_df["Sold_Date"], errors='coerce')
                    if not sold_df["Sold_Date"].isna().all():
                        # Group by month/year and count
                        sold_df['Month'] = sold_df["Sold_Date"].dt.strftime('%Y-%m')
                        sales_by_month = sold_df.groupby('Month').size().reset_index(name='Count')
                        
                        # Create a bar chart
                        st.bar_chart(sales_by_month.set_index('Month')['Count'])
        else:
            st.info("No vehicles have been marked as sold yet.")
    
    elif page == "Add New Vehicle":
        st.header("Add New Vehicle")
        
        # Form for adding a new vehicle
        with st.form("add_vehicle_form"):
            col1, col2, col3 = st.columns(3)
            
            vin = col1.text_input("VIN")
            make = col1.text_input("Make")
            mode = col1.text_input("Mode (Model)")
            model_year = col1.number_input("Model Year", min_value=1900, max_value=datetime.now().year + 1, value=datetime.now().year)
            mileage = col1.number_input("Mileage", min_value=0, value=0)
            
            vehicle_cost = col2.number_input("Vehicle Cost", min_value=0.0, value=0.0)
            parts_cost = col2.number_input("Parts Cost", min_value=0.0, value=0.0)
            labour_cost = col2.number_input("Labour Cost", min_value=0.0, value=0.0)
            title_state = col2.text_input("Title State")
            status = col2.selectbox("Status", ["Available", "In Process", "Hold"])
            
            markup = col3.number_input("Mark Up (%)", min_value=0.0, value=10.0)
            calling = col3.text_input("Calling")
            remark = col3.text_area("Remark")
            
            # Allow manual input of market value
            manual_market_value = col3.text_input("Manual Market Value (Optional)")
            
            # Calculate cost, price, and market value
            cost, price, market_value = calculate_market_value(
                vehicle_cost, parts_cost, labour_cost, markup,
                manual_market_value=manual_market_value
            )
            
            # Button to lookup VIN details
            lookup_vin = st.checkbox("Auto-fill from VIN (if available)")
            
            if lookup_vin and vin and validate_vin(vin):
                st.info("Looking up vehicle details from VIN...")
                vehicle_details = fetch_vehicle_details(vin)
                
                if vehicle_details:
                    st.success("VIN details retrieved!")
                    if not make and 'make' in vehicle_details and vehicle_details['make']:
                        make = vehicle_details['make']
                    if not mode and 'model' in vehicle_details and vehicle_details['model']:
                        mode = vehicle_details['model']
                    if 'year' in vehicle_details and vehicle_details['year']:
                        try:
                            model_year = int(vehicle_details['year'])
                        except ValueError:
                            pass
                else:
                    st.warning("Could not retrieve details from VIN.")
            
            # Display calculated values
            st.subheader("Calculated Values")
            calc_col1, calc_col2, calc_col3 = st.columns(3)
            calc_col1.metric("Total Cost", f"${cost:.2f}" if cost is not None else "N/A")
            calc_col2.metric("Selling Price", f"${price:.2f}" if price is not None else "N/A")
            calc_col3.metric("Market Value", f"${market_value:.2f}" if market_value is not None else "N/A")
            
            submitted = st.form_submit_button("Add Vehicle")
            
            if submitted:
                # Validate form data
                if not make or not mode or not vin:
                    st.error("Make, Mode, and VIN are required fields.")
                elif not validate_vin(vin):
                    st.error("Invalid VIN. VIN should be 17 alphanumeric characters.")
                else:
                    # Create new record
                    new_vehicle = {
                        "Make": make,
                        "Mode": mode,
                        "Model Year": model_year,
                        "VIN": vin,
                        "Mileage": mileage,
                        "VEHCLE COST": vehicle_cost,
                        "Parts Cost": parts_cost,
                        "Labour Cost": labour_cost,
                        "Title State": title_state,
                        "Status": status,
                        "Cost": cost,
                        "Mark Up": markup,
                        "Price": price,
                        "Market Value": market_value,
                        "Calling": calling,
                        "Remark": remark,
                        "Added_Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Add to Firestore
                    if add_vehicle(new_vehicle):
                        st.success(f"Vehicle {make} {mode} with VIN {vin} added successfully!")
                        # Refresh data
                        st.cache_data.clear()
    
    elif page == "Edit Vehicle":
        st.header("Edit Vehicle")
        
        # Filter out sold vehicles
        edit_df = df[df["Status"] != "Sold"]
        
        # VIN selection for editing
        if not edit_df.empty:
            vehicles = edit_df[["Make", "Mode", "VIN"]].apply(
                lambda x: f"{x['Make']} {x['Mode']} (VIN: {x['VIN']})", axis=1
            ).tolist()
            
            selected_vehicle = st.selectbox("Select Vehicle to Edit", vehicles)
            
            if selected_vehicle:
                vin_to_edit = selected_vehicle.split("(VIN: ")[1].split(")")[0]
                vehicle_data = edit_df[edit_df["VIN"] == vin_to_edit].iloc[0].to_dict()
                
                with st.form("edit_vehicle_form"):
                    col1, col2, col3 = st.columns(3)
                    
                    make = col1.text_input("Make", value=vehicle_data.get("Make", ""))
                    mode = col1.text_input("Mode (Model)", value=vehicle_data.get("Mode", ""))
                    model_year = col1.number_input("Model Year", min_value=1900, max_value=datetime.now().year + 1, value=int(vehicle_data.get("Model Year", datetime.now().year)))
                    vin = col1.text_input("VIN", value=vehicle_data.get("VIN", ""), disabled=True)
                    mileage = col1.number_input("Mileage", min_value=0, value=int(vehicle_data.get("Mileage", 0)))
                    
                    vehicle_cost = col2.number_input("Vehicle Cost", min_value=0.0, value=float(vehicle_data.get("VEHCLE COST", 0.0)))
                    parts_cost = col2.number_input("Parts Cost", min_value=0.0, value=float(vehicle_data.get("Parts Cost", 0.0)))
                    labour_cost = col2.number_input("Labour Cost", min_value=0.0, value=float(vehicle_data.get("Labour Cost", 0.0)))
                    title_state = col2.text_input("Title State", value=vehicle_data.get("Title State", ""))
                    status = col2.selectbox("Status", ["Available", "In Process", "Hold"], 
                                           index=["Available", "In Process", "Hold"].index(vehicle_data.get("Status", "Available")))
                    
                    markup = col3.number_input("Mark Up (%)", min_value=0.0, value=float(vehicle_data.get("Mark Up", 10.0)))
                    calling = col3.text_input("Calling", value=vehicle_data.get("Calling", ""))
                    remark = col3.text_area("Remark", value=vehicle_data.get("Remark", ""))
                    
                    # Allow manual input of market value
                    current_market_value = vehicle_data.get("Market Value", "")
                    manual_market_value = col3.text_input(
                        "Manual Market Value", 
                        value=str(current_market_value) if current_market_value else ""
                    )
                    
                    # Calculate cost, price, and market value
                    cost, price, market_value = calculate_market_value(
                        vehicle_cost, parts_cost, labour_cost, markup,
                        manual_market_value=manual_market_value
                    )
                    
                    # Display calculated values
                    st.subheader("Calculated Values")
                    calc_col1, calc_col2, calc_col3 = st.columns(3)
                    calc_col1.metric("Total Cost", f"${cost:.2f}" if cost is not None else "N/A")
                    calc_col2.metric("Selling Price", f"${price:.2f}" if price is not None else "N/A")
                    calc_col3.metric("Market Value", f"${market_value:.2f}" if market_value is not None else "N/A")
                    
                    submitted = st.form_submit_button("Update Vehicle")
                    
                    if submitted:
                        # Validate form data
                        if not make or not mode:
                            st.error("Make and Mode are required fields.")
                        else:
                            # Create updated record
                            updated_vehicle = {
                                "Make": make,
                                "Mode": mode,
                                "Model Year": model_year,
                                "Mileage": mileage,
                                "VEHCLE COST": vehicle_cost,
                                "Parts Cost": parts_cost,
                                "Labour Cost": labour_cost,
                                "Title State": title_state,
                                "Status": status,
                                "Cost": cost,
                                "Mark Up": markup,
                                "Price": price,
                                "Market Value": market_value,
                                "Calling": calling,
                                "Remark": remark,
                                "Updated_Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            # Update in Firestore
                            if update_vehicle(vin, updated_vehicle):
                                st.success(f"Vehicle {make} {mode} with VIN {vin} updated successfully!")
                                # Refresh data
                                st.cache_data.clear()
        else:
            st.info("No vehicles found to edit. Add a vehicle first.")
    
    elif page == "Mark as Sold":
        st.header("Mark Vehicle as Sold")
        
        # Filter to show only available vehicles
        available_df = df[df["Status"] != "Sold"]
        
        if not available_df.empty:
            vehicles = available_df[["Make", "Mode", "VIN", "Price"]].apply(
                lambda x: f"{x['Make']} {x['Mode']} (VIN: {x['VIN']}) - Listed: ${float(x['Price']):.2f}", 
                axis=1
            ).tolist()
            
            selected_vehicle = st.selectbox("Select Vehicle to Mark as Sold", vehicles)
            
            if selected_vehicle:
                vin_to_mark = selected_vehicle.split("(VIN: ")[1].split(")")[0]
                vehicle_data = available_df[available_df["VIN"] == vin_to_mark].iloc[0].to_dict()
                
                with st.form("mark_sold_form"):
                    col1, col2 = st.columns(2)
                    
                    # Display vehicle info
                    col1.markdown(f"**Make:** {vehicle_data.get('Make', '')}")
                    col1.markdown(f"**Model:** {vehicle_data.get('Mode', '')}")
                    col1.markdown(f"**Year:** {vehicle_data.get('Model Year', '')}")
                    col1.markdown(f"**VIN:** {vehicle_data.get('VIN', '')}")
                    
                    # Get listed price
                    listed_price = float(vehicle_data.get('Price', 0))
                    col2.markdown(f"**Listed Price:** ${listed_price:.2f}")
                    
                    # Get cost
                    cost = float(vehicle_data.get('Cost', 0))
                    col2.markdown(f"**Total Cost:** ${cost:.2f}")
                    
                    # Input fields for sale
                    sold_price = st.number_input("Actual Sold Price", 
                                               min_value=0.0, 
                                               value=listed_price)
                    
                    sold_date = st.date_input("Sale Date", 
                                            value=datetime.now())
                    
                    # Calculate profit
                    profit = sold_price - cost
                    profit_percentage = (profit / cost * 100) if cost > 0 else 0
                    
                    # Display profit information
                    profit_col1, profit_col2 = st.columns(2)
                    profit_col1.metric("Profit", f"${profit:.2f}")
                    profit_col2.metric("Profit %", f"{profit_percentage:.2f}%")
                    
                    # Sale notes
                    sale_notes = st.text_area("Sale Notes")
                    
                    submitted = st.form_submit_button("Confirm Sale")
                    
                    if submitted:
                        # Prepare sale data
                        sold_vehicle_data = {
                            "Status": "Sold",
                            "Sold_Price": sold_price,
                            "Sold_Date": sold_date.strftime("%Y-%m-%d"),
                            "Profit": profit,
                            "Profit_Percentage": profit_percentage,
                            "Sale_Notes": sale_notes
                        }
                        
                        # Update in Firestore
                        if update_vehicle(vin_to_mark, sold_vehicle_data):
                            st.success(f"Vehicle marked as sold for ${sold_price:.2f}!")
                            # Refresh data
                            st.cache_data.clear()
        else:
            st.info("No available vehicles found to mark as sold.")

# Run the app
if __name__ == "__main__":
    main()
