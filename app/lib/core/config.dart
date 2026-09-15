/// Configuración de la app.
///
/// La URL base de la API se puede sobrescribir en tiempo de compilación con:
///   flutter run --dart-define=API_BASE_URL=http://192.168.1.50:8000
class AppConfig {
  /// URL base del backend. Por defecto localhost para desarrollo web/escritorio.
  /// En un emulador Android usa http://10.0.2.2:8000
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  /// Intervalo de refresco de reserva por si el WebSocket no está disponible.
  static const Duration livePollInterval = Duration(seconds: 5);

  /// URL del WebSocket de precios en vivo, derivada de la URL base
  /// (http -> ws, https -> wss).
  static String get liveWsUrl {
    final base = apiBaseUrl.replaceFirst('http', 'ws');
    return '$base/market/ws';
  }
}
