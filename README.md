# Real-Time Toll Management and Speed Prediction Using ARIMA with a Custom Geospatial Dataset



## Overview

The goal of this project is to automatically deduct tolls from vehicles that are in toll zones. Flask was used to build the simulation environment. 
The ARIMA model is being used for the speed prediction of the vehicles.



## Features 💡

● **Automatic Toll Deduction:**  Based on the user's journey distance, tolls are automatically deducted from their account.


● **User Data Privacy:** User data is protected to ensure privacy and security.

● **Multiple Payment Vendors:** Supports a variety of payment methods for user convenience.

● **Auto-Generated Invoices:** Invoices are automatically generated for each toll transaction, allowing for easy record keeping and analysis.

● **Auto-Fine:** A simulation automatically Generate fine for a vehicle if it cross speed limit.

● **Auto-Speed Generation:** Simulation 
automatically Generate Avg. speeds for vehicles (likely for analysis purposes).

● **ARIMA Model:** Used for the speed prediction of the vehicles.

● **Data Insights:** Give user a proper analysis of their journey. 

## Requirements 📃

● Flask       
● GeoPandas    
● Requests   
● Shapely    
● Matplotlib   
● Folium  
● sqlalchemy
● scikit-learn
● plotly

## Installation 🔗
1. Download or Clone the repository. 
 
2. Create and activate a virtual environment.

step1:
```bash
$ pip install virtualenv
```
step2:
```bash
$ virtualenv env
```
step3:
```bash
$ .\env\Scripts\activate.ps1 
```
3. Install all packages                    
```bash
$ pip install -r requirements.txt
```
## Usage 🔗

### Run The Flask App:

```bash
$ python app.py
```
Click on this to open browser:

```bash
 Running on http://127.0.0.1:5000
```


# Output
## HOME ![Screenshot (203)](https://github.com/user-attachments/assets/5f43dd59-8810-4a74-afd1-d6912430b32d)
## DASHBOARD ![Screenshot (204)](https://github.com/user-attachments/assets/a0910caa-6213-4c62-b532-6eeeabc79411)
## SIMULATION ![Screenshot (206)](https://github.com/user-attachments/assets/f8d414fa-3cf4-4395-80de-3b45122eb7b8)
## ANALYSIS ![Screenshot (205)](https://github.com/user-attachments/assets/222d57cc-6d79-4426-a779-c7c738fab9c1)
## ADMIN ![Screenshot (208)](https://github.com/user-attachments/assets/478f0470-340e-4622-8250-57d1e5cdab5c)
## REPORT ![Screenshot (209)](https://github.com/user-attachments/assets/29488e3f-e0ed-4b92-b9f3-46f0cf6b4cc3)
## MAP ![Screenshot (210)](https://github.com/user-attachments/assets/fedfe1c2-4120-4d3b-aaa2-1d624ff41e34)

## Contact Us
●[Shriyansh Fasate](https://www.linkedin.com/in/shriyansh-fasate/) 
●[Shravani Shegokar](https://www.linkedin.com/in/shravani-shegokar-b09054291/) 

## Acknowledgement
● [GeoPandas](https://geopandas.org/en/stable/)  
● [Shapely](https://shapely.readthedocs.io/en)  
● [Flask](https://flask.palletsprojects.com/en/3.0.x/)
