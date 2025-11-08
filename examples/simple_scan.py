#!/usr/bin/env python3
"""
YDLiDAR T-mini Pro シンプルなスキャンサンプル

使用方法:
    python simple_scan.py /dev/tty.usbserial-xxxx
"""

import sys
import os
import argparse
import time

# ライブラリのパスを追加（開発時用）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ydlidar_tmini import TMiniDriver


def main():
    parser = argparse.ArgumentParser(description='YDLiDAR T-mini Pro シンプルスキャン')
    parser.add_argument('port', help='シリアルポート (例: /dev/tty.usbserial-xxxx)')
    parser.add_argument('--scans', type=int, default=10, help='取得するスキャン数 (デフォルト: 10)')
    parser.add_argument('--baudrate', type=int, default=230400, help='ボーレート (デフォルト: 230400)')
    parser.add_argument('--save', type=str, help='データをCSVファイルに保存')

    args = parser.parse_args()

    print(f"YDLiDAR T-mini Pro 接続中: {args.port}")

    try:
        # ドライバー初期化
        with TMiniDriver(port=args.port, baudrate=args.baudrate) as driver:
            print("接続成功！")

            # スキャン開始
            driver.start_scanning()
            print(f"\nスキャン開始... ({args.scans} スキャン取得)")

            csv_data = []

            for i in range(args.scans):
                # スキャンデータ取得
                scan = driver.get_scan(timeout=2.0)

                if scan is None:
                    print(f"  スキャン {i+1}: タイムアウト")
                    continue

                # 有効なポイント数
                valid_points = scan.get_valid_points()

                print(f"  スキャン {i+1}/{args.scans}:")
                print(f"    測定点数: {len(scan.points)} (有効: {len(valid_points)})")
                print(f"    周波数: {scan.scan_frequency:.1f} Hz")

                if len(valid_points) > 0:
                    distances = [p.distance for p in valid_points]
                    print(f"    距離範囲: {min(distances):.3f} - {max(distances):.3f} m")

                    # 最初のスキャンの詳細を表示
                    if i == 0:
                        print(f"\n  最初の10点のデータ:")
                        for j, point in enumerate(valid_points[:10]):
                            print(f"    [{j}] 角度: {point.angle:6.2f}°, "
                                  f"距離: {point.distance:.3f} m, "
                                  f"強度: {point.intensity}")

                    # CSV保存用データ
                    if args.save:
                        for point in valid_points:
                            csv_data.append([
                                i + 1,
                                point.angle,
                                point.distance,
                                point.intensity,
                                scan.timestamp
                            ])

                time.sleep(0.1)

            # CSV保存
            if args.save and csv_data:
                print(f"\nデータをCSVファイルに保存中: {args.save}")
                import csv
                with open(args.save, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Scan', 'Angle(deg)', 'Distance(m)', 'Intensity', 'Timestamp'])
                    writer.writerows(csv_data)
                print(f"保存完了: {len(csv_data)} 行")

            print(f"\n完了！ 合計スキャン数: {driver.get_scan_count()}")

    except KeyboardInterrupt:
        print("\n中断されました")
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
