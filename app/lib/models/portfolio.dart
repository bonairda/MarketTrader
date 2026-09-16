/// Una posición valorada de la cartera (proviene de /portfolio -> positions[]).
class PortfolioPosition {
  final String id;
  final String assetId;
  final double quantity;
  final double averagePrice;
  final double? currentPrice;
  final double? marketValue;
  final double cost;
  final double? pnl;
  final double? pnlPercent;

  const PortfolioPosition({
    required this.id,
    required this.assetId,
    required this.quantity,
    required this.averagePrice,
    required this.currentPrice,
    required this.marketValue,
    required this.cost,
    required this.pnl,
    required this.pnlPercent,
  });

  factory PortfolioPosition.fromJson(Map<String, dynamic> json) {
    double? dn(dynamic v) => v == null ? null : (v as num).toDouble();
    double d(dynamic v) => (v as num).toDouble();
    return PortfolioPosition(
      id: json['id'] as String,
      assetId: json['assetId'] as String,
      quantity: d(json['quantity']),
      averagePrice: d(json['averagePrice']),
      currentPrice: dn(json['currentPrice']),
      marketValue: dn(json['marketValue']),
      cost: d(json['cost']),
      pnl: dn(json['pnl']),
      pnlPercent: dn(json['pnlPercent']),
    );
  }
}

/// Totales de la cartera (proviene de /portfolio -> summary).
class PortfolioSummary {
  final double totalCost;
  final double totalValue;
  final double totalPnl;
  final double? totalPnlPercent;
  final int positions;

  const PortfolioSummary({
    required this.totalCost,
    required this.totalValue,
    required this.totalPnl,
    required this.totalPnlPercent,
    required this.positions,
  });

  factory PortfolioSummary.fromJson(Map<String, dynamic> json) {
    double? dn(dynamic v) => v == null ? null : (v as num).toDouble();
    double d(dynamic v) => (v as num).toDouble();
    return PortfolioSummary(
      totalCost: d(json['totalCost']),
      totalValue: d(json['totalValue']),
      totalPnl: d(json['totalPnl']),
      totalPnlPercent: dn(json['totalPnlPercent']),
      positions: (json['positions'] as num).toInt(),
    );
  }
}

/// Respuesta completa de /portfolio.
class Portfolio {
  final List<PortfolioPosition> positions;
  final PortfolioSummary summary;

  const Portfolio({required this.positions, required this.summary});

  factory Portfolio.fromJson(Map<String, dynamic> json) {
    final list = (json['positions'] as List)
        .map((e) => PortfolioPosition.fromJson(e as Map<String, dynamic>))
        .toList();
    return Portfolio(
      positions: list,
      summary: PortfolioSummary.fromJson(json['summary'] as Map<String, dynamic>),
    );
  }
}
