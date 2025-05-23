import json
import logging
import threading
import time
from collections import defaultdict
import websocket
from hyperliquid.utils.types import Any, Callable, Dict, List, NamedTuple, Optional, Subscription, Tuple, WsMsg

ActiveSubscription = NamedTuple("ActiveSubscription", [("callback", Callable[[Any], None]), ("subscription_id", int)])

def subscription_to_identifier(subscription: Subscription) -> str:
    if subscription["type"] == "allMids":
        return "allMids"
    elif subscription["type"] == "l2Book":
        return f'l2Book:{subscription["coin"].lower()}'
    elif subscription["type"] == "trades":
        return f'trades:{subscription["coin"].lower()}'
    elif subscription["type"] == "userEvents":
        return "userEvents"

def ws_msg_to_identifier(ws_msg: WsMsg) -> Optional[str]:
    if ws_msg["channel"] == "pong":
        return "pong"
    elif ws_msg["channel"] == "allMids":
        return "allMids"
    elif ws_msg["channel"] == "l2Book":
        return f'l2Book:{ws_msg["data"]["coin"].lower()}'
    elif ws_msg["channel"] == "trades":
        trades = ws_msg["data"]
        if len(trades) == 0:
            return None
        else:
            return f'trades:{trades[0]["coin"].lower()}'
    elif ws_msg["channel"] == "user":
        return "userEvents"

class WebsocketManager(threading.Thread):
    def __init__(self, base_url: str, on_allmids: Callable[[Any], None]):
        super().__init__(daemon=True)
        self.subscription_id_counter = 0
        self.ws_ready = False
        self.queued_subscriptions: List[Tuple[Subscription, ActiveSubscription]] = []
        self.active_subscriptions: Dict[str, List[ActiveSubscription]] = defaultdict(list)
        self.base_url = base_url
        self.on_allmids = on_allmids
        self.ws = None
        self.ping_sender = threading.Thread(target=self.send_ping, daemon=True)

    def run(self):
        self.ping_sender.start()
        while True:
            try:
                self.ws = websocket.WebSocketApp(
                    self.base_url,
                    on_message=self.on_message,
                    on_open=self.on_open,
                    on_close=self.on_close,
                    on_error=self.on_error
                )
                self.ws.run_forever()
            except Exception as e:
                logging.error(f"run_forever exception: {e}")
            logging.warning("WebSocket disconnected. Reconnecting in 5 seconds...")
            time.sleep(5)

    def send_ping(self):
        while True:
            time.sleep(50)
            try:
                if self.ws and self.ws.sock and self.ws.sock.connected:
                    self.ws.send(json.dumps({"method": "ping"}))
                    logging.debug("Ping sent.")
            except Exception as e:
                logging.error(f"Ping error: {e}")

    def on_message(self, _ws, message):
        if message == "Websocket connection established.":
            return
        try:
            ws_msg: WsMsg = json.loads(message)
            identifier = ws_msg_to_identifier(ws_msg)
            if identifier is None:
                return
            subscribers = self.active_subscriptions.get(identifier, [])
            for s in subscribers:
                s.callback(ws_msg)
        except Exception as e:
            logging.error(f"WebSocket message error: {e} - {message}")

    def on_open(self, _ws):
        logging.info("✅ WebSocket connection opened.")
        self.ws_ready = True
        for (subscription, active_subscription) in self.queued_subscriptions:
            self.subscribe(subscription, active_subscription.callback, active_subscription.subscription_id)
        self.queued_subscriptions.clear()

    def on_close(self, _ws, close_status_code, close_msg):
        logging.warning(f"⚠️ WebSocket closed: {close_status_code}, {close_msg}")
        self.ws_ready = False

    def on_error(self, _ws, error):
        logging.error(f"❌ WebSocket error: {error}")

    def subscribe(
        self, subscription: Subscription, callback: Callable[[Any], None], subscription_id: Optional[int] = None
    ) -> int:
        if subscription_id is None:
            self.subscription_id_counter += 1
            subscription_id = self.subscription_id_counter

        identifier = subscription_to_identifier(subscription)

        if not self.ws_ready:
            self.queued_subscriptions.append((subscription, ActiveSubscription(callback, subscription_id)))
        else:
            try:
                self.ws.send(json.dumps({
                    "method": "subscribe",
                    "subscription": subscription
                }))
                logging.info(f"📡 Subscription message sent: {subscription}")
            except Exception as e:
                logging.error(f"❌ Subscription failed: {e}")

        self.active_subscriptions[identifier].append(ActiveSubscription(callback, subscription_id))
        return subscription_id

