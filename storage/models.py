# storage/models.py
from django.db import models
import os
import uuid

class UserFile(models.Model):
    username = models.CharField(max_length=150)
    original_filename = models.CharField(max_length=255) # Original name before encryption
    encrypted_filename = models.CharField(max_length=255, unique=True) # Name of the stored encrypted file
    # Store the part of the key needed for decryption (e.g., prime q or the modulus n)
    # The user will provide the other part (e.g., prime p)
    stored_key_part = models.TextField() # Store prime 'q' or modulus 'n'
    # Store relative paths within MEDIA_ROOT
    location1 = models.CharField(max_length=512)
    location2 = models.CharField(max_length=512)
    location3 = models.CharField(max_length=512)
    upload_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} - {self.original_filename}"