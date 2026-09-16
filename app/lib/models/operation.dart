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
/// Si [fxRateToEur] es null y [fxSource] es ECB, el backend resuelve el cambio.
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
    this.fxRateToEur,
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
  final String? fxRateToEur;
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
        if (fxRateToEur != null && fxRateToEur!.isNotEmpty) 'fxRateToEur': fxRateToEur,
        'fxSource': fxSource,
        'source': source,
        if (notes != null && notes!.isNotEmpty) 'notes': notes,
      };
}

/// Página de operaciones con metadatos para scroll incremental.
class OperationPage {
  const OperationPage({
    required this.items,
    required this.total,
    required this.hasMore,
    required this.nextOffset,
  });

  final List<InvestmentOperation> items;
  final int total;
  final bool hasMore;
  final int? nextOffset;

  factory OperationPage.fromJson(Map<String, dynamic> json) => OperationPage(
        items: (json['items'] as List<dynamic>)
            .map((e) => InvestmentOperation.fromJson(e as Map<String, dynamic>))
            .toList(),
        total: (json['total'] as num).toInt(),
        hasMore: json['hasMore'] as bool? ?? false,
        nextOffset: json['nextOffset'] == null
            ? null
            : (json['nextOffset'] as num).toInt(),
      );
}

/// Resultado de una importación de operaciones.
class ImportResult {
  const ImportResult({
    required this.dryRun,
    required this.received,
    required this.created,
    required this.skipped,
    required this.failed,
  });

  final bool dryRun;
  final int received;
  final int created;
  final int skipped;
  final int failed;

  factory ImportResult.fromJson(Map<String, dynamic> json) => ImportResult(
        dryRun: json['dryRun'] as bool? ?? false,
        received: (json['received'] as num).toInt(),
        created: (json['created'] as num).toInt(),
        skipped: (json['skipped'] as num).toInt(),
        failed: (json['failed'] as num).toInt(),
      );
}
