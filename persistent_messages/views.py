import logging

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404

from .exceptions import PersistentMessageException
from .models import PersistentMessage

logger = logging.getLogger(__name__)


def dismiss_message(request: HttpRequest, message_id: int) -> HttpResponse:
    """
    Dismiss a message for the current user.

    Designed to be used from a JS function, so returns a simple
    HttpResponse with a 204 status code.

    There is no logic in here to determine whether the user should have
    seen the message in the first place - it's a dumb, optimistic
    approach to dismissing messages.

    If the message is not dismissable, it will return a 400 status code,
    and log the exception.

    """
    message = get_object_or_404(PersistentMessage, pk=message_id)
    try:
        message.dismiss(request.user)
    except PersistentMessageException:
        logger.exception("Error dismissing message %s", message_id)
        return HttpResponse(status=400)
    return HttpResponse(status=204)
