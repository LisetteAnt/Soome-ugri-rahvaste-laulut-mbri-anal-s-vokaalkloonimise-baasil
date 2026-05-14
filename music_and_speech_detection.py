"""
Muusika- ja kõnetuvastus MP3-failidest.

Töötleb sisendkaustas olevad MP3-failid, käivitab nende peal tuvastusmudeli (audio-seg-data-synth) ja kirjutab CSV-faili
kõik muusikalõigud, mis on vähemalt 10 sekundit pikad. Failid, kust ei leitud
ühtegi piisava pikkusega muusikalõiku, kirjutatakse eraldi .txt faili.

Eeldused:
    - Süsteemis on installitud ffmpeg
    - Süsteemis on installitud git
    - Python paketid: tensorflow, numpy, soundfile, librosa
      (pip install tensorflow numpy soundfile librosa)
"""

import os
import glob
import csv
import shutil
import tempfile
import subprocess

import librosa


# ---------------------------------------------------------------------------
# Konstandid ja seadistused
# ---------------------------------------------------------------------------

REPO_URL = "https://github.com/satvik-venkatesh/audio-seg-data-synth.git"
MODEL_FILE = "model d-DS.h5"
DETECTION_SCRIPT = "doMusicAndSpeechDetection.py"
REPO_DIR = "audio-seg-data-synth"

INPUT_FOLDER = ""  # kaust, kus asuvad kõik salvestused
OUTPUT_CSV = ""  # failitee, kuhu kirjutatakse tulemused
NO_MUSIC_TXT = "" # failitee, kuhu kirjutatakse failid, kust ei leitud ühtegi muusikalõiku

# Minimaalne muusikalõigu pikkus sekundites
MIN_MUSIC_LENGTH = 10.0

# ---------------------------------------------------------------------------
# Ettevalmistus
# ---------------------------------------------------------------------------

def setup():
    """Klooni repositoorium, kopeeri mudel ja skript."""
    if not os.path.exists(REPO_DIR):
        print("Kloonin repositooriumi...")
        subprocess.run(["git", "clone", REPO_URL], check=True)

    # Kopeeri mudel ja tuvastusskript töökataloogi
    for f in [MODEL_FILE, DETECTION_SCRIPT]:
        src = os.path.join(REPO_DIR, "models", f)
        if os.path.exists(src) and not os.path.exists(f):
            shutil.copy(src, f)


# ---------------------------------------------------------------------------
# Abifunktsioonid
# ---------------------------------------------------------------------------

def convert_mp3_to_wav(mp3_path, wav_path):
    """Teisenda MP3-fail WAV-iks ffmpeg abil."""
    cmd = ["ffmpeg", "-i", mp3_path, "-y", "-acodec", "pcm_s16le", wav_path]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def run_detection(audio_file, output_file):
    """Käivita tuvastusskript ühel audiofailil."""
    cmd = ["python3", DETECTION_SCRIPT, audio_file, output_file]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("STDERR tuvastusskriptilt:")
        print(result.stderr)
        print("STDOUT tuvastusskriptilt:")
        print(result.stdout)
        raise Exception(
            f"Tuvastusskript ebaõnnestus {result.returncode}"
        )


def parse_output(output_file):
    """Teeb ennustuste faili nimekirjaks (start, end, label)."""
    results = []
    with open(output_file, "r") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 3:
                start, end, label = parts
                results.append((float(start), float(end), label))
    return results


def format_time(seconds):
    """Teisendab sekundid H:MM:SS või M:SS stringiks."""
    seconds = float(seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(round(seconds % 60))

    if secs == 60:
        secs = 0
        minutes += 1
    if minutes == 60:
        minutes = 0
        hours += 1

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


# ---------------------------------------------------------------------------
# Põhitöötlus
# ---------------------------------------------------------------------------

def process_mp3_folder(input_folder, output_csv, no_music_txt=NO_MUSIC_TXT):
    """
    Töötle kõik input_folder kaustas olevad .mp3 failid ja kirjuta tulemused
    output_csv faili. Failid ilma piisava muusikata lähevad no_music_txt faili.
    """
    setup()

    mp3_files = glob.glob(os.path.join(input_folder, "*.mp3"))
    if not mp3_files:
        print("Ühtegi .mp3 faili ei leitud kaustas", input_folder)
        return

    no_music_files = []

    with open(output_csv, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["filename", "start", "end", "label", "duration"])

        for mp3_file in mp3_files:
            base = os.path.basename(mp3_file)
            pred_file = base.replace(".mp3", "-preds.txt") # ajutine ennustusfail mudeli tulemusteks
            tmp_wav = None
            found_music = False
            try:
                # Loo ajutine WAV-fail, sest mudel loeb ainult .wav faile
                tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                tmp_wav.close()
                print(f"Teisendan {base} WAV-iks...")
                convert_mp3_to_wav(mp3_file, tmp_wav.name)

                # Kogu faili kestus
                duration = librosa.get_duration(path=tmp_wav.name)
                duration_str = format_time(duration)

                print(f"Töötlen {base}...")
                run_detection(tmp_wav.name, pred_file) # mudeli tuvastus
                results = parse_output(pred_file) 
                for start, end, label in results:
                    segment_len = end - start
                    if label.lower() != "music" or segment_len < MIN_MUSIC_LENGTH: # kui tegemist pole muusikaga või segment on liiga lühike
                        continue # võtame uue segmendi failis
                    found_music = True
                    start_str = format_time(start)
                    end_str = format_time(end)
                    writer.writerow([base, start_str, end_str, label, duration_str]) 

                if not found_music: # kui muusikat ei leitud
                    no_music_files.append(base) # lisame faili muusikata failide nimekirja
            except Exception as e:
                print(f"Viga faili {base} töötlemisel: {e}")
            finally:
                # Eemalda ajutine WAV-fail
                if tmp_wav and os.path.exists(tmp_wav.name):
                    os.unlink(tmp_wav.name)
                # Eemalda ajutine ennustuste fail
                if os.path.exists(pred_file):
                    os.remove(pred_file)

    # Kirjuta muusikata failid eraldi tekstifaili
    with open(no_music_txt, "w") as f:
        for filename in no_music_files:
            f.write(filename + "\n")

    print(f"Tulemused kirjutatud: {output_csv}")
    print(
        f"Faile ilma muusikata (>= {int(MIN_MUSIC_LENGTH)}s): "
        f"{len(no_music_files)} — salvestatud faili {no_music_txt}"
    )


# ---------------------------------------------------------------------------
# Käivitamine
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    process_mp3_folder(INPUT_FOLDER, OUTPUT_CSV)
