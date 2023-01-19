import pandas as pd
import polars as pl
from scipy.io import loadmat
import os
import getpass

if __name__ == '__main__':
    user = getpass.getuser()
    filename = '/Users/' + user + '/Desktop/Data/5F-SubjectA-160405-5St-SGLHand.mat'
    data = loadmat(filename)
    dat = data['o']
    marker_codes = dat[0][0][4]
    readings = dat[0][0][5]
    electrode_names = dat[0][0][6]
    print("Finished.")

