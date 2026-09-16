/// Operación fiscal devuelta por /operations.
/// Los decimales se conservan como String para no perder precisión.
class InvestmentOperation {
  const InvestmentOperation({
    required this.id,
    required this.assetId,
    required this.side,
    required this.tradeDate,
    required this.quantity,
    required this.unitPriceOriginal,
    required this.grossAmountOriginal,
    required this.feesOriginal,
    required this.currency,
    required this.fxRateToEur,
    required this.grossAmountEur,
    required this.feesEur,
    required this.cashAmountEur,
    required this.source,
    this.executedAt,
    this.fxSource,
    this.externalId,
    this.notes,
  });

  final String id;
  final String assetId;
  final String side;
  final String tradeDate;
  final String? executedAt;
  final String quantity;
  final String unitPriceOriginal;
  final String grossAmountOriginal;
  final String feesOriginal;
  final String currency;
  final String fxRateToEur;
  final String grossAmountEur;
  final String feesEur;
  final String cashAmountEur;
  final String? fxSource;
  final String source;
  final String? externalId;
  final String? notes;

  bool get isBuy => side == 'BUY';

  factory InvestmentOperation.fromJson(Map<String, dynamic> json) {
    String s(String key) => json[key].toString();
    return InvestmentOperation(
      id: s('id'),
      assetId: s('assetId'),
      side: s('side'),
      tradeDate: s('tradeDate'),
      executedAt: json['executedAt'] as String?,
      quantity: s('quantity'),
      unitPriceOriginal: s('unitPriceOriginal'),
      grossAmountOriginal: s('grossAmountOriginal'),
      feesOriginal: s('feesOriginal'),
      currency: s('currency'),
      fxRateToEur: s('fxRateToEur'),
      grossAmountEur: s('grossAmountEur'),
      feesEur: s('feesEur'),
      cashAmountEur: s('cashAmountEur'),
      fxSource: json['fxSource'] as String?,
      source: s('source'),
      externalId: json['externalId'] as String?,
      notes: json['notes'] as String?,
    );
  }
}

/// Payload para crear una operación.
class NewInvestmentOperation {
  const NewInvestmentOperation({
    required this.assetId,
    required this.side,
    required this.tradeDate,
    required this.quantity,
    required this.unitPriceOriginal,
    required this.grossAmountOriginal,
    required this.feesOriginal,
    required this.currency,
    required this.fxRateToEur,
    this.fxSource = 'USER',
    this.source = 'MANUAL',
    this.notes,
  });

  final String assetId;
  final String side;
  final String tradeDate;
  final String quantity;
  final String unitPriceOriginal;
  final String grossAmountOriginal;
  final String feesOriginal;
  final String currency;
  final String fxRateToEur;
  final String fxSource;
  final String source;
  final String? notes;

  Map<String, dynamic> toJson() => {
        'assetId': assetId,
        'side': side,
        'tradeDate': tradeDate,
        'quantity': quantity,
        'unitPriceOriginal': unitPriceOriginal,
        'grossAmountOriginal': grossAmountOriginal,
        'feesOriginal': feesOriginal,
        'currency': currency,
        'fxRateToEur': fxRateToEur,
        'fxSource': fxSource,
        'source': source,
        if (notes != null && notes!.isNotEmpty) 'notes': notes,
      };
}
