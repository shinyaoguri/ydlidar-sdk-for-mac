#!/usr/bin/env python3
"""
YDLiDAR T-mini Pro デモスナップショット生成

デモデータの静止画を生成します。

使用方法:
    python demo_snapshot.py output.png
"""

import sys
import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import math

# 日本語フォント設定（Mac用）
matplotlib.rcParams['font.family'] = 'Hiragino Sans'

# ライブラリのパスを追加（開発時用）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ydlidar_tmini import LaserScan, LaserPoint


def generate_demo_scan() -> LaserScan:
    """デモスキャンデータを生成"""
    points = []

    # 360度をカバーする測定点を生成
    num_points = 400
    for i in range(num_points):
        angle = (i * 360.0 / num_points) % 360.0

        # 複数の物体をシミュレート
        distance = simulate_environment(angle)

        # 距離に基づいて強度を計算（近いほど強い）
        if distance > 0:
            intensity = int(255 * (1.0 - min(distance / 10.0, 1.0)))
        else:
            intensity = 0

        points.append(LaserPoint(
            angle=angle,
            distance=distance,
            intensity=intensity
        ))

    import time
    return LaserScan(
        points=points,
        scan_frequency=6.0,
        timestamp=time.time()
    )


def simulate_environment(angle: float) -> float:
    """環境をシミュレート（複数の物体）"""

    # 物体1: 正面の壁（90度付近）
    if 60 <= angle <= 120:
        wall_distance = 2.5 + 0.3 * math.sin(math.radians(angle * 4))
        return wall_distance

    # 物体2: 右側の柱（45度付近）
    angle_diff = abs(angle - 45)
    if angle_diff < 10:
        pillar_distance = 1.5 + 0.5 * (angle_diff / 10.0)
        return pillar_distance

    # 物体3: 左側の柱（135度付近）
    angle_diff = abs(angle - 135)
    if angle_diff < 10:
        pillar_distance = 1.5 + 0.5 * (angle_diff / 10.0)
        return pillar_distance

    # 物体4: 後方の壁（270度付近）
    if 240 <= angle <= 300:
        back_wall_distance = 4.0 + 0.5 * math.cos(math.radians(angle * 3))
        return back_wall_distance

    # 物体5: 床（下方向、180度付近）
    if 150 <= angle <= 210:
        floor_distance = 1.0 + 0.2 * math.sin(math.radians(angle * 6))
        return floor_distance

    # その他: ランダムなノイズ（遠方）
    if np.random.random() < 0.1:
        return 8.0 + np.random.random() * 2.0

    # 検出なし
    return 0.0


def create_visualization(scan: LaserScan, output_path: str, max_range: float = 10.0):
    """可視化画像を生成"""

    # 有効なポイントのみ抽出
    points = scan.get_valid_points()

    if len(points) == 0:
        print("有効なデータポイントがありません")
        return

    # データ抽出
    angles = np.array([np.radians(p.angle) for p in points])
    distances = np.array([p.distance for p in points])
    intensities = np.array([p.intensity for p in points])

    # 距離範囲でフィルタ
    valid_mask = (distances > 0) & (distances <= max_range)
    angles = angles[valid_mask]
    distances = distances[valid_mask]
    intensities = intensities[valid_mask]

    # プロット作成
    fig, ax = plt.subplots(figsize=(12, 12), subplot_kw=dict(projection='polar'))

    # 設定
    ax.set_ylim(0, max_range)
    ax.set_theta_zero_location('N')  # 0度を上に
    ax.set_theta_direction(-1)  # 時計回り
    ax.set_title('YDLiDAR T-mini Pro - Demo Scan', pad=20, fontsize=16, fontweight='bold')
    ax.grid(True, alpha=0.3, linewidth=1.5)

    # 測定点をプロット
    scatter = ax.scatter(angles, distances, c=distances, s=20, cmap='jet', alpha=0.8, edgecolors='black', linewidth=0.5)

    # カラーバー
    cbar = plt.colorbar(scatter, ax=ax, pad=0.1)
    cbar.set_label('Distance (m)', rotation=270, labelpad=20, fontsize=12)

    # 統計情報
    stats_text = f"Scan Statistics:\n"
    stats_text += f"  Total Points: {len(scan.points)}\n"
    stats_text += f"  Valid Points: {len(points)}\n"
    stats_text += f"  Scan Frequency: {scan.scan_frequency:.1f} Hz\n"
    stats_text += f"  Distance Range: {distances.min():.2f} - {distances.max():.2f} m\n"
    stats_text += f"  Mean Distance: {distances.mean():.2f} m\n"
    stats_text += f"  Intensity Range: {intensities.min()} - {intensities.max()}"

    ax.text(0.02, 0.98, stats_text, transform=fig.transFigure,
            verticalalignment='top', fontsize=10,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    # 保存
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"画像を保存しました: {output_path}")
    print(f"  画像サイズ: {fig.get_size_inches()[0]*150:.0f} x {fig.get_size_inches()[1]*150:.0f} pixels")
    print(f"  測定点数: {len(points)}")

    plt.close()


def main():
    parser = argparse.ArgumentParser(description='YDLiDAR T-mini Pro デモスナップショット生成')
    parser.add_argument('output', nargs='?', default='lidar_demo.png', help='出力画像ファイル名 (デフォルト: lidar_demo.png)')
    parser.add_argument('--max-range', type=float, default=10.0, help='表示最大距離 [m] (デフォルト: 10.0)')

    args = parser.parse_args()

    print("デモLiDARスキャンデータを生成中...")

    # デモデータ生成
    scan = generate_demo_scan()

    print(f"スキャンデータ生成完了:")
    print(f"  測定点数: {len(scan.points)}")
    print(f"  有効点数: {len(scan.get_valid_points())}")
    print(f"  スキャン周波数: {scan.scan_frequency} Hz")

    # 可視化画像生成
    print(f"\n可視化画像を生成中...")
    create_visualization(scan, args.output, args.max_range)

    print("\n完了！")


if __name__ == '__main__':
    main()
