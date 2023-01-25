import matplotlib.pyplot as plt
import numpy as np

import mne
from mne.datasets import somato
from mne.time_frequency import tfr_morlet

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
