# Servidor de Listas de Tarefas Colaborativas (Python 3 + TLS + bcrypt)

Sistema leve em Python que permite a vários usuários:

1. **Gerenciamento Seguro de Contas**  
   * Crie sua conta (`SIGNUP`) e entre (`LOGIN`) – senhas são protegidas com **bcrypt**.  
   * Exclua a conta de forma irreversível (`DELETEACC`).

2. **Múltiplas Listas Compartilhadas**  
   * Gere várias listas com `NEWLIST <nome> <código>`; o **código** funciona como “senha da lista”.  
   * Entre em listas existentes (`JOINLIST`) e alterne entre elas (`USELIST`).  
   * Veja rapidamente todas as listas às quais pertence com `MYLISTS`.

3. **Tarefas em Tempo Real (por lista selecionada)**  
   * `ADD` novas tarefas, marque como concluídas (`DONE`), exclua (`DELETE`) e liste (`LIST`) – cada tarefa recebe um ID único.  
   * Todas as mudanças são persistidas em *JSON* e visíveis instantaneamente para os demais membros.

4. **Comunicação Criptografada**  
   * Todo o tráfego cliente ⇄ servidor passa por **TLS**, garantindo confidencialidade mesmo em redes inseguras.

---

## Índice

1. [Funcionalidades](#funcionalidades)  
2. [Instalação rápida](#instalação-rápida)  
3. [Arquitetura](#arquitetura)  
4. [Protocolo de texto](#protocolo-de-texto)  
5. [Segurança](#segurança)  

---

## ✨ Funcionalidades

| Categoria  | Descrição                                                                                         |
|------------|---------------------------------------------------------------------------------------------------|
| **Conta**  | `SIGNUP`, `LOGIN`, `DELETEACC` (confirmação *Y/N*)                                                 |
| **Listas** | `NEWLIST`, `JOINLIST`, `USELIST`, `MYLISTS`                                                        |
| **Tarefas**| `ADD`, `LIST`, `DONE`, `DELETE`                                                                    |
| **Segurança** | TLS (SSL da stdlib) + senhas `bcrypt`; protocolo texto fácil de debugar                        |
| **Persistência** | Arquivo `storage.json` salvo a cada alteração (usuários, listas, tarefas)                    |

---

## 🚀 Instalação rápida

```bash
git clone https://github.com/erycastro/task_server.git
cd task_server

python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\activate

pip install -r requirements.txt
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
        -keyout server.key -out server.crt -subj "/CN=localhost"

# terminal 1
python task_server.py

# terminal 2
python task_client.py
```
## 🏗️ Arquitetura

```text
┌───────────────┐  TLS  ┌──────────────────┐
│  Cliente CLI  │ ⇄    │  Thread por user │
│ task_client   │      │  sockets + lock  │
└───────────────┘      └──────────────────┘
                            │
                            ▼
                storage.json (users + lists + tasks)
```

## 📝 Protocolo de texto – comandos suportados

```text
# ────────── CONTA ──────────
SIGNUP <usuario> <senha>
LOGIN  <usuario> <senha>
DELETEACC <senha>        ← inicia exclusão (servidor pergunta Y/N)

# ────────── LISTAS ─────────
NEWLIST  "<nome visível>" <código>
JOINLIST <código>
USELIST  <código>
MYLISTS                      ← mostra todas as listas do usuário

# ────────── TAREFAS (na lista ativa) ─────────
ADD    "<descrição da tarefa>"
LIST                          ← lista tarefas da lista atual
DONE   <id>                   ← marca concluída
DELETE <id>                   ← remove
```
## 🔐 Segurança

| Camada | Detalhes |
|--------|----------|
| **Transporte** | Todo o tráfego cliente ⇄ servidor é protegido por **TLS 1.2+** (via módulo `ssl` da stdlib). Para demonstração usamos um certificado autoassinado; em produção basta trocar por um certificado emitido por CA. |
| **Armazenamento** | Senhas nunca ficam em texto puro: são hashadas com **bcrypt** (cost 12) e salt único por usuário. Se o arquivo `storage.json` vazar, a quebra de força bruta continua cara. |
| **Escopo das listas** | Cada lista compartilhada exige um **código** (semelhante a uma chave de convite). O servidor valida se o usuário pertence à lista antes de permitir `USELIST`, `LIST`, `ADD`, etc. |
| **Exclusão de conta** | Processo em duas etapas: `DELETEACC <senha>` → servidor pergunta **Y/N**. Só com resposta correta a conta é removida e todas as tarefas do usuário são apagadas. |
| **Concorrência** | Acesso ao dicionário global acontece dentro de `threading.Lock`, evitando race‑conditions entre múltiplas threads. |




