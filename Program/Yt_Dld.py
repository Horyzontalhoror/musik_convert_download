import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import json
import os
import threading
import re
import logging
from yt_dlp import YoutubeDL
from datetime import datetime
from UI.style import apply_style, create_custom_widgets

# Konfigurasi Logger
logging.basicConfig(filename='app.log', level=logging.ERROR)

# Path lokal untuk yt-dlp dan ffmpeg
YTDLP_PATH = os.path.join("ffmpeg", "bin", "yt-dlp.exe")
FFMPEG_PATH = os.path.join("ffmpeg", "bin", "ffmpeg.exe")

# Global event untuk pembatalan
cancel_event = threading.Event()

# File pengaturan dan riwayat
config_file = 'config.json'
history_file = 'download_history.json'

# Mapping format
format_mapping = {}

# ===== Fungsi Utilitas =====
def safe_filename(name):
    """Membersihkan nama file dari karakter ilegal."""
    return re.sub(r'[\\/:"*?<>|]+', '', name)

def validate_dependencies():
    """Memvalidasi bahwa semua dependensi (yt-dlp dan ffmpeg) tersedia."""
    if not os.path.isfile(YTDLP_PATH):
        messagebox.showerror("Error", "yt-dlp executable not found. Please install it.")
        return False
    if not is_ffmpeg_installed():
        messagebox.showerror("Error", "FFmpeg executable not found. Please install it.")
        return False
    return True

def is_ffmpeg_installed():
    """Memeriksa apakah ffmpeg tersedia di path yang ditentukan."""
    return os.path.isfile(FFMPEG_PATH)

def load_config():
    """Memuat konfigurasi dari file JSON."""
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    """Menyimpan konfigurasi ke file JSON."""
    with open(config_file, 'w') as f:
        json.dump(config, f)

def add_to_history(video_name):
    """Menambahkan video ke riwayat unduhan."""
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
        except json.JSONDecodeError:
            history = []
    
    # Add new entry
    history.append({
        "name": video_name,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Keep only the last 100 entries
    history = history[-100:]
    
    # Save history
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=4)

def log_error(message):
    """Logging error dan menampilkan pesan error ke pengguna."""
    logging.error(message)
    messagebox.showerror("Error", message)

def create_tooltip(widget, text):
    """Membuat tooltip untuk widget tertentu."""
    tooltip = ttk.Label(widget, text=text, background="lightyellow", relief="solid")
    widget.bind("<Enter>", lambda _: tooltip.place(x=widget.winfo_x(), y=widget.winfo_y() + 20))
    widget.bind("<Leave>", lambda _: tooltip.place_forget())

def fetch_media(url):
    """
    Mengambil informasi format media dari URL menggunakan yt-dlp.
    Mengembalikan daftar format audio, video, dan judul video.
    """
    config = load_config()
    cookie_path = config.get('cookie_path', '')

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,  # Changed to False to get full format info
        'ffmpeg_location': FFMPEG_PATH
    }

    # Tambahkan cookie jika tersedia
    if cookie_path and os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path

    with YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=False)
            if not info_dict:
                raise Exception("Tidak dapat mengambil informasi video")

            formats = info_dict.get('formats', [])
            if not formats:
                raise Exception("Tidak ada format yang tersedia untuk video ini")

            audio_formats = []
            video_formats = []

            # Get best audio format for merging
            best_audio = None
            for f in formats:
                if f and isinstance(f, dict) and f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    if best_audio is None or (f.get('tbr', 0) or 0) > (best_audio.get('tbr', 0) or 0):
                        best_audio = f

            for f in formats:
                if not isinstance(f, dict):
                    continue
                try:
                    format_id = str(f.get('format_id', ''))
                    if not format_id:
                        continue
                    ext = str(f.get('ext', '')).lower()
                    resolution = f.get('height', 0)
                    filesize = float(f.get('filesize', 0))
                    vbr = float(f.get('vbr', 0) or 0)
                    audio_codec = str(f.get('acodec', ''))
                    video_codec = str(f.get('vcodec', ''))
                    fps = int(f.get('fps', 0) or 0)

                    # Format Audio
                    if audio_codec and audio_codec != 'none' and (not video_codec or video_codec == 'none'):
                        size_mb = filesize / (1024 * 1024) if filesize else 0
                        bitrate = float(f.get('abr', 0) or f.get('tbr', 0) or 0)
                        description = f"{format_id} - {ext} Audio ({audio_codec}, {bitrate:.0f}kbps, {size_mb:.1f}MB)"
                        audio_formats.append((format_id, description))

                    # Format Video
                    elif video_codec and video_codec != 'none':
                        size_mb = filesize / (1024 * 1024) if filesize else 0
                        has_audio = audio_codec and audio_codec != 'none'
                        fps_text = f", {fps}fps" if fps else ""
                        audio_text = " + Audio" if has_audio else " (No Audio)"
                        
                        if resolution and resolution > 0:
                            description = f"{format_id} - {resolution}p{fps_text}{audio_text} ({ext}, {video_codec}, {size_mb:.1f}MB)"
                        else:
                            description = f"{format_id} - {ext}{audio_text} ({video_codec}, {size_mb:.1f}MB)"
                        
                        # For formats without audio, we'll merge with best audio
                        if not has_audio and best_audio and best_audio.get('format_id'):
                            format_id = f"{format_id}+{best_audio['format_id']}"
                        video_formats.append((format_id, description))

                except (ValueError, TypeError, AttributeError) as e:
                    log_error(f"Gagal memproses format: {str(e)}")
                    continue

            if not audio_formats and not video_formats:
                raise Exception("Tidak ada format yang dapat diproses")

            # Sort video formats by resolution (highest first)
            video_formats.sort(key=lambda x: int(re.search(r'(\d+)p', x[1]).group(1)) if re.search(r'(\d+)p', x[1]) else 0, reverse=True)
            return audio_formats, video_formats, info_dict.get('title', url)

        except Exception as e:
            log_error(f"Gagal mengambil informasi video: {e}")
            return [], [], ""

def download_video(url, output_dir, selected_format):
    """
    Mengunduh video/audio berdasarkan URL dan format yang dipilih.
    Menampilkan progress bar selama proses unduhan.
    """
    def hook(d):
        if cancel_event.is_set():
            raise Exception("Proses dibatalkan oleh pengguna.")
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                percent = downloaded / total * 100
                progress_var.set(percent)
                root.update_idletasks()
        elif d['status'] == 'finished':
            progress_var.set(0)

    config = load_config()
    cookie_path = config.get('cookie_path', '')

    ydl_opts = {
        'format': selected_format,
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'progress_hooks': [hook],
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_PATH
    }

    # Tambahkan cookie jika tersedia
    if cookie_path and os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path

    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', url)
            add_to_history(safe_filename(title))
        except Exception as e:
            log_error(f"Gagal mengunduh {url}: {e}")

def queue_download(urls, output_dir, selected_format, selected_type):
    """
    Mengunduh beberapa video/audio secara berurutan.
    Mendukung pembatalan proses.
    """
    def download_thread():
        for url in urls:
            if cancel_event.is_set():
                break
            try:
                config = load_config()
                cookie_path = config.get('cookie_path', '')

                ydl_opts = {
                    'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
                    'ffmpeg_location': FFMPEG_PATH,
                    'quiet': True,
                    'no_warnings': True,
                    'progress_hooks': [update_download_progress],
                    'noprogress': False,
                    'updatetime': False,  # Prevent modifying file timestamps
                    'nocheckcertificate': True,  # Skip HTTPS certificate validation
                    'socket_timeout': 30,  # Increase timeout
                }

                # Tambahkan cookie jika tersedia
                if cookie_path and os.path.exists(cookie_path):
                    ydl_opts['cookiefile'] = cookie_path

                # Configure format and post-processing based on selection
                if selected_type == "audio":
                    ydl_opts.update({
                        'format': 'bestaudio/best'})
                else:  # video
                    # Use the exact format ID that was selected
                    ydl_opts['format'] = selected_format

                # Download with configured options
                with YoutubeDL(ydl_opts) as ydl:
                    try:
                        # Reset progress display
                        progress_var.set(0)
                        progress_text.set("Starting download...")
                        root.update_idletasks()
                        
                        # Start download
                        info = ydl.extract_info(url, download=True)
                        if info:
                            title = info.get('title', url)
                            add_to_history(safe_filename(title))
                            
                    except Exception as e:
                        error_msg = str(e)
                        if "ERROR:" in error_msg:
                            error_msg = error_msg.split("ERROR:", 1)[1].strip()
                        log_error(f"Error downloading {url}: {error_msg}")
                        messagebox.showerror("Error", f"Gagal mengunduh: {error_msg}")
                        continue

            except Exception as e:
                error_msg = str(e)
                log_error(f"Error in download thread: {error_msg}")
                messagebox.showerror("Error", f"Gagal mengunduh: {error_msg}")
                continue

        progress_var.set(0)
        progress_text.set("Ready")
        start_button.config(state='normal')
        cancel_button.config(state='disabled')

    cancel_event.clear()
    threading.Thread(target=download_thread, daemon=True).start()

def cancel_process():
    """Membatalkan proses unduhan/konversi."""
    cancel_event.set()
    progress_var.set(0)
    cancel_button.config(state='disabled')
    start_button.config(state='normal')
    messagebox.showinfo("Batal", "Proses sedang dibatalkan.")

def show_history():
    """Menampilkan riwayat pengunduhan."""
    if not os.path.exists(history_file):
        messagebox.showinfo("History", "No download history yet.")
        return
    
    try:
        with open(history_file, 'r') as f:
            history = json.load(f)
            
        if not history:
            messagebox.showinfo("History", "No download history yet.")
            return
            
        # Format history entries
        history_str = "\n".join([
            f"{item.get('name', 'Unknown')} - {item.get('date', 'Unknown date')}"
            for item in history
        ])
        
        # Show history in a message box
        messagebox.showinfo("Download History", history_str)
        
    except Exception as e:
        messagebox.showerror("Error", f"Could not load history: {str(e)}")

def convert_file(input_path, output_path, format_type, codec, quality='medium'):
    """
    Mengkonversi file media menggunakan FFmpeg.
    Mendukung konversi video/audio dengan kualitas yang dapat diatur.
    """
    try:
        # Video quality presets
        quality_presets = {
            'highest': {
                'mp4': ['-c:v', 'libx264', '-preset', 'slow', '-crf', '18'],
                'webm': ['-c:v', 'libvpx-vp9', '-crf', '24', '-b:v', '0'],
                'mkv': ['-c:v', 'libx264', '-preset', 'slow', '-crf', '18'],
                'avi': ['-c:v', 'libx264', '-preset', 'slow', '-crf', '18']
            },
            'high': {
                'mp4': ['-c:v', 'libx264', '-preset', 'medium', '-crf', '20'],
                'webm': ['-c:v', 'libvpx-vp9', '-crf', '27', '-b:v', '0'],
                'mkv': ['-c:v', 'libx264', '-preset', 'medium', '-crf', '20'],
                'avi': ['-c:v', 'libx264', '-preset', 'medium', '-crf', '20']
            },
            'medium': {
                'mp4': ['-c:v', 'libx264', '-preset', 'medium', '-crf', '23'],
                'webm': ['-c:v', 'libvpx-vp9', '-crf', '30', '-b:v', '0'],
                'mkv': ['-c:v', 'libx264', '-preset', 'medium', '-crf', '23'],
                'avi': ['-c:v', 'libx264', '-preset', 'medium', '-crf', '23']
            },
            'low': {
                'mp4': ['-c:v', 'libx264', '-preset', 'fast', '-crf', '28'],
                'webm': ['-c:v', 'libvpx-vp9', '-crf', '35', '-b:v', '0'],
                'mkv': ['-c:v', 'libx264', '-preset', 'fast', '-crf', '28'],
                'avi': ['-c:v', 'libx264', '-preset', 'fast', '-crf', '28']
            }
        }

        # Audio codec parameters
        audio_codec_params = {
            'mp3': ['-acodec', 'libmp3lame', '-q:a', '2'],
            'ogg': ['-acodec', 'libvorbis', '-q:a', '4'],
            'opus': ['-acodec', 'libopus', '-b:a', '128k'],
            'wav': ['-acodec', 'pcm_s16le']
        }

        # Build FFmpeg command
        command = [
            FFMPEG_PATH,
            '-i', input_path,
            '-y'  # Overwrite output file
        ]

        if format_type == "audio":
            command.append('-vn')  # No video for audio conversion
            if codec.lower() in audio_codec_params:
                command.extend(audio_codec_params[codec.lower()])
        else:  # video
            # Keep audio and convert it to AAC for compatibility
            command.extend(['-c:a', 'aac', '-b:a', '192k'])
            # Apply video quality settings
            if codec.lower() in quality_presets[quality]:
                command.extend(quality_presets[quality][codec.lower()])

        # Add output path
        command.append(output_path)

        # Run FFmpeg with progress monitoring
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        # Wait for completion
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {stderr}")
    except Exception as e:
        log_error(f"Konversi gagal: {str(e)}")
        raise

def pick_and_convert():
    """
    Memilih file untuk dikonversi dan memulai proses konversi.
    """
    # Get conversion type
    format_type = format_var.get()  # "audio" or "video"

    # Set file types based on conversion type
    if format_type == "audio":
        filetypes = [
            ("Media files", "*.mp3;*.mp4;*.webm;*.m4a;*.wav;*.ogg;*.opus;*.mkv;*.avi"),
            ("All files", "*.*")
        ]
    else:  # video
        filetypes = [
            ("Video files", "*.mp4;*.webm;*.mkv;*.avi;*.mov;*.flv;*.m4v;*.ts;*.mpg;*.mpeg"),
            ("All files", "*.*")
        ]

    input_path = filedialog.askopenfilename(
        title="Pilih file media untuk dikonversi",
        filetypes=filetypes
    )

    if not input_path:
        return

    # Get output format based on conversion type
    codec = codec_var.get()
    if not codec:
        messagebox.showwarning("Format Error", "Harap pilih format output terlebih dahulu.")
        return

    output_dir = folder_entry.get()
    if not output_dir:
        messagebox.showwarning("Folder kosong", "Pilih folder penyimpanan terlebih dahulu.")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Generate output filename
    ext = codec.lower()
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.{ext}")

    def conversion():
        try:
            progress_var.set(0)
            convert_button.config(state='disabled')

            # Get quality setting for video
            quality = quality_var.get() if format_type == "video" else "medium"
            convert_file(input_path, output_path, format_type, codec.lower(), quality)
            progress_var.set(100)
            messagebox.showinfo("Sukses", f"File berhasil dikonversi ke {codec.upper()}!")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal mengkonversi file: {str(e)}")
        finally:
            convert_button.config(state='normal')
            progress_var.set(0)

    threading.Thread(target=conversion).start()

# UI Updates for video conversion
def update_ui_visibility(*args):
    """Menyesuaikan visibilitas elemen UI berdasarkan tipe format."""
    format_type = format_var.get()
    if format_type == "video":
        quality_frame.grid()
    else:
        quality_frame.grid_remove()

def update_codec_menu(*args):
    """Memperbarui menu codec berdasarkan tipe format."""
    format_type = format_var.get()
    if format_type == "audio":
        codec_menu['values'] = ["mp3", "ogg", "opus", "wav"]
        codec_var.set("mp3")
    else:  # video
        codec_menu['values'] = ["mp4", "webm", "mkv", "avi"]
        codec_var.set("mp4")
    update_ui_visibility()

def fetch_and_select_format():
    """
    Mengambil format media dari URL dan memperbarui pilihan format di UI.
    """
    url = url_text.get("1.0", tk.END).strip().split('\n')[0]
    if not url:
        messagebox.showwarning("Input Error", "Harap masukkan URL video terlebih dahulu.")
        return

    audio_formats, video_formats, video_title = fetch_media(url)
    if video_title:
        # Store format IDs and descriptions
        global format_mapping
        format_mapping = {}
        
        if format_var.get() == "video":
            format_descriptions = []
            for format_id, desc in video_formats:
                format_mapping[desc] = format_id
                format_descriptions.append(desc)
            format_choice_menu['values'] = format_descriptions
        else:  # audio
            format_descriptions = []
            for format_id, desc in audio_formats:
                format_mapping[desc] = format_id
                format_descriptions.append(desc)
            format_choice_menu['values'] = format_descriptions
        
        format_choice_var.set('')  # Clear selection first
        if format_choice_menu['values']:
            format_choice_menu.current(0)  # Set default to first format
        messagebox.showinfo("Pilih Format", f"Format berhasil diperbarui untuk video: {video_title}")
    else:
        messagebox.showerror("Error", "Tidak dapat mengambil format dari video tersebut.")

def update_format_choices(*args):
    """Meriset pilihan format saat tipe format berubah."""
    format_choice_var.set('')
    format_choice_menu['values'] = []
    # Trigger fetch format if there's a URL
    if url_text.get("1.0", tk.END).strip():
        fetch_and_select_format()

# ===== Fungsi Utilitas Tambahan =====
def format_size(bytes):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KiB', 'MiB', 'GiB']:
        if bytes < 1024:
            return f"{bytes:.1f}{unit}"
        bytes /= 1024
    return f"{bytes:.1f}GiB"

def format_speed(bytes_per_sec):
    """Convert bytes/sec to human readable format"""
    return f"{format_size(bytes_per_sec)}/s"

def format_eta(seconds):
    """Convert seconds to HH:MM:SS format"""
    if seconds is None:
        return "--:--"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

def update_download_progress(d):
    """Update progress bar with detailed information"""
    try:
        if d['status'] == 'downloading':
            # Get download stats
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            speed = d.get('speed', 0)
            if speed is None:
                speed = 0
            
            # Calculate progress
            if total > 0:
                percent = (downloaded / total) * 100
                progress_var.set(percent)
                
                # Format progress text with fallback for unknown values
                speed_text = format_speed(speed) if speed > 0 else "Unknown"
                eta_text = format_eta(d.get('eta', None)) if d.get('eta') is not None else "Unknown"
                
                progress_text.set(
                    f"[download] {percent:.1f}% of {format_size(total)} "
                    f"at {speed_text}/s ETA {eta_text}"
                )
            else:
                # If total size unknown, show downloaded size and speed
                speed_text = format_speed(speed) if speed > 0 else "Unknown"
                progress_text.set(
                    f"[download] {format_size(downloaded)} "
                    f"at {speed_text}/s"
                )
            
            # Update UI
            root.update_idletasks()
            
        elif d['status'] == 'finished':
            progress_var.set(100)
            progress_text.set("Download completed")
            root.update_idletasks()
            
    except Exception as e:
        log_error(f"Error updating progress: {str(e)}")

# ===== UI =====
# Functions for UI interactions
def browse_cookie():
    """Browse and set cookie file path"""
    filename = filedialog.askopenfilename(
        title="Select Cookie File",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    if filename:
        cookie_path_var.set(filename)
        config = load_config()
        config['cookie_path'] = filename
        save_config(config)

# Membuat root window untuk aplikasi
root = tk.Tk()
root.title("YouTube Downloader")
root.geometry("510x545")
root.resizable(True, True)
root.configure(bg="#ffffff")

# Apply modern style
apply_style()
custom_widgets = create_custom_widgets()
ModernButton = custom_widgets["ModernButton"]

# Create variables
format_var = tk.StringVar(value="video")  # Default to video
format_choice_var = tk.StringVar()
codec_var = tk.StringVar(value="mp4")
quality_var = tk.StringVar(value="medium")
progress_var = tk.DoubleVar()
progress_text = tk.StringVar(value="Ready")

# Main frame with padding
main_frame = ttk.Frame(root, style="Modern.TFrame", padding="20")
main_frame.grid(row=0, column=0, sticky="nsew")
root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(0, weight=1)

# URL Input
url_frame = ttk.LabelFrame(main_frame, text="Video URL", style="Modern.TLabelframe", padding="10")
url_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
url_text = tk.Text(url_frame, height=3, width=50, font=("Segoe UI", 9))
url_text.pack(fill="x", expand=True)
create_tooltip(url_text, "Enter YouTube video URL(s). One URL per line.")

# Folder Selection
folder_frame = ttk.LabelFrame(main_frame, text="Output Location", style="Modern.TLabelframe", padding="10")
folder_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))
folder_entry = ttk.Entry(folder_frame, style="Modern.TEntry")
folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
folder_button = ModernButton(folder_frame, text="Browse", 
                           command=lambda: folder_entry.insert(0, filedialog.askdirectory()))
folder_button.pack(side="right")
create_tooltip(folder_frame, "Select where downloaded files will be saved")

# Format Selection
format_frame = ttk.LabelFrame(main_frame, text="Download Options", style="Modern.TLabelframe", padding="10")
format_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))

# Format type radio buttons
type_frame = ttk.Frame(format_frame, style="Modern.TFrame")
type_frame.pack(fill="x", pady=(0, 10))
ttk.Radiobutton(type_frame, text="Video", value="video", variable=format_var, 
                style="Modern.TRadiobutton").pack(side="left", padx=10)
ttk.Radiobutton(type_frame, text="Audio Only", value="audio", variable=format_var, 
                style="Modern.TRadiobutton").pack(side="left", padx=10)
create_tooltip(type_frame, "Choose to download video with audio or audio only")

# Format choice
format_choice_frame = ttk.Frame(format_frame, style="Modern.TFrame")
format_choice_frame.pack(fill="x")
ttk.Label(format_choice_frame, text="Format:", 
         style="Modern.TLabel").pack(side="left", padx=(0, 5))
format_choice_menu = ttk.Combobox(format_choice_frame, 
                                textvariable=format_choice_var, 
                                state="readonly", 
                                style="Modern.TCombobox")
format_choice_menu.pack(side="left", fill="x", expand=True)
create_tooltip(format_choice_menu, "Select quality and format. Click 'Fetch Format' first to load available options.")

# Cookie settings
cookie_frame = ttk.LabelFrame(main_frame, text="Cookie Settings", style="Modern.TLabelframe", padding="10")
cookie_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 10))
cookie_path_var = tk.StringVar(value=load_config().get('cookie_path', ''))
cookie_entry = ttk.Entry(cookie_frame, textvariable=cookie_path_var, style="Modern.TEntry")
cookie_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
cookie_browse = ModernButton(cookie_frame, text="Browse", command=browse_cookie)
cookie_browse.pack(side="right")
create_tooltip(cookie_frame, "Optional: Select cookie file for age-restricted or private videos")

# Buttons frame
button_frame = ttk.Frame(main_frame, style="Modern.TFrame")
button_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 10))

fetch_button = ModernButton(button_frame, text="Fetch Format", 
                          command=lambda: fetch_and_select_format())
fetch_button.pack(side="left", padx=5)
create_tooltip(fetch_button, "Get available formats for the entered URL")

start_button = ModernButton(button_frame, text="Start Download", 
                          command=lambda: start_process())
start_button.pack(side="left", padx=5)
create_tooltip(start_button, "Begin downloading with selected options")

cancel_button = ModernButton(button_frame, text="Cancel", 
                           command=cancel_process, state="disabled")
cancel_button.pack(side="left", padx=5)
create_tooltip(cancel_button, "Cancel current download")

history_button = ModernButton(button_frame, text="History", 
                            command=show_history)
history_button.pack(side="right", padx=5)
create_tooltip(history_button, "View download history")

# Progress frame
progress_frame = ttk.LabelFrame(main_frame, text="Download Progress", 
                              style="Modern.TLabelframe", padding="10")
progress_frame.grid(row=5, column=0, columnspan=3, sticky="ew")

progress_label = ttk.Label(progress_frame, textvariable=progress_text, 
                         style="Modern.TLabel")
progress_label.pack(fill="x", pady=(0, 5))

progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, 
                             maximum=100, style="Modern.Horizontal.TProgressbar")
progress_bar.pack(fill="x")
# Validasi Dependency
if not validate_dependencies():
    root.destroy()

def start_process():
    """
    Memulai proses unduhan atau konversi berdasarkan input pengguna.
    """
    urls = url_text.get("1.0", tk.END).strip().splitlines()
    output_dir = folder_entry.get()

    if not urls:
        messagebox.showwarning("Input Error", "Harap masukkan URL video.")
        return

    if not output_dir:
        messagebox.showwarning("Input Error", "Harap pilih folder output.")
        return

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Get selected format type and format
    selected_type = format_var.get()
    selected_format_desc = format_choice_var.get()
    
    if not selected_format_desc:
        messagebox.showwarning("Error", "Harap pilih format unduhan.")
        return
    
    # Get the actual format ID from the mapping
    selected_format = format_mapping.get(selected_format_desc)
    if not selected_format:
        messagebox.showerror("Error", "Format yang dipilih tidak valid.")
        return

    cancel_event.clear()
    start_button.config(state='disabled')
    cancel_button.config(state='normal')

    # Pass both selected_format and selected_type to queue_download
    queue_download(urls, output_dir, selected_format, selected_type)

root.mainloop()