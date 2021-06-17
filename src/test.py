import datetime as dt
from mbedtls import hashlib
from mbedtls import pk
from mbedtls import x509
import socket
from contextlib import suppress
import multiprocessing as mp

def block(callback, *args, **kwargs):
    while True:
        with suppress(tls.WantReadError, tls.WantWriteError):
            return callback(*args, **kwargs)


now = dt.datetime.utcnow()
ca0_key = pk.RSA()
_ = ca0_key.generate()
ca0_csr = x509.CSR.new(ca0_key, "CN=Trusted CA", hashlib.sha256())
ca0_crt = x509.CRT.selfsign(
     ca0_csr, ca0_key,
     not_before=now, not_after=now + dt.timedelta(days=90),
     serial_number=0x123456,
     basic_constraints=x509.BasicConstraints(True, 1))

ca1_key = pk.ECC()
_ = ca1_key.generate()
ca1_csr = x509.CSR.new(ca1_key, "CN=Intermediate CA", hashlib.sha256())

ca1_crt = ca0_crt.sign(
     ca1_csr, ca0_key, now, now + dt.timedelta(days=90), 0x123456,
     basic_constraints=x509.BasicConstraints(ca=True, max_path_length=3))

ee0_key = pk.ECC()
_ = ee0_key.generate()
ee0_csr = x509.CSR.new(ee0_key, "CN=End Entity", hashlib.sha256())

ee0_crt = ca1_crt.sign(
     ee0_csr, ca1_key, now, now + dt.timedelta(days=90), 0x987654)

from mbedtls import tls
trust_store = tls.TrustStore()
trust_store.add(ca0_crt)

dtls_srv_ctx = tls.ServerContext(tls.DTLSConfiguration(
     trust_store=trust_store,
     certificate_chain=([ee0_crt, ca1_crt], ee0_key),
     validate_certificates=False,
))

dtls_cli_ctx = tls.ClientContext(tls.DTLSConfiguration(
     trust_store=trust_store,
     validate_certificates=True,
))

dtls_srv = dtls_srv_ctx.wrap_socket(
    socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
)

def dtls_server_main_loop(sock):
     """A simple DTLS echo server."""
     conn, addr = sock.accept()
     conn.setcookieparam(addr[0].encode())
     with suppress(tls.HelloVerifyRequest):
        block(conn.do_handshake)
     conn, addr = conn.accept()
     conn.setcookieparam(addr[0].encode())
     block(conn.do_handshake)
     data = conn.recv(4096)
     conn.send(data)


port = 10000
dtls_srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
dtls_srv.bind(("0.0.0.0", port))
runner = mp.Process(target=dtls_server_main_loop, args=(dtls_srv, ))
runner.start()