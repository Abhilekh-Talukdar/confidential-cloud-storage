# storage/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
from django.conf import settings
from .models import UserFile
from django.contrib import messages # Import messages framework
from .forms import UsernameForm, UploadForm, DownloadForm # We'll create forms next
from django.views.decorators.http import require_POST # Ensure POST method
from .encryption_utils import encrypt_file, split_file
from .decryption_utils import combine_files, decrypt_file
import os
import uuid
import shutil # For cleaning up temporary files

def index_view(request):
    """Page 1: Ask for username and action (upload/download)."""
    if request.method == 'POST':
        form = UsernameForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            request.session['username'] = username # Store username in session
            if 'upload_action' in request.POST:
                return redirect('storage:upload_page')
            elif 'download_action' in request.POST:
                return redirect('storage:download_list')
    else:
        form = UsernameForm()
    return render(request, 'storage/index.html', {'form': form})

def upload_page_view(request):
    """Page 3: Handle file upload."""
    username = request.session.get('username')
    if not username:
        return redirect('storage:index') # Redirect if username not in session

    file_key_p = None # To display the key after upload

    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            desired_filename = form.cleaned_data['filename']
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            temp_file_path = os.path.join(temp_dir, uploaded_file.name)

            # 1. Save uploaded file temporarily
            with open(temp_file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # 2. Encrypt the temporary file
            unique_id = uuid.uuid4().hex # Unique identifier for filenames
            encrypted_filename_base = f"{username}_{unique_id}"
            encrypted_file_path, p, q, n = encrypt_file(temp_file_path, encrypted_filename_base)

            if encrypted_file_path and p and q and n:
                # 3. Split the encrypted file
                location1, location2, location3 = split_file(encrypted_file_path)

                if location1 is not None: # Check if splitting was successful
                    # 4. Save file info to database
                    UserFile.objects.create(
                        username=username,
                        original_filename=desired_filename or uploaded_file.name, # Use desired or original
                        encrypted_filename=os.path.basename(encrypted_file_path),
                        stored_key_part=str(q), # Store prime q
                        location1=location1,
                        location2=location2, # Can be None
                        location3=location3  # Can be None
                    )
                    file_key_p = p # Set the key to display to the user
                    print(f"File {desired_filename or uploaded_file.name} uploaded successfully for {username}.")
                    form = UploadForm() # Reset form after successful upload
                else:
                    print("Error: File splitting failed.")
                    # Clean up encrypted file if splitting failed
                    if os.path.exists(encrypted_file_path):
                        os.remove(encrypted_file_path)
                    # Add error message to form or context
            else:
                print("Error: File encryption failed.")
                # Add error message to form or context

            # 5. Clean up temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            try:
                if not os.listdir(temp_dir): # Remove temp dir if empty
                    os.rmdir(temp_dir)
            except OSError:
                 pass # Ignore if removal fails (e.g., race condition)


        # Else (form not valid): Fall through to render the form with errors
    else:
        form = UploadForm()

    return render(request, 'storage/upload_page.html', {
        'form': form,
        'username': username,
        'file_key_p': file_key_p # Pass the key to the template
        })

@require_POST # Ensures this view only accepts POST requests
def delete_file_view(request, file_id):
    """Handles the deletion of a file record and its associated chunks."""
    username = request.session.get('username')
    if not username:
        # Redirect to login or index if user not identified
        messages.error(request, "Session expired. Please enter username again.")
        return redirect('storage:index')

    # Get the file record, ensuring it belongs to the current user
    file_record = get_object_or_404(UserFile, id=file_id, username=username)

    # --- File Deletion Logic ---
    error_occurred = False

    # 1. Delete file chunks
    part_paths = [file_record.location1, file_record.location2, file_record.location3]
    chunk_dir = None
    for part_rel_path in part_paths:
        if part_rel_path: # Ensure path is not None
            part_full_path = os.path.join(settings.MEDIA_ROOT, part_rel_path)
            if chunk_dir is None: # Get the directory from the first valid part
                 chunk_dir = os.path.dirname(part_full_path)
            try:
                if os.path.exists(part_full_path):
                    os.remove(part_full_path)
                    print(f"Deleted chunk: {part_full_path}")
            except OSError as e:
                print(f"Error deleting chunk {part_full_path}: {e}")
                messages.error(request, f"Error deleting part of file {file_record.original_filename}.")
                error_occurred = True
                # Decide if you want to stop or continue trying to delete other parts/record

    # 2. Attempt to delete the chunk directory if it exists and is empty
    if chunk_dir and os.path.exists(chunk_dir):
        try:
            # Check if directory is empty AFTER attempting to delete files
            if not os.listdir(chunk_dir):
                os.rmdir(chunk_dir)
                print(f"Deleted chunk directory: {chunk_dir}")
        except OSError as e:
            # Ignore error if directory is not empty or other issues occur
            print(f"Could not remove chunk directory {chunk_dir}: {e}")
            pass # Don't flag as error if dir removal fails, main parts deleted are key

    # 3. Delete the main encrypted file (optional - depends if you keep it after splitting)
    # Check if your workflow keeps the combined encrypted file after splitting.
    # If encrypt_file saves it and split_file just reads it, you might need to delete it.
    # Let's assume the main encrypted file might exist in 'MEDIA_ROOT/encrypted/'
    encrypted_file_path = os.path.join(settings.MEDIA_ROOT, 'encrypted', file_record.encrypted_filename)
    try:
         if os.path.exists(encrypted_file_path):
              os.remove(encrypted_file_path)
              print(f"Deleted encrypted file: {encrypted_file_path}")
    except OSError as e:
          print(f"Error deleting encrypted file {encrypted_file_path}: {e}")
          messages.error(request, f"Could not delete main encrypted file for {file_record.original_filename}.")
          # Depending on severity, you might set error_occurred = True

    # 4. Delete the database record (only if file deletions were mostly successful, or always attempt?)
    # Let's attempt deletion even if some file parts failed to delete, but log errors.
    try:
        original_filename = file_record.original_filename # Save name for message
        file_record.delete()
        print(f"Deleted database record for: {original_filename}")
        if not error_occurred:
             messages.success(request, f"Successfully deleted '{original_filename}'.")
        else:
             messages.warning(request, f"Deleted database record for '{original_filename}', but encountered errors deleting some associated files.")

    except Exception as e:
        print(f"Error deleting database record for file ID {file_id}: {e}")
        messages.error(request, f"Failed to delete the database record for '{file_record.original_filename}'.")


    # 5. Redirect back to the download list
    return redirect('storage:download_list')


def download_list_view(request):
    """Page 2 (Part 1): Show list of files for the user."""
    username = request.session.get('username')
    if not username:
        return redirect('storage:index')

    user_files = UserFile.objects.filter(username=username).order_by('-upload_date')
    return render(request, 'storage/download_list.html', {
        'username': username,
        'files': user_files
        })


def download_file_view(request):
    """Page 2 (Part 2): Handle file download action."""
    username = request.session.get('username')
    if not username:
        return redirect('storage:index')

    if request.method == 'POST':
        form = DownloadForm(request.POST)
        if form.is_valid():
            file_id = form.cleaned_data['file_id']
            user_key_p_str = form.cleaned_data['file_key']

            try:
                user_key_p = int(user_key_p_str)
            except (ValueError, TypeError):
                user_files = UserFile.objects.filter(username=username).order_by('-upload_date')
                messages.error(request, 'Invalid file key format. Please enter a number.')
                return render(request, 'storage/download_list.html', {
                    'username': username,
                    'files': user_files,
                })


            try:
                file_record = UserFile.objects.get(id=file_id, username=username)
            except UserFile.DoesNotExist:
                raise Http404("File not found or access denied.")

            try:
                stored_key_q = int(file_record.stored_key_part)
            except (ValueError, TypeError):
                print(f"Error: Stored key for file {file_id} is invalid.")
                user_files = UserFile.objects.filter(username=username).order_by('-upload_date')
                messages.error(request, 'Error retrieving stored key. Cannot decrypt.')
                return render(request, 'storage/download_list.html', {
                    'username': username,
                    'files': user_files,
                })

            # Ensure the original filename ends with .txt (it should, due to upload validation)
            download_filename = file_record.original_filename
            if not download_filename.lower().endswith('.txt'):
                # This case shouldn't happen if upload validation works, but as a fallback:
                download_filename += '.txt'

            # Define paths for temporary combined and decrypted files
            temp_combined_dir = os.path.join(settings.MEDIA_ROOT, 'temp_combined')
            os.makedirs(temp_combined_dir, exist_ok=True)
            combined_encrypted_path = os.path.join(temp_combined_dir, file_record.encrypted_filename)

            temp_decrypted_dir = os.path.join(settings.MEDIA_ROOT, 'temp_decrypted')
            os.makedirs(temp_decrypted_dir, exist_ok=True)
            # Use a temporary name for decryption, final name is set in response header
            temp_decrypted_filename = f"{uuid.uuid4()}.tmp"
            decrypted_file_path = os.path.join(temp_decrypted_dir, temp_decrypted_filename)


            # 1. Combine file parts
            part_paths = [file_record.location1, file_record.location2, file_record.location3]
            if not combine_files(part_paths, combined_encrypted_path):
                print("Error: Failed to combine file parts.")
                if os.path.exists(combined_encrypted_path): os.remove(combined_encrypted_path)
                user_files = UserFile.objects.filter(username=username).order_by('-upload_date')
                messages.error(request, 'Error combining file parts. Download failed.')
                return render(request, 'storage/download_list.html', {
                    'username': username,
                    'files': user_files,
                })

            # 2. Decrypt the combined file
            decryption_success = decrypt_file(combined_encrypted_path, decrypted_file_path, user_key_p, stored_key_q)

            # 3. Clean up combined encrypted file
            if os.path.exists(combined_encrypted_path): os.remove(combined_encrypted_path)
            try:
                if not os.listdir(temp_combined_dir): os.rmdir(temp_combined_dir)
            except OSError: pass

            if decryption_success:
                # 4. Serve the decrypted file for download
                try:
                    with open(decrypted_file_path, 'rb') as f:
                        # *** CHANGE HERE: Set Content-Type to text/plain ***
                        response = HttpResponse(f.read(), content_type='text/plain')
                        # Ensure filename in header ends with .txt
                        response['Content-Disposition'] = f'attachment; filename="{download_filename}"'

                    # 5. Clean up decrypted file after serving
                    if os.path.exists(decrypted_file_path): os.remove(decrypted_file_path)
                    try:
                        if not os.listdir(temp_decrypted_dir): os.rmdir(temp_decrypted_dir)
                    except OSError: pass
                    return response

                except IOError:
                    print("Error: Could not read decrypted file for download.")
                    # Clean up potentially failed decrypted file before raising Http404
                    if os.path.exists(decrypted_file_path): os.remove(decrypted_file_path)
                    raise Http404("Error preparing file for download.")
            else:
                print("Error: Decryption failed (likely incorrect key or corrupted data).")
                if os.path.exists(decrypted_file_path): os.remove(decrypted_file_path)
                user_files = UserFile.objects.filter(username=username).order_by('-upload_date')
                messages.error(request, 'Decryption failed. Check your file key or the file might be corrupted.')
                return render(request, 'storage/download_list.html', {
                    'username': username,
                    'files': user_files,
                })

        else: # Form not valid
            print("Download form invalid:", form.errors)
             # Re-render download list with form errors if needed, or just redirect
            user_files = UserFile.objects.filter(username=username).order_by('-upload_date')
            # You might want to pass the specific form errors back to the template
            # For simplicity here, just add a general error message
            messages.error(request, 'Invalid download request.')
            return render(request, 'storage/download_list.html', {
                 'username': username,
                 'files': user_files,
            })


    # If GET request
    return redirect('storage:download_list')