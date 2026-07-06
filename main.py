import sys
import traceback
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent / "crash.log"


def log(msg: str):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='milliseconds')}] {msg}\n")
            f.flush()
    except Exception:
        pass


def write_crash(exc_type, exc_value, exc_tb):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 60}\n")
            f.write(f"CRASH @ {datetime.now().isoformat()}\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"Platform: {sys.platform}\n")
            f.write(f"argv: {sys.argv}\n")
            f.write("-" * 60 + "\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
            f.flush()
    except Exception:
        pass


def install_excepthook():
    def handler(t, v, tb):
        write_crash(t, v, tb)
        sys.__excepthook__(t, v, tb)
    sys.excepthook = handler


def main():
    # 清空旧日志
    try:
        LOG_FILE.write_text(f"kagent startup @ {datetime.now().isoformat()}\n", encoding="utf-8")
    except Exception:
        pass

    log(f"Python: {sys.version}")
    log(f"Platform: {sys.platform}")
    log(f"argv: {sys.argv}")
    log(f"cwd: {Path.cwd()}")

    install_excepthook()

    try:
        log("STEP 1: importing dotenv")
        from dotenv import load_dotenv
        load_dotenv()
        log("STEP 2: importing PyQt6.QtWidgets")
        from PyQt6.QtWidgets import QApplication, QMessageBox
        log("STEP 3: importing kagent.config")
        from kagent.config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL
        log(f"  config: model={MODEL}, base_url={OPENAI_BASE_URL}, key={'set' if OPENAI_API_KEY else 'EMPTY'}")
        log("STEP 4: importing kagent.db")
        from kagent import db
        log("STEP 5: init_db")
        db.init_db()
        log("STEP 6: creating QApplication")
        app = QApplication(sys.argv)
        app.setApplicationName("kagent")
        log("STEP 7: importing ChatWindow")
        from kagent.ui.main_window import ChatWindow
        log("STEP 8: creating ChatWindow")
        win = ChatWindow()
        log("STEP 9: showing window")
        win.show()
        log("STEP 10: entering event loop")
        sys.exit(app.exec())
    except Exception:
        traceback.print_exc()
        write_crash(*sys.exc_info())
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            if QApplication.instance() is None:
                QApplication(sys.argv)
            QMessageBox.critical(None, "kagent 启动失败", traceback.format_exc())
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
