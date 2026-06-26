import pandas as pd
import os

def save_dataset(results, output_root, logger):

    if not results or len(results) == 0:
        logger.warning("⚠️ No results to save → dataset skipped")
        return None

    try:
        df = pd.DataFrame(results)

        os.makedirs(output_root, exist_ok=True)

        path = os.path.join(output_root, "final_dataset.csv")
        df.to_csv(path, index=False)

        logger.info(f"📊 Dataset saved → {path}")

        return path

    except Exception as e:
        logger.error(f"❌ Failed to save dataset → {e}")
        return None