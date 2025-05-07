import os
import json
import threading
import re
from datetime import datetime
from yt_dlp import YoutubeDL
from tkinter import messagebox
from Program.Utils import (
    safe_filename, load_config, save_config, add_to_history, 
    format_size, format_speed, format_eta, log_error
)

# Path lokal untuk yt-dlp dan ffmpeg
YTDLP_PATH = os.path.join("ffmpeg", "bin", "yt-dlp.exe")
FFMPEG_PATH = os.path.join("ffmpeg", "bin", "ffmpeg.exe")

# Global event untuk pembatalan
cancel_event = threading.Event()

# File pengaturan dan riwayat
config_file = 'config.json'
history_file = 'download_history.json'

def validate_dependencies():
    """
    Memvalidasi bahwa semua dependensi (yt-dlp dan ffmpeg) tersedia.
    Menampilkan pesan error jika dependensi tidak ditemukan.
    """
    try:
        if not os.path.isfile(YTDLP_PATH):
            error_msg = "yt-dlp executable not found. Please install it."
            log_error(error_msg)
            messagebox.showerror("Error", error_msg)
            return False
        if not is_ffmpeg_installed():
            error_msg = "FFmpeg executable not found. Please install it."
            log_error(error_msg)
            messagebox.showerror("Error", error_msg)
            return False
        return True
    except Exception as e:
        log_error(f"Error validating dependencies: {str(e)}")
        messagebox.showerror("Error", f"Error validating dependencies: {str(e)}")
        return False

def is_ffmpeg_installed():
    """
    Memeriksa apakah ffmpeg tersedia di path yang ditentukan.
    """
    return os.path.isfile(FFMPEG_PATH)

def fetch_media(url):
    """
    Fetch available formats for the given URL.
    Returns tuple of (audio_formats, video_formats, title).
    Each format is a tuple of (format_id, description).
    """
    try:
        # Create yt-dlp options
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True
        }

        # Get video info
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        if not info:
            return [], [], None
            
        # Get video title
        title = info.get('title', '')
        
        # Get available formats
        formats = info.get('formats', [])
        
        # Sort formats by quality
        video_formats = []
        audio_formats = []
        
        for f in formats:
            format_id = f.get('format_id', '')
            
            # Skip formats without necessary info
            if not format_id:
                continue
                
            # Get format details
            ext = f.get('ext', '')
            filesize = f.get('filesize', 0)
            
            # Video format
            if f.get('vcodec', 'none') != 'none':
                height = f.get('height', 0)
                fps = f.get('fps', 0)
                vcodec = f.get('vcodec', '').split('.')[0]
                
                # Create format description
                desc = []
                if height > 0:
                    desc.append(f"{height}p")
                if fps > 0:
                    desc.append(f"{fps}fps")
                desc.append(ext)
                if vcodec:
                    desc.append(vcodec)
                if filesize > 0:
                    desc.append(f"{filesize/1024/1024:.1f}MB")
                    
                video_formats.append((format_id, " ".join(desc)))
                
            # Audio format
            elif f.get('acodec', 'none') != 'none':
                abr = f.get('abr', 0)
                acodec = f.get('acodec', '').split('.')[0]
                
                # Create format description
                desc = []
                if abr > 0:
                    desc.append(f"{abr}kbps")
                desc.append(ext)
                if acodec:
                    desc.append(acodec)
                if filesize > 0:
                    desc.append(f"{filesize/1024/1024:.1f}MB")
                    
                audio_formats.append((format_id, " ".join(desc)))
                
        # Sort by quality (assuming higher format_id = better quality)
        video_formats.sort(key=lambda x: x[0], reverse=True)
        audio_formats.sort(key=lambda x: x[0], reverse=True)
        
        return audio_formats, video_formats, title
        
    except Exception as e:
        log_error(f"Error fetching formats: {str(e)}")
        return [], [], None

def _progress_hook(d, callback=None):
    """Handle download progress updates."""
    if not callback:
        return
        
    try:
        status = d.get('status', '')
        
        if status == 'downloading':
            # Calculate progress
            total = d.get('total_bytes', 0)
            downloaded = d.get('downloaded_bytes', 0)
            
            if total > 0:
                progress = (downloaded / total) * 100
            else:
                progress = 0
                
            # Get speed and ETA
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)
            
            # Format values
            speed_str = format_speed(speed) if speed else 'Unknown'
            eta_str = format_eta(eta) if eta else 'Unknown'
            size_str = format_size(total) if total else ''
            
            # Send progress update
            callback({
                'status': 'downloading',
                'progress': progress,
                'speed': speed_str,
                'eta': eta_str,
                'size': size_str,
                'format': d.get('info_dict', {}).get('format', '')
            })
            
        elif status == 'finished':
            callback({
                'status': 'complete'
            })
            
    except Exception as e:
        log_error(f"Progress hook error: {str(e)}")
        callback({
            'status': 'error',
            'error': str(e)
        })

def queue_download(urls, output_dir, selected_format, selected_type, progress_callback=None):
    """Queue downloads for the given URLs."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract format ID from the selected format string
        # Format string looks like "720p mp4 [f299]"
        format_id = selected_format.split('[')[-1].strip(']')
        
        # Create yt-dlp options
        ydl_opts = {
            'format': format_id,
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: _progress_hook(d, progress_callback)],
            'quiet': True,
            'no_warnings': True
        }
        
        # Start download
        with YoutubeDL(ydl_opts) as ydl:
            for url in urls:
                try:
                    # Get video info first
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        continue
                        
                    # Update progress with video title
                    if progress_callback:
                        progress_callback({
                            'status': 'start',
                            'title': info.get('title', 'Unknown'),
                            'url': url
                        })
                    
                    # Download video
                    ydl.download([url])
                    
                    # Add to history
                    add_to_history(info.get('title', 'Unknown'))
                    
                except Exception as e:
                    log_error(f"Error downloading {url}: {str(e)}")
                    if progress_callback:
                        progress_callback({
                            'status': 'error',
                            'error': str(e),
                            'url': url
                        })
                    continue
            
        # Signal completion
        if progress_callback:
            progress_callback({'status': 'complete'})
            
        return True
        
    except Exception as e:
        log_error(f"Download error: {str(e)}")
        if progress_callback:
            progress_callback({
                'status': 'error',
                'error': str(e)
            })
        return False

def cancel_process():
    """Membatalkan proses unduhan."""
    cancel_event.set()

def show_history():
    """Menampilkan riwayat pengunduhan."""
    try:
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history = json.load(f)
                if not history:
                    return "Belum ada riwayat unduhan."
                
                result = "Riwayat Unduhan:\n\n"
                for entry in reversed(history):
                    result += f"{entry['name']} - {entry['date']}\n"
                return result
        return "Belum ada riwayat unduhan."
    except Exception as e:
        error_msg = f"Error showing history: {str(e)}"
        log_error(error_msg)
        return error_msg