import numpy as np
from scipy.interpolate import interp1d
from numpy.polynomial.polynomial import Polynomial
from Joule_sum_data_builder import load_sum_obj
from sklearn.metrics import mean_absolute_error


def local_reg_adjust_window(time_points, metric_points, deg=2, min_data_points_to_smooth=10, throw_min_error=False, nominal_window_size=14, force_start_value=True):
    """
    This function will smooth the data using local polynomial regression without additional
    weighting. 

    Args:
    @time_points(np.array): time points to smooth
    @metric_points(np.array): metric points to smooth (capacity or resistance either in % or Ah)
    @deg(int): degree of the polynomial to fit
    @min_data_points_to_smooth(int): The minimum data points to smooth. If below this it will either throw an
                                        error if throw_min_error is true, or just no-smoothing if True. 
    @nominal_window_size(int): Size of the window to fit the polynomial
    @force_start_value(Boolean): Forces the starting value to match the initial value of metric_points

    Returns:
    @smoothed_metric_points(np.array): Smoothed metric points after local polynomial regression
    """

    #Round to allow odd nominal_window_size. Remember round, rounds to the even number.
    half_window = round(nominal_window_size/2)
    smoothed_metric_points = np.zeros(len(time_points))
    start_idx_list = []
    end_idx_list = []

    #If data is too short either throw error or return it as is
    if len(time_points) <= min_data_points_to_smooth:
        if throw_min_error:
            raise Exception("Too few data points")
        else:
            smoothed_metric_points = metric_points
            return smoothed_metric_points

    #If not too short do local polynomial regression
    for time_idx in range(len(time_points)):

        if time_idx < half_window:
            start_time_idx = 0
            end_time_idx = half_window+time_idx
        elif time_idx >= half_window:
            start_time_idx = time_idx-half_window
            end_time_idx = half_window+time_idx

        start_idx_list.append(start_time_idx)
        end_idx_list.append(end_time_idx)
        
        time_window = time_points[start_time_idx:end_time_idx]
        metric_window = metric_points[start_time_idx:end_time_idx]

        poly = Polynomial.fit(time_window, metric_window, deg=deg)
        smoothed_metric_points[time_idx] = poly(time_points[time_idx])

    #Replace the first value to force them to match
    if force_start_value:
        smoothed_metric_points[0] = metric_points[0]

    return smoothed_metric_points

def get_smoothed_cap_eol_time(time_points, cap_points, eol_cond=90, min_data_points_to_smooth = 10, nominal_window_size=14):
    """
    Pass in raw capacity and time points will return the eol in whatever unit time_points is in
    
    """
    
    rel_cap_points = (cap_points/cap_points[0])*100
    rel_smoothed_cap_points = local_reg_adjust_window(np.array(time_points), np.array(rel_cap_points), min_data_points_to_smooth=min_data_points_to_smooth, 
                                                            throw_min_error=False, nominal_window_size=nominal_window_size, force_start_value=True)
    time_fun = interp1d(rel_smoothed_cap_points, time_points)
    eol_time = time_fun(eol_cond)
    return rel_smoothed_cap_points, eol_time

def get_mean_trend(sum_obj_list, sum_path, metric, normalize_before_mean):

    """Will return the mean array of the metric vs time curve given a list
    of sum_obj filenames. The option of normalizing before taking the mean can
    be toggled with normalize_before_mean. Metric is going to be either
    "RPT0.2C_2_D_capacity" or "Res_SS_2_D"

    Mean and std returned will be in units of % if normalize_before_mean is true
    or in units of whatever.

    If a test ends the mean will still be taken based on all the continuing cells.
    To see if this has happened num_cell_array returned tells you how many cells 
    are used to get the mean at each timepoint.
    
    Args:
    @sum_obj_list (list([str])): List of filenames to take the mean of
    @sum_path(str): Path to the location of where the files are present
    @metric(str): m
    @normalize_before_mean(Boolean): If True it sets normalizes all the indiviual cell trend lines to start
        at 100 (0% variability at beginning). If False instead the mean of all the trend lines is what is 
        set to start at 100.

    Returns:
    @mean_metric_array(np.array): Mean for all unique timepoints for the files provided.
    @std_metric_array(np.array): Mean for all unique timepoints for the files provided.
    @all_times(np.array): All unique time points in the files provided. Time is in units
        of weeks.
    @num_cells_array: The number of cells used in taking mean at each timepoint.
    """
    temp_cell_id_dict = {}


    #first get all unique time values that are tested
    all_times = []
    for idx, sum_name in enumerate(sum_obj_list):
        #Load in the sum_obj and data
        sum_obj=load_sum_obj(file_path=sum_path+sum_name)
        df = sum_obj.summary_data

        metric_points = np.array(df[metric])
        time_points =  np.array(df["Calendar_DateTime(days)"])/7

        #If time points are less than 4 we will just skip
        if(len(time_points))<4:
            continue

        #Add any new times to this array. This will help account for issues where we have taken out a data point etc
        all_times.extend(set(time_points) - set(all_times))
        temp_cell_id_dict[sum_name] = {"metric_points":metric_points,"time_points":time_points}


    #now for each cell get the array of values at every time
    all_times = np.array(sorted(all_times))
    interp_cell_id_array_metric = np.zeros((len(temp_cell_id_dict.keys()), len(all_times)))

    for idx, sum_name in enumerate(temp_cell_id_dict.keys()):
        metric_points = temp_cell_id_dict[sum_name]["metric_points"]
        if normalize_before_mean:
            metric_points = (metric_points/metric_points[0])*100
        time_points = temp_cell_id_dict[sum_name]["time_points"]

        smoothed_metric_points = local_reg_adjust_window(time_points, metric_points, deg=2)
        #interpolate so that we can get all time points standardized
        smooth_metric_fun = interp1d(time_points, smoothed_metric_points, bounds_error=False, fill_value=np.nan)
        interp_cell_id_array_metric[idx,:] = smooth_metric_fun(all_times)


    #now add the mean line to this as well as the std and the number of cells used at each calc
    mean_metric_array = np.nanmean(interp_cell_id_array_metric, axis=0)
    std_metric_array = np.nanstd(interp_cell_id_array_metric, axis=0)
    nan_mask_array = np.isnan(interp_cell_id_array_metric)
    num_cells_array = np.sum(~nan_mask_array, axis=0)

    return mean_metric_array, std_metric_array, all_times, num_cells_array


def cap_t_x_function(time_points, a, b):
    """
    Assumes functional form os Q(t) = 100-a*t^b


    time_points(np.array): array of time points
    a: preexponent parameter
    b: exponent parameter

    output: overpotential growth array
    """
    return 100-a*(time_points**b)


def cap_objective_t_x(params, time_points_to_fit, cap_points_to_fit):
    """
    Returns the mae error
    """
    a, b = params
    cap_growth_pred = cap_t_x_function(time_points_to_fit, a, b)
    mae = mean_absolute_error(cap_growth_pred, cap_points_to_fit)
    return mae

def res_t_x_function(time_points, a, b):
    """
    Assumes functional form os R(t) = 100+a*t^b


    time_points(np.array): array of time points
    a: preexponent parameter
    b: exponent parameter

    output: overpotential growth array
    """
    return 100+a*(time_points**b)


def res_objective_t_x(params, time_points_to_fit, res_points_to_fit):
    """
    Returns the mae error
    """
    a, b = params
    res_growth_pred = res_t_x_function(time_points_to_fit, a, b)
    mae = mean_absolute_error(res_growth_pred, res_points_to_fit)
    return mae