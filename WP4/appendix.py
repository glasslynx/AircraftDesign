import os
import numpy as np
import matplotlib.pyplot as plt

def calculate_airfoil_centroid(filepath, chord_length=1.0):
    x_coords = []
    y_coords = []
    
    # Read and parse the text file
    with open(filepath, 'r') as f:
        for line in f:
            try:
                parts = line.split()
                if len(parts) == 2:
                    x = float(parts[0])
                    y = float(parts[1])
                    
                    # Filter out metadata headers like "103. 103."
                    if x > 1.1 or y > 1.1:
                        continue
                        
                    x_coords.append(x)
                    y_coords.append(y)
            except ValueError:
                # Ignore lines with text
                pass

    # Convert to NumPy arrays for vectorized operations
    x_array = np.array(x_coords)
    y_array = np.array(y_coords)

    # Calculate the centroid as a ratio (average of the points)
    x_centroid_ratio = np.mean(x_array)
    y_centroid_ratio = np.mean(y_array)
    
    # Scale to the actual chord length
    x_centroid_actual = x_centroid_ratio * chord_length
    y_centroid_actual = y_centroid_ratio * chord_length
    
    # Generate the validation plot
    plt.figure(figsize=(10, 5))
    plt.plot(x_array * chord_length, y_array * chord_length, label='Airfoil Outline')
    plt.plot(x_centroid_actual, y_centroid_actual, 'ro', label='Centroid')
    plt.axis('equal')
    plt.title(f'Airfoil Centroid (Chord Length = {chord_length})')
    plt.xlabel("X Coordinate")
    plt.ylabel("Y Coordinate")
    plt.legend()
    plt.grid(True)
    plt.show()
    
    # Convert from numpy.float64 to standard Python float and return as a list
    return [float(x_centroid_actual), float(y_centroid_actual)]



#RUNNING THE CENTROID CALCULATOR

filename = "airfoil.txt" #put the name of the file here to execute
script_dir = os.path.dirname(os.path.abspath(__file__))
airfoil_path = os.path.join(script_dir, filename)

centroid = calculate_airfoil_centroid(airfoil_path, chord_length=2.5)
print(centroid)