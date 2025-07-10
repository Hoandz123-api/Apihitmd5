const express = require("express");
const WebSocket = require("ws");
const cors = require("cors");
const axios = require("axios");

const app = express();
app.use(cors());

const PORT = process.env.PORT || 5000;
const SELF_URL = process.env.SELF_URL || `http://localhost:${PORT}`;

// ✅ Dữ liệu kết quả mới nhất
let latestResult = {
  Phien: 0,
  Xuc_xac_1: 0,
  Xuc_xac_2: 0,
  Xuc_xac_3: 0,
  Tong: 0,
  Ket_qua: "",
  id: "@hatronghoann",
};

// ✅ Hàm tính kết quả tài/xỉu
function updateResult(d1, d2, d3, sid = null) {
  const total = d1 + d2 + d3;
  const result = total > 10 ? "Tài" : "Xỉu";
  latestResult = {
    Phien: sid || latestResult.Phien,
    Xuc_xac_1: d1,
    Xuc_xac_2: d2,
    Xuc_xac_3: d3,
    Tong: total,
    Ket_qua: result,
  };

  const timeStr = new Date().toISOString().replace("T", " ").slice(0, 19);
  console.log(
    `[🎲✅] Phiên ${latestResult.Phien} - ${d1}-${d2}-${d3} ➜ Tổng: ${total}, Kết quả: ${result} | ${timeStr}`
  );
}

// ✅ Hàm xử lý tin nhắn
function handleMessage(message) {
  try {
    const data = JSON.parse(message);
    if (!Array.isArray(data) || typeof data[1] !== "object") return;
    const payload = data[1];

    if ("d1" in payload && "d2" in payload && "d3" in payload) {
      updateResult(payload.d1, payload.d2, payload.d3, payload.sid);
    } else if ("rs" in payload) {
      const match = payload.rs.match(/\{(\d+)-(\d+)-(\d+)\}/);
      if (match) {
        const [_, d1, d2, d3] = match;
        updateResult(parseInt(d1), parseInt(d2), parseInt(d3), payload.sid);
      }
    } else if (Array.isArray(payload.hst)) {
      const last = payload.hst[payload.hst.length - 1];
      if ("d" in last && last.d.length === 3) {
        const [d1, d2, d3] = last.d.split("").map(Number);
        updateResult(d1, d2, d3, last.s);
      }
    } else if (Array.isArray(payload.htr)) {
      const last = payload.htr[payload.htr.length - 1];
      if ("d1" in last && "d2" in last && "d3" in last) {
        updateResult(last.d1, last.d2, last.d3, last.sid);
      }
    }
  } catch (err) {
    console.error("❌ Lỗi xử lý message:", err.message);
  }
}

// ✅ Kết nối WebSocket
function connectWebSocket() {
  console.log("🔌 Kết nối WebSocket...");
  const ws = new WebSocket("wss://mynygwais.hytsocesk.com/websocket", {
    headers: {
      Host: "mynygwais.hytsocesk.com",
      Origin: "https://i.hit.club",
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
      "Accept-Encoding": "gzip, deflate, br, zstd",
      "Accept-Language": "en-US,en;q=0.9",
      Pragma: "no-cache",
      "Cache-Control": "no-cache",
    },
  });

  ws.on("open", () => {
    console.log("✅ WebSocket kết nối thành công!");

    const messages = [
      [1, "MiniGame", "", "", {
        agentId: "1",
        accessToken: "1-17d1b52f17591f581fc8cd9102a28647",
        reconnect: false,
      }],
      ["6", "MiniGame", "taixiuKCBPlugin", { cmd: 2000 }],
      ["6", "MiniGame", "taixiuKCBPlugin", { cmd: 2001 }],
    ];

    messages.forEach((msg, index) => {
      setTimeout(() => ws.send(JSON.stringify(msg)), 1000 * index);
    });
  });

  ws.on("message", (msg) => handleMessage(msg));

  ws.on("close", (code, reason) => {
    console.warn(`⚠️ Mất kết nối WebSocket (${code}): ${reason}`);
    setTimeout(connectWebSocket, 1000); // Tự reconnect sau 1s
  });

  ws.on("error", (err) => {
    console.error("❌ Lỗi WebSocket:", err.message);
  });
}

connectWebSocket();


// ✅ API trả kết quả Tài/Xỉu
app.get("/api/taixiu", (req, res) => {
  res.json(latestResult);
});

// ✅ Root route
app.get("/", (req, res) => {
  res.json({ status: "HitClub Tài Xỉu đang chạy", phien: latestResult.Phien });
});

// ✅ Chống sleep: tự ping chính mình mỗi 5 phút
setInterval(() => {
  if (SELF_URL.includes("http")) {
    axios.get(`${SELF_URL}/api/taixiu`).catch(() => {});
  }
}, 300000); // 5 phút

// ✅ Khởi chạy server
app.listen(PORT, () => {
  console.log(`🚀 Server HitMD5 Tài Xỉu đang chạy tại http://localhost:${PORT}`);
});
