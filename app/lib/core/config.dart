import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

/// Configuración pública de la app.
///
/// En web, Nginx genera `/config.json` al arrancar a partir de
/// `PUBLIC_API_BASE_URL`. En móvil/escritorio se mantiene `--dart-define`.
class AppConfig {
  static const String _compiledApiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  static const bool _requireRuntimeConfig = bool.fromEnvironment(
    'REQUIRE_RUNTIME_CONFIG',
    defaultValue: false,
  );

  static String _apiBaseUrl = _compiledApiBaseUrl;

  /// Debe ejecutarse antes de runApp. En builds de producción
  /// REQUIRE_RUNTIME_CONFIG obliga a fallar en vez de apuntar a localhost.
  static Future<void> initialize() async {
    if (!kIsWeb) return;
    try {
      final uri = Uri.base.resolve(
        'config.json?v=${DateTime.now().millisecondsSinceEpoch}',
      );
      final response = await http.get(uri, headers: {'Cache-Control': 'no-cache'});
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw StateError('No se pudo cargar config.json (${response.statusCode})');
      }
      final payload = jsonDecode(response.body) as Map<String, dynamic>;
      final candidate = (payload['apiBaseUrl'] as String?)?.trim() ?? '';
      final parsed = Uri.tryParse(candidate);
      if (parsed == null || !parsed.hasAuthority) {
        throw const FormatException('apiBaseUrl no es una URL absoluta');
      }
      if (parsed.scheme != 'http' && parsed.scheme != 'https') {
        throw const FormatException('apiBaseUrl debe usar HTTP o HTTPS');
      }
      _apiBaseUrl = candidate.replaceFirst(RegExp(r'/+$'), '');
    } catch (_) {
      if (_requireRuntimeConfig) rethrow;
      // En desarrollo se conserva el fallback compilado.
    }
  }

  static String get apiBaseUrl => _apiBaseUrl;

  /// Intervalo de refresco de respaldo si el WebSocket no está disponible.
  static const Duration livePollInterval = Duration(seconds: 5);

  static String get liveWsUrl {
    final api = Uri.parse(apiBaseUrl);
    final basePath = api.path.replaceFirst(RegExp(r'/+$'), '');
    return api
        .replace(
          scheme: api.scheme == 'https' ? 'wss' : 'ws',
          path: '$basePath/market/ws',
          query: null,
          fragment: null,
        )
        .toString();
  }
}
