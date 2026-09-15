/// Precio en vivo de un activo (proviene de /market/prices).
class LivePrice {
  final String symbol;
  final double price;
  final int timestampMs;

  const LivePrice({
    required this.symbol,
    required this.price,
    required this.timestampMs,
  });

  factory LivePrice.fromJson(Map<String, dynamic> json) {
    return LivePrice(
      symbol: json['symbol'] as String,
      price: (json['price'] as num).toDouble(),
      timestampMs: (json['ts'] as num).toInt(),
    );
  }
}
