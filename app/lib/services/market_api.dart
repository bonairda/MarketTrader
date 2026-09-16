import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config.dart';
import '../models/backtest.dart';
import '../models/dashboard.dart';
import '../models/indicators.dart';
import '../models/live_price.dart';
import '../models/portfolio.dart';
import '../models/price_bar.dart';
import '../models/signal.dart';

/// Cliente HTTP de la API de MarketTracker.
class MarketApi {
  MarketApi({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;
  String get _base => AppConfig.apiBaseUrl;

  /// GET /market/prices -> precios en vivo de la watchlist.
  Future<List<LivePrice>> getLivePrices() async {
    final res = await _client.get(Uri.parse('$_base/market/prices'));
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
    final res = await _client.get(uri);
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
    final res = await _client.get(uri);
    _ensureOk(res);
    return Indicators.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  /// GET /signals/{symbol} -> señal + riesgo del activo.
  Future<TradingSignal> getSignal(String symbol, {String interval = '1m'}) async {
    final uri = Uri.parse('$_base/signals/$symbol?interval=$interval');
    final res = await _client.get(uri);
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
    final res = await _client.get(uri);
    _ensureOk(res);
    return BacktestResult.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  /// GET /portfolio -> posiciones valoradas + resumen P&L.
  Future<Portfolio> getPortfolio() async {
    final res = await _client.get(Uri.parse('$_base/portfolio'));
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
      headers: {'Content-Type': 'application/json'},
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
    final res =
        await _client.delete(Uri.parse('$_base/portfolio/positions/$id'));
    _ensureOk(res);
  }

  /// GET /dashboard -> resumen del mercado seguido.
  Future<Dashboard> getDashboard() async {
    final res = await _client.get(Uri.parse('$_base/dashboard'));
    _ensureOk(res);
    return Dashboard.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  /// GET /watchlist -> símbolos seguidos.
  Future<List<String>> getWatchlist() async {
    final res = await _client.get(Uri.parse('$_base/watchlist'));
    _ensureOk(res);
    final data = jsonDecode(res.body) as List<dynamic>;
    return data.map((e) => e as String).toList();
  }

  /// POST /watchlist -> añade un símbolo.
  Future<void> addToWatchlist(String assetId) async {
    final res = await _client.post(
      Uri.parse('$_base/watchlist'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'assetId': assetId}),
    );
    _ensureOk(res);
  }

  /// DELETE /watchlist/{assetId} -> quita un símbolo.
  Future<void> removeFromWatchlist(String assetId) async {
    final res = await _client.delete(Uri.parse('$_base/watchlist/$assetId'));
    _ensureOk(res);
  }

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
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _ensureOk(res);
  }

  void _ensureOk(http.Response res) {
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw Exception('API error ${res.statusCode}: ${res.body}');
    }
  }

  void dispose() => _client.close();
}
