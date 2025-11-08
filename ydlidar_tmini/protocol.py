"""
YDLiDAR T-mini Pro 通信プロトコル実装
"""

import struct
from typing import Optional, Tuple, List
from .types import LaserPoint, LaserScan
import time


class YDLidarProtocol:
    """T-mini Pro プロトコル処理クラス"""

    # パケットヘッダー定義
    PACKET_HEADER = bytes([0xAA, 0x55])  # リトルエンディアン: 0x55AA
    HEADER_SIZE = 10
    MAX_POINTS_PER_PACKET = 80

    # パケットタイプフラグ
    CT_ZERO_POSITION_FLAG = 0x01  # 零位包（回転開始）

    def __init__(self, has_intensity: bool = True, intensity_bit: int = 8):
        """
        Args:
            has_intensity: 強度データを含むか
            intensity_bit: 強度データのビット数 (8 or 10)
        """
        self.has_intensity = has_intensity
        self.intensity_bit = intensity_bit
        self.bytes_per_point = 3 if has_intensity else 2

    def parse_packet(self, data: bytes) -> Optional[Tuple[LaserScan, bool]]:
        """
        データパケットをパースする

        Args:
            data: パケットデータ（ヘッダー含む）

        Returns:
            (LaserScan, is_new_scan) のタプル、またはNone
            is_new_scan: 新しいスキャン（零位包）の場合True
        """
        if len(data) < self.HEADER_SIZE:
            return None

        # ヘッダー解析
        header = self._parse_header(data[:self.HEADER_SIZE])
        if header is None:
            return None

        ph, ct, lsn, fsa, lsa, cs = header

        # データ部のサイズチェック
        data_size = lsn * self.bytes_per_point
        expected_size = self.HEADER_SIZE + data_size
        if len(data) < expected_size:
            return None

        # データ部取得
        packet_data = data[self.HEADER_SIZE:self.HEADER_SIZE + data_size]

        # チェックサム検証
        if not self._verify_checksum(data[:expected_size], cs):
            return None

        # 測定点データをパース
        points = self._parse_points(packet_data, lsn, fsa, lsa)

        # スキャン周波数計算（0.1Hz単位）
        scan_frequency = (ct >> 1) * 0.1

        # 零位包（新しいスキャン）かどうか
        is_new_scan = bool(ct & self.CT_ZERO_POSITION_FLAG)

        # LaserScanオブジェクト作成
        scan = LaserScan(
            points=points,
            scan_frequency=scan_frequency,
            timestamp=time.time()
        )

        return scan, is_new_scan

    def _parse_header(self, header_data: bytes) -> Optional[Tuple]:
        """
        ヘッダー部をパース

        Returns:
            (PH, CT, LSN, FSA, LSA, CS) のタプル、またはNone
        """
        if len(header_data) != self.HEADER_SIZE:
            return None

        # ヘッダーチェック
        if header_data[0] != 0xAA or header_data[1] != 0x55:
            return None

        # フィールド解析（リトルエンディアン）
        ph = struct.unpack('<H', header_data[0:2])[0]   # 0x55AA
        ct = header_data[2]                             # パケットタイプ
        lsn = header_data[3]                            # サンプル点数
        fsa = struct.unpack('<H', header_data[4:6])[0]  # 開始角度
        lsa = struct.unpack('<H', header_data[6:8])[0]  # 終了角度
        cs = struct.unpack('<H', header_data[8:10])[0]  # チェックサム

        # サンプル点数の妥当性チェック
        if lsn < 1 or lsn > self.MAX_POINTS_PER_PACKET:
            return None

        return ph, ct, lsn, fsa, lsa, cs

    def _verify_checksum(self, packet_data: bytes, expected_cs: int) -> bool:
        """
        チェックサムを検証（公式SDK準拠）

        Args:
            packet_data: ヘッダー+データ部（チェックサム含む）
            expected_cs: 期待されるチェックサム値

        Returns:
            チェックサムが正しければTrue
        """
        # 公式SDKと同じチェックサム計算方法
        # 1. PH (0x55AA) で初期化
        cs = 0x55AA

        # 2. FSA（開始角度）をXOR
        fsa = struct.unpack('<H', packet_data[4:6])[0]
        cs ^= fsa

        # 3. データ部を2バイトずつXOR（強度なし: 2bytes/点）
        lsn = packet_data[3]
        data_start = self.HEADER_SIZE
        bytes_per_point = 3 if self.has_intensity else 2
        data_size = lsn * bytes_per_point

        if self.has_intensity:
            # 強度あり: 3バイト/点の場合
            for i in range(data_start, data_start + data_size, 3):
                if i + 2 < len(packet_data):
                    # 強度（1バイト）をXOR
                    cs ^= packet_data[i]
                    # 距離（2バイト）をワードとしてXOR
                    word = struct.unpack('<H', packet_data[i+1:i+3])[0]
                    cs ^= word
        else:
            # 強度なし: 2バイト/点の場合
            for i in range(data_start, data_start + data_size, 2):
                if i + 1 < len(packet_data):
                    word = struct.unpack('<H', packet_data[i:i+2])[0]
                    cs ^= word

        # 4. 最後に (CT + LSN) をワードとしてXOR
        ct_lsn = struct.unpack('<H', packet_data[2:4])[0]
        cs ^= ct_lsn

        # 5. LSA（終了角度）をワードとしてXOR
        lsa = struct.unpack('<H', packet_data[6:8])[0]
        cs ^= lsa

        return cs == expected_cs

    def _parse_points(self, data: bytes, lsn: int, fsa: int, lsa: int) -> List[LaserPoint]:
        """
        測定点データをパース

        Args:
            data: 測定点データ部
            lsn: サンプル点数
            fsa: 開始角度（生データ）
            lsa: 終了角度（生データ）

        Returns:
            LaserPointのリスト
        """
        points = []

        # 角度の計算（度単位）
        # FSAとLSAの bit0 は常に1で、これを除いて64で割る
        angle_fsa = (fsa >> 1) / 64.0
        angle_lsa = (lsa >> 1) / 64.0

        # 角度差の計算（360度を跨ぐ場合を考慮）
        angle_diff = angle_lsa - angle_fsa
        if angle_diff < 0:
            angle_diff += 360.0

        # 各点をパース
        for i in range(lsn):
            # 角度計算（線形補間）
            if lsn > 1:
                angle = angle_fsa + (i * angle_diff / (lsn - 1))
            else:
                angle = angle_fsa

            # 角度を0-360度の範囲に正規化
            angle = angle % 360.0

            # 距離と強度の抽出
            if self.has_intensity:
                # 強度あり: 3バイト/点
                offset = i * 3
                if offset + 2 >= len(data):
                    break

                s0 = data[offset]       # 強度バイト（下位8bit）
                s1 = data[offset + 1]   # 距離下位 + 強度上位2bit
                s2 = data[offset + 2]   # 距離上位

                # 距離抽出（上位14bit）
                raw_distance = ((s2 << 8) | s1) & 0xFFFC
                distance_mm = raw_distance / 4.0

                # 強度抽出
                if self.intensity_bit == 10:
                    # 10ビットモード
                    intensity = ((s1 & 0x03) << 8) | s0
                else:
                    # 8ビットモード
                    intensity = s0
            else:
                # 強度なし: 2バイト/点
                offset = i * 2
                if offset + 1 >= len(data):
                    break

                s0 = data[offset]
                s1 = data[offset + 1]

                # 距離抽出
                raw_distance = (s1 << 8) | s0
                distance_mm = raw_distance / 4.0
                intensity = 0

            # mm → m に変換
            distance_m = distance_mm / 1000.0

            # LaserPointオブジェクト作成
            point = LaserPoint(
                angle=angle,
                distance=distance_m,
                intensity=intensity
            )
            points.append(point)

        return points
