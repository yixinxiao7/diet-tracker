def get_claims(event):
    return event["requestContext"]["authorizer"]["claims"]


def get_cognito_sub(event):
    return get_claims(event)["sub"]


def get_email(event):
    return get_claims(event).get("email")


def get_user_id(event):
    return get_cognito_sub(event)


def get_user_email(event):
    return get_email(event)
