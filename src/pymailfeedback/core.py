import os
import sys
import time
import json
import socket
import smtplib
import platform
import traceback
import getpass
import inspect
from pathlib import Path
from functools import wraps
from email.message import EmailMessage

 #TODO:
 # test loading variable from env
 # test verbose 1 and 2 in multifile
 # test sendbacon
 # test in pytorch with multiple workers
 # test multiple addreesses
 # write readme
 # create repo
 # publication

# Global configuration variables, lazily populated by _ensure_config_loaded()
_SENDER_EMAIL = ""
_SENDER_PASSWORD = ""
_SMTP_SERVER = "smtp.gmail.com"
_SMTP_PORT = 465
_DEFAULT_RECIPIENT = ""
_DEFAULT_VERBOSE = 0
_CONFIG_LOADED = False  # NEW: tracks whether config has been loaded yet

_TIC_TIMES = []
_BEACON_NEXT_TIME = None

_TIC_TIMES = []
_BEACON_NEXT_TIME = None

_CONFIG_PATH_HOME = Path.home() / ".pymailfeedback.json"
_CONFIG_PATH_CWD = Path.cwd() / ".pymailfeedback.json"

_CONFIG_FACSIMILE = """{
    "sender_email": "your_email@gmail.com",
    "sender_password": "your_app_password",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 465,
    "default_recipient": "recipient@example.com",
    "default_verbose": 0
}"""


# ---------------------------------------------------------------------------
# CONFIGURATION HANDLING
# ---------------------------------------------------------------------------

def _interactive_setup():
    """Guides the user interactively to create a configuration file."""
    print("\n" + "=" * 50)
    print(" pymailfeedback - First Time Setup")
    print("=" * 50)
    print("Let's create a configuration file now.")
    print(f"It will be saved to: {_CONFIG_PATH_HOME.resolve()}\n")

    try:
        email = input("Sender Email (e.g., myemail@gmail.com): ").strip()
        password = input("Sender Password (e.g., App Password): ").strip()
        server = input("SMTP Server [press Enter for 'smtp.gmail.com']: ").strip() or "smtp.gmail.com"
        port_str = input("SMTP Port [press Enter for '465']: ").strip() or "465"
        port = int(port_str)
        default_recipient = input("Default recipient email (optional, press Enter to skip): ").strip()
        verbose_str = input("Default verbose level [0, 1, 2] (press Enter for '0'): ").strip() or "0"
        default_verbose = int(verbose_str)
    except (KeyboardInterrupt, EOFError):
        print("\nSetup cancelled by user.", file=sys.stderr)
        return False

    if not email or not password:
        print("\nError: Email and password are required. Setup aborted.", file=sys.stderr)
        return False

    config_data = {
        "sender_email": email,
        "sender_password": password,
        "smtp_server": server,
        "smtp_port": port,
        "default_recipient": default_recipient,
        "default_verbose": default_verbose,
    }

    try:
        with open(_CONFIG_PATH_HOME, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
        print(f"\nSuccess! Configuration saved to: {_CONFIG_PATH_HOME.resolve()}")
        print("=" * 50 + "\n")

        global _SENDER_EMAIL, _SENDER_PASSWORD, _SMTP_SERVER, _SMTP_PORT, _DEFAULT_RECIPIENT, _DEFAULT_VERBOSE
        _SENDER_EMAIL = email
        _SENDER_PASSWORD = password
        _SMTP_SERVER = server
        _SMTP_PORT = port
        _DEFAULT_RECIPIENT = default_recipient
        _DEFAULT_VERBOSE = default_verbose
        return True
    except Exception as e:
        print(f"\nFailed to save configuration: {e}", file=sys.stderr)
        return False


def _raise_missing_config_error():
    """Raises a descriptive error explaining how to fix a missing configuration."""
    raise RuntimeError(
        "\n\nNo pymailfeedback configuration found.\n"
        "You have two options:\n\n"
        "1) Create the file manually at one of these locations:\n"
        f"   - {_CONFIG_PATH_CWD.resolve()}\n"
        f"   - {_CONFIG_PATH_HOME.resolve()}\n\n"
        "   Using this template:\n"
        f"{_CONFIG_FACSIMILE}\n\n"
        "2) Run the interactive setup wizard:\n"
        "   python -c \"from pymailfeedback.core import _interactive_setup; _interactive_setup()\"\n"
        "   (or use the 'pymailfeedback-init' command if installed as a CLI entry point)\n"
    )


def _load_config():
    """
    Loads SMTP configuration. Order of precedence:
    1. Environment variables
    2. Local directory JSON file (./.pymailfeedback.json)
    3. User home directory JSON file (~/.pymailfeedback.json)
    4. Interactive setup (only in an interactive terminal)
    If nothing is found, raises a RuntimeError explaining how to fix it.
    """
    global _SENDER_EMAIL, _SENDER_PASSWORD, _SMTP_SERVER, _SMTP_PORT, _DEFAULT_RECIPIENT, _DEFAULT_VERBOSE

    env_email = os.getenv("PYMAIL_SENDER_EMAIL")
    env_pwd = os.getenv("PYMAIL_SENDER_PASSWORD")
    if env_email and env_pwd:
        _SENDER_EMAIL = env_email
        _SENDER_PASSWORD = env_pwd
        _SMTP_SERVER = os.getenv("PYMAIL_SMTP_SERVER", _SMTP_SERVER)
        _SMTP_PORT = int(os.getenv("PYMAIL_SMTP_PORT", _SMTP_PORT))
        _DEFAULT_RECIPIENT = os.getenv("PYMAIL_DEFAULT_RECIPIENT", _DEFAULT_RECIPIENT)
        _DEFAULT_VERBOSE = int(os.getenv("PYMAIL_DEFAULT_VERBOSE", _DEFAULT_VERBOSE))
        return

    for config_path in (_CONFIG_PATH_CWD, _CONFIG_PATH_HOME):
        if config_path.is_file():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    _SENDER_EMAIL = config.get("sender_email", _SENDER_EMAIL)
                    _SENDER_PASSWORD = config.get("sender_password", _SENDER_PASSWORD)
                    _SMTP_SERVER = config.get("smtp_server", _SMTP_SERVER)
                    _SMTP_PORT = config.get("smtp_port", _SMTP_PORT)
                    _DEFAULT_RECIPIENT = config.get("default_recipient", _DEFAULT_RECIPIENT)
                    _DEFAULT_VERBOSE = config.get("default_verbose", _DEFAULT_VERBOSE)
                return
            except Exception as e:
                print(f"Warning: Failed to read config file {config_path}: {e}", file=sys.stderr)

    if sys.stdin.isatty() and sys.stdout.isatty():
        response = input("[pymailfeedback] No email configuration found. Setup now? (y/n): ").strip().lower()
        if response == 'y' and _interactive_setup():
            return

    _raise_missing_config_error()


def _ensure_config_loaded():
    """
    Lazily loads the configuration on first actual use.
    This avoids raising an error just because the module was imported
    (e.g. to call _interactive_setup() manually).
    """
    global _CONFIG_LOADED
    if not _CONFIG_LOADED:
        _load_config()
        _CONFIG_LOADED = True

def _resolve_recipient(to_addresses):
    """Resolves the recipient list, falling back to the default recipient if none provided."""
    if to_addresses:
        return to_addresses
    if _DEFAULT_RECIPIENT:
        return _DEFAULT_RECIPIENT
    raise ValueError(
        "No recipient specified and no default_recipient configured. "
        "Pass a recipient explicitly or set 'default_recipient' in your .pymailfeedback.json."
    )


# ---------------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------------

def _plural(n):
    return "" if n == 1 else "s"


def readsec(t):
    """Converts seconds into a readable format (DAY:HH:MM:SS.mmm)."""
    days = int(t // (24 * 3600))
    t %= (24 * 3600)
    hours = int(t // 3600)
    t %= 3600
    mins = int(t // 60)
    sec = t % 60

    time_string = ""
    if days > 0:
        time_string += f"{days} day{_plural(days)}, "
    if hours > 0:
        time_string += f"{hours} hour{_plural(hours)}, "
    if mins > 0:
        time_string += f"{mins} min and "

    time_string += f"{sec:.3f} s"
    return time_string


def _shutdown_computer():
    """Executes the appropriate system shutdown command based on the OS."""
    system = platform.system()
    try:
        if system == "Windows":
            os.system("shutdown /s /t 0")
        elif system == "Linux":
            os.system("sudo shutdown -h now")
        elif system == "Darwin":
            os.system("""osascript -e 'tell app "System Events" to shut down'""")
        else:
            print(f"Shutdown not supported for {system}.", file=sys.stderr)
    except Exception as e:
        print(f"Error during shutdown: {e}", file=sys.stderr)


def _handle_shutdown(shutdown, shutdown_delay):
    """Shuts down the machine after shutdown_delay seconds if shutdown is True."""
    if shutdown:
        print(f"[pymailfeedback] System will shut down in {shutdown_delay} seconds...")
        time.sleep(shutdown_delay)
        _shutdown_computer()


# ---------------------------------------------------------------------------
# HTML EMAIL BUILDER
# ---------------------------------------------------------------------------

def _build_html_body(title_color, content_lines, footer_lines):
    """Builds a styled HTML email body (no leading title, subject already states it)."""
    content_html = "".join(f"<p style='margin:4px 0;'>{line}</p>" for line in content_lines)
    footer_html = "".join(f"<p style='margin:2px 0; color:#888; font-size:12px;'>{line}</p>" for line in footer_lines)

    html = f"""\
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <div style="border-left: 4px solid {title_color}; padding-left: 12px; margin: 12px 0;">
        {content_html}
    </div>
    <hr style="border:none; border-top:1px solid #ddd; margin: 16px 0;">
    <div>
        {footer_html}
        <p style="margin:2px 0; font-size:12px; color:#aaa;">Generated automatically by <b>pymailfeedback</b></p>
    </div>
</body>
</html>
"""
    return html


def _build_plain_body(content_lines, footer_lines):
    """Builds the plain-text fallback body (no leading title)."""
    lines = content_lines + [""] + footer_lines + ["", "Generated automatically by pymailfeedback"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CORE MAIL FUNCTIONS
# ---------------------------------------------------------------------------

def sendmsg(to_addresses=None, subject="", message="", attachments=None, html_body=None):
    """Sends an email with a subject, body message, and optional attachments."""
    _ensure_config_loaded()
    to_addresses = _resolve_recipient(to_addresses)

    if not _SENDER_EMAIL or not _SENDER_PASSWORD:
        print("Warning: Email credentials not configured. Skipping email.", file=sys.stderr)
        return

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = _SENDER_EMAIL
    msg['To'] = ", ".join(to_addresses) if isinstance(to_addresses, list) else to_addresses
    msg.set_content(message)

    if html_body:
        msg.add_alternative(html_body, subtype='html')

    if attachments:
        if isinstance(attachments, str):
            attachments = [attachments]
        for filepath in attachments:
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    file_data = f.read()
                    file_name = os.path.basename(filepath)
                msg.add_attachment(file_data, maintype='application',
                                   subtype='octet-stream', filename=file_name)

    try:
        if _SMTP_PORT == 465:
            with smtplib.SMTP_SSL(_SMTP_SERVER, _SMTP_PORT) as server:
                server.login(_SENDER_EMAIL, _SENDER_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(_SMTP_SERVER, _SMTP_PORT) as server:
                server.starttls()
                server.login(_SENDER_EMAIL, _SENDER_PASSWORD)
                server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email: {e}", file=sys.stderr)


def sendstatus(to_addresses=None, verbose=None, shutdown=False, shutdown_delay=0):
    """
    Decorator to send the execution status via email.
    Wraps the decorated function in a try/except block.

    verbose = None: uses the default_verbose from configuration (falls back to 0)
    verbose = 0: No attachments
    verbose = 1: Attaches the file that caused the error
    verbose = 2: Attaches the entire error stack trace files

    shutdown: if True, shuts down the machine after the run completes (success or failure).
    shutdown_delay: seconds to wait before shutting down the machine.
    """
    _ensure_config_loaded()
    if verbose is None:
        verbose = _DEFAULT_VERBOSE

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            global _TIC_TIMES
            start_time = time.time()
            _TIC_TIMES.append(start_time)

            try:
                username = getpass.getuser()
                computername = socket.gethostname()
            except Exception:
                username, computername = "Unknown", "Unknown"

            func_name = func.__name__
            try:
                func_file = inspect.getsourcefile(func)
                file_label = os.path.basename(func_file) if func_file else "unknown_file"
            except TypeError:
                func_file = "Unknown path"
                file_label = "unknown_file"

            exit_status = 0
            error_traceback = ""
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                exit_status = 1
                error_traceback = traceback.format_exc()
                raise
            finally:
                elapsed = time.time() - start_time
                elapsed_str = readsec(elapsed)

                if exit_status == 1:
                    subject = f"[{file_label}] {func_name} — ❌ FAILURE"
                    title_color = "#d32f2f"
                    content_lines = [
                        f"<b>Dear {username},</b>",
                        f"Function <b>{func_name}</b> in <b>{file_label}</b> has failed with the following error:",
                        f"<pre style='color:#d32f2f; font-weight:bold; background:#fdecea; padding:8px; border-radius:4px; white-space:pre-wrap;'>{error_traceback}</pre>",
                    ]
                    plain_content = [
                        f"Dear {username},",
                        f"Function {func_name} in {file_label} failed with the following error:",
                        error_traceback,
                    ]
                else:
                    subject = f"[{file_label}] {func_name} — ✅ SUCCESS"
                    title_color = "#2e7d32"
                    content_lines = [
                        f"<b>Dear {username},</b>",
                        f"Function <b>{func_name}</b> in <b>{file_label}</b> completed successfully.",
                    ]
                    plain_content = [
                        f"Dear {username},",
                        f"Function {func_name} in {file_label} completed successfully.",
                    ]

                footer_lines = [
                    f"Machine: {computername}",
                    f"Full path: {func_file}",
                    f"Elapsed time: {elapsed_str}",
                    f"Verbose level: {verbose}",
                ]

                html_body = _build_html_body(title_color, content_lines, footer_lines)
                plain_body = _build_plain_body(plain_content, footer_lines)

                attachments = []
                if exit_status == 1 and verbose > 0:
                    _, _, tb = sys.exc_info()
                    extracted_tb = traceback.extract_tb(tb)

                    if verbose >= 1 and func_file and os.path.exists(func_file):
                        attachments.append(func_file)

                    if verbose >= 2:
                        for frame in extracted_tb:
                            if os.path.exists(frame.filename) and frame.filename not in attachments:
                                attachments.append(frame.filename)

                sendmsg(to_addresses, subject, plain_body, attachments, html_body=html_body)

                _handle_shutdown(shutdown, shutdown_delay)

        return wrapper
    return decorator


def sendbeacon(to_addresses=None, delta_time_minutes=60):
    """Sends a periodic 'alive' email if delta_time_minutes has passed since the last beacon."""
    _ensure_config_loaded()
    global _BEACON_NEXT_TIME
    current_time = time.time()

    if _BEACON_NEXT_TIME is None:
        _BEACON_NEXT_TIME = current_time + (delta_time_minutes * 60)
        return

    if current_time >= _BEACON_NEXT_TIME:
        to_addresses = _resolve_recipient(to_addresses)
        try:
            computername = socket.gethostname()
        except Exception:
            computername = "Unknown"

        subject = f"[{computername}] beacon — 🟢 Still Running"
        content_lines = [
            "<b>So far so good!</b>",
            f"Beacon signal generated every {readsec(delta_time_minutes * 60)}."
        ]
        html_body = _build_html_body("#2e7d32", content_lines, [f"Machine: {computername}"])
        plain_body = _build_plain_body(
            ["So far so good!", f"Beacon signal generated every {readsec(delta_time_minutes * 60)}"],
            [f"Machine: {computername}"]
        )

        sendmsg(to_addresses, subject, plain_body, html_body=html_body)

        _BEACON_NEXT_TIME = current_time + (delta_time_minutes * 60)