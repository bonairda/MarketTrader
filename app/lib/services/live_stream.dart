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

  String? _token;

  Stream<LivePrice> get stream => _controller.stream;

  void connect(String? token) {
    _token = token;
    _closed = false;
    _open();
  }

  /// Reconecta para que el servidor recargue la watchlist tras altas/bajas.
  void reconnect(String? token) {
    _token = token;
    _reconnectTimer?.cancel();
    _sub?.cancel();
    _channel?.sink.close();
    _channel = null;
    _closed = false;
    _open();
  }

  void _open() {
    if (_closed || _token == null || _token!.isEmpty) return;
    try {
      final uri = Uri.parse(AppConfig.liveWsUrl).replace(
        queryParameters: {'token': _token!},
      );
      _channel = WebSocketChannel.connect(uri);
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
