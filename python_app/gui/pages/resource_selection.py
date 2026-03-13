from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QTableWidget

from ..header_views import GroupedHeaderView


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
        header = self._table.horizontalHeader()
        if not isinstance(header, GroupedHeaderView):
            return
        header.enable_checkbox(0)
        header.checkbox_state_changed.connect(self._handle_header_checkbox_changed)

    def update_header_state(self) -> None:
        header = self._table.horizontalHeader()
        if not isinstance(header, GroupedHeaderView):
            return
        names = self._get_visible_names()
        if not names:
            header.set_checkbox_state(0, Qt.CheckState.Unchecked)
            return
        selected = sum(1 for name in names if name in self._selected_names)
        if selected == 0:
            state = Qt.CheckState.Unchecked
        elif selected == len(names):
            state = Qt.CheckState.Checked
        else:
            state = Qt.CheckState.PartiallyChecked
        header.set_checkbox_state(0, state)

    def _handle_header_checkbox_changed(self, section: int, state_value: int) -> None:
        if section != 0:
            return
        state = Qt.CheckState(state_value)
        self._set_visible_selected(state == Qt.CheckState.Checked)

    def _set_visible_selected(self, checked: bool) -> None:
        names = self._get_visible_names()
        if checked:
            self._selected_names |= set(names)
        else:
            self._selected_names -= set(names)
        for row_index in range(self._table.rowCount()):
            wrapper = self._table.cellWidget(row_index, 0)
            if not wrapper:
                continue
            checkbox = wrapper.findChild(QCheckBox)
            if checkbox is None:
                continue
            checkbox.blockSignals(True)
            checkbox.setChecked(checked)
            checkbox.blockSignals(False)
        self.update_header_state()
        self._on_changed()
