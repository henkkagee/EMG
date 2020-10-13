from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5 import QtCore
from app import EMGApp
import sys
import traceback

def excepthook(type_, value, traceback_):
    traceback.print_exception(type_, value, traceback_)
    QtCore.qFatal('')
sys.excepthook = excepthook


class MainWindow(QMainWindow):
    
    def __init__(self, widget):
        QMainWindow.__init__(self)
        self.setWindowTitle("EMG feedback")
        
        self.setCentralWidget(widget)
        
def main():
    # Create the Qt Application
    app = QApplication(sys.argv)
    width, height = 1800, 800
    widget = EMGApp(width, height)
    
    window = MainWindow(widget)
    window.resize(width, height)
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()