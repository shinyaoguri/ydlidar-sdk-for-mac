"""
YDLiDAR T-mini Pro データ型定義
"""

from dataclasses import dataclass
from typing import List
import math


@dataclass
class LaserPoint:
    """LiDARの単一測定点データ"""
    angle: float      # 角度 (度)
    distance: float   # 距離 (メートル)
    intensity: int    # 信号強度 (0-255 or 0-1023)

    def to_cartesian(self):
        """極座標を直交座標に変換"""
        angle_rad = math.radians(self.angle)
        x = self.distance * math.cos(angle_rad)
        y = self.distance * math.sin(angle_rad)
        return x, y

    def is_valid(self):
        """有効なデータポイントか判定"""
        return self.distance > 0.0


@dataclass
class LaserScan:
    """1スキャン分のデータ（複数の測定点）"""
    points: List[LaserPoint]
    scan_frequency: float  # スキャン周波数 (Hz)
    timestamp: float       # タイムスタンプ (秒)

    def get_valid_points(self):
        """有効なポイントのみを返す"""
        return [p for p in self.points if p.is_valid()]

    def __len__(self):
        return len(self.points)
