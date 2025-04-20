import random
import os
from django.conf import settings # To use MEDIA_ROOT

# --- Helper Functions (generate_primes, decimal_to_binary) ---
def generate_primes(min_prime=1000, max_prime=10000):
    # ... (keep the function as provided) [cite: 9, 10]
    sieve = [True] * (max_prime + 1)
    sieve[0], sieve[1] = False, False
    for current in range(2, int(max_prime ** 0.5) + 1):
        if sieve[current]:
            sieve[current*current : max_prime+1 : current] = [False] * len(sieve[current*current : max_prime+1 : current])
    return [num for num, is_prime in enumerate(sieve) if is_prime and num >= min_prime and num % 4 == 3]

def decimal_to_binary(number):
    # ... (keep the function as provided) [cite: 10]
    return format(number, 'b')

# --- Main Encryption Function ---
def encrypt_file(input_filepath, output_filename_base):
    """
    Encrypts a file using Rabin's cryptosystem.

    Args:
        input_filepath (str): Path to the file to encrypt.
        output_filename_base (str): Base name for the encrypted output file (without extension).

    Returns:
        tuple: (encrypted_file_path, p, q, n) or None if encryption fails.
               p is the key for the user, q is stored, n is the modulus.
    """
    primes = generate_primes()
    if len(primes) < 2:
        print("Error: Not enough suitable primes found.")
        return None, None, None, None

    p, q = random.sample(primes, 2)
    n = p * q # [cite: 11]

    encrypted_file_path = os.path.join(settings.MEDIA_ROOT, 'encrypted', f"{output_filename_base}.enc")
    os.makedirs(os.path.dirname(encrypted_file_path), exist_ok=True)

    try:
        with open(input_filepath, "rb") as plain_file, open(encrypted_file_path, "w") as cypher_file:
            while True:
                byte = plain_file.read(1)
                if not byte:
                    break
                char = byte.decode('latin-1') # Read as bytes, decode carefully
                ascii_val = ord(char) # [cite: 12]
                binary_str = decimal_to_binary(ascii_val) # [cite: 12]
                extended_binary = binary_str + binary_str # [cite: 12]

                m = int(extended_binary, 2) # [cite: 12]
                c = pow(m, 2, n) # [cite: 12] # Modular exponentiation

                cypher_bits = decimal_to_binary(c).zfill(32) # [cite: 13] # Pad to 32 bits
                cypher_file.write(cypher_bits) # [cite: 13]

        print(f"Encryption successful. Encrypted file: {encrypted_file_path}")
        print(f"User Key (p): {p}, Stored Key Part (q): {q}, Modulus (n): {n}")
        return encrypted_file_path, p, q, n

    except Exception as e:
        print(f"Encryption failed: {e}")
        # Clean up incomplete encrypted file if necessary
        if os.path.exists(encrypted_file_path):
            os.remove(encrypted_file_path)
        return None, None, None, None

# --- File Splitting Function ---
def split_file(filepath, num_parts=3):
    """Splits a file into multiple parts."""
    chunk_dir = os.path.join(settings.MEDIA_ROOT, 'chunks', os.path.basename(filepath).replace('.enc', ''))
    os.makedirs(chunk_dir, exist_ok=True)
    part_paths = []
    try:
        filesize = os.path.getsize(filepath)
        chunksize = (filesize + num_parts - 1) // num_parts # Ceiling division

        with open(filepath, "rb") as f:
            for i in range(num_parts):
                chunk = f.read(chunksize)
                if not chunk:
                    break
                part_filename = os.path.join(chunk_dir, f"part_{i+1}")
                with open(part_filename, "wb") as part_file:
                    part_file.write(chunk)
                # Store relative path from MEDIA_ROOT
                relative_path = os.path.relpath(part_filename, settings.MEDIA_ROOT)
                part_paths.append(relative_path)

        # Pad part_paths if fewer parts were created (e.g., small file)
        while len(part_paths) < num_parts:
            part_paths.append(None) # Or handle as needed

        return part_paths[0], part_paths[1], part_paths[2]
    except Exception as e:
        print(f"Error splitting file: {e}")
        # Clean up created chunks if error occurs
        for part_path in part_paths:
             if part_path and os.path.exists(os.path.join(settings.MEDIA_ROOT, part_path)):
                 os.remove(os.path.join(settings.MEDIA_ROOT, part_path))
        if os.path.exists(chunk_dir):
            try:
                os.rmdir(chunk_dir) # Remove dir only if empty
            except OSError:
                pass # Directory might not be empty if cleanup failed partially
        return None, None, None