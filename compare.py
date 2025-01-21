from flask import render_template


#Method to allocate coordinate to the selected location
def coordinates_allot(loc):
  
  # Defining a dictionary to store location data
  locations = {
      "nagpur": ( 21.15235,79.08103),
      "wardha": ( 20.77272,78.59551),
      "karanja": ( 20.4983,77.47285)
  }
  
  lat= locations[loc][0]  
  lon = locations[loc][1] 

  return lat,lon

#method to allocate the dataset of selected module to the path file
def paths_allocated(loc1, loc2):
    path_map = {
        ("nagpur", "wardha"): "paths/nagpur_wardha.csv",
        ("nagpur", "karanja"): "paths/Nagpur_to_karanja.csv",
        ("karanja", "wardha"): "paths/wardha_karanja.csv",
        ("karanja", "nagpur"): "paths/Nagpur_to_karanja.csv",
        ("wardha", "nagpur"): "paths/nagpur_wardha.csv",
        ("wardha", "karanja"): "paths/wardha_karanja.csv",
    }
    
    file1_path = path_map.get((loc1, loc2))
    if file1_path:
        return file1_path
    else:
        return render_template('user/simulate.html')
