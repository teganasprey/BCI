import pandas as pd
import polars as pl
from scipy.io import loadmat
import getpass
import platform
from Utilities.Config.Config import Config
import mne

if platform.system() == 'Darwin':
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    mpl.use('macosx')


class DataLoader(object):

    # class level constants
    ELECTRODE_NAMES_EXPECTED = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2', 'A1', 'A2', 'F7', 'F8',
                                'T3', 'T4', 'T5', 'T6', 'Fz', 'Cz', 'Pz', 'X3']
    ELECTRODE_NAMES = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2', 'A1', 'A2', 'F7', 'F8',
                       'T3', 'T4', 'T5', 'T6', 'Fz', 'Cz', 'Pz']
    CLA_HALT_FREEFORM_EVENT_DICT = {'left hand MI': 1, 'right hand MI': 2, 'passive state': 3,
                                    'left leg MI': 4, 'tongue MI': 5, 'right leg MI': 6,
                                    'initial relaxation period': 99, 'inter-session rest break period': 91,
                                    'experiment end': 92}
    FIVE_FINGERS_EVENT_DICT = {'thumb MI': 1, 'index finger MI': 2, 'middle finger': 3, 'ring finger': 4,
                               'pinkie finger': 5, 'initial relaxation period': 99,
                               'inter-session rest break period': 91, 'experiment end': 92}

    # class level fields
    config = None
    data_directory = None
    operating_system = None
    user = None

    file_name = None
    marker_codes = None
    readings = None
    electrode_names_raw = None
    experiment_paradigm = None          # e.g., 5F, CLA, FREEFORM, HaLT, NoMT
    experiment_stimuli = None           # e.g., LRHand
    subject = None                      # A-J
    file_date = None                    # YYMMDD
    states = None                       # e.g., 3St
    experiment_mode = None              # e.g., Inter, HFREQ

    framework = None
    data_loaded = False

    def __init__(self, config=None):
        """
        Constructor for the data loader class
        :param config: - the config object to use for settings
        :type config:
        """
        self.config = config
        self.operating_system = platform.system()
        self.user = getpass.getuser()

        # use config settings to set fields
        self.file_name = config['data']['file']
        self.framework = config['framework']
        self.data_directory = config['data']['directory'].replace('{user}', self.user)

    def load_data_from_file(self) -> bool:
        """
        Method to load the data file specified in the config file being used
        :return: True when the data have been loaded successfully
        :rtype: bool
        """
        # form the full file name with path
        filename = self.data_directory
        if self.operating_system == 'Windows':
            filename += '\\' + self.file_name
        elif self.operating_system == 'Darwin':
            filename += '/' + self.file_name

        # extract information from the file name
        components = self.file_name.split('.')
        info = components[0].split('-')
        self.experiment_paradigm = info[0]
        self.subject = info[1][-1]
        self.file_date = info[2]
        self.states = info[3]
        self.experiment_stimuli = info[4]
        self.experiment_mode = info[5]

        # load the mat file
        rd = loadmat(filename)

        # process the mat file data into arrays
        raw_data = rd['o']
        self.marker_codes = raw_data[0][0][5]
        self.readings = raw_data[0][0][6]
        self.electrode_names_raw = raw_data[0][0][7]

        # return
        self.data_loaded = True
        return self.data_loaded

    def load_data_from_sql(self):
        pass

    def push_data_to_sql(self):
        pass

    def to_pandas(self) -> pd.DataFrame:
        """
        Method to convert the data into a Pandas DataFrame
        :return: DataFrame containing the data, including markers
        :rtype: pandas DataFrame
        """
        if self.data_loaded:
            markers_df = pd.DataFrame(self.marker_codes)
            readings_df = pd.DataFrame(self.readings)
            electrodes_df = pd.DataFrame(self.electrode_names_raw)
            dataframe = pd.concat([markers_df, readings_df], axis=1)
            headers = ['marker'] + self.electrode_names_expected
            dataframe.columns = headers
            return dataframe

    def to_polars(self) -> pl.DataFrame:
        """
        Method to convert the data into a Polars DataFrame
        :return: DataFrame containing the data, including markers
        :rtype: polars DataFrame
        """
        if self.data_loaded:
            markers_df = pl.DataFrame(self.marker_codes)
            markers_df.columns = ['marker']
            readings_df = pl.DataFrame(self.readings)
            electrodes_df = pl.DataFrame(self.electrode_names)
            dataframe = pl.concat([markers_df, readings_df], how='horizontal')
            headers = ['marker'] + self.electrode_names_expected
            dataframe.columns = headers
            return dataframe

    def to_mne_raw(self) -> mne.io.RawArray:
        """
        Method to convert the data into an MNE RawArray, with all relevant meta information
        :return: raw MNE data array containing the signal data, the info data and electrode montage
        :rtype: mne.io.RawArray
        """
        data = self.to_pandas()
        info = self.create_mne_info()
        raw = mne.io.RawArray(data=data[self.electrode_names].transpose(), info=info)
        return raw

    def create_mne_info(self) -> mne.Info:
        """
        Method to create an MNE info object for use in creating RawArray and EpochArray objects
        :return: MNE Info object containing meta information
        :rtype: mne.Info
        """
        # prepare data for the "info" object
        sample_freq = 200
        channel_types = ['eeg'] * 21
        info = mne.create_info(ch_names=self.electrode_names, sfreq=sample_freq, ch_types=channel_types)
        info.set_montage('standard_1020')

        # settable fields in info are:
        # info['bads'] - channel names with known bad data
        # info['description'] - general description field
        # info['subject_info'] - information about the subject
        # other fields of interest: info['device_info'], info['dev_head_t'], info['experimenter'], info[‘helium_info’],
        # info['line_freq'], info['temp']
        return info

    def create_mne_epochs(self) -> mne.EpochsArray:
        """
        Method to create MNE epochs array from scratch
        :return: MNE Epochs Array contains the epochs data
        :rtype: mne.EpochsArray
        """
        data = self.to_pandas()
        markers = pd.DataFrame(data['marker'])
        markers['zeros'] = 0
        markers['sample'] = markers.reset_index().index
        events = markers[['sample', 'zeros', 'marker']].to_numpy()
        epochs = mne.EpochsArray(data=data.to_numpy(), info=self.create_mne_info(), events=events, tmin=0,
                                 event_id=self.cla_halt_freeform_event_dict)
        return epochs


if __name__ == '__main__':
    if platform.system() == 'Windows':
        # for Steven
        filename = 'C:\\Users\\saspr\\source\\Python\\Tegan\\BCI\\Utilities\\Config\\config_steven.json'
    elif platform.system() == 'Darwin':
        # for Tegan
        filename = '/Users/teganasprey/Desktop/BCI/Utilities/Config/config_tegan.json'

    config = Config(file_name=filename)
    config = config.settings
    dl = DataLoader(config=config)
    loaded = dl.load_data_from_file()
    dfd = dl.to_pandas()
    dfl = dl.to_polars()
    raw_mne = dl.to_mne_raw()
    epochs = dl.create_mne_epochs()

    # raw_mne.plot()
    # testing feather file format for storing data in binary format:
    # dfd.to_feather('C:\\Users\\saspr\\source\\Python\\Tegan\\BCI\\Data\\CLA-SubjectJ-170508-3St-LRHand-Inter.fea')
    # testing parquet file format for storing data in binary format:
    # dfd.to_parquet('C:\\Users\\saspr\\source\\Python\\Tegan\\BCI\\Data\\CLA-SubjectJ-170508-3St-LRHand-Inter.gzip',
    #                compression='gzip')
    print("Finished.")

