# storage/forms.py
from django import forms
from django.core.exceptions import ValidationError
import os

class UsernameForm(forms.Form):
    username = forms.CharField(max_length=150, label="Enter Username",
                               widget=forms.TextInput(attrs={'placeholder': 'Your Username'}))

class UploadForm(forms.Form):
    filename = forms.CharField(max_length=255, required=False, label="Save File As (Optional)",
                               widget=forms.TextInput(attrs={'placeholder': 'Leave blank to use original name'}))
    file = forms.FileField(label="Select .txt File to Upload") # Update label slightly

    def clean_file(self):
        """Validate that the uploaded file is a .txt file."""
        file = self.cleaned_data.get('file')
        if file:
            # Get the file extension
            ext = os.path.splitext(file.name)[1] # Gets '.txt'
            if ext.lower() != '.txt':
                raise ValidationError("Invalid file type. Only .txt files are allowed.")
        return file

    def clean_filename(self):
        """Ensure the desired filename also ends with .txt if provided."""
        desired_filename = self.cleaned_data.get('filename')
        if desired_filename:
             # Ensure it ends with .txt, append if missing
             if not desired_filename.lower().endswith('.txt'):
                 desired_filename += '.txt'
             # Basic sanitization (optional but recommended)
             # Remove potentially harmful characters, but allow spaces, underscores, hyphens
             # Keep it simple for now, just ensure .txt extension
             pass
        return desired_filename


class DownloadForm(forms.Form):
    file_id = forms.IntegerField(widget=forms.HiddenInput())
    file_key = forms.CharField(label="Enter File Key", widget=forms.PasswordInput(attrs={'placeholder': 'Your Secret Key (p)'}))