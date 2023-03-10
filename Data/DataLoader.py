from Utilities.Config.Config import Config
from Utilities.Database.Postgres.PostgresConnector import PostgresConnector
import pandas as pd
import polars as pl
from scipy.io import loadmat
import getpass
import platform
import mne
import os

# imports for preprocessing and classification testing
import numpy as np
from mne.decoding import CSP
from mne.preprocessing import ICA
from mne.decoding import UnsupervisedSpatialFilter

from sklearn.pipeline import Pipeline
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.model_selection import ShuffleSplit, cross_val_score
from sklearn.decomposition import PCA, FastICA


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
    experiment_paradigm = None  # e.g., 5F, CLA, FREEFORM, HaLT, NoMT
    experiment_stimuli = None  # e.g., LRHand
    subject = None  # A-J
    file_date = None  # YYMMDD
    states = None  # e.g., 3St
    experiment_mode = None  # e.g., Inter, HFREQ

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
        self.framework = config['data_framework']
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
                full_filename = '/Users/Shared/' + filename
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
        # other fields of interest: info['device_info'], info['dev_head_t'], info['experimenter'], info[???helium_info???],
        # info['line_freq'], info['temp']
        return info

    def create_mne_epochs(self, raw_mne) -> mne.Epochs:
        """
        Method to create MNE epochs array from scratch
        :return: MNE Epochs Array contains the epochs data
        :rtype: mne.EpochsArray
        """
        events = mne.find_events(raw_mne, stim_channel='STI001')
        picks = mne.pick_types(raw_mne.info, meg=False, eeg=True, stim=False, eog=False, exclude='bads')
        event_dict= self.create_event_dict_from_events(events=events)
        t_min = dl.config['epochs_settings']['t_min']
        t_max = dl.config['epochs_settings']['t_max']
        epochs = mne.Epochs(raw=raw_mne, events=events, tmin=t_min, tmax=t_max, event_id=event_dict, preload=True,
                            picks=picks)
        return epochs

    def create_event_dict_from_events(self, events) -> dict:
        event_dict = {}
        unique_event_ids = np.unique(events[:, 2])
        # look for all entries in the supplied event ids
        for name, value in self.CLA_HALT_FREEFORM_EVENT_DICT.items():
            if value in unique_event_ids:
                event_dict[name] = value
        return event_dict

    def create_mne_evoked(self, raw_mne, method="mean", by_event_type=False) -> mne.Evoked:
        epochs = self.create_mne_epochs(raw_mne=raw_mne)
        evoked = epochs.average(method=method, by_event_type=by_event_type)
        return evoked


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
    do_plots = bool(config['do_plots'])

    # load data from file and push it to the Postgres db
    #loaded = dl.load_data_from_file()
    #dl.push_data_to_sql()

    # load data from the Postgres db
    raw_mne = dl.load_data_from_sql(experiment_id=dl.config['data']['experiment_id'])

    # find the events in the data
    events = mne.find_events(raw_mne, stim_channel='STI001')

    # create the vector to "pick" the EEG channels only
    picks = mne.pick_types(raw_mne.info, meg=False, eeg=True, stim=False, eog=False, exclude='bads')

    # plot the raw data with events overlaid
    if do_plots:
        raw_mne.plot(events=events, color='gray', event_color=dl.CLA_HALT_FREEFORM_EVENT_COLORS, scalings='auto')

    # try some filtering
    raw_filter = raw_mne.copy()
    low_pass_frequency = dl.config['filter_settings']['low_pass_frequency']
    high_pass_frequency = dl.config['filter_settings']['high_pass_frequency']
    if high_pass_frequency == 0:
        high_pass_frequency = None
    raw_filter.filter(low_pass_frequency, high_pass_frequency, fir_design='firwin', skip_by_annotation='edge',
                      picks='eeg')

    # other data format tests to run:
    # raw_mne_file = dl.to_mne_raw()
    # dfd = dl.to_pandas()
    # dfl = dl.to_polars()

    # create epochs
    t_min = dl.config['epochs_settings']['t_min']
    t_max = dl.config['epochs_settings']['t_max']
    event_dict = dl.create_event_dict_from_events(events=events)
    epochs = mne.Epochs(raw=raw_filter, events=events, tmin=t_min, tmax=t_max, event_id=event_dict, preload=True,
                        picks=picks)
    epochs_to_use = epochs[['left hand MI', 'right hand MI']]
    epochs_data = epochs_to_use.get_data()

    # create Evoked objects
    if bool(dl.config['create_evoked_objects']):
        evoked_lh = epochs['left hand MI'].average()
        evoked_rh = epochs['right hand MI'].average()

    # perform CSP classification
    if bool(dl.config['CSP_settings']['CSP_classifier']):
        # set aside training data for the CSP using left and right hand MI events only
        epochs_train = epochs_to_use.copy().crop(tmin=dl.config['CSP_settings']['t_min'],
                                                 tmax=dl.config['CSP_settings']['t_max'])
        labels = epochs_to_use.events[:, -1] - 1

        # define a monte-carlo cross-validation generator (reduce variance):
        epochs_data_train = epochs_train.get_data()
        cv = ShuffleSplit(10, test_size=0.2, random_state=42)
        cv_split = cv.split(epochs_data_train)

        # assemble a classifier
        lda = LinearDiscriminantAnalysis()
        csp = CSP(n_components=dl.config['CSP_settings']['num_components'], reg=None, log=True, norm_trace=False)

        # use scikit-learn Pipeline with cross_val_score function
        clf = Pipeline([('CSP', csp), ('LDA', lda)])
        scores = cross_val_score(clf, epochs_data_train, labels, cv=cv, n_jobs=1)

        # printing the results
        class_balance = np.mean(labels == labels[0])
        class_balance = max(class_balance, 1. - class_balance)
        print("Classification accuracy: %f / Chance level: %f" % (np.mean(scores), class_balance))

        # plot CSP patterns estimated on full data for visualization
        if do_plots:
            csp.fit_transform(epochs_data, labels)
            csp.plot_patterns(epochs.info, ch_type='eeg', units='Patterns (AU)', size=1.5)

        sfreq = raw_mne.info['sfreq']
        w_length = int(sfreq * 0.5)     # running classifier: window length
        w_step = int(sfreq * 0.1)       # running classifier: window step size
        w_start = np.arange(0, epochs_data.shape[2] - w_length, w_step)

        scores_windows = []
        for train_idx, test_idx in cv_split:
            y_train, y_test = labels[train_idx], labels[test_idx]

            X_train = csp.fit_transform(epochs_data_train[train_idx], y_train)
            X_test = csp.transform(epochs_data_train[test_idx])

            # fit classifier
            lda.fit(X_train, y_train)

            # running classifier: test classifier on sliding window
            score_this_window = []
            for n in w_start:
                X_test = csp.transform(epochs_data[test_idx][:, :, n:(n + w_length)])
                score_this_window.append(lda.score(X_test, y_test))
            scores_windows.append(score_this_window)

        # plot scores over time
        w_times = (w_start + w_length / 2.) / sfreq + epochs.tmin

        if do_plots:
            plt.figure()
            plt.plot(w_times, np.mean(scores_windows, 0), label='Score')
            plt.axvline(0, linestyle='--', color='k', label='Onset')
            plt.axhline(0.5, linestyle='-', color='k', label='Chance')
            plt.xlabel('time (s)')
            plt.ylabel('classification accuracy')
            plt.title('Classification score over time')
            plt.legend(loc='lower right')
            plt.show()

    # visualize Epochs
    if do_plots:
        epochs['left hand MI'].plot_psd(picks='eeg')
        epochs['left hand MI'].plot_psd_topomap()
        epochs['left hand MI'].plot_image(picks='eeg', combine='mean')

    # use PCA filtering
    if bool(dl.config['PCA_settings']['PCA_filter']):
        num_components = dl.config['PCA_settings']['num_components']
        pca = UnsupervisedSpatialFilter(PCA(num_components), average=False)
        pca_data = pca.fit_transform(epochs_data)
        ev = mne.EvokedArray(np.mean(pca_data, axis=0),
                             mne.create_info(num_components, epochs_to_use.info['sfreq'],
                                             ch_types='eeg'), tmin=t_min)
        if do_plots:
            ev.plot(show=False, window_title="PCA", time_unit='s')

    # use ICA filtering
    if bool(dl.config['ICA_settings']['ICA_filter']):
        num_components = dl.config['ICA_settings']['num_components']
        ica = UnsupervisedSpatialFilter(FastICA(num_components), average=False)
        ica_data = ica.fit_transform(epochs_data)
        ev1 = mne.EvokedArray(np.mean(ica_data, axis=0),
                              mne.create_info(num_components, epochs_to_use.info['sfreq'],
                                              ch_types='eeg'), tmin=t_min)
        if do_plots:
            ev1.plot(show=False, window_title='ICA', time_unit='s')

    # use ICA preprocessing
    if bool(dl.config['ICA_settings']['ICA_preprocess']):
        # vary num_components that seem to represent the actual brain activations well
        num_components = dl.config['ICA_settings']['num_components']
        ica = ICA(n_components=num_components, method='fastica')
        ica.fit(raw_filter)
        if do_plots:
            ica.plot_components()
            ica.plot_properties(raw_filter, picks=range(num_components))
            ica.plot_overlay(raw_filter)

    print("Finished.")
