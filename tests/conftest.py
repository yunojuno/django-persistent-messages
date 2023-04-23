from django.contrib.auth.models import User
from pytest import fixture

from persistent_messages.models import PersistentMessage


@fixture
def pm() -> PersistentMessage:
    return PersistentMessage.objects.create(content="This is a test message")


@fixture
def user() -> User:
    return User.objects.create_user(username="testuser", password="testpassword")
