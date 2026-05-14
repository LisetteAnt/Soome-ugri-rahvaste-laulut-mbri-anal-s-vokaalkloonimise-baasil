from pyexpat import features

import librosa
import numpy as np
import parselmouth
from parselmouth.praat import call
import pandas as pd
from pathlib import Path

# --- MUUTUJAD ---
INPUT_FOLDER = ""       # salvestuste kaust
OUTPUT_CSV = ""        # väljundfail
# ------------------------------------

def extract_all_features(audio_path, sr=22050):
    features = {"file": audio_path.name}

    # --- Librosa osa ---
    try:
        y, sr = librosa.load(audio_path, sr=sr)
    except Exception as e:
        print("Librosa ei suutnud faili avada:", audio_path.name, e)
        return None

    # 1. MFCC
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    for i in range(13):
        features[f"mfcc_{i+1}_mean"] = float(np.mean(mfcc[i]))
        features[f"mfcc_{i+1}_std"] = float(np.std(mfcc[i]))

    # 2. Spectral Centroid
    cent = librosa.feature.spectral_centroid(y=y, sr=sr)
    features["spectral_centroid_mean"] = float(np.mean(cent))
    features["spectral_centroid_std"] = float(np.std(cent))

    # 3. Spectral Brightness
    S = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    bright_mask = freqs >= 1500
    features["spectral_brightness"] = float(
        np.mean(S[bright_mask].sum(axis=0) / (S.sum(axis=0) + 1e-8))
    )

    # 4. Spectral Contrast
    contrast = librosa.feature.spectral_contrast(y=y, sr=sr, n_bands=6)
    for i in range(contrast.shape[0]):
        features[f"spectral_contrast_{i+1}_mean"] = float(np.mean(contrast[i]))
        features[f"spectral_contrast_{i+1}_std"] = float(np.std(contrast[i]))

    # 5. Spectral Flatness
    flatness = librosa.feature.spectral_flatness(y=y)[0]
    features["spectral_flatness_mean"] = float(np.mean(flatness))
    features["spectral_flatness_std"] = float(np.std(flatness))

    # 6. F0 (YIN)
    f0 = librosa.yin(y, fmin=50, fmax=1000, sr=sr)
    voiced = f0[f0 > 0]
    features["f0_mean"] = float(np.mean(voiced)) if len(voiced) else 0
    features["f0_std"] = float(np.std(voiced)) if len(voiced) else 0

    # --- Praat osa ---
    try:
        sound = parselmouth.Sound(str(audio_path))
    except Exception as e:
        print("Praat ei suutnud faili avada:", audio_path.name, e)
        features.update({
            "F1_mean": np.nan, "F2_mean": np.nan, "F3_mean": np.nan,
            "F1_bandwidth": np.nan, "F2_bandwidth": np.nan, "F3_bandwidth": np.nan,
            "vibrato_rate": np.nan, "vibrato_amplitude": np.nan,
            "jitter_local": np.nan,
            "hnr_mean": np.nan
        })
        return features

    # 7. Formandid
    try:
        formants = sound.to_formant_burg(
            time_step=0.01,
            max_number_of_formants=5,
            maximum_formant=5500,
            window_length=0.025
        )
        f1_vals, f2_vals, f3_vals = [], [], []
        f1_bw_vals, f2_bw_vals, f3_bw_vals = [], [], []

        for t in np.arange(0, sound.duration, 0.01):
            f1 = call(formants, "Get value at time", 1, t, "Hertz", "Linear")
            f2 = call(formants, "Get value at time", 2, t, "Hertz", "Linear")
            f3 = call(formants, "Get value at time", 3, t, "Hertz", "Linear")

            # Bandwidth (laius) — uus!
            f1_bw = call(formants, "Get bandwidth at time", 1, t, 'Hertz', 'Linear')
            f2_bw = call(formants, "Get bandwidth at time", 2, t, 'Hertz', 'Linear')
            f3_bw = call(formants, "Get bandwidth at time", 3, t, 'Hertz', 'Linear')

            if f1 > 0: f1_vals.append(f1)
            if f2 > 0: f2_vals.append(f2)
            if f3 > 0: f3_vals.append(f3)

            if f1_bw > 0: f1_bw_vals.append(f1_bw)
            if f2_bw > 0: f2_bw_vals.append(f2_bw)
            if f3_bw > 0: f3_bw_vals.append(f3_bw)


        features["F1_mean"] = float(np.mean(f1_vals)) if f1_vals else 0
        features["F2_mean"] = float(np.mean(f2_vals)) if f2_vals else 0
        features["F3_mean"] = float(np.mean(f3_vals)) if f3_vals else 0

        features['F1_bandwidth'] = np.mean(f1_bw_vals) if f1_bw_vals else 0
        features['F2_bandwidth'] = np.mean(f2_bw_vals) if f2_bw_vals else 0
        features['F3_bandwidth'] = np.mean(f3_bw_vals) if f3_bw_vals else 0

    except Exception:
        features["F1_mean"] = features["F2_mean"] = features["F3_mean"] = 0
        features['F1_bandwidth'] = features['F2_bandwidth'] = features['F3_bandwidth'] = 0

    # 8. Vibrato
    try:
        pitch_obj = sound.to_pitch(time_step=0.01, pitch_floor=60, pitch_ceiling=800)
        pitch_vals = []
        for t in np.arange(0, sound.duration, 0.01):
            p = call(pitch_obj, "Get value at time", t, "Hertz", "Linear")
            if p > 0:
                pitch_vals.append(p)

        if len(pitch_vals) > 20:
            pitch_arr_hz = np.array(pitch_vals)
            pitch_arr_semitones = 12 * np.log2(pitch_arr_hz / 100)
    
            fft_vals = np.abs(np.fft.rfft(pitch_arr_semitones - np.mean(pitch_arr_semitones)))
            fft_freqs = np.fft.rfftfreq(len(pitch_arr_semitones), d=0.01)
            vib_range = (fft_freqs >= 4) & (fft_freqs <= 8)
    
            if vib_range.any():
                # Vibrato kiirus (Hz) — kui sageli F0 võngub
                features['vibrato_rate'] = float(fft_freqs[vib_range][np.argmax(fft_vals[vib_range])])
        
                # Vibrato amplituud — kui tugev on vibrato (FFT tipu kõrgus)
                features['vibrato_amplitude'] = float(np.max(fft_vals[vib_range]))
            else:
                features['vibrato_rate'] = 0
                features['vibrato_amplitude'] = 0
    
    except Exception:
        features['vibrato_rate'] = 0
        features['vibrato_amplitude'] = 0

    # 9. Jitter
    try:
        pp = call(sound, "To PointProcess (periodic, cc)", 75, 600)
        features["jitter_local"] = float(
            call(pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        )
    except Exception:
        features["jitter_local"] = 0

    # 10. HNR
    try:
        harmonicity = call(sound, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
        features["hnr_mean"] = float(call(harmonicity, "Get mean", 0, 0))
    except Exception:
        features["hnr_mean"] = 0

    return features


def main():
    folder = Path(INPUT_FOLDER)
    files = sorted(folder.glob("*.wav"))

    print(f"Leidsin {len(files)} faili kaustast: {folder}")

    rows = []
    for f in files:
        print("Töötlen:", f.name)
        feats = extract_all_features(f)
        if feats is not None:
            rows.append(feats)

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_CSV, index=False)
    print("Valmis:", OUTPUT_CSV)


if __name__ == "__main__":
    main()
