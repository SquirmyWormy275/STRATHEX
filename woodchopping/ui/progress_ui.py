"""Progress UI helpers for long-running operations."""

from dataclasses import dataclass

from woodchopping.ui.terminal_rendering import (
    display_width,
    fit_display,
    install_terminal_output,
    sanitize_text,
    truncate_display,
)

# MainProgram imports ProgressDisplay before rendering its first banner. Installing
# here keeps the large legacy entry point untouched and makes all subsequent
# judge-facing output use the same width rules.
install_terminal_output()


@dataclass
class ProgressDisplay:
    title: str
    width: int = 70
    bar_length: int = 30
    item_label: str = "items"
    detail_label: str = "Processing"
    min_percent_delta: int = 1
    _started: bool = False
    _last_percent: int = -1
    _last_current: int = 0
    _last_total: int = 0

    def start(self) -> None:
        width = max(20, int(self.width))
        print("\n" + "-" * width)
        print(fit_display(sanitize_text(self.title), width, align="center"))
        print("-" * width)
        self._started = True
        self._last_percent = -1

    def _format_line(
        self,
        percent: int,
        current: int,
        total: int,
        detail_text: str,
    ) -> str:
        width = max(20, int(self.width))
        item_label = sanitize_text(self.item_label)
        detail_label = sanitize_text(self.detail_label)

        without_bar = f"  [] {percent:3d}% | {current}/{total} {item_label} | {detail_label}: "
        # Reserve a small readable detail area and shrink the bar before
        # truncating labels or status text.
        minimum_detail_width = min(10, max(3, width // 7))
        available_for_bar = width - display_width(without_bar) - minimum_detail_width
        actual_bar_length = max(3, min(int(self.bar_length), available_for_bar))

        filled = int((actual_bar_length * current) / total) if total > 0 else 0
        filled = max(0, min(actual_bar_length, filled))
        bar = "#" * filled + "-" * (actual_bar_length - filled)

        prefix = f"  [{bar}] {percent:3d}% | {current}/{total} {item_label} | {detail_label}: "
        detail_width = max(0, width - display_width(prefix))
        detail = truncate_display(sanitize_text(detail_text), detail_width)
        return fit_display(prefix + detail, width)

    def update(self, current: int, total: int, detail: str = "") -> None:
        if not self._started:
            self.start()

        percent = int((current / total) * 100) if total > 0 else 0
        if percent == self._last_percent and current != total:
            return
        if (percent - self._last_percent) < self.min_percent_delta and current != total:
            return

        self._last_percent = percent
        self._last_current = current
        self._last_total = total
        detail_text = detail if detail else "..."
        print(self._format_line(percent, current, total, detail_text))

    def finish(self, message: str) -> None:
        if not self._started:
            self.start()

        total = self._last_total if self._last_total else 1
        print(self._format_line(100, total, total, message))
        print("-" * max(20, int(self.width)))
