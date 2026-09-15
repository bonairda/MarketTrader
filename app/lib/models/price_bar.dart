/// Vela de precio (proviene de /market/bars/{symbol}).
class PriceBar {
  final DateTime openTime;
  final double open;
  final double high;
  final double low;
  final double close;
  final double? volume;

  const PriceBar({
    required this.openTime,
    required this.open,
    required this.high,
    required this.low,
    required this.close,
    this.volume,
  });

  factory PriceBar.fromJson(Map<String, dynamic> json) {
    return PriceBar(
      openTime: DateTime.parse(json['openTime'] as String),
      open: (json['open'] as num).toDouble(),
      high: (json['high'] as num).toDouble(),
      low: (json['low'] as num).toDouble(),
      close: (json['close'] as num).toDouble(),
      volume: json['volume'] == null ? null : (json['volume'] as num).toDouble(),
    );
  }
}
