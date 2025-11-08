"""
YDLiDAR T-mini Pro Mac用ドライバーライブラリ

使用例:
    from ydlidar_tmini import TMiniDriver, LaserScan, LaserPoint

    with TMiniDriver('/dev/tty.usbserial-xxxx') as lidar:
        lidar.start_scanning()
        scan = lidar.get_scan(timeout=2.0)
        if scan:
            for point in scan.get_valid_points():
                print(f"Angle: {point.angle:.2f}, Distance: {point.distance:.3f}m")
"""

from .tmini_driver import TMiniDriver
from .types import LaserPoint, LaserScan
from .protocol import YDLidarProtocol

__version__ = '1.0.0'
__all__ = ['TMiniDriver', 'LaserPoint', 'LaserScan', 'YDLidarProtocol']
