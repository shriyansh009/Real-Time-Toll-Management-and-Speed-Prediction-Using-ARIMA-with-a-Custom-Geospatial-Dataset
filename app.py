from flask import Flask, render_template ,render_template_string , request ,flash,redirect,url_for,make_response,jsonify,session,send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField , IntegerField
from wtforms.validators import InputRequired, Length
from flask_bcrypt import Bcrypt
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from sqlalchemy import create_engine ,Column, Integer, ForeignKey ,join ,func
import pandas as pd
from sqlalchemy.orm import relationship 
from map import paths
from geopy.distance import geodesic 
import random,datetime
from compare import coordinates_allot ,paths_allocated
import io ,csv
import tilemapbase
import base64 
from io import BytesIO
from speed_analyze import analyze_data, arima_analysis, scatter_plot, speed_png , lat_long
import geopandas as gpd
from shapely.geometry import Point
import seaborn as sns


#setting up  a flask application  
app = Flask(__name__)

#######################################################################################

from flask_mail import Mail, Message
import os

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'tollserver001@gmail.com')  # Your email address
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'uesm xfll lwdx hiio')  # Your email password
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME', 'tollserver001@gmail.com')  # Default sender


mail = Mail(app)  # Initialize Flask-Mail

@app.route('/simulation', methods=['GET', 'POST'])
@login_required
def simulation():
    date_today = datetime.date.today()
    image_map = paths()  # Assuming this function returns image paths or map data
    
    if request.method == 'POST':
        starting_coordinates = request.form['DecimalInput']
        ending_coordinates = request.form['DecimalInput1']
        vehicle_type = request.form['Vehicle_type']
        
        # Allocating coordinates
        start = coordinates_allot(starting_coordinates)
        end = coordinates_allot(ending_coordinates)
        
        global file1_path
        file1_path = paths_allocated(starting_coordinates, ending_coordinates)

        # Generate random speed limits
        speed_limits = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120]  
        num_steps = random.randint(6, len(speed_limits)) 
        steps = [random.randrange(10) for _ in range(num_steps)]  
        modified_limits = [limit + step for limit, step in zip(speed_limits, steps)]
        avg_speed = round((sum(modified_limits) / 12))
        
        # Check if the start and end coordinates are the same
        if start == end:
            flash("Both the locations are the same.")
            return render_template('user/simulate.html', image=image_map)
        else:
            df1 = pd.read_csv(file1_path)  # Car simulation data
            df2 = pd.read_csv(file2_path)  # Zone data

            gdf1 = gpd.GeoDataFrame(df1, geometry=gpd.points_from_xy(df1.longitude, df1.latitude))
            gdf2 = gpd.GeoDataFrame(df2, geometry=gpd.points_from_xy(df2.longitude, df2.latitude))
            gdf2_sindex = gdf2.sindex

            def find_matches(gdf1, gdf2, threshold=0.01):
                matches = []
                for idx1, point in gdf1.iterrows():
                    possible_matches_index = list(gdf2_sindex.intersection(point.geometry.buffer(threshold).bounds))
                    possible_matches = gdf2.iloc[possible_matches_index]
                    for idx2, match_point in possible_matches.iterrows():
                        if point.geometry.distance(match_point.geometry) <= threshold:
                            matches.append((idx1, idx2))
                return matches

            matches = find_matches(gdf1, gdf2)

            if matches:
                start_lat = gdf1.loc[matches[0][0], 'latitude']
                start_lon = gdf1.loc[matches[0][0], 'longitude']
                end_lat = gdf2.loc[matches[-1][1], 'latitude']
                end_lon = gdf2.loc[matches[-1][1], 'longitude']
                
                df = pd.read_csv(file1_path)
                selected_columns = df[["longitude", "latitude"]]
                tilemapbase.init(create=True)

                expand = 0.002
                extent = tilemapbase.Extent.from_lonlat(
                    selected_columns.longitude.min() - expand,
                    selected_columns.longitude.max() + expand,
                    selected_columns.latitude.min() - expand,
                    selected_columns.latitude.max() + expand,
                )

                map_projected = selected_columns.apply(
                    lambda x: tilemapbase.project(x.longitude, x.latitude), axis=1
                ).apply(pd.Series)
                map_projected.columns = ["x", "y"]

                tiles = tilemapbase.tiles.build_OSM()
                fig, ax = plt.subplots(figsize=(8, 8), dpi=300)
                ax.xaxis.set_visible(False)
                ax.yaxis.set_visible(False)
                plotter = tilemapbase.Plotter(extent, tiles, height=600)
                plotter.plot(ax, tiles, alpha=0.8)
                ax.plot(map_projected.x, map_projected.y, color="red", linewidth=1)
                plt.axis("off")

                buf = io.BytesIO()
                fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, dpi=300)
                buf.seek(0)
                image_upload = buf.getvalue()
                image_data = base64.b64encode(buf.read()).decode('utf-8')
                plt.close(fig)

                data1 = Admindata.query.filter_by(location1=starting_coordinates, location2=ending_coordinates).all()
                data2 = Admindata.query.filter_by(location1=ending_coordinates, location2=starting_coordinates).all()

                if data1:
                    for data in data1:
                        vh1 = data.Bike
                        vh2 = data.Car
                        vh3 = data.Truck
                        vh4 = data.Others
                    rate = vh4
                elif data2:
                    for data in data2:
                        vh1 = data.Bike
                        vh2 = data.Car
                        vh3 = data.Truck
                        vh4 = data.Others
                    rate = vh4

                rate = vehicle_allocate(vehicle_type, vh1, vh2, vh3, vh4)
                rates = rate

                distance_rest = geodesic((start_lon, start_lat), (end_lon, end_lat)).km
                distance = round(distance_rest, 3)

                time_hr = distance / avg_speed
                time = round(time_hr * 60)

                tax = round((distance) * (rates), 2)
                total_fine = calculate_fine(avg_speed, 50)
                total_tax = round((total_fine + tax))

                def send_email(username, email, start, end, vehicle, distance, speed, tax, fine, total, balance):
                    subject = "🚗 Toll Simulation Completed!"
                    body = f"""
Hello {username},

Your simulation has been successfully completed. Here are the details:

🔹 **Route**: {start} → {end}
🔹 **Vehicle Type**: {vehicle}
🔹 **Distance**: {distance} km
🔹 **Speed**: {speed} km/h
🔹 **Tax**: ₹{tax}
🔹 **Fine**: ₹{fine}
🔹 **Total Charge**: ₹{total}
🔹 **Remaining Balance**: ₹{round(balance,2)}

Thank you for using our service!

Best regards,  
GPS Toll System Team
                    """
                    try:
                        msg = Message(subject, recipients=[email], body=body)
                        mail.send(msg)
                        print(f"✅ Email sent to {email}")
                    except Exception as e:
                        print(f"❌ Email sending failed: {str(e)}")

                send_email(
                    current_user.username, current_user.email,
                    starting_coordinates, ending_coordinates,
                    vehicle_type, distance, avg_speed, tax, total_fine, total_tax,
                    current_user.balance
                )
                flash("🚀 Simulation completed! A confirmation email has been sent.")

                balance = current_user.balance
                id = current_user.id
                user_id_current=current_user.id
                user = User.query.get(id)
                if balance < tax:
                    flash("Insufficient amount")
                else:
                    if total_fine > 0:
                        user = User.query.get(id)
                        user.balance = user.balance - tax - total_fine
                        db.session.commit()
                        flash("Amount is deducted! Please check account for more")
                        flash("Fine is charged!!")
                    else:
                        deduct_tax(tax, id)
                        flash("Amount is deducted! Please check account for more")

                bill1 = Bill(destination1=starting_coordinates,
                            destination2=ending_coordinates,
                            fine=total_fine,
                            total=total_tax,
                            distance=distance,
                            tax=tax,
                            user_id=id,
                            vehicle=vehicle_type,
                            image=image_upload)
                user.bills.append(bill1)
                db.session.add(user)
                db.session.commit()

                List = [starting_coordinates, ending_coordinates, vehicle_type, total_fine, total_tax, distance, tax, user_id_current]
                file_path = 'datasets/simulation.csv'

                with open(file_path, 'a', newline='') as f_object:
                    writer_object = csv.writer(f_object)
                    writer_object.writerow(List)
                    f_object.close()

            else:
                render_template('user/simulate.html', image=image_map)

        return render_template('user/result.html',
                               distance=distance,
                               vehicle=vehicle_type,
                               speed=avg_speed,
                               tax=tax,
                               username=current_user.username,
                               number=current_user.mobnumber,
                               id=current_user.id,
                               destination1=starting_coordinates.upper(),
                               destination2=ending_coordinates.upper(),
                               date=date_today,
                               email=current_user.email,
                               time=time,
                               fine=total_fine,
                               total=total_tax,
                               image=image_data,
                               bike=vh1,
                               car=vh2,
                               truck=vh3,
                               other=vh4)

    else:
        return render_template('user/simulate.html', image=image_map)
###########################################################################################

app.secret_key='teamtechconnect'

#creating a database for data management 
bcrypt = Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SECRET_KEY'] = 'teamtechconnect'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.app_context().push()


#admin pass to access admin page
admin_pass='techconnect'



login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))




#creating a model for database 
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50), nullable=False, unique=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    balance = db.Column(db.Float, nullable=False)
    mobnumber= db.Column(db.Integer,nullable=False)
    bills = relationship("Bill", backref="User") 

class Admindata(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    location1 = db.Column(db.String(100), nullable=False)
    location2 = db.Column(db.String(100), nullable=False)
    Bike = db.Column(db.Integer(), nullable=False)
    Car = db.Column(db.Integer(), nullable=False)
    Truck = db.Column(db.Integer(), nullable=False)
    Others = db.Column(db.Integer(), nullable=False)

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    destination1 = db.Column(db.String(100), nullable=False)
    destination2 = db.Column(db.String(100), nullable=False)
    vehicle = db.Column(db.String(100), nullable=False)
    fine = db.Column(db.Float, nullable=False)
    total= db.Column(db.Float, nullable=False)
    distance = db.Column(db.Float, nullable=False)
    tax = db.Column(db.Float, nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    image = db.Column(db.LargeBinary)





# creating a registration form using flask form 
class RegisterForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=40)], render_kw={"placeholder": ""})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": ""})
    
    balance = IntegerField()
    
    email = StringField("Email",validators=[
                           InputRequired(), Length(min=4, max=60)], render_kw={"placeholder": ""})
    
    mobnumber = IntegerField(validators=[InputRequired()], render_kw={'placeholder': ''})


    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
            username=username.data).first()
        if existing_user_username:
            return flash("That username already exists.")
            # raise ValidationError(
            #     'That username already exists. Please choose a different one.')




# creating a login form using flask form 
class LoginForm(FlaskForm):
    email = StringField("Email",validators=[
                           InputRequired(), Length(min=4, max=60)], render_kw={"placeholder": ""})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": ""})

    submit = SubmitField('Login')




#making a route page for login 
@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data): #checking the data of user in database
                login_user(user)
                return redirect(url_for('home'))
        flash("Username or password is incorrect . please register if you don't have an account")        
    return render_template('login.html', form=form)





#making a route page for profile , if the login of user satisfied
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    balance = round(current_user.balance,2)
    username = current_user.username
    number=current_user.mobnumber
    email=current_user.email
    user=current_user.id
    # bills = Bill.query.all()  # Get all bills
    bills = Bill.query.filter_by(user_id=user).all()  # Get bills for a specific user

    return render_template('user/profile.html', username=username,balance=balance,number=number,user=bills,email=email)




#logout function if user want to logout
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))




#making a route page for registration 
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    form.balance.data = 50000 # 50000Rs is given to user for demo simulation
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data) # encoding the password of user for security
        new_user = User(username=form.username.data, password=hashed_password,balance=form.balance.data,mobnumber=form.mobnumber.data,email=form.email.data)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html', form=form)






#locations and there coordinates for testing , pseudo entry and exit
locations = {
      "nagpur": ( 21.15235,79.08103),
      "wardha": ( 20.77272,78.59551),
      "karanja": (20.4983, 77.47285)
      }      

# accesssing the  define toll zone from csv file 
file2_path = "paths/zone.csv"

#setting the initial value for fine (the fine changes according to user speed and steps)
fine=120


# making a simulation process
# @app.route('/simulation', methods=['GET', 'POST'])
# @login_required
# def simulation():
#   # To access current date for bill generation 
#   date_today = datetime.date.today()
#   image_map=paths()
#   #setting the starting and ending value for simulation 
#   if request.method == 'POST':
#     starting_coordinates = request.form['DecimalInput']
#     ending_coordinates = request.form['DecimalInput1']
#     vehicle_type = request.form['Vehicle_type']
#     # weather_condition = request.form['weather']
    
    
#     #allocating the coordinates to start and end ,to check wether the coordinates are same or not  
#     start=coordinates_allot(starting_coordinates)
#     end=coordinates_allot(ending_coordinates)

#     #the pseudo entry and exit is in the form of csv , allocating the csv file into file1_path for further simulation  
#     global file1_path
#     file1_path=paths_allocated(starting_coordinates,ending_coordinates)
    
#     # generating  avg speed for simulation , changes every time 
#     speed_limits = [10, 20, 30,40,50,60,70,80,90,100,110,120]  # List of speed limits
#     num_steps = random.randint(6,len(speed_limits)) 
#     steps = [random.randrange(10) for _ in range(num_steps)]  # Generate random steps

#     # Add random steps to each speed limit
#     modified_limits = [limit + step for limit, step in zip(speed_limits, steps)]
#     avg_speed=round((sum(modified_limits)/12))
    
    
#     # checking boths the entry and exit are same or not
#     if start==end:
#         flash("both the location are same")
#         return render_template('user/simulate.html',image=image_map)
#     else:
#         df1 = pd.read_csv(file1_path) # car simulation data
#         df2 = pd.read_csv(file2_path) # zone data

#         # Create GeoDataFrames
#         gdf1 = gpd.GeoDataFrame(df1, geometry=gpd.points_from_xy(df1.longitude, df1.latitude))
#         gdf2 = gpd.GeoDataFrame(df2, geometry=gpd.points_from_xy(df2.longitude, df2.latitude))

#         # Create spatial index for gdf2
#         gdf2_sindex = gdf2.sindex

#         # Define a function to find matching points
#         def find_matches(gdf1, gdf2, threshold=0.01):
#             matches = []
#             for idx1, point in gdf1.iterrows():
#                 possible_matches_index = list(gdf2_sindex.intersection(point.geometry.buffer(threshold).bounds))
#                 possible_matches = gdf2.iloc[possible_matches_index]
#                 for idx2, match_point in possible_matches.iterrows():
#                     if point.geometry.distance(match_point.geometry) <= threshold:
#                         matches.append((idx1, idx2))
#             return matches

#         # Find matches
#         matches = find_matches(gdf1, gdf2)

# # If matches are found, fetch the starting and ending coordinates
#         if matches:
#             start_lat = gdf1.loc[matches[0][0], 'latitude']
#             start_lon = gdf1.loc[matches[0][0], 'longitude']
#             end_lat = gdf2.loc[matches[-1][1], 'latitude']
#             end_lon = gdf2.loc[matches[-1][1], 'longitude']
            
        
            
#             # reading csv file of vehicle simulation to generate the paths/route the vehicle traveled during trip.
#             df = pd.read_csv(file1_path)
#             selected_columns = df[["longitude", "latitude"]]
#             tilemapbase.init(create=True)

#             expand = 0.002
#             extent = tilemapbase.Extent.from_lonlat(
#                         selected_columns.longitude.min() - expand,
#                         selected_columns.longitude.max() + expand,
#                         selected_columns.latitude.min() - expand,
#                         selected_columns.latitude.max() + expand,
#                          )

#             map_projected = selected_columns.apply(
#             lambda x: tilemapbase.project(x.longitude, x.latitude), axis=1
#             ).apply(pd.Series)
#             map_projected.columns = ["x", "y"]

#             tiles = tilemapbase.tiles.build_OSM()

#             fig, ax = plt.subplots(figsize=(8, 8), dpi=300)
#             ax.xaxis.set_visible(False)
#             ax.yaxis.set_visible(False)
#             plotter = tilemapbase.Plotter(extent, tiles, height=600)
#             plotter.plot(ax, tiles, alpha=0.8)
#             ax.plot(map_projected.x, map_projected.y, color="red", linewidth=1)
#             plt.axis("off")

#             # Creating buffer for image data
#             buf = io.BytesIO()
#             fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, dpi=300)
#             buf.seek(0)
#             image_upload=buf.getvalue()
#             # Encoding the image data to base64 to emmbeded it into html file
#             image_data = base64.b64encode(buf.read()).decode('utf-8')
#             plt.close(fig)
#             #fetching the data from admindata to apply the current price of tax for each vehicle according to admin
#             data1 = Admindata.query.filter_by(location1=starting_coordinates, location2=ending_coordinates).all()
#             data2 = Admindata.query.filter_by(location1=ending_coordinates, location2=starting_coordinates).all()
#             if data1:
#                 for data in data1: 
#                    vh1=data.Bike
#                    vh2=data.Car
#                    vh3=data.Truck
#                    vh4=data.Others
#                 rate=vh4
#                 # print(vh1,vh2,vh3,vh4,vehicle_type) 
#             elif data2:
#                 for data in data2: 
#                    vh1=data.Bike
#                    vh2=data.Car
#                    vh3=data.Truck
#                    vh4=data.Others
#                 rate=vh4           
 
#             #Allocating the rates according to the vehicle type 
#             rate=vehicle_allocate(vehicle_type,vh1,vh2,vh3,vh4)        
#             rates=rate 

#             #calculating the  distance between staring and ending coordinates
#             distance_rest= geodesic((start_lon,start_lat), (end_lon,end_lat)).km
#             distance=round(distance_rest,3)

#             #calculating the time
#             time_hr=distance/avg_speed
#             time=round(time_hr*60)

#             #calculating the  tax
#             tax=round((distance)*(rates),2)
            
#             #total amount calculation, including fine    
#             total_fine=calculate_fine(avg_speed,50) #if the vehicle is overspeeding the fine is charged
#             total_tax=round((total_fine+tax))
            

#             #modifying the balance of current user
#             balance = current_user.balance
#             id=current_user.id

#             if balance <tax:
#                 flash("insufficent amount")

#             else:

#                 #checking is fine is charged for the simulation 
#                 if total_fine>0:
#                     user = User.query.get(id)
#                     user.balance= user.balance-tax-total_fine
#                     db.session.commit()
#                     flash("Amount is deducted ! please check account for more")
#                     flash("fine is charge!!")
                    
#                 else:   
#                     deduct_tax(tax,id)    
#                     flash("Amount is deducted ! please check account for more")
            
#             #generated bill is added to user profile 
#             user_id_current=current_user.id
#             user = User.query.get(id)
#             bill1=Bill(destination1=starting_coordinates,
#                        destination2=ending_coordinates,
#                        fine=total_fine ,
#                        total=total_tax,
#                        distance=distance,
#                        tax=tax,
#                        user_id=id,
#                        vehicle=vehicle_type,
#                        image=image_upload)  
#             user.bills.append(bill1)
#             db.session.add(user)
#             db.session.commit()
            
#             List = [ starting_coordinates, ending_coordinates, vehicle_type, total_fine,total_tax,distance, tax, user_id_current]
    
#             # File path
#             file_path = 'datasets/simulation.csv'
    
#             # Open the CSV file in append mode
#             with open(file_path, 'a', newline='') as f_object:
#                 writer_object = csv.writer(f_object)
#                 writer_object.writerow(List)
#                 f_object.close()
            

           
#         else:
#             render_template('user/simulate.html',image=image_map)          

    
    

#     # if sumulation success then the result page is displayed ,else reload the simulation page
#     return render_template('user/result.html',
#                            distance=distance,
#                            vehicle=vehicle_type,
#                            speed=avg_speed,
#                            tax=tax,
#                            username=current_user.username,
#                            number=current_user.mobnumber,
#                            id=current_user.id,
#                            destination1=starting_coordinates.upper(),
#                            destination2=ending_coordinates.upper(),
#                            date=date_today,
#                            email=current_user.email,
#                            time=time,
#                            fine=total_fine,
#                            total=total_tax,
#                            image=image_data,
#                            bike=vh1,
#                            car=vh2,
#                            truck=vh3,
#                            other=vh4
#                            )

#   #if any of the condition unsatisfied , return the to simulation page  
#   else:
#     return render_template('user/simulate.html',image=image_map)



@app.route('/view_image/<upload_id>')
def view_image(upload_id):
    upload = Bill.query.filter_by(id=upload_id).first()
    if upload:
        return send_file(BytesIO(upload.image), mimetype='image/jpeg')
    else:
        return "File not found", 404



#method to debit tax amount from current user account
def deduct_tax(tax_amount, user_id):
    user = User.query.get(user_id)
    user.balance -=tax_amount
    db.session.commit() 



# method to alloct the rate of vehicle 
def vehicle_allocate(vehicle_type,vh1,vh2,vh3,vh4):
  if vehicle_type=="Truck": 
        rate=vh3 
        return rate 
  elif vehicle_type=="Bike":
        rate=vh1 
        return rate  
  elif vehicle_type=="Car":
        rate=vh2 
        return rate 
  else :
        rate=vh4
        return rate 


#method to calculate the fine for the vehicle (if Avg.speed > 50)
def calculate_fine(speed, speed_limit):
  # Checking if driver is over speeding
  if speed >= speed_limit:
     base_fine = 100 # No fine if under speed limit
     excess_speed = speed - speed_limit
     surcharge_per_mph = 5  # Hypothetical surcharge
     speeding_surcharge = excess_speed * surcharge_per_mph
     total_fine = base_fine + speeding_surcharge 
  
  else:
      total_fine=0
  
  return total_fine






#login page for admin 
@app.route('/admin_login',methods=['GET','POST'])
@login_required
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        admin_password = request.form['pwd1']

        user = User.query.filter_by(email=email).first()
        
        #if the password and the admin password is matched give access
        if user and bcrypt.check_password_hash(user.password, password):
            if (admin_pass == admin_password):
               session['email'] = user.email
               return redirect('/admin_home')
            else:
                 flash("Username or password is incorrect . please register if you don't have an account")
                 return render_template('admin/admin_login.html',error='Invalid user')
    flash("Username or password is incorrect ")
    return render_template('admin/admin_login.html')


@app.route('/admin_home',methods=['GET','POST'])
@login_required
def ad_home():
    # Loading the CSV data into a DataFrame
    df = pd.read_csv('datasets/simulation.csv')

    # Counting total number of simulations
    line_count = len(df)
    
    # Calculate total tax collected 
    total_tax = df["tax"].sum()
    total_tax_format = round(total_tax, 2)
    
    # Calculate total fine collected
    total_fine = df["Fine"].sum()
    total_fine_deduct = round(total_fine, 2)
    
    # Calculate total amount collected
    total_amount = df["Total"].sum()
    total_amount_deduct = round(total_amount, 2)
    
    # Calculate total vehicle categories
    unique_vehicle_types = df['Vehicle'].unique()
    vehicle_categories = len(unique_vehicle_types)
    
    # Simulations with fines applied
    simulations_with_fine = df[df['Fine'] > 0]

    # Correlation matrix
    relevant_columns = ['Total', 'distance', 'tax', 'Fine']
    df_selected = df[relevant_columns]
    correlation_matrix = df_selected.corr()

    # Plot the heatmap for correlation matrix
    plt.figure(figsize=(10, 8))
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', linewidths=0.5)
    plt.title('Correlation Matrix')
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    heatmap_url = base64.b64encode(buf.getvalue()).decode('utf8')

    # Vehicle type distribution graph
    vehicle_counts = df['Vehicle'].value_counts()
    
    plt.figure(figsize=(8, 8))
    vehicle_counts.plot(kind='pie', autopct='%1.1f%%', colors=['skyblue', 'lightgreen', 'salmon', 'orange'])
    plt.title('Distribution of Vehicle Types')
    plt.ylabel('')  # Hide the y-label
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    piechart_url = base64.b64encode(buf.getvalue()).decode('utf8')
   
    return render_template('admin/ad_home.html',
                           total_simulations=line_count,
                           total_tax=total_tax_format,
                           total_fine=total_fine_deduct,
                           total_amount=total_amount_deduct,
                           vehicle_categories=vehicle_categories,
                           simulations_with_fine=simulations_with_fine.to_html(index=False),
                           heatmap_url=heatmap_url,
                           piechart_url=piechart_url
                           )



@app.route('/analyze',methods=['GET','POST'])
@login_required
def analyze():
    results_analyze=analyze_data()
    return render_template("admin/analyze_report.html",results=results_analyze)


#admin page to make changes in  the rate of the vehicle 
@app.route('/admin',methods=['GET','POST'])
@login_required
def admin():
    if request.method == 'POST':
        location1 = request.form['loc1']
        location2 = request.form['loc2']
        Bike = int(request.form['bike'])
        Car = int(request.form['car'])
        Truck = int(request.form['truck'])
        Others = int(request.form['others'])
        
        #checking is the loaction are same or not
        if (location1==location2):
           return redirect('/admin')
        existing_data = Admindata.query.filter_by(location1=location1, location2=location2).first()
        
        #checking is the data entered by the admin is same as the previous one or new 
        if existing_data:
            # Update existing data (if locations match)
            existing_data.Bike = Bike
            existing_data.Car = Car
            existing_data.Truck = Truck
            existing_data.Others = Others
            db.session.commit()
            return redirect('/price')  # Redirect to price page
        else:         
          new_data = Admindata(
            location1=location1,
            location2=location2,
            Bike=Bike,
            Car=Car,
            Truck=Truck,
            Others=Others,
        )       
        db.session.add(new_data)
        db.session.commit()
        return redirect('/price' )
      
    return render_template('admin/admin.html')




#function for admin to logout form the admin page
@app.route('/logout_ad', methods=['GET', 'POST'])
@login_required
def logout_ad():
    logout_user()
    return redirect(url_for('admin_login'))




#default page 
@app.route('/home')
@login_required
def home():
    username = current_user.username
    number=current_user.mobnumber
    return render_template('home.html',username=username,number=number)




#page to display the current prices of the toll zone according to vehicle type   
@app.route('/price')
@login_required
def price():
   new_data = Admindata.query.all()  # Fetch all users
   return render_template('price.html', new_data=new_data)




#user can see the zone under toll plaza
@app.route('/map')
@login_required
def map():
 return paths()




#page for payment to user account 
@app.route ('/recharge', methods=['GET' ,'POST'])
@login_required
def recharge():
 return render_template('user/recharge.html')


#page to show all the user data 
@app.route('/user_data')
@login_required
def userdata():
    bills=Bill.query.all()
    return render_template('admin/user_data.html',bills=bills)


#page to show about us  
@app.route('/About_us')
def about():
    return render_template('about_us.html')


#show analytics
@app.route('/Analytics')
def analytics():
    username = current_user.username
    number=current_user.mobnumber
    user_id = current_user.id
    t_fine = db.session.query(func.sum(Bill.fine)).filter(Bill.user_id == user_id).scalar()
    t_distance = db.session.query(func.sum(Bill.distance)).filter(Bill.user_id == user_id).scalar()
    t_tax = db.session.query(func.sum(Bill.tax)).filter(Bill.user_id == user_id).scalar()
    t_total = db.session.query(func.sum(Bill.total)).filter(Bill.user_id == user_id).scalar()
    loc1 = Bill.query.filter_by(user_id=user_id).order_by(Bill.id.desc()).first()
    if loc1 is None or loc1.destination1 is None:
        flash("No data available!")
        return redirect(url_for('profile'))
    else:
       destination1 = loc1.destination1
       destination2 = loc1.destination2
   
    most_recent_bill = Bill.query.order_by(Bill.id.desc()).first()


    encoded_image = None
    if most_recent_bill and most_recent_bill.image:
        encoded_image = base64.b64encode(most_recent_bill.image).decode('utf-8')  
    
    file1=paths_allocated(destination1,destination2)
    lat_lon=lat_long(file1)
    speed_analytics=speed_png(file1)
    arima=arima_analysis(file1)
    scatter=scatter_plot(file1)

    return render_template('user/analytics.html',
                           username=username,
                           number=number,
                           fine=round(t_fine,2),
                           distance=round(t_distance,2),
                           tax=round(t_tax,2),
                           total=round(t_total,2),
                           image=encoded_image,
                           bill=most_recent_bill,
                           lat_long=lat_lon,
                           speed_analytics=speed_analytics,
                           arima=arima,
                           scatter=scatter
                           )



if __name__ == "__main__":
  app.run(debug=True)
