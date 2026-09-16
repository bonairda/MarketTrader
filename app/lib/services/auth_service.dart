import 'package:shared_preferences/shared_preferences.dart';

import 'market_api.dart';

/// Gestiona la sesión del usuario: login/registro, persistencia del token y
/// su inyección en [MarketApi]. El token se guarda en SharedPreferences para
/// que la sesión sobreviva a reinicios de la app.
class AuthService {
  AuthService({required MarketApi api}) : _api = api;

  final MarketApi _api;

  static const _tokenKey = 'auth_token';
  static const _emailKey = 'auth_email';

  String? _email;
  String? get email => _email;

  /// Carga el token guardado (si lo hay) y lo aplica a la API.
  /// Devuelve true si había una sesión almacenada.
  Future<bool> loadSession() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_tokenKey);
    _email = prefs.getString(_emailKey);
    if (token == null || token.isEmpty) return false;
    _api.authToken = token;
    return true;
  }

  /// Valida contra el backend que el token cargado sigue siendo válido.
  /// Si no lo es, limpia la sesión. Útil al arrancar la app.
  Future<bool> validateSession() async {
    if (_api.authToken == null) return false;
    try {
      final user = await _api.me();
      _email = user['email'] as String?;
      return true;
    } on UnauthorizedException {
      await logout();
      return false;
    }
  }

  Future<void> login(String email, String password) async {
    final result = await _api.login(email, password);
    await _persist(result);
  }

  Future<void> register(String email, String password) async {
    final result = await _api.register(email, password);
    await _persist(result);
  }

  Future<void> logout() async {
    _api.authToken = null;
    _email = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_emailKey);
  }

  Future<void> _persist(Map<String, dynamic> authResult) async {
    final token = authResult['token'] as String;
    final user = authResult['user'] as Map<String, dynamic>?;
    _email = user?['email'] as String?;
    _api.authToken = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
    if (_email != null) await prefs.setString(_emailKey, _email!);
  }
}
