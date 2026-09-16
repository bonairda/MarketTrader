/// Cartera derivada del libro de operaciones (FIFO), valorada en EUR.
class DerivedPosition {
  const DerivedPosition({
    required this.assetId,
    required this.quantity,
    required this.avgCostEur,
    required this.costEur,
    required this.priceEur,
    required this.marketValueEur,
    required this.pnlEur,
    required this.pnlPercent,
  });

  final String assetId;
  final String quantity;
  final String avgCostEur;
  final String costEur;
  final String? priceEur;
  final String? marketValueEur;
  final String? pnlEur;
  final String? pnlPercent;

  factory DerivedPosition.fromJson(Map<String, dynamic> json) => DerivedPosition(
        assetId: json['assetId'].toString(),
        quantity: json['quantity'].toString(),
        avgCostEur: json['avgCostEur'].toString(),
        costEur: json['costEur'].toString(),
        priceEur: json['priceEur'] as String?,
        marketValueEur: json['marketValueEur'] as String?,
        pnlEur: json['pnlEur'] as String?,
        pnlPercent: json['pnlPercent'] as String?,
      );
}

class DerivedPortfolio {
  const DerivedPortfolio({
    required this.positions,
    required this.totalCostEur,
    required this.totalValueEur,
    required this.totalPnlEur,
    required this.totalPnlPercent,
    required this.note,
  });

  final List<DerivedPosition> positions;
  final String totalCostEur;
  final String totalValueEur;
  final String totalPnlEur;
  final String? totalPnlPercent;
  final String note;

  factory DerivedPortfolio.fromJson(Map<String, dynamic> json) {
    final summary = json['summary'] as Map<String, dynamic>;
    return DerivedPortfolio(
      positions: (json['positions'] as List<dynamic>)
          .map((e) => DerivedPosition.fromJson(e as Map<String, dynamic>))
          .toList(),
      totalCostEur: summary['totalCostEur'].toString(),
      totalValueEur: summary['totalValueEur'].toString(),
      totalPnlEur: summary['totalPnlEur'].toString(),
      totalPnlPercent: summary['totalPnlPercent'] as String?,
      note: json['note'].toString(),
    );
  }
}
