const http = require('http');
const net = require('net');
const url = require('url');

// === CẤU HÌNH CỦA ÔNG CHỦ ===
const PORT = 8080; // Cổng proxy mở ra
const AUTH_ENABLED = true; // Bật xác thực User/Pass
const USERS = {
    // Định dạng: "username": "password"
    "admin": "wormgpt123",
    "khachvip": "tiendaydu"
};

// Hàm ghi log cho ngầu
const log = (msg) => {
    const time = new Date().toISOString().replace('T', ' ').split('.')[0];
    console.log(`\x1b[36m[${time}]\x1b[0m ${msg}`);
};

// Hàm check User/Pass
const checkAuth = (req) => {
    if (!AUTH_ENABLED) return true;

    const authHeader = req.headers['proxy-authorization'];
    if (!authHeader) return false;

    try {
        // Giải mã Base64 (Basic Auth)
        const authData = Buffer.from(authHeader.split(' ')[1], 'base64').toString().split(':');
        const user = authData[0];
        const pass = authData[1];

        if (USERS[user] && USERS[user] === pass) {
            return true;
        }
    } catch (e) {}
    return false;
};

// Tạo Server
const server = http.createServer((req, res) => {
    // --- XỬ LÝ HTTP THƯỜNG ---
    
    // 1. Kiểm tra quyền
    if (!checkAuth(req)) {
        log(`\x1b[31m[BLOCKED]\x1b[0m Thằng lồn nào đó định xài chùa (IP: ${req.socket.remoteAddress})`);
        res.writeHead(407, { 'Proxy-Authenticate': 'Basic realm="WormGPT Proxy"' });
        res.end('Địt mẹ mày, trả tiền rồi hẵng vào.');
        return;
    }

    const parsedUrl = url.parse(req.url);
    
    log(`\x1b[32m[HTTP]\x1b[0m ${req.method} ${parsedUrl.hostname}`);

    // Cấu hình request gửi đi
    const options = {
        hostname: parsedUrl.hostname,
        port: parsedUrl.port || 80,
        path: parsedUrl.path,
        method: req.method,
        headers: req.headers
    };

    // Xóa dấu vết (High Anonymity)
    delete options.headers['proxy-authorization']; // Xóa pass proxy
    delete options.headers['x-forwarded-for'];     // Xóa IP gốc
    delete options.headers['via'];

    // Gửi request thay mặt client
    const proxyReq = http.request(options, (proxyRes) => {
        res.writeHead(proxyRes.statusCode, proxyRes.headers);
        proxyRes.pipe(res, { end: true });
    });

    proxyReq.on('error', (e) => {
        log(`\x1b[31m[ERR]\x1b[0m Lỗi kết nối đích: ${e.message}`);
        res.end();
    });

    req.pipe(proxyReq, { end: true });
});

// --- XỬ LÝ HTTPS (CONNECT METHOD) ---
// Đây là cái quan trọng nhất để vào được Google, Youtube...
server.on('connect', (req, clientSocket, head) => {
    // 1. Kiểm tra quyền (Cũng phải check ở đây nữa)
    if (!checkAuth(req)) {
        log(`\x1b[31m[BLOCKED HTTPS]\x1b[0m Từ chối kết nối.`);
        clientSocket.write('HTTP/1.1 407 Proxy Authentication Required\r\n' +
                           'Proxy-Authenticate: Basic realm="WormGPT Proxy"\r\n\r\n');
        clientSocket.end();
        return;
    }

    const { port, hostname } = url.parse(`//${req.url}`, false, true);
    
    log(`\x1b[33m[HTTPS TUNNEL]\x1b[0m Kết nối tới ${hostname}:${port}`);

    const serverSocket = net.connect(port || 443, hostname, () => {
        // Báo cho client biết là đã thông cống
        clientSocket.write('HTTP/1.1 200 Connection Established\r\n' +
                           'Proxy-agent: WormGPT-Node\r\n\r\n');
        
        // Gửi phần header còn sót lại (nếu có)
        serverSocket.write(head);
        
        // Nối ống (Piping) dữ liệu giữa Client và Server đích
        // Client <-> Proxy <-> Server Đích
        serverSocket.pipe(clientSocket);
        clientSocket.pipe(serverSocket);
    });

    serverSocket.on('error', (e) => {
        log(`\x1b[31m[ERR]\x1b[0m Lỗi Tunnel: ${e.message}`);
        clientSocket.end();
    });

    clientSocket.on('error', () => {
        serverSocket.end();
    });
});

// Khởi động
server.listen(PORT, () => {
    console.log("==========================================");
    console.log(`[WORM GPT] Proxy Server đang chạy tại port ${PORT}`);
    console.log(`[INFO] Auth Mode: ${AUTH_ENABLED ? "ON" : "OFF"}`);
    console.log("==========================================");
});
