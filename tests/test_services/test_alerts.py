"""Tests for AlertService (src/services/alerts.py).

Fixtures tao mo truong co metrics nhanh: ghi truc tiep vao
in-memory deque cua AlertService, khong can mock time.
"""

import time

from src.services.alerts import AlertService, MetricWindow


class TestMetricWindow:
    """Test MetricWindow helper class."""

    def test_add_and_evict(self):
        """Gia tri cu hon 5 phut bi loai bo, gia tri trong cua so duoc giu.

        Ghi theo dung thu tu thoi gian (cu truoc, moi sau) vi `_evict_old`
        chi `popleft` tu dau deque — no dua tren gia dinh thoi gian luon
        tang dan, dung voi moi call site that (`add` luon dung `time.time()`
        hien tai). Nhet mot ban ghi CU vao CUOI deque la tinh huong khong
        the xay ra trong san pham.
        """
        mw = MetricWindow(seconds=300.0)
        now = time.time()

        mw.add(now - 400, 2)  # ngoai cua so
        mw.add(now, 1)        # trong cua so

        assert len(mw) == 1
        assert [v for _, v in mw.timestamps] == [1]

    def test_values_returns_all_trong_cua_so(self):
        """values() tra danh sach gia tri trong cua so."""
        mw = MetricWindow(seconds=300.0)
        now = time.time()
        mw.add(now, 100)
        mw.add(now, 200)
        assert sorted(mw.values(now)) == [100, 200]

    def test_values_loai_bo_gia_tri_cu(self):
        """values() goi _evict_old ben trong."""
        mw = MetricWindow(seconds=300.0)
        now = time.time()
        mw.add(now - 400, 999)  # ngoai cua so, ghi truoc theo dung thu tu
        mw.add(now, 100)
        assert mw.values(now) == [100]


class TestAlertServiceInit:
    """Test khoi tao AlertService."""

    def test_khoi_tao_khong_co_metrics(self):
        """Luc dau, khong co metrics nao."""
        svc = AlertService()
        assert svc._last_alert_time == 0.0
        assert svc._cooldown_seconds == 300.0
        assert len(svc._requests) == 0
        assert len(svc._latencies) == 0
        assert len(svc._costs) == 0

    def test_thresholds_mac_dinh(self):
        """Thresholds tu OPERATIONS.md."""
        svc = AlertService()
        assert svc.ERROR_RATE_THRESHOLD == 0.01
        assert svc.LATENCY_P95_THRESHOLD_MS == 8000


class TestRecordRequest:
    """Test record_request."""

    def test_ghi_nhan_request_thanh_cong(self):
        """Request thanh cong (2xx) duoc ghi nhan."""
        svc = AlertService()
        svc.record_request(200)
        svc.record_request(201)
        assert len(svc._requests) == 2

    def test_ghi_nhan_request_loi(self):
        """Request loi (5xx) duoc ghi nhan."""
        svc = AlertService()
        svc.record_request(500)
        svc.record_request(503)
        assert len(svc._requests) == 2


class TestRecordLatency:
    """Test record_latency."""

    def test_ghi_nhan_latency(self):
        """Latency duoc ghi nhan dung dinh dang."""
        svc = AlertService()
        svc.record_latency(150.5)
        svc.record_latency(3200.0)
        assert len(svc._latencies) == 2


class TestRecordCost:
    """Test record_cost."""

    def test_ghi_nhan_cost(self):
        """Cost duoc ghi nhan voi thoi gian."""
        svc = AlertService()
        svc.record_cost(0.05)
        svc.record_cost(0.10)
        assert len(svc._costs) == 2


class TestErrorRateThreshold:
    """Test nguong error rate > 1%."""

    def test_error_rate_duoi_1_khong_alert(self):
        """1% loi hoac thap hon khong trigger alert."""
        svc = AlertService()
        for _ in range(99):
            svc.record_request(200)
        svc.record_request(500)  # 1% loi
        assert svc.check_and_alert() is False

    def test_error_rate_tren_1_alert(self):
        """Tren 1% loi trigger alert."""
        svc = AlertService()
        for _ in range(49):
            svc.record_request(200)
        svc.record_request(500)  # 2% loi
        svc.record_request(500)
        assert svc.check_and_alert() is True

    def test_it_du_lieu_khong_alert(self):
        """Duoi 10 request khong alert du ty le loi cao.

        Nguong toi thieu la 10 mau (`len(statuses) >= 10`), nen 9 request
        voi 4 loi (44%) van phai im lang — mot vai loi luc khoi dong khong
        phai bang chung he thong dang hong.
        """
        svc = AlertService()
        for _ in range(5):
            svc.record_request(200)
        for _ in range(4):
            svc.record_request(500)
        assert svc.check_and_alert() is False


class TestLatencyThreshold:
    """Test nguong p95 latency > 8s."""

    def test_latency_duoi_8s_khong_alert(self):
        """Tat ca latencies duoi 8s khong trigger."""
        svc = AlertService()
        for _ in range(50):
            svc.record_latency(1000.0)  # 1s
        assert svc.check_and_alert() is False

    def test_latency_tren_8s_alert(self):
        """p95 > 8s trigger alert.

        Can it nhat 3 mau cham tren nen 50 mau nhanh: p95 lay phan tu thu
        `int(n * 0.95)`, voi n=53 la vi tri 50 — chi 1-2 mau cham thi vi tri
        do van roi vao vung 1s va nguong khong kich hoat. Dung nhu thiet ke:
        mot request cham don le khong phai su co.
        """
        svc = AlertService()
        for _ in range(50):
            svc.record_latency(1000.0)  # 1s
        for _ in range(3):
            svc.record_latency(9000.0)  # 9s
        assert svc.check_and_alert() is True


class TestCostThreshold:
    """Test nguong chi phi ngay."""

    def test_cost_duoi_nguong_khong_alert(self, monkeypatch):
        """Chi phi duoi $10/ngay khong alert."""
        import src.services.alerts as alerts_mod

        monkeypatch.setattr(alerts_mod, "get_settings", lambda: _FakeSettings(10.0))
        svc = AlertService()
        svc.record_cost(5.0)
        svc.record_cost(4.0)
        assert svc.check_and_alert() is False

    def test_cost_vuot_nguong_alert(self, monkeypatch):
        """Chi phi tren $10/ngay trigger alert."""
        import src.services.alerts as alerts_mod

        monkeypatch.setattr(alerts_mod, "get_settings", lambda: _FakeSettings(10.0))
        svc = AlertService()
        svc.record_cost(11.0)
        assert svc.check_and_alert() is True


class TestHealthCheck:
    """Test ghi nhan health check."""

    def test_healthy_duoc_ghi_nhan(self):
        """Health check thanh cong duoc ghi nhan."""
        svc = AlertService()
        svc.record_health_check(True)
        assert len(svc._health_checks) == 1

    def test_unhealthy_duoc_ghi_nhan(self):
        """Health check that bai duoc ghi nhan."""
        svc = AlertService()
        svc.record_health_check(False)
        assert len(svc._health_checks) == 1


class TestCooldown:
    """Test cooldow giua cac alert."""

    def test_alert_trong_cooldown_khong_gui(self):
        """Alert trong 5 phut khong gui lan nua."""
        svc = AlertService()
        # Trigger mot alert
        for _ in range(50):
            svc.record_request(500)
        assert svc.check_and_alert() is True

        # Thu ngay sau - trong cooldown
        for _ in range(50):
            svc.record_request(500)
        assert svc.check_and_alert() is False

    def test_alert_sau_cooldown_gui_duoc(self):
        """Sau 5 phut co the alert lai."""
        svc = AlertService()
        # Trigger mot alert
        for _ in range(50):
            svc.record_request(500)
        svc.check_and_alert()

        # Gia lap thoi gian troi qua
        svc._last_alert_time = time.time() - 400  # 6+ phut truoc
        for _ in range(50):
            svc.record_request(500)
        assert svc.check_and_alert() is True


class TestPrometheusHelpers:
    """Test cac ham tra ve metric cho Prometheus."""

    def test_error_rate_tinh_dung(self):
        """error_rate() tra gia tri 0.0 - 1.0."""
        svc = AlertService()
        for _ in range(90):
            svc.record_request(200)
        svc.record_request(500)  # 1% loi
        svc.record_request(500)  # 2% loi
        assert 0.01 < svc.error_rate() <= 0.03

    def test_error_rate_khong_co_du_lieu(self):
        """Khong co du lieu tra 0.0."""
        svc = AlertService()
        assert svc.error_rate() == 0.0

    def test_p95_latency_khong_du_du_lieu(self):
        """Duoi 10 latencies tra 0.0."""
        svc = AlertService()
        svc.record_latency(100.0)
        svc.record_latency(200.0)
        assert svc.p95_latency_ms() == 0.0

    def test_p95_latency_tinh_dung(self):
        """p95 duoc tinh dung."""
        svc = AlertService()
        for i in range(100):
            svc.record_latency(float(i * 100))  # 0, 100, 200, ...
        p95 = svc.p95_latency_ms()
        # p95 cua 100 gia tri la gia tri tai vi tri 95
        assert p95 > 9000  # phai lon hon 9s
        assert p95 < 10000

    def test_total_cost_today(self):
        """total_cost_today() tra tong chi phi."""
        svc = AlertService()
        svc.record_cost(1.5)
        svc.record_cost(2.5)
        assert svc.total_cost_today() == 4.0

    def test_request_count(self):
        """request_count() tra so request trong cua so."""
        svc = AlertService()
        svc.record_request(200)
        svc.record_request(200)
        svc.record_request(500)
        assert svc.request_count() == 3


class _FakeSettings:
    """Fake Settings cho test khong phu thuoc config thuc."""

    def __init__(self, daily_threshold: float = 10.0):
        self.alert_cost_daily_threshold = daily_threshold
        self.slack_webhook_url = ""
