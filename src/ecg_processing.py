import os
import numpy as np
import pandas as pd
import neurokit2 as nk

# 🔥 CRITICAL FIX → thread-safe plotting
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def process_single_ecg(file_path, record_id, output_root, sampling_rate, logger):

    file_name = os.path.basename(file_path).replace(".csv", "")
    logger.info(f"🫀 Processing {record_id} → {file_name}")

    output_dir = os.path.join(output_root, record_id, file_name)
    os.makedirs(output_dir, exist_ok=True)

    try:
        # ================================
        # 🔹 LOAD ECG (FAST + SAFE)
        # ================================
        try:
            ecg_signal = np.loadtxt(file_path, dtype=float)
        except Exception:
            # fallback for dirty files
            ecg_values = []
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    try:
                        ecg_values.append(float(line.strip()))
                    except:
                        continue
            ecg_signal = np.array(ecg_values)

        if len(ecg_signal) < 500:
            logger.warning(f"⚠️ {file_name} too short → skipped")
            return None

        if sampling_rate <= 0:
            logger.error("❌ Invalid sampling rate")
            return None

        # 🔥 Signal quality check
        if np.std(ecg_signal) < 0.01:
            logger.warning(f"⚠️ {file_name}: flat/noisy signal → skipped")
            return None

        logger.info(f"{file_name}: {len(ecg_signal)} samples")

        # ================================
        # 🔹 CLEAN SIGNAL
        # ================================
        ecg_cleaned = nk.ecg_clean(ecg_signal, sampling_rate=sampling_rate)

        # ================================
        # 🔹 R-PEAK DETECTION
        # ================================
        signals, info = nk.ecg_process(ecg_cleaned, sampling_rate=sampling_rate)
        r_peaks = np.array(info.get("ECG_R_Peaks", []))

        if len(r_peaks) < 2:
            logger.warning(f"⚠️ {file_name}: Not enough R-peaks")
            return None

        # 🔥 Safety check (avoid index mismatch)
        r_peaks = r_peaks[r_peaks < len(ecg_cleaned)]

        n_beats = len(r_peaks)
        logger.info(f"{file_name}: {n_beats} R-peaks detected")

        # ================================
        # 🔹 SAVE R-PEAKS
        # ================================
        pd.DataFrame({"R_peak_index": r_peaks}).to_csv(
            os.path.join(output_dir, "r_peaks_indices.csv"), index=False
        )

        # ================================
        # 🔹 TIME CONVERSION
        # ================================
        r_times = r_peaks / sampling_rate

        pd.DataFrame({"R_peak_time_sec": r_times}).to_csv(
            os.path.join(output_dir, "r_peaks_time_seconds.csv"), index=False
        )

        # ================================
        # 🔹 RR INTERVALS
        # ================================
        rr_sec = np.diff(r_times)
        rr_ms = rr_sec * 1000

        pd.DataFrame({
            "RR_interval_sec": rr_sec,
            "RR_interval_ms": rr_ms
        }).to_csv(
            os.path.join(output_dir, "rr_intervals.csv"),
            index=False
        )

        # ================================
        # 🔹 HRV METRICS
        # ================================
        if len(rr_ms) > 1:
            mean_rr = np.mean(rr_ms)
            sdnn = np.std(rr_ms)
            rmssd = np.sqrt(np.mean(np.diff(rr_ms) ** 2))
            nn50 = np.sum(np.abs(np.diff(rr_ms)) > 50)
            pnn50 = (nn50 / len(rr_ms)) * 100
            heart_rate = 60000 / mean_rr if mean_rr > 0 else np.nan
        else:
            mean_rr = sdnn = rmssd = pnn50 = heart_rate = np.nan

        pd.DataFrame({
            "Mean_RR_ms": [mean_rr],
            "SDNN_ms": [sdnn],
            "RMSSD_ms": [rmssd],
            "pNN50_percent": [pnn50],
            "Heart_Rate_bpm": [heart_rate]
        }).to_csv(
            os.path.join(output_dir, "hrv_manual_metrics.csv"),
            index=False
        )

        # ================================
        # 🔹 FULL HRV (OPTIONAL SAFE)
        # ================================
        try:
            hrv_full = nk.hrv(r_peaks, sampling_rate=sampling_rate, show=False)
            hrv_full.to_csv(
                os.path.join(output_dir, "hrv_full_metrics.csv"),
                index=False
            )
        except Exception as e:
            logger.warning(f"{file_name}: HRV full failed → {e}")

        # ================================
        # 🔹 ECG PLOT (THREAD SAFE)
        # ================================
        try:
            time = np.arange(len(ecg_cleaned)) / sampling_rate

            plt.figure(figsize=(12, 4))
            plt.plot(time, ecg_cleaned, linewidth=1)
            plt.scatter(
                r_peaks / sampling_rate,
                ecg_cleaned[r_peaks],
                s=10
            )

            plt.title(f"{record_id} - {file_name}")
            plt.xlabel("Time (seconds)")
            plt.ylabel("Amplitude")
            plt.grid()

            plt.savefig(os.path.join(output_dir, "ecg_plot.png"))
            plt.close()

        except Exception as e:
            logger.warning(f"{file_name}: Plot failed → {e}")

        # ================================
        # 🔹 SUMMARY
        # ================================
        with open(os.path.join(output_dir, "summary.txt"), "w") as f:
            f.write(f"Record ID: {record_id}\n")
            f.write(f"File: {file_name}\n")
            f.write(f"Samples: {len(ecg_signal)}\n")
            f.write(f"R-peaks: {n_beats}\n")
            f.write(f"Mean RR (ms): {mean_rr:.2f}\n")
            f.write(f"SDNN (ms): {sdnn:.2f}\n")
            f.write(f"RMSSD (ms): {rmssd:.2f}\n")
            f.write(f"pNN50 (%): {pnn50:.2f}\n")
            f.write(f"Heart Rate (bpm): {heart_rate:.2f}\n")

        return {
            "record_id": record_id,
            "file": file_name,
            "mean_rr_ms": mean_rr,
            "sdnn_ms": sdnn,
            "rmssd_ms": rmssd,
            "pnn50_percent": pnn50,
            "heart_rate_bpm": heart_rate,
            "n_beats": n_beats
        }

    except Exception as e:
        logger.error(f"❌ {file_name} failed → {e}")
        return None