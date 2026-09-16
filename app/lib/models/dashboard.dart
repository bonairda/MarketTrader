/// Resumen de un activo en el dashboard.
class AssetSummary {
  final String symbol;
  final double? price;
  final double? changePercent;
  final double? high;
  final double? low;
  final double? volatility;

  const AssetSummary({
    required this.symbol,
    this.price,
    this.changePercent,
    this.high,
    this.low,
    this.volatility,
  });

  factory AssetSummary.fromJson(Map<String, dynamic> json) {
    double? d(dynamic v) => v == null ? null : (v as num).toDouble();
    return AssetSummary(
      symbol: json['symbol'] as String,
      price: d(json['price']),
      changePercent: d(json['changePercent']),
      high: d(json['high']),
      low: d(json['low']),
      volatility: d(json['volatility']),
    );
  }
}

/// Payload completo del dashboard (proviene de /dashboard).
class Dashboard {
  final List<AssetSummary> watchlist;
  final List<AssetSummary> gainers;
  final List<AssetSummary> losers;
  final List<AssetSummary> mostVolatile;
  final int tracked;

  const Dashboard({
    required this.watchlist,
    required this.gainers,
    required this.losers,
    required this.mostVolatile,
    required this.tracked,
  });

  factory Dashboard.fromJson(Map<String, dynamic> json) {
    List<AssetSummary> list(String key) => ((json[key] as List<dynamic>?) ?? [])
        .map((e) => AssetSummary.fromJson(e as Map<String, dynamic>))
        .toList();
    final counts = (json['counts'] as Map<String, dynamic>?) ?? {};
    return Dashboard(
      watchlist: list('watchlist'),
      gainers: list('gainers'),
      losers: list('losers'),
      mostVolatile: list('mostVolatile'),
      tracked: (counts['tracked'] as num?)?.toInt() ?? 0,
    );
  }
}
