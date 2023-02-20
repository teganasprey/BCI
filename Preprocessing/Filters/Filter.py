from Data.DataLoader import DataLoader
from Utilities.Config.Config import Config
import platform
import mne


class Filter(object):

    config = None
    raw_mne_data = None
    pandas_data = None
    data_loader = None
    data_loaded = False

    def __init__(self, config=None):
        self.config = config
        self.data_loader = DataLoader(config=self.config)

    def get_data(self) -> bool:
        self.raw_mne_data = self.data_loader.load_data_from_sql(self.config['data']['experiment_id'])
        return True

    def set_data(self, data=None):
        self.raw_mne_data = data

    def filter(self) -> mne.io.RawArray:
        filtered_data = self.raw_mne_data.copy()
        low_pass_frequency = self.config['filter_settings']['low_pass_frequency']
        high_pass_frequency = self.config['filter_settings']['high_pass_frequency']
        if high_pass_frequency == 0:
            high_pass_frequency = None
        filtered_data.filter(low_pass_frequency, high_pass_frequency, fir_design='firwin', skip_by_annotation='edge',
                             picks='eeg')
        return filtered_data


if __name__ == '__main__':
    if platform.system() == 'Windows':
        # for Steven
        filename = 'C:\\Users\\saspr\\source\\Python\\Tegan\\BCI\\Utilities\\Config\\config_steven.json'
    elif platform.system() == 'Darwin':
        # for Tegan
        filename = '/Users/teganasprey/Desktop/BCI/Utilities/Config/config_tegan.json'

    config = Config(file_name=filename)
    config = config.settings