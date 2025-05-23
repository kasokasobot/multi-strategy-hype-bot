# Multi-Strategy HYPE Bot

## 📌 Overview
This is a trading bot designed for the Hyperliquid exchange. It utilizes multiple strategies including Bollinger Band reversal, spike rebound detection, and trend breakout logic to automatically trade the HYPE token.

## ⚙️ How to Run

```bash
pip install -r requirements.txt
python main.py --sz 0.01
```

## 📐 Strategy Parameters
- Z-score window: 30
- Entry threshold: ±0.5
- Exit threshold (Z-score): ±0.3
- Take Profit / Stop Loss: ±0.5%

## 🔐 Security Notice
The `config.json` file contains your private key. Be sure to keep it secure and **never share it in public repositories**. Use a placeholder like `"YOUR_PRIVATE_KEY_HERE"` for safety in public uploads.

## ⚠️ Disclaimer

This project is provided for educational and research purposes only.  
Use it at your own risk. The authors and contributors are not responsible for any financial losses, legal issues, or damages caused by the use of this bot.
