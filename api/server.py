import json, time, threading, socket, os, secrets, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from http import cookies
from collections import deque

USER = os.getenv("DOCOPS_USER", "admin")
PASS = os.getenv("DOCOPS_PASS", "admin")
SESSIONS = set()

# Histórico Circular de 1 hora (1800 pontos com intervalo de 2s) - Tamanho Máx na RAM: ~100 KB
HISTORY_RX = deque([0] * 30, maxlen=1800) 
HISTORY_TX = deque([0] * 30, maxlen=1800)

STATE = {
    "host": {"cpu_pct": 0, "ram_pct": 0, "ram_used": 0, "ram_tot": 0, "disk_pct": 0, "disk_used": 0, "disk_tot": 0, "io_pct": 0, "ct_on": 0, "ct_tot": 0},
    "network": {"rx_mbps": 0, "tx_mbps": 0, "history_rx": [], "history_tx": []}, 
    "projects": {}
}

LAST_NET = {"rx": 0, "tx": 0, "time": time.time()}
LAST_IO = {"ticks": 0, "time": time.time()}

def req_docker(path):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect('/var/run/docker.sock')
            s.sendall(f"GET {path} HTTP/1.0\r\nHost: localhost\r\n\r\n".encode())
            res = b""
            while True:
                d = s.recv(4096)
                if not d: break
                res += d
        if b"\r\n\r\n" in res: return json.loads(res.split(b"\r\n\r\n", 1)[1].decode())
    except: return None
    return None

def monitor_loop():
    global LAST_NET, LAST_IO
    
    while True:
        now = time.time()
        dt = now - LAST_NET["time"] if (now - LAST_NET["time"]) > 0 else 1

        try:
            with open('/host/proc/meminfo') as f: mem = {l.split(':')[0]: int(l.split()[1]) for l in f}
            STATE["host"]["ram_tot"] = mem['MemTotal'] * 1024
            STATE["host"]["ram_used"] = STATE["host"]["ram_tot"] - (mem['MemAvailable'] * 1024)
            STATE["host"]["ram_pct"] = round((STATE["host"]["ram_used"] / STATE["host"]["ram_tot"]) * 100, 1)
            with open('/host/proc/loadavg') as f: STATE["host"]["cpu_pct"] = min(round((float(f.read().split()[0]) / (os.cpu_count() or 1)) * 100, 1), 100.0)
            st = os.statvfs('/host/root')
            STATE["host"]["disk_tot"] = st.f_blocks * st.f_frsize
            STATE["host"]["disk_used"] = (st.f_blocks - st.f_bavail) * st.f_frsize
            STATE["host"]["disk_pct"] = round((STATE["host"]["disk_used"] / STATE["host"]["disk_tot"]) * 100, 1) if STATE["host"]["disk_tot"] > 0 else 0
        except: pass

        try:
            with open('/host/proc/diskstats') as f:
                for line in f:
                    parts = line.split()
                    if parts[2] in ['sda', 'vda', 'nvme0n1']:
                        ticks = int(parts[12])
                        dt_io = now - LAST_IO["time"]
                        if dt_io > 0:
                            STATE["host"]["io_pct"] = min(round(max(0, ((ticks - LAST_IO["ticks"]) / (dt_io * 1000)) * 100), 1), 100.0)
                            LAST_IO = {"ticks": ticks, "time": now}
                        break
        except: pass

        try:
            rx = 0; tx = 0
            with open('/host/proc/net/dev') as f:
                for line in f.readlines()[2:]:
                    parts = line.split()
                    if parts[0].strip(':') not in ['lo', 'docker0'] and not parts[0].startswith('veth') and not parts[0].startswith('br-'):
                        rx += int(parts[1]); tx += int(parts[9])
            
            rx_mbps = round(((rx - LAST_NET["rx"]) / 1024 / 1024) / dt, 2) if LAST_NET["rx"] > 0 else 0
            tx_mbps = round(((tx - LAST_NET["tx"]) / 1024 / 1024) / dt, 2) if LAST_NET["tx"] > 0 else 0
            
            STATE["network"]["rx_mbps"] = rx_mbps
            STATE["network"]["tx_mbps"] = tx_mbps
            LAST_NET.update({"rx": rx, "tx": tx, "time": now})
            
            # Alimenta o Buffer Circular
            HISTORY_RX.append(rx_mbps)
            HISTORY_TX.append(tx_mbps)
            STATE["network"]["history_rx"] = list(HISTORY_RX)
            STATE["network"]["history_tx"] = list(HISTORY_TX)
            
        except: pass

        containers = req_docker('/containers/json?all=1') or []
        projects = {}
        for c in containers:
            labels = c.get('Labels', {})
            proj = labels.get('com.docker.compose.project', 'Standalone').upper()
            if proj not in projects: projects[proj] = {"stats": {"cpu": 0, "ram": 0, "net_rx": 0, "net_tx": 0, "io_rw": 0}, "banco": [], "front": [], "back": []}
            
            name = c['Names'][0].lstrip('/')
            state = c['State']
            ports = [f"{p['PublicPort']}:{p['PrivatePort']}" for p in c.get('Ports', []) if 'PublicPort' in p]
            domains = [v.split("Host(`")[1].split("`)")[0] for k, v in labels.items() if k.startswith('traefik.http.routers.') and '.rule' in k and "Host(`" in v]

            c_type = 'back'
            if any(x in c['Image'].lower() for x in ['postgres', 'mysql', 'mariadb', 'redis', 'mongo']): c_type = 'banco'
            elif any(x in c['Image'].lower() for x in ['frontend', 'ui', 'viewer', 'web', 'nginx', 'apache', 'portal']): c_type = 'front'

            cpu = 0; ram = 0; n_rx = 0; n_tx = 0; blk_io = 0
            if state == 'running':
                stats = req_docker(f"/containers/{c['Id']}/stats?stream=false")
                if stats:
                    try:
                        sys_d = stats['cpu_stats']['system_cpu_usage'] - stats.get('precpu_stats', {}).get('system_cpu_usage', 0)
                        cpu_d = stats['cpu_stats']['cpu_usage']['total_usage'] - stats.get('precpu_stats', {}).get('cpu_usage', {}).get('total_usage', 0)
                        if sys_d > 0 and cpu_d > 0: cpu = (cpu_d / sys_d) * stats['cpu_stats'].get('online_cpus', 1) * 100
                        ram = max(0, stats['memory_stats'].get('usage', 0) - stats['memory_stats'].get('stats', {}).get('inactive_file', 0))
                        for net in stats.get('networks', {}).values(): n_rx += net.get('rx_bytes', 0); n_tx += net.get('tx_bytes', 0)
                        for io in stats.get('blkio_stats', {}).get('io_service_bytes_recursive', []): blk_io += io.get('value', 0)
                    except: pass
            
            projects[proj]["stats"]["cpu"] += cpu
            projects[proj]["stats"]["ram"] += ram
            projects[proj]["stats"]["net_rx"] += n_rx
            projects[proj]["stats"]["net_tx"] += n_tx
            projects[proj]["stats"]["io_rw"] += blk_io
            projects[proj][c_type].append({"name": name, "image": c['Image'], "state": state, "ports": ports, "domains": domains, "cpu": round(cpu, 1), "ram": ram})

        STATE["projects"] = projects
        time.sleep(2)

class APIHandler(BaseHTTPRequestHandler):
    def check_auth(self):
        if "Cookie" in self.headers:
            C = cookies.SimpleCookie(self.headers["Cookie"])
            if "docops_session" in C and C["docops_session"].value in SESSIONS: return True
        return False

    def do_GET(self):
        if self.path == '/api/data':
            if not self.check_auth():
                self.send_response(401)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(STATE).encode('utf-8'))
        elif self.path == '/api/logout':
            if "Cookie" in self.headers:
                C = cookies.SimpleCookie(self.headers["Cookie"])
                if "docops_session" in C and C["docops_session"].value in SESSIONS:
                    SESSIONS.remove(C["docops_session"].value)
            self.send_response(302)
            self.send_header('Set-Cookie', 'docops_session=; HttpOnly; Path=/; Max-Age=0')
            self.send_header('Location', '/login.html')
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/login':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode()
            data = urllib.parse.parse_qs(body)
            u = data.get('user', [''])[0]
            p = data.get('pass', [''])[0]
            
            if u == USER and p == PASS:
                token = secrets.token_hex(32)
                SESSIONS.add(token)
                self.send_response(302)
                self.send_header('Set-Cookie', f'docops_session={token}; HttpOnly; Path=/')
                self.send_header('Location', '/')
                self.end_headers()
            else:
                self.send_response(302)
                self.send_header('Location', '/login.html')
                self.end_headers()

    def log_message(self, format, *args): pass

if __name__ == '__main__':
    threading.Thread(target=monitor_loop, daemon=True).start()
    HTTPServer(('127.0.0.1', 8001), APIHandler).serve_forever()