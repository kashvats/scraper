"""HTTP proxy with public-address checks and DNS-pinned upstream connections.
Only expose on the internal Docker network. Never publish this port.
"""
import ipaddress
import os
import select
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

SLOTS=threading.BoundedSemaphore(64)

def resolve_public(host,port):
    if port not in (80,443):raise ValueError('Only public HTTP/HTTPS ports are allowed')
    infos=socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)
    if not infos:raise ValueError('No DNS records')
    for info in infos:
        ip=ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:raise ValueError('Private, local and reserved addresses are blocked')
    return infos

def dial(host,port):
    demo=os.getenv('DEMO_UPSTREAM','')
    if host=='demo.harvest.test' and port==80 and demo:
        h,p=demo.rsplit(':',1)
        infos=socket.getaddrinfo(h,int(p),type=socket.SOCK_STREAM)
    else:infos=resolve_public(host,port)
    # Connect to the resolved IP, not the hostname: no second DNS lookup/rebinding window.
    error=None
    for family,kind,proto,_,address in infos:
        s=socket.socket(family,kind,proto);s.settimeout(10)
        try:s.connect(address);return s
        except OSError as exc:error=exc;s.close()
    raise error or ValueError('Connection failed')

class Proxy(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.0'
    def log_message(self,*_):pass
    def setup(self):
        super().setup();self.connection.settimeout(15)
    def handle_one_request(self):
        if not SLOTS.acquire(blocking=False):return
        try:super().handle_one_request()
        finally:SLOTS.release()
    def do_CONNECT(self):
        try:
            p=urlsplit('https://'+self.path)
            if p.username or p.password:raise ValueError('Credentials not permitted')
            upstream=dial(p.hostname,p.port or 443)
        except Exception:self.send_error(403,'Destination blocked or unavailable');return
        with upstream:
            self.send_response(200,'Connection Established');self.end_headers()
            self.wfile.flush();end=time.monotonic()+120;total=0
            sockets=[self.connection,upstream]
            try:
                while time.monotonic()<end and total<50*1024*1024:
                    readable,_,_=select.select(sockets,[],[],10)
                    if not readable:continue
                    for s in readable:
                        data=s.recv(65536)
                        if not data:return
                        total+=len(data)
                        (upstream if s is self.connection else self.connection).sendall(data)
            except (OSError,TimeoutError):pass
    def forward(self):
        try:
            p=urlsplit(self.path)
            if p.scheme!='http' or not p.hostname or p.username or p.password:raise ValueError('Invalid proxy URL')
            if self.headers.get('Transfer-Encoding'):raise ValueError('Chunked request bodies are unsupported')
            length=int(self.headers.get('Content-Length','0'))
            if length<0 or length>5*1024*1024:raise ValueError('Request too large')
            upstream=dial(p.hostname,p.port or 80)
        except Exception:self.send_error(403,'Destination blocked or unavailable');return
        with upstream:
            try:
                target=(p.path or '/')+('?' + p.query if p.query else '')
                headers=[f'{self.command} {target} HTTP/1.0',f'Host: {p.netloc}','Connection: close']
                blocked={'host','connection','proxy-connection','proxy-authorization','transfer-encoding','upgrade'}
                headers += [f'{k}: {v}' for k,v in self.headers.items() if k.lower() not in blocked]
                upstream.sendall(('\r\n'.join(headers)+'\r\n\r\n').encode('latin1'))
                if length:upstream.sendall(self.rfile.read(length))
                total=0;end=time.monotonic()+120
                while total<50*1024*1024 and time.monotonic()<end:
                    data=upstream.recv(65536)
                    if not data:break
                    self.wfile.write(data);total+=len(data)
            except (OSError,TimeoutError):pass
    do_GET=do_HEAD=do_POST=do_PUT=do_PATCH=do_DELETE=do_OPTIONS=forward

if __name__=='__main__':
    server=ThreadingHTTPServer(('0.0.0.0',3128),Proxy)
    server.daemon_threads=True
    server.serve_forever()
