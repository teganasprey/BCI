import pandas as pd
import polars as pl
from scipy.io import loadmat
import os

if __name__ == '__main__':
    user = os.getlogin()
    filename = 'C:\\Users\\' + user + '\\Desktop\\Data'
    data = loadmat(filename)
    dat = data['o']
    marker_codes = dat[0][0][4]
    readings = dat[0][0][5]
    electrode_names = dat[0][0][6]
    print("Finished.")

