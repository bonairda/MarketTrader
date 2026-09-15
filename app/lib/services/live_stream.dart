import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

import '../core/config.dart';
import '../models/live_price.dart';

/// Cliente del stream de precios en vivo (WebSocket /market/ws).
///
/// Expone un Stream de LivePrice y reconecta automáticamente si la conexión
/// se cae. Si el WebSocket no está disponible, el consumidor puede seguir
/// usando el polling REST como respaldo.
class LiveStream {
  final _controller = StreamController<LivePrice>.broadcast();
  WebSocketChannel? _channel;
  StreamSubscription? _sub;
  Timer? _reconnectTimer;
  bool _closed = false;

  Stream<LivePrice> get stream => _controller.stream;

  void connect() {
    _closed = false;
    _open();
  }

  void _open() {
    if (_closed) return;
    try {
      _channel = WebSocketChannel.connect(Uri.parse(AppConfig.liveWsUrl));
      _sub = _channel!.stream.listen(
        _onMessage,
        onError: (_) => _scheduleReconnect(),
        onDone: _scheduleReconnect,
      );
    } catch (_) {
      _scheduleReconnect();
    }
  }

  void _onMessage(dynamic raw) {
    try {
      final json = jsonDecode(raw as String) as Map<String, dynamic>;
      _controller.add(LivePrice.fromJson(json));
    } catch (_) {
      // Mensaje no válido: se ignora sin romper el stream.
    }
  }

  void _scheduleReconnect() {
    if (_closed) return;
    _sub?.cancel();
    _channel = null;
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 3), _open);
  }

  void dispose() {
    _closed = true;
    _reconnectTimer?.cancel();
    _sub?.cancel();
    _channel?.sink.close();
    _controller.close();
  }
}
