#!/usr/bin/env python3
"""
YDLiDAR T-mini Pro デモ可視化サンプル

センサーなしでもデモデータで動作確認できます。

使用方法:
    # デモモード
    python demo_visualization.py --demo

    # 実際のセンサー使用
    python demo_visualization.py /dev/tty.usbserial-xxxx
"""

import sys
import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib
import time
import math

# 日本語フォント設定（Mac用）
matplotlib.rcParams['font.family'] = 'Hiragino Sans'

# ライブラリのパスを追加（開発時用）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ydlidar_tmini import TMiniDriver, LaserScan, LaserPoint


class DemoLidarGenerator:
    """デモLiDARデータ生成器"""

    def __init__(self):
        self.frame = 0
        self.scan_frequency = 6.0

    def generate_scan(self) -> LaserScan:
        """デモスキャンデータを生成"""
        points = []

        # 360度をカバーする測定点を生成
        num_points = 400
        for i in range(num_points):
            angle = (i * 360.0 / num_points) % 360.0

            # 複数の物体をシミュレート
            distance = self._simulate_environment(angle, self.frame)

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

        self.frame += 1

        return LaserScan(
            points=points,
            scan_frequency=self.scan_frequency,
            timestamp=time.time()
        )

    def _simulate_environment(self, angle: float, frame: int) -> float:
        """環境をシミュレート（複数の物体）"""

        # アニメーション用の時間変数
        t = frame * 0.05

        # 物体1: 静止した壁（半円）
        if 30 <= angle <= 150:
            wall_distance = 3.0 + 0.5 * math.sin(math.radians(angle * 3))
            return wall_distance

        # 物体2: 回転する障害物
        obstacle_angle = (90 + t * 20) % 360
        angle_diff = abs(angle - obstacle_angle)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff

        if angle_diff < 20:
            # 角度差に応じて距離を変化
            obstacle_distance = 2.0 + 1.5 * (angle_diff / 20.0)
            return obstacle_distance

        # 物体3: 移動する物体
        moving_angle = (180 + math.sin(t) * 60) % 360
        angle_diff = abs(angle - moving_angle)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff

        if angle_diff < 15:
            moving_distance = 4.0 + 1.0 * math.cos(t * 2)
            return moving_distance

        # 物体4: 床（下方向）
        if 200 <= angle <= 340:
            floor_distance = 1.5 + 0.3 * math.sin(math.radians(angle * 2))
            return floor_distance

        # その他: 検出なし
        return 0.0


class LidarVisualizer:
    """LiDARデータのリアルタイム可視化クラス"""

    def __init__(self, demo_mode=False, driver=None, max_range=16.0):
        """
        Args:
            demo_mode: デモモードを使用するか
            driver: TMiniDriverインスタンス（実センサー使用時）
            max_range: 表示する最大距離 (m)
        """
        self.demo_mode = demo_mode
        self.driver = driver
        self.max_range = max_range
        self.initial_max_range = max_range  # 初期値を保存
        self.latest_scan = None

        if demo_mode:
            self.demo_generator = DemoLidarGenerator()
            self.scan_count = 0

        # グラフ設定
        self.fig, self.ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        self.scatter = None
        self.stats_text = None
        self.help_text = None

        # マウス操作用の状態
        self.pan_start = None
        self.r_min = 0
        self.r_max = max_range

        self._setup_plot()

    def _setup_plot(self):
        """グラフの初期設定"""
        self.ax.set_ylim(0, self.max_range)
        self.ax.set_theta_zero_location('N')  # 0度を上に
        self.ax.set_theta_direction(-1)  # 時計回り

        title = 'YDLiDAR T-mini Pro - デモモード' if self.demo_mode else 'YDLiDAR T-mini Pro - リアルタイムスキャン'
        self.ax.set_title(title, pad=20, fontsize=14, fontweight='bold')
        self.ax.grid(True, alpha=0.3)

        # 初期プロット（空）
        self.scatter = self.ax.scatter([], [], c=[], s=10, cmap='jet', alpha=0.8)

        # 統計情報テキスト
        self.stats_text = self.fig.text(0.02, 0.98, '', transform=self.fig.transFigure,
                                        verticalalignment='top', fontsize=10,
                                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        # ヘルプテキスト
        help_str = "マウス操作:\n"
        help_str += "  スクロール: ズーム\n"
        help_str += "  中クリック: リセット"
        self.help_text = self.fig.text(0.98, 0.02, help_str, transform=self.fig.transFigure,
                                       horizontalalignment='right', verticalalignment='bottom',
                                       fontsize=9,
                                       bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

        # カラーバー
        cbar = plt.colorbar(self.scatter, ax=self.ax, pad=0.1)
        cbar.set_label('距離 (m)', rotation=270, labelpad=20)

        # マウスイベント接続
        self.fig.canvas.mpl_connect('scroll_event', self._on_scroll)
        self.fig.canvas.mpl_connect('button_press_event', self._on_button_press)
        self.fig.canvas.mpl_connect('button_release_event', self._on_button_release)
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)

    def update_scan(self, scan: LaserScan):
        """スキャンデータを更新"""
        self.latest_scan = scan

    def _update_plot(self, frame):
        """プロット更新（アニメーション用）"""

        # デモモードの場合、データを生成
        if self.demo_mode:
            self.latest_scan = self.demo_generator.generate_scan()
            self.scan_count += 1

        if self.latest_scan is None:
            return self.scatter,

        # 有効なポイントのみ抽出
        points = self.latest_scan.get_valid_points()

        if len(points) == 0:
            return self.scatter,

        # データ抽出
        angles = np.array([np.radians(p.angle) for p in points])
        distances = np.array([p.distance for p in points])

        # 距離範囲でフィルタ（現在の表示範囲を使用）
        valid_mask = (distances >= self.r_min) & (distances <= self.r_max)
        angles = angles[valid_mask]
        distances = distances[valid_mask]

        # プロット更新
        self.scatter.set_offsets(np.c_[angles, distances])
        self.scatter.set_array(distances)
        self.scatter.set_clim(0, self.r_max)

        # 統計情報更新
        stats = self._calculate_stats(points)
        self.stats_text.set_text(stats)

        return self.scatter,

    def _calculate_stats(self, points):
        """統計情報を計算"""
        valid_points = [p for p in points if p.is_valid()]

        if len(valid_points) == 0:
            return "データなし"

        distances = [p.distance for p in valid_points]
        intensities = [p.intensity for p in valid_points]

        scan_count = self.scan_count if self.demo_mode else self.driver.get_scan_count()

        stats = f"{'[デモモード]' if self.demo_mode else '[実データ]'}\n"
        stats += f"スキャン数: {scan_count}\n"
        stats += f"測定点数: {len(valid_points)}\n"
        stats += f"周波数: {self.latest_scan.scan_frequency:.1f} Hz\n"
        stats += f"距離: {min(distances):.2f} - {max(distances):.2f} m\n"
        stats += f"平均距離: {np.mean(distances):.2f} m\n"
        if intensities and max(intensities) > 0:
            stats += f"強度: {min(intensities)} - {max(intensities)}"

        return stats

    def _on_scroll(self, event):
        """マウスホイール/トラックパッドでズーム"""
        if event.inaxes != self.ax:
            return

        # ズーム係数
        # Macトラックパッド: 2本指スクロールでズーム
        # event.step > 0: 上方向スクロール → 拡大
        # event.step < 0: 下方向スクロール → 縮小
        if event.step > 0:
            zoom_factor = 0.8  # 範囲を狭くする = 拡大
        else:
            zoom_factor = 1.2  # 範囲を広げる = 縮小

        # 現在の範囲を取得
        r_min, r_max = self.ax.get_ylim()

        # 新しい範囲を計算
        # 極座標プロットでは常に中心（0）から表示するため、r_maxのみを変更
        new_r_max = r_max * zoom_factor

        # 最小・最大制限
        new_r_max = max(0.5, min(new_r_max, self.initial_max_range))

        # 極座標プロットは常に0から開始
        new_r_min = 0

        self.ax.set_ylim(new_r_min, new_r_max)
        self.r_min = new_r_min
        self.r_max = new_r_max
        self.fig.canvas.draw_idle()

    def _on_button_press(self, event):
        """マウスボタン押下"""
        if event.inaxes != self.ax:
            return

        # 中クリック: リセット
        if event.button == 2:
            self.ax.set_ylim(0, self.initial_max_range)
            self.r_min = 0
            self.r_max = self.initial_max_range
            self.fig.canvas.draw_idle()

        # 右クリック: パン開始
        elif event.button == 3:
            self.pan_start = (event.xdata, event.ydata)

    def _on_button_release(self, event):
        """マウスボタン解放"""
        if event.button == 3:
            self.pan_start = None

    def _on_mouse_move(self, event):
        """マウス移動（パン処理）"""
        if self.pan_start is None or event.inaxes != self.ax:
            return

        if event.xdata is None or event.ydata is None:
            return

        # パン量を計算
        dx = event.xdata - self.pan_start[0]
        dy = event.ydata - self.pan_start[1]

        # 距離方向のみパン（極座標なので）
        r_min, r_max = self.ax.get_ylim()
        r_range = r_max - r_min

        # dyを距離の変化に変換
        new_r_min = r_min - dy
        new_r_max = r_max - dy

        # 範囲チェック
        if new_r_min < 0:
            new_r_max -= new_r_min
            new_r_min = 0

        if new_r_max > self.initial_max_range:
            new_r_min -= (new_r_max - self.initial_max_range)
            new_r_max = self.initial_max_range

        self.ax.set_ylim(new_r_min, new_r_max)
        self.r_min = new_r_min
        self.r_max = new_r_max

        # パン開始位置を更新
        self.pan_start = (event.xdata, event.ydata)
        self.fig.canvas.draw_idle()

    def start(self, interval=50):
        """
        可視化開始

        Args:
            interval: アニメーション更新間隔 (ms)
        """
        # 実センサーの場合、スキャン開始
        if not self.demo_mode and self.driver:
            self.driver.start_scanning(callback=self.update_scan)

        # アニメーション開始（blit=Falseでマウス操作時の再描画を有効化）
        ani = FuncAnimation(self.fig, self._update_plot, interval=interval, blit=False)

        mode_str = "デモモード" if self.demo_mode else "実センサーモード"
        print(f"{mode_str}で可視化開始。ウィンドウを閉じると終了します。")
        plt.show()


def main():
    parser = argparse.ArgumentParser(
        description='YDLiDAR T-mini Pro デモ可視化',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # デモモード（センサーなし）
  %(prog)s --demo

  # 実センサー使用
  %(prog)s /dev/tty.usbserial-0001

  # デモモードで距離範囲指定
  %(prog)s --demo --max-range 10
        """
    )

    parser.add_argument('port', nargs='?', help='シリアルポート (例: /dev/tty.usbserial-xxxx)')
    parser.add_argument('--demo', action='store_true', help='デモモードで動作（センサー不要）')
    parser.add_argument('--baudrate', type=int, default=230400, help='ボーレート (デフォルト: 230400)')
    parser.add_argument('--max-range', type=float, default=16.0, help='表示最大距離 [m] (デフォルト: 16.0)')
    parser.add_argument('--no-intensity', action='store_true', help='強度データを使用しない')
    parser.add_argument('--intensity-bit', type=int, default=8, choices=[8, 10], help='強度ビット数 (デフォルト: 8)')

    args = parser.parse_args()

    # デモモード
    if args.demo:
        print("デモモードで起動します（センサー不要）")
        visualizer = LidarVisualizer(demo_mode=True, max_range=args.max_range)
        visualizer.start()
        return

    # 実センサーモード
    if not args.port:
        print("エラー: シリアルポートを指定するか、--demo オプションを使用してください")
        parser.print_help()
        sys.exit(1)

    print(f"実センサーモードで起動します")
    print(f"  ポート: {args.port}")
    print(f"  ボーレート: {args.baudrate}")

    try:
        with TMiniDriver(
            port=args.port,
            baudrate=args.baudrate,
            has_intensity=not args.no_intensity,
            intensity_bit=args.intensity_bit
        ) as driver:

            visualizer = LidarVisualizer(demo_mode=False, driver=driver, max_range=args.max_range)
            visualizer.start()

    except KeyboardInterrupt:
        print("\n中断されました")
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
