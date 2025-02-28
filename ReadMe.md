# Calendar Aging Dataset and Analysis

This repository contains the data and the code to generate the figures present in *A Decade of Insights: Delving into Calendar Aging Trends and Implications* by Vivek Lam et al (2024)̦. The data contained and the code provided are described in greater detail below.

## Data
The data is hosted on the corresponding OSF repository (https://osf.io/ju325/). The data included is calendar aging data taken at 24°C, 45°C, 60°C, and 85°C at 50% or 100% for 8 different cell types. For further testing details see the accompanying paper. For a summary of all cells tested in this work and their corresponding cell ids see [Joule_cell_id.csv](Joule_cell_id.csv). The data itself is stored in the following two folders depending on the data type needed:

- **[Raw Data](https://osf.io/ju325/)**: Raw data containing whole voltage, current, time, etc curves at every diagnostic. This allows easy plotting of things like the voltage vs capacity curve at each diagnostic cycle. Each file is a json file with a data, comment, and metadata field. The name of each file is of the form {cell_id}_raw.json. Data across files are standardized to be in the same units (time in seconds, current in amps, etc).
- **[Summary Data](https://osf.io/ju325/)**: Summary data that summarizes each diagnostic with a set of features such as capacity, energy, and resistance. This allows easy plotting of capacity and resistance vs time. Each file is a json file with a data, comment, and metadata field. The name of each file is of the form {cell_id}_sum.json. See [joule_generate_summary_data.ipynb](notebooks/using_data_example.ipynb) to see how the summary data is generated from the raw data, and full calculation of features of interest. 

## Summary Data Feature Naming Convention

The summary data calculates certain features of interest. The naming convention for ease of use is explained below:
- Capacity metrics: Capacity metrics (Ah) end in "_capacity" and are calculated for low rate (RPT0.2C), high rate(RPT_HighC), for the 1st, 2nd, and 3rd cycle (0,1,2). These are calculated for both charge (C) and discharge (D), and CV hold or not where applicable. Examples:
    - RPT0.2C_2_D_capacity (low rate RPT, 3rd diagnostic cycle, discharge capacity)
    - RPT_HighC_0_C_CV_capacity (high rate RPT, 1st diagnostic cycle, charge capacity, including CV)
- Energy metrics: Energy metrics (Wh) have the same naming convention as capacity metrics, but end in "_energy". Example:
    - RPT0.2C_1_D_energy (low rate RPT, 2nd diagnostic cycle, discharge capacity)
- Resistance metrics: Steady state resistance metrics (Ohm) start with Res_SS and are taken between the 1st, 2nd or 3rd low and high rate RPT on discharge only as charging rate is fixed. Example:
    - Res_SS_2_D (Steady state resistance using the 3rd low and high rate RPT)
- Time metrics: To denote the time diagnostics were performed some metrics are reported in the summary data:
    - diag_num: The diagnostic number
    - Calendar_time(date): The date of the diagnostic
    - Calendar_DateTime(days): The number of days since the first diagnostic cycle

For further calculation details of all metrics see [Joule_sum_data_builder.py](structuring_code/Joule_sum_data_builder.py).

## Notebooks: 
- **[using_data_example.ipynb](notebooks/using_data_example.ipynb)**: Example notebook of how to use the data, and what data is present
- **[joule_generate_summary_data.ipynb](notebooks/using_data_example.ipynb)**: Example of the code that is used to generate the summary data from the raw data.
- **[figure1_cap_res_summary.ipynb](notebooks/figure1_cap_res_summary.ipynb)**: Produces figure 1 of the paper summarizing the trends of resistance and capacity. 
- **[figure2_Arrhenius_prediction.ipynb](notebooks/figure2_Arrhenius_prediction.ipynb)**: Produces figure 2 of the paper showing a simple Arrhenius prediction of room temperature data
- **[figure3-6_txFittingResults.ipynb](notebooks/figure3-6_txFittingResults.ipynb)**: Produces figures 3, 4, 5, and 6 in the paper. This notebook shows the process fo 
- **[figure7_variability.ipynb](notebooks/figure7_variability.ipynb)**: Produces figure 7 in the paper. Shows variability of capacity and resistance.
- **[figure8_tx_eol_prediction.ipynb](notebooks/figure8_tx_eol_prediction.ipynb)**: Produces figure 8 in the paper. Shows the prediction error of tx models taking increasing amount of data.

## Structuring Code:
These modules contain the needed functions to use the raw data and generate certain plots. 
- **[Joule_raw_data_builder.py](structuring_code/Joule_raw_data_builder.py)**: Contains code needed to load in raw data.
- **[Joule_sum_data_builder.py](structuring_code/Joule_raw_data_builder.py)**: Contains code needed to load in summary data as well as code for generating summary data from the raw data.
- **[plotting_and_fitting_helpers.py](structuring_code/plotting_and_fitting_helpers.py)**: Contains code needed to generate several plots such as smoothing function used, fitting functions for power-law expressions, etc. 

## Saved Fitting Results:
Contains pre-saved fitting results to exactly reproduce the results shown in the paper. This contains the power-law fitting results of capacity ([tx_cap_fitting_2024-11-08](saved_fitting_results/tx_cap_fitting_2024-11-08)) and resistance ([tx_res_fitting_2024-11-08](saved_fitting_results/tx_res_fitting_2024-11-08)) used in [figure3-6_txFittingResults.ipynb](notebooks/figure3-6_txFittingResults.ipynb). It also contains the fitting results ([eol_error_dictionary_all_tpoints_2024-11-10](saved_fitting_results/eol_error_dictionary_all_tpoints_2024-11-10)) of the error of extrapolating power-law expression to end of life used in [figure8_tx_eol_prediction.ipynb](notebooks/figure8_tx_eol_prediction.ipynb).




