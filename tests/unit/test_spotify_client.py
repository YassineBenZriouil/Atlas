"""SpotifyClient logic, with requests mocked - never makes a real network
call in the default test suite."""

from unittest.mock import MagicMock, patch

import pytest

from atlas.integrations.spotify.client import (
    SpotifyApiError,
    SpotifyClient,
    SpotifyNoActiveDeviceError,
    SpotifyNotAuthenticatedError,
)


def _mock_response(status_code=200, json_data=None, text=""):
    response = MagicMock()
    response.status_code = status_code
    response.ok = status_code < 400
    response.text = text
    response.json.return_value = json_data or {}
    return response


@patch("atlas.integrations.spotify.client.load_refresh_token", return_value="refresh-token")
@patch("atlas.integrations.spotify.client.requests.post")
def test_ensure_access_token_refreshes(mock_post, _mock_refresh):
    mock_post.return_value = _mock_response(json_data={"access_token": "abc", "expires_in": 3600})
    client = SpotifyClient("client-id", "client-secret")

    token = client._ensure_access_token()

    assert token == "abc"
    mock_post.assert_called_once()


@patch("atlas.integrations.spotify.client.load_refresh_token", return_value=None)
def test_ensure_access_token_requires_refresh_token(_mock_refresh):
    client = SpotifyClient("client-id", "client-secret")
    with pytest.raises(SpotifyNotAuthenticatedError):
        client._ensure_access_token()


@patch("atlas.integrations.spotify.client.load_refresh_token", return_value="refresh-token")
@patch("atlas.integrations.spotify.client.requests.post")
def test_ensure_access_token_failure_raises_not_authenticated(mock_post, _mock_refresh):
    mock_post.return_value = _mock_response(status_code=400, text="invalid_client")
    client = SpotifyClient("client-id", "client-secret")
    with pytest.raises(SpotifyNotAuthenticatedError):
        client._ensure_access_token()


@patch("atlas.integrations.spotify.client.requests.request")
@patch.object(SpotifyClient, "_ensure_access_token", return_value="abc")
def test_no_active_device_raises_specific_error(_mock_token, mock_request):
    mock_request.return_value = _mock_response(status_code=404, text="NO_ACTIVE_DEVICE")
    client = SpotifyClient("client-id", "client-secret")
    with pytest.raises(SpotifyNoActiveDeviceError):
        client.play()


@patch("atlas.integrations.spotify.client.requests.request")
@patch.object(SpotifyClient, "_ensure_access_token", return_value="abc")
def test_generic_api_error_raises(_mock_token, mock_request):
    mock_request.return_value = _mock_response(status_code=500, text="server error")
    client = SpotifyClient("client-id", "client-secret")
    with pytest.raises(SpotifyApiError):
        client.play()


@patch("atlas.integrations.spotify.client.requests.request")
@patch.object(SpotifyClient, "_ensure_access_token", return_value="abc")
def test_search_track_returns_first_item(_mock_token, mock_request):
    mock_request.return_value = _mock_response(
        json_data={"tracks": {"items": [{"name": "Song", "uri": "spotify:track:1"}]}}
    )
    client = SpotifyClient("client-id", "client-secret")
    track = client.search_track("song")
    assert track == {"name": "Song", "uri": "spotify:track:1"}


@patch("atlas.integrations.spotify.client.requests.request")
@patch.object(SpotifyClient, "_ensure_access_token", return_value="abc")
def test_search_track_returns_none_when_empty(_mock_token, mock_request):
    mock_request.return_value = _mock_response(json_data={"tracks": {"items": []}})
    client = SpotifyClient("client-id", "client-secret")
    assert client.search_track("nonexistent") is None


@patch("atlas.integrations.spotify.client.requests.request")
@patch.object(SpotifyClient, "_ensure_access_token", return_value="abc")
def test_find_playlist_matches_case_insensitively(_mock_token, mock_request):
    mock_request.return_value = _mock_response(
        json_data={"items": [{"name": "Workout Mix", "uri": "spotify:playlist:1"}]}
    )
    client = SpotifyClient("client-id", "client-secret")
    playlist = client.find_playlist("workout")
    assert playlist is not None
    assert playlist["uri"] == "spotify:playlist:1"
