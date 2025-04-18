from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Message(models.Model):
    sender = models.ForeignKey(User, related_name="sent_messages", on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name="received_messages", on_delete=models.CASCADE)
    content = models.TextField()
    audio_file = models.FileField(upload_to='audio/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} -> {self.receiver}: {self.content[:20]}"

    def get_local_timestamp(self):
        # Ensure that timestamp is timezone-aware
        if timezone.is_naive(self.timestamp):
            self.timestamp = timezone.make_aware(self.timestamp, timezone.utc)
        # Convert the timestamp to local time
        return timezone.localtime(self.timestamp)
