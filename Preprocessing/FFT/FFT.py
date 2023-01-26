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
        self.raw_mne_data = dl.to_mne()
        return self.data_loaded

    def to_fft(self):
        psd, freqs = mne.time_frequency.psd_welch(inst=self.raw_mne_data)


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
    f



#replace somato with RawArray and our own data
data_path = somato.data_path()
subject = '01'
task = 'somato'
#if platform.system() == 'Windows':
    # for Steven
    #raw_fname = 'C:\\Users\\saspr\\source\\Python\\Tegan\\BCI\\Utilities\\Config\\config_steven.json'
#elif platform.system() == 'Darwin':
    # for Tegan
    #raw_fname = '/Users/teganasprey/Desktop/BCI/Utilities/Config/config_tegan.json'
raw_fname = (data_path / f'sub-{subject}' / 'meg' /
            f'sub-{subject}_task-{task}_meg.fif')

# Setup for reading the raw data
raw = mne.io.read_raw_fif(raw_fname)
# crop and resample just to reduce computation time
raw.crop(120, 360).load_data().resample(200)
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
