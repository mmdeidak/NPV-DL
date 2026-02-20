import os
import json
import time
import subprocess
from telethon import TelegramClient, events, sync
from telethon.sessions import StringSession

api_id = int(os.environ["API_ID"])
api_hash = os.environ["API_HASH"]
session_string = os.environ["SESSION_STRING"]
channel_username = 'mitivpn'
download_path = './downloads'
data_file = './data.json'
EXTENSIONS = ('.npv', '.npvt')

MAX_DIR_SIZE_MB = 3
MAX_SITE_DISPLAY = 35
CHECK_LIMIT = 100

if not os.path.exists(download_path):
    os.makedirs(download_path)

file_dates = {}

def load_existing_dates():
    global file_dates
    if os.path.exists(data_file):
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                for item in old_data:
                    file_dates[item['name']] = item['timestamp']
        except:
            pass

def get_dir_size_mb(path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024)

def enforce_storage_limit():
    current_size = get_dir_size_mb(download_path)
    
    if current_size <= MAX_DIR_SIZE_MB:
        return

    files = []
    for filename in os.listdir(download_path):
        file_path = os.path.join(download_path, filename)
        if os.path.isfile(file_path):
            ts = file_dates.get(filename, get_file_time(file_path))
            size = os.path.getsize(file_path)
            files.append({'path': file_path, 'name': filename, 'ts': ts, 'size': size})

    files.sort(key=lambda x: x['ts'])

    for f in files:
        if current_size <= MAX_DIR_SIZE_MB:
            break 
        
        try:
            os.remove(f['path'])
            current_size -= (f['size'] / (1024 * 1024))
            print(f"🗑️ Storage Cleanup -> Deleted: {f['name']}")
        except Exception as e:
            print(f"Error deleting {f['name']}: {e}")
            
def get_file_time(file_path):
    try:
        time_str = subprocess.check_output(
            ['git', 'log', '-1', '--format=%ct', '--', file_path]
        ).decode('utf-8').strip()
        
        if time_str:
            return int(time_str)
    except Exception:
        pass
    
    return int(os.path.getmtime(file_path))
    
def update_json():
    files_data = []
    if os.path.exists(download_path):
        for filename in os.listdir(download_path):
            if filename.endswith(EXTENSIONS):
                file_path = os.path.join(download_path, filename)
                timestamp = file_dates.get(filename, get_file_time(file_path))
                
                files_data.append({
                    "name": filename,
                    "url": f"downloads/{filename}",
                    "timestamp": timestamp
                })
    
    files_data.sort(key=lambda x: x['timestamp'], reverse=True)

    final_list = files_data[:MAX_SITE_DISPLAY]

    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, ensure_ascii=False, indent=4)
    print(f"📝 data.json updated! (Top {len(final_list)} files)")

with TelegramClient(StringSession(session_string), api_id, api_hash) as client:
    print("🚀 Bot Started...")
    load_existing_dates()

    try:
        print(f"🔍 Checking last {CHECK_LIMIT} messages...")
        messages = client.get_messages(channel_username, limit=CHECK_LIMIT)
        
        for msg in messages:
            if msg.file and msg.file.name:
                if msg.file.name.endswith(EXTENSIONS):
                    
                    msg_timestamp = msg.date.timestamp()
                    file_dates[msg.file.name] = msg_timestamp

                    f_path = os.path.join(download_path, msg.file.name)
                    if not os.path.exists(f_path):
                        print(f"⬇️ Downloading: {msg.file.name}")
                        msg.download_media(file=download_path)
                    else:
                        print(f"♻️ Exists: {msg.file.name}")

        enforce_storage_limit()

    except Exception as e:
        print(f"⚠️ Error: {e}")

    update_json()
    print("🏁 Done.")
