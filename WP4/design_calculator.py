import astropy.units as u

# Design Format: [t_spar (mm), mid_spar (bool), stringer_num, stringer_area_top (mm^2), stringer_area_bottom (mm^2), t_skin (mm)]

design_spar_heavy     = [10.0 * u.mm, True,  4,  200 * u.mm**2, 200 * u.mm**2,  5.0 * u.mm]  # Design C
design_stringer_heavy = [ 8.0 * u.mm, False, 10, 400 * u.mm**2, 400 * u.mm**2,  4.0 * u.mm]  # Design B
design_skin_heavy     = [ 8.0 * u.mm, False, 4,  200 * u.mm**2, 200 * u.mm**2, 12.0 * u.mm]  # Design A

designs = [design_spar_heavy, design_stringer_heavy, design_skin_heavy]

for design in designs:
    #check if the design is feasable here
    #output: twist and deflection for each ddesign
    i = 0 #remove    
