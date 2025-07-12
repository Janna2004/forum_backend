from django.shortcuts import render

def test_websocket(request):
    """WebSocket测试页面"""
    return render(request, 'webrtc/test_websocket.html') 