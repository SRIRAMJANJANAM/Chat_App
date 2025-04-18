from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Message
from django.db.models import Q
from datetime import datetime
from django.utils import timezone

@login_required
def chat_room(request, room_name):
    search_query = request.GET.get('search', '')
    users = User.objects.exclude(id=request.user.id)

    # Filter chat messages between logged-in user and selected room user
    chats = Message.objects.filter(
        (Q(sender=request.user) & Q(receiver__username=room_name)) |
        (Q(receiver=request.user) & Q(sender__username=room_name))
    )

    if search_query:
        chats = chats.filter(Q(content__icontains=search_query))

    # Order messages by timestamp
    chats = chats.order_by('timestamp')

    # Convert timestamps to local time (India Standard Time)
    for chat in chats:
        print("Timestamp (UTC):", chat.timestamp)

        # Ensure timestamp is aware if it is naive (in case USE_TZ is True)
        if timezone.is_naive(chat.timestamp):
            chat.timestamp = timezone.make_aware(chat.timestamp, timezone.get_current_timezone())  # Use current time zone

        # Convert to local time (IST)
        local_time = timezone.localtime(chat.timestamp)  # Convert UTC to local time

        print("Timestamp (Local):", local_time)  # For debugging purposes

        # Update the chat object with the local time (optional, for display purposes)
        chat.timestamp = local_time

    user_last_messages = []

    for user in users:
        last_message = Message.objects.filter(
            (Q(sender=request.user) & Q(receiver=user)) |
            (Q(receiver=request.user) & Q(sender=user))
        ).order_by('-timestamp').first()

        user_last_messages.append({
            'user': user,
            'last_message': last_message
        })

    # Sort users by most recent message (converted to local time)
    user_last_messages.sort(
        key=lambda x: timezone.localtime(x['last_message'].timestamp) if x['last_message'] and x['last_message'].timestamp and not timezone.is_naive(x['last_message'].timestamp) else timezone.make_aware(datetime.min),
        reverse=True
    )

    return render(request, 'chat.html', {
        'room_name': room_name,
        'chats': chats,
        'users': users,
        'user_last_messages': user_last_messages,
        'search_query': search_query
    })
