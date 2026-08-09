# pymailfeedback

**Never wonder if your long-running script finished or crashed.**

**pymailfeedback** is Python decorator that emails you the moment your script finishes, whether it succeeded or crashed. Get instant notifications with full tracebacks on failure and optional file attachments.

<div>
  <img src="https://raw.githubusercontent.com/dmascali/pymailfeedback/master/assets/example_success_msg.png" alt="Example Success" width="75%" />
</div>
<br />
<div>
  <img src="https://raw.githubusercontent.com/dmascali/pymailfeedback/master/assets/example_failure_msg.png" alt="Example Failure" width="75%" />
</div>

This project is a Python port of [MatlabMailFeedback](https://github.com/dmascali/MatlabMailFeedback). `pymailfeedback` reproduces the same core idea — wrapping a script/function in a try/except block to report its exit status by email.

## Installation

```bash
pip install pymailfeedback
```

---

## Quick start

```python
from pymailfeedback import sendstatus

@sendstatus("recipient@example.com")
def train_model():
    # your long-running code here
    ...

train_model()
```

That's it. If `train_model()` finishes normally, you get a ✅ SUCCESS email. If it raises an exception, you get a ❌ FAILURE email with the full traceback — and the exception is still re-raised, so your program behaves exactly as if the decorator wasn't there.

---

## `sendstatus` — the core feature

`sendstatus` is a **decorator**. Place it directly above the function or script entry point you want to monitor:

```python
@sendstatus(to_addresses=None, verbose=None, shutdown=False, shutdown_delay=60)
def my_function(...):
    ...
```

| Parameter | Description                                                                                                                                                                                                                        |
|---|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `to_addresses` | Recipient email address, or a list of addresses. If omitted, the `default_recipient` from your configuration is used.                                                                                                              |
| `verbose` | Controls attachments sent on failure: `0` = no attachment, `1` = attach the file that caused the error, `2` = attach the entire traceback's file stack. If omitted, uses `default_verbose` from your configuration (default: `0`). |
| `shutdown` | If `True`, shuts down the machine after the run completes, regardless of success or failure.                                                                                                                                       |
| `shutdown_delay` | Seconds to wait before shutting down (default 60 seconds).                                                                                                                                                                         |

## Configuration

`pymailfeedback` needs SMTP credentials (sender email + password) to actually send mail.
There are three ways to configure it, checked in this order (note: you probably want to go with option 2 or 3):

### 1. Environment variables

| Variable | Maps to                                          | Required |
|---|--------------------------------------------------|---|
| `PYMAIL_SENDER_EMAIL` | sender email                                     | Yes |
| `PYMAIL_SENDER_PASSWORD` | sender password (e.g. a Yahoo Mail App Password) | Yes |
| `PYMAIL_SMTP_SERVER` | SMTP server                                      | No (default: `smtp.mail.yahoo.com`) |
| `PYMAIL_SMTP_PORT` | SMTP port                                        | No (default: `465`) |
| `PYMAIL_DEFAULT_RECIPIENT` | default recipient if none is passed explicitly   | No |
| `PYMAIL_DEFAULT_VERBOSE` | default verbose level                            | No (default: `0`) |

```bash
export PYMAIL_SENDER_EMAIL="you@gmail.com"
export PYMAIL_SENDER_PASSWORD="your_app_password"
export PYMAIL_DEFAULT_RECIPIENT="you@example.com"
python train.py
```

If both `PYMAIL_SENDER_EMAIL` and `PYMAIL_SENDER_PASSWORD` are set, environment variables take priority over any JSON config file.

### 2. A JSON configuration file (recommended)

Create a file named `.pymailfeedback.json`, either in your current working directory or in your home directory (checked in that order):

```json
{
    "sender_email": "you@gmail.com",
    "sender_password": "your_app_password",
    "smtp_server": "smtp.mail.yahoo.com",
    "smtp_port": 465,
    "default_recipient": "you@example.com",
    "default_verbose": 0
}
```

### 3. Interactive setup wizard

If no environment variables or config file are found, and you're running in an interactive terminal, `pymailfeedback` will offer to walk you through creating `~/.pymailfeedback.json` on the spot. You can also trigger this manually at any time:

```bash
python -c "from pymailfeedback.core import _interactive_setup; _interactive_setup()"
```

It will prompt you for the sender email, password, SMTP server/port, default recipient, and default verbose level, then print exactly where the file was saved.

### No configuration found?

If configuration is missing and no interactive terminal is available (e.g. inside a script run non-interactively), `pymailfeedback` raises a `RuntimeError` with a ready-to-copy JSON template and the command to launch the setup wizard.

---

## A note on security: don't use your personal email

Whichever configuration method you choose, the sender password ends up stored in plain text somewhere on your machine — in a JSON file, in an environment variable, or in your shell history. That's fine for a throwaway or dedicated address, but it is **not wise** to use your personal, everyday email account for this. If that password (or app password) ever leaks — through a shared server, a committed config file, a misconfigured Docker image — you don't want it to be the same account tied to your personal identity, contacts, and other services.

**Best practice: create a dedicated, "burner" email account used only for sending these notifications.** [Yahoo Mail](https://mail.yahoo.com) is a good, free choice for this. Once created, don't use its regular password in `pymailfeedback` — generate a dedicated **App Password** instead, which can be revoked independently at any time without affecting the account's main login:

1. Sign in to your new Yahoo account and go to **Account settings**.
2. Open **External Connections** (sometimes shown as "App passwords" depending on the region/UI).
3. Select **Create app password** (a generic label like "python" or "pymailfeedback" is fine).
4. Copy the generated password and use it as `sender_password` — either in your `.pymailfeedback.json` file or as the `PYMAIL_SENDER_PASSWORD` environment variable.
5. Set `smtp_server` to `smtp.mail.yahoo.com` when using a Yahoo account.

This way, even in the worst case, the only thing exposed is a disposable notification account, not your main mailbox.

---

## Extra utilities

These are optional helpers built on top of the same configuration system. `sendstatus` is the main feature — the rest are conveniences for specific use cases.

### `sendmsg`

Send a one-off email manually, with an optional attachment:

```python
from pymailfeedback import sendmsg

sendmsg("you@example.com", subject="Checkpoint saved", message="Epoch 50 completed.")
```

If `to_addresses` is omitted, the configured `default_recipient` is used.

### `sendbeacon`

Send a periodic "still alive" email from inside a long-running loop, without spamming your inbox every iteration:

```python
from pymailfeedback import sendbeacon

for epoch in range(1000):
    # ... training code ...
    sendbeacon(delta_time_minutes=60 * 12)  # one email every ~12 hours
```
