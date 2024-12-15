import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLineEdit, QPushButton, QLabel,
                             QSpinBox, QMessageBox, QTextEdit, QListWidget,
                             QListWidgetItem, QMenu, QGridLayout, QComboBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import pyttsx3
import random
import queue
import threading
import time


class SpellingGame(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Học Spelling Tiếng Anh")
        self.setMinimumSize(800, 600)

        self.colors = [
            "#FF9999", "#99FF99", "#9999FF",
            "#FFB366", "#66FFB3", "#B366FF",
            "#FF99CC", "#99FFCC", "#CC99FF",
            "#FFE5CC", "#CCE5FF", "#E5CCFF",
            "#FFCC99", "#99CCFF", "#CC99FF",
            "#FFB3B3", "#B3FFB3", "#B3B3FF"
        ]

        # Lưu trữ danh sách giọng đọc
        self.available_voices = []

        self.init_tts_engine()

        self.words = []
        self.current_word_index = 0
        self.auto_play_timer = QTimer()
        self.auto_play_timer.timeout.connect(self.auto_play_word)

        self.speech_queue = queue.Queue()
        self.is_speaking = False

        self.speech_thread = threading.Thread(target=self.process_speech_queue, daemon=True)
        self.speech_thread.start()

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Phần nhập từ vựng
        input_layout = QHBoxLayout()
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Nhập từ vựng và nhấn Enter")
        self.word_input.returnPressed.connect(self.add_words)
        input_layout.addWidget(self.word_input)

        # Danh sách từ vựng
        word_list_label = QLabel("Danh sách từ vựng:")
        self.word_list = QListWidget()
        self.word_list.setMaximumHeight(150)
        self.word_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.word_list.customContextMenuRequested.connect(self.show_context_menu)

        # Phần cài đặt
        settings_layout = QHBoxLayout()

        # Tốc độ đọc
        speed_layout = QHBoxLayout()
        speed_label = QLabel("Tốc độ đọc:")
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(50, 200)
        self.speed_spin.setValue(100)
        self.speed_spin.valueChanged.connect(self.change_speed)
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_spin)

        # Thời gian chờ
        delay_layout = QHBoxLayout()
        delay_label = QLabel("Thời gian chờ (giây):")
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(1, 30)
        self.delay_spin.setValue(10)
        self.delay_spin.valueChanged.connect(self.change_delay)
        delay_layout.addWidget(delay_label)
        delay_layout.addWidget(self.delay_spin)

        # Thêm combobox chọn giọng
        voice_layout = QHBoxLayout()
        voice_label = QLabel("Chọn giọng:")
        self.voice_combo = QComboBox()

        # Thêm các giọng vào combo box
        for voice in self.available_voices:
            self.voice_combo.addItem(voice['name'], voice['id'])

        self.voice_combo.currentIndexChanged.connect(self.change_voice)
        voice_layout.addWidget(voice_label)
        voice_layout.addWidget(self.voice_combo)

        settings_layout.addLayout(speed_layout)
        settings_layout.addSpacing(20)
        settings_layout.addLayout(delay_layout)
        settings_layout.addSpacing(20)
        settings_layout.addLayout(voice_layout)
        settings_layout.addStretch()

        # Nút điều khiển
        control_layout = QHBoxLayout()
        self.start_button = QPushButton("Bắt đầu")
        self.start_button.clicked.connect(self.start_game)
        self.auto_play_button = QPushButton("Tự động đọc")
        self.auto_play_button.clicked.connect(self.toggle_auto_play)
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.auto_play_button)

        # Grid layout cho các nút từ vựng
        self.words_layout = QGridLayout()

        # Thêm các layout vào layout chính
        main_layout.addLayout(input_layout)
        main_layout.addWidget(word_list_label)
        main_layout.addWidget(self.word_list)
        main_layout.addLayout(settings_layout)
        main_layout.addLayout(control_layout)
        main_layout.addLayout(self.words_layout)
        main_layout.addStretch()

    def show_context_menu(self, position):
        menu = QMenu()
        delete_action = menu.addAction("Xóa từ này")
        action = menu.exec(self.word_list.mapToGlobal(position))

        if action == delete_action:
            current_item = self.word_list.currentItem()
            if current_item:
                word = current_item.text()
                self.words.remove(word)
                self.word_list.takeItem(self.word_list.currentRow())

    def add_words(self):
        text = self.word_input.text().strip()
        if text:
            new_words = [word.strip() for word in text.split(',') if word.strip()]
            self.words.extend(new_words)
            self.word_input.clear()

            # Thêm từ mới vào QListWidget
            for word in new_words:
                self.word_list.addItem(word)

    def create_word_button(self, word):
        button = QPushButton(word)
        button.setFont(QFont("Arial", 14))

        base_color = random.choice(self.colors)
        darker_color = self.adjust_color(base_color, -30)

        button.setStyleSheet(f"""
            QPushButton {{
                text-align: center;
                qproperty-alignment: AlignCenter; 
                background-color: {base_color};
                padding: 3px;
                border-radius: 5px;
                border: none;
                min-width: 100px;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background-color: {darker_color};
            }}
            QPushButton:pressed {{
                background-color: #A0A0A0;
            }}
        """)
        button.clicked.connect(lambda: self.queue_word(word))
        return button

    def adjust_color(self, hex_color, factor):
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

        r = max(0, min(255, r + factor))
        g = max(0, min(255, g + factor))
        b = max(0, min(255, b + factor))

        return f"#{r:02x}{g:02x}{b:02x}"

    def start_game(self):
        # Xóa các nút cũ
        for i in reversed(range(self.words_layout.count())):
            self.words_layout.itemAt(i).widget().setParent(None)

        # Thêm các nút vào grid theo 2 cột
        for i, word in enumerate(self.words):
            row = i // 2  # Xác định hàng
            col = i % 2  # Xác định cột (0 hoặc 1)
            button = self.create_word_button(word)
            self.words_layout.addWidget(button, row, col)

    def init_tts_engine(self):
        try:
            self.engine = pyttsx3.init()
            voices = self.engine.getProperty('voices')
            # english_voice = next((voice for voice in voices if 'english' in voice.languages[0].lower()), None)
            # if english_voice:
            #     self.engine.setProperty('voice', english_voice.id)
            # self.engine.setProperty('voice', voices[1].id)

            # Lọc các giọng tiếng Anh và phân loại nam/nữ
            for voice in voices:
                    self.available_voices.append({
                        'id': voice.id,
                        'name': voice.name,
                        'gender': 'Default'
                    })

            # Nếu không tìm thấy giọng nào, sử dụng giọng mặc định
            if not self.available_voices:
                self.available_voices.append({
                    'id': None,
                    'name': "Default Voice",
                    'gender': 'Default'
                })

            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 1.0)
        except Exception as e:
            #QMessageBox.warning(self, "Lỗi", f"Không thể khởi tạo text-to-speech engine: {str(e)}")
            pass

    def process_speech_queue(self):
        while True:
            try:
                word = self.speech_queue.get()
                self.is_speaking = True

                while self.engine._inLoop:
                    time.sleep(0.1)

                temp_engine = pyttsx3.init()
                temp_engine.setProperty('rate', self.engine.getProperty('rate'))
                temp_engine.setProperty('volume', self.engine.getProperty('volume'))
                if hasattr(self.engine, 'voice') and self.engine.voice:
                    temp_engine.setProperty('voice', self.engine.voice.id)

                temp_engine.say(word)
                temp_engine.runAndWait()

                temp_engine.stop()
                del temp_engine

                self.is_speaking = False
                self.speech_queue.task_done()

                time.sleep(0.2)

            except Exception as e:
                print(f"Lỗi khi đọc từ: {str(e)}")
                self.is_speaking = False
                self.speech_queue.task_done()
                continue

    def queue_word(self, word):
        if self.speech_queue.qsize() < 5:
            self.speech_queue.put(word)

    def change_speed(self):
        try:
            rate = self.speed_spin.value()
            self.engine.setProperty('rate', rate * 2)
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể thay đổi tốc độ đọc: {str(e)}")

    def change_delay(self):
        if self.auto_play_timer.isActive():
            self.auto_play_timer.setInterval(self.delay_spin.value() * 1000)

    def toggle_auto_play(self):
        if self.auto_play_timer.isActive():
            self.auto_play_timer.stop()
            self.auto_play_button.setText("Tự động đọc")
        else:
            self.current_word_index = 0
            delay = self.delay_spin.value() * 1000
            self.auto_play_timer.setInterval(delay)
            self.auto_play_timer.start()
            self.auto_play_button.setText("Dừng")

    def auto_play_word(self):
        if self.current_word_index < len(self.words):
            self.queue_word(self.words[self.current_word_index])
            self.current_word_index += 1
        else:
            self.auto_play_timer.stop()
            self.auto_play_button.setText("Tự động đọc")
            self.current_word_index = 0

    def closeEvent(self, event):
        try:
            self.engine.stop()
            event.accept()
        except:
            event.accept()

    def change_voice(self, index):
        """Thay đổi giọng đọc"""
        try:
            voice_id = self.voice_combo.currentData()
            if voice_id:
                self.engine.setProperty('voice', voice_id)
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể thay đổi giọng đọc: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SpellingGame()
    window.show()
    sys.exit(app.exec())