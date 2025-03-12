# region Imports
# Standard Library
import threading
import subprocess
from os import environ as os_environ
from typing import List, TextIO

# Local
import blockchain.sbchain as sbchain
# endregion

# region Waitress


def start_flask_app_waitress() -> None:
    """
    Starts a Flask application using Waitress as the WSGI server.
    This function initializes a Waitress subprocess to serve the Flask
    application. It also starts separate threads to stream the standard
    output and error output from the Waitress subprocess.
    Global Variables:
        waitress_process: The subprocess running the Waitress server.
    """
    global waitress_process

    def stream_output(pipe: TextIO, prefix: str) -> None:
        """
        Streams output from a given pipe, prefixing each line with a
        specified string.

        Args:
            pipe: The pipe to read the output from.
            prefix: The string to prefix each line of output with.
        """
        # Receive output from the Waitress subprocess
        for line in iter(pipe.readline, ''):
            # print(f"{prefix}: {line}", end="")
            print(f"{line}", end="")
        if hasattr(pipe, 'close'):
            pipe.close()

    print("Starting Flask app with Waitress...")
    program = "waitress-serve"
    app_name = "blockchain.sbchain"
    host = "*"
    # Use the environment variable or default to 8000
    port: str = os_environ.get("PORT", "8080")
    command: List[str] = [
        program,
        f"--listen={host}:{port}",
        f"{app_name}:app"
    ]
    waitress_process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("Flask app started with Waitress.")

    # Start threads to read output from the subprocess
    threading.Thread(
        target=stream_output,
        args=(waitress_process.stdout, "STDOUT"),
        daemon=True
    ).start()
    threading.Thread(
        target=stream_output,
        args=(waitress_process.stderr, "STDERR"),
        daemon=True
    ).start()
# endregion

# region Start flask app


def start_flask_app() -> None:
    """
    Starts the Flask application.

    This function initializes and runs the Flask development server.
    If an exception occurs during the startup, it catches the exception and
    prints an error message.

    Raises:
        Exception: If there is an error running the Flask app.
    """
    # For use with the Flask development server
    print("Starting flask app...")
    try:
        sbchain.app.run(port=5000, debug=True, use_reloader=False)
    except Exception as e:
        error_message: str = f"ERROR: Error running Flask app: {e}"
        raise Exception(error_message)
# endregion

# region Start flask thread


def start_flask_app_thread() -> None:
    print("Starting blockchain flask app thread...")
    try:
        flask_thread = threading.Thread(target=start_flask_app_waitress)
        flask_thread.daemon = True  # Set the thread as a daemon thread
        flask_thread.start()
        print("Flask app thread started.")
    except Exception as e:
        print(f"ERROR: Error starting Flask app thread: {e}")
# endregion
