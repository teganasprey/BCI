from Data.DataLoader import DataLoader
from Utilities.Config.Config import Config
import platform
import mne


class FFT(object):

    config = None
    raw_mne_data = None
    pandas_data = None
    data_loaded = False

    def __init__(self, config=None):
        self.config = config

    def get_data(self) -> bool:
        dl = DataLoader(config=self.config)
        self.raw_mne_data = dl.load_data_from_sql(self.config['data']['experiment_id'])
        return True

    def to_fft(self):
        psd, freqs = mne.time_frequency.psd_welch(inst=self.raw_mne_data)
        return psd, freqs


if __name__ == '__main__':
    if platform.system() == 'Windows':
        # for Steven
        filename = 'C:\\Users\\saspr\\source\\Python\\Tegan\\BCI\\Utilities\\Config\\config_steven.json'
    elif platform.system() == 'Darwin':
        # for Tegan
        filename = '/Users/teganasprey/Desktop/BCI/Utilities/Config/config_tegan.json'

    config = Config(file_name=filename)
    config = config.settings
    fft = FFT(config=config)
    if fft.get_data():
        psd, freqs = fft.to_fft()
