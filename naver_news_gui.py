"""
네이버 뉴스 검색 크롤러 - PyQt6 GUI
- naver_news_crawler.py의 파싱 로직을 그대로 재사용한다.
- 검색/본문 로딩은 모두 별도 스레드에서 실행해 창이 멈추지 않도록 한다.
"""

import sys
import webbrowser

import requests
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from naver_news_crawler import (
    HEADERS,
    build_search_url,
    fetch_article_body,
    parse_news_list,
    save_to_csv,
    save_to_excel,
)

COLUMNS = [
    ("press", "언론사"),
    ("title", "제목"),
    ("summary", "요약"),
    ("time", "게시시각"),
]


class CrawlWorker(QThread):
    succeeded = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            res = requests.get(build_search_url(self.query), headers=HEADERS, timeout=10)
            res.raise_for_status()
            articles = parse_news_list(res.text)
            self.succeeded.emit(articles)
        except requests.RequestException as e:
            self.failed.emit(str(e))


class ArticleWorker(QThread):
    succeeded = pyqtSignal(str, dict)
    failed = pyqtSignal(str, str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            data = fetch_article_body(self.url)
            self.succeeded.emit(self.url, data)
        except requests.RequestException as e:
            self.failed.emit(self.url, str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("네이버 뉴스 크롤러")
        self.resize(1280, 720)

        self.articles = []
        self.worker = None
        self.article_workers = []  # 실행 중인 ArticleWorker를 붙잡아 두어 도중에 GC되지 않도록 함
        self.article_cache = {}  # url -> {title, date, content}
        self.current_request_url = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 검색창
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("검색어:"))
        self.query_input = QLineEdit("반도체")
        self.query_input.returnPressed.connect(self.start_crawl)
        search_row.addWidget(self.query_input)
        self.search_btn = QPushButton("검색")
        self.search_btn.clicked.connect(self.start_crawl)
        search_row.addWidget(self.search_btn)
        layout.addLayout(search_row)

        # 결과 테이블 + 본문 미리보기
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels([label for _, label in COLUMNS])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.cellClicked.connect(self.show_article_preview)
        self.table.cellDoubleClicked.connect(self.open_selected_link)
        splitter.addWidget(self.table)

        detail_panel = QWidget()
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(8, 0, 0, 0)

        self.detail_title = QLabel("기사를 선택하면 원문이 여기에 표시됩니다.")
        self.detail_title.setWordWrap(True)
        self.detail_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        detail_layout.addWidget(self.detail_title)

        self.detail_meta = QLabel("")
        self.detail_meta.setStyleSheet("color: #666;")
        detail_layout.addWidget(self.detail_meta)

        self.detail_body = QTextBrowser()
        self.detail_body.setOpenExternalLinks(True)
        detail_layout.addWidget(self.detail_body)

        splitter.addWidget(detail_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        # 하단 상태/저장
        bottom_row = QHBoxLayout()
        self.status_label = QLabel("검색어를 입력하고 검색 버튼을 누르세요.")
        bottom_row.addWidget(self.status_label)
        bottom_row.addStretch()
        self.save_btn = QPushButton("파일로 저장")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_file)
        bottom_row.addWidget(self.save_btn)
        layout.addLayout(bottom_row)

    def start_crawl(self):
        query = self.query_input.text().strip()
        if not query:
            QMessageBox.warning(self, "알림", "검색어를 입력해 주세요.")
            return

        self.set_busy(True, f"'{query}' 검색 중...")
        self.worker = CrawlWorker(query)
        self.worker.succeeded.connect(self.on_crawl_succeeded)
        self.worker.failed.connect(self.on_crawl_failed)
        self.worker.finished.connect(lambda: self.set_busy(False))
        self.worker.start()

    def set_busy(self, busy, message=None):
        self.search_btn.setEnabled(not busy)
        self.query_input.setEnabled(not busy)
        if message:
            self.status_label.setText(message)

    def on_crawl_succeeded(self, articles):
        self.articles = articles
        self.article_cache = {}
        self.populate_table(articles)
        self.detail_title.setText("기사를 선택하면 원문이 여기에 표시됩니다.")
        self.detail_meta.setText("")
        self.detail_body.clear()
        self.status_label.setText(f"{len(articles)}건 수집 완료 (행을 클릭하면 원문을 볼 수 있습니다)")
        self.save_btn.setEnabled(bool(articles))

    def on_crawl_failed(self, message):
        self.status_label.setText("검색 실패")
        QMessageBox.critical(self, "오류", f"검색 중 오류가 발생했습니다:\n{message}")

    def populate_table(self, articles):
        self.table.setRowCount(len(articles))
        for row, article in enumerate(articles):
            for col, (key, _) in enumerate(COLUMNS):
                item = QTableWidgetItem(article.get(key, ""))
                item.setToolTip(article.get(key, ""))
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, article.get("original_url", ""))
                self.table.setItem(row, col, item)

    def open_selected_link(self, row, _column):
        item = self.table.item(row, 0)
        if not item:
            return
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            webbrowser.open(url)

    def show_article_preview(self, row, _column):
        if row < 0 or row >= len(self.articles):
            return
        article = self.articles[row]
        url = article.get("naver_url") or article.get("original_url")

        self.detail_title.setText(article.get("title", ""))
        self.detail_meta.setText(f"{article.get('press', '')} · {article.get('time', '')}")

        if not url:
            self.detail_body.setPlainText(article.get("summary", ""))
            return

        cached = self.article_cache.get(url)
        if cached:
            self.detail_body.setPlainText(cached["content"])
            return

        self.current_request_url = url
        self.detail_body.setPlainText("본문을 불러오는 중...")
        worker = ArticleWorker(url)
        worker.succeeded.connect(self.on_article_succeeded)
        worker.failed.connect(self.on_article_failed)
        worker.finished.connect(lambda: self.article_workers.remove(worker))
        self.article_workers.append(worker)
        worker.start()

    def on_article_succeeded(self, url, data):
        self.article_cache[url] = data
        if url == self.current_request_url:
            self.detail_body.setPlainText(data["content"])

    def on_article_failed(self, url, message):
        if url == self.current_request_url:
            self.detail_body.setPlainText(f"본문을 불러오지 못했습니다: {message}")

    def save_file(self):
        if not self.articles:
            return
        default_name = f"naver_news_{self.query_input.text().strip()}"
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "파일로 저장",
            default_name,
            "Excel 파일 (*.xlsx);;CSV 파일 (*.csv)",
        )
        if not path:
            return

        use_excel = path.lower().endswith(".xlsx") or (
            not path.lower().endswith(".csv") and "Excel" in selected_filter
        )
        if use_excel:
            if not path.lower().endswith(".xlsx"):
                path += ".xlsx"
            save_to_excel(self.articles, path)
        else:
            if not path.lower().endswith(".csv"):
                path += ".csv"
            save_to_csv(self.articles, path)

        QMessageBox.information(self, "저장 완료", f"'{path}'에 저장했습니다.")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
