from google.cloud.datastore import Client
from google.oauth2.service_account import Credentials


class MyDatastoreClient(Client):
    def __init__(self, service_account_dict: dict):
        credentials = Credentials.from_service_account_info(service_account_dict)
        super().__init__(credentials=credentials)
