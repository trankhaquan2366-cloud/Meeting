from datetime import datetime, timezone

from app.schemas.meeting import MeetingCreateRequest, MeetingResponse


def test_create_request_converts_naive_vietnamese_wall_time_to_utc():
    request = MeetingCreateRequest(
        title="UTC conversion",
        meeting_type="online",
        online_link="https://meet.example.com",
        start_time=datetime(2030, 1, 1, 20),
        end_time=datetime(2030, 1, 1, 21),
    )

    assert request.start_time == datetime(2030, 1, 1, 13)
    assert request.end_time == datetime(2030, 1, 1, 14)
    assert request.start_time.tzinfo is None


def test_create_request_converts_offset_aware_times_to_utc():
    request = MeetingCreateRequest(
        title="UTC conversion",
        meeting_type="online",
        online_link="https://meet.example.com",
        start_time="2030-01-01T20:00:00+07:00",
        end_time="2030-01-01T21:00:00+07:00",
    )

    assert request.start_time == datetime(2030, 1, 1, 13)
    assert request.end_time == datetime(2030, 1, 1, 14)


def test_meeting_response_marks_database_times_as_utc():
    response = MeetingResponse(
        id=1,
        title="UTC response",
        start_time=datetime(2030, 1, 1, 13),
        end_time=datetime(2030, 1, 1, 14),
        status="CONFIRMED",
    )

    assert response.start_time.tzinfo is timezone.utc
    assert response.model_dump(mode="json")["start_time"] == "2030-01-01T13:00:00Z"
