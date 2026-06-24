
import os
import requests

# --- Configuration ---
WHITEPAPER_PATH = "/home/ubuntu/upload/omega_whitepaper.pdf"
WHITEPAPER_FILENAME = os.path.basename(WHITEPAPER_PATH)

def upload_to_file_io(file_path):
    print(f"Uploading {WHITEPAPER_FILENAME} to file.io...")
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (WHITEPAPER_FILENAME, f, 'application/pdf')}
            response = requests.post('https://file.io/', files=files)
            response.raise_for_status() # Raise an exception for HTTP errors
            data = response.json()
            if data.get('success'):
                print(f"Successfully uploaded to file.io. Download Link: {data['link']}")
                return data['link']
            else:
                print(f"Failed to upload to file.io: {data.get('message', 'Unknown error')}")
                return None
    except requests.exceptions.RequestException as e:
        print(f"Error uploading to file.io: {e}")
        return None

def upload_to_transfer_sh(file_path):
    print(f"Uploading {WHITEPAPER_FILENAME} to transfer.sh...")
    try:
        with open(file_path, 'rb') as f:
            headers = {'Content-Type': 'application/pdf'}
            response = requests.put(f'https://transfer.sh/{WHITEPAPER_FILENAME}', data=f, headers=headers)
            response.raise_for_status() # Raise an exception for HTTP errors
            link = response.text.strip()
            print(f"Successfully uploaded to transfer.sh. Download Link: {link}")
            return link
    except requests.exceptions.RequestException as e:
        print(f"Error uploading to transfer.sh: {e}")
        return None

def main():
    print("Starting no-key whitepaper distribution...")
    
    if not os.path.exists(WHITEPAPER_PATH):
        print(f"Error: Whitepaper not found at {WHITEPAPER_PATH}")
        return

    results = {}

    # Upload to file.io
    file_io_link = upload_to_file_io(WHITEPAPER_PATH)
    if file_io_link: results['file.io'] = file_io_link

    # Upload to transfer.sh
    transfer_sh_link = upload_to_transfer_sh(WHITEPAPER_PATH)
    if transfer_sh_link: results['transfer.sh'] = transfer_sh_link

    print("\n--- Distribution Results (No API Key) ---")
    if results:
        for platform, link in results.items():
            print(f"{platform}: {link}")
        print("\nNote: Links from file.io and transfer.sh are temporary. file.io links expire after one download or 24 hours. transfer.sh links expire after 14 days.")
    else:
        print("No platforms were successfully updated. Please check your internet connection and file path.")

if __name__ == "__main__":
    main()
