import subprocess
import os
import logging
import re
import threading
from Program.Utils import safe_filename, load_config, save_config, add_to_history, format_size, format_speed, format_eta

# Path lokal untuk ffmpeg
FFMPEG_PATH = os.path.join("ffmpeg", "bin", "ffmpeg.exe")

# Logging
logging.basicConfig(filename='app.log', level=logging.ERROR)

# Global event untuk pembatalan
cancel_event = threading.Event()

def log_error(message):
    logging.error(message)

def get_media_duration(input_path):
    """Get duration of media file in seconds."""
    try:
        cmd = [
            FFMPEG_PATH,
            '-i', input_path,
            '-hide_banner'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', result.stderr)
        if duration_match:
            hours, minutes, seconds, centiseconds = map(int, duration_match.groups())
            total_seconds = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
            return total_seconds
        return 0
    except Exception:
        return 0

def convert_file(input_path, output_path, codec, quality='medium', progress_callback=None):
    """
    Mengkonversi file media menggunakan FFmpeg.
    Mendukung konversi video/audio dengan kualitas yang dapat diatur.
    """
    try:
        # Reset cancel event
        cancel_event.clear()

        # Get input file duration
        duration = get_media_duration(input_path)
        if duration == 0:
            raise Exception("Could not determine media duration")

        # Video quality presets with optimized settings
        quality_presets = {
            'highest': {
                'mp4': ['-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-movflags', '+faststart'],
                'webm': ['-c:v', 'libvpx-vp9', '-crf', '24', '-b:v', '0', '-row-mt', '1', '-tile-columns', '2'],
                'mkv': ['-c:v', 'libx264', '-preset', 'slow', '-crf', '18'],
                'avi': ['-c:v', 'libx264', '-preset', 'slow', '-crf', '18']
            },
            'high': {
                'mp4': ['-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-movflags', '+faststart'],
                'webm': ['-c:v', 'libvpx-vp9', '-crf', '27', '-b:v', '0', '-row-mt', '1', '-tile-columns', '2'],
                'mkv': ['-c:v', 'libx264', '-preset', 'medium', '-crf', '20'],
                'avi': ['-c:v', 'libx264', '-preset', 'medium', '-crf', '20']
            },
            'medium': {
                'mp4': ['-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-movflags', '+faststart'],
                'webm': ['-c:v', 'libvpx-vp9', '-crf', '30', '-b:v', '0', '-row-mt', '1', '-tile-columns', '2'],
                'mkv': ['-c:v', 'libx264', '-preset', 'medium', '-crf', '23'],
                'avi': ['-c:v', 'libx264', '-preset', 'medium', '-crf', '23']
            },
            'low': {
                'mp4': ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28', '-movflags', '+faststart'],
                'webm': ['-c:v', 'libvpx-vp9', '-crf', '35', '-b:v', '0', '-row-mt', '1', '-tile-columns', '2'],
                'mkv': ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28'],
                'avi': ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28']
            }
        }

        # Audio codec parameters with optimized settings
        audio_codec_params = {
            'mp3': ['-acodec', 'libmp3lame', '-q:a', '2', '-threads', '0'],
            'ogg': ['-acodec', 'libvorbis', '-q:a', '4', '-threads', '0'],
            'opus': ['-acodec', 'libopus', '-b:a', '128k', '-threads', '0'],
            'wav': ['-acodec', 'pcm_s16le', '-threads', '0'],
            'm4a': ['-c:a', 'aac', '-b:a', '192k', '-threads', '0'],
            'aac': ['-c:a', 'aac', '-b:a', '192k', '-threads', '0']
        }

        # Determine if this is an audio-only format
        is_audio_format = codec.lower() in audio_codec_params

        # Build FFmpeg command with optimized settings
        command = [
            FFMPEG_PATH,
            '-i', input_path,
            '-y',  # Overwrite output file
            '-progress', 'pipe:1',  # Output progress to stdout
            '-threads', '0'  # Use all available CPU threads
        ]

        if is_audio_format:
            # Audio conversion
            command.append('-vn')  # No video for audio conversion
            command.extend(audio_codec_params[codec.lower()])
        else:
            # Video conversion
            # Get extension and quality settings
            ext = codec.lower()
            if ext not in quality_presets[quality]:
                raise Exception(f"Unsupported video format: {codec}")

            # Add video codec parameters
            command.extend(quality_presets[quality][ext])
            
            # Add high-quality audio settings with sample rate
            command.extend(['-c:a', 'aac', '-b:a', '192k', '-ar', '48000'])

        # Add output file
        command.append(output_path)

        # Start conversion process
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )

        # Track progress
        frame_count = 0
        last_progress_time = 0
        while True:
            if cancel_event.is_set():
                process.terminate()
                raise Exception("Conversion cancelled by user")

            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break

            # Parse progress information
            if line.startswith("frame="):
                try:
                    frame = re.search(r"frame=\s*(\d+)", line)
                    time = re.search(r"time=\s*(\d+):(\d+):(\d+)\.(\d+)", line)
                    speed = re.search(r"speed=\s*(\d+\.?\d*)", line)
                    bitrate = re.search(r"bitrate=\s*(\d+\.?\d*)", line)
                    
                    if frame and time:
                        frame_count = int(frame.group(1))
                        h, m, s, ms = map(int, time.groups())
                        current_time = h * 3600 + m * 60 + s + ms / 100
                        progress = min(100, (current_time / duration) * 100)
                        
                        # Only update progress every 100ms to reduce UI load
                        current_time_ms = int(current_time * 1000)
                        if current_time_ms - last_progress_time >= 100:
                            if progress_callback:
                                info = {
                                    'frame': frame_count,
                                    'time': current_time,
                                    'duration': duration,
                                    'progress': progress,
                                    'speed': float(speed.group(1)) if speed else 0,
                                    'bitrate': float(bitrate.group(1)) if bitrate else 0
                                }
                                progress_callback(info)
                            last_progress_time = current_time_ms
                            
                except Exception as e:
                    log_error(f"Error parsing progress: {str(e)}")
                    continue

        # Check if conversion was successful
        if process.returncode != 0:
            error_output = process.stderr.read()
            raise Exception(f"FFmpeg error: {error_output}")

        # Ensure progress reaches 100%
        if progress_callback:
            progress_callback({
                'frame': frame_count,
                'time': duration,
                'duration': duration,
                'progress': 100,
                'speed': 0,
                'bitrate': 0
            })

        return True

    except Exception as e:
        error_msg = f"Conversion error: {str(e)}"
        log_error(error_msg)
        if progress_callback:
            progress_callback({'error': error_msg})
        return False

def cancel_conversion():
    """Cancel the ongoing conversion process."""
    cancel_event.set()