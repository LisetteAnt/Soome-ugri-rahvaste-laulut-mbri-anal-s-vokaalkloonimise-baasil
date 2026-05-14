import os
import numpy as np
import librosa
import soundfile as sf

# --- MUUTUJAD ---
NO_CLIPS_FOLDER = "" # kaust, kuhu kopeerida failid millelt klippe ei leitud
OUTPUT_FOLDER = "" # kuhu salvestada 10-sekundilised klipid
SR = 44100 
CLIP_LENGTH = 10
FRAME_MS = 30 # ms, mille kaupa vaikust kontrollitakse
SILENCE_THRESHOLD = 0.01  # alla selle = vaikus,  (0.0 - 1.0, muuda vastavalt katsetamisele)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- ABIFUNKTSIOONID ---

def remove_silence(audio, sr, silence_threshold = SILENCE_THRESHOLD, frame_ms=30):
    """
    Eemaldab helifailist vaikuse amplituudi põhjal.
    Jagab audio frame_ms-pikkusteks tükkideks ja jätab alles ainult need,
    mille maksimaalne amplituud ületab läve. Allesjäänud tükid liidetakse
    järjestikku üheks pidevaks signaaliks.

    Argumendid:
        audio (np.ndarray):       sisendaudio float32 massiivina
        sr (int):                 diskreetimissagedus Hz-des
        silence_threshold (float): amplituudi lävi; frame, mille max amplituud on alla selle, loetakse vaikuseks
        frame_ms (int):           ühe frame'i pikkus millisekundites

    Tagastab:
        np.ndarray: float32 massiiv, mis sisaldab ainult mitte-vaikseid osi
                    kokku liidetuna. Kui mitte ühtki mitte-vaikset frame'i ei leitud,
                    tagastatakse tühi massiiv.
    """
    frame_len = int(sr * frame_ms / 1000) # proovide arv ühes frame'is (30ms = 1323 proovi)
    result = []

    for i in range(0, len(audio), frame_len): 
        frame = audio[i:i + frame_len] # võtame frame_ms kaupa audio tükke
        if np.max(np.abs(frame)) >= silence_threshold:
            result.append(frame) # kui frame pole vaikus, siis lisame selle tulemustesse

    if result:
        return np.concatenate(result) # kui leiti mitte-vaikust, ühendame osad kokku
    return np.array([], dtype=np.float32) # 

# --- TÖÖTLUS ---

files = [f for f in os.listdir(NO_CLIPS_FOLDER) if f.endswith(".mp3")] 

if not files:
    print("no_clips kaust on tühi!")
else:
    still_no_clips = []

    for filename in files:
        path = os.path.join(NO_CLIPS_FOLDER, filename)
        print(f"\nTöötlen: {filename}")

        audio, _ = librosa.load(path, sr=SR) 
        cleaned = remove_silence(audio, SR, threshold=SILENCE_THRESHOLD)

        clip_samples = CLIP_LENGTH * SR
        clip_idx = 0 
        buffer = cleaned 
        
        # bufferisse kogume klippe, kuni saame 10-sekundilise klipi, siis salvestame selle ja jätkame ülejäänud puhastatud audio bufferisse lisamist
        while len(buffer) >= clip_samples: 
            clip = buffer[:clip_samples]
            buffer = buffer[clip_samples:] # eemaldame bufferist selle klipi, et järgmine klipp saaks võtta järgmise 10-sekundilise osa

            out_name = f"{filename[:-4]}_clip{clip_idx}.wav"
            out_path = os.path.join(OUTPUT_FOLDER, out_name) 
            sf.write(out_path, clip, SR)
            print(f"  Salvestatud: {out_name}")
            clip_idx += 1

        if clip_idx == 0:
            print(f"  Ikka ei leitud sobivaid klippe: {filename}")
            still_no_clips.append(filename)

    print("\nLõpetatud")
    if still_no_clips:
        print(f"Faile millelt ikka ei leitud sobivaid klippe ({len(still_no_clips)}):")
        for f in still_no_clips:
            print(f"  {f}")
