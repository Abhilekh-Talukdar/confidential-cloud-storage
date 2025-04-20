import os
from django.conf import settings

# --- Helper Functions (decimal_to_binary, is_repeating_string, extended_gcd) ---
def decimal_to_binary(number):
    # ... (keep the function as provided) [cite: 1]
     return format(number, 'b')


def is_repeating_string(binary_str):
     # ... (keep the function as provided) [cite: 1]
     midpoint = len(binary_str) // 2
     # Handle potential odd length - maybe pad or error? Rabin assumes even length.
     if len(binary_str) % 2 != 0:
          print(f"Warning: Binary string '{binary_str}' has odd length.")
          # Option 1: Pad (might not be correct for Rabin)
          # binary_str = '0' + binary_str
          # midpoint = len(binary_str) // 2
          # Option 2: Return False (safer)
          return False
     # Ensure midpoint is valid even for empty string
     if midpoint == 0 and len(binary_str) == 0: return True # Empty string repeats?
     if midpoint == 0 and len(binary_str) > 0: return False # Single char doesn't repeat half

     return binary_str[:midpoint] == binary_str[midpoint:]


def extended_gcd(a, b):
     # ... (keep the function as provided) [cite: 1, 2]
     if a == 0:
         return (b, 0, 1)
     else:
         gcd_val, x, y = extended_gcd(b % a, a)
         return (gcd_val, y - (b // a) * x, x)

# --- File Combining Function ---
def combine_files(part_paths, output_filepath):
    """Combines file parts back into a single file."""
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    try:
        with open(output_filepath, "wb") as outfile:
            for part_rel_path in part_paths:
                if part_rel_path: # Ensure path is not None
                    part_full_path = os.path.join(settings.MEDIA_ROOT, part_rel_path)
                    if os.path.exists(part_full_path):
                        with open(part_full_path, "rb") as infile:
                            outfile.write(infile.read())
                    else:
                         raise FileNotFoundError(f"Chunk not found: {part_full_path}")
        return True
    except Exception as e:
        print(f"Error combining files: {e}")
        # Clean up incomplete combined file
        if os.path.exists(output_filepath):
             os.remove(output_filepath)
        return False


# --- Main Decryption Function ---
def decrypt_file(encrypted_filepath, decrypted_output_path, p, q):
    """
    Decrypts a file encrypted with Rabin's cryptosystem.

    Args:
        encrypted_filepath (str): Path to the encrypted file.
        decrypted_output_path (str): Path to save the decrypted file.
        p (int): User's key (prime p).
        q (int): Stored key part (prime q).

    Returns:
        bool: True if decryption is successful, False otherwise.
    """
    n = p * q

    # Calculate Bézout coefficients [cite: 3]
    gcd_val, a, b = extended_gcd(p, q) # [cite: 3]
    if gcd_val != 1: # [cite: 3]
        print("Error: Primes p and q must be coprime.") # [cite: 3]
        return False

    os.makedirs(os.path.dirname(decrypted_output_path), exist_ok=True)

    try:
        with open(encrypted_filepath, "r") as cypher_file, open(decrypted_output_path, "wb") as decrypt_file: # Write bytes
            while True:
                cypher_bits = cypher_file.read(32) # [cite: 4]
                if not cypher_bits: # [cite: 4]
                    break # [cite: 4]
                if len(cypher_bits) < 32:
                     print(f"Warning: Trailing non-32-bit chunk ignored: '{cypher_bits}'")
                     break # Ignore incomplete chunk at the end

                c = int(cypher_bits, 2) # [cite: 4]

                # Compute square roots modulo p and q [cite: 4]
                # Ensure p and q are 3 mod 4 for this formula to work easily
                if p % 4 != 3 or q % 4 != 3:
                     print("Error: Decryption requires primes p and q to be congruent to 3 mod 4.")
                     # Need a more general square root algorithm (Tonelli-Shanks) if this is not guaranteed
                     return False

                exponent_p = (p + 1) // 4 # [cite: 4]
                exponent_q = (q + 1) // 4 # [cite: 5]
                r = pow(c, exponent_p, p) # [cite: 5]
                s = pow(c, exponent_q, q) # [cite: 5]

                # Use Chinese Remainder Theorem [cite: 5]
                x = (a * p * s + b * q * r) % n # [cite: 5]
                y = (a * p * s - b * q * r) % n # [cite: 6]
                candidates = [x, y, n - x, n - y] # [cite: 6]

                found = False # [cite: 6]
                for candidate in candidates: # [cite: 6]
                    binary_str = decimal_to_binary(candidate) # [cite: 7]
                    if is_repeating_string(binary_str): # [cite: 7]
                        midpoint = len(binary_str) // 2 # [cite: 7]
                        plain_bits = binary_str[:midpoint] # [cite: 7]
                        try:
                             # Convert bits to int, then to char, then encode back to bytes
                             decrypted_char_code = int(plain_bits, 2) # [cite: 7]
                             decrypted_char = chr(decrypted_char_code) # [cite: 7]
                             decrypt_file.write(decrypted_char.encode('latin-1')) # Write as bytes
                             found = True # [cite: 8]
                             break # [cite: 8]
                        except (ValueError, OverflowError):
                             print(f"Warning: Could not decode bits: {plain_bits}")
                             # Skip this candidate
                        except UnicodeEncodeError:
                            print(f"Warning: Could not encode character with code {decrypted_char_code} to latin-1.")
                            # Write a replacement byte sequence if needed
                            decrypt_file.write(b'?') # Example: write a question mark byte
                            found = True
                            break


                if not found: # [cite: 8]
                    print(f"Warning: No valid repeating pattern found for ciphertext block {c}. Writing replacement.")
                    decrypt_file.write(b'?') # Write a replacement byte [cite: 8]


        print(f"Decryption successful. Decrypted file: {decrypted_output_path}")
        return True

    except FileNotFoundError:
         print(f"Error: Encrypted file not found at {encrypted_filepath}")
         return False
    except Exception as e:
        print(f"Decryption failed: {e}")
        # Clean up incomplete decrypted file
        if os.path.exists(decrypted_output_path):
             os.remove(decrypted_output_path)
        return False