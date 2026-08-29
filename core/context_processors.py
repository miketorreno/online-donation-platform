def unread_notifications_count(request):
    from .models import Notification

    if request.user.is_authenticated:
        count = Notification.objects.filter(
            recipient=request.user, read=False
        ).count()
    else:
        count = 0
    return {"unread_notifications_count": count}
