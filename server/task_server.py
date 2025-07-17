import json, ssl, socket, threading, bcrypt, os, uuid

HOST, PORT = '0.0.0.0', 65432
CERT, KEY = 'server.crt', 'server.key'
STORE = 'storage.json'
LOCK = threading.Lock()
WELCOME = """\
Welcome to the Task Server!
 HELP for commands:
 SIGNUP <user> <pwd>           create account
 LOGIN  <user> <pwd>           login
 NEWLIST <name> <code>         create new shared list
 JOINLIST <code>               join an existing list
 USELIST <code>                switch to that list
 MYLISTS                       show your lists
 ADD "task text"               add task to current list
 DONE <id> / DELETE <id>       mark done / remove
 LIST                          show tasks of current list
 LOGOUT                        logout
 DELETEACC <pwd>               delete account"""


def load_data():
    if os.path.exists(STORE):
        with open(STORE) as f:
            d = json.load(f)
    else:
        d = {"users": {}, "tasks": []}         
    if "lists" not in d:
        d["lists"] = {
            "default": {
                "name": "default",
                "owner": None,
                "members": [],
                "tasks": d.pop("tasks", [])
            }
        }
    return d

def get_list(code):
    return data['lists'].get(code)

def save_data(data):
    with open(STORE, 'w') as f:
        json.dump(data, f, indent=2)

def list_exists(code):
    return code in data["lists"]

def is_member(code, user):
    lst = data["lists"][code]
    return user in lst["members"] or lst["owner"] == user


data = load_data()

def handle(client, addr):
    def send(msg, end='\n'):
        client.write((msg + "\n\n").encode())
        client.flush()

    send(WELCOME)
    user = None
    current_list = None
    pending_delete = False
    delete_password = ""
    try:
        for line in client:
            #print(f"DEBUG raw -> {line!r}")
            cmd, *args = line.decode().strip().split(' ', 1)
            #print(f"DEBUG cmd={cmd} arg={args}")
            arg = args[0] if args else ''
            cmd = cmd.upper()
            if pending_delete:
                if cmd == 'Y':
                    if not bcrypt.checkpw(delete_password.encode(), data['users'][user].encode()):
                        send("Invalid password, account not deleted.")
                        pending_delete = False
                        continue
                    with LOCK:
                        del data['users'][user]
                        for lst in data['lists'].values():
                            lst['tasks'] = [t for t in lst['tasks'] if t['user'] != user]
                        save_data(data)
                    send("Account deleted successfully. Bye!")
                    user = None
                    pending_delete = False
                    delete_password = ""
                    continue
                elif cmd == 'N':
                    pending_delete = False
                    send("Account deletion cancelled.")
                    continue
                else:
                    send("Please confirm deletion with Y or N.")
                    continue
            if cmd == 'HELP':
                send(WELCOME)
            if cmd == 'SIGNUP':
                parts = arg.split()
                if len(parts) != 2:
                    send("Usage: SIGNUP <username> <password>")
                    continue
                username, password = parts
                with LOCK:
                    if username in data['users']:
                        send("Username already exists.")
                    else:
                        hashpw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                        data['users'][username] = hashpw
                        save_data(data)
                        send("User created successfully.")
            elif cmd == 'LOGIN':
                parts = arg.split()
                if len(parts) != 2:
                    send("Usage: LOGIN <username> <password>")
                    continue
                username, password = parts
                with LOCK:
                    hashpw = data['users'].get(username)
                    if hashpw and bcrypt.checkpw(password.encode(), hashpw.encode()):
                        user = username
                        send(f"Welcome {username}!")
                    else:
                        send("Invalid username or password.")
            elif cmd == 'ADD'and user:
                if not current_list:
                    send("No list selected. Use USELIST <code> to select a list.")
                    continue
                text = arg.strip('"')
                if not text:
                    send("Usage: ADD \"task text\"")
                    continue
                tasks = data['lists'][current_list]['tasks']

                with LOCK:
                    task_id = str(uuid.uuid4())[:8]
                    tasks.append({"id": task_id, "text": arg.strip('"'), "done": False, "user": user})
                    save_data(data)
                send(f"Task added with ID {task_id}.")
            elif cmd == 'DONE' and user:
                if not current_list:
                    send("No list selected. Use USELIST <code> to select a list.")
                    continue
                tid = arg.strip()
                if not tid:
                    send("Usage: DONE <id>")
                    continue
                tasks = data['lists'][current_list]['tasks']
                updated = False
                with LOCK:
                    for t in tasks:
                        if t['id'] == tid:
                            if t['done']:
                                send(f"Task {tid} is already done.")
                            else:
                                t['done'] = True
                                save_data(data)
                                send(f"Task {tid} marked as done.")
                            updated = True
                            break
                if not updated:
                    send(f"Task {tid} not found.")
            elif cmd == 'DELETE' and user:
                if not current_list:
                    send("No list selected. Use USELIST <code> to select a list.")
                    continue
                tid = arg.strip()
                if not tid:
                    send("Usage: DELETE <id>")
                    continue
                tasks = data['lists'][current_list]['tasks']
                with LOCK:
                    data['lists'][current_list]['tasks'] = [t for t in tasks if t['id'] != arg]
                    save_data(data)
                send(f"Task {arg} deleted.")
            elif cmd == 'LIST' and user:
                if not current_list:
                    send("No list selected. Use USELIST <code> to select a list.")
                    continue
                tasks = data['lists'][current_list]['tasks']
                lines = [
                    f"{t['id']} - [{'x' if t['done'] else ' '}] {t['text']} "
                    f"(User: {t['user']})"
                    for t in tasks
                ]
                send("Tasks:\n" + ("\n".join(lines) if lines else "No tasks found."))
            elif cmd == 'LOGOUT':
                user = None
                current_list = None
                send("Logged out successfully.")
            elif cmd == 'DELETEACC' and user:
                parts = arg.split()
                if len(parts) != 1:
                    send("Usage: DELETEACC <password>")
                    continue
                password = parts[0]
                with LOCK:
                    hashpw = data['users'].get(user)
                    if not bcrypt.checkpw(password.encode(), hashpw.encode()):
                        send("Invalid password, account not deleted.")
                        continue
                    pending_delete = True
                    delete_password = password
                    send("Are you sure you want to delete your account? (Y/N)")
            elif cmd == 'NEWLIST' and user:
                try:
                    name, code = arg.split()
                except ValueError:
                    send("Usage: NEWLIST <name> <code>")
                    continue
                if list_exists(code):
                    send(f"List with code {code} already exists.")
                    continue
                with LOCK:
                    data['lists'][code] = {
                        "name": name,
                        "owner": user,
                        "members": [user],
                        "tasks": []
                    }
                    save_data(data)
                send(f"List '{name}' created with code {code}.")
            elif cmd == 'JOINLIST' and user:
                code = arg.strip()
                if not code:
                    send("Usage: JOINLIST <code>")
                    continue
                if not list_exists(code):
                    send(f"List with code {code} not found.")
                    continue
                if is_member(code, user):
                    send(f"You are already a member.")
                    continue
                with LOCK:
                    data['lists'][code]['members'].append(user)
                    save_data(data)
                send(f"Joined list {code}. Use USELIST {code} to switch.")
            elif cmd == 'USELIST' and user:
                code = arg.strip()
                if not code:
                    send("Usage: USELIST <code>")
                    continue
                if not list_exists(code):
                    send(f"List with code {code} not found.")
                    continue
                if not is_member(code, user):
                    send(f"You are not a member of list {code}.")
                    continue
                current_list = code
                send(f"Now using list '{data['lists'][code]['name']}' ({code}).")
            elif cmd == 'MYLISTS' and user:
                lines = []
                for code, lst in data['lists'].items():
                    if is_member(code, user):
                        mark = "*" if code == current_list else " "
                        lines.append(f"{mark} ({code}) {lst['name']}")
                send("Your lists:\n" + "\n".join(lines) if lines else "No lists found.")
            elif not user:
                send("LOGIN first.")
            else:
                send("Unknown command. Type HELP to see available commands.")
    except Exception as e:
        print("Closed", addr, "due to", e)
    finally:
        client.close()
        if user:
            print(f"User {user} disconnected from {addr}.")
        else:
            print(f"Client {addr} disconnected.")

context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(CERT, KEY)

with socket.create_server((HOST, PORT)) as srv:
    print(f"Server running on {HOST}:{PORT}")
    with context.wrap_socket(srv, server_side=True) as tls_srv:
        while True:
            conn, addr = tls_srv.accept()
            print(f"Client {addr} connected.")
            threading.Thread(target=handle, args=(conn.makefile('rwb'), addr), daemon=True).start()