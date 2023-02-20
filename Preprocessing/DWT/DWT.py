from Data.DataLoader import DataLoader
from Utilities.Config.Config import Config
import platform
import mne
from mne.time_frequency import tfr_morlet


class DWT(object):

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

    def to_dwt(self):
        # create Epochs data
        epochs = self.data_loader.create_mne_epochs(self.raw_mne_data)
        # Morlet wavelet requires MNE Epochs format
        power, itc = mne.time_frequency.tfr_morlet(inst=epochs)
        return power, itc


if __name__ == '__main__':
    if platform.system() == 'Windows':
        # for Steven
        filename = 'C:\\Users\\saspr\\source\\Python\\Tegan\\BCI\\Utilities\\Config\\config_steven.json'
    elif platform.system() == 'Darwin':
        # for Tegan
        filename = '/Users/teganasprey/Desktop/BCI/Utilities/Config/config_tegan.json'

    config = Config(file_name=filename)
    config = config.settings
    dwt = DWT(config=config)
    if dwt.get_data():
        power, itc = dwt.to_dwt()
