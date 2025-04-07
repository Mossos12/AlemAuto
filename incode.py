import streamlit as st
import pandas as pd
import os
from datetime import datetime
import shutil
import re

# Set page configuration
st.set_page_config(
    page_title="Automotive Sales Management",
    page_icon="🚗",
    layout="wide"
)

# File paths
DATA_FILE = "automotive_sales.xlsx"
BACKUP_DIR = "backups"

# Ensure backup directory exists
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

# Function to create backup
def create_backup():
    if os.path.exists(DATA_FILE):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{BACKUP_DIR}/automotive_sales_{timestamp}.xlsx"
        shutil.copy2(DATA_FILE, backup_file)
        return backup_file
    return None

# Function to load data
@st.cache_data
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            return pd.read_excel(DATA_FILE)
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return pd.DataFrame(columns=[
                "Make", "Mode", "Model Year", "VIN", "Mileage", "VEHCLE COST", 
                "Parts Cost", "Labour Cost", "Title State", "Status", 
                "Cost", "Mark Up", "Price", "Market Value", "Calling", "Remark"
            ])
    else:
        return pd.DataFrame(columns=[
            "Make", "Mode", "Model Year", "VIN", "Mileage", "VEHCLE COST", 
            "Parts Cost", "Labour Cost", "Title State", "Status", 
            "Cost", "Mark Up", "Price", "Market Value", "Calling", "Remark"
        ])

# Function to save data
def save_data(df):
    try:
        # Create backup before saving
        create_backup()
        df.to_excel(DATA_FILE, index=False)
        return True
    except Exception as e:
        st.error(f"Error saving data: {e}")
        return False

# Function to validate VIN
def validate_vin(vin):
    # Basic VIN validation - 17 alphanumeric characters (excluding I, O, Q)
    if not vin:
        return False
    pattern = re.compile(r'^[A-HJ-NPR-Z0-9]{17}$')
    return bool(pattern.match(vin))

# Function to fetch KBB market value using VIN
def fetch_kbb_value(vin, make, model, year, mileage):
    try:
        import requests
        from bs4 import BeautifulSoup
        
        # This is a placeholder for KBB API integration
        # In a real implementation, you would use KBB's API or a third-party API that provides this data
        # For demonstration purposes, we'll simulate a response
        
        st.info("Attempting to fetch KBB value for VIN: " + vin)
        
        # Simulate API call - in real implementation, replace with actual API call
        # Example: https://www.kbb.com/api/vehicle-values?vin={vin}
        
        # For now, we'll return an estimated value based on the provided info
        # This should be replaced with actual API integration
        base_value = 10000  # Base value
        year_factor = (int(year) - 2010) * 1000  # Adjust based on year
        mileage_factor = -1 * (float(mileage) / 10000) * 1000  # Adjust based on mileage
        
        estimated_value = max(1000, base_value + year_factor + mileage_factor)
        
        return round(estimated_value, 2)
    except Exception as e:
        st.warning(f"Could not fetch KBB value: {e}. Using manual calculation instead.")
        return None

# Calculate market value with option to use KBB data
def calculate_market_value(vehicle_cost, parts_cost, labour_cost, markup, vin=None, make=None, model=None, year=None, mileage=None, use_kbb=False):
    try:
        vehicle_cost = float(vehicle_cost) if vehicle_cost else 0
        parts_cost = float(parts_cost) if parts_cost else 0
        labour_cost = float(labour_cost) if labour_cost else 0
        markup = float(markup) if markup else 0
        
        # Calculate cost and price
        cost = vehicle_cost + parts_cost + labour_cost
        price = cost * (1 + markup/100)
        
        # Get market value - either from KBB or through calculation
        market_value = None
        
        if use_kbb and vin and make and model and year and mileage:
            kbb_value = fetch_kbb_value(vin, make, model, year, mileage)
            if kbb_value:
                market_value = kbb_value
        
        # If KBB value wasn't retrieved, fall back to calculation
        if not market_value:
            market_value = price * 1.1  # Example: 10% above price
        
        return cost, price, market_value
    except ValueError:
        return None, None, None

# Main application
def main():
    st.title("Automotive Sales Management")
    
    # Sidebar navigation
    page = st.sidebar.radio("Navigation", ["View Inventory", "Sold Vehicles", "Add New Vehicle", "Edit Vehicle"])
    
    # Load data
    df = load_data()
    
    if page == "View Inventory":
        st.header("Current Inventory")
        
        # Search filters
        st.subheader("Search Filters")
        col1, col2, col3 = st.columns(3)
        
        all_makes = ["All"] + sorted(df["Make"].dropna().unique().tolist())
        selected_make = col1.selectbox("Make", all_makes)
        
        # Filter by Make if not "All"
        filtered_df = df
        if selected_make != "All":
            filtered_df = df[df["Make"] == selected_make]
        
        # Display data
        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True)
            st.write(f"Total Vehicles: {len(filtered_df)}")
        else:
            st.info("No vehicles found. Add a vehicle to get started.")
    
    elif page == "Sold Vehicles":
        st.header("Sold Vehicles")
        
        # Filter to show only sold vehicles
        sold_df = df[df["Status"] == "Sold"]
        
        if not sold_df.empty:
            st.dataframe(sold_df, use_container_width=True)
            
            # Calculate total profit
            total_profit = sold_df["Price"].sum() - sold_df["Cost"].sum()
            avg_markup = sold_df["Mark Up"].mean()
            
            # Display summary statistics
            st.subheader("Sold Vehicle Statistics")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Vehicles Sold", len(sold_df))
            col2.metric("Total Profit", f"${total_profit:,.2f}")
            col3.metric("Average Markup", f"{avg_markup:.2f}%")
            
            # Optionally add a chart for sold vehicles over time if you have date data
        else:
            st.info("No vehicles have been marked as sold yet.")
    
    elif page == "Add New Vehicle":
        st.header("Add New Vehicle")
        
        # Form for adding a new vehicle
        with st.form("add_vehicle_form"):
            col1, col2, col3 = st.columns(3)
            
            make = col1.text_input("Make")
            mode = col1.text_input("Mode (Model)")
            model_year = col1.number_input("Model Year", min_value=1900, max_value=datetime.now().year + 1, value=datetime.now().year)
            vin = col1.text_input("VIN")
            mileage = col1.number_input("Mileage", min_value=0, value=0)
            
            vehicle_cost = col2.number_input("Vehicle Cost", min_value=0.0, value=0.0)
            parts_cost = col2.number_input("Parts Cost", min_value=0.0, value=0.0)
            labour_cost = col2.number_input("Labour Cost", min_value=0.0, value=0.0)
            title_state = col2.text_input("Title State")
            status = col2.selectbox("Status", ["Available", "Sold", "In Process", "Hold"])
            
            markup = col3.number_input("Mark Up (%)", min_value=0.0, value=10.0)
            calling = col3.text_input("Calling")
            remark = col3.text_area("Remark")
            
            # Option to use KBB for market value
            use_kbb = col3.checkbox("Use Kelley Blue Book for Market Value", value=True)
            
            # Calculate cost, price, and market value
            cost, price, market_value = calculate_market_value(
                vehicle_cost, parts_cost, labour_cost, markup,
                vin=vin, make=make, model=mode, year=model_year, mileage=mileage,
                use_kbb=use_kbb
            )
            
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
                elif any(df["VIN"] == vin):
                    st.error(f"Vehicle with VIN {vin} already exists.")
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
                        "Remark": remark
                    }
                    
                    # Add to dataframe
                    df = pd.concat([df, pd.DataFrame([new_vehicle])], ignore_index=True)
                    
                    # Save changes
                    if save_data(df):
                        st.success(f"Vehicle {make} {mode} with VIN {vin} added successfully!")
                        # Refresh data
                        st.cache_data.clear()
    
    elif page == "Edit Vehicle":
        st.header("Edit Vehicle")
        
        # VIN selection for editing
        vehicles = df[["Make", "Mode", "VIN"]].apply(lambda x: f"{x['Make']} {x['Mode']} (VIN: {x['VIN']})", axis=1).tolist()
        if not vehicles:
            st.info("No vehicles found to edit.")
            return
        
        selected_vehicle = st.selectbox("Select Vehicle to Edit", vehicles)
        
        if selected_vehicle:
            vin_to_edit = selected_vehicle.split("(VIN: ")[1].split(")")[0]
            vehicle_data = df[df["VIN"] == vin_to_edit].iloc[0].to_dict()
            
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
                status = col2.selectbox("Status", ["Available", "Sold", "In Process", "Hold"], index=["Available", "Sold", "In Process", "Hold"].index(vehicle_data.get("Status", "Available")))
                
                markup = col3.number_input("Mark Up (%)", min_value=0.0, value=float(vehicle_data.get("Mark Up", 10.0)))
                calling = col3.text_input("Calling", value=vehicle_data.get("Calling", ""))
                remark = col3.text_area("Remark", value=vehicle_data.get("Remark", ""))
                
                # Option to use KBB for market value
                use_kbb = col3.checkbox("Use Kelley Blue Book for Market Value", value=True)
                
                # Calculate cost, price, and market value
                cost, price, market_value = calculate_market_value(
                    vehicle_cost, parts_cost, labour_cost, markup,
                    vin=vin, make=make, model=mode, year=model_year, mileage=mileage,
                    use_kbb=use_kbb
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
                        # Update record
                        df.loc[df["VIN"] == vin, "Make"] = make
                        df.loc[df["VIN"] == vin, "Mode"] = mode
                        df.loc[df["VIN"] == vin, "Model Year"] = model_year
                        df.loc[df["VIN"] == vin, "Mileage"] = mileage
                        df.loc[df["VIN"] == vin, "VEHCLE COST"] = vehicle_cost
                        df.loc[df["VIN"] == vin, "Parts Cost"] = parts_cost
                        df.loc[df["VIN"] == vin, "Labour Cost"] = labour_cost
                        df.loc[df["VIN"] == vin, "Title State"] = title_state
                        df.loc[df["VIN"] == vin, "Status"] = status
                        df.loc[df["VIN"] == vin, "Cost"] = cost
                        df.loc[df["VIN"] == vin, "Mark Up"] = markup
                        df.loc[df["VIN"] == vin, "Price"] = price
                        df.loc[df["VIN"] == vin, "Market Value"] = market_value
                        df.loc[df["VIN"] == vin, "Calling"] = calling
                        df.loc[df["VIN"] == vin, "Remark"] = remark
                        
                        # Save changes
                        if save_data(df):
                            st.success(f"Vehicle {make} {mode} with VIN {vin} updated successfully!")
                            # Refresh data
                            st.cache_data.clear()

# Run the app
if __name__ == "__main__":
    main()
