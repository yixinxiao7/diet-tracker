import copy
import pytest


@pytest.fixture
def mock_event():
    return {
        "httpMethod": "GET",
        "resource": "/meals",
        "pathParameters": {},
        "queryStringParameters": {},
        "body": None,
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "test-cognito-user-id",
                    "email": "test@example.com"
                }
            }
        }
    }


@pytest.fixture
def event_copy(mock_event):
    return copy.deepcopy(mock_event)
