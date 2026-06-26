import logging
import os


def setup_logger(log_file):

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logger = logging.getLogger(f"CardioLens_{log_file}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    logger.handlers = []  # 🔥 reset handlers every time

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger