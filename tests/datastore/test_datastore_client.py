from unittest.mock import MagicMock, patch

from google.oauth2.service_account import Credentials

from pdf_bot.datastore import MyDatastoreClient


class TestMyDatastoreClient:
    def test_init(self) -> None:
        service_account = {"service": "account"}
        creds = MagicMock(spec=Credentials)

        with patch("pdf_bot.datastore.datastore_client.Credentials") as creds_cls, patch(
            "pdf_bot.datastore.datastore_client.Client.__init__"
        ) as client_init:
            creds_cls.from_service_account_info.return_value = creds

            MyDatastoreClient(service_account)

            creds_cls.from_service_account_info.assert_called_once_with(service_account)
            client_init.assert_called_once_with(credentials=creds)
