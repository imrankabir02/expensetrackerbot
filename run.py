import threading
from bot import main as bot_main
from web_server import app

def run_bot():
    bot_main()

def run_web_server():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    web_thread = threading.Thread(target=run_web_server)

    bot_thread.start()
    web_thread.start()

    bot_thread.join()
    web_thread.join()
