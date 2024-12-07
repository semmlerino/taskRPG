"""Styles for the settings dialog."""

TABLE_STYLE = """
    QTableView {
        selection-background-color: #A7C7E7;
        selection-color: #2c456b;
        alternate-background-color: #EDF5FF;
        background-color: white;
        font-size: 13pt;
        gridline-color: #D0D0D0;
    }
    QTableView::item {
        border: none;
        padding: 5px;
        color: #2c456b;
    }
    QTableView::item:selected {
        background-color: #A7C7E7;
        color: #2c456b;
    }
    QTableView::indicator {
        width: 20px;
        height: 20px;
        border: 2px solid #BDBDBD;
        border-radius: 4px;
        background-color: white;
    }
    QTableView::indicator:hover {
        border-color: #2196F3;
        background-color: #E3F2FD;
    }
    QTableView::indicator:checked {
        background-color: #2196F3;
        border: 2px solid #2196F3;
        border-radius: 4px;
    }
    QTableView::indicator:checked:hover {
        background-color: #1976D2;
        border-color: #1976D2;
    }
    QTableView::indicator:unchecked:hover {
        border-color: #2196F3;
        background-color: #E3F2FD;
    }
"""

HEADER_STYLE = """
    QHeaderView::section {
        padding: 6px;
        background-color: #A7C7E7;
        color: #2c456b;
        border: 1px solid #2c456b;
        font-weight: bold;
    }
"""

VERTICAL_HEADER_STYLE = """
    QHeaderView::section {
        background-color: #F5F5F5;
        padding: 4px;
        border: 1px solid #E0E0E0;
    }
"""

ADD_BUTTON_STYLE = """
    QPushButton {
        background-color: #BDECC4;
        color: #2E7D32;
        padding: 10px 20px;
        border: none;
        border-radius: 5px;
        min-width: 120px;
    }
    QPushButton:hover { background-color: #A5D6A7; }
    QPushButton:pressed { background-color: #C8E6C9; }
"""

REMOVE_BUTTON_STYLE = """
    QPushButton {
        background-color: #FFD7D9;
        color: #C62828;
        padding: 10px 20px;
        border: none;
        border-radius: 5px;
        min-width: 120px;
    }
    QPushButton:hover { background-color: #FFCDD2; }
    QPushButton:pressed { background-color: #FFEBEE; }
"""

SAVE_BUTTON_STYLE = """
    QPushButton {
        background-color: #D6EAFF;
        color: #1565C0;
        padding: 10px 20px;
        border: none;
        border-radius: 5px;
        min-width: 120px;
    }
    QPushButton:hover { background-color: #BBDEFB; }
    QPushButton:pressed { background-color: #E3F2FD; }
"""

CANCEL_BUTTON_STYLE = """
    QPushButton {
        background-color: #EDF2F7;
        color: #4A5568;
        padding: 10px 20px;
        border: none;
        border-radius: 5px;
        min-width: 120px;
    }
    QPushButton:hover { background-color: #E2E8F0; }
    QPushButton:pressed { background-color: #F7FAFC; }
"""

CHECKBOX_STYLE = """
    QCheckBox {
        spacing: 10px;
        padding: 5px;
    }
    QCheckBox::indicator {
        width: 20px;
        height: 20px;
        border: 2px solid #BDBDBD;
        border-radius: 4px;
        background-color: white;
    }
    QCheckBox::indicator:hover {
        border-color: #2196F3;
        background-color: #E3F2FD;
    }
    QCheckBox::indicator:checked {
        background-color: #90CAF9;
        border: 2px solid #90CAF9;
        border-radius: 4px;
    }
    QCheckBox::indicator:checked:hover {
        background-color: #64B5F6;
        border-color: #64B5F6;
    }
    QCheckBox::indicator:unchecked:hover {
        border-color: #2196F3;
        background-color: #E3F2FD;
    }
"""
