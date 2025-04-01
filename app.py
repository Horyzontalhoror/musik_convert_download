import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import yt_dlp
from tkinter import ttk  # Import ttk for Progressbar

# Deteksi OS dan atur path FFmpeg
FFMPEG_PATH = os.path.join(os.path.dirname(__file__), "ffmpeg", "bin", "ffmpeg")
if os.name == "nt":  # Windows
    FFMPEG_PATH += ".exe"

# Global variable to store the cookies file path
cookies_file = ""

def select_file():
    file_path = filedialog.askopenfilename(filetypes=[("Media Files", "*.mp4;*.ts"), ("All Files", "*.*")])
    if file_path:
        entry_var.set(file_path)

def convert_to_format():
    input_file = entry_var.get()
    selected_format = format_var.get()  # Ambil format yang dipilih dari dropdown

    if not input_file:
        messagebox.showerror("Error", "Pilih file terlebih dahulu!")
        return

    # Tentukan nama file output berdasarkan format yang dipilih
    output_file = os.path.splitext(input_file)[0] + f".{selected_format}"

    if os.path.exists(output_file):
        if not messagebox.askyesno("File Exists", f"File {output_file} sudah ada. Apakah Anda ingin menimpanya?"):
            return

    if not os.path.exists(FFMPEG_PATH):
        messagebox.showerror("Error", f"FFmpeg tidak ditemukan di {FFMPEG_PATH}! Pastikan file FFmpeg ada di folder 'ffmpeg/bin/'.")
        return

    try:
        progress_var.set(0)  # Reset progress bar
        root.update_idletasks()

        # Tentukan codec audio dan video berdasarkan format
        if selected_format == "mp3":
            codec_options = ["-acodec", "libmp3lame", "-q:a", "2"]
        elif selected_format == "wav":
            codec_options = ["-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2"]
        elif selected_format == "webm":
            codec_options = ["-c:v", "libvpx", "-c:a", "libvorbis"]
        elif selected_format == "mkv":
            codec_options = ["-c:v", "libx264", "-c:a", "aac"]
        else:  # Default untuk mp4 atau format lainnya
            codec_options = ["-c:v", "libx264", "-c:a", "aac"]

        # Jalankan perintah FFmpeg
        command = [FFMPEG_PATH, "-i", input_file] + codec_options + [output_file]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

        for line in process.stdout:
            if "time=" in line:
                # Simulasi progress (atau parsing output FFmpeg untuk progress sebenarnya)
                progress_var.set(progress_var.get() + 10)
                root.update_idletasks()

        process.wait()
        if process.returncode == 0:
            progress_var.set(100)  # Selesaikan progress
            messagebox.showinfo("Sukses", f"Konversi selesai!\nTersimpan sebagai: {output_file}")
        else:
            messagebox.showerror("Error", "Konversi gagal. Pastikan FFmpeg terinstal dengan benar.")
    except Exception as e:
        messagebox.showerror("Error", f"Terjadi kesalahan: {str(e)}")

# Fungsi untuk mengunduh video/audio dari YouTube
def download_video():
    url = url_var.get()
    format_choice = format_var.get()

    if not url:
        messagebox.showerror("Error", "Masukkan URL YouTube terlebih dahulu!")
        return

    if not cookies_file:
        messagebox.showwarning("Peringatan", "File cookies belum dipilih. Beberapa video mungkin tidak dapat diunduh.")

    save_path = filedialog.askdirectory()
    if not save_path:
        return  # Jika user membatalkan pemilihan folder

    # Konfigurasi opsi yt_dlp
    ydl_opts = {
        'progress_hooks': [progress_hook],  # Tambahkan progress hook
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
        'cookies': cookies_file,
    }

    # Tentukan format berdasarkan pilihan pengguna
    if format_choice == "mp4":
        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
    elif format_choice == "mp3":
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    elif format_choice == "wav":
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        }]
    elif format_choice == "webm":
        ydl_opts['format'] = 'bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]'
    elif format_choice == "mkv":
        ydl_opts['format'] = 'bestvideo+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mkv'
    else:  # Default ke format original
        ydl_opts['format'] = 'best'

    try:
        progress_var.set(0)  # Reset progress bar
        root.update_idletasks()

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        progress_var.set(100)  # Selesaikan progress
        messagebox.showinfo("Sukses", "Unduhan selesai!")
    except Exception as e:
        messagebox.showerror("Error", f"Gagal mengunduh video!\n{str(e)}")

def progress_hook(d):
    if d['status'] == 'downloading':
        downloaded = d.get('downloaded_bytes', 0)
        total = d.get('total_bytes', 1)
        progress = (downloaded / total) * 100
        progress_var.set(progress)
        root.update_idletasks()

# Fungsi untuk memilih cookies file
def select_cookies_file():
    global cookies_file
    cookies_file = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
    if cookies_file:
        messagebox.showinfo("Sukses", f"Cookies file berhasil dipilih: {cookies_file}")
    else:
        messagebox.showwarning("Peringatan", "Tidak ada file cookies yang dipilih.")

# GUI Setup
root = tk.Tk()
root.title("MP4 Converter & YouTube Downloader")
root.geometry("500x550")

entry_var = tk.StringVar()
url_var = tk.StringVar()
format_var = tk.StringVar(value="MP4")

# Frame untuk konversi file lokal
frame1 = tk.LabelFrame(root, text="Konversi File Lokal", padx=10, pady=10)
frame1.pack(pady=10, fill="x", padx=10)

tk.Label(frame1, text="Pilih File:").grid(row=0, column=0, pady=5)
entry_file = tk.Entry(frame1, textvariable=entry_var, width=40)
entry_file.grid(row=0, column=1, pady=5)
tk.Button(frame1, text="Browse", command=select_file).grid(row=0, column=2, pady=5, padx=5)
tk.Label(frame1, text="Format:").grid(row=1, column=0, pady=5)

# Dropdown menu untuk format
format_local = ttk.Combobox(frame1, textvariable=format_var, values=["original", "mp4", "mp3", "wav", "webm", "mkv"], state="readonly")
format_local.grid(row=1, column=1, pady=5)
tk.Button(frame1, text="Konversi", command=convert_to_format, bg="green", fg="white").grid(row=2, column=0, columnspan=3, pady=10)

# Frame untuk pengunduhan video
frame2 = tk.LabelFrame(root, text="Unduh Video dari YouTube", padx=10, pady=10)
frame2.pack(pady=10, fill="x", padx=10)

tk.Label(frame2, text="Masukkan URL:").grid(row=0, column=0, pady=5)
entry_url = tk.Entry(frame2, textvariable=url_var, width=40)
entry_url.grid(row=0, column=1, pady=5)

# Dropdown menu untuk format unduhan
format_menu = ttk.Combobox(frame2, textvariable=format_var, values=["original", "mp4", "mp3", "wav", "webm", "mkv"], state="readonly")
format_menu.grid(row=1, column=1, pady=5)
tk.Button(frame2, text="Download", command=download_video, bg="blue", fg="white").grid(row=2, column=0, columnspan=3, pady=10)

# Progress
frame3 = tk.LabelFrame(root, text="Progress", padx=10, pady=10)
progress_label = tk.Label(root, text="")
progress_label.pack(pady=10)

# Frame untuk memilih cookies file
frame3 = tk.LabelFrame(root, text="Pilih Cookies File", padx=10, pady=10)
frame3.pack(pady=10, fill="x", padx=10)

tk.Button(frame3, text="Pilih Cookies", command=select_cookies_file, bg="purple", fg="white").pack(pady=10)

# Add a progress bar variable
progress_var = tk.DoubleVar()

# Add a progress bar widget
progress_bar = ttk.Progressbar(frame3, variable=progress_var, maximum=100)
progress_bar.pack(pady=10, fill="x")

root.mainloop()
