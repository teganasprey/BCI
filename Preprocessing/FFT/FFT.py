from Data.DataLoader import DataLoader
from Utilities.Config.Config import Config
import platform
import mne

import matplotlib.pyplot as plt
import numpy as np
from mne.datasets import somato
from mne.time_frequency import tfr_morlet


class FFT(object):

    config = None
    raw_mne_data = None
    pandas_data = None
    data_loaded = False

    def __init__(self, config=None):
        self.config = config

    def get_data(self) -> bool:
        dl = DataLoader(config=self.config)
        self.data_loaded = dl.load_data()
        self.pandas_data = dl.to_pandas()
        self.raw_mne_data = dl.to_mne_raw()
        return self.data_loaded

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
    psd, freqs = fft.to_fft()


''' 
# other useful code:
events = mne.find_events(raw, stim_channel='STI 014')

# picks MEG gradiometers
picks = mne.pick_types(raw.info, meg='grad', eeg=False, eog=True, stim=False)

# Construct Epochs
event_id, tmin, tmax = 1, -1., 3.
baseline = (None, 0)
epochs = mne.Epochs(raw, events, event_id, tmin, tmax, picks=picks,
                    baseline=baseline, reject=dict(grad=4000e-13, eog=350e-6),
                    preload=True)
#epochs.plot_psd(fmin=2., fmax=40., average=True)
epochs.plot_psd_topomap(ch_type='grad', normalize=False)
'''