from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, 
    QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout,
    QPushButton, QSpinBox, QDialog, QDialogButtonBox, QListWidget, QListWidgetItem, QMessageBox,
    QComboBox, QGroupBox, QCheckBox, QFrame, QStackedWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QColor, QIcon, QPainter
from PyQt5.QtSvg import QSvgRenderer
import sys
import requests
import search_parser
import card_handler
import os

class SearchThread(QThread):
    """Thread for performing search to avoid UI freezing"""
    results_ready = pyqtSignal(list)
    
    def __init__(self, query):
        super().__init__()
        self.query = query
    
    def run(self):
        results = search_parser.execute_search(self.query)
        self.results_ready.emit(results)

class AddCardDialog(QDialog):
    """Dialog for adding cards to collection"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Card to Collection")
        self.setGeometry(200, 200, 500, 400)
        self.selected_card = None
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # Search field
        search_label = QLabel("Search for card:")
        search_label.setFont(QFont("Arial", 11))
        search_label.setStyleSheet("color: black;")
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Type card name...")
        self.search_field.textChanged.connect(self.update_card_list)
        
        # Card list
        self.card_list = QListWidget()
        self.card_list.itemDoubleClicked.connect(self.accept_card)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Card")
        self.add_button.clicked.connect(self.accept_card)
        self.add_button.setEnabled(False)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(cancel_button)
        
        # Quantity
        quantity_layout = QHBoxLayout()
        quantity_label = QLabel("Quantity:")
        quantity_label.setStyleSheet("color: black;")
        self.quantity_spinbox = QSpinBox()
        self.quantity_spinbox.setMinimum(1)
        self.quantity_spinbox.setMaximum(100)
        self.quantity_spinbox.setValue(1)
        quantity_layout.addWidget(quantity_label)
        quantity_layout.addWidget(self.quantity_spinbox)
        quantity_layout.addStretch()
        
        # Set dialog stylesheet (after QListWidget to avoid overriding)
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: black;
            }
            QLineEdit {
                color: black;
                background-color: white;
            }
            QListWidget {
                color: black;
                background-color: white;
            }
            QListWidget::item {
                color: black;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        layout.addWidget(search_label)
        layout.addWidget(self.search_field)
        layout.addWidget(self.card_list)
        layout.addLayout(quantity_layout)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Connect list selection
        self.card_list.itemSelectionChanged.connect(self.on_selection_changed)
        
        # Initial load
        self.update_card_list()
    
    def update_card_list(self):
        query = self.search_field.text()
        cards = card_handler.search_catalog(query)
        self.card_list.clear()
        
        if not cards:
            self.card_list.addItem("No cards found. Try a different search term.")
            self.add_button.setEnabled(False)
        else:
            for card in cards:
                self.card_list.addItem(card)
            # Auto-select first item if available
            if self.card_list.count() > 0:
                self.card_list.setCurrentRow(0)
    
    def on_selection_changed(self):
        self.add_button.setEnabled(len(self.card_list.selectedItems()) > 0)
    
    def accept_card(self):
        selected = self.card_list.currentItem()
        if selected:
            self.selected_card = selected.text()
            self.accept()
    
    def get_card_and_quantity(self):
        return self.selected_card, self.quantity_spinbox.value()

class DeckListDialog(QDialog):
    """Dialog for viewing and removing cards from collection."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Deck List")
        self.setGeometry(250, 250, 500, 600)
        self.parent_results_page = parent
        self.initUI()
        self.refresh()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        title = QLabel("Cards to Remove from Collection")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: black;")
        layout.addWidget(title)
        
        # Info label
        info_label = QLabel("Review the list below, then click 'Remove All from Collection' to remove these cards.")
        info_label.setFont(QFont("Arial", 10))
        info_label.setStyleSheet("color: #666; padding: 5px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Use a scroll area with custom widget for list items with remove buttons
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: 1px solid #ddd; background-color: white;")
        
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout()
        self.list_layout.setContentsMargins(5, 5, 5, 5)
        self.list_layout.setSpacing(5)
        self.list_container.setLayout(self.list_layout)
        
        scroll_area.setWidget(self.list_container)
        layout.addWidget(scroll_area)
        
        button_layout = QHBoxLayout()
        self.remove_button = QPushButton("Remove All from Collection")
        self.remove_button.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #a93226;
            }
        """)
        self.remove_button.clicked.connect(self.remove_all_from_collection)
        
        clear_list_button = QPushButton("Clear List Only")
        clear_list_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        clear_list_button.clicked.connect(self.clear_list_only)
        
        close_button = QPushButton("Close")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(clear_list_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def refresh(self):
        # Clear existing items
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        rows = card_handler.deck_get_all()
        total = 0
        
        # Store card data for removal
        self.card_data_map = {}  # uuid -> (name, qty, pile)
        
        # Group by pile for display
        pile_groups = {}
        for name, uuid, qty, pile in rows:
            total += int(qty or 0)
            self.card_data_map[uuid] = (name, qty, pile)
            if pile not in pile_groups:
                pile_groups[pile] = []
            pile_groups[pile].append((name, uuid, qty))
        
        if not rows:
            empty_label = QLabel("(empty)")
            empty_label.setStyleSheet("color: #999; padding: 10px;")
            self.list_layout.addWidget(empty_label)
        else:
            # Display grouped by pile
            for pile in sorted(pile_groups.keys()):
                # Pile header
                pile_header = QLabel(f"--- PILE {pile} ---")
                pile_header.setFont(QFont("Arial", 11, QFont.Bold))
                pile_header.setStyleSheet("color: #9b59b6; padding: 5px 0px;")
                self.list_layout.addWidget(pile_header)
                
                # Cards in this pile
                for name, uuid, qty in sorted(pile_groups[pile]):
                    card_widget = QWidget()
                    card_layout = QHBoxLayout()
                    card_layout.setContentsMargins(10, 2, 2, 2)
                    
                    card_label = QLabel(f"{qty}x {name}")
                    card_label.setStyleSheet("color: black;")
                    card_label.setFont(QFont("Arial", 11))
                    card_layout.addWidget(card_label)
                    
                    card_layout.addStretch()
                    
                    # Remove button - removes all copies from list
                    remove_btn = QPushButton("Remove")
                    remove_btn.setFixedSize(70, 25)
                    remove_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #c0392b;
                            color: white;
                            border: none;
                            border-radius: 3px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #a93226;
                        }
                    """)
                    remove_btn.clicked.connect(lambda checked, u=uuid: self.remove_card_from_list(u, None))
                    card_layout.addWidget(remove_btn)
                    
                    card_widget.setLayout(card_layout)
                    self.list_layout.addWidget(card_widget)
            
            self.list_layout.addStretch()
        
        self.setWindowTitle(f"Deck List ({total} cards)")
        self.remove_button.setEnabled(len(rows) > 0)
    
    def remove_card_from_list(self, uuid, quantity):
        """Remove a card from the deck list."""
        if quantity is None:
            # Remove all - get current quantity
            if uuid in self.card_data_map:
                _, qty, _ = self.card_data_map[uuid]
                quantity = qty
        
        success, message = card_handler.deck_remove_card(uuid, quantity)
        if success:
            self.refresh()
            # Update deck count in parent
            if self.parent_results_page and hasattr(self.parent_results_page, "refresh_deck_count"):
                self.parent_results_page.refresh_deck_count()
            # Update all card widgets' deck button states
            if self.parent_results_page:
                self.update_all_card_widgets_deck_buttons(self.parent_results_page)
    
    def remove_all_from_collection(self):
        """Remove all cards in list from collection."""
        # Create custom dialog for better button control
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox
        
        confirm_dialog = QDialog(self)
        confirm_dialog.setWindowTitle("Confirm Removal")
        confirm_dialog.setModal(True)
        confirm_dialog.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: black;
            }
        """)
        
        layout = QVBoxLayout()
        
        msg_label = QLabel("Are you sure you want to remove all cards in this list from your collection?")
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: black; padding: 10px;")
        layout.addWidget(msg_label)
        
        warning_label = QLabel("This cannot be undone.")
        warning_label.setStyleSheet("color: #c0392b; font-weight: bold; padding: 5px;")
        layout.addWidget(warning_label)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
        button_box.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
            QPushButton[text="&Yes"] {
                background-color: #c0392b;
            }
            QPushButton[text="&Yes"]:hover {
                background-color: #a93226;
            }
        """)
        
        yes_button = button_box.button(QDialogButtonBox.Yes)
        yes_button.setText("Yes")
        no_button = button_box.button(QDialogButtonBox.No)
        no_button.setText("No")
        
        button_box.accepted.connect(confirm_dialog.accept)
        button_box.rejected.connect(confirm_dialog.reject)
        
        layout.addWidget(button_box)
        confirm_dialog.setLayout(layout)
        
        reply = confirm_dialog.exec_()
        
        if reply == QDialog.Accepted:
            success, message, count = card_handler.deck_remove_all_from_collection()
            if success:
                # Show success message
                success_dialog = QDialog(self)
                success_dialog.setWindowTitle("Success")
                success_dialog.setModal(True)
                success_dialog.setStyleSheet("""
                    QDialog {
                        background-color: white;
                    }
                    QLabel {
                        color: black;
                    }
                """)
                success_layout = QVBoxLayout()
                success_label = QLabel(message)
                success_label.setStyleSheet("color: black; padding: 10px;")
                success_layout.addWidget(success_label)
                ok_button = QPushButton("OK")
                ok_button.setStyleSheet("""
                    QPushButton {
                        background-color: #27ae60;
                        color: white;
                        padding: 8px 20px;
                        border: none;
                        border-radius: 4px;
                        font-weight: bold;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #229954;
                    }
                """)
                ok_button.clicked.connect(success_dialog.accept)
                success_layout.addWidget(ok_button)
                success_dialog.setLayout(success_layout)
                success_dialog.exec_()
                
                self.refresh()
                # Refresh parent results page if it exists
                if self.parent_results_page and hasattr(self.parent_results_page, "refresh_deck_count"):
                    self.parent_results_page.refresh_deck_count()
                # Refresh search results if parent has last_query
                if self.parent_results_page and hasattr(self.parent_results_page, "last_query"):
                    self.parent_results_page.perform_search(self.parent_results_page.last_query)
                # Update all card widgets' deck button states
                if self.parent_results_page:
                    self.update_all_card_widgets_deck_buttons(self.parent_results_page)
            else:
                # Show error message
                error_dialog = QDialog(self)
                error_dialog.setWindowTitle("Error")
                error_dialog.setModal(True)
                error_dialog.setStyleSheet("""
                    QDialog {
                        background-color: white;
                    }
                    QLabel {
                        color: black;
                    }
                """)
                error_layout = QVBoxLayout()
                error_label = QLabel(message)
                error_label.setStyleSheet("color: #c0392b; padding: 10px;")
                error_layout.addWidget(error_label)
                ok_button = QPushButton("OK")
                ok_button.setStyleSheet("""
                    QPushButton {
                        background-color: #c0392b;
                        color: white;
                        padding: 8px 20px;
                        border: none;
                        border-radius: 4px;
                        font-weight: bold;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #a93226;
                    }
                """)
                ok_button.clicked.connect(error_dialog.accept)
                error_layout.addWidget(ok_button)
                error_dialog.setLayout(error_layout)
                error_dialog.exec_()
    
    def clear_list_only(self):
        """Clear the list without removing from collection."""
        card_handler.deck_clear()
        self.refresh()
        # Let parent update any deck count badge/label
        if self.parent_results_page and hasattr(self.parent_results_page, "refresh_deck_count"):
            try:
                self.parent_results_page.refresh_deck_count()
            except Exception:
                pass
        # Update all card widgets' deck button states
        if self.parent_results_page:
            self.update_all_card_widgets_deck_buttons(self.parent_results_page)
    
    def update_all_card_widgets_deck_buttons(self, results_page):
        """Update deck button states for all card widgets in results page."""
        try:
            for i in range(results_page.results_layout.count()):
                item = results_page.results_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if isinstance(widget, CardWidget) and hasattr(widget, 'update_deck_button_state'):
                        widget.update_deck_button_state()
        except Exception:
            pass

class ImageLoadThread(QThread):
    """Thread for loading card images"""
    image_loaded = pyqtSignal(QPixmap)
    
    def __init__(self, image_url, card_uuid=None):
        super().__init__()
        self.image_url = image_url
        self.card_uuid = card_uuid
    
    def run(self):
        pixmap = QPixmap()
        
        # Try to load from provided URL first
        if self.image_url:
            try:
                response = requests.get(self.image_url, timeout=5)
                if response.status_code == 200:
                    pixmap.loadFromData(response.content)
                    if not pixmap.isNull():
                        self.image_loaded.emit(pixmap)
                        return
            except Exception as e:
                print(f"Error loading image from URL: {e}")
        
        # If no URL or failed, try fetching from Scryfall API using UUID
        if self.card_uuid:
            try:
                scryfall_url = f"https://api.scryfall.com/cards/{self.card_uuid}"
                response = requests.get(scryfall_url, timeout=5)
                if response.status_code == 200:
                    card_data = response.json()
                    # Get normal image URL
                    image_uri = None
                    if "image_uris" in card_data and "normal" in card_data["image_uris"]:
                        image_uri = card_data["image_uris"]["normal"]
                    elif "card_faces" in card_data and len(card_data["card_faces"]) > 0:
                        # For double-faced cards
                        if "image_uris" in card_data["card_faces"][0] and "normal" in card_data["card_faces"][0]["image_uris"]:
                            image_uri = card_data["card_faces"][0]["image_uris"]["normal"]
                    
                    if image_uri:
                        img_response = requests.get(image_uri, timeout=5)
                        if img_response.status_code == 200:
                            pixmap.loadFromData(img_response.content)
                            # Update database with image URL for future use
                            if not pixmap.isNull():
                                import utils
                                conn = utils.get_connection()
                                c = conn.cursor()
                                c.execute('UPDATE card_catalog SET image_url = ? WHERE uuid = ?', (image_uri, self.card_uuid))
                                conn.commit()
                                conn.close()
                                self.image_loaded.emit(pixmap)
                                return
            except Exception as e:
                print(f"Error fetching from Scryfall API: {e}")
        
        # If all else fails, emit null pixmap
        self.image_loaded.emit(QPixmap())

class CardWidget(QWidget):
    """Widget to display a single card"""
    def __init__(self, card_data, parent_window=None):
        super().__init__()
        # card_data: (name, uuid, quantity, pile, colors, cmc, image_url)
        self.card_data = card_data
        self.parent_window = parent_window
        self.image_thread = None
        self.initUI()
        self.load_image()
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Card name
        name_label = QLabel(self.card_data[0])
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setFont(QFont("Arial", 10, QFont.Bold))
        name_label.setStyleSheet("color: black;")
        layout.addWidget(name_label)
        
        # Card image
        self.image_label = QLabel()
        self.image_label.setMinimumSize(200, 280)
        self.image_label.setMaximumSize(200, 280)
        self.image_label.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0; color: black;")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setText("Loading...")
        self.image_label.setScaledContents(True)
        layout.addWidget(self.image_label)
        
        # Pile number - prominently displayed
        pile_label = QLabel(f"PILE {self.card_data[3]}")
        pile_label.setAlignment(Qt.AlignCenter)
        pile_label.setFont(QFont("Arial", 12, QFont.Bold))
        pile_label.setStyleSheet("background-color: #3498db; color: white; padding: 5px; border-radius: 3px;")
        layout.addWidget(pile_label)
        
        # Quantity only
        quantity_label = QLabel(f"Quantity: {self.card_data[2]}")
        quantity_label.setAlignment(Qt.AlignCenter)
        quantity_label.setFont(QFont("Arial", 9))
        quantity_label.setStyleSheet("color: black;")
        layout.addWidget(quantity_label)
        
        # Remove button
        button_layout = QHBoxLayout()
        remove_one_button = QPushButton("-1")
        remove_one_button.setToolTip("Remove 1")
        remove_one_button.clicked.connect(lambda: self.remove_card(1))
        remove_all_button = QPushButton("Remove All")
        remove_all_button.setToolTip("Remove all copies")
        remove_all_button.clicked.connect(lambda: self.remove_card(self.card_data[2]))
        
        remove_one_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        
        remove_all_button.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #a93226;
            }
        """)
        
        button_layout.addWidget(remove_one_button)
        button_layout.addWidget(remove_all_button)
        layout.addLayout(button_layout)
        
        # Deck list button
        self.deck_button = QPushButton("Add to Deck")
        self.deck_button.setToolTip("Add 1 copy to deck list")
        self.deck_button.clicked.connect(self.add_to_deck)
        self.update_deck_button_state()
        layout.addWidget(self.deck_button)
        
        self.setLayout(layout)
        self.setStyleSheet("border: 1px solid #ddd; border-radius: 5px; background-color: white;")
        self.setFixedSize(220, 380)
    
    def load_image(self):
        """Load card image asynchronously"""
        # Handle both old format (6 items) and new format (7 items with image_url)
        image_url = None
        card_uuid = self.card_data[1]
        
        if len(self.card_data) > 6:
            image_url = self.card_data[6]
        elif len(self.card_data) == 6:
            # Try to get image URL from database if not in results
            import utils
            conn = utils.get_connection()
            c = conn.cursor()
            result = c.execute('SELECT image_url FROM card_catalog WHERE uuid = ?', (card_uuid,)).fetchone()
            conn.close()
            if result and result[0]:
                image_url = result[0]
        
        # Always try to load image (will fetch from API if needed)
        self.image_thread = ImageLoadThread(image_url, card_uuid)
        self.image_thread.image_loaded.connect(self.on_image_loaded)
        self.image_thread.start()
    
    def on_image_loaded(self, pixmap):
        """Handle loaded image"""
        if pixmap.isNull():
            self.image_label.setText("No Image")
        else:
            # Scale pixmap to fit label while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setText("")
    
    def cleanup(self):
        """Clean up resources when widget is destroyed"""
        if self.image_thread and self.image_thread.isRunning():
            self.image_thread.terminate()
            self.image_thread.wait()
    
    def remove_card(self, quantity):
        """Remove card from collection"""
        uuid = self.card_data[1]
        card_name = self.card_data[0]
        
        if card_handler.remove_card_by_uuid(uuid, quantity):
            # Update deck button state since quantity changed
            self.update_deck_button_state()
            # Find ResultsPage through parent chain and refresh
            widget = self.parent()
            while widget:
                if isinstance(widget, ResultsPage):
                    # Re-run the last search
                    if hasattr(widget, 'last_query'):
                        widget.perform_search(widget.last_query)
                    break
                widget = widget.parent()
    
    def update_deck_button_state(self):
        """Update the deck button state based on available capacity."""
        uuid = self.card_data[1]
        available_qty = self.card_data[2]  # Quantity in collection
        
        # Check current quantity in deck list
        import utils
        conn = utils.get_connection()
        c = conn.cursor()
        deck_result = c.execute('SELECT quantity FROM deck_list WHERE uuid = ?', (uuid,)).fetchone()
        current_deck_qty = deck_result[0] if deck_result else 0
        conn.close()
        
        can_add = current_deck_qty < available_qty
        
        if can_add:
            self.deck_button.setEnabled(True)
            self.deck_button.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
            """)
            remaining = available_qty - current_deck_qty
            self.deck_button.setToolTip(f"Add 1 copy to deck list ({remaining} available)")
        else:
            self.deck_button.setEnabled(False)
            self.deck_button.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 6px;
                    font-weight: bold;
                }
            """)
            if current_deck_qty > 0:
                self.deck_button.setToolTip(f"All {available_qty} copies already in deck list")
            else:
                self.deck_button.setToolTip("No copies available")
    
    def add_to_deck(self):
        """Add this card to deck list."""
        uuid = self.card_data[1]
        name = self.card_data[0]
        success, message = card_handler.deck_add_card(uuid, name, 1)
        if success:
            # Update button state
            self.update_deck_button_state()
            # Update deck count in ResultsPage if present
            widget = self.parent()
            while widget:
                if isinstance(widget, ResultsPage):
                    if hasattr(widget, "refresh_deck_count"):
                        widget.refresh_deck_count()
                    # Refresh any open deck list dialog
                    if hasattr(widget, "_deck_dialog") and widget._deck_dialog:
                        try:
                            widget._deck_dialog.refresh()
                        except Exception:
                            pass
                    # Update all card widgets' deck button states
                    self.update_all_card_widgets_deck_buttons(widget)
                    break
                widget = widget.parent()
        else:
            # Show error message
            QMessageBox.warning(self, "Cannot Add Card", message)
            # Update button state in case it changed
            self.update_deck_button_state()
    
    def update_all_card_widgets_deck_buttons(self, results_page):
        """Update deck button states for all card widgets in results page."""
        try:
            for i in range(results_page.results_layout.count()):
                item = results_page.results_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if isinstance(widget, CardWidget) and hasattr(widget, 'update_deck_button_state'):
                        widget.update_deck_button_state()
        except Exception:
            pass

class SearchPage(QWidget):
    """Page containing all search filters"""
    search_requested = pyqtSignal(str)  # Emit query string when search is clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.color_name_to_code = {"white": "W", "blue": "U", "black": "B", "red": "R", "green": "G"}
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 20, 40, 20)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Advanced Search")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 28, QFont.Bold))
        title.setStyleSheet("color: #9b59b6; padding: 20px;")
        layout.addWidget(title)
        
        # Scroll area for filters
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: white;")
        
        filter_widget = QWidget()
        filter_layout = QVBoxLayout()
        filter_layout.setSpacing(20)
        filter_layout.setContentsMargins(20, 20, 20, 20)
        
        # Helper function to create filter section with separator and boxed layout
        def create_filter_section(icon_path, label_text, widget, description_text=None, add_separator=True):
            section_layout = QVBoxLayout()
            section_layout.setSpacing(8)
            
            # Separator line before this section (except first)
            if add_separator:
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setFrameShadow(QFrame.Sunken)
                separator.setStyleSheet("color: #e0e0e0; background-color: #e0e0e0; max-height: 1px;")
                section_layout.addWidget(separator)
            
            # Outer frame to visually box the filter section
            frame = QFrame()
            frame.setObjectName("filterSectionFrame")
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(12, 10, 12, 10)
            frame_layout.setSpacing(6)
            
            # Icon and label row
            header_layout = QHBoxLayout()
            header_layout.setSpacing(10)
            header_layout.setAlignment(Qt.AlignTop)
            
            icon_label = QLabel()
            icon_label.setFixedSize(24, 24)
            icon_label.setAlignment(Qt.AlignCenter | Qt.AlignTop)
            # Try to load SVG icon
            if os.path.exists(icon_path):
                try:
                    # Use QSvgRenderer for proper SVG rendering
                    renderer = QSvgRenderer(icon_path)
                    if renderer.isValid():
                        pixmap = QPixmap(24, 24)
                        pixmap.fill(Qt.transparent)
                        painter = QPainter(pixmap)
                        renderer.render(painter)
                        painter.end()
                        if not pixmap.isNull():
                            icon_label.setPixmap(pixmap)
                        else:
                            raise Exception("Pixmap is null")
                    else:
                        raise Exception("Invalid SVG renderer")
                except Exception as e:
                    print(f"Error loading icon {icon_path}: {e}")
                    # Fallback: try QIcon
                    try:
                        icon = QIcon(icon_path)
                        pixmap = icon.pixmap(24, 24)
                        if not pixmap.isNull():
                            icon_label.setPixmap(pixmap)
                        else:
                            # Check if it's an emoji SVG
                            with open(icon_path, 'r') as f:
                                svg_content = f.read()
                                if '<text' in svg_content:
                                    # Emoji SVG - extract emoji or use placeholder
                                    icon_label.setText("📋")
                                    icon_label.setFont(QFont("Arial", 14))
                                else:
                                    icon_label.setText("📋")
                                    icon_label.setFont(QFont("Arial", 14))
                    except Exception as e2:
                        print(f"Fallback icon load failed: {e2}")
                        icon_label.setText("📋")
                        icon_label.setFont(QFont("Arial", 14))
            else:
                icon_label.setText("📋")
                icon_label.setFont(QFont("Arial", 14))
            icon_label.setStyleSheet("color: #9b59b6;")
            icon_label.setFixedWidth(30)
            icon_label.setFixedHeight(24)
            
            label = QLabel(label_text)
            label.setFont(QFont("Arial", 14, QFont.Bold))
            label.setStyleSheet("color: #9b59b6;")
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            
            header_layout.addWidget(icon_label)
            header_layout.addWidget(label)
            header_layout.addStretch()
            header_layout.setContentsMargins(0, 0, 0, 0)
            
            frame_layout.addLayout(header_layout)
            frame_layout.addWidget(widget)
            
            if description_text:
                desc_label = QLabel(description_text)
                desc_label.setFont(QFont("Arial", 11))
                desc_label.setStyleSheet("color: #666; margin-top: 5px;")
                desc_label.setWordWrap(True)
                frame_layout.addWidget(desc_label)
            
            section_layout.addWidget(frame)
            return section_layout
        
        color_names = {"White": "W", "Blue": "U", "Black": "B", "Red": "R", "Green": "G"}
        color_colors = {"White": "#f8f8f8", "Blue": "#0e68ab", "Black": "#150b00", "Red": "#d3202a", "Green": "#00733e"}
        
        # Card Name filter
        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText("Any words in the name, e.g. 'Fire'")
        self.name_field.setFont(QFont("Arial", 14))
        name_section = create_filter_section("icons/card_name.svg", "Card Name", self.name_field, add_separator=False)
        filter_layout.addLayout(name_section)
        
        # Text/Oracle filter
        self.oracle_field = QLineEdit()
        self.oracle_field.setPlaceholderText("Any text, e.g. 'draw a card'")
        self.oracle_field.setFont(QFont("Arial", 14))
        oracle_desc = "Enter text that should appear in the rules box. You can use ~ as a placeholder for the card name. Word order doesn't matter."
        oracle_section = create_filter_section("icons/text.svg", "Text", self.oracle_field, oracle_desc)
        filter_layout.addLayout(oracle_section)
        
        # Type Line filter
        self.type_field = QLineEdit()
        self.type_field.setPlaceholderText("Enter a type or choose from the list")
        self.type_field.setFont(QFont("Arial", 14))
        type_desc = "Choose any card type, supertype, or subtypes to match. Click the 'IS' or 'NOT' button to toggle between including and excluding a type."
        type_section = create_filter_section("icons/type.svg", "Type Line", self.type_field, type_desc)
        filter_layout.addLayout(type_section)
        
        # Colors filter
        colors_widget = QWidget()
        colors_layout = QVBoxLayout()
        colors_layout.setSpacing(10)
        
        colors_button_layout = QHBoxLayout()
        colors_button_layout.setSpacing(5)
        self.color_buttons = {}
        for color_name, color_code in color_names.items():
            btn = QPushButton(color_name)
            btn.setCheckable(True)
            btn.setFont(QFont("Arial", 11))
            btn.setFixedHeight(35)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color_colors[color_name]};
                    color: {'black' if color_name == 'White' else 'white'};
                    padding: 5px 15px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border: 2px solid #9b59b6;
                }}
                QPushButton:checked {{
                    border: 2px solid #9b59b6;
                    font-weight: bold;
                }}
            """)
            self.color_buttons[color_name.lower()] = btn
            colors_button_layout.addWidget(btn)
        colors_button_layout.addStretch()
        colors_layout.addLayout(colors_button_layout)
        
        color_combo = QComboBox()
        color_combo.addItems(["Exactly these colors", "Including these colors", "At most these colors"])
        color_combo.setFont(QFont("Arial", 12))
        colors_layout.addWidget(color_combo)
        
        colors_widget.setLayout(colors_layout)
        colors_desc = "'Including' means cards that are all the colors you select, with or without any others. 'At most' means cards that have some or all of the colors you select, plus colorless."
        colors_section = create_filter_section("icons/colors.svg", "Colors", colors_widget, colors_desc)
        filter_layout.addLayout(colors_section)
        
        # Commander color identity filter
        commander_widget = QWidget()
        commander_layout = QVBoxLayout()
        commander_layout.setSpacing(10)
        
        commander_button_layout = QHBoxLayout()
        commander_button_layout.setSpacing(5)
        self.commander_color_buttons = {}
        for color_name, color_code in color_names.items():
            btn = QPushButton(color_name)
            btn.setCheckable(True)
            btn.setFont(QFont("Arial", 11))
            btn.setFixedHeight(35)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color_colors[color_name]};
                    color: {'black' if color_name == 'White' else 'white'};
                    padding: 5px 15px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border: 2px solid #9b59b6;
                }}
                QPushButton:checked {{
                    border: 2px solid #9b59b6;
                    font-weight: bold;
                }}
            """)
            self.commander_color_buttons[color_name.lower()] = btn
            commander_button_layout.addWidget(btn)
        commander_button_layout.addStretch()
        commander_layout.addLayout(commander_button_layout)
        
        commander_widget.setLayout(commander_layout)
        commander_desc = "Select your commanders' color identity, and only cards that fit in your deck will be returned."
        commander_section = create_filter_section("icons/commander.svg", "Commander", commander_widget, commander_desc)
        filter_layout.addLayout(commander_section)
        
        # Mana Cost filter
        self.mana_field = QLineEdit()
        self.mana_field.setPlaceholderText("Any mana symbols, e.g. '{W}{W}'")
        self.mana_field.setFont(QFont("Arial", 14))
        mana_desc = "Find cards with this exact mana cost."
        mana_section = create_filter_section("icons/mana_cost.svg", "Mana Cost", self.mana_field, mana_desc)
        filter_layout.addLayout(mana_section)
        
        # Stats filter (Mana Value / Power / Toughness) - Dynamic rows
        stats_widget = QWidget()
        stats_main_layout = QVBoxLayout()
        stats_main_layout.setSpacing(8)
        
        # Container for stat rows
        self.stats_rows_layout = QVBoxLayout()
        self.stats_rows_layout.setSpacing(8)
        
        # List to store stat row widgets and data
        self.stat_rows = []
        self.stat_row_data = []
        
        # Create first stat row
        self.add_stat_row()
        
        stats_main_layout.addLayout(self.stats_rows_layout)
        stats_main_layout.addStretch()
        
        stats_widget.setLayout(stats_main_layout)
        stats_desc = "Restrict cards based on their numeric statistics. Cards without stats will not be returned."
        stats_section = create_filter_section("icons/stats.svg", "Stats", stats_widget, stats_desc)
        filter_layout.addLayout(stats_section)
        
        # Sets filter - DROPDOWN
        self.set_combo = QComboBox()
        self.set_combo.setEditable(True)
        self.set_combo.setFont(QFont("Arial", 14))
        self.set_combo.lineEdit().setPlaceholderText("Enter a set name or choose from the list")
        try:
            sets = card_handler.get_unique_sets()
            self.set_combo.addItem("Any")
            for set_code in sorted(sets):
                self.set_combo.addItem(set_code.upper())
        except Exception as e:
            print(f"Error loading sets: {e}")
            self.set_combo.addItem("Any")
        sets_desc = "Restrict cards based on their set, block, or group."
        sets_section = create_filter_section("icons/sets.svg", "Sets", self.set_combo, sets_desc)
        filter_layout.addLayout(sets_section)
        
        # Rarity filter
        rarity_widget = QWidget()
        rarity_layout = QHBoxLayout()
        rarity_layout.setSpacing(10)
        
        self.rarity_common = QCheckBox("Common")
        self.rarity_uncommon = QCheckBox("Uncommon")
        self.rarity_rare = QCheckBox("Rare")
        self.rarity_mythic = QCheckBox("Mythic Rare")
        
        for checkbox in [self.rarity_common, self.rarity_uncommon, self.rarity_rare, self.rarity_mythic]:
            checkbox.setFont(QFont("Arial", 12))
            rarity_layout.addWidget(checkbox)
        rarity_layout.addStretch()
        
        rarity_widget.setLayout(rarity_layout)
        rarity_desc = "Only return cards of the selected rarities."
        rarity_section = create_filter_section("icons/rarity.svg", "Rarity", rarity_widget, rarity_desc)
        filter_layout.addLayout(rarity_section)
        
        # Artist filter
        self.artist_field = QLineEdit()
        self.artist_field.setPlaceholderText("Any artist name, e.g. 'Magali'")
        self.artist_field.setFont(QFont("Arial", 14))
        artist_section = create_filter_section("icons/artist.svg", "Artist", self.artist_field)
        filter_layout.addLayout(artist_section)
        
        # Flavor Text filter
        self.flavor_field = QLineEdit()
        self.flavor_field.setPlaceholderText("Any flavor text, e.g. 'Kjeldoran'")
        self.flavor_field.setFont(QFont("Arial", 14))
        flavor_desc = "Enter words that should appear in the flavor text. Word order doesn't matter."
        flavor_section = create_filter_section("icons/flavor.svg", "Flavor Text", self.flavor_field, flavor_desc)
        filter_layout.addLayout(flavor_section)
        
        filter_widget.setLayout(filter_layout)
        scroll.setWidget(filter_widget)
        layout.addWidget(scroll)
        
        # Search button
        search_button_layout = QHBoxLayout()
        search_button_layout.addStretch()
        search_button = QPushButton("Search")
        search_button.setFont(QFont("Arial", 16, QFont.Bold))
        search_button.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                padding: 15px 40px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        search_button.clicked.connect(self.perform_search)
        search_button_layout.addWidget(search_button)
        search_button_layout.addStretch()
        layout.addLayout(search_button_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("background-color: white;")
    
    def add_stat_row(self):
        """Add a new stat filter row"""
        row_widget = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)
        
        # Stat type dropdown
        stat_type_combo = QComboBox()
        stat_type_combo.addItems(["Mana Value", "Power", "Toughness"])
        stat_type_combo.setFont(QFont("Arial", 12))
        stat_type_combo.setMinimumWidth(140)
        
        # Comparison operator dropdown
        operator_combo = QComboBox()
        operator_combo.addItems([
            "equal to",
            "greater than",
            "less than",
            "greater than or equal",
            "less than or equal",
            "not equal to",
        ])
        operator_combo.setFont(QFont("Arial", 12))
        operator_combo.setMinimumWidth(160)
        
        # Value entry
        value_field = QLineEdit()
        value_field.setPlaceholderText("Any value, e.g. \"2\"")
        value_field.setFont(QFont("Arial", 12))
        value_field.setFixedWidth(160)
        
        # Connect signals to add new row when data is entered
        def on_stat_changed():
            # Check if this row has any data entered
            has_data = bool(value_field.text().strip())
            
            # Check if this is the last row
            is_last = (len(self.stat_rows) == 0 or 
                      self.stat_rows[-1] == row_widget)
            
            # If this row has data and is the last, add a new row
            if has_data and is_last:
                # Use QTimer to avoid adding multiple rows during rapid changes
                QTimer.singleShot(50, lambda: self.add_stat_row())
        
        stat_type_combo.currentTextChanged.connect(on_stat_changed)
        operator_combo.currentTextChanged.connect(on_stat_changed)
        value_field.textChanged.connect(on_stat_changed)
        
        row_layout.addWidget(stat_type_combo)
        row_layout.addWidget(operator_combo)
        row_layout.addWidget(value_field)
        row_layout.addStretch()
        
        row_widget.setLayout(row_layout)
        self.stats_rows_layout.addWidget(row_widget)
        self.stat_rows.append(row_widget)
        
        # Store references for query building
        self.stat_row_data.append({
            'type': stat_type_combo,
            'operator': operator_combo,
            'value': value_field,
            'widget': row_widget
        })
    
    def build_query(self):
        """Build query string from all filters"""
        query_parts = []
        
        # Name search
        name_query = self.name_field.text().strip()
        if name_query:
            query_parts.append(name_query)
        
        # Colors
        selected_colors = [self.color_name_to_code[color] for color, btn in self.color_buttons.items() if btn.isChecked()]
        if selected_colors:
            colors_str = ",".join(selected_colors)
            query_parts.append(f"c:{colors_str}")
        
        # Commander color identity
        selected_commander_colors = [self.color_name_to_code[color] for color, btn in self.commander_color_buttons.items() if btn.isChecked()]
        if selected_commander_colors:
            commander_colors_str = ",".join(selected_commander_colors)
            query_parts.append(f"commander:{commander_colors_str}")
        
        # Stats (Mana Value / Power / Toughness) - process all rows
        for row_data in self.stat_row_data:
            stat_value = row_data['value'].text().strip()
            if stat_value:
                stat_type = row_data['type'].currentText()
                operator_text = row_data['operator'].currentText()
                
                operator_map = {
                    "equal to": "",
                    "greater than": ">",
                    "less than": "<",
                    "greater than or equal": ">=",
                    "less than or equal": "<=",
                    "not equal to": "!=",
                }
                op = operator_map.get(operator_text, "")
                comparator = f"{op}{stat_value}" if op else stat_value
                
                if stat_type == "Mana Value":
                    query_parts.append(f"cmc:{comparator}")
                elif stat_type == "Power":
                    query_parts.append(f"pow:{comparator}")
                elif stat_type == "Toughness":
                    query_parts.append(f"tou:{comparator}")
        
        # Type
        type_value = self.type_field.text().strip()
        if type_value:
            query_parts.append(f"t:{type_value}")
        
        # Oracle text
        oracle_value = self.oracle_field.text().strip()
        if oracle_value:
            query_parts.append(f"o:{oracle_value}")
        
        # Rarity
        rarity_parts = []
        if self.rarity_common.isChecked():
            rarity_parts.append("common")
        if self.rarity_uncommon.isChecked():
            rarity_parts.append("uncommon")
        if self.rarity_rare.isChecked():
            rarity_parts.append("rare")
        if self.rarity_mythic.isChecked():
            rarity_parts.append("mythic")
        if rarity_parts:
            query_parts.append(f"r:{rarity_parts[0]}")
        
        # Mana Cost
        mana_value = self.mana_field.text().strip()
        if mana_value:
            query_parts.append(f"m:{mana_value}")
        
        # Set
        set_value = self.set_combo.currentText().strip()
        if set_value and set_value != "Any":
            query_parts.append(f"set:{set_value.lower()}")
        
        # Artist
        artist_value = self.artist_field.text().strip()
        if artist_value:
            query_parts.append(f"artist:{artist_value}")
        
        # Flavor Text
        flavor_value = self.flavor_field.text().strip()
        if flavor_value:
            query_parts.append(f"flavor:{flavor_value}")
        
        return " ".join(query_parts)
    
    def perform_search(self):
        """Emit search signal with built query"""
        query = self.build_query()
        self.search_requested.emit(query)

class ResultsPage(QWidget):
    """Page displaying search results"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_thread = None
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Header with back button
        header_layout = QHBoxLayout()
        back_button = QPushButton("← Back to Search")
        back_button.setFont(QFont("Arial", 12))
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        back_button.clicked.connect(self.go_back)
        header_layout.addWidget(back_button)
        
        # Deck list button / count
        self.deck_button = QPushButton("Deck List (0)")
        self.deck_button.setFont(QFont("Arial", 12))
        self.deck_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.deck_button.clicked.connect(self.open_deck_list)
        header_layout.addWidget(self.deck_button)
        self.refresh_deck_count()
        
        header_layout.addStretch()
        
        self.results_label = QLabel("")
        self.results_label.setFont(QFont("Arial", 12))
        self.results_label.setStyleSheet("color: black; padding: 5px;")
        header_layout.addWidget(self.results_label)
        
        layout.addLayout(header_layout)
        
        # Results widget
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none; background-color: white;")
        
        self.results_widget = QWidget()
        self.results_layout = QGridLayout()
        self.results_layout.setSpacing(10)
        self.results_layout.setContentsMargins(10, 10, 10, 10)
        self.results_widget.setLayout(self.results_layout)
        
        scroll_area.setWidget(self.results_widget)
        layout.addWidget(scroll_area)
        
        self.setLayout(layout)
        self.setStyleSheet("background-color: white;")
    
    def refresh_deck_count(self):
        total = 0
        try:
            total = card_handler.deck_total_cards()
        except Exception:
            total = 0
        if hasattr(self, "deck_button"):
            self.deck_button.setText(f"Deck List ({total})")
    
    def open_deck_list(self):
        # Store reference so CardWidget can refresh it
        self._deck_dialog = DeckListDialog(self)
        self._deck_dialog.exec_()
        self.refresh_deck_count()
        self._deck_dialog = None
    
    def go_back(self):
        """Signal to go back to search page"""
        # Find MainWindow through parent chain
        widget = self.parent()
        while widget:
            if isinstance(widget, QMainWindow):
                if hasattr(widget, 'show_search_page'):
                    widget.show_search_page()
                break
            widget = widget.parent()
    
    def perform_search(self, query):
        """Perform search and display results"""
        # Store query for refresh purposes
        self.last_query = query
        
        # Cancel previous search if running
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.terminate()
            self.search_thread.wait()
        
        # Clear previous results
        self.clear_results()
        self.results_label.setText("Searching...")
        
        # Start search in thread
        self.search_thread = SearchThread(query)
        self.search_thread.results_ready.connect(self.display_results)
        self.search_thread.start()
    
    def clear_results(self):
        """Clear all card widgets from results"""
        for i in range(self.results_layout.count()):
            item = self.results_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, CardWidget):
                    widget.cleanup()
                widget.deleteLater()
        
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item:
                if item.widget():
                    widget = item.widget()
                    if isinstance(widget, CardWidget):
                        widget.cleanup()
                    widget.deleteLater()
                elif item.layout():
                    self.clear_layout(item.layout())
        
        QApplication.processEvents()
    
    def clear_layout(self, layout):
        """Recursively clear a layout"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())
    
    def display_results(self, results):
        """Display search results in grid"""
        self.clear_results()
        
        if not results:
            no_results = QLabel("No cards found in your collection.")
            no_results.setAlignment(Qt.AlignCenter)
            no_results.setFont(QFont("Arial", 14))
            no_results.setStyleSheet("color: black; padding: 20px;")
            self.results_layout.addWidget(no_results, 0, 0)
            self.results_label.setText("0 results")
            return
        
        cols = 5
        batch_size = 25
        
        for i, card_data in enumerate(results[:batch_size]):
            row = i // cols
            col = i % cols
            card_widget = CardWidget(card_data, self)
            self.results_layout.addWidget(card_widget, row, col)
            # Update deck button state after widget is created
            if hasattr(card_widget, 'update_deck_button_state'):
                card_widget.update_deck_button_state()
        
        self.results_label.setText(f"{len(results)} result(s) found" + (f" (showing first {min(batch_size, len(results))})" if len(results) > batch_size else ""))
        
        self.results_layout.invalidate()
        self.results_widget.updateGeometry()
        QApplication.processEvents()
        
        if len(results) > batch_size:
            QTimer.singleShot(100, lambda: self.load_remaining_cards(results[batch_size:], batch_size, cols))
    
    def load_remaining_cards(self, remaining_results, start_index, cols):
        """Load remaining cards incrementally"""
        if not remaining_results:
            return
        
        batch_size = 10
        batch = remaining_results[:batch_size]
        
        for i, card_data in enumerate(batch):
            row = (start_index + i) // cols
            col = (start_index + i) % cols
            card_widget = CardWidget(card_data, self)
            self.results_layout.addWidget(card_widget, row, col)
            # Update deck button state after widget is created
            if hasattr(card_widget, 'update_deck_button_state'):
                card_widget.update_deck_button_state()
        
        QApplication.processEvents()
        
        if len(remaining_results) > batch_size:
            QTimer.singleShot(50, lambda: self.load_remaining_cards(remaining_results[batch_size:], start_index + batch_size, cols))
        else:
            self.results_widget.updateGeometry()
            QApplication.processEvents()

class MainWindow(QMainWindow):
    def __init__(self):
        print("  Creating MainWindow...")
        super().__init__()
        self.setWindowTitle("MTG Collection Search")
        self.setGeometry(100, 100, 1200, 800)
        self.search_thread = None
        print("  Calling initUI...")
        self.initUI()
        print("  MainWindow created successfully.")
    
    def initUI(self):
        print("  Initializing UI components...")
        
        # Create stacked widget to switch between search and results pages
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # Create search page
        self.search_page = SearchPage()
        self.search_page.search_requested.connect(self.on_search_requested)
        
        # Create results page
        self.results_page = ResultsPage()
        
        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.search_page)
        self.stacked_widget.addWidget(self.results_page)
        
        # Show search page initially
        self.stacked_widget.setCurrentWidget(self.search_page)
        
        # Settings bar (always visible)
        settings_widget = QWidget()
        settings_widget.setStyleSheet("background-color: #f8f8f8; padding: 10px;")
        settings_layout = QHBoxLayout()
        settings_layout.setContentsMargins(20, 10, 20, 10)
        
        settings_label = QLabel("Number of Piles:")
        settings_label.setFont(QFont("Arial", 11))
        settings_label.setStyleSheet("color: black;")
        self.pile_num_spinbox = QSpinBox()
        self.pile_num_spinbox.setMinimum(1)
        self.pile_num_spinbox.setMaximum(100)
        self.pile_num_spinbox.setValue(card_handler.get_pile_num())
        self.pile_num_spinbox.setFont(QFont("Arial", 11))
        self.pile_num_spinbox.valueChanged.connect(self.update_pile_num)
        
        add_card_button = QPushButton("+ Add Card")
        add_card_button.setFont(QFont("Arial", 11))
        add_card_button.clicked.connect(self.show_add_card_dialog)
        add_card_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        
        settings_layout.addWidget(settings_label)
        settings_layout.addWidget(self.pile_num_spinbox)
        settings_layout.addStretch()
        settings_layout.addWidget(add_card_button)
        settings_widget.setLayout(settings_layout)
        
        # Add settings bar to main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(settings_widget)
        main_layout.addWidget(self.stacked_widget)
        
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        
        # Set stylesheet for the main window - Scryfall style
        self.setStyleSheet("""
            QMainWindow {
                background-color: white;
            }
            QFrame#filterSectionFrame {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background-color: #ffffff;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #b0b0b0;
                border-radius: 4px;
                background-color: white;
                color: black;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #9b59b6;
            }
            QComboBox {
                padding: 8px;
                border: 1px solid #b0b0b0;
                border-radius: 4px;
                background-color: white;
                color: black;
                font-size: 14px;
            }
            QComboBox:focus {
                border: 2px solid #9b59b6;
            }
            QComboBox::drop-down {
                border-left: 1px solid #d0d0d0;
                width: 25px;
            }
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #9b59b6;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #9b59b6;
                selection-color: white;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #666;
                width: 0;
                height: 0;
            }
            QPushButton {
                padding: 8px 20px;
                background-color: #9b59b6;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
            QPushButton:pressed {
                background-color: #7d3c98;
            }
            QSpinBox {
                padding: 5px;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: white;
                color: black;
                font-size: 14px;
            }
            QLabel {
                color: black;
            }
            QGroupBox {
                border: none;
                margin-top: 10px;
            }
            QCheckBox {
                spacing: 5px;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #9b59b6;
                border-color: #9b59b6;
            }
        """)
        
        print("  UI initialization complete.")
    
    def on_search_requested(self, query):
        """Handle search request from search page"""
        self.show_results_page()
        self.results_page.perform_search(query)
    
    def show_search_page(self):
        """Switch to search page"""
        self.stacked_widget.setCurrentWidget(self.search_page)
    
    def show_results_page(self):
        """Switch to results page"""
        self.stacked_widget.setCurrentWidget(self.results_page)
    
    def update_pile_num(self, value):
        """Update the number of piles in metadata"""
        card_handler.set_pile_num(value)
    
    def show_add_card_dialog(self):
        """Show dialog to add a card to collection"""
        dialog = AddCardDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            card_name, quantity = dialog.get_card_and_quantity()
            if card_name:
                success, message, pile = card_handler.add_card(card_name, quantity)
                if success:
                    QMessageBox.information(self, "Success", message)
                else:
                    QMessageBox.warning(self, "Error", message)

def gui():
    # Start app and create window
    print("Creating QApplication...")
    app = QApplication(sys.argv)
    print("Creating MainWindow...")
    window = MainWindow()
    print("Showing window...")
    window.show()
    print("Starting event loop...")
    sys.exit(app.exec_())

if __name__ == "__main__":
    # Ensure database is initialized when running standalone
    import table_handler
    table_handler.setup_tables()
    gui()
