import json


class Config(object):

    file_name = None
    settings = None

    def __init__(self, file_name=None):
        self.file_name = file_name

        # load the config
        try:
            with open(self.file_name, "r") as f:
                self.settings = json.load(f)
        except FileNotFoundError as e:
            pass


if __name__ == '__main__':
    # for Steven
    filename = 'C:\\Users\\saspr\\source\\Python\\Tegan\\BCI\\Utilities\\Config\\config_steven.json'
    # for Tegan
    # filename = '/Users/BCI/Utilities/Config/config_tegan.json'
    config = Config(filename)
    print('Finished testing.')
