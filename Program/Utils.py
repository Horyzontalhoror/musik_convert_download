import os
import json
import re
from datetime import datetime

# File pengaturan dan riwayat
config_file = 'config.json'
history_file = 'download_history.json'

def safe_filename(name):
    """
    Membersihkan nama file dari karakter ilegal.
    Contoh: Menghapus karakter seperti / \ : * ? " < > |
    """
    return re.sub(r'[\\/:"*?<>|]+', '', name)

def load_config():
    """
    Memuat konfigurasi dari file JSON.
    Jika file tidak ada, mengembalikan dictionary kosong.
    """
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # Handle corrupted or unreadable config file
            return {}
    return {}

def save_config(config):
    """
    Menyimpan konfigurasi ke file JSON.
    """
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
    except IOError:
        print("Gagal menyimpan konfigurasi.")

def add_to_history(video_name):
    """
    Menambahkan video ke riwayat unduhan.
    Membatasi riwayat hingga 100 entri terakhir.
    """
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                data = json.load(f)
                # Ensure history is a list
                history = data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError):
            # Handle corrupted or unreadable history file
            history = []
    
    # Add new entry
    history.append({
        "name": video_name,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Keep only the last 100 entries
    history = history[-100:]
    
    # Save updated history
    try:
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=4)
    except IOError:
        print("Gagal menyimpan riwayat unduhan.")

def format_size(bytes):
    """
    Mengonversi ukuran byte ke format yang lebih mudah dibaca.
    Contoh: 1024 -> 1.0KiB, 1048576 -> 1.0MiB
    """
    if not isinstance(bytes, (int, float)) or bytes < 0:
        return "0B"
        
    try:
        bytes = float(bytes)
        for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
            if bytes < 1024.0:
                return f"{bytes:.1f}{unit}"
            bytes /= 1024.0
        return f"{bytes:.1f}TiB"
    except (ValueError, TypeError):
        return "0B"

def format_speed(bytes_per_sec):
    """
    Mengonversi kecepatan unduhan ke format yang lebih mudah dibaca.
    Contoh: 1024 -> 1.0KiB/s
    """
    if not isinstance(bytes_per_sec, (int, float)) or bytes_per_sec < 0:
        return "0B/s"
        
    try:
        speed = format_size(float(bytes_per_sec))
        return f"{speed}/s" if speed != "0B" else "0B/s"
    except (ValueError, TypeError):
        return "0B/s"

def format_eta(seconds):
    """
    Mengonversi waktu tersisa (ETA) ke format HH:MM:SS.
    """
    if seconds is None or not isinstance(seconds, (int, float)):
        return "--:--"
        
    try:
        # Convert to int
        seconds = int(seconds)
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
            
    except (ValueError, TypeError):
        return "--:--"

def log_error(message):
    """
    Logging error dan menampilkan pesan error ke pengguna.
    """
    try:
        with open('app.log', 'a') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] ERROR: {message}\n")
    except Exception as e:
        print(f"Failed to log error: {str(e)}")
        print(f"Original error: {message}")