"""TMiniDriver のスキャン開始・停止コマンド送信のテスト"""

from ydlidar_tmini import TMiniDriver

START_SCAN = bytes([0xA5, 0x60])
STOP_SCAN = bytes([0xA5, 0x65])


class FakeSerial:
    """書き込まれたバイト列を記録するだけのシリアルポート代替"""

    def __init__(self):
        self.written = bytearray()
        self.is_open = True
        self.in_waiting = 0

    def write(self, data):
        self.written.extend(data)
        return len(data)

    def flush(self):
        pass

    def reset_input_buffer(self):
        pass

    def read(self, size=1):
        return b""

    def close(self):
        self.is_open = False


def make_driver():
    driver = TMiniDriver("/dev/null")
    driver.serial_conn = FakeSerial()
    return driver


def test_start_scanning_sends_start_command():
    driver = make_driver()
    driver.start_scanning()
    try:
        assert driver.serial_conn.written.endswith(START_SCAN)
    finally:
        driver.stop_scanning()


def test_stop_scanning_sends_stop_command():
    driver = make_driver()
    driver.start_scanning()
    driver.stop_scanning()
    assert driver.serial_conn.written.endswith(STOP_SCAN)
    assert not driver.is_scanning()


def test_start_scanning_without_connection_sends_nothing():
    driver = TMiniDriver("/dev/null")
    driver.start_scanning()
    assert not driver.is_scanning()
