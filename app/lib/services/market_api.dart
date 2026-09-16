import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config.dart';
import '../models/backtest.dart';
import '../models/dashboard.dart';
import '../models/indicators.dart';
import '../models/corporate_event.dart';
import '../models/derived_portfolio.dart';
import '../models/live_price.dart';
import '../models/operation.dart';
import '../models/paper_trading.dart';
import '../models/portfolio.dart';
import '../models/price_bar.dart';
import '../models/signal.dart';
import '../models/tax_report.dart';

/// Se lanza cuando la API responde 401 (token ausente, inválido o caducado).
/// La capa de UI la usa para volver a la pantalla de login.
class UnauthorizedException implements Exception {
  const UnauthorizedException([this.message = 'No autenticado']);
  final String message;
  @override
  String toString() => 'UnauthorizedException: $message';
}

/// Cliente HTTP de la API de MarketTracker.
///
/// Todas las peticiones (salvo login/registro) incluyen el token JWT en la
/// cabecera Authorization. Si falta o caduca, la API responde 401 y aquí se
/// traduce a [UnauthorizedException].
class MarketApi {
  MarketApi({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;
  String get _base => AppConfig.apiBaseUrl;

  /// Notifica al gate de sesión si cualquier llamada detecta un JWT caducado.
  void Function()? onUnauthorized;

  /// Token de acceso (JWT) usado en las cabeceras. Se establece tras el login y
  /// se limpia (null) al cerrar sesión.
  String? authToken;

  Map<String, String> _headers({bool json = false}) {
    final headers = <String, String>{};
    if (json) headers['Content-Type'] = 'application/json';
    final token = authToken;
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  // -------------------------- Autenticación --------------------------

  /// POST /auth/login -> devuelve el mapa { token, user }.
  Future<Map<String, dynamic>> login(String email, String password) async {
    final res = await _client.post(
      Uri.parse('$_base/auth/login'),
      headers: _headers(json: true),
      body: jsonEncode({'email': email, 'password': password}),
    );
    _ensureOk(res);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// POST /auth/register -> crea la cuenta y devuelve { token, user }.
  Future<Map<String, dynamic>> register(String email, String password) async {
    final res = await _client.post(
      Uri.parse('$_base/auth/register'),
      headers: _headers(json: true),
      body: jsonEncode({'email': email, 'password': password}),
    );
    _ensureOk(res);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// GET /auth/me -> valida el token actual y devuelve el usuario.
  Future<Map<String, dynamic>> me() async {
    final res = await _client.get(Uri.parse('$_base/auth/me'), headers: _headers());
    _ensureOk(res);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  // -------------------------- Datos de mercado --------------------------

  /// GET /market/prices -> precios en vivo de la watchlist del usuario.
  Future<List<LivePrice>> getLivePrices() async {
    final res = await _client.get(Uri.parse('$_base/market/prices'), headers: _headers());
    _ensureOk(res);
    final data = jsonDecode(res.body) as List<dynamic>;
    return data
        .map((e) => LivePrice.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// GET /market/bars/{symbol} -> velas históricas.
  Future<List<PriceBar>> getBars(
    String symbol, {
    String interval = '1m',
    int limit = 200,
  }) async {
    final uri = Uri.parse(
      '$_base/market/bars/$symbol?interval=$interval&limit=$limit',
    );
    final res = await _client.get(uri, headers: _headers());
    _ensureOk(res);
    final data = jsonDecode(res.body) as List<dynamic>;
    return data
        .map((e) => PriceBar.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// GET /market/indicators/{symbol} -> indicadores técnicos.
  Future<Indicators> getIndicators(
    String symbol, {
    String interval = '1m',
    int limit = 500,
  }) async {
    final uri = Uri.parse(
      '$_base/market/indicators/$symbol?interval=$interval&limit=$limit',
    );
    final res = await _client.get(uri, headers: _headers());
    _ensureOk(res);
    return Indicators.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  /// GET /signals/{symbol} -> señal + riesgo del activo.
  Future<TradingSignal> getSignal(String symbol, {String interval = '1m'}) async {
    final uri = Uri.parse('$_base/signals/$symbol?interval=$interval');
    final res = await _client.get(uri, headers: _headers());
    _ensureOk(res);
    return TradingSignal.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  /// GET /backtest/{symbol} -> métricas de la estrategia sobre velas históricas.
  Future<BacktestResult> getBacktest(
    String symbol, {
    String interval = '1m',
    int limit = 1000,
  }) async {
    final uri = Uri.parse(
      '$_base/backtest/$symbol?interval=$interval&limit=$limit',
    );
    final res = await _client.get(uri, headers: _headers());
    _ensureOk(res);
    return BacktestResult.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  // -------------------------- Operaciones fiscales --------------------------

  Future<OperationPage> getOperations({
    String? assetId,
    String? side,
    int? year,
    int limit = 50,
    int offset = 0,
  }) async {
    final params = <String, String>{
      'limit': '$limit',
      'offset': '$offset',
      if (assetId != null && assetId.isNotEmpty) 'assetId': assetId,
      if (side != null && side.isNotEmpty) 'side': side,
      if (year != null) 'year': '$year',
    };
    final uri = Uri.parse('$_base/operations').replace(queryParameters: params);
    final res = await _client.get(uri, headers: _headers());
    _ensureOk(res);
    return OperationPage.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  /// GET /operations/export -> devuelve el contenido (JSON o CSV) como texto.
  Future<String> exportOperations({String format = 'json'}) async {
    final uri = Uri.parse('$_base/operations/export')
        .replace(queryParameters: {'format': format});
    final res = await _client.get(uri, headers: _headers());
    _ensureOk(res);
    return utf8.decode(res.bodyBytes);
  }

  /// POST /operations/import -> importa operaciones (con dryRun opcional).
  Future<ImportResult> importOperations({
    required String content,
    String format = 'json',
    bool dryRun = false,
  }) async {
    final res = await _client.post(
      Uri.parse('$_base/operations/import'),
      headers: _headers(json: true),
      body: jsonEncode({'content': content, 'format': format, 'dryRun': dryRun}),
    );
    _ensureOk(res);
    return ImportResult.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  /// GET /operations/brokers -> brokers soportados para importación por CSV.
  Future<List<String>> getSupportedBrokers() async {
    final res = await _client.get(
      Uri.parse('$_base/operations/brokers'),
      headers: _headers(),
    );
    _ensureOk(res);
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    return (data['brokers'] as List<dynamic>).map((e) => e.toString()).toList();
  }

  /// POST /operations/import/broker -> importa el CSV de un broker (dryRun opcional).
  Future<ImportResult> importBrokerCsv({
    required String broker,
    required String content,
    bool dryRun = true,
  }) async {
    final res = await _client.post(
      Uri.parse('$_base/operations/import/broker'),
      headers: _headers(json: true),
      body: jsonEncode({'broker': broker, 'content': content, 'dryRun': dryRun}),
    );
    _ensureOk(res);
    return ImportResult.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  // -------------------------- Eventos corporativos --------------------------

  Future<List<CorporateEvent>> getCorporateEvents({int? year}) async {
    final uri = Uri.parse('$_base/corporate-events').replace(
      queryParameters: {if (year != null) 'year': '$year'},
    );
    final res = await _client.get(uri, headers: _headers());
    _ensureOk(res);
    final data = jsonDecode(res.body) as List<dynamic>;
    return data
        .map((e) => CorporateEvent.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<CorporateEvent> addCorporateEvent(NewCorporateEvent event) async {
    final res = await _client.post(
      Uri.parse('$_base/corporate-events'),
      headers: _headers(json: true),
      body: jsonEncode(event.toJson()),
    );
    _ensureOk(res);
    return CorporateEvent.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  Future<void> deleteCorporateEvent(String id) async {
    final res = await _client.delete(
      Uri.parse('$_base/corporate-events/$id'),
      headers: _headers(),
    );
    _ensureOk(res);
  }

  // -------------------------- Paper trading (Alpaca) --------------------------

  Future<PaperTradingStatus> getPaperStatus() async {
    final res = await _client.get(
      Uri.parse('$_base/paper-trading/status'),
      headers: _headers(),
    );
    _ensureOk(res);
    return PaperTradingStatus.fromJson(
      jsonDecode(res.body) as Map<String, dynamic>,
    );
  }

  Future<List<PaperOrder>> getPaperOrders() async {
    final res = await _client.get(
      Uri.parse('$_base/paper-trading/orders'),
      headers: _headers(),
    );
    _ensureOk(res);
    final data = jsonDecode(res.body) as List<dynamic>;
    return data
        .map((e) => PaperOrder.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Map<String, dynamic>> submitPaperOrder({
    required String assetId,
    required String side,
    required String quantity,
    required bool confirm,
  }) async {
    final res = await _client.post(
      Uri.parse('$_base/paper-trading/orders'),
      headers: _headers(json: true),
      body: jsonEncode({
        'assetId': assetId,
        'side': side,
        'quantity': quantity,
        'confirm': confirm,
      }),
    );
    _ensureOk(res);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// GET /portfolio/derived -> cartera calculada desde el libro (FIFO) en EUR.
  Future<DerivedPortfolio> getDerivedPortfolio() async {
    final res = await _client.get(
      Uri.parse('$_base/portfolio/derived'),
      headers: _headers(),
    );
    _ensureOk(res);
    return DerivedPortfolio.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  Future<InvestmentOperation> createOperation(NewInvestmentOperation operation) async {
    final res = await _client.post(
      Uri.parse('$_base/operations'),
      headers: _headers(json: true),
      body: jsonEncode(operation.toJson()),
    );
    _ensureOk(res);
    return InvestmentOperation.fromJson(
      jsonDecode(res.body) as Map<String, dynamic>,
    );
  }

  Future<void> deleteOperation(String id) async {
    final res = await _client.delete(
      Uri.parse('$_base/operations/$id'),
      headers: _headers(),
    );
    _ensureOk(res);
  }

  Future<TaxReport> getTaxReport(int year) async {
    final res = await _client.get(
      Uri.parse('$_base/tax/reports/$year'),
      headers: _headers(),
    );
    _ensureOk(res);
    return TaxReport.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  Future<String> getTaxCsv(int year) async {
    final res = await _client.get(
      Uri.parse('$_base/tax/reports/$year/csv'),
      headers: _headers(),
    );
    _ensureOk(res);
    return utf8.decode(res.bodyBytes);
  }

  // -------------------------- Cartera --------------------------

  /// GET /portfolio -> posiciones valoradas + resumen P&L.
  Future<Portfolio> getPortfolio() async {
    final res = await _client.get(Uri.parse('$_base/portfolio'), headers: _headers());
    _ensureOk(res);
    return Portfolio.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  /// POST /portfolio/positions -> añade una posición.
  Future<void> addPosition({
    required String assetId,
    required double quantity,
    required double averagePrice,
  }) async {
    final res = await _client.post(
      Uri.parse('$_base/portfolio/positions'),
      headers: _headers(json: true),
      body: jsonEncode({
        'assetId': assetId,
        'quantity': quantity,
        'averagePrice': averagePrice,
      }),
    );
    _ensureOk(res);
  }

  /// DELETE /portfolio/positions/{id} -> borra una posición.
  Future<void> deletePosition(String id) async {
    final res = await _client.delete(
      Uri.parse('$_base/portfolio/positions/$id'),
      headers: _headers(),
    );
    _ensureOk(res);
  }

  // -------------------------- Dashboard --------------------------

  /// GET /dashboard -> resumen del mercado seguido.
  Future<Dashboard> getDashboard() async {
    final res = await _client.get(Uri.parse('$_base/dashboard'), headers: _headers());
    _ensureOk(res);
    return Dashboard.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  // -------------------------- Watchlist --------------------------

  /// GET /watchlist -> símbolos seguidos.
  Future<List<String>> getWatchlist() async {
    final res = await _client.get(Uri.parse('$_base/watchlist'), headers: _headers());
    _ensureOk(res);
    final data = jsonDecode(res.body) as List<dynamic>;
    return data.map((e) => e as String).toList();
  }

  /// POST /watchlist -> añade un símbolo.
  Future<void> addToWatchlist(String assetId) async {
    final res = await _client.post(
      Uri.parse('$_base/watchlist'),
      headers: _headers(json: true),
      body: jsonEncode({'assetId': assetId}),
    );
    _ensureOk(res);
  }

  /// DELETE /watchlist/{assetId} -> quita un símbolo.
  Future<void> removeFromWatchlist(String assetId) async {
    final res = await _client.delete(
      Uri.parse('$_base/watchlist/$assetId'),
      headers: _headers(),
    );
    _ensureOk(res);
  }

  // -------------------------- Alertas --------------------------

  /// POST /alerts -> crea una alerta.
  /// [type]: PRICE_CROSS | PERCENT_CHANGE | INDICATOR_CROSS.
  /// [direction]: 'ABOVE' o 'BELOW'.
  /// [indicator]: solo para INDICATOR_CROSS (ej. 'rsi14').
  Future<void> createAlert({
    required String assetId,
    required String type,
    required String direction,
    required double threshold,
    String? indicator,
    String timeframe = '1m',
  }) async {
    final body = <String, dynamic>{
      'assetId': assetId,
      'type': type,
      'direction': direction,
      'threshold': threshold,
      'timeframe': timeframe,
    };
    if (indicator != null) body['indicator'] = indicator;
    final res = await _client.post(
      Uri.parse('$_base/alerts'),
      headers: _headers(json: true),
      body: jsonEncode(body),
    );
    _ensureOk(res);
  }

  // -------------------------- Administración (SUPERADMIN) --------------------------

  /// GET /admin/users -> lista de usuarios (solo superadmin).
  Future<List<Map<String, dynamic>>> adminListUsers() async {
    final res = await _client.get(
      Uri.parse('$_base/admin/users'),
      headers: _headers(),
    );
    _ensureOk(res);
    final data = jsonDecode(res.body) as List<dynamic>;
    return data.map((e) => e as Map<String, dynamic>).toList();
  }

  /// POST /admin/users -> crea un usuario con rol.
  Future<Map<String, dynamic>> adminCreateUser({
    required String email,
    required String password,
    required String role,
  }) async {
    final res = await _client.post(
      Uri.parse('$_base/admin/users'),
      headers: _headers(json: true),
      body: jsonEncode({'email': email, 'password': password, 'role': role}),
    );
    _ensureOk(res);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// PUT /admin/users/{id}/role -> cambia el rol de un usuario.
  Future<Map<String, dynamic>> adminSetRole(String userId, String role) async {
    final res = await _client.put(
      Uri.parse('$_base/admin/users/$userId/role'),
      headers: _headers(json: true),
      body: jsonEncode({'role': role}),
    );
    _ensureOk(res);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// PUT /admin/users/{id}/active -> activa o desactiva un usuario.
  Future<Map<String, dynamic>> adminSetActive(String userId, bool isActive) async {
    final res = await _client.put(
      Uri.parse('$_base/admin/users/$userId/active'),
      headers: _headers(json: true),
      body: jsonEncode({'isActive': isActive}),
    );
    _ensureOk(res);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// DELETE /admin/users/{id} -> borra un usuario.
  Future<void> adminDeleteUser(String userId) async {
    final res = await _client.delete(
      Uri.parse('$_base/admin/users/$userId'),
      headers: _headers(),
    );
    _ensureOk(res);
  }

  // -------------------------- Notificaciones (Telegram) --------------------------

  /// GET /notifications/telegram -> estado de la vinculación del usuario.
  /// Devuelve { botConfigured, linked, enabled }.
  Future<Map<String, dynamic>> getTelegramStatus() async {
    final res = await _client.get(
      Uri.parse('$_base/notifications/telegram'),
      headers: _headers(),
    );
    _ensureOk(res);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// POST /notifications/telegram/link -> genera un código de vinculación.
  /// Devuelve { botConfigured, code?, expiresInSeconds?, instructions? }.
  Future<Map<String, dynamic>> createTelegramLinkCode() async {
    final res = await _client.post(
      Uri.parse('$_base/notifications/telegram/link'),
      headers: _headers(),
    );
    _ensureOk(res);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// POST /notifications/telegram/enabled -> activa o pausa el envío.
  Future<void> setTelegramEnabled(bool enabled) async {
    final res = await _client.post(
      Uri.parse('$_base/notifications/telegram/enabled'),
      headers: _headers(json: true),
      body: jsonEncode({'enabled': enabled}),
    );
    _ensureOk(res);
  }

  /// DELETE /notifications/telegram -> desvincula el chat.
  Future<void> unlinkTelegram() async {
    final res = await _client.delete(
      Uri.parse('$_base/notifications/telegram'),
      headers: _headers(),
    );
    _ensureOk(res);
  }

  void _ensureOk(http.Response res) {
    if (res.statusCode == 401) {
      onUnauthorized?.call();
      throw const UnauthorizedException();
    }
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw Exception('API error ${res.statusCode}: ${res.body}');
    }
  }

  void dispose() => _client.close();
}
