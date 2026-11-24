"""
evaluasi.py - TAHAP 8: membandingkan hasil detektor dengan BERKAS KUNCI.

Istilah:
- TP (True Positive)  : detektor menandai jam+kolom yang memang ditanami anomali.
- FP (False Positive) : detektor menandai, padahal tidak ada di kunci (alarm palsu).
- FN (False Negative) : ada di kunci, tetapi detektor tidak menandainya (terlewat).

    precision = TP / (TP + FP)  -> dari semua alarm, berapa persen yang benar?
    recall    = TP / (TP + FN)  -> dari semua anomali, berapa persen yang tertangkap?

Toleransi waktu (config evaluasi.toleransi_jam) mengizinkan deteksi meleset
beberapa jam tetap dianggap benar. Default 0 = harus tepat di jam yang sama.
"""

import pandas as pd

from src.utils import get_logger, path_proyek


def evaluasi_detektor(df_deteksi, cfg):
    """Hitung TP/FP/FN, precision, recall, F1 per kolom dan total."""
    log = get_logger()
    # Kunci dibaca DI SINI (modul evaluasi), bukan di detektor.
    kunci = pd.read_csv(path_proyek(cfg["path"]["file_kunci_anomali"]))
    kunci["waktu_lokal"] = pd.to_datetime(kunci["waktu_lokal"], utc=True).dt.tz_convert(cfg["zona_waktu"])
    tol = pd.Timedelta(hours=cfg["evaluasi"]["toleransi_jam"])

    deteksi = df_deteksi.copy()
    deteksi["status"] = "FP"
    kunci["tertangkap"] = False

    for i, d in deteksi.iterrows():
        cocok = kunci[(kunci["kolom"] == d["kolom"]) &
                      ((kunci["waktu_lokal"] - d["waktu_lokal"]).abs() <= tol)]
        if len(cocok):
            deteksi.at[i, "status"] = "TP"
            kunci.loc[cocok.index, "tertangkap"] = True

    baris = []
    for kolom in list(cfg["detektor"]["kolom"]) + ["TOTAL"]:
        dk = deteksi if kolom == "TOTAL" else deteksi[deteksi["kolom"] == kolom]
        kk = kunci if kolom == "TOTAL" else kunci[kunci["kolom"] == kolom]
        tp, fp = int((dk["status"] == "TP").sum()), int((dk["status"] == "FP").sum())
        fn = int((~kk["tertangkap"]).sum())
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = (len(kk) - fn) / len(kk) if len(kk) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        baris.append({"kolom": kolom, "anomali_di_kunci": len(kk), "terdeteksi": len(dk),
                      "TP": tp, "FP": fp, "FN": fn, "precision": round(prec, 3),
                      "recall": round(rec, 3), "f1": round(f1, 3)})
    metrik = pd.DataFrame(baris)
    tot = metrik.iloc[-1]
    log.info(f"Evaluasi detektor: precision={tot['precision']}, recall={tot['recall']}, "
             f"F1={tot['f1']} (TP={tot['TP']}, FP={tot['FP']}, FN={tot['FN']})")
    return metrik, deteksi, kunci
