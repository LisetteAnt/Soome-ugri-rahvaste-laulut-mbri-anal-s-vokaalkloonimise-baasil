# =============================================================================
# Laulja-sõltumatu (speaker-independent) random forest klassifikatsioon
#
# Meetod: groupKFold, kus iga laulja kuulub ainult ühte plokki
# =============================================================================

library(randomForest)
library(caret)
library(dplyr)
library(stringr)
library(tibble)

set.seed(42)

# =============================================================================
# 1. SAMM: Lae features.csv ja clean-tabelid (andmed koos lauljatega)
# =============================================================================
features <- read.csv("features.csv", stringsAsFactors = FALSE, check.names = FALSE)

# iga rahva individuaalne metadata
eesti   <- read.csv("filtered_eesti_clean.csv",        stringsAsFactors = FALSE)
saami   <- read.csv("filtered_saamid_clean.csv",       stringsAsFactors = FALSE)
karjala <- read.csv("filtered_karjala_clean.csv",      stringsAsFactors = FALSE)
handi   <- read.csv("filtered_handidmansid_clean.csv", stringsAsFactors = FALSE)
ungari  <- read.csv("filtered_ungari.csv", sep = ";",  stringsAsFactors = FALSE)

# =============================================================================
# 2. SAMM: Ühine tabel (viide, esitaja) mapping kõigist clean-tabelitest
# =============================================================================
# Eesti tabelis on mõnel real "Viide: Marie Sepp, Laad: ..." formaadiga -
# eraldame puhta nime
puhasta_esitaja <- function(s) {
  s <- as.character(s)
  ifelse(
    str_detect(s, "Viide:"),
    str_trim(str_extract(s, "(?<=Viide:\\s)[^,]+")),
    str_trim(s)
  )
}

# kõik salvestused ja nende esitajad
mapping <- bind_rows(
  data.frame(viide = eesti$Viide,       esitaja = puhasta_esitaja(eesti$Esitaja)),
  data.frame(viide = saami$Viide,       esitaja = saami$Esitaja),
  data.frame(viide = karjala$Viide,     esitaja = karjala$Esitaja),
  data.frame(viide = handi$Viide,       esitaja = handi$Esitaja),
  data.frame(viide = ungari$Reference,  esitaja = ungari$Informer)
) %>% distinct()

# parandus Olga nimega
mapping <- mapping %>%
  mutate(esitaja = case_when(
    esitaja == "Olja Jefimovna Sopotšina (Kostja Pokatševi abikaasa)" ~
      "Olga Jefimovna Sopotšina (Kostja Pokatševa abikaasa)",
    TRUE ~ esitaja
  ))

# =============================================================================
# 3. SAMM: Failinimedest -> viide
# =============================================================================

# faili nimede puhastus viidele identseks
ekstrakti_viide <- function(failinimi, rahvas) {
  nimi <- failinimi
  on_kloonitud <- str_starts(nimi, "vc_")
  
  if (on_kloonitud) {
    nimi <- str_replace(nimi, "^vc_[a-z]+_", "")
    nimi <- str_replace(nimi, "_wav_[0-9.]+_[0-9]+_[0-9.]+\\.wav$", "")
  } else {
    nimi <- str_replace(nimi, "\\.wav$", "")
  }
  # _clipN ja _vad sufiksid (viimane = puhastuse marker, mitte rahvus)
  nimi <- str_replace(nimi, "_clip[0-9]+$", "")
  nimi <- str_replace(nimi, "_vad$", "")
  
  if (rahvas == "ungari") {
    # Eemalda lõpust ID-number (nt _1312251). Ungari clean-tabelis on
    # alakriipsudega viide, jätame alakriipsud alles.
    nimi <- str_replace(nimi, "_\\d{6,}$", "")
  } else {
    # Kloonitud failidel on alakriipsud asendatud:
    if (on_kloonitud) {
      nimi <- str_replace_all(nimi, ",_", ", ")
      nimi <- str_replace_all(nimi, "__", ". ")
      nimi <- str_replace_all(nimi, "_", " ")
    }
  }
  str_trim(nimi)
}

features$viide <- mapply(ekstrakti_viide, features$file, features$rahvas)
features$kloonitud <- str_starts(features$file, "vc_")

# =============================================================================
# 4. SAMM: Liidame esitaja suurele andmestikule ja kontrollime
# =============================================================================
features <- features %>% left_join(mapping, by = "viide")

cat("Kogu ridu:", nrow(features), "\n")
cat("Esitaja teada:", sum(!is.na(features$esitaja)), "\n")
cat("Esitaja teadmata:", sum(is.na(features$esitaja)), "\n\n")

# Kontroll. esitajate arv rahvuste lõikes
cat("=== ESITAJATE JAOTUS (originaalmaterjal) ===\n")
toor_diag <- features %>% filter(!kloonitud)
for (r in unique(toor_diag$rahvas)) {
  sub <- toor_diag %>% filter(rahvas == r)
  n_es <- length(unique(sub$esitaja))
  cat(sprintf("  %-15s: %d esitajat, %d klippi\n", r, n_es, nrow(sub)))
}

write.csv(features, "features.csv")

# =============================================================================
# 5. SAMM: Tunnuste loend (tämbri tunnused)
# =============================================================================
tämber_tunnused <- features %>%
  select(-file, -viide, -kloonitud, -esitaja,
         -rahvas, -RAHVUS, -tyyp) %>%
  colnames()

cat("\nTunnuste arv:", length(tämber_tunnused), "\n")

}

# =============================================================================
# 6. SAMM: Klassifitseerimise funktsioon 
# =============================================================================
tee_klassifikatsioon <- function(andmed, silt) {
  cat("\n========================================\n")
  cat("===", silt, "\n")
  cat("========================================\n")
  
  X <- andmed %>% select(all_of(tämber_tunnused))
  y <- factor(andmed$rahvas)
  grupid <- factor(andmed$esitaja)
  
  cat("Vaatlusi:", nrow(andmed),
      "| Gruppe (esitajaid):", length(unique(grupid)),
      "| Rahvusi:", length(unique(y)), "\n")
  
  # Klassikaalud (väiksemad klassid saavad suurema kaalu)
  kaalud <- as.numeric(1 / table(y)[y])
  
  # GROUP-BASED k-fold CV: iga laulja kõik klipid samas voldis
  # Kasutame k = min(5, vähim esitajate arv klassis)
  min_esitajaid_klassis <- andmed %>%
    group_by(rahvas) %>%
    summarise(n = n_distinct(esitaja)) %>%
    pull(n) %>% min()
  n_folds <- min(5, min_esitajaid_klassis) # 1/5 = 20% testis, 80% treeningus
  cat("Voldide arv (k):", n_folds,
      "  [vähim esitajaid klassis:", min_esitajaid_klassis, "]\n\n")
  
  voldid <- groupKFold(grupid, k = n_folds) # jagab grupid 5 ploki vahel
  
  kontroll <- trainControl(
    method = "cv",
    index = voldid,
    savePredictions = "final",
    classProbs = TRUE
  )
  
  mudel <- train(
    X, y,
    method    = "rf",
    trControl = kontroll,
    ntree     = 100,
    weights   = kaalud,
    importance = TRUE
  )
  
  cat("Täpsus (laulja-sõltumatu CV):",
      round(max(mudel$results$Accuracy), 3), "\n\n")
  
  cat("Segadusmaatriks (kõik CV-ennustused):\n")
  cm <- confusionMatrix(mudel$pred$pred, mudel$pred$obs)
  print(cm$table)
  cat("\nKlassipõhine täpsus:\n")
  print(round(cm$byClass[, c("Sensitivity", "Specificity", "Precision")], 3))
}

# =============================================================================
# 7. SAMM: Klassifitseerimine eraldi toor- ja kloonitud materjalil
# =============================================================================
set.seed(42)
toor  <- features %>% filter(!kloonitud)
kloon <- features %>% filter(kloonitud)

klf_toor  <- tee_klassifikatsioon(toor,  "Toormaterjal")
klf_kloon <- tee_klassifikatsioon(kloon, "Kloonitud materjal")

