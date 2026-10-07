from django.db import models
from cloudinary.models import CloudinaryField

class Entry(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    image = CloudinaryField("image", blank=True, null=True)
    def __str__(self):
        return self.title