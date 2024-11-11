import pandas as pd
import os
import json
#ignoring future warnings from pandas due to loading in json
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

def load_raw_obj(file_path):
    """
    This function converts the json file back in to a cellLife_raw_obj and returns it. Manually add each field 
    and convert certain json fields back in to pandas dataframes
    
    Args:
    @file_path(string): location to the file of interest
    
    Returns:
    @obj(cellLife_raw_obj): reconstructed cellLife_raw_obj
    """
    
    with open(file_path, 'r') as openfile:
         json_file = json.load(openfile)
            
    
    meta_data = json_file["meta_data"]

    raw_data = pd.read_json(json_file["raw_data"])
    comment = json_file["comment"]
    obj = cellLife_raw_obj(meta_data=meta_data, raw_data=raw_data, comment=comment)
    return obj

class cellLife_raw_obj():
    def __init__(self, meta_data, raw_data, comment="N/A"):
        """
        Constructor for cellLife_data_object
        Args:
        @meta_data(Dict): Dictionary with key being the week, value is all the header files
        @raw_data(pd.DataFrame): concatentation of all raw data with the inclusion of Calendar 
            time and diagnostic num column. Nothing else is changed.
        @comment(string): A string commenting on the data.
        """
        self.meta_data = meta_data
        self.raw_data  = raw_data
        self.comment   = comment
        
    def to_json_file(self, file_path, overwrite=False):
        """
        This function saves the cellLife_raw_obj to a json file. All pieces are converted to 
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
        
        #Convert data to jsonable object
        dict_to_save = {"meta_data":self.meta_data, "raw_data":self.raw_data.to_json(),
                       "comment": self.comment}
        #Open and save to json file
        with open(file_path, "w") as outfile:
            json.dump(dict_to_save, outfile)