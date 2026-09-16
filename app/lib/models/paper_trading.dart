/// Estado del paper trading (habilitado sólo si hay credenciales de Alpaca).
class PaperTradingStatus {
  const PaperTradingStatus({required this.enabled, required this.mode});

  final bool enabled;
  final String mode;

  factory PaperTradingStatus.fromJson(Map<String, dynamic> json) =>
      PaperTradingStatus(
        enabled: json['enabled'] as bool? ?? false,
        mode: json['mode']?.toString() ?? 'paper',
      );
}

/// Orden de paper trading devuelta por Alpaca (simulada, sin dinero real).
class PaperOrder {
  const PaperOrder({
    required this.symbol,
    required this.side,
    required this.quantity,
    required this.status,
    this.submittedAt,
  });

  final String symbol;
  final String side;
  final String quantity;
  final String status;
  final String? submittedAt;

  factory PaperOrder.fromJson(Map<String, dynamic> json) => PaperOrder(
        symbol: (json['symbol'] ?? json['symbol'] ?? '').toString(),
        side: (json['side'] ?? '').toString().toUpperCase(),
        quantity: (json['qty'] ?? json['quantity'] ?? '').toString(),
        status: (json['status'] ?? '').toString(),
        submittedAt: (json['submitted_at'] ?? json['submittedAt']) as String?,
      );
}
