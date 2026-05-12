import os
import csv
import numpy as np
import librosa
import soundfile as sf
from collections import defaultdict
import shutil

# --- MUUTUJAD ---

NO_CLIPS_FOLDER = "" # kaust, kuhu kopeerida failid millelt klippe ei leitud
os.makedirs(NO_CLIPS_FOLDER, exist_ok=True)
INPUT_FOLDER = "" # kaust, kust lugeda kõik mp3 failid
OUTPUT_FOLDER = "" # kaust, kuhu salvestada 10-sekundilised klipid
CSV_FILE = "" # CSV fail, mis sisaldab veerge: filename, start, end (aeg sekundites) -> saadakse MusicAndSpeeckDetection.py skriptiga
CLIP_LENGTH = 10 
SR = 44100
SILENCE_THRESHOLD = 0.01  # alla selle = vaikus, (0.0 - 1.0, muuda kuulamise järgi), mida madalam, seda rangemalt vaikus tuvastatakse
FRAME_MS = 30  

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- ABIFUNKTSIOONID ---

# Kood on loodud tehisaru selgitava ja parandava abiga. (Claude.ai, Opus 4.7)

def parse_time(time_str):
    """CSV failist aja formaadi 'M:SS' või 'H:MM:SS' teisendamine sekunditeks
    
    Argumendid:
        time_str (str): Aeg stringina, näiteks '1:23' või '0:01:23'

    Tagastab:
        int: Aeg sekundites
    """
    parts = time_str.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0

def remove_silence(audio, sr, silence_threshold=SILENCE_THRESHOLD, frame_ms=30):
    """
    Eemaldab vaikuse amplituudi järgi. 

    Argumendid:
        audio (np.ndarray): Sisendheli NumPy massiivina
        sr (int): Heli sagedus 
        silence_threshold (float): Alla selle amplituudi loetakse vaikuseks (0.0 - 1.0)
        frame_ms (int): Ajaaken, milles kontrollitakse vaikust
    Tagastab:
        np.ndarray: Puhastatud heli, kus vaikuse osad on eemaldatud
    """
    frame_len = int(sr * frame_ms / 1000)
    result = []

    for i in range(0, len(audio), frame_len):
        frame = audio[i:i + frame_len]
        if np.max(np.abs(frame)) >= silence_threshold:
            result.append(frame)

    if result:
        return np.concatenate(result)
    return np.array([], dtype=np.float32)

# --- LOE CSV ---

with open(CSV_FILE, newline='') as f:
    reader = csv.DictReader(f)
    segments = [
        {
            "filename": row["filename"].strip('"'),
            "start": parse_time(row["start"]),
            "end": parse_time(row["end"])
        }
        for row in reader
    ]

by_file = defaultdict(list)
for seg in segments:
    by_file[seg["filename"]].append((seg["start"], seg["end"]))

# --- PEAMINE TÖÖTLUS ---

# Kõik mp3 failid input kaustas
all_files = set(f for f in os.listdir(INPUT_FOLDER) if f.endswith(".mp3") or f.endswith(".wav"))
# Failid mis said klippe
got_clips_files = set()

for filename, segs in by_file.items():
    path = os.path.join(INPUT_FOLDER, filename)

    if not os.path.exists(path):
        print(f"Fail ei leitud: {filename}")
        continue

    print(f"\nTöötlen: {filename}")
    audio, _ = librosa.load(path, sr=SR)
    clip_samples = CLIP_LENGTH * SR
    clip_idx = 0
    # tühi buffer, kuhu kogume mitu järjestikust CSV-segmenti, et neist saaks
    # moodustada täis 10-sekundilisi klippe (üks segment võib olla lühem kui 10 s)
    buffer = np.array([], dtype=np.float32) 

    for seg_start_sec, seg_end_sec in segs:
        seg_start_sample = int(seg_start_sec * SR)
        seg_end_sample = int(seg_end_sec * SR)

        # Lõika segment ja eemalda vaikus
        segment_audio = audio[seg_start_sample:seg_end_sample]
        cleaned = remove_silence(segment_audio, SR, silence_threshold=SILENCE_THRESHOLD)

        # Lisa bufferisse
        buffer = np.concatenate([buffer, cleaned])

        # Lõika 10-sekundilised klipid
        while len(buffer) >= clip_samples:
            clip = buffer[:clip_samples]
            buffer = buffer[clip_samples:]

            out_name = f"{filename[:-4]}_clip{clip_idx}.wav"
            out_path = os.path.join(OUTPUT_FOLDER, out_name)
            sf.write(out_path, clip, SR)
            print(f"  Salvestatud: {out_name}")
            clip_idx += 1

    
    if clip_idx > 0:
        got_clips_files.add(filename)
    else:
        print(f"Ühtegi klipi ei leitud — {filename}")
        shutil.copy(path, os.path.join(NO_CLIPS_FOLDER, filename))

# Failid mis polnud CSV-s (polnud muusikalist osa tuvastatud)
csv_files = set(by_file.keys())
missing_from_csv = all_files - csv_files

for filename in missing_from_csv:
    print(f"  CSV-s puudub: {filename}")
    path = os.path.join(INPUT_FOLDER, filename)
    shutil.copy(path, os.path.join(NO_CLIPS_FOLDER, filename))

print(f"Klippe leiti: {len(got_clips_files)} faililt")
print(f"no_clips kausta kopeeritud: {len(all_files - got_clips_files)} faili")
