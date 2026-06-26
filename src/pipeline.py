import os

from src.extraction import extract_all
from src.ecg_processing import process_single_ecg
from src.dataset import save_dataset


# ================================
# 🔹 PROCESS ONE RECORD FOLDER
# ================================
def process_record_folder(folder, record_id, output_root, sampling_rate, logger, stop_flag):

    results = []
    file_count = 0

    for root, _, files in os.walk(folder):

        if stop_flag and stop_flag():
            logger.warning(" Stopped by user")
            return results, file_count

        for file in files:

            if "ecg" not in file.lower():
                continue

            file_path = os.path.join(root, file)

            res = process_single_ecg(
                file_path=file_path,
                record_id=record_id,
                output_root=output_root,
                sampling_rate=sampling_rate,
                logger=logger
            )

            if res:
                results.append(res)
                file_count += 1

    if file_count == 0:
        logger.warning(f"⚠️ No ECG found in {record_id}")
    else:
        logger.info(f" {record_id} → {file_count} ECG files processed")

    return results, file_count


# ================================
# 🚀 MAIN PIPELINE
# ================================
def run_pipeline(
    main_zip,
    extract_path,
    output_root,
    sampling_rate=512,
    stop_flag=None,
    logger=None
):

    # ----------------------------
    # Logger fallback
    # ----------------------------
    if logger is None:
        class DummyLogger:
            def info(self, msg): print(msg)
            def warning(self, msg): print(msg)
            def error(self, msg): print(msg)
        logger = DummyLogger()

    logger.info(" Pipeline started")

    os.makedirs(extract_path, exist_ok=True)
    os.makedirs(output_root, exist_ok=True)

    logger.info(f"📂 Extract path: {extract_path}")
    logger.info(f"📂 Output path: {output_root}")

    # ================================
    # 🔹 EXTRACTION (NEW)
    # ================================
    records = extract_all(main_zip, extract_path, logger)

    logger.info(f"📦 Total records detected: {len(records)}")

    all_results = []
    total_files = 0

    # ================================
    # 🔹 PROCESS EACH RECORD
    # ================================
    for i, (record_id, folder) in enumerate(records):

        if stop_flag and stop_flag():
            logger.warning("⛔ Stopped by user")
            return

        logger.info(f"🫀 Processing record {i+1}/{len(records)} → {record_id}")

        results, count = process_record_folder(
            folder=folder,
            record_id=record_id,
            output_root=output_root,
            sampling_rate=sampling_rate,
            logger=logger,
            stop_flag=stop_flag
        )

        all_results.extend(results)
        total_files += count

        # 🔥 Progress logging (for UI)
        progress = int(((i + 1) / len(records)) * 100)
        logger.info(f"[PROGRESS] {progress}")

    logger.info(f" Total ECG files processed: {total_files}")

    # ================================
    # 🔹 SAVE DATASET
    # ================================
    save_dataset(all_results, output_root, logger)

    logger.info(" Pipeline completed")