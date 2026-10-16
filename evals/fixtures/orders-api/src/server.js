import http from 'node:http';
import { handleOrders } from './routes/orders.js';
import { handleHealth } from './routes/health.js';

export function createServer() {
  return http.createServer(async (req, res) => {
    const chunks = [];
    for await (const c of req) chunks.push(c);
    const body = chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : null;
    const result = req.url.startsWith('/orders')
      ? await handleOrders({ method: req.method, url: req.url, body })
      : handleHealth();
    res.writeHead(result.status, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(result.body));
  });
}

if (process.argv[1] && process.argv[1].endsWith('server.js')) {
  createServer().listen(3000);
}
