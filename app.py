import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import yt_dlp

# Deteksi OS dan atur path FFmpeg
FFMPEG_PATH = os.path.join(os.path.dirname(__file__), "ffmpeg", "bin", "ffmpeg")
if os.name == "nt":  # Windows
    FFMPEG_PATH += ".exe"

# Global variable to store the cookies file path
cookies_file = ""

def select_file():
    file_path = filedialog.askopenfilename(filetypes=[("MP4 Files", "*.mp4")])
    if file_path:
        entry_var.set(file_path)

def convert_to_wav():
    input_file = entry_var.get()
    if not input_file:
        messagebox.showerror("Error", "Pilih file MP4 terlebih dahulu!")
        return

    output_file = os.path.splitext(input_file)[0] + ".wav"

    if not os.path.exists(FFMPEG_PATH):
        messagebox.showerror("Error", "FFmpeg tidak ditemukan! Pastikan ada di folder 'ffmpeg/bin/'.")
        return

    try:
        command = [FFMPEG_PATH, "-i", input_file, "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", output_file]
        subprocess.run(command, check=True)
        messagebox.showinfo("Sukses", f"Konversi selesai!\nTersimpan sebagai: {output_file}")
    except subprocess.CalledProcessError:
        messagebox.showerror("Error", "Konversi gagal. Pastikan FFmpeg terinstal dengan benar.")

# Fungsi untuk mengunduh video/audio dari YouTube
def download_video():
    url = url_var.get()
    format_choice = format_var.get()

    if not url:
        messagebox.showerror("Error", "Masukkan URL YouTube terlebih dahulu!")
        return

    save_path = filedialog.askdirectory()
    if not save_path:
        return  # Jika user membatalkan pemilihan folder

    ydl_opts = {}

    if format_choice == "MP4":
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
            'cookies': cookies_file,  # Menggunakan cookies dari file yang dipilih
            'sleep-requests': 5
        }
    elif format_choice == "MP3":
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
            'cookies': cookies_file,  # Menggunakan cookies dari file yang dipilih
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        messagebox.showinfo("Sukses", "Unduhan selesai!")
    except Exception as e:
        messagebox.showerror("Error", f"Gagal mengunduh video!\n{str(e)}")

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
root.geometry("500x400")

entry_var = tk.StringVar()
url_var = tk.StringVar()
format_var = tk.StringVar(value="MP4")

# Frame untuk konversi MP4 ke WAV
frame1 = tk.LabelFrame(root, text="Konversi MP4 ke WAV", padx=10, pady=10)
frame1.pack(pady=10, fill="x", padx=10)

tk.Label(frame1, text="Pilih File MP4:").grid(row=0, column=0, pady=5)
entry = tk.Entry(frame1, textvariable=entry_var, width=40)
entry.grid(row=0, column=1, pady=5)
tk.Button(frame1, text="Browse", command=select_file).grid(row=0, column=2, padx=5)
tk.Button(frame1, text="Convert to WAV", command=convert_to_wav, bg="green", fg="white").grid(row=1, column=0, columnspan=3, pady=10)

# Frame untuk pengunduhan video
frame2 = tk.LabelFrame(root, text="Unduh Video dari YouTube", padx=10, pady=10)
frame2.pack(pady=10, fill="x", padx=10)

tk.Label(frame2, text="Masukkan URL:").grid(row=0, column=0, pady=5)
entry_url = tk.Entry(frame2, textvariable=url_var, width=40)
entry_url.grid(row=0, column=1, pady=5)
format_menu = ttk.Combobox(frame2, textvariable=format_var, values=["MP4", "MP3"], state="readonly")
format_menu.grid(row=1, column=1, pady=5)
tk.Button(frame2, text="Download", command=download_video, bg="blue", fg="white").grid(row=2, column=0, columnspan=3, pady=10)

# Frame untuk memilih cookies file
frame3 = tk.LabelFrame(root, text="Pilih Cookies File", padx=10, pady=10)
frame3.pack(pady=10, fill="x", padx=10)

tk.Button(frame3, text="Pilih Cookies", command=select_cookies_file, bg="purple", fg="white").pack(pady=10)

root.mainloop()
