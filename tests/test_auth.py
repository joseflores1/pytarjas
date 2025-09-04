import pytest
from flask import session, Flask
from flask.testing import FlaskClient

from conftest import AuthActions
from pytarjas.db import get_db

def test_register(client: FlaskClient, app: Flask):
    assert client.get('/auth/register').status_code == 200
    response = client.post(
        '/auth/register', data={'username': 'a', 'password': 'a'}
    )
    assert response.headers["Location"] == "/auth/login"

    with app.app_context():
        assert get_db().execute(
            "SELECT * FROM user WHERE username = 'a'",
        ).fetchone() is not None


@pytest.mark.parametrize(('username', 'password', 'message'), (
    ('', '', b'Username is required.'),
    ('a', '', b'Password is required.'),
    ('test', 'test', b'already registered'),
))
def test_register_validate_input(client: Flask, username: str, password: str, message: str):
    response = client.post(
        '/auth/register',
        data={'username': username, 'password': password}
    )
    assert message in response.data

def test_logout(client: FlaskClient, auth: AuthActions):
    auth.login()

    with client:
        auth.logout()
        assert "user_id" not in session