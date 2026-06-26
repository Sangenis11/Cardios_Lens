from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
import shutil
import os
import uuid
import threading
import time
import zipfile

from src.pipeline import run_pipeline
from src.logger import setup_logger

app = FastAPI(title="CardioLens API")

BASE_OUTPUT = "outputs"
os.makedirs(BASE_OUTPUT, exist_ok=True)

jobs = {}

# 🔥 CONFIG (tune these)
TIME_PER_MB = 1.5      # seconds per MB
TIME_PER_ECG = 2.0     # seconds per ECG file


# =========================
# 🏠 HOME
# =========================
@app.get("/")
def home():
    return {"message": "CardioLens API running 🚀"}


# =========================
# 🔍 ESTIMATE ECG COUNT
# =========================
def estimate_ecg_count(zip_path):
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            names = z.namelist()
            return sum(1 for n in names if "ecg" in n.lower())
    except:
        return 1


# =========================
# 🚀 RUN PIPELINE
# =========================
@app.post("/process-ecg/")
async def process_ecg(file: UploadFile = File(...)):

    run_id = str(uuid.uuid4())

    run_folder = os.path.join(BASE_OUTPUT, f"run_{run_id}")
    extract_path = os.path.join(run_folder, "extracted")
    output_path = os.path.join(run_folder, "processed")
    log_file = os.path.join(run_folder, "pipeline.log")
    zip_path = os.path.join(run_folder, "input.zip")

    os.makedirs(run_folder, exist_ok=True)

    # =========================
    # 📦 FILE SIZE
    # =========================
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    file_size_mb = file_size / (1024 * 1024)

    # =========================
    # SAVE FILE
    # =========================
    with open(zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # =========================
    # 🧠 ESTIMATE WORKLOAD
    # =========================
    num_ecg = estimate_ecg_count(zip_path)

    estimated_time = int(
        max(10,
            file_size_mb * TIME_PER_MB +
            num_ecg * TIME_PER_ECG
        )
    )

    logger = setup_logger(log_file)
    stop_flag = {"stop": False}

    # =========================
    # JOB INIT
    # =========================
    jobs[run_id] = {
        "status": "running",
        "stop": stop_flag,
        "folder": run_folder,
        "log": log_file,
        "zip": None,
        "error": None,

        # 🔥 SMART ETA
        "start_time": time.time(),
        "estimated_time": estimated_time,
        "file_size_mb": round(file_size_mb, 2),
        "num_ecg": num_ecg,

        # future extension
        "progress": 0
    }

    # =========================
    # BACKGROUND JOB
    # =========================
    def job():
        try:
            run_pipeline(
                main_zip=zip_path,
                extract_path=extract_path,
                output_root=output_path,
                stop_flag=lambda: stop_flag["stop"],
                logger=logger
            )

            if stop_flag["stop"]:
                jobs[run_id]["status"] = "stopped"
            else:
                jobs[run_id]["status"] = "completed"

        except Exception as e:
            jobs[run_id]["status"] = "failed"
            jobs[run_id]["error"] = str(e)
            logger.error(f"❌ Job failed → {e}")

    thread = threading.Thread(target=job, daemon=True)
    thread.start()

    return {
        "run_id": run_id,
        "status": "running",
        "estimated_time": estimated_time
    }


# =========================
# 📡 STATUS
# =========================
@app.get("/status/{run_id}")
def get_status(run_id: str):

    job = jobs.get(run_id)

    if not job:
        return {"status": "not_found"}

    return {
        "status": job["status"],
        "error": job["error"],

        # 🔥 ETA DATA
        "start_time": job.get("start_time"),
        "estimated_time": job.get("estimated_time"),
        "file_size_mb": job.get("file_size_mb"),
        "num_ecg": job.get("num_ecg"),
        "progress": job.get("progress", 0)
    }


# =========================
# 🛑 STOP
# =========================
@app.post("/stop/{run_id}")
def stop_pipeline(run_id: str):

    job = jobs.get(run_id)

    if not job:
        return {"status": "not_found"}

    job["stop"]["stop"] = True
    job["status"] = "stopping"

    return {"status": "stopping"}


# =========================
# 📜 LOGS
# =========================
@app.get("/logs/{run_id}")
def get_logs(run_id: str):

    job = jobs.get(run_id)

    if not job:
        return PlainTextResponse("No logs")

    log_file = job["log"]

    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            return PlainTextResponse(f.read())

    return PlainTextResponse("No logs yet")


# =========================
# 📥 DOWNLOAD
# =========================
@app.get("/download/{run_id}")
def download(run_id: str):

    job = jobs.get(run_id)

    if not job:
        return JSONResponse({"error": "run not found"}, status_code=404)

    if job["status"] != "completed":
        return JSONResponse({"error": "job not completed"}, status_code=400)

    folder = job["folder"]
    zip_path = folder + ".zip"

    if not os.path.exists(zip_path):
        shutil.make_archive(folder, 'zip', folder)
        job["zip"] = zip_path

    return FileResponse(
        zip_path,
        filename="cardiolens_results.zip",
        media_type="application/zip"
    )


# =========================
# 🧹 CLEANUP
# =========================
@app.delete("/cleanup/{run_id}")
def cleanup(run_id: str):

    job = jobs.get(run_id)

    if not job:
        return {"status": "not_found"}

    folder = job["folder"]

    try:
        shutil.rmtree(folder, ignore_errors=True)

        zip_path = folder + ".zip"
        if os.path.exists(zip_path):
            os.remove(zip_path)

        jobs.pop(run_id)

        return {"status": "cleaned"}

    except Exception as e:
        return {"status": "error", "message": str(e)}