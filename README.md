# YDLiDAR T-mini Pro Mac用ドライバー

YDLiDAR T-mini Pro LiDARセンサー用のMac対応Pythonライブラリです。

公式SDKがMacに対応していないため、macOS向けに完全に新規実装されました。純粋なPythonで実装されており、シリアル通信（pyserial）のみに依存しています。

## 特徴

- macOS ネイティブサポート
- 純粋なPython実装（C++コンパイル不要）
- リアルタイムデータ取得
- 強度データ対応（8bit/10bit）
- マルチスレッド対応
- リアルタイム可視化サンプル付属

## 動作環境

- macOS (Darwin 25.0.0以降で動作確認)
- Python 3.7以降
- pipenv

## インストール

### 1. pipenvのインストール

```bash
# Homebrewでインストール
brew install pipenv

# またはpipでインストール
pip install --user pipenv
```

### 2. 依存パッケージのインストール

```bash
# プロジェクトディレクトリで実行
pipenv install

# 開発用パッケージも含める場合
pipenv install --dev
```

### 3. ライブラリのインストール（オプション）

開発モードでインストール:

```bash
pipenv install -e .
```

## 使用方法

### シリアルポートの確認

```bash
# macOSでUSBシリアルデバイスを確認
ls /dev/tty.usbserial-*
```

または、サンプルプログラムで確認:

```bash
pipenv run python examples/visualize_realtime.py --list-ports
```

### 基本的な使い方

```python
from ydlidar_tmini import TMiniDriver

# ドライバー初期化
with TMiniDriver('/dev/tty.usbserial-xxxx') as lidar:
    # スキャン開始
    lidar.start_scanning()

    # スキャンデータ取得
    scan = lidar.get_scan(timeout=2.0)

    if scan:
        print(f"測定点数: {len(scan.points)}")
        print(f"スキャン周波数: {scan.scan_frequency} Hz")

        # 有効なポイントのみ取得
        for point in scan.get_valid_points():
            print(f"角度: {point.angle:.2f}°, "
                  f"距離: {point.distance:.3f}m, "
                  f"強度: {point.intensity}")
```

### コールバック関数を使用

```python
def on_scan(scan):
    valid_points = scan.get_valid_points()
    print(f"スキャン受信: {len(valid_points)} 点")

with TMiniDriver('/dev/tty.usbserial-xxxx') as lidar:
    lidar.start_scanning(callback=on_scan)

    # スキャン継続
    import time
    time.sleep(10)
```

## サンプルプログラム

### 1. シンプルなスキャン

データを取得して表示するシンプルなサンプル:

```bash
pipenv run python examples/simple_scan.py /dev/tty.usbserial-xxxx
```

オプション:
```bash
# 100スキャン取得
pipenv run python examples/simple_scan.py /dev/tty.usbserial-xxxx --scans 100

# データをCSVに保存
pipenv run python examples/simple_scan.py /dev/tty.usbserial-xxxx --save output.csv
```

### 2. リアルタイム可視化

matplotlibを使ったリアルタイム可視化（マウス操作対応）:

```bash
pipenv run python examples/visualize_realtime.py /dev/tty.usbserial-xxxx
```

**マウス操作:**
- **スクロール**: ズームイン/ズームアウト
- **中クリック**: ビューのリセット

オプション:
```bash
# 最大表示距離を10mに設定
pipenv run python examples/visualize_realtime.py /dev/tty.usbserial-xxxx --max-range 10

# 強度データを使用しない
pipenv run python examples/visualize_realtime.py /dev/tty.usbserial-xxxx --no-intensity

# 10bit強度モード
pipenv run python examples/visualize_realtime.py /dev/tty.usbserial-xxxx --intensity-bit 10
```

### 3. デモモード（センサー不要）

センサーなしでデモデータを表示:

```bash
# リアルタイム可視化（デモモード）
pipenv run python examples/demo_visualization.py --demo

# 静止画生成（デモモード）
pipenv run python examples/demo_snapshot.py output.png
```

## API リファレンス

### TMiniDriver

メインドライバークラス。

#### コンストラクタ

```python
TMiniDriver(port, baudrate=230400, has_intensity=True, intensity_bit=8)
```

パラメータ:
- `port` (str): シリアルポート (例: '/dev/tty.usbserial-0001')
- `baudrate` (int): ボーレート（デフォルト: 230400）
- `has_intensity` (bool): 強度データを使用するか（デフォルト: True）
- `intensity_bit` (int): 強度ビット数 8 or 10（デフォルト: 8）

#### メソッド

- `connect()`: シリアルポートに接続
- `disconnect()`: シリアルポートから切断
- `start_scanning(callback=None)`: スキャン開始
- `stop_scanning()`: スキャン停止
- `get_scan(timeout=1.0)`: スキャンデータを取得
- `get_scan_count()`: 完了したスキャン数を取得
- `is_scanning()`: スキャン中かどうか

### LaserScan

スキャンデータクラス。

#### 属性

- `points` (List[LaserPoint]): 測定点のリスト
- `scan_frequency` (float): スキャン周波数 (Hz)
- `timestamp` (float): タイムスタンプ (秒)

#### メソッド

- `get_valid_points()`: 有効なポイント（距離 > 0）のみを返す

### LaserPoint

測定点データクラス。

#### 属性

- `angle` (float): 角度（度、0-360）
- `distance` (float): 距離（メートル）
- `intensity` (int): 信号強度（0-255 or 0-1023）

#### メソッド

- `to_cartesian()`: 極座標を直交座標(x, y)に変換
- `is_valid()`: 有効なデータか判定（距離 > 0）

## プロトコル仕様

このライブラリは公式SDKのプロトコルを参考に実装されています。

### パケット構造

**ヘッダー部（10バイト）:**
- `[0-1]` PH: パケットヘッダー (0xAA55)
- `[2]` CT: パケットタイプ（bit0=1で零位包、bit1-7はスキャン周波数×10）
- `[3]` LSN: サンプル点数（1-80）
- `[4-5]` FSA: 開始角度（64倍、リトルエンディアン）
- `[6-7]` LSA: 終了角度（64倍、リトルエンディアン）
- `[8-9]` CS: チェックサム（XOR）

**データ部:**
- 強度あり: 各点3バイト `[強度1B][距離下位1B][距離上位1B]`
- 強度なし: 各点2バイト `[距離下位1B][距離上位1B]`

### 通信設定

- ボーレート: 230400
- データビット: 8
- パリティ: なし
- ストップビット: 1
- フロー制御: なし

## トラブルシューティング

### シリアルポートが見つからない

```bash
# USB-Serialドライバーが正しくインストールされているか確認
ls /dev/tty.*

# 権限エラーの場合、ポートへのアクセス権限を付与
sudo chmod 666 /dev/tty.usbserial-xxxx
```

### データが取得できない

1. ボーレートが正しいか確認（T-mini Proは230400）
2. センサーの電源が入っているか確認
3. USBケーブルが正しく接続されているか確認
4. 他のプログラムがポートを使用していないか確認

### macOS Sonomaでのパーミッション問題

macOS Sonoma以降では、USBデバイスへのアクセスに追加の権限が必要な場合があります。システム設定の「プライバシーとセキュリティ」を確認してください。

## 開発

### pipenvシェルに入る

```bash
pipenv shell
```

### テストの実行

```bash
pipenv run pytest
```

### コードフォーマット

```bash
pipenv run black ydlidar_tmini/
```

### 依存関係の更新

```bash
# Pipfile.lockの更新
pipenv update

# 特定のパッケージの更新
pipenv update numpy
```

## ライセンス

MIT License

## 参考

- [YDLiDAR公式SDK](https://github.com/YDLIDAR/YDLidar-SDK)
- [T-mini Pro製品ページ](https://www.ydlidar.com/products/view/6.html)

## 貢献

バグ報告や機能要望は Issue でお願いします。
プルリクエストも歓迎します。

## 作者

開発: 2025
