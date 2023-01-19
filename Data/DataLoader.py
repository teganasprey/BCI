import pandas as pd
import polars as pl
from scipy.io import loadmat
import getpass
import platform
from Utilities.Config.Config import Config


class DataLoader(object):

    config = None
    data_directory = None
    operating_system = None
    file_name = None
    user = None
    marker_codes = None
    readings = None
    electrode_names = None
    electrode_names_expected = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2', 'A1', 'A2', 'F7', 'F8', 'T3', 'T4', 'T5', 'T6', 'Fz', 'Cz', 'Pz', 'X3']
    dataframe = None
    framework = None
    data_loaded = False

    def __init__(self, config=None):
        self.config = config
        self.operating_system = platform.system()
        self.user = getpass.getuser()

        # use config settings
        self.file_name = config['data']['file']
        self.framework = config['framework']

        self.data_directory = config['data']['directory'].replace('{user}', self.user)

    def load_data(self):
        filename = self.data_directory
        if self.operating_system == 'Windows':
            filename += '\\' + self.file_name
        elif self.operating_system == 'Darwin':
            filename += '/' + self.file_name
        rd = loadmat(filename)
        raw_data = rd['o']
        self.marker_codes = raw_data[0][0][5]
        self.readings = raw_data[0][0][6]
        self.electrode_names = raw_data[0][0][7]
        self.data_loaded = True

    def to_pandas(self):
        if self.data_loaded:
            markers_df = pd.DataFrame(self.marker_codes)
            readings_df = pd.DataFrame(self.readings)
            electrodes_df = pd.DataFrame(self.electrode_names)
            self.dataframe = pd.concat([markers_df, readings_df], axis=1)
            headers = ['marker'] + self.electrode_names_expected
            self.dataframe.columns = headers

    def to_polars(self):
        if self.data_loaded:
            markers_df = pl.DataFrame(self.marker_codes)
            markers_df.columns = ['marker']
            readings_df = pl.DataFrame(self.readings)
            electrodes_df = pl.DataFrame(self.electrode_names)
            self.dataframe = pl.concat([markers_df, readings_df], how='horizontal')
            headers = ['marker'] + self.electrode_names_expected
            self.dataframe.columns = headers


if __name__ == '__main__':
    # for Steven
    filename = 'C:\\Users\\saspr\\source\\Python\\Tegan\\BCI\\Utilities\\Config\\config_steven.json'
    # for Tegan
    # filename = '/Users/BCI/Utilities/Config/config_tegan.json'

    config = Config(file_name=filename)
    config = config.settings
    dl = DataLoader(config=config)
    dl.load_data()
    dl.to_pandas()
    dl.to_polars()
    print("Finished.")

