import numpy as np
import pandas as pd
import json
import os
from tqdm import tqdm
from Joule_raw_data_builder import load_raw_obj
from datetime import datetime
import re
#ignoring future warnings from pandas due to loading in json
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

HIGH_C_RATE_CONSTANTS = {'Panasonic NCR18650GA': 1.0, 'Panasonic NCR18650B': 1.0, 'K2 Energy LFP18650P': 3.0, 
                'K2 Energy LFP18650E':3.0, 'Ultralife UBP001': 1.0, 'Ultralife 502030':2.0, 
                'Sony-Murata US18650VTC6':3.0, 'Tenergy 302030':1.0}


def load_sum_obj(file_path):
    """
    This function converts the json file back in to a cellLife_sum_obj and returns it. Manually add each field 
    and convert certain json fields back in to pandas dataframes
    
    Args:
    @file_path(string): location to the file of interest
    
    Returns:
    @obj(cellLife_data_object): reconstructed cellLife_sum_obj
    """
    
    with open(file_path, 'r') as openfile:
         json_file = json.load(openfile)
            
    
    meta_data = json_file["meta_data"]
    summary_data = pd.read_json(json_file["summary_data"])
    comment = json_file["comment"]
    obj = cellLife_sum_obj(meta_data=meta_data, summary_data=summary_data, comment=comment)
    return obj

class cellLife_sum_obj():
    def __init__(self, meta_data, summary_data, comment="N/A"):
        """
        Constructor for cellLife_data_object
        Args:
        @meta_data(Dict): Dictionary with key being the week/month folder name. Value is a dictionary
            with information on the channel, cycler, and starting time of the diagnostic
        @summary_data(pd.DataFrame): concatentation of all raw data with the inclusion of 
            Calendar time column
        @comment(string): A string commenting on the data. For example: week 13 has a mistake. 
        """
        self.meta_data     = meta_data
        self.summary_data  = summary_data
        self.comment       = comment
        
    def to_json_file(self, file_path, overwrite=False):
        """
        This function saves the cellLife_data_object to a json file. All pieces are converted to 
        serializable objects such as Pandas dataframes to json and then put inside a parent
        dictionary which is converted to the json file.

        Args:
        @file_path(string): Path to save_file location
        @overwrite(Boolean): True if you want to overwrite the file at file_path

        Returns:
        None
        """
        
        #throw error if file already exists so we don't overwrite it
        if (os.path.exists(file_path) and not overwrite):
            raise Exception("File already exists")
        #If file exists, but you want to overwrite it delete it first
        if (os.path.exists(file_path) and overwrite):
            os.remove(file_path)
        #This essentially does what an encoder does
        dict_to_save = {"meta_data":self.meta_data, "summary_data":self.summary_data.to_json(),
                       "comment": self.comment}
        #Open and save to json file
        with open(file_path, "w") as outfile:
            json.dump(dict_to_save, outfile)


def generate_sum_data(cell_type, raw_path, save_path, code_path, overwrite=True):
    """
    This function looks through the raw data folder provided with raw_path and generates the feature 
    dataframe for all of the raw data that is in that folder. This function calls feature functions
    that are general enough that they should not fail on otherwise good files. 
    
    Args:
    @cell_type(str): String of what cell type it is (ex: "Panasonic NCR18650B")
    @raw_path(str): Path to the raw data json objects
    @save_path(str): Path of where to save the summary data objects
    @code_path(string): Where the Joule_cell_id.csv is stored. This is also where the sum and raw code is. 
    @overwrite(Boolean): Whether you want to overwrite already existing summary objects
    """
    
    joule_cell_id_path = code_path+"Joule_cell_id.csv"
    cell_id_df = pd.read_csv(joule_cell_id_path, dtype=str, index_col=False)
    cell_type_df = cell_id_df[cell_id_df["Cell_type"]==cell_type]
    cell_id_list = list(cell_type_df["Cell_id"])
    files_failed = []
    
    for i in tqdm(range(len(cell_id_list[:]))):
        cell_id=str(cell_id_list[i])

        try:
            sum_obj = generate_sum_data_cell_id(cell_id, raw_path, cell_type)
            filename = save_path+"{}_sum.json".format(cell_id)
            sum_obj.to_json_file(filename, overwrite=overwrite)
        except:
            files_failed.append(cell_id)

    return files_failed

def generate_sum_data_cell_id(cell_id, raw_path, cell_type):
    """
    This function generates a cellLife_sum_obj for a specific cell_id. It uses
    the raw data that is already generated (and given via the raw_path) to perform
    featurization scripts to get metrics of interest.
    
    Args:
    @cell_id(str): Unqiue Cell identification number ex: "C00001"
    @raw_path(str): Path to where all the raw data objects are stored
    @cell_type(str): The cell type corresponding to the cell_id. Used in steady
                    state resistance feature extraction.
    
    Returns:
    @sum_obj(cellLife_sum_obj): Summary data object for that cell_id
    """
    
    file_name = [x for x in os.listdir(raw_path) if x.startswith(cell_id)][0]
    file_path = raw_path+file_name
    
    raw_obj = load_raw_obj(file_path)
    total_df = raw_obj.raw_data

    total_num_diags = total_df["diag_num"].iloc[-1]+1

    df_featurized = pd.DataFrame()

    for i in range(total_num_diags):

        df_diag = total_df[total_df["diag_num"]==i]
        #If diagnostic failed don't try to generate features
        if diagnostic_failed(df_diag):
            continue


        temp_feat_total_df = generate_diag_summary_dataframe(df_diag, cell_type)
        #Concatenate to total df
        df_featurized = pd.concat([df_featurized, temp_feat_total_df], ignore_index=True)

    #add a column for the date_time measure in days
    if len(df_featurized)>0:
        start_date = datetime.strptime(df_featurized["Calendar_Time(date)"].iloc[0], '%Y-%m-%d')
        df_featurized["Calendar_DateTime(days)"] = df_featurized["Calendar_Time(date)"].apply(lambda x: (datetime.strptime(x, '%Y-%m-%d')-start_date).days)


    #save to sum object
    sum_obj = cellLife_sum_obj(meta_data=raw_obj.meta_data, summary_data=df_featurized, 
                               comment=raw_obj.comment)
    return sum_obj

def generate_diag_summary_dataframe(df_diag, cell_type):
    """
    This is a wrapper function that contains all the summary dataframes that are to
    be generated on a single, specific diagnostic cycle. These dataframes are then 
    concatenated and returned. To add other features make a generate_df function for a 
    different feature
    
    Args:
    @df_diag(pd.DataFrame): Dataframe of a single diagnostic on a single cell worth of data
    @cell_type(str): The cell type corresponding to the cell_id. Used in steady state resistance 
            feature extraction.
    
    Returns:
    @temp_feat_total_df(pd.DataFrame): Dataframe with all the features concatenated as columns.
            This dataframe essentially has a single row with many columns for different features
    """
    temp_feat_df_time = pd.DataFrame({"diag_num": [df_diag["diag_num"].iloc[0]],
                                     "Calendar_Time(date)": df_diag["Diag_Start_Datetime"].iloc[0]})
    temp_feat_df_cap = generate_capacity_df(df_diag)
    temp_feat_df_energy = generate_energy_df(df_diag)
    temp_feat_df_res_ss = generate_ss_resistance_df(df_diag, cell_type)
    temp_feat_total_df  = pd.concat([temp_feat_df_cap, temp_feat_df_energy, 
                                     temp_feat_df_time, temp_feat_df_res_ss], axis=1)
    return temp_feat_total_df

def diagnostic_failed(df_diag):
    """
    This function determines if a diagnostic has failed. If so then it does not attempt to gather
    any features on the data. It determines if the diagnostic has failed if it doesn't complete
    a certain number of cycles.

    Args:
    @df_diag(pd.DataFrame): DataFrame with data from a single diagnostic cycle of a single cell
    
    Returns: Boolean, True when the diagnostic has failed, False if it has not
    
    """
    cycle_list = sorted(set(df_diag["Cycle"]))
    # If diagnostic does not complete 7 cycles it didn't complete the diagnostic
    # there can be edge cases on this.
    return (len(cycle_list) < 7)    

def get_capacity(df_cycle, state="D", no_CV = True):
    """
    Input the cycle of interest and this will provide the capacity. If the no_CV flag is is True
    it will return only the CC capacity of the charge capacity. The CV is determined by the current
    falling 1/100th below its average value. The discharge capacity doesn't have a CV hold, so nothing
    changes for this
    
    Args:
    @df_cycle(pd.DataFrame): A pandas dataframe filtered to be the RPT cycle of interest
    @state(string): Expects either "D" for discharge or "C" for charge
    
    Output:
    @capacity(float): Capacity of this cycle
    """
    
    #The charge state includes a CV hold. This might not want to be included.
    if ((state=="C") & no_CV):
        #Get CC current by just averaging what the current is for first few datapoints 
        avgCurr = np.mean(df_cycle["Current (A)"].iloc[:10])
        #If current falls below the average value by 1/100th of the value
        #You are in CV portion, this value needs to higher than noise
        epsilon=avgCurr/100
        temp_df = df_cycle[df_cycle["MD"]==state]
        temp_df = temp_df[temp_df["Current (A)"]>=avgCurr-epsilon]
        capacity = temp_df['Capacity (Ah)'].iloc[-1]
    #For discharge or if we also want the CV for charge
    else:
        capacity = df_cycle[df_cycle["MD"]==state]["Capacity (Ah)"].iloc[-1]

    return float(capacity)

def get_energy(df_cycle, state="D", no_CV = True):
    """
    Input the cycle of interest and this will provide the capacity. If the no_CV flag is is True
    it will return only the CC capacity of the charge capacity. The discharge capacity doesn't have
    a CV hold, so nothing changes for this. 
    
    Args:
    @df_cycle(pd.DataFrame): A pandas dataframe filtered to be the RPT cycle of interest
    @state(string): Expects either "D" for discharge or "C" for charge
    
    Output:
    @capacity(float): Capacity of this cycle
    """
    
    #The charge state includes a CV hold. This might not want to be included.
    if ((state=="C") & no_CV):
        #Get CC current by just averaging what the current is for first few datapoints 
        avgCurr = np.mean(df_cycle["Current (A)"].iloc[:10])
        #If current falls below this average value by epsilon amount. You are in CV portion
        epsilon=avgCurr/100
        temp_df = df_cycle[df_cycle["MD"]==state]
        temp_df = temp_df[temp_df["Current (A)"]>=avgCurr-epsilon]
        energy = temp_df['Energy (Wh)'].iloc[-1]
    #For discharge or if we also want the CV for charge
    else:
        energy = df_cycle[df_cycle["MD"]==state]["Energy (Wh)"].iloc[-1]
    
    #Some of the energy data is corrupted and is a string. This makes that whole
    #diagnostic of float values actually str. This will coerce the correct type, 
    # if it can't (because it is corrupted) will return nan.
    try:
        energy = float(energy)
        return energy
    except:
        return np.nan


def get_ss_resistance(df_cycle_RPTLowC, df_cycle_RPTHighC, cell_type):
    """
    This function get the steady state resistance between two CC discharge voltage
    vs capacity curves. The average voltage of the discharge for a CC step is gotten
    from the energy/capacity. The average voltage between the low rate discharge and 
    the high rate discharge cycle is then divided by the difference in the C-rate
    instead of current to give a capacity normalized steady state resistance.

    Args:
    @df_cycle_RPTLowC(pd.DataFrame): One cycle of the diagnostic containing the low rate RPT
    @df_cycle_RPTHighC(pd.DataFrame): One cycle of the diagnostic containing the high rate RPT
    @cell_type(str): String of the cell_type used to get the high Crate from HIGH_C_RATE_CONSTANTS

    Return: res_ss(float): The steady state resistance in units of Ohm*Ah
    """
    #can only do for discharge since charge is always C/5
    state="D"
    #Get average voltage at low and high rate discharge from energy/capacity
    disc_energy_lowrate = get_energy(df_cycle_RPTLowC, state=state)
    disc_energy_highrate = get_energy(df_cycle_RPTHighC, state=state)

    disc_cap_lowrate = get_capacity(df_cycle_RPTLowC, state=state, no_CV = True)
    disc_cap_highrate = get_capacity(df_cycle_RPTHighC, state=state, no_CV = True)
    
    #Can get divide by 0 errors etc here depending on if a diagnostic failed prematurely etc
    #for these just return nan instead
    try:
        avg_volt_lowrate = disc_energy_lowrate/disc_cap_lowrate
        avg_volt_highrate = disc_energy_highrate/disc_cap_highrate
    except:
        return np.nan

    lowCrate = 1/5
    highCrate = HIGH_C_RATE_CONSTANTS[cell_type]
    
    #multiply by -1 to account for the C-rate being negative
    res_ss = -1*(avg_volt_highrate-avg_volt_lowrate)/(highCrate-lowCrate)
    return float(res_ss)

def generate_energy_df(df_diag):
    """
    This is a wrapper function for the dataframe to generate all the energy values of interest.
    Note that the naming convention relies on cycles 1-3 being a RPT_C/5 and cycles 4-6 being a
    RPT_HighC. Note that the cycle number can be different, but the cycles order should be right.
    
    Inputs: pd.DataFrame for a single diagnostic. 
    
    Output: pd.DataFrame with columns corresponding to all energies of interest
    """
    
    df = pd.DataFrame()
    cycle_list = sorted(set(df_diag["Cycle"]))

    for idx, cycle in enumerate(range(1,7)):
        if cycle<4:
            for state in ["C", "D"]:
                name = "RPT0.2C_{}_{}_energy".format(idx,state)
                df_cycle = df_diag[df_diag["Cycle"]==cycle_list[cycle]]
                df[name]=[get_energy(df_cycle, state=state)]
                #If in charge state also get the charge energy with CV
                if state=="C":
                    name = "RPT0.2C_{}_{}_CV_energy".format(idx,state)
                    df[name]=[get_energy(df_cycle, state=state, no_CV = False)]
        #1C cycles
        else:
            for state in ["C", "D"]:
                name = "RPT_HighC_{}_{}_energy".format(idx-3, state)
                df_cycle = df_diag[df_diag["Cycle"]==cycle_list[cycle]]
                df[name]=[get_energy(df_cycle, state=state)]
                #If in charge state also get the charge energy with CV
                if state=="C":
                    name = "RPT_HighC_{}_{}_CV_energy".format(idx,state)
                    df[name]=[get_energy(df_cycle, state=state, no_CV = False)]


    return df

def generate_capacity_df(df_diag):
    """
    This is a wrapper function for the dataframe to generate all the capacity values of interest.
    Note that the naming convention relies on cycles 1-3 being a RPT_C/5 and cycles 4-6 being a
    high rate RPT. Note that the cycle number can be different, but the cycles order should be right.
    
    Inputs: pd.DataFrame for a single diagnostic. 
    
    Output: pd.DataFrame with columns corresponding to all capacities of interest
    """
    
    df = pd.DataFrame()
    cycle_list = sorted(set(df_diag["Cycle"]))
    for idx, cycle in enumerate(range(1,7)):
        if cycle<4:
            for state in ["C", "D"]:
                name = "RPT0.2C_{}_{}_capacity".format(idx,state)
                df_cycle = df_diag[df_diag["Cycle"]==cycle_list[cycle]]
                df[name]=[get_capacity(df_cycle, state=state)]
                #If in charge state also get the charge capacity with CV
                if state=="C":
                    name = "RPT0.2C_{}_{}_CV_capacity".format(idx,state)
                    df[name]=[get_capacity(df_cycle, state=state, no_CV = False)]

        #1C cycles
        else:
            for state in ["C", "D"]:
                name = "RPT_HighC_{}_{}_capacity".format(idx-3, state)
                df_cycle = df_diag[df_diag["Cycle"]==cycle_list[cycle]]
                df[name]=[get_capacity(df_cycle, state=state)]
                #If in charge state also get the charge capacity with CV
                if state=="C":
                    name = "RPT_HighC_{}_{}_CV_capacity".format(idx,state)
                    df[name]=[get_capacity(df_cycle, state=state, no_CV = False)]
    return df

def generate_ss_resistance_df(df_diag, cell_type):
    """
    This is a wrapper function for the dataframe to generate all the steady state resistance
    values of interest. Note that this relies on cycles 1-3 being a RPT_C/5 and cycles 4-6 being 
    a high rate RPT. The high rate RPT is gotten by adding 3 to the index of the chosen RPT. First 
    low rate discharge is used with first high rate discharge and so on for the three discharges.

    Args: 
    @df_diag(pd.DataFrame): Dataframe of a single diagnostic
    @cell_type(str): The cell type corresponding to the cell_id. Used in steady
                state resistance feature extraction. 
    
    Output: pd.DataFrame with columns corresponding to all steady state resistance of interest
    """

    df = pd.DataFrame()

    cycle_list = sorted(set(df_diag["Cycle"]))
    for idx, cycle in enumerate(range(1,4)):
        name = "Res_SS_{}_D".format(idx)
        df_cycle_RPTLowC = df_diag[df_diag["Cycle"]==cycle_list[cycle]]
        df_cycle_RPTHighC = df_diag[df_diag["Cycle"]==(cycle_list[cycle+3])]
        df[name] = [get_ss_resistance(df_cycle_RPTLowC, df_cycle_RPTHighC, cell_type)]
            

    return df

