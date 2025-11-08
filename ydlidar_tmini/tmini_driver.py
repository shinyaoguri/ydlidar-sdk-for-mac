"""
YDLiDAR T-mini Pro ドライバー
"""

import serial
import threading
import time
from typing import Optional, Callable
from queue import Queue, Empty
from .protocol import YDLidarProtocol
from .types import LaserScan


class TMiniDriver:
    """YDLiDAR T-mini Pro ドライバークラス"""

    # デフォルト設定
    DEFAULT_BAUDRATE = 230400
    DEFAULT_TIMEOUT = 1.0

    def __init__(self,
                 port: str,
                 baudrate: int = DEFAULT_BAUDRATE,
                 has_intensity: bool = True,
                 intensity_bit: int = 8):
        """
        Args:
            port: シリアルポート (例: '/dev/tty.usbserial-xxxx')
            baudrate: ボーレート (デフォルト: 230400)
            has_intensity: 強度データを使用するか
            intensity_bit: 強度データのビット数 (8 or 10)
        """
        self.port = port
        self.baudrate = baudrate
        self.serial_conn: Optional[serial.Serial] = None
        self.protocol = YDLidarProtocol(has_intensity, intensity_bit)

        # スレッド制御
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._scan_queue = Queue(maxsize=10)

        # スキャンコールバック
        self._scan_callback: Optional[Callable[[LaserScan], None]] = None

        # スキャン統計
        self._current_scan_points = []
        self._scan_count = 0

    def connect(self) -> bool:
        """
        シリアルポートに接続

        Returns:
            接続成功ならTrue
        """
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.DEFAULT_TIMEOUT,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )

            # バッファをクリア
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()

            print(f"シリアルポート {self.port} に接続しました")
            return True

        except serial.SerialException as e:
            print(f"シリアルポート接続エラー: {e}")
            return False

    def disconnect(self):
        """シリアルポートから切断"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("シリアルポート切断")

    def start_scanning(self, callback: Optional[Callable[[LaserScan], None]] = None):
        """
        スキャン開始

        Args:
            callback: スキャン完了時に呼ばれるコールバック関数
        """
        if self._running:
            print("既にスキャン中です")
            return

        if not self.serial_conn or not self.serial_conn.is_open:
            print("シリアルポートが接続されていません")
            return

        self._scan_callback = callback
        self._running = True
        self._thread = threading.Thread(target=self._scan_thread, daemon=True)
        self._thread.start()
        print("スキャン開始")

    def stop_scanning(self):
        """スキャン停止"""
        if not self._running:
            return

        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print("スキャン停止")

    def get_scan(self, timeout: float = 1.0) -> Optional[LaserScan]:
        """
        スキャンデータを取得（キューから）

        Args:
            timeout: タイムアウト時間（秒）

        Returns:
            LaserScanオブジェクト、またはNone
        """
        try:
            return self._scan_queue.get(timeout=timeout)
        except Empty:
            return None

    def _scan_thread(self):
        """スキャンスレッド（バックグラウンド処理）"""
        buffer = bytearray()

        while self._running:
            try:
                # データ読み込み
                if self.serial_conn.in_waiting > 0:
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    buffer.extend(data)

                    # パケット処理
                    self._process_buffer(buffer)
                else:
                    # データが無い場合、少し待機
                    time.sleep(0.001)

            except serial.SerialException as e:
                print(f"シリアル読み込みエラー: {e}")
                break
            except Exception as e:
                print(f"スキャンスレッドエラー: {e}")
                break

    def _process_buffer(self, buffer: bytearray):
        """
        バッファ内のデータを処理してパケットを抽出

        Args:
            buffer: 受信データバッファ
        """
        while len(buffer) >= YDLidarProtocol.HEADER_SIZE:
            # パケットヘッダーを探す
            header_idx = self._find_header(buffer)
            if header_idx == -1:
                # ヘッダーが見つからない場合、バッファをクリア
                buffer.clear()
                break

            # ヘッダーの前のデータを削除
            if header_idx > 0:
                del buffer[:header_idx]

            # パケットサイズを予測（最大サイズで試す）
            max_packet_size = YDLidarProtocol.HEADER_SIZE + \
                             (YDLidarProtocol.MAX_POINTS_PER_PACKET * 3)

            if len(buffer) < YDLidarProtocol.HEADER_SIZE:
                # まだヘッダー全体が揃っていない
                break

            # LSN（サンプル点数）を取得してパケットサイズを正確に計算
            lsn = buffer[3]
            bytes_per_point = 3 if self.protocol.has_intensity else 2
            packet_size = YDLidarProtocol.HEADER_SIZE + (lsn * bytes_per_point)

            if len(buffer) < packet_size:
                # パケット全体が揃っていない
                break

            # パケットを抽出
            packet_data = bytes(buffer[:packet_size])
            del buffer[:packet_size]

            # パケットをパース
            result = self.protocol.parse_packet(packet_data)
            if result is not None:
                scan, is_new_scan = result

                # 測定点を蓄積
                self._current_scan_points.extend(scan.points)

                # 零位包（新しいスキャン）の場合、完成したスキャンを出力
                if is_new_scan and len(self._current_scan_points) > 0:
                    complete_scan = LaserScan(
                        points=self._current_scan_points,
                        scan_frequency=scan.scan_frequency,
                        timestamp=scan.timestamp
                    )

                    # コールバック呼び出し
                    if self._scan_callback:
                        try:
                            self._scan_callback(complete_scan)
                        except Exception as e:
                            print(f"コールバックエラー: {e}")

                    # キューに追加
                    try:
                        self._scan_queue.put_nowait(complete_scan)
                    except:
                        # キューが満杯の場合、古いデータを削除
                        try:
                            self._scan_queue.get_nowait()
                            self._scan_queue.put_nowait(complete_scan)
                        except:
                            pass

                    self._scan_count += 1
                    self._current_scan_points = []

    def _find_header(self, buffer: bytearray) -> int:
        """
        バッファ内でパケットヘッダーを探す

        Args:
            buffer: 検索対象のバッファ

        Returns:
            ヘッダーの開始インデックス、見つからない場合は-1
        """
        for i in range(len(buffer) - 1):
            if buffer[i] == 0xAA and buffer[i + 1] == 0x55:
                return i
        return -1

    def get_scan_count(self) -> int:
        """完了したスキャン数を取得"""
        return self._scan_count

    def is_scanning(self) -> bool:
        """スキャン中かどうか"""
        return self._running

    def __enter__(self):
        """コンテキストマネージャー: with文のサポート"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー: クリーンアップ"""
        self.stop_scanning()
        self.disconnect()
