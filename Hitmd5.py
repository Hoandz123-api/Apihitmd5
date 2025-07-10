import websocket
import json
import ssl
import time
import logging
import re
from threading import Thread, Lock
from flask import Flask, jsonify
import os

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

xuc_xac_moi_nhat = {
    "Phien": 0,
    "Xuc_xac_1": 0,
    "Xuc_xac_2": 0,
    "Xuc_xac_3": 0,
    "Tong": 0,
    "Ket_qua": "",
}
data_lock = Lock()

app = Flask(__name__)

@app.route("/api/taixiu", methods=["GET"])
def get_taixiu():
    with data_lock:
        return jsonify(xuc_xac_moi_nhat)

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

def update_ket_qua(d1, d2, d3, sid=None):
    total = d1 + d2 + d3
    result = "Tài" if total > 10 else "Xỉu"
    with data_lock:
        xuc_xac_moi_nhat.update({
            "Phien": sid or xuc_xac_moi_nhat["Phien"],
            "Xuc_xac_1": d1,
            "Xuc_xac_2": d2,
            "Xuc_xac_3": d3,
            "Tong": total,
            "Ket_qua": result
        })
    logger.info(f"[KẾT QUẢ] Phiên {xuc_xac_moi_nhat['Phien']} - {d1}-{d2}-{d3} → Tổng: {total}, Kết quả: {result}")

def on_message(ws, message):
    try:
        data = json.loads(message)
        if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], dict):
            cmd_data = data[1]

            if all(k in cmd_data for k in ["d1", "d2", "d3"]):
                d1, d2, d3 = cmd_data["d1"], cmd_data["d2"], cmd_data["d3"]
                sid = cmd_data.get("sid")
                update_ket_qua(d1, d2, d3, sid)

            elif "rs" in cmd_data:
                rs = cmd_data["rs"]
                match = re.search(r"{(\\d+)-(\\d+)-(\\d+)}", rs)
                if match:
                    d1, d2, d3 = map(int, match.groups())
                    sid = cmd_data.get("sid")
                    update_ket_qua(d1, d2, d3, sid)

            elif "hst" in cmd_data and isinstance(cmd_data["hst"], list):
                last = cmd_data["hst"][-1]
                if "d" in last:
                    d_str = last["d"]
                    if len(d_str) == 3:
                        try:
                            d1, d2, d3 = int(d_str[0]), int(d_str[1]), int(d_str[2])
                            sid = last.get("s")
                            update_ket_qua(d1, d2, d3, sid)
                        except:
                            pass

            elif "htr" in cmd_data and isinstance(cmd_data["htr"], list):
                last = cmd_data["htr"][-1]
                if all(k in last for k in ["d1", "d2", "d3"]):
                    d1, d2, d3 = last["d1"], last["d2"], last["d3"]
                    sid = last.get("sid")
                    update_ket_qua(d1, d2, d3, sid)

    except Exception as e:
        logger.error(f"Lỗi xử lý tin nhắn: {e}", exc_info=True)

def on_open(ws):
    logger.info("WebSocket kết nối thành công!")
    messages_to_send = [
        [1, "MiniGame", "", "", {
            "agentId": "1",
            "accessToken": "1-6ae8c6c5e499eb5bfd25986adb78b374",
            "reconnect": False
        }],
        ["6","MiniGame","taixiuKCBPlugin",{"cmd":2000}],
        ["6","MiniGame","taixiuKCBPlugin",{"cmd":2001}]
    ]
    for msg in messages_to_send:
        ws.send(json.dumps(msg))
        time.sleep(1)

def on_error(ws, error):
    logger.error(f"WebSocket lỗi: {error}")

def on_close(ws, close_status_code, close_msg):
    logger.warning(f"Kết nối WebSocket đóng: {close_status_code}, {close_msg}")

def connect_forever():
    logger.info("Đang kết nối đến WebSocket...")
    while True:
        try:
            ws = websocket.WebSocketApp(
                "wss://mynygwais.hytsocesk.com/websocket",
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                header={
                    "Host": "mynygwais.hytsocesk.com",
                    "Origin": "https://i.hit.club", 
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache"
                }
            )
            ws.run_forever(
                sslopt={"cert_reqs": ssl.CERT_NONE},
                ping_interval=30,
                ping_timeout=10
            )
        except Exception as e:
            logger.error(f"Lỗi trong quá trình kết nối: {e}")
        logger.info("Mất kết nối. Đang thử lại...")
        time.sleep(0.5)

if __name__ == "__main__":
    logger.info("Khởi động hệ thống...")
    flask_thread = Thread(target=run_flask, name="FlaskThread", daemon=True)
    flask_thread.start()
    connect_forever()