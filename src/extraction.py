import os
import zipfile
import shutil


# =========================
# 📦 MAIN EXTRACTION
# =========================
def extract_main_zip(main_zip, output_folder, logger):

    os.makedirs(output_folder, exist_ok=True)

    with zipfile.ZipFile(main_zip, 'r') as zip_ref:
        zip_ref.extractall(output_folder)

    logger.info("📦 Main ZIP extracted")


# =========================
# 🔍 FIND NESTED ZIPS
# =========================
def find_nested_zips(folder):
    zip_files = []

    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(".zip"):
                zip_files.append(os.path.join(root, file))

    return zip_files


# =========================
# 📂 FLATTEN (avoid double folders)
# =========================
def flatten_if_single_subfolder(path):
    items = os.listdir(path)

    if len(items) == 1:
        sub = os.path.join(path, items[0])

        if os.path.isdir(sub):
            for f in os.listdir(sub):
                shutil.move(os.path.join(sub, f), path)

            os.rmdir(sub)


# =========================
# 🚀 UNIVERSAL EXTRACTION
# =========================
def extract_all(main_zip, extract_path, logger):

    # Step 1: Extract main ZIP
    extract_main_zip(main_zip, extract_path, logger)

    # Step 2: Find nested ZIPs
    nested_zips = find_nested_zips(extract_path)

    extracted_records = []

    # =========================
    # CASE A: Nested ZIPs exist
    # =========================
    if nested_zips:

        logger.info(f"📂 Found {len(nested_zips)} nested ZIP(s)")

        for zip_path in nested_zips:

            record_id = os.path.basename(zip_path).replace(".zip", "")
            target_folder = os.path.join(extract_path, record_id)

            os.makedirs(target_folder, exist_ok=True)

            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(target_folder)

                # 🔥 FIX: avoid nested duplication
                flatten_if_single_subfolder(target_folder)

                logger.info(f"✅ Extracted → {record_id}")

                extracted_records.append((record_id, target_folder))

            except Exception as e:
                logger.error(f"❌ Failed {record_id} → {e}")

    # =========================
    # CASE B: SINGLE ZIP
    # =========================
    else:

        logger.warning("📁 No nested ZIP → SINGLE RECORD MODE")

        record_id = os.path.basename(main_zip).replace(".zip", "")

        # Already extracted in extract_path
        flatten_if_single_subfolder(extract_path)

        extracted_records.append((record_id, extract_path))

    return extracted_records