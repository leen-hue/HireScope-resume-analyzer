import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.textanalytics import TextAnalyticsClient
from azure.storage.blob import BlobServiceClient

load_dotenv()


def get_doc_intel_client():
    return DocumentIntelligenceClient(
        endpoint=os.environ["DOCUMENTINTELLIGENCE_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["DOCUMENTINTELLIGENCE_KEY"]),
    )


def get_language_client():
    return TextAnalyticsClient(
        endpoint=os.environ["LANGUAGE_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["LANGUAGE_KEY"]),
    )


def get_blob_container():
    service = BlobServiceClient.from_connection_string(
        os.environ["STORAGE_CONNECTION_STRING"]
    )
    return service.get_container_client(os.environ["BLOB_CONTAINER_NAME"])
