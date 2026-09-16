/// Resultado de un backtest (proviene de /backtest/{symbol}).
class BacktestResult {
  final String symbol;
  final int candles;
  final int trades;
  final double winRate;
  final double totalReturnPct;
  final double avgReturnPct;
  final double maxDrawdownPct;

  const BacktestResult({
    required this.symbol,
    required this.candles,
    required this.trades,
    required this.winRate,
    required this.totalReturnPct,
    required this.avgReturnPct,
    required this.maxDrawdownPct,
  });

  factory BacktestResult.fromJson(Map<String, dynamic> json) {
    double d(dynamic v) => (v as num).toDouble();
    return BacktestResult(
      symbol: json['symbol'] as String,
      candles: (json['candles'] as num).toInt(),
      trades: (json['trades'] as num).toInt(),
      winRate: d(json['winRate']),
      totalReturnPct: d(json['totalReturnPct']),
      avgReturnPct: d(json['avgReturnPct']),
      maxDrawdownPct: d(json['maxDrawdownPct']),
    );
  }
}
