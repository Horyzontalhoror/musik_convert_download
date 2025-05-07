import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from UI.style import apply_style, create_custom_widgets
import os
import threading
import subprocess
import json
import logging
from Program.Utils import (
    load_config, save_config, log_error,
    format_size, format_speed, format_eta
)
from Program.DownloadLogic import (
    validate_dependencies, fetch_media, queue_download,
    show_history, cancel_process
)
from Program.ConvertLogic import convert_file, cancel_conversion

# Setup logging
logging.basicConfig(level=logging.ERROR)

class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Media Downloader & Converter")
        
        # Load config
        try:
            config = load_config()
            self.default_output_dir = config.get('default_output_dir', os.path.expanduser("~"))
        except Exception as e:
            log_error(f"Failed to load config: {str(e)}")
            self.default_output_dir = os.path.expanduser("~")
        
        # Setup variables
        self.setup_variables()
        
        # Setup UI
        self.setup_ui()
        
        # Apply style
        self.setup_style()
        
        # Set window size and position
        window_width = 800
        window_height = 600
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Make window resizable
        root.resizable(True, True)
        
        # Set minimum size
        root.minsize(600, 400)
        
        # Handle window close
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Validate dependencies
        if not validate_dependencies():
            self.root.destroy()

    def setup_variables(self):
        """Setup tkinter variables."""
        # Download tab variables
        self.url_var = tk.StringVar()
        self.type_var = tk.StringVar(value="video")
        self.format_var = tk.StringVar()
        
        # Progress variables
        self.title_var = tk.StringVar(value="Ready")
        self.format_info_var = tk.StringVar(value="")
        self.progress_var = tk.DoubleVar()
        self.speed_var = tk.StringVar(value="Speed: --")
        self.eta_var = tk.StringVar(value="ETA: --")
        self.size_var = tk.StringVar(value="Size: --")
        self.count_var = tk.StringVar(value="")
        
        # Convert tab variables
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.codec_var = tk.StringVar(value="mp4")
        self.quality_var = tk.StringVar(value="medium")
        self.convert_progress_text = tk.StringVar(value="Ready to convert")
        self.convert_progress_var = tk.DoubleVar()
        
        # Other variables
        self.channel_var = tk.StringVar(value="")
        self.current_formats = None

    def setup_style(self):
        """Apply modern style to the application."""
        style = ttk.Style()
        
        # Configure colors
        style.configure("Modern.TFrame", background="#ffffff")
        style.configure("Modern.TLabelframe", background="#ffffff")
        style.configure("Modern.TLabelframe.Label", background="#ffffff", foreground="#333333", font=("Segoe UI", 9))
        style.configure("Modern.TLabel", background="#ffffff", foreground="#333333", font=("Segoe UI", 9))
        style.configure("Modern.TEntry", fieldbackground="#ffffff", font=("Segoe UI", 9))
        
        # Configure Combobox
        style.configure("Modern.TCombobox", 
            background="#ffffff",
            fieldbackground="#ffffff",
            selectbackground="#0078d7",
            selectforeground="#ffffff",
            font=("Segoe UI", 9)
        )
        
        # Configure Progressbar
        style.configure("Modern.Horizontal.TProgressbar",
            background="#0078d7",
            troughcolor="#f0f0f0",
            bordercolor="#ffffff",
            lightcolor="#0078d7",
            darkcolor="#0078d7"
        )

    def create_custom_widgets(self):
        """Create custom widget classes."""
        class ModernButton(tk.Button):
            def __init__(self, master=None, **kwargs):
                kwargs.update({
                    'background': '#0078d7',
                    'foreground': '#ffffff',
                    'activebackground': '#005a9e',
                    'activeforeground': '#ffffff',
                    'relief': 'flat',
                    'font': ('Segoe UI', 9),
                    'cursor': 'hand2',
                    'padx': 15,
                    'pady': 5
                })
                super().__init__(master, **kwargs)
                
                # Bind hover events
                self.bind('<Enter>', self._on_enter)
                self.bind('<Leave>', self._on_leave)
            
            def _on_enter(self, e):
                self['background'] = '#005a9e'
            
            def _on_leave(self, e):
                self['background'] = '#0078d7'
        
        return {
            "ModernButton": ModernButton
        }

    def setup_ui(self):
        # Main frame
        self.main_frame = ttk.Frame(self.root, style="Modern.TFrame", padding="20")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        # Download tab
        self.download_frame = ttk.Frame(self.notebook, style="Modern.TFrame", padding="10")
        self.notebook.add(self.download_frame, text="Download")
        self.setup_download_tab()

        # Convert tab
        self.convert_frame = ttk.Frame(self.notebook, style="Modern.TFrame", padding="10")
        self.notebook.add(self.convert_frame, text="Convert")
        self.setup_convert_tab()

    def setup_download_tab(self):
        """Setup the download tab UI."""
        # URL input
        url_frame = ttk.LabelFrame(self.download_frame, text="URL", style="Modern.TLabelframe", padding="10")
        url_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        self.url_entry = ttk.Entry(url_frame, style="Modern.TEntry", textvariable=self.url_var)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        paste_button = self.create_custom_widgets()["ModernButton"](url_frame, text="Paste", command=self.paste_url)
        paste_button.pack(side="right")

        # Output directory selection
        output_frame = ttk.LabelFrame(self.download_frame, text="Output Directory", style="Modern.TLabelframe", padding="10")
        output_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        self.output_entry = ttk.Entry(output_frame, style="Modern.TEntry", textvariable=self.output_var)
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        browse_button = self.create_custom_widgets()["ModernButton"](output_frame, text="Browse", command=self.browse_output)
        browse_button.pack(side="right")

        # Type and format selection
        type_frame = ttk.Frame(self.download_frame)
        type_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        # Type selection
        type_label = ttk.Label(type_frame, text="Type:", style="Modern.TLabel")
        type_label.pack(side="left", padx=(0, 5))
        self.type_menu = ttk.Combobox(type_frame, textvariable=self.type_var, values=["video", "audio"], state="readonly", style="Modern.TCombobox")
        self.type_menu.pack(side="left", padx=(0, 10))
        self.type_menu.bind('<<ComboboxSelected>>', self.on_type_change)
        
        # Format selection
        format_label = ttk.Label(type_frame, text="Format:", style="Modern.TLabel")
        format_label.pack(side="left", padx=(0, 5))
        self.format_menu = ttk.Combobox(type_frame, textvariable=self.format_var, state="readonly", style="Modern.TCombobox")
        self.format_menu.pack(side="left", fill="x", expand=True)
        
        # Buttons
        button_frame = ttk.Frame(self.download_frame)
        button_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        # Download button
        self.download_button = self.create_custom_widgets()["ModernButton"](button_frame, text="Download", command=self.start_download)
        self.download_button.pack(side="left", padx=5)
        
        # Cancel button
        self.cancel_button = self.create_custom_widgets()["ModernButton"](button_frame, text="Cancel", command=self.cancel_download, state="disabled")
        self.cancel_button.pack(side="left", padx=5)
        
        # Fetch formats button
        self.fetch_button = self.create_custom_widgets()["ModernButton"](button_frame, text="Fetch Formats", command=self.fetch_and_select_format)
        self.fetch_button.pack(side="left", padx=5)

        # Progress frame
        progress_frame = ttk.LabelFrame(self.download_frame, text="Progress", style="Modern.TLabelframe", padding="10")
        progress_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        # Video info frame
        video_info_frame = ttk.Frame(progress_frame)
        video_info_frame.pack(fill="x", pady=(0, 5))
        
        # Title and channel
        ttk.Label(video_info_frame, textvariable=self.title_var, style="Modern.TLabel", font=("Segoe UI", 9, "bold")).pack(fill="x")
        ttk.Label(video_info_frame, textvariable=self.channel_var, style="Modern.TLabel").pack(fill="x")
        
        # Format info
        ttk.Label(video_info_frame, textvariable=self.format_info_var, style="Modern.TLabel").pack(fill="x")
        
        # Progress details frame
        details_frame = ttk.Frame(progress_frame)
        details_frame.pack(fill="x", pady=(5, 0))
        
        # Left side: Speed and ETA
        left_frame = ttk.Frame(details_frame)
        left_frame.pack(side="left", fill="x", expand=True)
        ttk.Label(left_frame, textvariable=self.speed_var, style="Modern.TLabel").pack(side="left", padx=(0, 10))
        ttk.Label(left_frame, textvariable=self.eta_var, style="Modern.TLabel").pack(side="left")
        
        # Right side: Size and count
        right_frame = ttk.Frame(details_frame)
        right_frame.pack(side="right")
        ttk.Label(right_frame, textvariable=self.size_var, style="Modern.TLabel").pack(side="right", padx=(10, 0))
        ttk.Label(right_frame, textvariable=self.count_var, style="Modern.TLabel").pack(side="right")
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, style="Modern.Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", pady=(5, 0))

    def setup_convert_tab(self):
        """Setup the convert tab UI."""
        # Input file selection
        input_frame = ttk.LabelFrame(self.convert_frame, text="Input File", style="Modern.TLabelframe", padding="10")
        input_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        self.input_entry = ttk.Entry(input_frame, style="Modern.TEntry", textvariable=self.input_var)
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        input_button = self.create_custom_widgets()["ModernButton"](input_frame, text="Browse", command=self.browse_input)
        input_button.pack(side="right")

        # Output file selection
        output_frame = ttk.LabelFrame(self.convert_frame, text="Output File", style="Modern.TLabelframe", padding="10")
        output_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        self.output_entry = ttk.Entry(output_frame, style="Modern.TEntry", textvariable=self.output_var)
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        output_button = self.create_custom_widgets()["ModernButton"](output_frame, text="Browse", command=self.browse_output_file)
        output_button.pack(side="right")

        # Codec and quality selection
        options_frame = ttk.Frame(self.convert_frame)
        options_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        # Codec selection
        codec_label = ttk.Label(options_frame, text="Format:", style="Modern.TLabel")
        codec_label.pack(side="left", padx=(0, 5))
        self.codec_menu = ttk.Combobox(options_frame, textvariable=self.codec_var, values=["mp4", "mkv", "webm", "avi", "mp3", "m4a", "ogg", "opus", "wav", "aac"], state="readonly", style="Modern.TCombobox")
        self.codec_menu.pack(side="left", padx=(0, 10))
        
        # Quality selection
        quality_label = ttk.Label(options_frame, text="Quality:", style="Modern.TLabel")
        quality_label.pack(side="left", padx=(0, 5))
        self.quality_menu = ttk.Combobox(options_frame, textvariable=self.quality_var, values=["highest", "high", "medium", "low"], state="readonly", style="Modern.TCombobox")
        self.quality_menu.pack(side="left", fill="x", expand=True)
        
        # Progress frame
        progress_frame = ttk.LabelFrame(self.convert_frame, text="Progress", style="Modern.TLabelframe", padding="10")
        progress_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        # Progress details
        details_frame = ttk.Frame(progress_frame)
        details_frame.pack(fill="x", pady=(0, 5))
        
        # Progress text
        ttk.Label(details_frame, textvariable=self.convert_progress_text, style="Modern.TLabel").pack(side="left")
        
        # Progress bar
        self.convert_progress_bar = ttk.Progressbar(progress_frame, 
            variable=self.convert_progress_var, 
            maximum=100, 
            style="Modern.Horizontal.TProgressbar"
        )
        self.convert_progress_bar.pack(fill="x")

        # Buttons frame
        button_frame = ttk.Frame(self.convert_frame, style="Modern.TFrame")
        button_frame.grid(row=4, column=0, columnspan=3, sticky="ew")
        self.convert_button = self.create_custom_widgets()["ModernButton"](button_frame, text="Start Conversion", command=self.start_conversion)
        self.convert_button.pack(side="left", padx=5)
        self.convert_cancel_button = self.create_custom_widgets()["ModernButton"](button_frame, text="Cancel", command=self.cancel_conversion, state="disabled")
        self.convert_cancel_button.pack(side="left", padx=5)

    def browse_output(self):
        """Browse for output directory."""
        from Program.Utils import load_config, save_config
        
        initial_dir = self.output_entry.get() or os.path.expanduser("~")
        folder = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=initial_dir
        )
        if folder:
            # Normalize path
            folder = os.path.normpath(folder)
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, folder)
            
            try:
                # Save as default directory
                config = load_config()
                config['default_output_dir'] = folder
                save_config(config)
            except Exception as e:
                log_error(f"Could not save default directory: {str(e)}")

    def browse_input(self):
        """Browse for input media file."""
        initial_dir = os.path.dirname(self.input_entry.get()) if self.input_entry.get() else os.path.expanduser("~")
        file = filedialog.askopenfilename(
            title="Select Input File", 
            initialdir=initial_dir,
            filetypes=[
                ("All Media Files", "*.mp4;*.mkv;*.avi;*.webm;*.mp3;*.wav;*.ogg;*.opus;*.m4a;*.aac"),
                ("Video Files", "*.mp4;*.mkv;*.avi;*.webm"),
                ("Audio Files", "*.mp3;*.wav;*.ogg;*.opus;*.m4a;*.aac"),
                ("All files", "*.*")
            ]
        )
        if file:
            # Normalize path
            file = os.path.normpath(file)
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, file)
            # Auto-update output path
            self.on_format_change()

    def browse_output_file(self):
        """Browse for output file location."""
        input_file = self.input_entry.get()
        initial_dir = os.path.dirname(input_file) if input_file else os.path.expanduser("~")
        initial_file = None
        
        if input_file:
            input_filename = os.path.splitext(os.path.basename(input_file))[0]
            output_ext = self.codec_var.get()
            initial_file = f"{input_filename}.{output_ext}"
            
        file = filedialog.asksaveasfilename(
            title="Save Output File",
            initialdir=initial_dir,
            initialfile=initial_file,
            defaultextension=f".{self.codec_var.get()}",
            filetypes=[
                ("MP4 Video", "*.mp4"),
                ("MKV Video", "*.mkv"),
                ("WebM Video", "*.webm"),
                ("AVI Video", "*.avi"),
                ("MP3 Audio", "*.mp3"),
                ("M4A Audio", "*.m4a"),
                ("OGG Audio", "*.ogg"),
                ("Opus Audio", "*.opus"),
                ("WAV Audio", "*.wav"),
                ("AAC Audio", "*.aac"),
                ("All files", "*.*")
            ]
        )
        if file:
            # Normalize path
            file = os.path.normpath(file)
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, file)

    def start_download(self):
        """Start the download process."""
        urls = [url.strip() for url in self.url_entry.get().split('\n') if url.strip()]
        output_dir = self.output_entry.get()
        
        if not urls:
            messagebox.showwarning("Error", "Please enter at least one URL")
            return
            
        if not output_dir:
            # Try to use default directory
            config = load_config()
            default_dir = config.get('default_output_dir')
            if default_dir and os.path.exists(default_dir):
                output_dir = default_dir
                self.output_entry.delete(0, tk.END)
                self.output_entry.insert(0, output_dir)
            else:
                messagebox.showwarning("Error", "Please select output directory")
                return
            
        # Create output directory if it doesn't exist
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Could not create output directory: {str(e)}")
            return
            
        if not self.format_var.get():
            messagebox.showwarning("Error", "Please select a format")
            return
            
        # Get the selected format ID
        selected_type = self.type_var.get()
        selected_format = self.format_var.get()
        
        # Find the format ID from stored formats
        if not hasattr(self, 'current_formats'):
            messagebox.showerror("Error", "Please fetch formats first")
            return
            
        formats = self.current_formats.get(selected_type, [])
        format_id = None
        for fmt_id, fmt_desc in formats:
            if fmt_desc == selected_format:
                format_id = fmt_id
                break
                
        if not format_id:
            messagebox.showerror("Error", "Invalid format selected")
            return
            
        # Disable controls during download
        self._disable_download_controls()
        
        # Start download in a thread
        threading.Thread(target=self._download_thread, args=(
            urls, 
            output_dir,
            format_id,
            selected_type
        ), daemon=True).start()

    def start_conversion(self):
        """Start the conversion process."""
        input_file = self.input_entry.get()
        output_file = self.output_entry.get()
        
        if not input_file or not output_file:
            messagebox.showerror("Error", "Please select input and output files")
            return
            
        if not os.path.exists(input_file):
            messagebox.showerror("Error", "Input file does not exist")
            return
            
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_file)
        try:
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Could not create output directory: {str(e)}")
            return
            
        # Disable controls during conversion
        self._disable_convert_controls()
        
        # Start conversion in a thread
        threading.Thread(target=self._convert_thread, args=(
            input_file, 
            output_file, 
            self.codec_var.get(),
            self.quality_var.get()
        ), daemon=True).start()

    def fetch_media_info(self):
        """Fetch media information for the input file."""
        input_file = self.input_entry.get()
        if not input_file or not os.path.exists(input_file):
            return
            
        try:
            # Use FFprobe to get media info
            command = [
                "ffprobe",
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                input_file
            ]
            
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0:
                return
                
            info = json.loads(result.stdout)
            
            # Get stream info
            video_stream = None
            audio_stream = None
            for stream in info.get('streams', []):
                if stream['codec_type'] == 'video' and not video_stream:
                    video_stream = stream
                elif stream['codec_type'] == 'audio' and not audio_stream:
                    audio_stream = stream
                    
            # Update format options based on media type
            if video_stream:
                # It's a video file
                self.type_var.set('video')
                self.codec_menu['values'] = ["mp4", "mkv", "webm", "avi"]
            else:
                # Audio only
                self.type_var.set('audio')
                self.codec_menu['values'] = ["mp3", "m4a", "ogg", "opus", "wav", "aac"]
                
            # Set default output format
            if not self.codec_var.get():
                self.codec_menu.current(0)
                
            # Set default quality
            if not self.quality_var.get():
                self.quality_menu.current(2)  # medium
                
        except Exception as e:
            logging.error(f"Error fetching media info: {str(e)}")

    def _download_thread(self, urls, output_dir, format_id, selected_type):
        """Run download in a separate thread."""
        from Program.DownloadLogic import queue_download
        
        try:
            # Reset progress
            self.root.after(0, lambda: self.title_var.set("Starting download..."))
            self.root.after(0, lambda: self.channel_var.set(""))
            self.root.after(0, lambda: self.format_info_var.set(""))
            self.root.after(0, lambda: self.progress_var.set(0))
            self.root.after(0, lambda: self.speed_var.set("Speed: --"))
            self.root.after(0, lambda: self.eta_var.set("ETA: --"))
            self.root.after(0, lambda: self.size_var.set("Size: --"))
            self.root.after(0, lambda: self.count_var.set(""))
            
            # Start download
            queue_download(
                urls, 
                output_dir,
                format_id,
                selected_type,
                self._update_download_progress
            )
            
        except Exception as e:
            self.root.after(0, lambda: self._show_download_error(str(e)))

    def _update_download_progress(self, info):
        """Update download progress UI."""
        if 'error' in info:
            self.root.after(0, lambda: self._show_download_error(info['error']))
            return
            
        # Update UI based on status
        status = info.get('status', '')
        
        if status == 'start':
            # New download starting
            title = info.get('title', 'Unknown')
            channel = info.get('channel', '')
            self.root.after(0, lambda: self.title_var.set(title))
            self.root.after(0, lambda: self.channel_var.set(channel))
            self.root.after(0, lambda: self.format_info_var.set("Starting download..."))
            self.root.after(0, lambda: self.progress_var.set(0))
            self.root.after(0, lambda: self.count_var.set(f"({info.get('current', 0)}/{info.get('total', 0)})"))
            
        elif status == 'downloading':
            # Update progress
            progress = info.get('progress', 0)
            speed = info.get('speed', 'Unknown')
            eta = info.get('eta', 'Unknown')
            size = info.get('size', '')
            current = info.get('current', 0)
            total = info.get('total', 0)
            
            self.root.after(0, lambda: self.progress_var.set(progress))
            self.root.after(0, lambda: self.speed_var.set(f"Speed: {speed}"))
            self.root.after(0, lambda: self.eta_var.set(f"ETA: {eta}"))
            self.root.after(0, lambda: self.size_var.set(f"Size: {size}"))
            self.root.after(0, lambda: self.count_var.set(f"({current}/{total})"))
            self.root.after(0, lambda: self.format_info_var.set(info.get('format', 'Downloading...')))
            
        elif status == 'complete':
            # Download complete
            self.root.after(0, lambda: self._enable_download_controls())
            self.root.after(0, lambda: self.format_info_var.set("Download complete!"))
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.speed_var.set("Speed: --"))
            self.root.after(0, lambda: self.eta_var.set("ETA: --"))
            self.root.after(0, lambda: self.size_var.set("Size: --"))
            self.root.after(0, lambda: self.count_var.set(""))
            self.root.after(0, lambda: messagebox.showinfo("Success", "Download completed successfully!"))

    def _convert_thread(self, input_file, output_file, codec, quality):
        """Run conversion in a separate thread."""
        from Program.ConvertLogic import convert_file
        
        try:
            # Reset progress
            self.root.after(0, lambda: self.convert_progress_text.set("Starting conversion..."))
            self.root.after(0, lambda: self.convert_progress_var.set(0))
            
            # Start conversion
            convert_file(
                input_file, 
                output_file, 
                codec,
                quality,
                self._update_convert_progress
            )
            
        except Exception as e:
            self.root.after(0, lambda: self._show_convert_error(str(e)))

    def _update_convert_progress(self, info):
        """Update conversion progress UI."""
        if 'error' in info:
            self.root.after(0, lambda: self._show_convert_error(info['error']))
            return
            
        # Update UI based on status
        status = info.get('status', '')
        
        if status == 'start':
            # Conversion starting
            self.root.after(0, lambda: self.convert_progress_text.set("Starting conversion..."))
            self.root.after(0, lambda: self.convert_progress_var.set(0))
            
        elif status == 'converting':
            # Update progress
            progress = info.get('progress', 0)
            speed = info.get('speed', 'Unknown')
            eta = info.get('eta', 'Unknown')
            
            status_text = f"Converting... {speed}/s, ETA: {eta}"
            self.root.after(0, lambda: self.convert_progress_text.set(status_text))
            self.root.after(0, lambda: self.convert_progress_var.set(progress))
            
        elif status == 'complete':
            # Conversion complete
            self.root.after(0, lambda: self._enable_convert_controls())
            self.root.after(0, lambda: self.convert_progress_text.set("Conversion complete!"))
            self.root.after(0, lambda: self.convert_progress_var.set(100))
            self.root.after(0, lambda: messagebox.showinfo("Success", "Conversion completed successfully!"))

    def _show_download_error(self, error):
        """Show download error and reset UI."""
        error_msg = str(error)
        self.title_var.set("Error occurred")
        self.channel_var.set("")
        self.format_info_var.set(f"Error: {error_msg}")
        self.progress_var.set(0)
        self.speed_var.set("Speed: --")
        self.eta_var.set("ETA: --")
        self.size_var.set("Size: --")
        self.count_var.set("")
        self._enable_download_controls()
        messagebox.showerror("Download Error", f"Download failed:\n{error_msg}")
        log_error(f"Download error: {error_msg}")

    def _show_convert_error(self, error):
        """Show conversion error and reset UI."""
        error_msg = str(error)
        self.convert_progress_text.set(f"Error: {error_msg}")
        self.convert_progress_var.set(0)
        self._enable_convert_controls()
        messagebox.showerror("Convert Error", f"Conversion failed:\n{error_msg}")
        log_error(f"Convert error: {error_msg}")

    def cancel_download(self):
        """Cancel the ongoing download."""
        from Program.DownloadLogic import cancel_process
        cancel_process()
        self.format_info_var.set("Cancelling download...")

    def cancel_conversion(self):
        """Cancel the ongoing conversion."""
        from Program.ConvertLogic import cancel_conversion
        cancel_conversion()
        self.convert_progress_text.set("Cancelling conversion...")

    def _disable_download_controls(self):
        """Disable controls during download."""
        self.download_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.url_entry.configure(state="disabled")
        self.output_entry.configure(state="disabled")
        self.type_menu.configure(state="disabled")  
        self.format_menu.configure(state="disabled")
        self.fetch_button.configure(state="disabled")

    def _enable_download_controls(self):
        """Enable controls after download."""
        self.download_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self.url_entry.configure(state="normal")
        self.output_entry.configure(state="normal")
        self.type_menu.configure(state="readonly")  
        self.format_menu.configure(state="readonly")
        self.fetch_button.configure(state="normal")

    def _disable_convert_controls(self):
        """Disable controls during conversion."""
        self.convert_button.configure(state="disabled")
        self.convert_cancel_button.configure(state="normal")
        self.input_entry.configure(state="disabled")
        self.output_entry.configure(state="disabled")
        self.codec_menu.configure(state="disabled")  
        self.quality_menu.configure(state="disabled")  

    def _enable_convert_controls(self):
        """Enable controls after conversion."""
        self.convert_button.configure(state="normal")
        self.convert_cancel_button.configure(state="disabled")
        self.input_entry.configure(state="normal")
        self.output_entry.configure(state="normal")
        self.codec_menu.configure(state="readonly")  
        self.quality_menu.configure(state="readonly")  

    def on_format_change(self, event=None):
        """Update output path when format changes."""
        input_file = self.input_entry.get()
        if input_file:
            input_path = os.path.abspath(input_file)
            input_dir = os.path.dirname(input_path)
            input_filename = os.path.splitext(os.path.basename(input_path))[0]
            output_ext = self.codec_var.get()
            output_path = os.path.join(input_dir, f"{input_filename}.{output_ext}")
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, output_path)

    def on_type_change(self, event=None):
        """Handle type (video/audio) selection change."""
        self._update_format_menu()

    def fetch_and_select_format(self):
        """Fetch available formats for the video URL."""
        url = self.url_entry.get().strip().split('\n')[0]
        if not url:
            messagebox.showwarning("Error", "Please enter a video URL first.")
            return
            
        try:
            # Show fetching status
            self.format_info_var.set("Fetching available formats...")
            self.root.update()
            
            # Get formats from yt-dlp
            from Program.DownloadLogic import fetch_media
            audio_formats, video_formats, video_title = fetch_media(url)
            
            if not video_title:
                raise Exception("Could not fetch video information")
                
            # Store formats for later use
            self.current_formats = {
                'video': video_formats,
                'audio': audio_formats
            }
                
            # Update format menu based on selected type
            self._update_format_menu()
            
            # Update title and status
            self.title_var.set(video_title)
            self.format_info_var.set("Formats fetched successfully")
            
            # Show success message
            messagebox.showinfo("Success", f"Available formats fetched for:\n{video_title}")
            
        except Exception as e:
            error_msg = str(e)
            self.format_info_var.set(f"Error: {error_msg}")
            messagebox.showerror("Error", f"Failed to fetch formats: {error_msg}")
            
        finally:
            self.root.update()

    def _update_format_menu(self):
        """Update format menu based on selected type and fetched formats."""
        if not hasattr(self, 'current_formats'):
            return
            
        # Get formats for current type
        formats = self.current_formats.get(self.type_var.get(), [])
        
        if not formats:
            self.format_menu['values'] = []
            self.format_var.set('')
            return
            
        # Update format menu
        self.format_menu['values'] = [fmt[1] for fmt in formats]
        self.format_var.set('')  # Clear current selection
        self.format_menu.current(0)  # Set to first format

    def paste_url(self):
        """Paste clipboard content into URL entry."""
        try:
            clipboard_content = self.root.clipboard_get()
            if clipboard_content:
                # Get current content
                current_content = self.url_entry.get()
                # Add newline if there's existing content
                if current_content:
                    clipboard_content = f"\n{clipboard_content}"
                # Append to existing content
                self.url_entry.insert("end", clipboard_content)
        except tk.TclError:
            pass  # Clipboard was empty or invalid

    def on_close(self):
        """Handle window close."""
        if messagebox.askyesno("Confirm", "Are you sure you want to quit?"):
            self.root.destroy()

def main():
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()