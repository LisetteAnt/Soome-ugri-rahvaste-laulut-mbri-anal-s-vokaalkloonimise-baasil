
library(tidyverse) 
library(ggplot2)      
library(FactoMineR)   
library(factoextra)   
library(ggpubr)      
library(knitr)      
library(dplyr)
library(patchwork)
library(Rtsne)


# loen andmestiku sisse
koik <- read.csv("features.csv")
koik <- koik %>%
  mutate(
    tyyp   = ifelse(str_starts(RAHVUS, "kloon"), "kloon", "originaal"),
    rahvas = str_remove(RAHVUS, "^kloon"),  
    rahvas = factor(rahvas, levels = c("eesti", "karjala", "handidmansid", "saamid", "ungari"))
  )

# toor = originaalmaterjal, kloon = kloonitud materj
toor  <- koik %>% filter(tyyp == "originaal")
kloon <- koik %>% filter(tyyp == "kloon")

# ============================================================
# KIRJELDAV ANALÜÜS 
# ============================================================

# ============================================================
# TUNNUSTE GRUPID
# ============================================================

spektraalsed <- c("spectral_centroid_mean", "spectral_brightness", 
                  "spectral_flatness_mean")

formandid <- c("F1_mean", "F2_mean", "F3_mean",
               "F1_bandwidth", "F2_bandwidth", "F3_bandwidth")

haalekvaliteet <- c("f0_mean", "f0_std",
                    "vibrato_rate", "vibrato_amplitude",
                    "jitter_local", "hnr_mean")

# ============================================================
# TABELID
# ============================================================

tee_tabel_eraldi <- function(andmed, tunnused, materjal_tyyp, decimals = 2) {
  sub <- andmed %>% filter(tyyp == materjal_tyyp)
  
  # Loon iga tunnuse jaoks eraldi M ja SD veerud
  tulemus <- sub %>%
    group_by(rahvas) %>%
    summarise(across(all_of(tunnused),
                     list(M = ~round(mean(.x, na.rm = TRUE), decimals),
                          SD = ~round(sd(.x, na.rm = TRUE), decimals)),
                     .names = "{.col}_{.fn}")) %>%
    mutate(rahvas = factor(rahvas, 
                           levels = c("Eestlased", "Karjalased", "Handid-mansid", 
                                      "Saamid", "Ungarlased"))) %>%
    arrange(rahvas)
  
  return(tulemus)
}

# ============================================================
# SPECTRAL FLATNESS — KORRUTAME 1000-GA
# ============================================================

# Loon uue muutuja, mis on selguse huvides 1000x suurem
koik <- koik %>%
  mutate(spectral_flatness_x1000 = spectral_flatness_mean * 1000)

spektraalsed_kohandatud <- c("spectral_centroid_mean", "spectral_brightness", 
                             "spectral_flatness_x1000")

# ============================================================
# TABELID
# ============================================================

# 1. SPEKTRAALSED — toor
tabel1 <- tee_tabel_eraldi(koik, spektraalsed_kohandatud, "originaal", decimals = 2)
cat("Tabel 1. Spektraalsed tunnused (TOORMATERJAL) ")
print(kable(tabel1, format = "pipe"))

# 2. SPEKTRAALSED — kloon
tabel2 <- tee_tabel_eraldi(koik, spektraalsed_kohandatud, "kloon", decimals = 2)
cat("Tabel 2. Spektraalsed tunnused (KLOONMATERJAL)")
print(kable(tabel2, format = "pipe"))

# 3. FORMANDID — toor
tabel3 <- tee_tabel_eraldi(koik, formandid, "originaal", decimals = 1)
cat("Tabel 3. Formandid (TOORMATERJAL)")
print(kable(tabel3, format = "pipe"))

# 4. FORMANDID — kloon
tabel4 <- tee_tabel_eraldi(koik, formandid, "kloon", decimals = 1)
cat("\n=== Tabel 4. Formandid (KLOONMATERJAL) — Hz ===\n\n")
print(kable(tabel4, format = "pipe"))

# 5. HÄÄLEKVALITEET — toor
tabel5 <- tee_tabel_eraldi(koik, haalekvaliteet, "originaal", decimals = 2)
cat("Tabel 5. Häälekvaliteet (TOORMATERJAL) ")
print(kable(tabel5, format = "pipe"))

# 6. HÄÄLEKVALITEET — kloon
tabel6 <- tee_tabel_eraldi(koik, haalekvaliteet, "kloon", decimals = 2)
cat("Tabel 6. Häälekvaliteet (KLOONMATERJAL) ")
print(kable(tabel6, format = "pipe"))

# ============================================================
# SALVESTAMINE CSV-NA
# ============================================================

write_csv(tabel1, "tabel1_spektraalsed_toor.csv")
write_csv(tabel2, "tabel2_spektraalsed_kloon.csv")
write_csv(tabel3, "tabel3_formandid_toor.csv")
write_csv(tabel4, "tabel4_formandid_kloon.csv")
write_csv(tabel5, "tabel5_haalekvaliteet_toor.csv")
write_csv(tabel6, "tabel6_haalekvaliteet_kloon.csv")


# ============================================================
#  BOXPLOTID 
# ============================================================


# ==========================
# SPEKTRAALSED TUNNUSED
# ==========================

# vali tunnused (ülevalt), siin on näitena tehtud läbi spektraalsed tunnused
tunnused <- spektraalsed_kohandatud
# tunnused <- formandid
# tunnused <- haalekvaliteet


sildid <- c("spectral_centroid_mean" = "Raskuskese (Hz)",
            "spectral_brightness" = "Heledus (osakaal)", 
            "spectral_flatness_x1000" = "Tasasus (osakaal, x1000 skaala)")

#sildid <- c("F1_mean" = "Keskmine F1",
#            "F2_mean" = "Keskmine F2",
#            "F3_mean" = "Keskmine F3",
#            "F1_bandwidth" = "F1 laius",
#            "F2_bandwidth" = "F2 laius", 
#            "F3_bandwidth" = "F3 laius")

#sildid <- c("f0_mean" = "Keskmine F0 (Hz)",
#            "f0_std" = "F0 standardhälve (Hz)",
#            "vibrato_rate" = "Vibraato kiirus (Hz)",
#            "vibrato_amplitude" = "Vibraato ulatus (FFT amplituud)",
#            "jitter_local" = "Jitter (0-1)",
#            "hnr_mean" = "HNR (dB)")

rahvas_sildid <- c(
  "eesti" = "Eestlased",
  "karjala" = "Karjalased",
  "ungari" = "Ungarlased",
  "saamid" = "Saamid",
  "handidmansid" = "Handid-Mansid"
)

# Tee andmed "pikaks" formaadiks (vajalik facet_wrap'i jaoks)
df_long <- koik %>%
  select(rahvas, tyyp, all_of(tunnused)) %>%
  pivot_longer(cols = all_of(tunnused),
               names_to = "tunnus",
               values_to = "väärtus")

ggplot(df_long, aes(x = rahvas, y = väärtus, fill = tyyp)) +
  geom_boxplot(outlier.size = 0.5) +
  facet_wrap(~ tunnus, scales = "free_y", ncol = 3,
             labeller = labeller(tunnus = sildid)) +
  scale_fill_manual(values = c("originaal" = "#E69F00", "kloon" = "#56B4E9")) +
  scale_x_discrete(labels = rahvas_sildid) +  
  scale_y_continuous(limits = c(0, NA), expand = expansion(mult = c(0, 0.05))) +
  labs(x = "Rahvas", y = NULL, fill = "Materjal") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 30, hjust = 1),
        legend.position = "bottom")




# =================================================
# SPECTRAL CONTRAST JOONIS
# =================================================

# =======================
# ANDMETE ETTEVALMISTUS
# =======================

# Toor
df_contrast_t <- toor %>%
  select(rahvas, starts_with("spectral_contrast") & ends_with("_mean")) %>%
  pivot_longer(-rahvas, names_to = "riba", values_to = "väärtus") %>%
  mutate(riba = as.numeric(gsub("\\D", "", riba))) %>%
  group_by(rahvas, riba) %>%
  summarise(kesk = mean(väärtus), .groups = "drop") %>%
  mutate(rahvas = factor(rahvas, 
                         levels = c("eesti", "karjala", "handidmansid", 
                                    "saamid", "ungari")))

# Kloon
df_contrast_k <- kloon %>%
  select(rahvas, starts_with("spectral_contrast") & ends_with("_mean")) %>%
  pivot_longer(-rahvas, names_to = "riba", values_to = "väärtus") %>%
  mutate(riba = as.numeric(gsub("\\D", "", riba))) %>%
  group_by(rahvas, riba) %>%
  summarise(kesk = mean(väärtus), .groups = "drop") %>%
  mutate(rahvas = factor(rahvas, 
                         levels = c("eesti", "karjala", "handidmansid", 
                                    "saamid", "ungari")))

# ==============================
# ÜHE JOONISE TEGEMINE (toor)
# ==============================

p_toor <- ggplot(df_contrast_t, aes(x = riba, y = kesk, color = rahvas)) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_x_continuous(breaks = 1:7) +
  scale_color_discrete(labels = c("eesti" = "Eestlased",
                                  "karjala" = "Karjalased",
                                  "handidmansid" = "Handid-mansid",
                                  "saamid" = "Saamid",
                                  "ungari" = "Ungarlased")) +
  labs(x = "Sagedusriba (madal → kõrge)",
       y = "Kontrast (dB)",
       title = "Originaal",
       color = "Rahvus") +
  theme_minimal() +
  theme(plot.title = element_text(size = 11, face = "bold", hjust = 0.5))

# ================================
# TEISE JOONISE TEGEMINE (kloon)
# ================================

p_kloon <- ggplot(df_contrast_k, aes(x = riba, y = kesk, color = rahvas)) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_x_continuous(breaks = 1:7) +
  scale_color_discrete(labels = c("eesti" = "Eestlased",
                                  "karjala" = "Karjalased",
                                  "handidmansid" = "Handid-mansid",
                                  "saamid" = "Saamid",
                                  "ungari" = "Ungarlased")) +
  labs(x = "Sagedusriba (madal → kõrge)",
       title = "Kloonitud",
       y = "",
       color = "Rahvus") +
  theme_minimal() +
  theme(plot.title = element_text(size = 11, face = "bold", hjust = 0.5))

# ============================================================
# KOMBINEERI ÜHEKS JOONISEKS ÜHISE LEGENDIGA
# ============================================================

joonis_kontrast <- (p_toor | p_kloon) +
  plot_layout(guides = "collect") +
  plot_annotation(
    theme = theme(plot.title = element_text(size = 13, face = "bold",
                                            hjust = 0.5))
  ) &
  theme(legend.position = "bottom")

print(joonis_kontrast)

# ===================================
# MFCC -  t-SNE
# ===================================


# Vali MFCC tunnused
mfcc_tunnused <- paste0("mfcc_", 1:13, "_mean")

# Eemalda duplikaadid, kui on
kloon_unique <- kloon %>% distinct(across(all_of(mfcc_tunnused)), .keep_all = TRUE)
# toor_unique <- toor %>% distinct(across(all_of(mfcc_tunnused)), .keep_all = TRUE)

# Standardiseeri
X <- scale(kloon_unique[, mfcc_tunnused])
# X <- scale(toor_unique[, mfcc_tunnused])

# Käivita t-SNE
set.seed(42)  # reprodutseeritavuse jaoks
tsne_tulemus <- Rtsne(X, dims = 2, perplexity = 30, max_iter = 1000)

df_tsne <- data.frame(
  X = tsne_tulemus$Y[, 1],
  Y = tsne_tulemus$Y[, 2],
  rahvas = factor(
    kloon_unique$rahvas,
    levels = c("eesti", "karjala", "ungari", "saamid", "handidmansid"),
    labels = c("Eestlased", "Karjalased", "Ungarlased", "Saamid", "Handid-Mansid")))
# asenda: toor_unique$rahvas

ggplot(df_tsne, aes(x = X, y = Y, color = rahvas)) +
  geom_point(alpha = 0.6, size = 1.5) +
  scale_color_manual(values = c("#E69F00", "#56B4E9", "#009E73", "#CC79A7", "#D55E00")) +
  labs(title = "t-SNE: MFCC profiilid rahvuste kaupa",
       x = "t-SNE dimensioon 1",
       y = "t-SNE dimensioon 2") +
  theme_minimal()




# Selleks on vaja RandomForest.R tulemust!
# =============================================================================
# KLASSIFITSEERIMISE TABEL 1: Kogutäpsus ja meta-info
# =============================================================================
tabel1 <- data.frame(
  Materjal       = c("Toormaterjal", "Kloonitud materjal"),
  Vaatlusi       = c(nrow(toor), nrow(kloon)),
  Esitajaid      = c(length(unique(toor$esitaja)), length(unique(kloon$esitaja))),
  Plokkide_arv_k = c(5, 5),
  Tapsus         = c(
    round(max(klf_toor$mudel$results$Accuracy),  3),
    round(max(klf_kloon$mudel$results$Accuracy), 3)
  )
)
write.csv(tabel1, "tabel1_kokkuvote.csv", row.names = FALSE, fileEncoding = "UTF-8")
print(tabel1)

# =============================================================================
# TABEL 2: Klassipõhine täpsus (sensitivity, specificity, precision)
# =============================================================================
saa_klassipohine <- function(cm, silt) {
  df <- as.data.frame(cm$byClass[, c("Sensitivity", "Specificity", "Precision")])
  df$Klass <- gsub("Class: ", "", rownames(df))
  df$Materjal <- silt
  df %>% select(Materjal, Klass, Sensitivity, Specificity, Precision)
}

tabel2_pikk <- bind_rows(
  saa_klassipohine(klf_toor$segadus,  "Toor"),
  saa_klassipohine(klf_kloon$segadus, "Kloon")
)

# Tee laiaks: iga klassi kohta üks rida, toor ja kloon kõrvuti
tabel2 <- tabel2_pikk %>%
  pivot_wider(
    names_from  = Materjal,
    values_from = c(Sensitivity, Specificity, Precision),
    names_glue  = "{.value}_{Materjal}"
  ) %>%
  mutate(across(where(is.numeric), ~round(.x, 3))) %>%
  select(Klass,
         Sens_Toor   = Sensitivity_Toor,  Sens_Kloon  = Sensitivity_Kloon,
         Spec_Toor   = Specificity_Toor,  Spec_Kloon  = Specificity_Kloon,
         Prec_Toor   = Precision_Toor,    Prec_Kloon  = Precision_Kloon)

write.csv(tabel2, "tabel2_klassipohine.csv", row.names = FALSE, fileEncoding = "UTF-8")
print(tabel2)


# =============================================================================
# Segadusmaatriksid protsentidena 
# =============================================================================
segadus_protsendina <- function(cm) {
  m <- cm$table
  # Iga tegeliku klassi kohta protsendid
  m_pct <- round(prop.table(m, margin = 2) * 100, 1)
  as.data.frame.matrix(m_pct)
}

seg_toor  <- segadus_protsendina(klf_toor$segadus)
seg_kloon <- segadus_protsendina(klf_kloon$segadus)

# Lisa veerg "Ennustus"
seg_toor  <- data.frame(Ennustus = rownames(seg_toor),  seg_toor)
seg_kloon <- data.frame(Ennustus = rownames(seg_kloon), seg_kloon)

print(seg_toor)
print(seg_kloon)


# =============================================================================
# GRAAFIK: Segadusmaatriksite heatmap
# =============================================================================
# Toome mõlemad maatriksid pikka formaati ja paneme kõrvuti
saa_heatmap_andmed <- function(cm, silt) {
  m_count <- as.data.frame.table(cm$table)
  colnames(m_count) <- c("Ennustus", "Tegelik", "Sagedus")
  # Protsent veerust (st tegelikust klassist)
  m_count <- m_count %>%
    group_by(Tegelik) %>%
    mutate(Protsent = round(100 * Sagedus / sum(Sagedus), 1)) %>%
    ungroup() %>%
    mutate(Materjal = silt)
  m_count
}

heat_andmed <- bind_rows(
  saa_heatmap_andmed(klf_toor$segadus,  "Originaalmaterjal"),
  saa_heatmap_andmed(klf_kloon$segadus, "Kloonitud materjal")
)
heat_andmed$Materjal <- factor(heat_andmed$Materjal,
                               levels = c("Originaalmaterjal", "Kloonitud materjal"))

p <- ggplot(heat_andmed, aes(x = Tegelik, y = Ennustus, fill = Protsent)) +
  geom_tile(color = "white", linewidth = 0.5) +
  geom_text(aes(label = paste0(Protsent, "%")), size = 3.5, color = "black") +
  scale_fill_gradient(low = "#f7fbff", high = "#08519c",
                      limits = c(0, 100), name = "Protsent") +
  facet_wrap(~ Materjal, ncol = 2) +
  scale_y_discrete(limits = rev) +  # diagonaal vasakult ülevalt
  labs(
    x = "Tegelik rahvus",
    y = "Mudeli ennustus",
    title = " "
  ) +
  theme_minimal(base_size = 11) +
  theme(
    axis.text.x  = element_text(angle = 45, hjust = 1),
    panel.grid   = element_blank(),
    strip.text   = element_text(face = "bold", size = 12),
    legend.position = "right"
  )

print(p)
