from flask import Flask, request, render_template, send_file, jsonify
import os
from cryptography.fernet import Fernet
from datetime import datetime

app = Flask(__name__)

# Folder paths
UPLOAD_FOLDER = 'server_files'
TEMP_FOLDER = 'temp'
LOG_FILE = 'download_log.txt'
KEY_FILE = 'key.key'

# Ensure necessary folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Load or generate the encryption key
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, 'rb') as key_file:
        key = key_file.read()
else:
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as key_file:
        key_file.write(key)

cipher = Fernet(key)

@app.route('/')
def index():
    """Render the main page with options: Upload, Download, and View Log."""
    return render_template('index.html')

@app.route('/upload-page')
def upload_page():
    """Render the upload page."""
    return render_template('upload_page.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload, encrypt it, and save to the server."""
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    # Read file and encrypt it
    file_data = file.read()
    encrypted_data = cipher.encrypt(file_data)

    # Save the encrypted file
    encrypted_file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(encrypted_file_path, 'wb') as f:
        f.write(encrypted_data)

    # Redirect to success page
    return render_template('upload_success.html', filename=file.filename)

@app.route('/download-page')
def download_page():
    """Render the download page."""
    return render_template('download_page.html')

@app.route('/files', methods=['GET'])
def list_files():
    """Return a list of available files for download."""
    files = []
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            files.append({"name": filename, "size": os.path.getsize(file_path)})
    return jsonify(files)


@app.route('/download/<filename>')
def download_file(filename):
    """Decrypt and allow the user to download a file."""
    encrypted_file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(encrypted_file_path):
        return "File not found", 404

    decrypted_file_path = os.path.join(TEMP_FOLDER, filename)
    with open(encrypted_file_path, 'rb') as f:
        encrypted_data = f.read()
    with open(decrypted_file_path, 'wb') as f:
        f.write(cipher.decrypt(encrypted_data))

    # Log the download (exclude microseconds)
    with open(LOG_FILE, 'a') as log:
        log.write(f"{filename}\t{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Send the decrypted file for download
    response = send_file(decrypted_file_path, as_attachment=True)
    
    # Optionally delete the temporary file after sending it
    os.remove(decrypted_file_path)
    
    return response



@app.route('/view-log-page')
def view_log_page():
    """Render the view log page."""
    return render_template('view_log_page.html')

@app.route('/download-log', methods=['GET'])
def download_log():
    """Provide the download log entries in JSON format."""
    if not os.path.exists(LOG_FILE):
        return jsonify([])  # Return empty list if no log file exists

    logs = []
    with open(LOG_FILE, 'r') as log:
        for line in log:
            parts = line.strip().split(' downloaded on ')
            if len(parts) == 2:
                filename, timestamp = parts
                logs.append({"filename": filename, "timestamp": timestamp})

    return jsonify(logs)


@app.route('/download-success/<filename>', methods=['POST'])
def download_success(filename):
    """Log the download and show a success message."""
    with open(LOG_FILE, 'a') as log:
        log.write(f"{filename} downloaded on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    return jsonify({"message": "Download logged successfully"}), 200


if __name__ == '__main__':
    app.run(debug=True)
