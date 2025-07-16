import ssl, socket

HOST, PORT = "localhost", 65432
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with ctx.wrap_socket(socket.create_connection((HOST, PORT)), server_hostname=HOST) as s:
    f = s.makefile("rwb")

    def read_block():
        while True:
            line = f.readline().decode()
            if not line or line.strip() == "":
                break
            print(line, end="")

    # ------ banner ------
    read_block()          

    while True:
        try:
            cmd = input("> ")
        except EOFError:
            break

        f.write((cmd + "\n").encode())
        f.flush()
        read_block()      
