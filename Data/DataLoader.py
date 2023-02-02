from Utilities.Config.Config import Config
from Utilities.Database.Postgres.PostgresConnector import PostgresConnector
import pandas as pd
import polars as pl
from scipy.io import loadmat
import getpass
import platform
import mne
import os

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
                                    'experiment end': 92, 'warm-up': 90}
    CLA_HALT_FREEFORM_EVENT_COLORS = {1: 'r', 2: 'g', 3: 'b', 4: 'm', 5: 'y', 6: 'k',
                                      99: 'k', 91: 'k', 92: 'k', 90: 'k'}
    FIVE_FINGERS_EVENT_DICT = {'thumb MI': 1, 'index finger MI': 2, 'middle finger': 3, 'ring finger': 4,
                               'pinkie finger': 5, 'initial relaxation period': 99,
                               'inter-session rest break period': 91, 'experiment end': 92, 'warm-up': 90}
    FIVE_FINGERS_EVENT_COLORS = {1: 'r', 2: 'g', 3: 'b', 4: 'm', 5: 'y',
                                 99: 'k', 91: 'k', 92: 'k', 90: 'k'}

    # class level fields
    config = None
    data_directory = None
    operating_system = None
    user = None

    file_name = None
    marker_codes = None
    signal_readings = None
    electrode_names_raw = None
    experiment_paradigm = None          # e.g., 5F, CLA, FREEFORM, HaLT, NoMT
    experiment_stimuli = None           # e.g., LRHand
    subject = None                      # A-J
    file_date = None                    # YYMMDD
    states = None                       # e.g., 3St
    experiment_mode = None              # e.g., Inter, HFREQ

    data_pandas = None
    data_polars = None
    data_raw_mne = None

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
        # form the full file name with path, depending on the OS
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
        if len(info) > 5:
            self.experiment_mode = info[5]
        else:
            self.experiment_mode = 'Empty'

        # load the mat file
        rd = loadmat(filename)

        # process the mat file data into arrays
        raw_data = rd['o']
        self.marker_codes = raw_data[0][0][4]
        self.signal_readings = raw_data[0][0][5]
        self.electrode_names_raw = raw_data[0][0][6]

        # return
        self.data_loaded = True
        return self.data_loaded

    def load_data_from_sql(self, experiment_id=None, marker=None) -> mne.io.RawArray:
        postgres = PostgresConnector()
        if experiment_id is None:
            experiment_id = 1
        sql_query = 'SELECT sample_index, marker as "STI001", "Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4", ' \
                    '"O1", "O2", "A1", "A2", "F7", "F8", "T3", "T4", "T5", "T6", "Fz", "Cz", "Pz" ' \
                    'FROM signal_data ' \
                    'where experiment_id = ' + str(experiment_id) + ' '
        if marker is not None:
            sql_query += 'and marker = ' + str(marker) + ' '
        sql_query += 'order by sample_index'
        data = postgres.execute_query_to_pandas(sql_query=sql_query)
        # convert units from uV to V (expected by MNE)
        for electrode in self.ELECTRODE_NAMES:
            data[electrode] = data[electrode] / 1.0e6
        info = self.create_mne_info()
        raw = mne.io.RawArray(data=data[self.ELECTRODE_NAMES + ['STI001']].transpose(), info=info)
        self.data_raw_mne = raw
        self.data_pandas = data[self.ELECTRODE_NAMES + ['STI001']]
        return raw

    def push_data_to_sql(self) -> bool:
        """
        Method to insert data into the Postgres tables (experiment_information and signal_data). The method uses
        the COPY command to push a csv file to Postgres, which in turn is created using Pandas.
        :return: whether the data push was successful
        :rtype: bool
        """
        postgres = PostgresConnector()
        experiment_id = self.get_next_experiment_id()
        if experiment_id > 0:
            experiment_query = 'insert into experiment_information ' \
                               '(experiment_id, experiment_date, paradigm, subject_id, states, stimuli, mode) ' \
                               'values ' \
                               '('
            experiment_query += str(experiment_id) + ', '
            experiment_query += 'to_date(\'20' + self.file_date + '\', \'YYYYMMDD\'), '
            experiment_query += '\'' + self.experiment_paradigm + '\', '
            experiment_query += '\'' + self.subject + '\', '
            experiment_query += '\'' + self.states + '\', '
            experiment_query += '\'' + self.experiment_stimuli + '\', '
            experiment_query += '\'' + self.experiment_mode + '\')'
            postgres.execute(sql_query=experiment_query)

            # create a csv file with the data formatted correctly for the signal_data table
            data = self.to_pandas()
            data['experiment_id'] = experiment_id
            data['sample_index'] = data.reset_index().index
            columns = data.columns[-2:].tolist() + data.columns[:-2].to_list()
            data_to_file = data[columns]
            filename = ''.join([self.experiment_paradigm, self.file_date, self.subject]) + '.csv'
            if self.operating_system == 'Windows':
                full_filename = 'C:\\Users\\Public\\Downloads\\' + filename
            elif self.operating_system == 'Darwin':
                full_filename = '/' + filename
            data_to_file.to_csv(full_filename, sep=',', index=False)
            data_query = 'COPY signal_data (experiment_id, sample_index, marker, "Fp1", "Fp2", "F3", "F4", "C3", ' \
                         '"C4", "P3", "P4", "O1", "O2", "A1", "A2", "F7", "F8", "T3", "T4", "T5", "T6", "Fz", "Cz", ' \
                         '"Pz", "X3") '
            data_query += 'FROM \'' + full_filename + '\' '
            data_query += 'DELIMITER \',\' '
            data_query += 'CSV HEADER;'
            postgres.execute(sql_query=data_query)

            # delete the temporary csv file
            try:
                os.remove(full_filename)
            except OSError as ex:
                pass
        else:
            # experiment_id already exists, no need to push the data again
            return True
        return True

    def get_next_experiment_id(self) -> int:
        """
        Method to check Postgres tables and calculate the next experiment_id tag based on what is already in
        the database and the file being processed.
        :return: the experiment_id to use, -1 if already in the database
        :rtype: int
        """
        postgres = PostgresConnector()
        sql_query = 'select max(experiment_id) from experiment_information where ' \
                    'concat(paradigm, to_char(experiment_date, \'YYYYMMDD\')) != \''
        sql_query += self.experiment_paradigm + '20' + self.file_date + '\''
        rows = postgres.execute_query(sql_query=sql_query)
        # handle null value
        value = rows[0][0]
        if value is None:
            # check whether there are any entries in the table (should only occur once)
            sql_query = 'select count(*) from experiment_information'
            rows = postgres.execute_query(sql_query=sql_query)
            count = int(rows[0][0])
            if count == 0:
                value = 0
            else:
                return -1
        else:
            value = int(value)
        experiment_id = value + 1
        return experiment_id

    def to_pandas(self) -> pd.DataFrame:
        """
        Method to convert the data into a Pandas DataFrame
        :return: DataFrame containing the data, including markers
        :rtype: pandas DataFrame
        """
        if self.data_loaded:
            markers_df = pd.DataFrame(self.marker_codes)
            readings_df = pd.DataFrame(self.signal_readings)
            electrodes_df = pd.DataFrame(self.electrode_names_raw)
            dataframe = pd.concat([markers_df, readings_df], axis=1)
            headers = ['marker'] + self.ELECTRODE_NAMES_EXPECTED
            dataframe.columns = headers
            self.data_pandas = dataframe
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
            readings_df = pl.DataFrame(self.signal_readings)
            electrodes_df = pl.DataFrame(self.ELECTRODE_NAMES)
            dataframe = pl.concat([markers_df, readings_df], how='horizontal')
            headers = ['marker'] + self.ELECTRODE_NAMES_EXPECTED
            dataframe.columns = headers
            self.data_polars = dataframe
            return dataframe

    def to_mne_raw(self) -> mne.io.RawArray:
        """
        Method to convert the data into an MNE RawArray, with all relevant meta information
        :return: raw MNE data array containing the signal data, the info data and electrode montage
        :rtype: mne.io.RawArray
        """
        data = self.to_pandas()
        # convert units from uV to V (expected by MNE)
        for electrode in self.ELECTRODE_NAMES:
            data[electrode] = data[electrode] / 1.0e6
        info = self.create_mne_info()
        raw = mne.io.RawArray(data=data[self.ELECTRODE_NAMES + ['STI001']].transpose(), info=info)
        self.data_raw_mne = raw
        return raw

    def create_mne_info(self) -> mne.Info:
        """
        Method to create an MNE info object for use in creating RawArray and EpochArray objects
        :return: MNE Info object containing meta information
        :rtype: mne.Info
        """
        # prepare data for the "info" object
        sample_freq = 200
        channel_types = ['eeg'] * 21 + ['stim']
        info = mne.create_info(ch_names=self.ELECTRODE_NAMES + ['STI001'], sfreq=sample_freq, ch_types=channel_types)
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
        data = self.data_pandas
        events = mne.find_events(raw_mne, stim_channel='STI001')
        epochs = mne.EpochsArray(data=data.to_numpy(), info=self.create_mne_info(), events=events, tmin=0,
                                 event_id=self.CLA_HALT_FREEFORM_EVENT_DICT)
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

    # load data from file and push it to the Postgres db
    # loaded = dl.load_data_from_file()
    # dl.push_data_to_sql()

    # load data from the Postgres db
    raw_mne = dl.load_data_from_sql(experiment_id=6)

    # find the events in the data
    events = mne.find_events(raw_mne, stim_channel='STI001')

    # other tests to run:
    # raw_mne_file = dl.to_mne_raw()
    # dfd = dl.to_pandas()
    # dfl = dl.to_polars()

    # create epochs
    # epochs = dl.create_mne_epochs()

    # raw_mne.plot()
    # testing feather file format for storing data in binary format:
    # dfd.to_feather('C:\\Users\\saspr\\source\\Python\\Tegan\\BCI\\Data\\CLA-SubjectJ-170508-3St-LRHand-Inter.fea')
    # testing parquet file format for storing data in binary format:
    # dfd.to_parquet('C:\\Users\\saspr\\source\\Python\\Tegan\\BCI\\Data\\CLA-SubjectJ-170508-3St-LRHand-Inter.gzip',
    #                compression='gzip')
    print("Finished.")

