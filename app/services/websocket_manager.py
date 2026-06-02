import json
from typing import Set, Dict
from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self._rider_connections: Dict[str, Set[WebSocket]] = {}
        self._seller_connections: Dict[str, Set[WebSocket]] = {}
        self._user_connections: Dict[str, Set[WebSocket]] = {}

    async def connect_rider(self, rider_id: str, ws: WebSocket):
        await ws.accept()
        if rider_id not in self._rider_connections:
            self._rider_connections[rider_id] = set()
        self._rider_connections[rider_id].add(ws)

    async def connect_seller(self, seller_id: str, ws: WebSocket):
        await ws.accept()
        if seller_id not in self._seller_connections:
            self._seller_connections[seller_id] = set()
        self._seller_connections[seller_id].add(ws)

    async def connect_user(self, email: str, ws: WebSocket):
        await ws.accept()
        if email not in self._user_connections:
            self._user_connections[email] = set()
        self._user_connections[email].add(ws)

    def disconnect_rider(self, rider_id: str, ws: WebSocket):
        if rider_id in self._rider_connections:
            self._rider_connections[rider_id].discard(ws)
            if not self._rider_connections[rider_id]:
                del self._rider_connections[rider_id]

    def disconnect_seller(self, seller_id: str, ws: WebSocket):
        if seller_id in self._seller_connections:
            self._seller_connections[seller_id].discard(ws)
            if not self._seller_connections[seller_id]:
                del self._seller_connections[seller_id]

    def disconnect_user(self, email: str, ws: WebSocket):
        if email in self._user_connections:
            self._user_connections[email].discard(ws)
            if not self._user_connections[email]:
                del self._user_connections[email]

    async def _send_to_set(self, ws_set: Set[WebSocket], payload: str):
        dead = set()
        for ws in ws_set:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            ws_set.discard(ws)

    async def notify_rider(self, rider_id: str, event: dict):
        if rider_id not in self._rider_connections:
            return
        payload = json.dumps(event, default=str)
        await self._send_to_set(self._rider_connections[rider_id], payload)
        if not self._rider_connections[rider_id]:
            del self._rider_connections[rider_id]

    async def notify_seller(self, seller_id: str, event: dict):
        if seller_id not in self._seller_connections:
            return
        payload = json.dumps(event, default=str)
        await self._send_to_set(self._seller_connections[seller_id], payload)
        if not self._seller_connections[seller_id]:
            del self._seller_connections[seller_id]

    async def notify_user(self, email: str, event: dict):
        if email not in self._user_connections:
            return
        payload = json.dumps(event, default=str)
        await self._send_to_set(self._user_connections[email], payload)
        if not self._user_connections[email]:
            del self._user_connections[email]

    async def broadcast_rider_status_change(self, rider_id: str, status: str, name: str):
        event = {
            "type": "rider_status_changed",
            "rider_id": rider_id,
            "status": status,
            "name": name,
        }
        for sid in list(self._seller_connections.keys()):
            await self.notify_seller(sid, event)

    async def broadcast_new_delivery(self, order_id: str, rider_id: str, delivery_data: dict):
        event = {
            "type": "new_delivery_assigned",
            "order_id": order_id,
            "delivery": delivery_data,
        }
        await self.notify_rider(rider_id, event)

    async def broadcast_delivery_status_change(self, order_id: str, status: str, rider_id: str):
        event = {
            "type": "delivery_status_changed",
            "order_id": order_id,
            "status": status,
        }
        await self.notify_rider(rider_id, event)


ws_manager = WebSocketManager()
