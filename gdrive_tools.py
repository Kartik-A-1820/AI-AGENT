from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import Optional
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
from googleapiclient.discovery import build
from get_google_service import get_google_credentials
import os

class UploadDriveInput(BaseModel):
    local_path: str = Field(..., description="The local path of the file to upload.")
    drive_folder_id: Optional[str] = Field(None, description="The ID of the Google Drive folder to upload to.")

@tool
def upload_drive_file(input_data: UploadDriveInput) -> str:
    """Uploads a local file to Google Drive, optionally to a specific folder."""
    try:
        service = build('drive', 'v3', credentials=get_google_credentials())
        file_metadata = {'name': os.path.basename(input_data.local_path)}
        if input_data.drive_folder_id:
            file_metadata['parents'] = [input_data.drive_folder_id]
        media = MediaFileUpload(input_data.local_path, resumable=True)
        file = service.files().create(
            body=file_metadata, media_body=media, fields='id, webViewLink'
        ).execute()
        return f"File uploaded! ID: {file.get('id')}, Link: {file.get('webViewLink')}"
    except Exception as e:
        return f"Failed to upload file: {e}"

class DownloadDriveInput(BaseModel):
    file_id: str = Field(..., description="The ID of the file to download from Google Drive.")
    local_path: str = Field(..., description="The local path to save the downloaded file to.")

@tool
def download_drive_file(input_data: DownloadDriveInput) -> str:
    """Downloads a file from Google Drive to a local path."""
    try:
        service = build('drive', 'v3', credentials=get_google_credentials())
        request = service.files().get_media(fileId=input_data.file_id)
        fh = io.FileIO(input_data.local_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        return f"File downloaded as {input_data.local_path}"
    except Exception as e:
        return f"Failed to download file: {e}"

class ListDriveInput(BaseModel):
    query: str = Field("mimeType != 'application/vnd.google-apps.folder'", description="The search query for files in Google Drive.")
    max_results: int = Field(10, description="The maximum number of files to return.")

@tool
def list_drive_files(input_data: ListDriveInput) -> str:
    """
    Lists files in Google Drive matching a search query.
    """
    try:
        service = build('drive', 'v3', credentials=get_google_credentials())
        results = service.files().list(q=input_data.query, pageSize=input_data.max_results, fields="files(id, name, mimeType)").execute()
        files = results.get('files', [])
        if not files:
            return "No files found."
        msg = ""
        for file in files:
            msg += f"ID: {file['id']} | Name: {file['name']} | Type: {file['mimeType']}\n"
        return msg
    except Exception as e:
        return f"Failed to list files: {e}"

