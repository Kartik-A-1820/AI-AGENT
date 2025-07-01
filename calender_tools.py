from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from get_google_service import get_google_credentials

def get_calendar_service():
    creds = get_google_credentials()
    return build('calendar', 'v3', credentials=creds)

class ScheduleMeetInput(BaseModel):
    event_title: str = Field(..., description="The title of the event.")
    start_time: str = Field(..., description="The start time of the event in ISO format.")
    end_time: str = Field(..., description="The end time of the event in ISO format.")
    description: str = Field("", description="A description of the event.")
    attendees: Optional[List[str]] = Field(None, description="A list of attendee email addresses.")
    timezone: str = Field("Asia/Kolkata", description="The timezone for the event.")

@tool
def schedule_google_meet_event(input_data: ScheduleMeetInput) -> str:
    """Create a calendar event with a Google Meet link."""
    try:
        service = build('calendar', 'v3', credentials=get_google_credentials())
        event = {
            "summary": input_data.event_title,
            "description": input_data.description,
            "start": {"dateTime": input_data.start_time, "timeZone": input_data.timezone},
            "end": {"dateTime": input_data.end_time, "timeZone": input_data.timezone},
            "attendees": [{"email": email} for email in (input_data.attendees or [])],
            "conferenceData": {
                "createRequest": {
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    "requestId": f"meet-{input_data.event_title}-{input_data.start_time}".replace(" ", "-"),
                }
            }
        }
        created_event = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1
        ).execute()
        meet_link = created_event.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri", "Meet link not generated")
        event_link = created_event.get("htmlLink")
        return f"Event scheduled: {event_link}\nGoogle Meet Link: {meet_link}"
    except Exception as e:
        return f"Failed to create Meet event: {e}"

class CreateEventInput(BaseModel):
    event_name: str = Field(..., description="The name of the event.")
    start_time: str = Field(..., description="The start time of the event in ISO format.")
    end_time: str = Field(..., description="The end time of the event in ISO format.")
    description: str = Field("", description="A description of the event.")
    timezone: str = Field("Asia/Kolkata", description="The timezone for the event.")

@tool
def create_calendar_event(input_data: CreateEventInput) -> str:
    """Create a new Google Calendar event."""
    try:
        service = get_calendar_service()
        event = {
            "summary": input_data.event_name,
            "description": input_data.description,
            "start": {"dateTime": input_data.start_time, "timeZone": input_data.timezone},
            "end": {"dateTime": input_data.end_time, "timeZone": input_data.timezone}
        }
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Event '{input_data.event_name}' created: {created_event.get('htmlLink')}"
    except Exception as e:
        return f"Failed to create event: {e}"

class ListEventsInput(BaseModel):
    max_results: int = Field(10, description="The maximum number of events to return.")

@tool
def list_calendar_events(input_data: ListEventsInput) -> str:
    """List upcoming Google Calendar events."""
    try:
        service = get_calendar_service()
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=input_data.max_results, singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        if not events:
            return "No upcoming events found."
        msg = ""
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            msg += f"Event ID: {event['id']}\nSummary: {event['summary']}\nStart: {start}\n\n"
        return msg
    except Exception as e:
        return f"Failed to list events: {e}"

class DeleteEventInput(BaseModel):
    event_id: str = Field(..., description="The ID of the event to delete.")

@tool
def delete_calendar_event(input_data: DeleteEventInput) -> str:
    """Delete a calendar event by its event ID."""
    try:
        service = get_calendar_service()
        service.events().delete(calendarId='primary', eventId=input_data.event_id).execute()
        return f"Event with ID '{input_data.event_id}' deleted."
    except Exception as e:
        return f"Failed to delete event: {e}"

class UpdateEventInput(BaseModel):
    event_id: str = Field(..., description="The ID of the event to update.")
    new_summary: Optional[str] = Field(None, description="The new summary for the event.")
    new_start: Optional[str] = Field(None, description="The new start time for the event in ISO format.")
    new_end: Optional[str] = Field(None, description="The new end time for the event in ISO format.")
    new_description: Optional[str] = Field(None, description="The new description for the event.")
    timezone: str = Field("Asia/Kolkata", description="The timezone for the event.")

@tool
def update_calendar_event(input_data: UpdateEventInput) -> str:
    """Update a calendar event's title, time, or description."""
    try:
        service = get_calendar_service()
        event = service.events().get(calendarId='primary', eventId=input_data.event_id).execute()
        if input_data.new_summary:
            event['summary'] = input_data.new_summary
        if input_data.new_description:
            event['description'] = input_data.new_description
        if input_data.new_start:
            event['start']['dateTime'] = input_data.new_start
            event['start']['timeZone'] = input_data.timezone
        if input_data.new_end:
            event['end']['dateTime'] = input_data.new_end
            event['end']['timeZone'] = input_data.timezone
        updated_event = service.events().update(calendarId='primary', eventId=input_data.event_id, body=event).execute()
        return f"Event updated: {updated_event.get('htmlLink')}"
    except Exception as e:
        return f"Failed to update event: {e}"

