import configparser

def get_db_connection():
    config = configparser.ConfigParser()
    config.read('config.ini')

    return (f"mssql+pyodbc://{config['DATABASE']['USER']}:{config['DATABASE']['PASSWORD']}@"
            f"{config['DATABASE']['SERVER']}/{config['DATABASE']['DATABASE']}?"
            f"driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes")