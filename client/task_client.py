import ssl, socket, xml.etree.ElementTree as ET, pathlib, sys

base_dir = pathlib.Path(getattr(sys, "_MEIPASS", pathlib.Path(__file__).parent))
cfg_path = base_dir / "client.config"

# --- ler XML ---
try:
    root  = ET.parse(cfg_path).getroot()
    pairs = {el.attrib['key']: el.attrib['value']
             for el in root.find('appSettings')}
    HOST  = pairs.get("ServerIpAddress", "localhost")
    PORT  = int(pairs.get("ServerPort", 65432))
except Exception:
    print("⚠️  Falha ao ler client.config — usando localhost/65432")
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
