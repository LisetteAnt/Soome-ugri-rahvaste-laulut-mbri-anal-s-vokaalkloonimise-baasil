#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

# Skripti enda asukoht — kõik teed lähtuvad sellest
BASE_DIR = Path(__file__).resolve().parent

reference        = BASE_DIR / "reference" / "aaaaa.wav" # sisendsignaal, mille sisu tahame kloonida sihtsignaali tämbriga
INPUT_FOLDER     = BASE_DIR / "input" / "saamid" # kataloog, kust lugeda kloonitavaid helifaile 
OUTPUT_FOLDER    = BASE_DIR / "cloned_files" # kataloog, kuhu salvestada kloonitud helid.
SEED_VC_DIR      = BASE_DIR / "seed-vc"
SEED_VC_INFERENCE = SEED_VC_DIR / "inference.py"
CONFIG_FILE      = SEED_VC_DIR / "config_dit_mel_seed_uvit_whisper_base_f0_44k.yml"

OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

toetatud = (".wav", ".mp3")
failid = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(toetatud)] # loetleb kõik toetatud helifailid kataloogis
print(f"Leitud {len(failid)} faili.")

for idx, faili_nimi in enumerate(failid, 1):
    sisend_tee  = INPUT_FOLDER / faili_nimi
    valjund_tee = OUTPUT_FOLDER / f"cloned_{Path(faili_nimi).stem}.wav"

    print(f"\n[{idx}/{len(failid)}] Kloonin: {faili_nimi}")
    result = subprocess.run([
        "python", str(SEED_VC_INFERENCE),
        "--source", str(reference), # sisendsignaal, mille sisu tahame kloonida sihtsignaali tämbriga
        "--target", str(sisend_tee), # sihtsignaal, mille tämbri tahame kloonida sisendsignaali sisu peale
        "--output", str(valjund_tee),
        "--diffusion-steps", "150",
        "--length-adjust", "1.0",
        "--inference-cfg-rate", "0.9",
        "--f0-condition", "True",
        "--auto-f0-adjust", "False",
        "--semi-tone-shift", "0",
        "--config", str(CONFIG_FILE),
        "--fp16", "True"
    ], capture_output=True, text=True)

    print("Õnnestus" if result.returncode == 0 else f"Viga: {result.stderr}")

print("\nFailid töödeldud!")
