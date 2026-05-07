const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 8899;
const WEB_DIR = path.join(__dirname, '..', 'web');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
};

const server = http.createServer((req, res) => {
  let filePath = path.join(WEB_DIR, req.url === '/' ? '/index.html' : req.url.split('?')[0]);
  filePath = path.normalize(filePath);

  if (!filePath.startsWith(WEB_DIR)) {
    res.writeHead(403);
    return res.end('Forbidden');
  }

  const ext = path.extname(filePath);
  const contentType = MIME[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end('Not Found');
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(data);
    }
  });
});

const { exec } = require('child_process');

// 获取本机局域网IP
function getLocalIP() {
  const os = require('os');
  const interfaces = os.networkInterfaces();
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        return iface.address;
      }
    }
  }
  return '0.0.0.0';
}

server.listen(PORT, () => {
  const localIP = getLocalIP();
  console.log('');
  console.log('╔══════════════════════════════════════════════╗');
  console.log('║   🚀 Agent Daily Radar 已启动               ║');
  console.log(`║   💻 电脑访问: http://localhost:${PORT}           ║`);
  console.log(`║   📱 手机访问: http://${localIP}:${PORT}       ║`);
  console.log('║   📁 ' + WEB_DIR + '  ║');
  console.log('║   ⚠️  确保手机和电脑在同一WiFi下              ║');
  console.log('║   按 Ctrl+C 停止                              ║');
  console.log('╚══════════════════════════════════════════════╝');
  console.log('');

  // 自动打开浏览器
  const cmd = process.platform === 'win32' ? `start http://localhost:${PORT}` : `open http://localhost:${PORT}`;
  exec(cmd);
});
