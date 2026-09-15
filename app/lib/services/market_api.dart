import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config.dart';
import '../models/live_price.dart';
import '../models/price_bar.dart';

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

  /// POST /alerts -> crea una alerta de cruce de precio.
  /// [direction] debe ser 'ABOVE' o 'BELOW'.
  Future<void> createPriceAlert({
    required String assetId,
    required String direction,
    required double threshold,
  }) async {
    final res = await _client.post(
      Uri.parse('$_base/alerts'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'assetId': assetId,
        'direction': direction,
        'threshold': threshold,
      }),
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
