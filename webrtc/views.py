from django.shortcuts import render

def test_websocket(request):
    """WebSocket测试页面"""
    return render(request, 'webrtc/test_websocket.html')

def audio_ws_test(request):
    """音频WebSocket测试页面（无需认证）"""
    return render(request, 'webrtc/audio_ws_test.html') 