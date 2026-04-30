from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Final

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QMouseEvent,
    QPainter,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsSceneDragDropEvent,
    QGraphicsView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

APP_NAME: Final = "Image / SVG / PDF Viewer"
SUPPORTED_SUFFIXES: Final[frozenset[str]] = frozenset({".png", ".jpg", ".jpeg", ".pdf", ".svg"})
IMAGE_SUFFIXES: Final[frozenset[str]] = frozenset({".png", ".jpg", ".jpeg"})
MIN_ZOOM: Final = 0.1
MAX_ZOOM: Final = 8.0
ZOOM_STEP: Final = 1.15
PAN_STEP: Final = 80
TOOLBAR_HEIGHT: Final = 48
BUTTON_HEIGHT: Final = 28


def _toolbar_gap(width: int) -> QWidget:
    gap = QWidget()
    gap.setFixedWidth(width)
    return gap


class DocumentKind(Enum):
    IMAGE = "image"
    SVG = "svg"
    PDF = "pdf"


class ViewerScene(QGraphicsScene):
    dropped = Signal(Path)

    def dragEnterEvent(self, event: QGraphicsSceneDragDropEvent) -> None:
        if _path_from_drop(event) is not None:
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event: QGraphicsSceneDragDropEvent) -> None:
        path = _path_from_drop(event)
        if path is None:
            super().dropEvent(event)
            return
        self.dropped.emit(path)
        event.acceptProposedAction()


class DocumentView(QGraphicsView):
    file_dropped = Signal(Path)
    zoom_requested = Signal(float, QPointF)

    def __init__(self, scene: QGraphicsScene) -> None:
        super().__init__(scene)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(Qt.GlobalColor.darkGray)

    def wheelEvent(self, event: QWheelEvent) -> None:
        steps = event.angleDelta().y() / 120.0
        if steps == 0:
            event.ignore()
            return
        factor = ZOOM_STEP**steps
        self.zoom_requested.emit(factor, self.mapToScene(event.position().toPoint()))
        event.accept()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if _path_from_drop(event) is not None:
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if _path_from_drop(event) is not None:
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        path = _path_from_drop(event)
        if path is None:
            super().dropEvent(event)
            return
        self.file_dropped.emit(path)
        event.acceptProposedAction()


class PdfDocumentView(QPdfView):
    file_dropped = Signal(Path)
    zoom_requested = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setPageMode(QPdfView.PageMode.SinglePage)
        self.setZoomMode(QPdfView.ZoomMode.Custom)
        self._last_pan_position: QPoint | None = None

    def wheelEvent(self, event: QWheelEvent) -> None:
        steps = event.angleDelta().y() / 120.0
        if steps == 0:
            event.ignore()
            return
        self.zoom_requested.emit(ZOOM_STEP**steps)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._last_pan_position = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._last_pan_position is None:
            super().mouseMoveEvent(event)
            return
        position = event.position().toPoint()
        delta = position - self._last_pan_position
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        self._last_pan_position = position
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._last_pan_position = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if _path_from_drop(event) is not None:
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if _path_from_drop(event) is not None:
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        path = _path_from_drop(event)
        if path is None:
            super().dropEvent(event)
            return
        self.file_dropped.emit(path)
        event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 800)
        self.setAcceptDrops(True)

        self._scene = ViewerScene(self)
        self._scene.dropped.connect(self.load_file)
        self._view = DocumentView(self._scene)
        self._view.file_dropped.connect(self.load_file)
        self._view.zoom_requested.connect(self.zoom_by)
        self._pdf_view = PdfDocumentView()
        self._pdf_view.file_dropped.connect(self.load_file)
        self._pdf_view.zoom_requested.connect(lambda factor: self.zoom_by(factor))
        self._stack = QStackedWidget()
        self._stack.addWidget(self._view)
        self._stack.addWidget(self._pdf_view)

        self._item: QGraphicsItem | None = None
        self._kind: DocumentKind | None = None
        self._path: Path | None = None
        self._pdf_document: QPdfDocument | None = None
        self._pdf_page = 0
        self._zoom = 1.0

        self._zoom_label = QLabel("100%")
        self._page_label = QLabel("")
        self._prev_page_button = QPushButton("Prev")
        self._next_page_button = QPushButton("Next")

        self._build_ui()
        self._update_controls()

    def _build_ui(self) -> None:
        toolbar = QToolBar("Controls")
        toolbar.setMovable(False)
        toolbar.setFixedHeight(TOOLBAR_HEIGHT)
        toolbar.setStyleSheet(
            """
            QToolBar {
                spacing: 5px;
                padding-left: 6px;
                padding-right: 6px;
            }
            QToolBar QPushButton {
                min-height: 24px;
                max-height: 28px;
            }
            """
        )
        self.addToolBar(toolbar)

        open_button = QPushButton("Open")
        open_button.setFixedSize(96, BUTTON_HEIGHT)
        open_button.clicked.connect(self.open_file)
        toolbar.addWidget(open_button)
        toolbar.addSeparator()

        zoom_out = QPushButton("-")
        zoom_out.setToolTip("Zoom out")
        zoom_out.setFixedSize(38, BUTTON_HEIGHT)
        zoom_out.clicked.connect(lambda: self.zoom_by(1 / ZOOM_STEP))
        toolbar.addWidget(zoom_out)

        zoom_in = QPushButton("+")
        zoom_in.setToolTip("Zoom in")
        zoom_in.setFixedSize(38, BUTTON_HEIGHT)
        zoom_in.clicked.connect(lambda: self.zoom_by(ZOOM_STEP))
        toolbar.addWidget(zoom_in)

        reset = QPushButton("Reset")
        reset.setFixedSize(76, BUTTON_HEIGHT)
        reset.clicked.connect(self.reset_zoom)
        toolbar.addWidget(reset)
        toolbar.addWidget(self._zoom_label)
        toolbar.addSeparator()
        toolbar.addWidget(_toolbar_gap(8))

        pan_buttons = (
            ("↑", 0, -PAN_STEP),
            ("↓", 0, PAN_STEP),
            ("←", -PAN_STEP, 0),
            ("→", PAN_STEP, 0),
        )
        for label, dx, dy in pan_buttons:
            button = QPushButton(label)
            button.setFixedSize(32, BUTTON_HEIGHT)
            button.clicked.connect(lambda _checked=False, x=dx, y=dy: self.pan_by(x, y))
            toolbar.addWidget(button)
        toolbar.addWidget(_toolbar_gap(8))
        toolbar.addSeparator()
        toolbar.addWidget(_toolbar_gap(16))

        self._prev_page_button.clicked.connect(self.previous_page)
        self._next_page_button.clicked.connect(self.next_page)
        self._prev_page_button.setFixedSize(68, BUTTON_HEIGHT)
        self._next_page_button.setFixedSize(68, BUTTON_HEIGHT)
        toolbar.addWidget(self._prev_page_button)
        toolbar.addWidget(self._next_page_button)
        toolbar.addWidget(self._page_label)
        toolbar.addSeparator()

        help_label = QLabel("Drag & Drop files | Mouse wheel: Zoom | Mouse drag: Pan")
        toolbar.addWidget(help_label)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        empty = self._scene.addText("Open or drag a PNG, JPG, PDF, or SVG file")
        empty.setDefaultTextColor(Qt.GlobalColor.white)
        empty.setPos(230, 230)
        self._scene.setSceneRect(QRectF(0, 0, 800, 500))

    def open_file(self) -> None:
        filename, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Open file",
            "",
            "Supported files (*.png *.jpg *.jpeg *.pdf *.svg)",
        )
        if filename:
            self.load_file(Path(filename))

    def load_file(self, path: Path) -> None:
        path = path.resolve()
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            self._show_error(f"Unsupported file type: {path.suffix}")
            return
        if not path.exists():
            self._show_error(f"File not found: {path}")
            return

        self._path = path
        self._pdf_page = 0
        self._zoom = 1.0
        self._clear_document()

        suffix = path.suffix.lower()
        if suffix in IMAGE_SUFFIXES:
            self._load_image(path)
        elif suffix == ".svg":
            self._load_svg(path)
        elif suffix == ".pdf":
            self._load_pdf(path)

        self._fit_current_item()
        self._update_controls()

    def zoom_by(self, factor: float, _anchor: QPointF | None = None) -> None:
        new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, self._zoom * factor))
        if new_zoom == self._zoom:
            return
        self._zoom = new_zoom
        self._apply_zoom()

    def reset_zoom(self) -> None:
        self._zoom = 1.0
        self._apply_zoom()
        self._view.centerOn(self._scene.sceneRect().center())

    def pan_by(self, dx: int, dy: int) -> None:
        active_view = self._pdf_view if self._kind == DocumentKind.PDF else self._view
        active_view.horizontalScrollBar().setValue(active_view.horizontalScrollBar().value() + dx)
        active_view.verticalScrollBar().setValue(active_view.verticalScrollBar().value() + dy)

    def previous_page(self) -> None:
        if self._pdf_document is None or self._pdf_page <= 0:
            return
        self._pdf_page -= 1
        self._jump_to_pdf_page()

    def next_page(self) -> None:
        if self._pdf_document is None or self._pdf_page >= self._pdf_document.pageCount() - 1:
            return
        self._pdf_page += 1
        self._jump_to_pdf_page()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if _path_from_drop(event) is not None:
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        path = _path_from_drop(event)
        if path is None:
            super().dropEvent(event)
            return
        self.load_file(path)
        event.acceptProposedAction()

    def _load_image(self, path: Path) -> None:
        self._stack.setCurrentWidget(self._view)
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._show_error(f"Could not load image: {path}")
            return
        self._kind = DocumentKind.IMAGE
        self._item = QGraphicsPixmapItem(pixmap)
        self._scene.addItem(self._item)
        self._set_scene_to_item()

    def _load_svg(self, path: Path) -> None:
        self._stack.setCurrentWidget(self._view)
        self._kind = DocumentKind.SVG
        item = QGraphicsSvgItem(str(path))
        if not item.renderer().isValid():
            self._show_error(f"Could not load SVG: {path}")
            return
        item.setFlags(QGraphicsItem.GraphicsItemFlag.ItemClipsToShape)
        item.setCacheMode(QGraphicsItem.CacheMode.NoCache)
        self._item = item
        self._scene.addItem(item)
        self._set_scene_to_item()

    def _load_pdf(self, path: Path) -> None:
        document = QPdfDocument(self)
        status = document.load(str(path))
        if status != QPdfDocument.Error.None_:
            self._show_error(f"Could not load PDF: {path}")
            return
        if document.pageCount() <= 0:
            document.close()
            self._show_error(f"PDF has no pages: {path}")
            return
        self._kind = DocumentKind.PDF
        self._pdf_document = document
        self._pdf_view.setDocument(document)
        self._pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
        self._pdf_view.setZoomFactor(self._zoom)
        self._stack.setCurrentWidget(self._pdf_view)
        self._jump_to_pdf_page()
        self._update_controls()

    def _apply_zoom(self) -> None:
        if self._kind == DocumentKind.PDF:
            self._pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
            self._pdf_view.setZoomFactor(self._zoom)
        else:
            self._view.resetTransform()
            self._view.scale(self._zoom, self._zoom)
        self._update_controls()

    def _jump_to_pdf_page(self) -> None:
        if self._pdf_document is None:
            return
        self._pdf_view.pageNavigator().jump(self._pdf_page, QPointF(), self._zoom)
        self._update_controls()

    def _fit_current_item(self) -> None:
        if self._item is None:
            return
        self._view.resetTransform()
        self._view.centerOn(self._item)

    def _set_scene_to_item(self) -> None:
        if self._item is None:
            return
        rect = self._item.boundingRect()
        self._scene.setSceneRect(rect.adjusted(-50, -50, 50, 50))

    def _clear_document(self) -> None:
        self._scene.clear()
        self._item = None
        self._kind = None
        if self._pdf_document is not None:
            self._pdf_view.setDocument(None)  # type: ignore[arg-type]
            self._pdf_document.close()
        self._pdf_document = None

    def _remove_item(self) -> None:
        if self._item is not None:
            self._scene.removeItem(self._item)
            self._item = None

    def _update_controls(self) -> None:
        self._zoom_label.setText(f"{round(self._zoom * 100)}%")
        is_pdf = self._pdf_document is not None
        page_count = self._pdf_document.pageCount() if self._pdf_document is not None else 0
        self._prev_page_button.setVisible(is_pdf)
        self._next_page_button.setVisible(is_pdf)
        self._page_label.setVisible(is_pdf)
        self._prev_page_button.setEnabled(is_pdf and self._pdf_page > 0)
        self._next_page_button.setEnabled(is_pdf and self._pdf_page < page_count - 1)
        self._page_label.setText(f"Page {self._pdf_page + 1} / {page_count}" if is_pdf else "")

    def _show_error(self, message: str) -> None:
        QTimer.singleShot(0, lambda: QMessageBox.critical(self, APP_NAME, message))


def _path_from_drop(
    event: QDragEnterEvent | QDragMoveEvent | QDropEvent | QGraphicsSceneDragDropEvent,
) -> Path | None:
    urls = event.mimeData().urls()
    if not urls:
        return None
    path = Path(urls[0].toLocalFile())
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        return None
    return path


def build_app(argv: list[str] | None = None) -> QApplication:
    return QApplication(sys.argv if argv is None else argv)


def main() -> int:
    app = build_app()
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
