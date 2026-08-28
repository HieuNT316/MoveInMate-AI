"""Alert service với sliding window counter và Slack webhook.

Thresholds từ docs/OPERATIONS.md mục 4:
  - Error rate > 1% trong 5 phút → alert
  - p95 latency `/chat` > 8s → alert
  - Cost/day vượt ngưỡng → alert
  - Health check fail → alert
"""

from collections import deque
from dataclasses import dataclass, field
from threading import Lock

import requests

from src.config import get_settings
from src.observability import logger


@dataclass
class MetricWindow:
    """Một deque lưu (timestamp, value) tuples, tự evict sau 5 phút."""

    seconds: float = 300.0  # 5 phút

    timestamps: deque[tuple[float, int | float]] = field(
        default_factory=lambda: deque(maxlen=10000)
    )

    def add(self, timestamp: float, value: int | float) -> None:
        self.timestamps.append((timestamp, value))
        self._evict_old(timestamp)

    def _evict_old(self, now: float) -> None:
        cutoff = now - self.seconds
        while self.timestamps and self.timestamps[0][0] < cutoff:
            self.timestamps.popleft()

    def values(self, now: float) -> list[float]:
        self._evict_old(now)
        return [v for _, v in self.timestamps]

    def __len__(self) -> int:
        return len(self.timestamps)


class AlertService:
    """Ghi nhận metrics theo thời gian và gửi alert khi vượt ngưỡng."""

    # Các threshold cố định theo OPERATIONS.md
    ERROR_RATE_THRESHOLD = 0.01      # 1%
    LATENCY_P95_THRESHOLD_MS = 8000  # 8 giây

    def __init__(self) -> None:
        self._requests = MetricWindow()     # (timestamp, status_code)
        self._latencies = MetricWindow()    # (timestamp, duration_ms)
        self._costs = MetricWindow(seconds=86400)  # 1 ngày cho cost

        self._last_alert_time = 0.0
        self._cooldown_seconds = 300.0  # 5 phút giữa các alert

        self._health_checks = MetricWindow()  # (timestamp, is_healthy: 0/1)
        self._lock = Lock()  # Bảo vệ compound operations khỏi race condition

    def record_request(self, status_code: int) -> None:
        """Ghi nhận một request hoàn tất."""
        import time

        now = time.time()
        self._requests.add(now, status_code)

    def record_latency(self, duration_ms: float) -> None:
        """Ghi nhận độ trễ của một request."""
        import time

        now = time.time()
        self._latencies.add(now, duration_ms)

    def record_cost(self, cost_usd: float) -> None:
        """Ghi nhận chi phí của một lượt gọi API."""
        import time

        now = time.time()
        self._costs.add(now, cost_usd)

    def record_health_check(self, is_healthy: bool) -> None:
        """Ghi nhận kết quả health check."""
        import time

        now = time.time()
        self._health_checks.add(now, 1 if is_healthy else 0)

    def check_and_alert(self) -> bool:
        """Kiểm tra tất cả threshold, gửi Slack nếu cần.

        Thread-safe: dùng lock để đảm bảo cooldown check + alert send là atomic,
        tránh duplicate alerts khi nhiều request đến đồng thời.

        Returns:
            True nếu đã gửi alert, False nếu không có alert nào được kích hoạt.
        """
        import time

        with self._lock:
            now = time.time()

            # Cooldown: không alert quá thường xuyên
            if now - self._last_alert_time < self._cooldown_seconds:
                return False

            alerts: list[str] = []

            # 1. Error rate > 1% trong 5 phút
            statuses = self._requests.values(now)
            if len(statuses) >= 10:
                errors = sum(1 for s in statuses if s >= 500)
                error_rate = errors / len(statuses)
                if error_rate > self.ERROR_RATE_THRESHOLD:
                    alerts.append(
                        f"Error rate {error_rate * 100:.1f}% "
                        f"({errors}/{len(statuses)} requests) > 1% threshold"
                    )

            # 2. p95 latency > 8s
            latencies = self._latencies.values(now)
            if len(latencies) >= 10:
                sorted_latencies = sorted(latencies)
                p95_idx = int(len(sorted_latencies) * 0.95)
                p95 = sorted_latencies[p95_idx]
                if p95 > self.LATENCY_P95_THRESHOLD_MS:
                    alerts.append(
                        f"p95 latency {p95 / 1000:.1f}s > 8s threshold"
                    )

            # 3. Cost/day vượt ngưỡng
            settings = get_settings()
            day_costs = self._costs.values(now)
            day_cost = sum(day_costs)
            if day_cost > settings.alert_cost_daily_threshold:
                alerts.append(
                    f"Cost today ${day_cost:.2f} > "
                    f"${settings.alert_cost_daily_threshold} threshold"
                )

            # 4. Health check fail liên tục (3 lần liên tiếp)
            health_values = self._health_checks.values(now)
            if len(health_values) >= 3 and sum(health_values[-3:]) == 0:
                alerts.append("Health check failed 3 times in a row")

            if alerts:
                self._send_slack(alerts)
                self._last_alert_time = now
                return True

            return False

    def _send_slack(self, alerts: list[str]) -> None:
        """Gửi thông báo tới Slack webhook."""
        settings = get_settings()
        if not settings.slack_webhook_url:
            logger.warning(
                "slack_alert_skipped_no_webhook",
                extra={"alerts": alerts},
            )
            return

        lines = "\n".join(f"• {a}" for a in alerts)
        payload = {"text": f"MoveInMate Alert\n{lines}"}

        try:
            r = requests.post(
                settings.slack_webhook_url,
                json=payload,
                timeout=5,
            )
            if r.status_code != 200:
                logger.warning(
                    "slack_alert_failed",
                    extra={
                        "status_code": r.status_code,
                        "response": r.text[:200],
                    },
                )
        except requests.RequestException as e:
            logger.warning("slack_alert_failed", extra={"error": str(e)})

    # --- Prometheus metrics helpers ---

    def error_rate(self) -> float:
        """Tỷ lệ lỗi 5xx trong 5 phút (0.0 - 1.0)."""
        import time

        now = time.time()
        statuses = self._requests.values(now)
        if not statuses:
            return 0.0
        errors = sum(1 for s in statuses if s >= 500)
        return errors / len(statuses)

    def p95_latency_ms(self) -> float:
        """p95 độ trễ trong 5 phút (ms)."""
        import time

        now = time.time()
        latencies = self._latencies.values(now)
        if len(latencies) < 10:
            return 0.0
        sorted_latencies = sorted(latencies)
        return sorted_latencies[int(len(sorted_latencies) * 0.95)]

    def total_cost_today(self) -> float:
        """Tổng chi phí trong 24 giờ ($)."""
        import time

        now = time.time()
        return sum(self._costs.values(now))

    def request_count(self) -> int:
        """Số request trong 5 phút."""
        import time

        return len(self._requests.values(time.time()))


# Singleton instance — khởi tạo khi import, gắn vào app lifecycle trong main.py
_alert_service: AlertService | None = None


def get_alert_service() -> AlertService:
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
    return _alert_service
