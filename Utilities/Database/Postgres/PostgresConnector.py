import psycopg2 as pg
import pandas as pd


class PostgresConnector(object):

    DATABASE = 'BCI'
    USER = 'postgres'
    PWD = 'root'
    HOST = '127.0.0.1'
    PORT = '5432'

    connection = None
    cursor = None
    connected = None

    def __init__(self):
        self.connection = pg.connect(database=self.DATABASE, user=self.USER, password=self.PWD, host=self.HOST,
                                              port=self.PORT)
        self.cursor = self.connection.cursor()
        self.connected = True

    def execute_query(self, sql_query=None) -> list:
        self.cursor.execute(sql_query)
        rows = self.cursor.fetchall()
        return rows

    def execute_query_to_pandas(self, sql_query=None) -> pd.DataFrame:
        self.cursor.execute(sql_query)
        rows = self.cursor.fetchall()

        # now create a Pandas DataFrame from the results
        columns = []
        for desc in self.cursor.description:
            columns.append(desc.name)
        df = pd.DataFrame(data=rows, columns=columns)
        return df

    def execute(self, sql_query=None):
        self.cursor.execute(sql_query)
        self.connection.commit()

    def close_connection(self):
        self.cursor.close()
        self.connection.close()


if __name__ == '__main__':
    postgres = PostgresConnector()
    df = postgres.execute_query_to_pandas('select * from marker_codes')
    print('Finished.')
