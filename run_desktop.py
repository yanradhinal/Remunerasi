import threading
import webview
import subprocess
import time
import requests

def start_streamlit():
    subprocess.Popen(["streamlit", "run", "nilai.py", "--server.port=8501"])
    for _ in range(30):
        try:
            res = requests.get("http://localhost:8501")
            if res.status_code == 200:
                break
        except:
            pass
        time.sleep(1)

threading.Thread(target=start_streamlit, daemon=True).start()
time.sleep(5)
webview.create_window("Aplikasi Penilaian Remunerasi", "http://localhost:8501", width=1200, height=800)
webview.start()
