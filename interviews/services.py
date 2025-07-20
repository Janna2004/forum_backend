import base64
import hashlib
import hmac
import json
import threading
import time
from datetime import datetime
from urllib.parse import urlencode, quote
import websocket
from websocket import create_connection, WebSocketConnectionClosedException
from django.conf import settings

class XunfeiRealtimeTranscribeClient:
    """
    讯飞实时语音转写WebSocket客户端（rtasr.xfyun.cn/v1/ws）
    用法：
        client = XunfeiRealtimeTranscribeClient(on_result=回调函数)
        client.connect()
        client.send_audio(audio_bytes)
        ...
        client.close()
    """
    def __init__(self, on_result=None):
        import hashlib, base64, time
        from django.conf import settings
        self.appid = getattr(settings, 'XUNFEI_APP_ID', '')
        self.api_key = getattr(settings, 'XUNFEI_ASR_API_KEY', '')
        self.on_result = on_result
        self.ws = None
        self.thread = None
        self.connected = False
        self.closed = False
        self.url = self._create_url()

    def _create_url(self):
        import hashlib, base64, time
        appid = self.appid
        api_key = self.api_key
        ts = str(int(time.time()))
        md5 = hashlib.md5((appid + ts).encode('utf-8')).hexdigest()
        signa = base64.b64encode(hashlib.sha1((md5 + api_key).encode('utf-8')).digest()).decode('utf-8')
        print(f"调试: appid={appid}, api_key={api_key}, ts={ts}, signa={signa}")
        url = f"wss://rtasr.xfyun.cn/v1/ws?appid={appid}&ts={ts}&signa={signa}"
        return url

    def connect(self):
        import websocket
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        import threading
        self.thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self.thread.start()
        # 等待连接建立
        for _ in range(30):
            if self.connected:
                break
            import time
            time.sleep(0.1)

    def _on_open(self, ws):
        self.connected = True
        # 实时转写无需发送握手参数，直接发送音频帧

    def send_audio(self, audio_bytes, is_last=False):
        if not self.connected or self.closed:
            return
        try:
            self.ws.send(audio_bytes, opcode=websocket.ABNF.OPCODE_BINARY)
            if is_last:
                self.ws.send("{" + '"end": true' + "}")
        except Exception:
            pass

    def _on_message(self, ws, message):
        try:
            print("ASR原始返回：", message)  # 新增调试
            import json
            data = json.loads(message)
            if data.get('code') == 0:
                if 'data' in data and self.on_result:
                    self.on_result(data['data'])
            else:
                if self.on_result:
                    # 返回原始错误内容，便于排查
                    self.on_result(f"[ASR错误] {data.get('message') or message}")
        except Exception as e:
            if self.on_result:
                self.on_result(f"[ASR解析异常] {str(e)}")

    def _on_error(self, ws, error):
        self.closed = True
        if self.on_result:
            self.on_result(f"[ASR连接错误] {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        self.closed = True
        self.connected = False
        if self.on_result:
            self.on_result(f"[ASR连接关闭] {close_status_code} {close_msg}")

    def close(self):
        self.closed = True
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass

class XunfeiRTASRClient:
    def __init__(self, app_id, api_key, on_result=None):
        self.app_id = app_id
        self.api_key = api_key
        self.on_result = on_result
        self.ws = None
        self.trecv = None
        self.connected = False
        self.closed = False

    def connect(self):
        base_url = "ws://rtasr.xfyun.cn/v1/ws"
        ts = str(int(time.time()))
        tt = (self.app_id + ts).encode('utf-8')
        md5 = hashlib.md5()
        md5.update(tt)
        baseString = md5.hexdigest()
        baseString = bytes(baseString, encoding='utf-8')
        apiKey = self.api_key.encode('utf-8')
        signa = hmac.new(apiKey, baseString, hashlib.sha1).digest()
        signa = base64.b64encode(signa)
        signa = str(signa, 'utf-8')
        url = base_url + "?appid=" + self.app_id + "&ts=" + ts + "&signa=" + quote(signa)
        self.ws = create_connection(url)
        self.connected = True
        self.trecv = threading.Thread(target=self.recv)
        self.trecv.start()

    def send_audio(self, audio_bytes, is_last=False):
        if self.connected and not self.closed:
            self.ws.send(audio_bytes, opcode=2)  # opcode=2 for binary
            if is_last:
                self.ws.send(b'{"end": true}')

    def recv(self):
        try:
            while self.ws.connected:
                result = str(self.ws.recv())
                if len(result) == 0:
                    break
                result_dict = json.loads(result)
                if result_dict["action"] == "result":
                    if self.on_result:
                        self.on_result(result_dict["data"])
                if result_dict["action"] == "error":
                    if self.on_result:
                        self.on_result("[RTASR错误] " + result)
                    self.ws.close()
                    self.closed = True
                    return
        except WebSocketConnectionClosedException:
            self.closed = True
        except Exception as e:
            self.closed = True
            if self.on_result:
                self.on_result(f"[RTASR异常] {str(e)}")

    def close(self):
        if self.ws:
            self.ws.close()
        self.connected = False
        self.closed = True 