/// Precio en vivo de un activo (proviene de /market/prices).
///
/// `price` y `timestampMs` pueden ser null: un activo recién añadido a la
/// watchlist (o una acción/forex fuera de horario) aún no tiene precio en Redis,
/// pero igualmente aparece en la lista como "esperando precio".
class LivePrice {
  final String symbol;
  final double? price;
  final int? timestampMs;

  const LivePrice({
    required this.symbol,
    required this.price,
    required this.timestampMs,
  });

  /// True si todavía no hay un precio en vivo para este activo.
  bool get isPending => price == null;

  factory LivePrice.fromJson(Map<String, dynamic> json) {
    final rawPrice = json['price'];
    final rawTs = json['ts'];
    return LivePrice(
      symbol: json['symbol'] as String,
      price: rawPrice == null ? null : (rawPrice as num).toDouble(),
      timestampMs: rawTs == null ? null : (rawTs as num).toInt(),
    );
  }
}
