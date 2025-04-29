# Confidential Cloud Storage

A simple Django web application for securely uploading, storing, and downloading text files (`.txt`). The application uses Rabin's cryptosystem for encryption and splits the encrypted files into three parts for storage.

## Features

* **User Association:** Files are associated with a username (currently based on session input).
* **Secure Upload:** Upload `.txt` files via a web interface.
* **Encryption:** Files are encrypted using Rabin's cryptosystem upon upload.
    * Two keys (primes `p` and `q`) are generated.
    * Key `p` is shown to the user as the "File Key" required for download.
    * Key `q` is stored securely in the database alongside file metadata.
* **File Splitting:** Encrypted files are split into three parts before storage.
* **Storage:** File parts are stored locally on the server's filesystem within the `media/chunks/` directory.
* **Secure Download:** Users can view their uploaded files and download a specific file by providing the correct "File Key" (`p`). The application retrieves the parts, combines them, decrypts using the provided key `p` and the stored key `q`, and serves the original `.txt` file.
* **File Deletion:** Users can delete their uploaded files, which removes the database record and the stored file parts.

## Technology Stack and Architectire Overview

* **Backend:** Python, Django
* **Encryption:** Custom implementation of Rabin's Cryptosystem (requires primes `p, q ≡ 3 mod 4`)
* **Web Server (Deployment):** Gunicorn
* **Reverse Proxy (Deployment):** Nginx
* **Database:** SQLite (default, configurable in `settings.py`)
* **Frontend:** HTML, CSS (basic styling)

```mermaid

graph TD
    %% Entities
    User(User)
    Browser(User's Browser)
    DjangoApp(Django Web Application)
    DB[(Database)]
    S3[<img src='https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/Amazon_Web_Services_Logo.svg/32px-Amazon_Web_Services_Logo.svg.png' width='20' /> AWS S3 Bucket]
    GCS[<img src='https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/Google_Cloud_logo.svg/32px-Google_Cloud_logo.svg.png' width='20' /> GCP Cloud Storage Bucket]
    Azure[<img src='https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Microsoft_Azure_Logo.svg/32px-Microsoft_Azure_Logo.svg.png' width='20' /> Azure Blob Storage]

    subgraph User Interaction
        User -- Enters Username/Chooses Action --> Browser
        Browser -- Displays UI --> User
        Browser -- Submits Upload Request (.txt file) --> DjangoApp
        Browser -- Submits Download Request (File ID, Key p) --> DjangoApp
        DjangoApp -- Serves Decrypted .txt File --> Browser
        Browser -- Presents Download --> User
        DjangoApp -- Displays File List/Key p/Errors --> Browser
    end

    subgraph Upload Process
        DjangoApp -- Receives Upload --> EncryptSplit(Encrypt File & Split Parts)
        EncryptSplit -- Generates Keys --> DjangoApp
        EncryptSplit -- Encrypted Part 1 --> StoreS3(Store Part 1 in S3)
        EncryptSplit -- Encrypted Part 2 --> StoreGCS(Store Part 2 in GCS)
        EncryptSplit -- Encrypted Part 3 --> StoreAzure(Store Part 3 in Azure)
        StoreS3 -- S3 URL/ID --> SaveMeta(Save Metadata to DB)
        StoreGCS -- GCS URL/ID --> SaveMeta
        StoreAzure -- Azure URL/ID --> SaveMeta
        DjangoApp -- Key q, Filenames, User, Part URLs/IDs --> SaveMeta
        SaveMeta -- Write Record --> DB
        DjangoApp -- Sends Key p to User --> Browser
    end

    subgraph Download Process
        DjangoApp -- Receives Download Request --> GetMeta(Get Metadata from DB)
        GetMeta -- File ID, Username --> DB
        DB -- Record (Key q, Part URLs/IDs) --> GetMeta
        GetMeta -- Part URLs/IDs --> RetrieveParts(Retrieve Encrypted Parts)
        RetrieveParts -- Request Part 1 --> S3
        RetrieveParts -- Request Part 2 --> GCS
        RetrieveParts -- Request Part 3 --> Azure
        S3 -- Encrypted Part 1 Data --> RetrieveParts
        GCS -- Encrypted Part 2 Data --> RetrieveParts
        Azure -- Encrypted Part 3 Data --> RetrieveParts
        RetrieveParts -- All Encrypted Parts --> CombineDecrypt(Combine Parts & Decrypt File)
        GetMeta -- Key q --> CombineDecrypt
        DjangoApp -- User Key p --> CombineDecrypt
        CombineDecrypt -- Decrypted File Data --> DjangoApp
    end

    %% Style External Storage
    style S3 fill:#f9f9f9,stroke:#232F3E,stroke-width:2px
    style GCS fill:#f9f9f9,stroke:#4285F4,stroke-width:2px
    style Azure fill:#f9f9f9,stroke:#0078D4,stroke-width:2px

```


## Core Logic

1.  **Upload:**
    * User provides username and selects a `.txt` file.
    * Server generates two large prime numbers `p` and `q` (both congruent to 3 mod 4).
    * The file content is encrypted character by character using Rabin's algorithm ($c = m^2 \mod n$, where $n=pq$).
    * The encrypted file is saved.
    * The encrypted file is split into 3 parts.
    * Metadata (username, original filename, encrypted filename, key `q`, part locations) is saved to the database.
    * Key `p` is displayed to the user.
2.  **Download:**
    * User provides username and selects a file to download.
    * User enters their File Key (`p`).
    * Server retrieves file metadata and stored key `q` from the database using the file ID and username.
    * Server retrieves the 3 file parts from their stored locations.
    * The parts are combined into the complete encrypted file.
    * The encrypted file is decrypted using the user's key `p` and the stored key `q` via the Chinese Remainder Theorem and Rabin's square root properties.
    * The original `.txt` file is served to the user.
