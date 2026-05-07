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

server.listen(PORT, () => {
  console.log('');
  console.log('╔══════════════════════════════════════════════╗');
  console.log('║   🚀 Agent Daily Radar 已启动               ║');
  console.log(`║   👉 http://localhost:${PORT}                   ║`);
  console.log('║   📁 ' + WEB_DIR + '  ║');
  console.log('║   按 Ctrl+C 停止                              ║');
  console.log('╚══════════════════════════════════════════════╝');
  console.log('');

  // 自动打开浏览器
  const { exec } = require('child_process');
  const cmd = process.platform === 'win32' ? `start http://localhost:${PORT}` : `open http://localhost:${PORT}`;
  exec(cmd);
});
