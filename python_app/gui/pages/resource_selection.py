from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QTableWidget


class PageSelection:
    def __init__(
        self,
        table: QTableWidget,
        selected_names: set[str],
        get_visible_names: Callable[[], list[str]],
        on_changed: Callable[[], None],
    ) -> None:
        self._table = table
        self._selected_names = selected_names
        self._get_visible_names = get_visible_names
        self._on_changed = on_changed

    def configure_header_checkbox(self) -> None:
        item = self._table.horizontalHeaderItem(0)
        if item is None:
            return
        item.setText("")
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        item.setData(Qt.ItemDataRole.CheckStateRole, Qt.CheckState.Unchecked)
        item.setToolTip("勾选/取消勾选当前页全部条目")
        self._table.horizontalHeader().sectionClicked.connect(self._handle_header_clicked)

    def update_header_state(self) -> None:
        item = self._table.horizontalHeaderItem(0)
        if item is None:
            return
        names = self._get_visible_names()
        if not names:
            item.setData(Qt.ItemDataRole.CheckStateRole, Qt.CheckState.Unchecked)
            return
        selected = sum(1 for name in names if name in self._selected_names)
        if selected == 0:
            state = Qt.CheckState.Unchecked
        elif selected == len(names):
            state = Qt.CheckState.Checked
        else:
            state = Qt.CheckState.PartiallyChecked
        item.setData(Qt.ItemDataRole.CheckStateRole, state)

    def _handle_header_clicked(self, section: int) -> None:
        if section != 0:
            return
        item = self._table.horizontalHeaderItem(0)
        if item is None:
            return
        state = item.data(Qt.ItemDataRole.CheckStateRole) or Qt.CheckState.Unchecked
        self._set_visible_selected(state != Qt.CheckState.Checked)

    def _set_visible_selected(self, checked: bool) -> None:
        names = self._get_visible_names()
        if checked:
            self._selected_names |= set(names)
        else:
            self._selected_names -= set(names)
        for row_index, name in enumerate(names):
            wrapper = self._table.cellWidget(row_index, 0)
            checkbox = wrapper.findChild(QCheckBox) if wrapper else None
            if checkbox is None:
                continue
            checkbox.blockSignals(True)
            checkbox.setChecked(name in self._selected_names)
            checkbox.blockSignals(False)
        self.update_header_state()
        self._on_changed()

