/// Indicadores técnicos de un activo (proviene de /market/indicators/{symbol}).
///
/// Cada serie es una lista alineada por índice con `times`; los valores pueden
/// ser null donde el indicador aún no tiene datos suficientes.
class Indicators {
  final String symbol;
  final String interval;
  final Map<String, List<double?>> series;

  const Indicators({
    required this.symbol,
    required this.interval,
    required this.series,
  });

  factory Indicators.fromJson(Map<String, dynamic> json) {
    final rawIndicators = json['indicators'] as Map<String, dynamic>;
    final series = <String, List<double?>>{};
    rawIndicators.forEach((key, value) {
      series[key] = (value as List<dynamic>)
          .map((e) => e == null ? null : (e as num).toDouble())
          .toList();
    });
    return Indicators(
      symbol: json['symbol'] as String,
      interval: json['interval'] as String,
      series: series,
    );
  }

  /// Último valor no nulo de una serie (el indicador "actual"), o null.
  double? latest(String name) {
    final list = series[name];
    if (list == null) return null;
    for (var i = list.length - 1; i >= 0; i--) {
      if (list[i] != null) return list[i];
    }
    return null;
  }
}
